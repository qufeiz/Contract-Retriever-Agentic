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

> **Seal-decayed (archived):** `sqlite-on-serverless` (the v1 "bundled SQLite won't open on Vercel serverless" gotcha) **no longer applies** — the agentic build has no SQLite/bundled index (the agent reads `knowledge/` files directly). Kept for provenance at [`../archive/sqlite-on-serverless.md`](../archive/sqlite-on-serverless.md).
