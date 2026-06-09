# Verify with the EXACT CI command, not your own pytest invocation

> **Confirmation status: SEALED (2026-06-09).** `npm run test:agent` now runs `python -m pytest
> backend/tests -q` **from the repo root** (was `cd backend && pytest …`, which broke `from backend.
> … import`), and `backend/__init__.py` was added so `backend` is an importable package. Verified by
> running the exact `npm run test:agent` command (15 passed) — the same command CI runs. Re-open if a
> test passes locally but the CI `test:agent` step fails.

## Lesson (read this first)

**A test that passes when you run pytest your way can still fail the CI step, because CI runs the
`package.json` script — not your invocation.** The first push to the new repo went RED on
`test:agent` even though I'd run the tests green locally. Always verify with the **exact npm script
CI executes** (`npm run test:agent`), not `pytest backend/tests` from wherever you happen to be.

## What happened

- `package.json` had `"test:agent": "cd backend && python -m pytest tests/test_validate.py -q"`.
- The tests do `from backend.models import EvidenceItem`. With the working directory `cd`'d **into**
  `backend/`, the `backend` package is no longer importable → `ModuleNotFoundError: No module named
  'backend'` → CI exit 2.
- It passed locally only because I ran `.venv/bin/python -m pytest backend/tests/` **from the repo
  root**, where `backend.` resolves. My local command and the CI command differed — the classic
  green-locally / red-in-CI gap.
- Compounding: `backend/__init__.py` was missing, so `backend` was only an implicit namespace package
  (worked from root, fragile elsewhere).

## The fix

- `test:agent` → `python -m pytest backend/tests -q` (run from repo root; also now runs BOTH test
  files, not just `test_validate.py`).
- `eval:agent` → `python -m backend.eval.run` (same reason).
- Added `backend/__init__.py` so `backend` is a real package.

## Enforcement (gotcha ⇄ check)

- CI's `test:agent` step IS the enforcement — it runs the corrected script on every push.
- `verify:release` (the local CI mirror) chains `npm run test:agent`; run THAT before pushing, not a
  hand-rolled pytest command. **Rule: the local pre-push check must be the same command string CI
  runs.**

## META-MISS

The miss slipped because my local check (`pytest` from root) was not the CI check (`npm run
test:agent`). The strengthening: always run the **npm script** as the pre-push gate, so the thing I
verify and the thing CI verifies are byte-identical.
