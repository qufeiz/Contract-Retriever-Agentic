"""Integration tests for the /api/uploads endpoint + session_id threading (backend/main.py).

Uses FastAPI's TestClient — no agent run, no credits spent. Proves the endpoint stores the
files and returns the {session_id, files} contract, rejects bad uploads with a 4xx, and that a
session_id submitted on /api/ask reaches answer_question (so the agent is scoped to the session).
"""
import pytest
from fastapi.testclient import TestClient

from backend import main, uploads

client = TestClient(main.app)

FIXTURES = uploads.PROJECT_ROOT / "docs" / "features" / "live-upload" / "fixtures"
CSV_BYTES = (FIXTURES / "customers.csv").read_bytes()
PDF_BYTES = (FIXTURES / "service-agreement.pdf").read_bytes()


@pytest.fixture(autouse=True)
def _key_present(monkeypatch):
    # The upload/ask guards require a key to be PRESENT (they never run the agent here).
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-used")
    yield


def _cleanup(session_id: str):
    uploads.prune_session_now(session_id)


def test_upload_two_fixtures_returns_session_and_files():
    r = client.post(
        "/api/uploads",
        files=[
            ("files", ("customers.csv", CSV_BYTES, "text/csv")),
            ("files", ("service-agreement.pdf", PDF_BYTES, "application/pdf")),
        ],
    )
    assert r.status_code == 201, r.text
    body = r.json()
    sid = body["session_id"]
    try:
        assert len(sid) >= 24
        names = {f["name"]: f for f in body["files"]}
        assert names["customers.csv"]["rows"] == 10
        assert names["customers.csv"]["columns"][0] == "customer"
        assert names["service-agreement.pdf"]["pages"] == 4
        # the session is live and its dir holds the pre-extracted txt + the map
        sess = uploads.get_session(sid)
        assert (sess.dir / "service-agreement.txt").exists()
        assert (sess.dir / "data_structure.md").exists()
    finally:
        _cleanup(sid)


def test_upload_rejects_wrong_type():
    r = client.post("/api/uploads", files=[("files", ("evil.exe", b"MZ", "application/octet-stream"))])
    assert r.status_code == 400
    assert "unsupported file type" in r.json()["error"]


def test_upload_rejects_empty():
    r = client.post("/api/uploads", files=[("files", ("empty.csv", b"", "text/csv"))])
    assert r.status_code == 400


def test_upload_rejects_corrupt_pdf_and_discards_session():
    before = set(uploads._SESSIONS.keys())
    r = client.post("/api/uploads", files=[("files", ("broken.pdf", b"%PDF junk", "application/pdf"))])
    assert r.status_code == 400
    # the half-built session was discarded (no leak of partial sessions)
    assert set(uploads._SESSIONS.keys()) == before


def test_session_id_threads_into_answer_question(monkeypatch):
    """A session_id on /api/ask must reach answer_question — that is what scopes the run to the
    session's uploads. We stub answer_question to capture the kwarg (no agent run)."""
    # First create a real session so the id is valid.
    up = client.post("/api/uploads", files=[("files", ("customers.csv", CSV_BYTES, "text/csv"))])
    sid = up.json()["session_id"]
    captured = {}

    async def _fake_answer(question, on_trace=None, session_id=None, model=None, skill=None):
        captured["question"] = question
        captured["session_id"] = session_id
        captured["skill"] = skill
        from backend.models import AskResponse, Validation

        return AskResponse(question=question, answer="ok", validation=Validation(ok=True))

    monkeypatch.setattr(main, "answer_question", _fake_answer)
    try:
        r = client.post("/api/ask", json={"question": "anything", "session_id": sid, "skill": "lean"})
        assert r.status_code == 200, r.text
        assert captured["session_id"] == sid  # threaded through
        assert captured["skill"] == "lean"  # the UI toggle threads through too
    finally:
        _cleanup(sid)


def test_ask_without_session_id_passes_none(monkeypatch):
    captured = {}

    async def _fake_answer(question, on_trace=None, session_id=None, model=None, skill=None):
        captured["session_id"] = session_id
        captured["skill"] = skill
        from backend.models import AskResponse, Validation

        return AskResponse(question=question, answer="ok", validation=Validation(ok=True))

    monkeypatch.setattr(main, "answer_question", _fake_answer)
    r = client.post("/api/ask", json={"question": "no uploads"})
    assert r.status_code == 200, r.text
    assert captured["session_id"] is None  # committed-corpus path, unchanged
    assert captured["skill"] is None  # no toggle in body → None (server KB_SKILL default applies)
