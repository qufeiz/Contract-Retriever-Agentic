# A per-session read-scope check must verify EVERY path, not just that SOME allowed root is mentioned

> **Confirmation status: SEALED (2026-06-10).** The cross-session leak is closed and proven three
> ways: (1) `backend/tests/test_hardening.py::test_bash_cannot_read_another_session_even_if_it_names_its_own`
> (unit-locks the per-path scope policy: every leak vector denied, every legit own-session command
> allowed); (2) `backend/eval/upload_run.py::isolation_gate` drives the REAL SDK across N
> cross-session attempts and asserts no leak; (3) `backend/eval/_deny_enforcement_probe.py` proves a
> `_pre_tool_use` deny genuinely BLOCKS the tool on this SDK (deny-all hook → agent starved, 0 `open`
> steps). The verifier found the live leak; re-verified fixed on the deployed Fly app. Re-open if a
> new tool/path form bypasses `_PATH_TOKEN_RE`.

## Lesson (read this first)

**When you widen a single-root allow-list (`knowledge/`) to PER-SESSION roots (`knowledge/` + the
current session's `uploads/<id>/`), a scope check that asks "does the command MENTION an allowed
root?" is NOT enough — it must verify that EVERY filesystem path the command touches is in scope.**

The original `_bash_is_readonly_kb` proved scope with `"knowledge" in cmd` — fine when `knowledge/`
was the *only* allowed root (any command touching the repo's data necessarily named it). But with a
second, per-session root, a command can **name its own session AND read another session's dir** in
one call:

```bash
python3 -c "import pandas as pd; pd.read_csv('uploads/<MINE>/x.csv'); print(pd.read_csv('uploads/<OTHER>/secret.csv'))"
cat uploads/<MINE>/x.csv uploads/<OTHER>/secret.csv
ls uploads/<OTHER>/        # a 'scaffold' program (ls) bypassed the check entirely
```

The substring check saw `uploads/<MINE>` (its own session) and **approved the whole command**, so the
agent read another client's uploaded data. The leak was **non-deterministic**: the model
self-refused most runs (a discretion-level defense), and leaked when it complied — which is exactly
why a single manual isolation check passed (a **false green**: it hit a refusal run). The boundary
must be the HOOK, never the model's discretion.

## Why it matters (the threat)

The agent is internet-exposed and the upload demo is multi-session. A cross-session read is a
**privacy breach** — one client reading another client's uploaded CSV/PDF. "It refused when I tried"
is not a fix if the refusal is the model's choice, not the sandbox's.

## The fix

`backend/agent.py`: replace the substring "mentions an allowed root" check with **per-path scoping**.
- `_PATH_TOKEN_RE` pulls EVERY `knowledge/…` / `uploads/…` path token (quoted or bare, relative or
  absolute, incl. the live `/app/uploads/<id>/…` form) from the command.
- `_all_named_paths_in_scope(cmd)` requires `_path_in_kb(p)` for **each** token — one out-of-scope
  path (another session's dir, an absolute escape) fails the whole command.
- This guard runs for **every** Bash command, including the `echo`/`test`/`true`/`ls` scaffolds (so
  `ls uploads/<OTHER>` is denied) and python one-liners/heredocs.
- `_path_in_kb` itself was already correct (it checks against `_allowed_roots()` = `knowledge/` +
  the current `_SESSION_ROOT` contextvar, never another session); the hole was only the Bash
  command-level check trusting a substring instead of calling it per path.

## Enforcement (gotcha ⇄ check)

- `backend/tests/test_hardening.py::test_bash_cannot_read_another_session_even_if_it_names_its_own`
  — unit-locks the per-path policy (every leak vector denied; own-session + `knowledge/` allowed).
  Removable-handler-proof: revert to the substring check and it goes red. Runs in `npm run test:agent`
  (keyless CI).
- `backend/eval/upload_run.py::isolation_gate` — REAL-SDK, N cross-session attempts, asserts no
  leak (run: `python -m backend.eval.upload_run isolation`).
- `backend/eval/_deny_enforcement_probe.py` — positive control proving a deny actually blocks a tool
  (the enforcement the isolation relies on). Related: [public-agent-hardening-hook-not-callback.md](public-agent-hardening-hook-not-callback.md)
  (the hook IS the boundary) — this gotcha extends it: the hook's *policy* must be per-path once
  there's more than one allowed root.

## The meta-lesson (for the next person)

A green isolation check that depends on the MODEL refusing is a false green. **Prove the sandbox
denies on a run the model would otherwise comply with** — force the attempt (compliance-inducing
framing) or test the enforcement mechanism directly (deny-all positive control). "It refused once"
≠ "it cannot leak."
