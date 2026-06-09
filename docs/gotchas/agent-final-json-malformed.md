# Don't make the agent hand-write JSON whose string field holds free prose

> **Confirmation status: SEALED (2026-06-09).** The agent now emits its final output in a two-block
> `===ANSWER===` / `===EVIDENCE===` format — the prose answer (quotes/$/newlines) is OUTSIDE any
> JSON, and only the small, prose-free EVIDENCE array is JSON. Verified via
> `backend/tests/test_extract_json.py` (incl. the exact G-4 quoted-date case) AND all four golden
> fixtures (G-1's 38-row answer, G-4's quoted dates) now parse + pass the eval gates. Re-open if a
> new output shape slips past the parser.

## Lesson (read this first)

**Do NOT ask an agent to emit a single JSON object where a string field contains free prose.** The
prose WILL contain a double-quote (a legal doc quoting `"Filed: 10 February 2026."`), a `$`, or raw
newlines — any of which breaks `json.loads`, and a stray `"` is not mechanically un-ambiguous to
repair. Instead, **separate the free prose from the structured data**: put the prose in its own
delimited block and keep JSON only for the small, prose-free part (here, the evidence list). Also
never assume the model honored "output ONLY the object" — it intermittently prefixes prose.

## What happened (two real breaks, same root cause)

The eval harness drove the realistic large/quote-heavy answers that a single happy-path smoke test
misses:

1. **G-1** (~13 KB, 40 evidence items): the agent prefixed `"...Composing the final JSON now.\n\n{...}"`
   and put **literal newlines** inside the `answer` string → `Expecting ',' delimiter` at char 6516.
2. **G-4**: the `answer` string contained an embedded **double-quote** — `"Filed: 10 February 2026."`
   — which terminated the JSON string early → `Expecting ',' delimiter: line 2 column 214`.

Both are inherent: the answers legitimately contain quotes, newlines, and `$`.

## The fix

The agent's final output is now the two-block format (`backend/agent.py` system prompt +
`_extract_output`):

```
===ANSWER===
<free prose with inline [F:..] tokens — quotes/newlines/$ all fine, it is NOT inside JSON>
===EVIDENCE===
[{"file": "...", "loc": "...", "snippet": "single-quotes only"}]
```

`_extract_output` splits on the markers (ignoring any prose before them) and parses ONLY the small
EVIDENCE array as JSON (still defensively: balanced-bracket extraction + control-char escape). A
legacy single-object fallback remains for safety.

## Enforcement (gotcha ⇄ check)

- Regression test: `backend/tests/test_extract_json.py` — the two-block format, an answer WITH
  double-quotes (the exact G-4 break), multi-line answers, prose-before-markers, and the legacy
  fallback. Runs in `npm run test:agent` (the keyless CI gate).
- The eval harness (`backend/eval/run.py`) drives the **real** G-1 (38-row) and G-4 (quoted-date)
  answers every run, so a regression fails the eval, not just the unit test.
