# 00 — Research: Maintenance Spend Intelligence

Derived from: the problem (JOB_DESCRIPTION.md example question 2 — "overdue payments + service-suspension terms" — and the "source attribution you can trust" requirement) + first-hand inspection of `data/school data 3.csv`.

> **The domain truth that defines this feature: the spec's Q2 asks about *overdue payments* and *service-suspension terms*, but the data we were given has NEITHER a payment-status field NOR a service agreement. The honest feature is maintenance/invoice **spend analysis** — plus a hard rule that the assistant SAYS SO when asked the literal overdue question instead of fabricating a status. The refusal is not a gap in the feature; it IS the feature's most important demonstration.**

---

## 1. What the spec's Q2 assumes vs. what we have

Spec Q2: *"Which customers have overdue payments and what does the agreement say about service suspension?"* This assumes three things:
1. an **accounts-receivable** dataset with a **paid/unpaid status** and a **due date** per invoice;
2. a notion of **"customers"** who owe money;
3. a **service agreement document** that defines what happens on non-payment (suspension clauses).

**None of the three exist in our data.** `data/school data 3.csv` is a **maintenance-ticket / cost** dataset, not an AR ledger:

| Column | What it is | Is it a payment status? |
|---|---|---|
| `Ticket ID` | actually holds **product/category names** (Cookies, Juice, Jigsaw Puzzles) — mislabeled, like the contracts file | no |
| `Vendor` | the maintenance vendor (Oyoba, Voolith, …) — these are who we **pay**, not customers who owe us | no |
| `Invoice` | a dollar figure (often a small unit cost) | no |
| `Labor Cost`, `Parts Cost`, `Total Cost` | the cost breakdown — Labor+Parts **always** equals Total (clean) | no |
| `Completion Date` | when the work was completed | no — completion ≠ payment |

There is **no `status`, no `paid`, no `due_date`, no `balance`, no `overdue` field anywhere**, and there is **no service-agreement document** defining suspension. Verified directly.

## 2. How a real analyst reads this

A real finance/operations analyst, handed this file and asked Q2, would say within seconds: *"This isn't a receivables ledger — it's a maintenance cost log. I can tell you what we **spent** and which **vendors** cost the most, but I cannot tell you who is **overdue**, because there's no payment status here, and there's no agreement defining suspension."* That sentence **is the golden behavior.** The product must reproduce that honesty, not paper over it.

The anti-pattern — and the exact thing the client says they do **not** want — is a system that, to satisfy a demo, invents an "overdue" flag (e.g. treats old completion dates as "overdue") and prints confident, fabricated names. That is a **trust failure**, and trust/attribution is the property the client is explicitly paying for.

## 3. What the data CAN honestly support (the real feature)

Maintenance **spend analysis** — every figure traceable to the rows that compose it:
- **Total maintenance spend** — verified: **$40,597.00 across 750 tickets**.
- **Spend by period** — e.g. **2026 completions: $13,485.66 across 248 tickets**.
- **Spend by vendor** — e.g. top vendor by total: **Oyoba, $949.94 across 3 tickets**.
- **Cost breakdown** (labor vs parts) per ticket / vendor.
- **Anomaly spotting** — unusually high single tickets (e.g. the $549.98 "Cookies" ticket).

These are real SQL aggregations over real rows. They are useful, and they are honest.

## 4. How spend analysis works in the real world (competitors / prior art)

- **Spend-analytics / AP tools** (Coupa, SAP Ariba spend analysis, simple FP&A dashboards) aggregate cost by vendor/category/period and **always let you drill from a total down to the line items** that make it up — drill-to-detail is the trust mechanism. Our citation model (every figure cites the rows that sum to it) is the same idea.
- **AR/collections tools** (the thing Q2 *literally* asks for) require a status+due-date ledger and dunning rules. We don't have that data, so we don't pretend to be that tool.

## 5. Implications for design (handed to `01`)

1. The real feature is **spend analysis** (SQL over `school data 3.csv`), with every figure cited to its rows.
2. The **defining gate** is the **honest refusal** of the literal Q2: when asked about "overdue payments" or "service suspension," the assistant must state that **no payment-status field and no service agreement exist** and must **not fabricate** an overdue status. This is enforced by `validateNoFabrication()` and a golden "honest refusal" example in `02`/`03`.
3. The `Ticket ID`=category mislabel and the Vendor=who-we-pay (not customer) facts are part of the honesty bar — the answer must not call vendors "customers."
4. If a service-agreement **document** is later supplied, the suspension half becomes a real RAG branch — the architecture supports it; it's deferred for lack of the document, not for lack of capability.
