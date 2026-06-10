# A public Agent SDK sandbox cannot rely on a PreToolUse deny LIVE — constrain the TOOLSET instead

> **Confirmation status: SEALED (2026-06-10) for the DIAGNOSIS + the design; the golden re-verify is
> PENDING an Anthropic usage-limit reset (2026-07-01).** What's proven: the deployed Fly SDK does NOT
> honor a `PreToolUse` "deny" for a `Read` (a cross-session `Read /app/uploads/<victim>` leaked
> live), while the SAME code DENIES locally — a local↔live divergence. The durable fix (the upload
> agent has NO raw Read/Bash/Glob/Grep, only scoped data-reader tools that refuse any out-of-scope
> path) is unit-proven airtight-by-construction (`backend/tests/test_upload_tools.py`). OPEN: the
> live U-1 golden + live cross-session re-verify could not run (API usage limit) — re-confirm on
> restore. Re-open if a live `Read`-deny is ever observed to actually block.

## Lesson (read this first)

**Do NOT trust a `PreToolUse` hook deny as the SECURITY boundary for a publicly-exposed Agent SDK —
on the deployed CLI/SDK it may be ADVISORY (the tool runs anyway), even though it blocks locally.**
A green local "the hook denies it" test is a **false green about production**. If the agent must be
sandboxed (e.g. multi-tenant uploads where one client's data must never reach another), make the
unsafe action **impossible by construction**: give the agent a CONSTRAINED TOOLSET — no raw
`Read`/`Bash`/`Glob`/`Grep` — only scoped tools that take a *filename* and resolve it against the
allowed roots, refusing any absolute/`..`/foreign path. Then there is no tool to bypass.

This supersedes [public-agent-hardening-hook-not-callback.md](public-agent-hardening-hook-not-callback.md)
for the UPLOAD path: that gotcha established "the hook, not `can_use_tool`/`allowed_tools`, is what
fires" — true — but it did NOT establish that the hook's deny is *enforced*. Live, it isn't for a
`Read`. (The committed-corpus path still uses raw tools + the hook over `knowledge/`, which is
read-only public data — a leak there is not a tenant breach. The constrained toolset is the
upload-path requirement.)

## How it was found (the worked failure)

Two-tenant test on the LIVE Fly app: session B (uploaded only its own file) was asked to read
session A's `/app/uploads/<A>/customers.csv`. **It leaked A's rows** on a compliance run (the trace
showed a real `Read` of A's dir). Non-deterministic — the model self-refused most runs, so a single
manual check passed (a false green). My "deny-enforcement positive control" passed only because it
ran LOCALLY (where the deny blocks); the committed isolation gate also ran the SDK locally → another
false green about live. **A green isolation check that depends on the MODEL refusing, or that runs
the SDK only locally, does not prove the LIVE sandbox blocks.**

## The fix (airtight by construction)

`backend/upload_tools.py` — five in-process MCP data-reader tools (`list_files`, `read_csv`,
`read_pdf_pages`, `read_text`, `grep_files`). Each takes a FILENAME (or `kb/<path>`), and `_resolve`
joins it to ONLY the per-request run dir + `knowledge/`, REFUSING any string with a leading `/`,
`~`, or a `..` segment, or that resolves outside the allowed root. `backend/agent.py` runs the
upload path with `allowed_tools=UPLOAD_ALLOWED_TOOLS` (only these) +
`disallowed_tools=[Read,Bash,Glob,Grep,Write,Edit,Agent,Task,…]`. Defense-in-depth retained: the
store lives OUTSIDE `/app` and each ask sees only an ephemeral run dir (so `/app/uploads/<other>`
doesn't exist); the hook stays as an advisory 2nd layer.

> **SDK return-shape footgun:** an in-process `@tool` error result uses **`is_error`** (snake_case),
> NOT `isError`. The wrong key makes the SDK's MCP layer fail to serialize the result ("tuples
> instead of dicts"), the agent sees an error for every call, and answers come back EMPTY. Match the
> SDK's documented shape exactly.

## Enforcement (gotcha ⇄ check)

- `backend/tests/test_upload_tools.py` — unit-locks the constrained toolset's refusals (absolute
  victim path, `..`, `/etc/passwd`, `/app/uploads/...`, `~/...` all REFUSED; `list_files`/`grep`
  never surface a foreign file/secret; own-session + `kb/` allowed). Removable-handler-proof: widen
  `_resolve` to accept an absolute path → red. Keyless CI gate.
- `backend/eval/upload_run.py::isolation_gate` — real-SDK cross-session probe across multiple attack
  vectors (the old `uploads/<A>`, the real store abs path, `/app/uploads/<A>`, read-map-then-cat),
  asserting the victim secret never appears in the answer NOR the trace. **Run against the LIVE
  deploy** (or a faithful reproduction) — a local-only run is a false green per the lesson above.

## The meta-lesson

"It blocks locally" and "the model refused" are NOT "the production sandbox prevents it." For a
real tenant-isolation boundary, prefer **impossible-by-construction** (no tool can do the unsafe
thing) over **deny-by-policy** (a hook the runtime may ignore). And verify the security gate where
it actually runs — in production.
