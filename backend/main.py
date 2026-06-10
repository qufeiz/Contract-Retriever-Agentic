"""FastAPI app — the agentic /api/ask endpoint.

The Next.js frontend's /api/ask route proxies to this backend. One question in, the Aletheia
output contract out. Returns 503 if no Anthropic key is configured (never fakes an answer).

Two transports for the SAME agent run:
  - **Synchronous** `POST /api/ask` — one request, blocks until the answer. Fine direct-to-Fly
    (no request cap) and used by the prod-verify runbook; but Vercel's serverless proxy has a HARD
    300s ceiling, so the heaviest query 504s through it. Kept for direct/back-compat callers.
  - **Async job** `POST /api/ask/jobs` → returns a job id immediately (well under any cap); the agent
    runs in a background task on Fly (no cap); the frontend polls `GET /api/ask/jobs/{id}` for the
    live agent trace as it works, then the final cited answer. This is the path the public Vercel
    demo uses so NO golden query 504s. (See docs/features/.../04-implementation.md §async-job.)

Public-surface guards (the endpoint is internet-exposed): a length cap on the question (413)
and a simple per-IP rolling rate limit (429), so a hijacked/abusive caller can't bleed agent
runs. The deeper RCE/prompt-injection defense — the agent's read-only allow-list — lives in
backend/agent.py (`_pre_tool_use`).

Health vs readiness: `/health` is liveness (process up + key PRESENT) — cheap, frequent. `/ready`
is real readiness (one minimal agent turn actually completes), used on deploy / before declaring
live, because a present-but-dead key (e.g. out of credit) once passed /health while every agent run
died at CLI startup. When the agent CLI fails, the REAL reason (e.g. "Credit balance is too low")
is surfaced in the job/response error — answer_question re-raises it instead of the SDK's generic
"exit code 1" wrapper.
"""
import asyncio
import os
import time
import uuid
from collections import deque
from dataclasses import dataclass, field

from fastapi import FastAPI, File, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.agent import answer_question, probe_agent_ready
from backend.config import (
    JOB_TTL_SEC,
    MAX_QUESTION_CHARS,
    RATE_LIMIT_MAX,
    RATE_LIMIT_WINDOW_SEC,
    UPLOAD_MAX_FILES,
    UPLOAD_MODEL,
    anthropic_key_present,
)
from backend.models import AskRequest, AskResponse, TraceStep
from backend.uploads import (
    UploadError,
    create_session,
    finalize_session_map,
    get_session,
    store_upload,
)

app = FastAPI(title="Aletheia Agentic API")

# CORS: allow the Vercel demo origin (set at deploy) plus localhost for dev.
# A comma-separated ALLOWED_ORIGINS env overrides; default keeps local dev working.
_origins_env = os.environ.get("ALLOWED_ORIGINS", "").strip()
_allow_origins = (
    [o.strip() for o in _origins_env.split(",") if o.strip()]
    if _origins_env
    else ["http://localhost:3000"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allow_origins,
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type"],
)

# In-process per-IP rate limiter (single-instance Fly app). Maps client IP →
# deque of recent request timestamps; prunes outside the rolling window.
_REQUESTS: dict[str, deque] = {}


def _rate_limited(ip: str) -> bool:
    now = time.monotonic()
    dq = _REQUESTS.setdefault(ip, deque())
    while dq and now - dq[0] > RATE_LIMIT_WINDOW_SEC:
        dq.popleft()
    if len(dq) >= RATE_LIMIT_MAX:
        return True
    dq.append(now)
    return False


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


# ---------------------------------------------------------------------------
# Async job store (in-process; single-instance Fly app, same assumption as the
# rate limiter). A job holds the live trace as the agent works + the final
# result/error. Finished jobs are pruned after JOB_TTL_SEC so the dict can't grow
# unbounded. This is a demo-scale store, not a durable queue — a machine restart
# drops in-flight jobs (the UI re-submits); that's acceptable for this surface.
# ---------------------------------------------------------------------------
@dataclass
class Job:
    status: str = "running"  # running | done | error
    trace: list[TraceStep] = field(default_factory=list)
    result: AskResponse | None = None
    error: str | None = None
    created: float = field(default_factory=time.monotonic)


_JOBS: dict[str, Job] = {}


def _prune_jobs() -> None:
    """Drop finished jobs past their TTL so the store stays bounded."""
    now = time.monotonic()
    stale = [
        jid
        for jid, j in _JOBS.items()
        if j.status in ("done", "error") and now - j.created > JOB_TTL_SEC
    ]
    for jid in stale:
        _JOBS.pop(jid, None)


async def _run_job(job_id: str, question: str, session_id: str | None = None) -> None:
    """Background task: run the agent, streaming trace into the job, then store the result."""
    job = _JOBS[job_id]

    async def _on_trace(step: TraceStep) -> None:
        job.trace.append(step)

    try:
        # An upload run (session present) uses the stronger UPLOAD_MODEL (Sonnet) — Haiku is
        # unreliable on arbitrary uploaded data (it mis-cited CSV rows); the committed-corpus
        # path (no session) keeps the default MODEL.
        model = UPLOAD_MODEL if session_id else None
        resp = await answer_question(
            question, on_trace=_on_trace, session_id=session_id, model=model
        )
        job.result = resp
        job.trace = list(resp.trace)  # the authoritative final trace
        job.status = "done"
    except ValueError as e:  # input guard tripped inside the agent
        job.error = str(e)
        job.status = "error"
    except Exception as e:  # surface real failures, never fabricate a pass
        job.error = str(e)
        job.status = "error"


def _guard_question(question: str, request: Request) -> JSONResponse | None:
    """Shared pre-flight checks (key/rate/empty/length). Returns an error response or None."""
    if not anthropic_key_present():
        return JSONResponse(
            status_code=503,
            content={"error": "ANTHROPIC_API_KEY is not configured on the server."},
        )
    if _rate_limited(_client_ip(request)):
        return JSONResponse(
            status_code=429,
            content={"error": "Too many requests — please slow down and retry shortly."},
        )
    if not question:
        return JSONResponse(status_code=400, content={"error": "question is required"})
    if len(question) > MAX_QUESTION_CHARS:
        return JSONResponse(
            status_code=413,
            content={"error": f"question too long (max {MAX_QUESTION_CHARS} characters)."},
        )
    return None


@app.get("/health")
async def health() -> dict:
    """Liveness only: the process is up and a key is PRESENT. Does NOT prove the key works —
    use /ready for that (a present-but-dead key once shipped a broken demo behind this green check)."""
    return {"ok": True, "key_configured": anthropic_key_present()}


@app.get("/ready")
async def ready():
    """Real readiness: run ONE minimal agent turn and report whether the CLI/key can actually
    complete. Returns 200 {ready:true} when the agent works, 503 {ready:false, reason:"..."} with
    the real reason (e.g. "Credit balance is too low") when it can't. This is a real API call (a
    couple of tokens), so call it on deploy / before declaring live — not as a high-frequency probe."""
    if not anthropic_key_present():
        return JSONResponse(
            status_code=503,
            content={"ready": False, "reason": "ANTHROPIC_API_KEY is not configured."},
        )
    # Run in a detached task, not inline in the request: the readiness probe's fallback (a direct
    # `claude -p` to recover the real reason) spawns a subprocess right after the SDK's child failed,
    # which the in-request uvloop task can silently no-op on. A standalone task gets a clean
    # child-watcher context — the same reason the async-job path (_run_job, itself a create_task)
    # reliably surfaces "Credit balance is too low".
    ok, reason = await asyncio.create_task(probe_agent_ready())
    return JSONResponse(
        status_code=200 if ok else 503,
        content={"ready": ok, "reason": reason},
    )


@app.post("/api/ask", response_model=AskResponse)
async def ask(req: AskRequest, request: Request):
    """Synchronous: run the agent and block until the answer (direct-to-Fly / back-compat)."""
    question = (req.question or "").strip()
    guard = _guard_question(question, request)
    if guard is not None:
        return guard
    try:
        # An upload run (session present) uses the stronger UPLOAD_MODEL; the committed-corpus path
        # keeps the default model. Same policy as the async-job path.
        model = UPLOAD_MODEL if req.session_id else None
        result = await answer_question(question, session_id=req.session_id, model=model)
        return result
    except ValueError as e:  # input guard tripped inside the agent
        return JSONResponse(status_code=400, content={"error": str(e)})
    except Exception as e:  # surface real failures, never fabricate a pass
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/ask/jobs")
async def submit_job(req: AskRequest, request: Request):
    """Async: create a job, start the agent in the background, return the job id immediately.

    Returns fast (well under any serverless cap). The caller polls GET /api/ask/jobs/{id}.
    A `session_id` (from a prior /api/uploads) scopes the run to that session's uploaded files.
    """
    question = (req.question or "").strip()
    guard = _guard_question(question, request)
    if guard is not None:
        return guard
    _prune_jobs()
    job_id = uuid.uuid4().hex
    _JOBS[job_id] = Job()
    # Fire-and-forget; the task streams trace into the job and stores the result.
    asyncio.create_task(_run_job(job_id, question, session_id=req.session_id))
    return JSONResponse(status_code=202, content={"job_id": job_id, "status": "running"})


@app.post("/api/uploads")
async def upload(request: Request, files: list[UploadFile] = File(...)):
    """Live file upload: store the client's CSV/PDF/xlsx in a fresh per-session dir, pre-extract
    PDFs, auto-generate the session map, and return {session_id, files} so the subsequent ask can
    carry the session_id and the agent answers over the uploaded files.

    Validation (type/size/filename) happens at upload, BEFORE any agent run is spent — a bad file
    is rejected here with a clear 4xx. The unguessable session_id + the agent's read-only hook
    (scoped to this session's dir only) are the isolation/hardening boundary; this endpoint just
    writes the store.
    """
    if not anthropic_key_present():
        return JSONResponse(
            status_code=503,
            content={"error": "ANTHROPIC_API_KEY is not configured on the server."},
        )
    if _rate_limited(_client_ip(request)):
        return JSONResponse(
            status_code=429,
            content={"error": "Too many requests — please slow down and retry shortly."},
        )
    if not files:
        return JSONResponse(status_code=400, content={"error": "no files uploaded"})
    if len(files) > UPLOAD_MAX_FILES:
        return JSONResponse(
            status_code=400,
            content={"error": f"too many files (max {UPLOAD_MAX_FILES} per session)."},
        )

    session = create_session()
    stored = []
    try:
        for f in files:
            data = await f.read()
            uf = store_upload(session, f.filename or "upload", data)
            stored.append(uf)
    except UploadError as e:
        # A bad file: discard the whole half-built session so a client never half-uploads.
        from backend.uploads import prune_session_now  # local import to keep config import order

        prune_session_now(session.session_id)
        return JSONResponse(status_code=400, content={"error": str(e)})

    finalize_session_map(session)
    return JSONResponse(
        status_code=201,
        content={
            "session_id": session.session_id,
            "files": [
                {
                    "name": uf.name,
                    "kind": uf.kind,
                    "size": uf.size,
                    "columns": uf.columns,
                    "pages": uf.pages,
                    "rows": uf.rows,
                }
                for uf in stored
            ],
        },
    )


@app.get("/api/ask/jobs/{job_id}")
async def job_status(job_id: str):
    """Poll a job: returns {status, trace, result?, error?}.

    `status` is running | done | error. While running, `trace` carries the live agent steps
    (maps read, files opened) so the UI can show real progress. On done, `result` is the full
    Aletheia output contract; on error, `error` is the message.
    """
    job = _JOBS.get(job_id)
    if job is None:
        return JSONResponse(
            status_code=404,
            content={"error": "unknown or expired job id", "status": "error"},
        )
    body: dict = {
        "status": job.status,
        "trace": [t.model_dump() for t in job.trace],
    }
    if job.status == "done" and job.result is not None:
        body["result"] = job.result.model_dump()
    elif job.status == "error":
        body["error"] = job.error or "agent run failed"
    return JSONResponse(status_code=200, content=body)
