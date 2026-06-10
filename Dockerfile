# Aletheia agentic backend — Fly.io container.
#
# The Claude Agent SDK spawns the `claude` CLI and runs multi-minute retrieval
# loops, and the kb-retriever skill shells out to `pdftotext` (poppler) and a
# pandas one-liner — so this needs a REAL container with BOTH Python and Node,
# not a serverless function. We bundle the knowledge/ tree + .claude/skills +
# backend/ and serve the FastAPI app with uvicorn on the Fly internal port 8080.
#
# The ANTHROPIC_API_KEY is NEVER baked in — it is injected at runtime as a Fly
# secret (`fly secrets set ANTHROPIC_API_KEY=...`).

FROM python:3.12-slim

# --- OS deps: poppler (pdftotext) for the PDF path, curl/ca-certs for Node setup,
#     and the Node runtime the `claude` CLI requires. ---
RUN apt-get update && apt-get install -y --no-install-recommends \
        poppler-utils \
        curl \
        ca-certificates \
        gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# --- The Claude Code CLI the Agent SDK drives (pinned for reproducibility). ---
RUN npm install -g @anthropic-ai/claude-code@2.1.170

# --- A non-root app user with a writable HOME (the CLI writes its config there). ---
RUN useradd --create-home --uid 10001 app
ENV HOME=/home/app
WORKDIR /app

# --- Python deps first (layer-cached) ---
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# --- App payload: the backend, the knowledge base, and the skill. The agent runs
#     with /app as cwd, so knowledge/ and .claude/skills/ must resolve from here. ---
COPY backend/ /app/backend/
COPY knowledge/ /app/knowledge/
COPY .claude/ /app/.claude/

# The CLI + SDK write transient state under HOME; make the tree app-owned.
RUN chown -R app:app /app /home/app
USER app

# Fly routes to this internal port; uvicorn binds all interfaces.
ENV PORT=8080
EXPOSE 8080

# Serve the FastAPI app. The hardened agent (read-only PreToolUse hook) is the
# security boundary; the key arrives via the ANTHROPIC_API_KEY secret.
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
