"""Unit tests for surfacing the REAL agent-CLI failure reason (backend/agent.py).

The Claude Agent SDK collapses any non-zero `claude` CLI exit into a generic
"Command failed with exit code 1 / Check stderr output for details" ProcessError
and discards the actual cause. Once, the deployed key ran out of credit and every
agent run died at CLI startup with that opaque wrapper — `/health` was green
(key present) but the demo was dead. These tests lock the two fixes:

  1. `_real_stderr` distils the captured CLI stderr into the one-glance reason
     (preferring a credit/auth/quota signal line over chatty noise).
  2. `answer_question` re-raises a ProcessError with that real reason attached,
     instead of the SDK's placeholder — so the job/response error field is
     actually actionable ("Credit balance is too low", not "exit code 1").

No agent run is spent: `query` is stubbed to raise the wrapper while feeding the
real stderr through the SDK's per-line callback, exactly as the live CLI does.
"""
import asyncio

import pytest
from claude_agent_sdk import ProcessError

from backend import agent


def test_real_stderr_prefers_the_signal_line():
    lines = [
        "[debug] spawning claude\n",
        "Some chatty version notice\n",
        "Credit balance is too low\n",
    ]
    assert agent._real_stderr(lines) == "Credit balance is too low"


def test_real_stderr_falls_back_to_last_nonempty_line():
    lines = ["   \n", "warming up\n", "unexpected token near line 4\n", "\n"]
    assert agent._real_stderr(lines) == "unexpected token near line 4"


def test_real_stderr_empty_is_empty_string():
    assert agent._real_stderr([]) == ""
    assert agent._real_stderr(["\n", "   "]) == ""


def _fake_query_that_dies(stderr_text: str, *, bare: bool = False):
    """A drop-in for claude_agent_sdk.query: feed any stderr through the options.stderr
    callback (as the live CLI does), then raise the way the SDK actually does.

    The SDK raises a dead CLI INCONSISTENTLY: sometimes a typed ProcessError, sometimes a
    bare Exception("Command failed with exit code 1 … Check stderr output for details") from
    its message reader (the path that actually fired in prod). `bare=True` reproduces the latter."""

    async def _gen(*, prompt, options):
        if options.stderr is not None:
            for line in stderr_text.splitlines():
                options.stderr(line)
        if bare:
            raise Exception(
                "Command failed with exit code 1 (exit code: 1)\n"
                "Error output: Check stderr output for details"
            )
        raise ProcessError(
            "Command failed with exit code 1",
            exit_code=1,
            stderr="Check stderr output for details",
        )
        yield  # make this an async generator

    return _gen


def test_answer_question_surfaces_credit_reason(monkeypatch):
    monkeypatch.setattr(agent, "query", _fake_query_that_dies("Credit balance is too low"))

    with pytest.raises(RuntimeError) as ei:
        asyncio.run(agent.answer_question("What contracts expire soon?"))

    msg = str(ei.value)
    # the REAL reason is surfaced — not the SDK's opaque placeholder
    assert "Credit balance is too low" in msg
    assert "Check stderr output for details" not in msg


def test_answer_question_surfaces_auth_reason(monkeypatch):
    monkeypatch.setattr(
        agent, "query", _fake_query_that_dies("noise\n401 unauthorized: invalid api key")
    )

    with pytest.raises(RuntimeError) as ei:
        asyncio.run(agent.answer_question("anything"))

    assert "401 unauthorized" in str(ei.value)


def test_answer_question_recovers_from_bare_wrapper_exception(monkeypatch):
    # The path that actually fired in prod: the SDK raises a BARE Exception (not ProcessError)
    # carrying only the opaque wrapper, and the real reason is on stdout. We must still recover it.
    monkeypatch.setattr(agent, "query", _fake_query_that_dies("", bare=True))

    async def fake_probe():
        return "Credit balance is too low"

    monkeypatch.setattr(agent, "_probe_cli_failure_reason", fake_probe)

    with pytest.raises(RuntimeError) as ei:
        asyncio.run(agent.answer_question("anything"))

    msg = str(ei.value)
    assert "Credit balance is too low" in msg
    assert "Check stderr output for details" not in msg


def test_input_guard_error_is_not_wrapped(monkeypatch):
    # A ValueError from the input guard is intentional and must propagate as-is (not become a
    # generic "agent CLI failed"). No query call should happen.
    with pytest.raises(ValueError):
        asyncio.run(agent.answer_question("   "))  # empty after strip


def test_answer_question_falls_back_to_stdout_probe_when_stderr_empty(monkeypatch):
    # The real-world case: the credit line goes to the CLI's STDOUT (not stderr), which the SDK
    # ate — so the per-line stderr callback captures NOTHING and we must fall back to a direct
    # CLI probe that reads stdout.
    monkeypatch.setattr(agent, "query", _fake_query_that_dies(""))  # no stderr at all

    async def fake_probe():
        return "Credit balance is too low"

    monkeypatch.setattr(agent, "_probe_cli_failure_reason", fake_probe)

    with pytest.raises(RuntimeError) as ei:
        asyncio.run(agent.answer_question("anything"))

    msg = str(ei.value)
    assert "Credit balance is too low" in msg
    assert "Check stderr output for details" not in msg


def test_probe_agent_ready_reports_real_reason_via_stdout_fallback(monkeypatch):
    monkeypatch.setattr(agent, "query", _fake_query_that_dies(""))  # stderr empty

    async def fake_probe():
        return "Credit balance is too low"

    monkeypatch.setattr(agent, "_probe_cli_failure_reason", fake_probe)

    ready, reason = asyncio.run(agent.probe_agent_ready())
    assert ready is False
    assert reason == "Credit balance is too low"
