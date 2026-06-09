# Environment & ops

## Env vars

| Var | What | Self-serve? |
|---|---|---|
| `ANTHROPIC_API_KEY` | Anthropic key — powers the Claude Agent SDK retrieval agent. | Set in `.env` (gitignored) and as a Vercel/host env var. **Never commit.** |
| `AGENT_MODEL` | Default agent model (`claude-sonnet-4-6`). `claude-haiku-4-5` is used for cheap sub-steps (the eval LLM-judge). | Optional |
| `AGENT_MAX_TURNS` | Hard ceiling on agent turns (runaway-cost guard, default 40). | Optional |
| `AGENT_BACKEND_URL` | The URL the Next.js `/api/ask` route proxies to (the Python FastAPI agent backend). Defaults to `http://127.0.0.1:8000`. | Set to the deployed backend URL in production. |
| `ASSISTANT_TODAY` | Anchors date-relative answers (e.g. "expire in 90 days") to a fixed date so the mock-data demo is deterministic. Set to `2026-06-09`. | Optional |

All variable **names + placeholders** live in [`../../.env.example`](../../.env.example) (committed). Real values live **only** in `.env` (gitignored) and the host env.

> 🚨 **Secrets hygiene.** `.gitignore` excludes every `.env*` except `.env.example`. Never commit, print, or hardcode a key. If a key is ever exposed, rotate it.

## Local run

Three pieces: the Python agent backend, the Next.js frontend, and the knowledge tree (already in the repo). There is **no index build** — the `data_structure.md` maps ARE the index.

```bash
# 1. Python backend (the agent) — needs pdftotext (poppler-utils) on PATH
python -m venv .venv && .venv/bin/pip install -r backend/requirements.txt
cp .env.example .env              # then fill in the real ANTHROPIC_API_KEY
.venv/bin/python -m uvicorn backend.main:app --port 8000

# 2. Frontend (separate terminal)
npm install
npm run dev                       # http://localhost:3000  (proxies /api/ask → :8000)
```

## Deploy (Vercel + the Python backend)

The Next.js frontend deploys to Vercel; the Python FastAPI agent backend needs a Python host (a Vercel Python function, or a separate service that `AGENT_BACKEND_URL` points at). `pdftotext` (poppler-utils) must be available wherever the backend runs.

```bash
vercel env add ANTHROPIC_API_KEY  # + AGENT_BACKEND_URL (production)
vercel --prod
```

Verify the deployment is **READY** (`vercel ls` / `vercel inspect <url>`), not merely pushed, then run the post-deploy prod-verify runbook in [`../features/agentic-knowledge-assistant/03-tests.md`](../features/agentic-knowledge-assistant/03-tests.md) §Prod-verify (G-1…G-4 + Hebrew + citation-chip) against the live URL.

## Access / auth matrix
| Platform | How access works | Agent self-serve? |
|---|---|---|
| GitHub (`gh`) | token | ✅ authed as `qufeiz` |
| Vercel | token | ✅ authed as `qufeiz` |
| Anthropic | API key in env | ✅ if `.env` set |
