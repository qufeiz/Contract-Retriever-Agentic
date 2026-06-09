# 01 — Design: Maintenance Spend Intelligence

Derived from: 00-research.md (the data is a maintenance cost log, not an AR ledger; verified spend figures; the no-overdue-field / no-agreement facts).

> **What it does:** answers free-form questions about **maintenance spend** — totals, by vendor, by period, with anomalies — over `school data 3.csv`, with every figure **cited to the rows that compose it**; and, when asked the spec's literal Q2 about *overdue payments / service-suspension terms*, it **honestly states that the data has no payment-status field and no service agreement, and refuses to fabricate an overdue status**. English and Hebrew.

---

## The visible outcome (what the user SEES when it works)

- For a spend question: a readable answer with a **total and/or breakdown** (by vendor or period), each number carrying a **citation to the rows** that sum to it, drillable to the line items.
- For the literal overdue/suspension question: a clear, honest answer — *"this dataset has no payment-status or due-date field and no service-agreement document, so I can't determine overdue payments or suspension terms from it"* — followed by an offer of the spend analysis the data **can** do. **No invented "overdue" list, no fabricated customer names.**

## The single workflow (single-spine)

Single-spine: one ask→route→retrieve→ground→cite sequence. The **honest-refusal** path is a first-class branch off step 2/3, not a separate feature.

| Step | Who/what | What happens | Output | Citation |
|---|---|---|---|---|
| **1. Ask** | user | free-form NL spend question (EN/HE) | raw question | — |
| **2. Route** | LLM router | classifies as **SQL** (spend aggregation). If the question asks for a **field/concept the data lacks** (overdue, paid status, suspension terms, "customers" who owe), route to the **honest-refusal** path. | routing decision (`sql` or `unanswerable: <missing concept>`) | the decision is loggable |
| **3a. SQL retrieve (spend)** | engine | aggregate `Total Cost` by vendor / period / category; identify anomalies | the aggregated rowset | each figure → the **rows** that compose it |
| **3b. Honest-refusal** | engine | detect that the asked concept (overdue/paid/due/suspension/customer-debt) **maps to no column and no document**; produce the "not in this data" statement | the refusal text + the list of fields that **do** exist | cites the **schema** (the columns that exist) to prove the absence |
| **4. Compose (grounded)** | LLM | spend answer with cited figures, OR the honest refusal + offer of available analysis | final answer | citations preserved |
| **5. Render (EN/HE)** | UI | show answer + citations; same for Hebrew | what the user sees | citations visible |

**Single golden scenario for `02`:** the **honest refusal of the literal Q2** (the trust demo) **plus** a real spend answer (total + top vendor), so `02` shows both the working analysis and the refusal.

## Decisions & deferrals

- **Decision — the honest refusal is a designed path, not an error.** "No overdue field" is computed: the concept the user asked for is mapped against the actual schema; finding no column AND no document, the system states the absence and **cites the schema** (the columns that *do* exist) as the evidence. This is auditable, not a guess.
- **Decision — never fabricate a status.** Old completion dates are **not** reinterpreted as "overdue." Vendors are **not** relabeled "customers who owe." A figure is never attributed to a field that doesn't exist. → enforced by `validateNoFabrication()` in `03`.
- **Decision — `Ticket ID` is treated as a `category label`** (it holds product/category names), not an identifier; rows keyed by (Vendor + Completion Date) / row index.
- **Decision — figures are drillable.** Every total cites the rows that compose it (drill-to-detail = the trust mechanism), so a reviewer can verify $40,597.00 = the sum of the 750 rows.
- **Deferral — the service-suspension RAG branch.** If a service-agreement **document** is supplied later, the suspension half of Q2 becomes a real RAG lookup (cited to the document). Deferred for **lack of the document**, not lack of capability — the architecture's hybrid path already supports it.
- **Deferral — a true AR/overdue feature.** Requires a receivables ledger (status + due date) we don't have. Listed so the gap is explicit; un-blocked only by new data.

## Phased plan

- **R1 (this slice):** spend analysis (total / by-vendor / by-period / anomaly) with cited figures, EN/HE; **and** the honest-refusal path for overdue/suspension/customer-debt questions.
- **R2 (deferred):** the service-agreement RAG branch (when a document exists); a real AR/overdue feature (when AR data exists).

## Security / authorization

- **MVP scope:** single-tenant; the maintenance data is the client's own; no per-row access control required.
- **The integrity rule in scope:** the answer must **never attribute a figure to a field the data lacks** and must **never fabricate a status/customer/penalty**. This honest-refusal property is the clearest single demonstration of the trust attribute the client is buying — a system that confidently invents an overdue list is *worse* than one that says "I don't have that data." Enforced by `validateNoFabrication()` + the golden honest-refusal fixture in `03`.
- **Future (extensibility note):** when real AR or service-agreement sources are added, each carries its own scope and the refusal path narrows automatically (the concept now maps to a real source). The schema-aware refusal is what makes the system safely extensible.
