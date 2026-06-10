"""Unit tests for the constrained upload-path toolset (backend/upload_tools.py).

The upload-path agent has NO raw Read/Bash/Glob/Grep — only these scoped data-reader tools, each of
which resolves a FILENAME against ONLY the allowed roots (the per-request run dir + knowledge/) and
REFUSES any absolute path, `..` traversal, or foreign-session path. That makes a cross-session read
impossible BY CONSTRUCTION — no hook to bypass. These tests lock that boundary as a permanent,
removable-handler-proof gate: widen `_resolve` to accept an absolute path and they go red.
"""
import asyncio
from pathlib import Path

import pytest

from backend import upload_tools as ut
from backend.config import KB_PATH
from backend.uploads import (
    create_session,
    finalize_session_map,
    materialize_run,
    prune_session_now,
    store_upload,
)

FIXTURES = Path(__file__).resolve().parents[2] / "docs" / "features" / "live-upload" / "fixtures"


def _call(tool, **kwargs):
    return asyncio.run(tool.handler(kwargs))


def _is_refused(result) -> bool:
    return bool(result.get("is_error")) and "REFUSED" in result["content"][0]["text"]


@pytest.fixture
def two_sessions():
    """Session V (victim, holds a secret) + session B (attacker), with B's run dir bound as scope."""
    sV = create_session()
    store_upload(sV, "secret.csv", b"customer,secret_token\nAcme,SECRET_XYZ\n")
    finalize_session_map(sV)
    sB = create_session()
    store_upload(sB, "customers.csv", (FIXTURES / "customers.csv").read_bytes())
    finalize_session_map(sB)
    run = materialize_run(sB.session_id)
    token = ut.set_tool_roots(run.path, KB_PATH)
    try:
        yield sV, sB, run
    finally:
        ut.reset_tool_roots(token)
        run.__exit__(None, None, None)
        prune_session_now(sV.session_id)
        prune_session_now(sB.session_id)


def test_reads_own_session_file(two_sessions):
    _sV, _sB, _run = two_sessions
    r = _call(ut.read_csv, name="customers.csv")
    assert not r.get("is_error")
    assert "#row-1" in r["content"][0]["text"]  # numbered rows for citation


def test_kb_prefix_allowed(two_sessions):
    r = _call(ut.read_text, name="kb/data_structure.md")
    assert not r.get("is_error")


def test_absolute_victim_store_path_refused(two_sessions):
    sV, _sB, _run = two_sessions
    victim_abs = str((sV.dir / "secret.csv").resolve())
    r = _call(ut.read_csv, name=victim_abs)
    assert _is_refused(r)
    # the secret must NOT have been returned
    assert "SECRET_XYZ" not in r["content"][0]["text"]


def test_traversal_and_absolute_refused(two_sessions):
    sV, _sB, _run = two_sessions
    assert _is_refused(_call(ut.read_text, name=f"../{sV.session_id}/secret.csv"))
    assert _is_refused(_call(ut.read_text, name="/etc/passwd"))
    assert _is_refused(_call(ut.read_text, name="/app/uploads/anything/secret.csv"))
    assert _is_refused(_call(ut.read_text, name="~/.aletheia-upload-store/x/secret.csv"))
    assert _is_refused(_call(ut.read_csv, name="../../backend/config.py"))


def test_list_files_shows_only_own_session(two_sessions):
    sV, _sB, _run = two_sessions
    r = _call(ut.list_files)
    txt = r["content"][0]["text"]
    assert "customers.csv" in txt  # B's own file
    assert sV.session_id not in txt  # the victim's session id never appears
    assert "secret.csv" not in txt  # the victim's file never appears


def test_grep_scoped_to_available_files(two_sessions):
    sV, _sB, _run = two_sessions
    r = _call(ut.grep_files, pattern="SECRET_XYZ")
    # the victim's secret is NOT in scope, so grep can't find it
    assert "SECRET_XYZ" not in r["content"][0]["text"]


def test_no_roots_means_no_access():
    # With no run bound (committed-corpus path), the upload tools grant nothing.
    r = _call(ut.read_csv, name="anything.csv")
    assert _is_refused(r)
