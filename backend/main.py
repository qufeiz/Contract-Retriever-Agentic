"""FastAPI app — the agentic /api/ask endpoint.

The Next.js frontend's /api/ask route proxies to this backend. One question in, the Aletheia
output contract out. Returns 503 if no Anthropic key is configured (never fakes an answer).

Public-surface guards (the endpoint is internet-exposed): a length cap on the question (413)
and a simple per-IP rolling rate limit (429), so a hijacked/abusive caller can't bleed agent
runs. The deeper RCE/prompt-injection defense — the agent's read-only allow-list — lives in
backend/agent.py (`_can_use_tool`).
"""
import os
import time
from collections import deque

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.agent import answer_question
from backend.config import (
    MAX_QUESTION_CHARS,
    RATE_LIMIT_MAX,
    RATE_LIMIT_WINDOW_SEC,
    anthropic_key_present,
)
from backend.models import AskRequest, AskResponse

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


@app.get("/health")
async def health() -> dict:
    return {"ok": True, "key_configured": anthropic_key_present()}


@app.post("/api/ask", response_model=AskResponse)
async def ask(req: AskRequest, request: Request):
    if not anthropic_key_present():
        return JSONResponse(
            status_code=503,
            content={"error": "ANTHROPIC_API_KEY is not configured on the server."},
        )
    client_ip = (request.client.host if request.client else "unknown")
    if _rate_limited(client_ip):
        return JSONResponse(
            status_code=429,
            content={"error": "Too many requests — please slow down and retry shortly."},
        )
    question = (req.question or "").strip()
    if not question:
        return JSONResponse(status_code=400, content={"error": "question is required"})
    if len(question) > MAX_QUESTION_CHARS:
        return JSONResponse(
            status_code=413,
            content={"error": f"question too long (max {MAX_QUESTION_CHARS} characters)."},
        )
    try:
        result = await answer_question(question)
        return result
    except ValueError as e:  # input guard tripped inside the agent
        return JSONResponse(status_code=400, content={"error": str(e)})
    except Exception as e:  # surface real failures, never fabricate a pass
        return JSONResponse(status_code=500, content={"error": str(e)})
