"""Runtime configuration for the agentic backend.

The Anthropic key is read from the project `.env` (gitignored) or the process
environment. It is NEVER hardcoded and NEVER logged.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# Project root is the directory above backend/. The agent runs with this as its
# cwd so the kb-retriever skill resolves `knowledge/` and `.claude/skills/`.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

load_dotenv(PROJECT_ROOT / ".env")

KB_PATH = PROJECT_ROOT / "knowledge"

# Default model: capable + cost-reasonable. Cheap sub-steps can override.
MODEL = os.environ.get("AGENT_MODEL", "claude-haiku-4-5")

# Model for the LIVE-UPLOAD path specifically. Navigating ARBITRARY uploaded data (unknown
# columns, an unfamiliar contract) is harder than the known committed corpus, and Haiku proved
# unreliable on it — it repeatedly cited uploaded-CSV rows OFF BY ONE (counting the header),
# pointing citations at the wrong row, while Sonnet produced the exact golden (rows 2/3/4/7,
# $18,965.50, §4.3#p3). So the upload path defaults to Sonnet; the committed-corpus path stays on
# MODEL (Haiku, for cost). Override with UPLOAD_MODEL. Decided empirically per 01-design's model note.
UPLOAD_MODEL = os.environ.get("UPLOAD_MODEL", "claude-sonnet-4-6")

# Hard ceiling on agent turns so a runaway loop can't bleed cost.
MAX_TURNS = int(os.environ.get("AGENT_MAX_TURNS", "40"))

# Public-surface input guards (the endpoint is internet-exposed). A question
# longer than this is rejected before an agent run is spent; the per-IP request
# rate is capped in main.py. Tuned generously enough for the longest real
# business question (the bilingual Carter / multi-clause contract prompts).
MAX_QUESTION_CHARS = int(os.environ.get("MAX_QUESTION_CHARS", "600"))

# Simple in-process rate limit: max questions per IP per rolling window.
RATE_LIMIT_MAX = int(os.environ.get("RATE_LIMIT_MAX", "20"))
RATE_LIMIT_WINDOW_SEC = int(os.environ.get("RATE_LIMIT_WINDOW_SEC", "60"))

# Async-job store: how long a FINISHED job (done/error) is retained for polling
# before it's pruned. Generous enough that a slow poller still reads its result,
# short enough that the in-process dict stays bounded on the demo surface.
JOB_TTL_SEC = int(os.environ.get("JOB_TTL_SEC", "900"))  # 15 min

# ── Live-upload store (the per-session uploads root the agent reads alongside
# knowledge/). Limits are enforced AT UPLOAD, before an agent run is spent, so a
# wrong-type / oversize file is rejected cheaply. Demo-scale + controlled exposure
# (just the client): generous but bounded; not public-abuse hardening.
UPLOAD_MAX_FILE_BYTES = int(os.environ.get("UPLOAD_MAX_FILE_BYTES", str(10 * 1024 * 1024)))  # 10 MB/file
UPLOAD_MAX_SESSION_BYTES = int(
    os.environ.get("UPLOAD_MAX_SESSION_BYTES", str(25 * 1024 * 1024))
)  # 25 MB total per session
UPLOAD_MAX_FILES = int(os.environ.get("UPLOAD_MAX_FILES", "10"))  # files per session
# How long a session's uploads are retained before pruning (dir + registry). Ephemeral, like the
# job store — one client's uploaded data isn't kept indefinitely.
UPLOAD_TTL_SEC = int(os.environ.get("UPLOAD_TTL_SEC", "3600"))  # 60 min


def anthropic_key_present() -> bool:
    """True iff an Anthropic key is configured. Never returns the key itself."""
    return bool(os.environ.get("ANTHROPIC_API_KEY"))
