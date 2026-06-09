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
MODEL = os.environ.get("AGENT_MODEL", "claude-sonnet-4-6")

# Hard ceiling on agent turns so a runaway loop can't bleed cost.
MAX_TURNS = int(os.environ.get("AGENT_MAX_TURNS", "40"))


def anthropic_key_present() -> bool:
    """True iff an Anthropic key is configured. Never returns the key itself."""
    return bool(os.environ.get("ANTHROPIC_API_KEY"))
