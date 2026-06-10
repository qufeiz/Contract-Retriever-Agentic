"""Unit tests for the async-job transport (backend/main.py).

The async-job path (submit → poll) is what keeps the heaviest golden query from
504-ing on Vercel's 300s function cap: the long agent run lives in a background
task on Fly, and the frontend polls short status requests. These tests lock the
job lifecycle — submit returns a job id fast, polling streams the live trace, and
the final poll carries the full Aletheia contract — WITHOUT spending an agent run
(answer_question is stubbed). The real agent content is proven by the eval harness.
"""
import asyncio

import httpx
from httpx import ASGITransport

from backend import main
from backend.models import AskResponse, EvidenceItem, TraceStep, Validation


def _stub_response(question: str) -> AskResponse:
    return AskResponse(
        question=question,
        answer="38 contracts expire [F:school-operations/contracts.csv#expiring-90d].",
        evidence=[
            EvidenceItem(
                file="school-operations/contracts.csv",
                loc="expiring-90d",
                snippet="pandas filter End Date in [2026-06-09, 2026-09-07] -> 38 rows",
            )
        ],
        trace=[
            TraceStep(kind="map", detail="read map knowledge/data_structure.md"),
            TraceStep(kind="open", detail="pandas: read contracts.csv"),
        ],
        validation=Validation(ok=True, reasons=[]),
    )


async def _drive(monkeypatched_answer):
    """Submit a job, poll until done, return (submit_status, final_body)."""
    main._JOBS.clear()
    transport = ASGITransport(app=main.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        sub = await client.post("/api/ask/jobs", json={"question": "What expires?"})
        assert sub.status_code == 202, sub.text
        job_id = sub.json()["job_id"]
        # Poll until the background task finishes (bounded so a hang fails the test).
        for _ in range(200):
            poll = await client.get(f"/api/ask/jobs/{job_id}")
            body = poll.json()
            if body["status"] in ("done", "error"):
                return sub.json(), body
            await asyncio.sleep(0.02)
        raise AssertionError("job never finished")


def test_submit_returns_job_id_then_poll_yields_full_contract(monkeypatch):
    async def fake_answer(question, on_trace=None, session_id=None, model=None):
        # emit a couple of live trace steps (the streaming contract)
        if on_trace:
            await on_trace(TraceStep(kind="map", detail="read root map"))
        return _stub_response(question)

    monkeypatch.setattr(main, "answer_question", fake_answer)
    monkeypatch.setattr(main, "anthropic_key_present", lambda: True)

    submit_body, final = asyncio.run(_drive(fake_answer))
    assert submit_body["status"] == "running"
    assert final["status"] == "done"
    # the final poll carries the full Aletheia contract the UI consumes
    assert "38 contracts" in final["result"]["answer"]
    assert final["result"]["validation"]["ok"] is True
    assert any(t["kind"] == "open" for t in final["result"]["trace"])


def test_job_error_is_surfaced_not_swallowed(monkeypatch):
    async def boom(question, on_trace=None, session_id=None, model=None):
        raise RuntimeError("agent exploded")

    monkeypatch.setattr(main, "answer_question", boom)
    monkeypatch.setattr(main, "anthropic_key_present", lambda: True)

    _submit, final = asyncio.run(_drive(boom))
    assert final["status"] == "error"
    assert "agent exploded" in final["error"]


def test_unknown_job_id_is_404(monkeypatch):
    monkeypatch.setattr(main, "anthropic_key_present", lambda: True)

    async def _go():
        main._JOBS.clear()
        transport = ASGITransport(app=main.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get("/api/ask/jobs/does-not-exist")

    resp = asyncio.run(_go())
    assert resp.status_code == 404
    assert resp.json()["status"] == "error"


def test_submit_413_on_overlong_question(monkeypatch):
    monkeypatch.setattr(main, "anthropic_key_present", lambda: True)

    async def _go():
        main._JOBS.clear()
        transport = ASGITransport(app=main.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post(
                "/api/ask/jobs", json={"question": "x" * (main.MAX_QUESTION_CHARS + 1)}
            )

    resp = asyncio.run(_go())
    assert resp.status_code == 413
