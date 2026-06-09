# Maintenance Spend Intelligence

Answers maintenance **spend** questions (total, by year, by vendor) over `school data 3.csv`, every figure cited to its rows — and, when asked about **overdue payments / who owes us / service-suspension terms** (fields this data lacks), it **honestly refuses**, citing the existing columns as evidence of the absent field and pivoting to the real spend analysis, rather than fabricating an overdue list. This honest-refusal is the clearest demonstration of the trust property the client is buying.

## Docs
- [00-research.md](00-research.md) · [01-design.md](01-design.md) · [02-examples.md](02-examples.md) · [03-tests.md](03-tests.md) · [04-implementation.md](04-implementation.md)
- [user-guide.md](user-guide.md) — the how-to.

## Screenshot / gate ledger

One row per capability → its golden screenshot (captured from the live app) → the journey gate that proves it.

| Capability | Screenshot | Gate (proves it works) |
|---|---|---|
| Spend breakdown (2026 $13,485.66/248, $40,597 total, top vendors), cited rows | `images/maintenance-spend-breakdown.png` | `maintenance-spend-intelligence.spec.ts` (F-B) |
| Honest refusal of the overdue/suspension question (schema-cited, no fabrication) | `images/maintenance-overdue-honest-refusal.png` | `maintenance-spend-intelligence.spec.ts` (F-A) |
| Same honest refusal in Hebrew | `images/maintenance-hebrew-refusal.png` | `maintenance-spend-intelligence.spec.ts` (F-C) |

**Golden facts:** all-time total **$40,597.00 / 750 tickets**; 2026 **$13,485.66 / 248**; top vendor **Oyoba $949.94 / 3**. The data has **no** payment-status/due-date/suspension field → overdue/suspension questions are honestly refused, never fabricated (`validateNoFabrication`).
