# Contract Intelligence

Answers free-form questions about vendor-contract **expiry, vendor, and annual cost** by routing to SQL over `school data 1.csv`, citing every figure to its source row — and honestly states that **penalty terms are not available** (no penalty field, no contract documents) rather than fabricating them or reaching into the unrelated case file.

## Docs
- [00-research.md](00-research.md) · [01-design.md](01-design.md) · [02-examples.md](02-examples.md) · [03-tests.md](03-tests.md) · [04-implementation.md](04-implementation.md)
- [user-guide.md](user-guide.md) — the how-to.

## Screenshot / gate ledger

One row per capability → its golden screenshot (captured from the live app at the pinned anchor `2026-06-09`) → the journey gate that proves it.

| Capability | Screenshot | Gate (proves it works) |
|---|---|---|
| Expiry list with count + combined value, cited rows, honest penalty (spec Q1) | `images/contract-90day-answer.png` | `contract-intelligence.spec.ts` (F-A) |
| Cited rows trace to real CSV rows (expanded Sources panel) | `images/contract-citations-expanded.png` | `contract-intelligence.spec.ts` (F-A) |
| Same answer in Hebrew — identical figures + citations | `images/contract-hebrew-answer.png` | `contract-intelligence.spec.ts` (F-B) |
| Single contract (Skalith), honest "no penalty information available" | `images/contract-single-no-penalty.png` | `contract-intelligence.spec.ts` (F-C) |

**Golden facts pinned at `asOfDate=2026-06-09`:** 38 contracts expiring, combined annual value **$18,924,883.79**. The cross-domain-leak guard (J1) keeps Carter case-file content out of every contract answer.
