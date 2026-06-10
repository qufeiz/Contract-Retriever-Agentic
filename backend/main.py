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
"""
import asyncio
import os
import time
import uuid
from collections import deque
from dataclasses import dataclass, field

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.agent import answer_question
from backend.config import (
    JOB_TTL_SEC,
    MAX_QUESTION_CHARS,
    RATE_LIMIT_MAX,
    RATE_LIMIT_WINDOW_SEC,
    anthropic_key_present,
)
from backend.models import AskRequest, AskResponse, TraceStep

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


async def _run_job(job_id: str, question: str) -> None:
    """Background task: run the agent, streaming trace into the job, then store the result."""
    job = _JOBS[job_id]

    async def _on_trace(step: TraceStep) -> None:
        job.trace.append(step)

    try:
        resp = await answer_question(question, on_trace=_on_trace)
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
    return {"ok": True, "key_configured": anthropic_key_present()}


@app.post("/api/ask", response_model=AskResponse)
async def ask(req: AskRequest, request: Request):
    """Synchronous: run the agent and block until the answer (direct-to-Fly / back-compat)."""
    question = (req.question or "").strip()
    guard = _guard_question(question, request)
    if guard is not None:
        return guard
    try:
        result = await answer_question(question)
        return result
    except ValueError as e:  # input guard tripped inside the agent
        return JSONResponse(status_code=400, content={"error": str(e)})
    except Exception as e:  # surface real failures, never fabricate a pass
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/ask/jobs")
async def submit_job(req: AskRequest, request: Request):
    """Async: create a job, start the agent in the background, return the job id immediately.

    Returns fast (well under any serverless cap). The caller polls GET /api/ask/jobs/{id}.
    """
    question = (req.question or "").strip()
    guard = _guard_question(question, request)
    if guard is not None:
        return guard
    _prune_jobs()
    job_id = uuid.uuid4().hex
    _JOBS[job_id] = Job()
    # Fire-and-forget; the task streams trace into the job and stores the result.
    asyncio.create_task(_run_job(job_id, question))
    return JSONResponse(status_code=202, content={"job_id": job_id, "status": "running"})


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
