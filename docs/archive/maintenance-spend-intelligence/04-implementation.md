# 04 — Implementation: Maintenance Spend Intelligence

Derived from: 01-design.md (workflow steps 1–5 + decisions/deferrals) + 03-tests.md (the gate list this build satisfies).

The build doc: the data model, the build order (spend analysis + the honest-refusal path), and the deploy gate. Shared engine internals: [../shared-engine/reference.md](../shared-engine/reference.md).

## Data model (read-only, from `school data 3.csv`)

Table `maintenance` (built by `lib/engine/loader.ts` per `lib/engine/schema.ts`). Citations read `[S:maintenance#<id>]`.

| Column | From CSV | Notes |
|---|---|---|
| `id` | (row index) | the citation anchor |
| `ticket_id` | `Ticket ID` | a **category label** (product/category), NOT an identifier |
| `vendor` | `Vendor` | a maintenance **provider we pay** — NOT a customer who owes |
| `invoice`, `labor_cost`, `parts_cost`, `total_cost` | … | REAL; `total_cost` is summed for spend |
| `completion_date`, `completion_date_iso` | `Completion Date` | when the ticket was completed (≠ paid/overdue) |
| `__malformed` | (derived) | quarantine flag |

**The columns above are the COMPLETE set** — there is **no** payment-status, paid/unpaid, due-date, balance, or service-suspension field, and no service-agreement document. This absence is the evidence the honest-refusal path cites.

## Build order (R1 — this slice)

1. **Intent** (`lib/engine/intents.ts`) — `maintenance_spend` returns the all-time total ($40,597.00 / 750), an optional per-year subtotal (2026 = $13,485.66 / 248), the top-vendor breakdown (Oyoba $949.94 …), and representative rows — every figure backed by a SQL aggregate over the cited rows. It always reports the grand total, even when the question scopes to a year.
2. **Router** (`lib/engine/router.ts`) — questions about overdue/who-owes/unpaid/suspension are routed to **maintenance_spend** (structured), **not** to the unrelated Carter documents. The router prompt states the only documents are a divorce case, not business agreements.
3. **Honest-refusal grounding** (`lib/engine/answer.ts` → `buildSchemaContext`) — a maintenance turn gets the table's schema injected into generation, so the model cites the existing columns as evidence of the absent field, refuses to invent an overdue list, and pivots to the real spend analysis.
4. **Feature gate** (`lib/engine/validate-maintenance-answer.ts`) — `validateNoFabrication()`: no fabricated overdue/owed/suspension claim; spend figures carry row citations. Merged into the response `validation`.

## Tests this build satisfies (from `03`)

- **Unit:** `tests/unit/validate-maintenance-answer.test.mts` — `validateNoFabrication()` (passes the honest refusal + the real spend answer; fails a fabricated overdue list, an invented suspension clause, a vendor-relabelled-as-debtor) + the **schema-absence guard** (no status/paid/due/overdue/balance column) + **aggregation determinism** ($40,597.00; 2026 $13,485.66/248; Oyoba $949.94).
- **Journey (permanent gate):** `tests/journeys/maintenance-spend-intelligence.spec.ts` — F-A the honest refusal (schema-cited, pivots to $40,597, no fabricated list, no Carter leak), F-B a real spend answer (figures + cited rows), F-C the refusal in Hebrew. Runs against the live deploy.

## Deploy / migration gate

- The `maintenance` table + ISO completion dates are built by `build:index` at deploy; the read path runs after, same step.
- **Post-deploy verify:** run `03` Part 4's runbook (overdue Q → honest refusal + schema + NO invented list; spend Q → $40,597 + 2026 $13,485.66/248 + Oyoba + cited rows; Hebrew refusal; click a citation to drill to tickets). **If the system ever returns an overdue list, a "customer owes" figure, or a suspension clause → fail immediately** — that is the one failure this feature exists to prevent.
