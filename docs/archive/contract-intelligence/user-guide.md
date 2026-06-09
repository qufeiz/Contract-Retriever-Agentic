---
title: Find expiring contracts and their value
type: how-to
feature: contract-intelligence
summary: Ask the assistant which vendor contracts are expiring and get a cited, verifiable list with the combined annual value.
---

# Contract Intelligence — find expiring contracts and their value

> Derived from: 01-design.md (the single contract workflow) + 02-examples.md (Examples A/B/C). This guide gets you a cited, verifiable list of expiring contracts and an honest answer about penalty terms.

## Overview

Contract Intelligence answers free-form questions about your vendor contracts — **which expire in a given window, for which vendor, and at what annual cost** — by querying the structured contract data and citing every figure to its source row. Reach for it when you need a defensible expiry list (for renewals or budgeting), not a vague summary. It is honest about its one limit: the data has no penalty/termination terms, so it tells you that plainly instead of inventing them.

![The assistant answering "what contracts expire in the next 90 days and what penalties are defined" — 38 contracts, $18,924,883.79 combined value, cited rows, and an honest "penalties not available" statement](images/contract-90day-answer.png)

## 1. Ask which contracts are expiring

Type a natural-language question naming a horizon, e.g. *"What contracts expire in the next 90 days and what penalties are defined in those contracts?"* The window is computed from the assistant's anchor date (pinned to 2026-06-09 for this demo data).

```text
What contracts expire in the next 90 days and what penalties are defined in those contracts?
```

## 2. Read the routing decision

The assistant shows that it routed the question to **Structured · SQL** (the contract data) — and, because no contract documents exist, it does **not** pull from the unrelated case-file documents. The routing is visible, not hidden.

![The routing panel showing the question routed to Structured · SQL only](images/contract-90day-answer.png)

## 3. Read the verifiable answer

The answer states a **verifiable count** ("38 contracts expire between 2026-06-09 and 2026-09-07"), the **combined annual value** ($18,924,883.79), and a list of the earliest-expiring contracts — each row carrying a `[S:contracts#id]` citation you can trace to the source CSV row.

![The answer: 38 contracts, $18,924,883.79, and cited rows](images/contract-90day-answer.png)

## 4. See the honest penalty statement

Because the contract data has **no penalty/termination field** and no contract documents are loaded, the assistant states that penalty terms are **not available** — it does not fabricate a clause and does not reach into the unrelated case file. This honesty is part of the working answer.

![The penalty section of the answer stating the terms are not available](images/contract-single-no-penalty.png)

## 5. Trace a citation to its source row

Every `[S:contracts#id]` token corresponds to a real row in `school data 1.csv`. Expand the Sources panel to see the full cited rowset that backs the count and total.

![The expanded Sources panel listing the cited contract rows](images/contract-citations-expanded.png)

## 6. Ask in Hebrew

The same question in Hebrew returns the **identical** figures (38, $18,924,883.79), the same row citations (the `[S:...]` tokens are not translated), and the same honest penalty statement — the architecture is multilingual-ready.

![The same answer in Hebrew with identical figures and citations](images/contract-hebrew-answer.png)

## Result / Verify

You get a defensible, cited expiry list with a correct combined value, in English or Hebrew, and an honest "penalty terms not available" statement — never a fabricated penalty and never content from an unrelated source. Click any citation token to confirm it resolves to the real contract row.

## Related
- [Shared engine reference](../shared-engine/reference.md) — how routing, retrieval, and citation work under the hood.
- [README](README.md) — the screenshot/gate ledger for this feature.
- [Architecture](../../architecture.md) — the system overview.
