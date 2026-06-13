# Testing

The test discipline for this repo. The core rule: **a passing test must mean the user can actually use the feature** — assert what the user SEES (a cited answer + a real trace), not just that a handler fired.

> **Why the gate shape changed from the parent.** The parent's content gate was a *deterministic pure function* (`validateAnswer()` + fixed-seed journeys). This is an **agent** — non-deterministic by construction (file order, phrasing, run-to-run variance). So the gate is a **looser-but-strong** replacement: pure checks that survive non-determinism (citation-resolvability, required-figure-presence, forbidden-token-absence, trace inspection) run over **N repeated real runs** (flaky == fail) plus an LLM-judge. See `../features/agentic-knowledge-assistant/03-tests.md` for the full rationale.

## Suites

| Suite | What it proves | Run |
|---|---|---|
| **Unit** (`backend/tests/*.py`) | Pure, deterministic, runs every time (keyless). The headline gate is **`validateAnswer()`** (`backend/validate.py`): every `[F:file#loc]` citation token must resolve to a real file + real printed-PAGE label / real row natural-key — it passes every golden answer and **rejects** a fabricated page/row/file or an unbacked token. Also the agent's final-output parser (`_extract_output`) against real messy output (quotes, newlines, prose-prefix). | `npm run test:agent` |
| **Eval harness** (`backend/eval/`) | The golden bar over the **real** agent + **real** `knowledge/` tree, **N times** (default N=5, flaky == fail). Deterministic gates (required facts/citations, validateAnswer, forbidden + cross-domain stop-list, trace T1–T4, self-check audit, pivot) + an LLM-judge for the prose layer. **Calls the Anthropic API** → key-gated, NOT part of the keyless push gate. | `npm run eval:agent` |
| **Journey** (`tests/journeys/*.spec.ts`) | End-to-end against the **running app** (post-deploy): ask a golden question → the answer renders with resolvable `[F:..]` citation chips, the agent **TRACE** panel shows the right files opened (and the wrong domain NOT opened), and the `validateAnswer` badge reads Grounded. Removable-handler-proof: stub the agent → red. | `npm run test:journeys` |

**Run the journey suite against the LIVE deploy, not just localhost.** Set `JOURNEY_BASE_URL=https://<the-new-vercel-url>` so the **prod path** (Next.js → the Python agent backend) is asserted. The final pass runs both localhost and the deployed URL.

**The "done" bar after a release (non-negotiable):** a build is done only when (a) `npm run test:agent` is green (keyless), (b) `npm run eval:agent` is green across **all N runs** (key-gated), and (c) the journey suite is GREEN against the **freshly-deployed production URL** — run it *after* deploy, not against a possibly-stale `.next`. A debug stub once passed locally on a stale bundle and broke every answer in prod: `../gotchas/committed-debug-stub-broke-prod.md`.

## Journey-test discipline (non-negotiable)
- **Assert the visible outcome**, not feedback. "The answer contains 38 expiring contracts, each citing a `[F:contracts.csv#row=…]`, and the trace shows `contracts.csv` opened" — not "a response div appeared".
- **Feedback ≠ outcome.** A spinner stopping proves the request fired, not that the answer is grounded. Assert the citation chips resolve, the claimed facts are present, AND the trace opened the right files.
- **Removable-handler-proof.** If the agent/retrieval were stubbed, the test must fail. A test that would still pass against an empty engine is invalid.
- **Wait on the real signal** (the rendered answer), never a fixed `waitForTimeout`. A test that only passes on retry is a must-investigate race.
- **No graceful skips for missing preconditions.** A missing `knowledge/` file is a RED (asserted by the eval's data-presence check), not a skipped test.

## Journey specs (the ledger — keep in sync with disk)
| Spec | Proves |
|---|---|
| `agentic-knowledge-assistant.spec.ts` | The agentic assistant end-to-end against the live UI: G-1 (contract expiry → 38 / $18,924,883.79, cited rows, honest penalty refusal, trace shows `contracts.csv` and **not** the Carter PDFs), G-2 (Carter Final Judgment → $1,285 + Joni, page-cited to the court file), G-3 (maintenance overdue → honest refusal + $40,597 pivot cited to `maintenance.csv`), G-4 (filing-date **conflict surfaced** — both Feb 10 and Feb 3, both PDFs in the trace), and G-2 in Hebrew (identical figure + citation). Asserts the rendered `[F:..]` chips, the agent TRACE panel, the cross-domain leak guard, and the `validateAnswer` Grounded badge. |
| `live-upload.spec.ts` | The **live-upload** feature end-to-end against the live UI: U-1 (upload `customers.csv` + `service-agreement.pdf` → the cross-source answer with **$18,965.50** overdue, an uploaded-CSV `#row-N` chip and the **§4.3 `service-agreement.pdf#p3`** chip both resolving against the SESSION uploads, the agent TRACE opening **both** uploaded files, the Grounded badge), and U-2 (upload **only** the CSV → lists overdue but **honestly refuses** the penalty rate, no fabricated `1.5%`). Uploads via the dropzone (`file-input`), proving the `session_id` is threaded into the ask. Run against a deploy where the upload path's model (`UPLOAD_MODEL`) is configured. |
| `skill-toggle.spec.ts` | The lean⇄full retrieval-skill **toggle** end-to-end against the running UI (**KEYLESS** — no agent round-trip; stubs submit/poll): the toggle renders, defaults to **full**, flips to **lean** and back (`aria-checked`), and the selected skill is **sent on the ask request** (`skill: "lean"` reaches the wire). Removable-handler-proof: delete the toggle or stop sending `skill` → red. Proves the SWITCH only — the lean skill's ANSWER quality is the cap-blocked eval, not this. Goldens: `../features/live-upload/images/skill-toggle.png` (+ `-lean.png`); captured via `scripts/capture-skill-toggle.mjs`. |

> doc-lint fails the build if a `tests/journeys/*.spec.ts` exists but isn't listed here, or vice-versa.
