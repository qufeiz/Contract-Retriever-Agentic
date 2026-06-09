"""FastAPI app — the agentic /api/ask endpoint.

The Next.js frontend's /api/ask route proxies to this backend. One question in, the Aletheia
output contract out. Returns 503 if no Anthropic key is configured (never fakes an answer).
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.agent import answer_question
from backend.config import anthropic_key_present
from backend.models import AskRequest, AskResponse

app = FastAPI(title="Aletheia Agentic API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type"],
)


@app.get("/health")
async def health() -> dict:
    return {"ok": True, "key_configured": anthropic_key_present()}


@app.post("/api/ask", response_model=AskResponse)
async def ask(req: AskRequest):
    if not anthropic_key_present():
        return JSONResponse(
            status_code=503,
            content={"error": "ANTHROPIC_API_KEY is not configured on the server."},
        )
    question = (req.question or "").strip()
    if not question:
        return JSONResponse(status_code=400, content={"error": "question is required"})
    try:
        result = await answer_question(question)
        return result
    except Exception as e:  # surface real failures, never fabricate a pass
        return JSONResponse(status_code=500, content={"error": str(e)})
