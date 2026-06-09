# 04 — Implementation: Contract Intelligence

Derived from: 01-design.md (workflow steps 1–5 + decisions/deferrals) + 03-tests.md (the gate list this build satisfies).

This is the build doc: the data model the feature reads, the build order per phase, and the deploy/migration gate. The shared engine internals it sits on are in [../shared-engine/reference.md](../shared-engine/reference.md).

## Data model (read-only, from `school data 1.csv`)

Table `contracts` (built by `lib/engine/loader.ts` per `lib/engine/schema.ts`):

| Column | From CSV | Notes |
|---|---|---|
| `id` | (row index) | the citation anchor → `[S:contracts#<id>]` |
| `contract_id` | `Contract ID` | a **role label** (job title), NOT an identifier — never call it a "contract number" |
| `vendor` | `Vendor` | |
| `start_date`, `end_date` | `Start Date`, `End Date` | raw `M/D/YYYY` strings (defects like End<Start preserved) |
| `end_date_iso`, `start_date_iso` | (derived) | `YYYY-MM-DD` so the window filter sorts/compares correctly |
| `annual_cost` | `Annual Cost` | REAL; summed for the combined value |
| `__malformed` | (derived) | 1 if any cell was an `error: undefined …` marker (none in this table) |

**No penalty column exists** — this is why the penalty half of the spec's Q1 is answered "not available" (`01` deferral; `03` Part 3 rule 3).

## Build order (R1 — this slice)

1. **Loader** (`lib/engine/loader.ts`, `schema.ts`) — already built in the shared engine; contracts is one of its 7 tables. ISO dates derived for the window filter.
2. **Intent** (`lib/engine/intents.ts`) — `contracts_expiring` runs the parameterized window `SELECT` AND a `COUNT(*)` / `SUM(annual_cost)` aggregate over the **same** filter, returned as the intent `summary` (the verifiable 38 / $18,924,883.79). `contracts_by_vendor` serves the single-contract case (Example C). **Deterministic ordering:** the list is `ORDER BY end_date_iso ASC, vendor ASC, id ASC` — a **stable tiebreak** so ties on End Date (the 4-way 2026-06-17 tie: Brainsphere, Fanoodle, Feedfish, Topicware) reproduce the same row order every run, keeping the golden answer + screenshot deterministic (pinned by `tests/unit/loader.test.mts`).
3. **Router guard** (`lib/engine/router.ts`) — when a `contracts_*` intent is selected, the plan is forced **SQL-only** (documents dropped). This is the cross-domain-leak prevention (J1) at the strongest layer: no Carter chunk ever enters evidence.
4. **Grounding** (`lib/engine/answer.ts`) — the verified aggregate is injected into the generation prompt ("state these exact figures"); the prompt requires single-id citation tokens in every language.
5. **Feature gate** (`lib/engine/validate-contract-answer.ts`) — `validateContractAnswer()` runs in the answer path for contract turns: verifiable count, row citations, honest penalty-unavailable, no Carter tokens, defect honesty. Its failures are merged into the response `validation`.

## Tests this build satisfies (from `03`)

- **Unit:** `tests/unit/validate-contract-answer.test.mts` (passes goldens A/B/C, fails toys: vague count, generic penalty prose, fabricated figure, Carter leak, no citation) + `tests/unit/loader.test.mts` (the 38-at-anchor golden, defect preservation).
- **Journey (permanent gate):** `tests/journeys/contract-intelligence.spec.ts` — F-A (EN), F-B (Hebrew), F-C (Skalith), each asserting SQL-only routing, the 38/$18.9M figures, a resolvable citation, the honest penalty statement, **no Carter leak**, and the Grounded validation. Runs against the live deploy.

## Deploy / migration gate

- **The index is rebuilt at deploy** (`npm run build` → `build:index`). The `contracts` table + `end_date_iso` must exist before the read path runs — they're built in the same step, so there's no read-before-column hazard here.
- **`ASSISTANT_TODAY=2026-06-09`** must be set as a Vercel env var so the "next 90 days" window is the pinned anchor and the golden count stays **38** (without it, the count drifts with the wall clock and the golden screenshot/test would rot). → [../../ops/environment.md](../../ops/environment.md).
- **Serverless SQLite:** the bundled `.sqlite` is opened via a `/tmp` copy (see [../../gotchas/sqlite-on-serverless.md](../../gotchas/sqlite-on-serverless.md)) — a prior miss; the journey suite now runs against the live URL to catch a regression.
- **Post-deploy verify:** run `03` Part 5's runbook (EN Q1 → 38 + total + cited rows + honest penalty; HE Q1; Skalith; click a citation; leak check).
