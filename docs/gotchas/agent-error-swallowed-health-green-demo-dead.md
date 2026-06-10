# A green `/health` shipped a dead demo: the Agent SDK swallows the real CLI error ("Credit balance is too low")

> **Confirmation status: PARTIALLY SEALED (2026-06-10).** The two CODE fixes are tested + locked:
> (1) `answer_question` now re-raises the REAL CLI failure reason instead of the SDK's opaque
> wrapper, and (2) a `/ready` probe runs one real agent turn so a dead key can't pass as ready —
> both verified by `backend/tests/test_error_surfacing.py` (5 tests, no agent run spent) and the
> live root cause was confirmed by running `claude -p` directly inside the Fly machine (it printed
> `Credit balance is too low`, which the SDK had hidden behind `exit code 1`). **OPEN until** the
> deployed key is topped up / rotated and ONE real golden + `/ready: true` is observed live — the
> ROOT CAUSE (out-of-credit key) is a user/billing action, not a code change. Re-seal fully once
> `/ready` returns `{ready:true}` and a golden answers end-to-end on the public URL.

## Lesson (read this first)

**A liveness check that only proves a key is *present* will certify a *dead* demo green.** The
deployed `ANTHROPIC_API_KEY` ran out of credit; every agent run then died in ~1.6s at `claude` CLI
startup, before any retrieval — yet `/health` stayed green (`key_configured: true`) and the async
transport still returned 202 + a job id (the transport was fine; the agent it polls was dead). The
build looked live and was not.

**Two compounding traps:**

1. **The Claude Agent SDK swallows the real CLI error.** On a non-zero `claude` exit the SDK raises
   a generic `ProcessError("Command failed with exit code 1 … Check stderr output for details")` and
   **discards the actual reason** — so "out of credit", "401 unauthorized", and "malformed prompt"
   all look identical and tell the operator nothing. The `ProcessError.stderr` field is a placeholder.
   **Worse: the credit/auth message lands on the CLI's STDOUT, not stderr** — verified by running
   `claude -p` directly in the Fly machine: `Credit balance is too low` went to stdout, stderr was
   empty. The SDK consumes stdout as a `--output-format stream-json` message stream, so that plain
   line is unparseable JSON and is **silently dropped**. So the per-line `stderr` callback
   (`ClaudeAgentOptions(stderr=…)`) catches the auth/quota cases that DO use stderr, but the
   out-of-credit case needs a **last-resort fallback: a direct `claude -p` probe that reads stdout**
   (a failing auth/credit call returns instantly and costs nothing — it never reaches the model).
2. **`/health` checked presence, not validity.** `os.environ` having a key says nothing about whether
   that key can complete a call. Health was green while the product was down.

**Fixes (both in this repo):**

- **Surface the real reason.** `backend/agent.py::answer_question` registers a `stderr` collector
  and, on `ProcessError`, re-raises `RuntimeError(f"agent CLI failed (exit {code}): {real_reason}")`.
  `_real_stderr()` distils captured stderr (preferring a credit/auth/quota signal line); when stderr
  is empty (the out-of-credit case), `_probe_cli_failure_reason()` runs one direct `claude -p` and
  reads its **stdout** for the real line. The async job's `error` field and the sync `/api/ask` 500
  now carry the actionable reason.
- **A real readiness probe.** `backend/agent.py::probe_agent_ready` runs ONE minimal no-tool agent
  turn; `GET /ready` returns `200 {ready:true}` only when it completes, else `503 {ready:false,
  reason:"…"}`. **"Declare live" must gate on a real golden completing end-to-end + `/ready:true`,
  not on `/health` + screenshots.** `/health` stays as cheap liveness; `/ready` is the real gate.

**General rule:** when a wrapper library reports a generic failure, find where it captured the
underlying stderr/stdout and surface THAT; and never let a presence check stand in for a real
end-to-end readiness check on an outward-facing demo.

## How it was caught / where it's enforced

- **Live, by the Verifier:** every golden errored in ~1.6s with the opaque wrapper on all 4 domains,
  both transports, both surfaces (Vercel + direct Fly) — a constant fast failure = CLI dies at
  startup. Confirmed the real cause by `flyctl ssh console -a aletheia-agentic -C 'claude -p "say ok"'`
  → printed `Credit balance is too low`.
- **Locked by** `backend/tests/test_error_surfacing.py`: `_real_stderr` picks the signal line; a
  stubbed `query` that raises the SDK wrapper while feeding real stderr proves `answer_question`
  surfaces "Credit balance is too low" / "401 unauthorized" and NOT the placeholder. Runs in CI's
  `test:agent` (no agent run spent).
- **Operational check:** `GET /ready` is the live readiness gate (a real API call; call on deploy /
  before declaring live, not as a high-frequency probe).

Related: [committed-debug-stub-broke-prod.md](committed-debug-stub-broke-prod.md) (also "verify the
FRESH prod URL really works, don't trust a green-looking check") and
[public-agent-hardening-hook-not-callback.md](public-agent-hardening-hook-not-callback.md) (same
theme: prove the boundary/agent actually fires on a real run, don't assume from an API existing).
