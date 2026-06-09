# 03 — Acceptance Gates: Maintenance Spend Intelligence

Derived from: 01-design.md §workflow (steps 1–5 → one gate per step) + 02-examples.md (Examples A/B/C → one fixture per example).

> **The gate list — *what* to assert.** The Engineer writes the runnable tests at build. Every gate is **removable-handler-proof**: stub the handler to a no-op (or to a plausible fabrication) and the gate must go **red**. The marquee gate of this feature — and arguably of the whole MVP — is the **no-fabrication / honest-refusal** gate.

---

## Part 1 — A gate per workflow step (from `01`)

| # | Workflow step | Gate — what it asserts | Removable-handler proof |
|---|---|---|---|
| **G1** | 1. Ask | EN and HE spend/overdue questions are both accepted and reach the router. | Reject HE → G1 red. |
| **G2** | 2. Route | A spend question routes to `sql`; an **overdue/paid/suspension/customer-debt** question routes to the **honest-refusal** path (`unanswerable: <missing concept>`), NOT to a fabricated SQL result. | Make the router send the overdue question to SQL and return rows → G2 red. |
| **G3a** | 3a. SQL spend | Spend aggregation returns verified figures: total **$40,597.00 / 750 tickets**; 2026 = **$13,485.66 / 248**; top vendor **Oyoba $949.94**. | Return all-zero or all-rows totals → figures wrong → G3a red. |
| **G3b** | 3b. Honest-refusal | The refusal path produces a "no payment-status field / no agreement" statement **and cites the schema** (the real column list) as evidence. | Make it return an empty string or a fabricated overdue list → G3b red. |
| **G4** | 4. Compose | The composed answer is either cited spend figures OR the honest refusal — never a fabricated overdue list. | Compose a fake overdue list → G4 red (via `validateNoFabrication`). |
| **G5** | 5. Render EN/HE | The HE refusal carries the **same reasoning + the $40,597.00 figure** as EN. | HE path fabricates or drops the schema citation → G5 red. |

## Part 2 — A fixture per golden example (from `02`)

| # | Fixture | Assertion | Removable-handler proof |
|---|---|---|---|
| **F-A** | Example A (EN honest refusal) | Answer states no payment-status field exists, cites the schema, contains **zero fabricated customer/overdue names or figures**, and offers the real spend analysis. | An answer naming "overdue customers" fails F-A. |
| **F-B** | Example B (EN spend) | Answer states **$13,485.66 / 248** for 2026, the top-vendor table (Oyoba $949.94 …), and **$40,597.00 / 750** total, each cited to rows. | A vague "about $40k" answer (no exact figure, no citation) fails F-B. |
| **F-C** | Example C (HE refusal) | The HE refusal carries identical reasoning + the **$40,597.00** figure + schema citation. | A HE answer that fabricates or errors fails F-C. |

## Part 3 — `validateNoFabrication()` — the marquee content-fidelity gate

A **pure function** the Engineer builds and runs in the answer path, pinned by a unit test that **passes every golden answer (A/B/C) and fails every toy/fabricating answer**. Rules:

1. **No status invented from absence** — if the question asks for a concept (`overdue`, `paid`, `unpaid`, `due`, `suspension`, `delinquent`, `customer owes`) that maps to **no column in the maintenance schema and no document**, the answer MUST contain an explicit "not in this data" statement and MUST NOT contain a list/total attributed to that concept. *(A fabricated overdue list → fail.)*
2. **Schema-cited absence** — the refusal cites the actual column set as evidence (proves the absence is checked, not asserted).
3. **No role confusion** — vendors are not labeled "customers who owe us."
4. **Figures are exact + cited** — any spend figure is a specific number cited to rows, not a vague quantifier; the figure must match a real SQL aggregation over `school data 3.csv`.
5. **No fabricated document** — no suspension/agreement clause is quoted, since no agreement document exists (unless one is genuinely added to the corpus, in which case it must carry a real document citation).

> **Why this gate is the most important in the MVP:** removable-handler proves the handler ran; it **passes** a confident fabrication ("Oyoba is overdue $1,733"). The client's single stated requirement is **source attribution you can trust** — a system that invents an overdue list fails that requirement catastrophically while *looking* like it works. `validateNoFabrication()` turns "doesn't make things up" into a **red unit test**. **Required.**

## Part 4 — Generic SWE + prod-verify

- **Schema-absence unit test:** assert the maintenance schema has **no** `status`/`paid`/`due`/`overdue`/`balance` column (a regression guard: if someone later adds a fake "overdue" column derived from completion date, this test catches it and forces a design conversation).
- **Aggregation determinism:** the spend figures are computed from the static CSV → assert exact values ($40,597.00; $13,485.66/248; Oyoba $949.94) so a query regression is caught.
- **Journey test (Phase 5, committed permanently):** drive the real UI — ask the literal Q2 → assert the rendered answer contains the honest-refusal language and the schema citation and contains **no** fabricated overdue names; ask the spend question → assert $40,597.00 and a cited vendor row; repeat the refusal in Hebrew. Seed data via `ensure*`; **no graceful skips**.

### Prod-verify runbook (post-deploy)
1. Ask the literal Q2 (EN) → confirm the honest refusal + schema citation + **no** invented overdue list.
2. Ask the spend question (EN) → confirm $40,597.00 total, 2026 $13,485.66/248, Oyoba top vendor, cited rows.
3. Ask the refusal in Hebrew → confirm identical reasoning + $40,597.00.
4. Click a spend citation → confirm it drills to the real tickets that sum to the figure.
5. If the system **ever** returns an overdue list, a "customer owes" figure, or a suspension clause → **fail immediately**; that is the one failure this feature exists to prevent.
