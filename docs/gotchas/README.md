# Gotchas — sealed postmortems

This is the **append-driven** home for footguns: a trap that cost real time, written up so the next agent doesn't pay for it twice. **Lead with the lesson, not the narrative.** At bootstrap this folder has no gotcha files yet — that's correct; the first real miss creates the first one.

## The "seal" convention (read before writing one)

A fix is documented as *solved* only when it is **tested AND user-confirmed**. Every gotcha file opens with a **Confirmation status** line:

```markdown
> **Confirmation status: SEALED (YYYY-MM-DD).** <what's verified> — tested via <regression test>
> AND <who> confirmed on <what environment>. Root cause closed.
> (If not sealed: list what's verified vs. open, and "re-open if X recurs".)
```

- **A wrong "it's fixed" doc is worse than none** — the next agent trusts it. If you can't seal it yet, write it *not sealed* (verified vs. open).
- **Seal-decay:** a seal certifies correctness *at write time, not forever*. Treat an old gotcha as a hypothesis — if it names a file/flag/behavior, confirm that still exists before relying on it; if the bug recurs, flip the status back and re-open.
- **Link the gotcha ⇄ the enforcement both ways.** The gotcha names where it's now caught (a CI lint, a unit test, a self-check); the check points back to the why (this file). A gotcha with no enforcement link is a flag: should the lesson be *enforced*, not just remembered?

## Index
| Gotcha | Lesson |
|---|---|
| [committed-debug-stub-broke-prod.md](committed-debug-stub-broke-prod.md) | A removable-handler probe (`FORCED:` always-fail) got committed + deployed and forced every answer to "Rejected". Never commit a probe; verify the suite GREEN against the FRESH prod URL, not a stale build. Now blocked by a `doc-lint` forbidden-marker scan. |
| [agent-final-json-malformed.md](agent-final-json-malformed.md) | The agent's final JSON breaks on large/multi-line answers (prose prefix + raw newlines inside strings) — parse defensively (balanced-brace extraction + escape control chars in strings), don't trust "JSON only". Caught by `backend/tests/test_extract_json.py` + the real-G1 eval fixture. |
| [test-command-must-match-ci.md](test-command-must-match-ci.md) | A test green locally can fail CI because CI runs the `package.json` script, not your pytest invocation: `cd backend && pytest` broke `from backend.…` imports. Verify with the EXACT npm script (`npm run test:agent`), run pytest from the repo root, ship `backend/__init__.py`. |
| [public-agent-hardening-hook-not-callback.md](public-agent-hardening-hook-not-callback.md) | To sandbox a public Agent SDK loop the real gate is a **`PreToolUse` hook**, not `can_use_tool` (silently inert on the `query()` path here) and not `allowed_tools` (auto-approves). The hook hard-denies anything outside read-only `knowledge/` ops; verified by blocking a live `/etc/passwd`/key-print injection. Locked by `backend/tests/test_hardening.py`. |
| [agent-error-swallowed-health-green-demo-dead.md](agent-error-swallowed-health-green-demo-dead.md) | An out-of-credit key killed every agent run at CLI startup while `/health` stayed green (it only checks key *presence*). The Agent SDK hides the real reason ("Credit balance is too low") behind a generic "exit code 1"; recover it via the `stderr` callback. Fixes: `answer_question` re-raises the real reason; new `/ready` runs a real agent turn. "Declare live" gates on a real golden + `/ready:true`, not `/health`+screenshots. Locked by `backend/tests/test_error_surfacing.py`. |
| [upload-scope-substring-check-leaked-other-sessions.md](upload-scope-substring-check-leaked-other-sessions.md) | (Necessary-but-INSUFFICIENT — see next row.) The Bash scope check used a substring ("does the command MENTION an allowed root?"), so a command naming its OWN session AND reading ANOTHER's was allowed. Fixed with per-path scoping — but that's a HOOK-level fix, and the hook isn't enforced live (next row), so a raw `Read` still leaked. Locked by `test_hardening.py::test_bash_cannot_read_another_session_even_if_it_names_its_own`. |
| [live-sdk-ignores-pretooluse-deny-use-constrained-tools.md](live-sdk-ignores-pretooluse-deny-use-constrained-tools.md) | The deployed Fly SDK does NOT honor a `PreToolUse` "deny" for a `Read` (cross-session `Read /app/uploads/<victim>` leaked LIVE) while the SAME code denies LOCALLY — a local↔live divergence; a local hook test is a false green about prod. Durable fix: the UPLOAD agent gets NO raw Read/Bash/Glob/Grep — only scoped data-reader MCP tools that take a filename and refuse any absolute/`..`/foreign path → cross-session read impossible BY CONSTRUCTION. (+ store moved outside `/app`, ephemeral per-request run dir.) Locked by `test_upload_tools.py` + the real-SDK `upload_run.py::isolation_gate` run against the LIVE deploy. Footgun: an `@tool` error result uses `is_error` (snake_case), not `isError`, or the result fails to serialize and answers come back empty. Meta-lesson: prefer impossible-by-construction over deny-by-policy; verify the security gate in PRODUCTION. |

> **Seal-decayed (archived):** `sqlite-on-serverless` (the v1 "bundled SQLite won't open on Vercel serverless" gotcha) **no longer applies** — the agentic build has no SQLite/bundled index (the agent reads `knowledge/` files directly). Kept for provenance at [`../archive/sqlite-on-serverless.md`](../archive/sqlite-on-serverless.md).
