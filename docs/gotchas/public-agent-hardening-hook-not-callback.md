# To sandbox a public Agent SDK, the gate is a PreToolUse HOOK — `can_use_tool` is silently inert

> **Confirmation status: SEALED (2026-06-09).** The internet-exposed agent is constrained to
> read-only file ops over `knowledge/` by a `PreToolUse` hook (`backend/agent.py::_pre_tool_use`),
> which the SDK consults before EVERY tool and which hard-denies anything outside the allow-list.
> Verified two ways: (1) a live `whoami`/`/etc/passwd`/`print ANTHROPIC_API_KEY` injection against
> the deployed Fly app was BLOCKED (empty/refusal answer, no system data, no key) and the deny
> reason appeared as the tool result; (2) `backend/tests/test_hardening.py` locks the policy
> (path-escape, write, network, pipe, find -exec all denied; the real pdftotext/pandas/grep flow
> allowed). Re-open if an SDK upgrade changes which mechanism the CLI escalates to.

## Lesson (read this first)

**When you expose a Claude Agent SDK loop to the public internet, you MUST sandbox its tools — and
on this SDK/CLI version (`claude-agent-sdk` 0.1.69, `claude` CLI 2.1.x) the working enforcement
point is a `PreToolUse` HOOK, NOT the `can_use_tool` callback and NOT the `allowed_tools` list.**

- `allowed_tools=[...]` only says which tools the model may *attempt*; the CLI **auto-approves**
  those without ever asking your code, so it cannot enforce path/command scoping. It is not a
  security boundary.
- `can_use_tool=<callback>` *looks* like the boundary (it returns `PermissionResultAllow/Deny`), but
  on the `query()` path here it was **never invoked** — a spy callback logged ZERO decisions while
  tools ran freely. Relying on it would have shipped an **inert** "hardening" — a fake pass.
- A `PreToolUse` hook IS consulted before every tool, and returning
  `{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", ...}}`
  **genuinely blocks execution** — verified: a denied `whoami` did not run; the model saw the deny
  reason and could not work around it.

**Always verify the gate fires by instrumenting it on a real run — don't assume a permission API is
wired just because it exists.** "It compiled and the import resolved" is not "it blocked anything."

## Why it matters (the threat)

A public `/api/ask` is a prompt-injection / RCE surface: the agent runs `Bash` (pdftotext, a pandas
one-liner) under `bypassPermissions`. Without a real gate, a hijacked prompt could `cat /etc/passwd`,
print `ANTHROPIC_API_KEY`, exfiltrate via `curl`, or write/delete files. The skill's whole method
*depends* on shelling out, so we can't just drop `Bash` — we must vet each call.

## The fix (the read-only allow-list hook)

`backend/agent.py`:
- `permission_mode="bypassPermissions"` (no interactive prompts) **plus** the hook as the boundary:
  `hooks={"PreToolUse": [HookMatcher(hooks=[_pre_tool_use])]}`.
- `_pre_tool_use` ALLOWS only: `Read`/`Glob`/`Grep` scoped under `knowledge/` (path OR a
  `knowledge/...` pattern), and `Bash` limited to read-only extraction over `knowledge/` —
  `pdftotext` / a write-and-network-free `python` pandas one-liner / `grep`/`find`(no `-exec`)/etc.,
  with no redirection (`>`), command-substitution (`$(`,`` ` ``), pipes, or path escape (`..`,
  `/etc`). Everything else (`Write`, `Edit`, `WebFetch`, …) is DENIED.
- Input guards in `backend/main.py`/`config.py`: a `MAX_QUESTION_CHARS` length cap (413) and a
  per-IP rolling rate limit (429), so an abusive caller can't bleed agent runs.
- `_extract_output` last-resort fallback: a hard refusal comes back as free prose (no
  ANSWER/EVIDENCE blocks); return it as an un-grounded answer instead of 500-ing.

## Enforcement (gotcha ⇄ check)

- `backend/tests/test_hardening.py` — unit-locks the pure policy: `_path_in_kb`,
  `_bash_is_readonly_kb`, and the `_pre_tool_use` allow/deny matrix (write/network/pipe/escape/
  out-of-scope all denied; the real retrieval commands allowed). Runs in `npm run test:agent`
  (keyless CI gate).
- `backend/tests/test_extract_json.py::test_free_prose_refusal_does_not_crash` — the refusal path.
- Live evidence (recapture if the SDK changes): the injection probe against the Fly URL returns no
  system data and no key; the length probe returns 413.
