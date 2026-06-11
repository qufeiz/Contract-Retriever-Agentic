"""Keyless unit tests for the lean<->full retrieval-skill toggle selection.

These prove the toggle's MECHANISM (variant -> skill dir, safe fallback, both skills present on
disk) WITHOUT any agent run. The answer-QUALITY of the lean skill (does it still produce the
goldens?) is validated separately, live, against the eval set — that needs a real agent turn.
"""
from backend.config import KB_SKILLS, PROJECT_ROOT, resolve_kb_skill


def test_full_and_lean_map_to_their_skill_dirs():
    assert resolve_kb_skill("full") == "kb-retriever"
    assert resolve_kb_skill("lean") == "kb-retriever-lean"


def test_case_insensitive_and_trimmed():
    assert resolve_kb_skill("LEAN") == "kb-retriever-lean"
    assert resolve_kb_skill("  Full ") == "kb-retriever"


def test_unknown_empty_and_none_fall_back_to_full(monkeypatch):
    monkeypatch.delenv("KB_SKILL", raising=False)
    assert resolve_kb_skill(None) == "kb-retriever"
    assert resolve_kb_skill("") == "kb-retriever"
    assert resolve_kb_skill("garbage") == "kb-retriever"


def test_env_default_used_when_variant_absent(monkeypatch):
    monkeypatch.setenv("KB_SKILL", "lean")
    assert resolve_kb_skill(None) == "kb-retriever-lean"
    # an explicit variant still overrides the env default
    assert resolve_kb_skill("full") == "kb-retriever"


def test_both_skill_variants_exist_on_disk():
    # the toggle is meaningless if a variant points at a skill dir that isn't there
    for name in KB_SKILLS.values():
        assert (PROJECT_ROOT / ".claude" / "skills" / name / "SKILL.md").exists(), name
