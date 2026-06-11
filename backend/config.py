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

# ── Live-upload filesystem isolation (defense-in-depth, not hook-dependent) ──
# The persistent upload store lives OUTSIDE the agent's cwd (PROJECT_ROOT/=/app on Fly),
# so the agent's reachable /app tree contains NO session dirs at all — a cross-session
# absolute Read like `/app/uploads/<OTHER>` simply does not resolve, regardless of whether
# the SDK honors the PreToolUse deny. Each ask materializes ONLY the current session's files
# into a fresh per-request RUN dir under the cwd; that run dir is the only uploads view the
# agent ever sees, and it's pruned after the run. Override with UPLOAD_STORE_DIR.
UPLOAD_STORE_DIR = Path(
    os.environ.get("UPLOAD_STORE_DIR", str(Path.home() / ".aletheia-upload-store"))
).resolve()
# Per-request isolated run dirs live here, UNDER the agent cwd (so the agent can reach the
# current run by a relative path) but each holds exactly one session's files — never a sibling.
UPLOAD_RUN_DIR = (PROJECT_ROOT / ".runs").resolve()

# Default model: capable + cost-reasonable. Cheap sub-steps can override.
MODEL = os.environ.get("AGENT_MODEL", "claude-haiku-4-5")

# Model for the LIVE-UPLOAD path specifically. Navigating ARBITRARY uploaded data (unknown
# columns, an unfamiliar contract) is harder than the known committed corpus, and Haiku proved
# unreliable on it — it repeatedly cited uploaded-CSV rows OFF BY ONE (counting the header),
# pointing citations at the wrong row, while Sonnet produced the exact golden (rows 2/3/4/7,
# $18,965.50, §4.3#p3). So the upload path defaults to Sonnet; the committed-corpus path stays on
# MODEL (Haiku, for cost). Override with UPLOAD_MODEL. Decided empirically per 01-design's model note.
UPLOAD_MODEL = os.environ.get("UPLOAD_MODEL", "claude-sonnet-4-6")

# Committed-corpus retrieval skill variant. "full" = kb-retriever (thorough nav; reads the
# processing references in full). "lean" = kb-retriever-lean (recipe inlined, ~half the
# per-question prompt, SAME honesty + citation contract). Default stays "full" until the lean
# variant is answer-validated against the goldens; the ask API's optional `skill` field overrides
# per run (that's what the UI toggle sends). Only the committed-corpus path uses a skill — the
# upload path runs its own self-contained prompt.
KB_SKILLS = {"full": "kb-retriever", "lean": "kb-retriever-lean"}


def resolve_kb_skill(variant: str | None) -> str:
    """Map a skill variant ("full"/"lean") to its `.claude/skills` directory name. Falls back to
    the KB_SKILL env default, then "full". Unknown/empty/garbage input never crashes a run."""
    key = (variant or os.environ.get("KB_SKILL") or "full").strip().lower()
    return KB_SKILLS.get(key, KB_SKILLS["full"])


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
