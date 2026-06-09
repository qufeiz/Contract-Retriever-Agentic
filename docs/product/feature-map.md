# Feature Map — AI Business Knowledge Assistant (MVP)

Derived from: JOB_DESCRIPTION.md (the 3 example questions + "NOT a PDF chatbot") + first-hand inspection of every file in `data/`.

> **⚠️ Agentic re-platforming note (read first).** This document's **source verdicts** (which of the 9 sources are usable + their defects) are current and carried forward. But its **engine framing is v1**: it describes the three domain capabilities as separate `docs/features/<name>/` folders over a "RAG+SQL fusion" engine. In the **agentic rebuild** those three capabilities are the **four golden questions of one umbrella feature** — `docs/features/agentic-knowledge-assistant/` — answered by an agent navigating the `knowledge/` tree (no SQL, no embeddings). Read "`contract-intelligence` / `maintenance-spend-intelligence` / `case-file-qa`" below as the **G-1 / G-3 / G-2+G-4** golden scenarios in `02-examples.md`, and "the shared engine / RAG+SQL fusion" as the agentic loop in `architecture.md`. The *data judgments* are what's authoritative here.

> **What this document is.** The authoritative list of the product's *user-facing domain features*, each grounded in the **actual data we were given** (not in the spec's wishful phrasing), plus the one thing that is shared across all of them — the retrieval **engine** — which is *infrastructure*, documented once, not a user feature. Each feature listed as **IN** owns its own `docs/features/<name>/` doc chain (00–04 + user-guide + README). Each **DEFERRED** feature names the exact data defect that blocks a real golden example, so the decision is auditable, not a vibe.

> **Companion — the source vetting.** The full row-level evaluation of all 9 provided sources (usable vs unusable + the exact named defect for each) is the client-facing **`docs/product/data-quality-assessment.md`**. That document is the canonical record of *why* each source is in or out; this map is *which features* the usable ones support. The deferred-features table below summarizes the drops — the assessment holds the evidence.

---

## The one rule that shaped this map: the data is real, messy, and partly broken — we map to what it can *honestly* answer

The single most important act of product judgment here was **reading every file before believing the spec**. The job description's three example questions describe an idealized dataset. The data we actually have only partly matches it. A toy build would wire up all three questions and quietly fabricate the missing pieces; the honest build maps each feature to **what its source can actually ground**, and **defers** (loudly, with the reason) what it cannot.

The findings that drive every decision below (full evidence in each feature's `00-research.md`):

| Source file | What it really is | Real & usable? | The defect that matters |
|---|---|---|---|
| `school data 1.csv` (1000 rows) | **Vendor contracts** — Vendor, Start, End, Annual Cost | **YES** — the spine of `contract-intelligence` | `Contract ID` column actually holds **job titles**, not IDs; many `End Date` precede `Start Date`; **no penalty column at all** |
| `school data 3.csv` (750 rows) | **Maintenance tickets / invoices** — Vendor, Invoice, Labor, Parts, Total, Completion Date | **YES** — the spine of `maintenance-spend-intelligence` | Labor+Parts **always** equals Total (clean); **there is NO paid/unpaid/overdue/due-date status column** |
| `📄 FAMILY COURT CASE FILE (MOCK).pdf` (24 pp) | **Carter divorce case file** — structured, page-numbered, with a Final Judgment | **YES** — the spine of `case-file-qa` | none material; rich and citable |
| `story if the Carters.pdf` (3 pp) | **Carter narrative** — same case, more biographical detail | **YES** — the corroborating second document for `case-file-qa` | one cross-doc nuance: filing date reads "10 Feb 2026" on the court cover but "Feb 3, 2026" in both narratives |
| `school data 2.csv` (1000 rows) | *intended* course enrollment | **NO** | `term_name` is **100% a Ruby error string** (`error: undefined method 'first'…`); the `status` column holds **gender values**, not enrollment status — header/data are misaligned |
| `school data 4.csv` (235 rows) | *intended* payroll | **PARTIAL** | salary/gross/net are real, but `pay_method` and `payroll_notes` are **100% error strings** |
| `school data 5.csv` (788 rows) | *intended* invoice totals | **NO** | **every row is identical** (`students=180, per_student=6, total=1080`) — degenerate, zero analytical value |
| `school data 6.csv` (720 rows) | *intended* payroll (alt) | **PARTIAL** | `pay_month` ranges **1–100** (impossible), `payment_method` is a random integer, currency is a free-for-all of 80+ codes |
| `school data .csv` (1000 rows) | a generic **person list** (name, email, IP) | **NO** | not a business domain — no question in scope touches it |

**The product consequence, stated plainly:** of the spec's three example questions, **two are answerable as a real golden example and one is not as literally phrased**:
- Q1 (expiring contracts + penalties) → **answerable**, but with an honest seam: the *expiry* is structured (SQL over `school data 1`), the *penalty* is **not in the structured data** and must come from a contract **document**. This is the canonical RAG+SQL fusion the client is paying for. → `contract-intelligence`.
- Q2 (overdue payments + suspension terms) → **NOT answerable as written**: `school data 3` has **no overdue/paid status and no agreement document defining suspension**. We do **not** fabricate an "overdue" flag. We ship the honest, real version of what the data supports — **maintenance/invoice spend analysis** (totals by vendor, by period, anomaly spotting) — and we make the assistant **say so** when asked the literal overdue question rather than inventing a status. → `maintenance-spend-intelligence` (+ the no-fabrication gate).
- Q3 (active projects + risks from docs) → there is **no projects table** and no per-project risk document; the only rich document set is the Carter case file. So Q3's *shape* (document-grounded narrative summary with citations) is delivered by **`case-file-qa`** over the real documents we have.

This is not a downgrade of the spec — it is the **honest delivery** of it. The client explicitly does **not** want "uploads PDFs into a vector DB and semantic-searches." They want routing, hybrid retrieval, grounded generation, and **source attribution you can trust**. A system that fabricates an "overdue" column to satisfy a demo would fail exactly the trust requirement the client cares about most.

---

## The shared engine (INFRASTRUCTURE — documented once, NOT a user feature)

Every feature below is the **same pipeline** pointed at a different domain. That pipeline is documented **once**, as architecture, and is **not** itself a feature with a `user-guide`:

```
question → [router: which source(s)?] → [SQL retrieval over SQLite]  ┐
                                       → [RAG retrieval over doc chunks]┤→ [grounded compose] → answer + citations
                                       → [both, kept SEPARATELY cited] ┘
                          (English + Hebrew on both the question and the answer)
```

- **Ingestion** — CSVs → SQLite tables (typed, with the data defects preserved/flagged, not silently "cleaned"); PDFs → page/section chunks → embeddings → a vector index.
- **Query router** — an LLM decides, per question, whether the answer lives in structured data, documents, or both.
- **Hybrid retrieval** — SQL for the structured side, vector-RAG for the document side.
- **Grounding + citation** — every claim in an answer traces to a **row** (table + row key) or a **document span** (file + page/section). Structured and document sources are cited **separately and never joined on a fabricated key**.
- **Hebrew seam** — questions and answers in English **and** Hebrew.

→ Documented in `docs/architecture.md` (the request loop, router design, extensibility for the spec's future CRM/email/cloud integrations) and `docs/features/<shared>/reference.md` (the live ops runbook). **Authored by the Engineer**, not the PM; the PM's per-feature docs *cite* it.

**The cross-source integrity rules (apply to every feature):**
1. **No false join** — when an answer combines a CSV row and a document span, the two are **cited as two distinct sources**; we never invent a join key to pretend they're one record unless a real shared identifier exists.
2. **No cross-domain leak (critical)** — a question about one domain must **never** be answered with text retrieved from an unrelated document. The corpus's only documents are the Carter divorce case + story; a **contract** question must never surface Carter case-file text, and a **maintenance** question must never either. Answering "what's the contract penalty?" with divorce-case content is the worst-case hallucination and is a hard gate in each feature's `03`.
3. **Honest about a missing source** — if the source for the asked concept doesn't exist (a penalty document, an overdue field), the answer **says so** rather than fabricating or cross-retrieving. This is the unifying trust property across all three features.

---

## Features — IN this MVP

Each owns a full Big-tier, single-spine doc chain under `docs/features/<name>/`.

### 1. `contract-intelligence` — **build first** (it is the spec's headline question)
- **Source(s):** `school data 1.csv` (structured: expiry, vendor, annual cost). **There is NO penalty source** — no penalty column, and no vendor-contract documents are loaded (the only PDFs are the unrelated Carter case). So this slice is **SQL-only**; the penalty half is answered honestly as "not available."
- **Workflow:** ask → router picks **SQL** for expiry/cost and marks penalty **unavailable** (it must NOT route to the Carter documents) → SQL finds contracts whose `End Date` is within the window (pinned `asOfDate = 2026-06-09`) → compose a grounded answer that lists the expiring contracts with row citations **and explicitly states penalty terms are not available** → English/Hebrew.
- **Golden Q → cited answer:** *"What contracts expire in the next 90 days and what penalties are defined in those contracts?"* → **"38 contracts expire between 2026-06-09 and 2026-09-07"** (combined annual value **$18,924,883.79**; cite `school data 1` rows, e.g. Edgepulse End 2026-06-11 $779,823.65, **and** the 37 others), **and an honest statement that penalty terms are not available** (no penalty field, no contract documents) — penalties are **not** fabricated and **not** pulled from the Carter case.
- **Honesty bar (the toy-vs-real line):** a toy build invents a penalty per contract, or worse answers the penalty question with divorce-case text. The real build cites expiry to a **row**, says **"penalty terms not available"**, never fabricates, and **never leaks Carter content** into a contract answer (a hard `03` gate).
- **Golden screenshot:** the assistant answering the 90-day question at the pinned anchor, showing the **38-count**, the **$18,924,883.79** total, a sample of cited contract rows, and the **honest "penalties not available"** statement.

### 2. `maintenance-spend-intelligence` — the honest version of spec Q2
- **Source(s):** `school data 3.csv` (maintenance tickets / invoices: Vendor, Invoice, Labor, Parts, Total, Completion Date). Optionally a service-agreement **document** if one exists for the suspension-terms half.
- **Workflow:** ask → router picks **SQL** (and **RAG** if a service agreement is in scope) → SQL aggregates spend by vendor / period / category → compose a grounded answer with the **rows that make up the total** cited → English/Hebrew.
- **Golden Q → cited answer:** *"How much did we spend on maintenance in 2026, and which vendors cost the most?"* → a total + a vendor breakdown, **each figure traceable to the `school data 3` rows** that sum to it.
- **The defining honesty gate (this is the most important gate in the whole MVP):** when asked the **literal spec Q2** — *"Which customers have overdue payments and what does the agreement say about service suspension?"* — the assistant must answer **"this dataset has no payment-status or due-date field, and no service agreement defining suspension, so I can't determine overdue payments from it"** and offer the spend analysis it *can* do. **It must not fabricate an 'overdue' status.** A `validateNoFabrication()` gate + a golden "honest refusal" example enforce this. This is the single clearest demonstration of the trust property the client is paying for.
- **Golden screenshots (two):** (a) the spend breakdown **doing real work** (real totals, real vendors, cited rows); (b) the **honest "no overdue field" answer** to the literal Q2 — clearly labeled as the *refusal* demo, not the headline.

### 3. `case-file-qa` — document-grounded Q&A (the spec Q3 *shape*)
- **Source(s):** the **two Carter PDFs** — the formal court case file (page-numbered, with the Final Judgment) **and** the corroborating narrative. Document-only RAG (no SQL side).
- **Workflow:** ask → router picks **RAG (documents only)** → retrieve the relevant page/section spans → compose a grounded answer that cites **file + page/section** → English/Hebrew.
- **Golden Q → cited answer:** *"What was the final child support amount and who got primary residence in the Carter case?"* → **"$1,285/month child support; primary residence to Joni Carter; joint legal custody; equal asset split; home sale ordered within 12 months"** — each fact cited to **Page 24 – Final Judgment** of the court case file. A second golden Q on **grounds for divorce** corroborates across **both** documents (gambling addiction → alcohol → domestic incident), citing each.
- **Honesty bar:** answers cite the **specific page/section**; the cross-document **filing-date discrepancy** (10 Feb on the cover vs Feb 3 in the narratives) is surfaced, not silently averaged — a real document-QA system flags conflicting sources.
- **Golden screenshot:** the assistant answering the Final-Judgment question with **$1,285/mo** and the **Page 24** citation visible.

---

## Features — DEFERRED (with the exact blocking defect — this list is the honesty record)

These are listed so the decision is **auditable**: each was inspected and rejected for a *specific, named* data defect, not skipped for time.

| Candidate feature | Source(s) | Why deferred (the defect) | What would un-block it |
|---|---|---|---|
| `enrollment-intelligence` | `school data 2.csv` | `term_name` is **100% a Ruby error string**; the `status` column contains **gender values**, not enrollment status — the columns that the feature needs are **structurally corrupt**. No real golden example is possible. | A re-export of the source where `term_name` and `status` carry real values. |
| `payroll-intelligence` | `school data 4.csv` + `school data 6.csv` | Salary/net are real, but **`4`'s `pay_method`+`payroll_notes` are 100% error strings**, and **`6`'s `pay_month` ranges 1–100** (impossible) with a random-integer `payment_method`. Aggregates (total payroll, by department) are *technically* computable, but the two files **disagree in schema and can't be joined**, and the headline payroll fields are corrupt — any golden example would be built on broken columns. | A single clean payroll export with valid pay periods and methods; then this is a strong SQL feature. |
| `invoice-volume` | `school data 5.csv` | **Every row is identical** (`180/6/1080`). There is no variance to analyze — any "insight" is the same constant. Degenerate. | A real per-entity invoice-count export. |
| `people-directory` | `school data .csv` | A generic person list (name/email/IP) with **no business question in scope**. Not a domain feature. | A business question that needs it (none in the spec). |

> If the client later supplies clean re-exports, `payroll-intelligence` and `enrollment-intelligence` slot straight into the same engine — the architecture's extensibility (the spec's explicit requirement) is exactly what makes them cheap to add later. That is the point of documenting the engine once.

---

## Build order (for the Engineer + the shared task list)

1. **Shared engine + immune system** (Engineer, task #1) — ingestion, router, hybrid retrieval, grounding/citation, Hebrew seam, base UI, CI with doc-lint + doc-structure-lint, first deploy. Documented in `architecture.md` + the shared `reference.md`.
2. **`contract-intelligence`** (task #2) — first feature slice; exercises the full SQL+RAG fusion and the dual-citation/no-false-join rule. PM authors its 00–03 first.
3. **`maintenance-spend-intelligence`** (task #3) — exercises the **no-fabrication / honest-refusal** gate (the trust property).
4. **`case-file-qa`** (task #4) — exercises document-only RAG, multi-document corroboration, and conflicting-source surfacing.
5. **Final assembly** (task #5) — single client deliverable, architecture diagram, final deploy, full verify.

Each feature's PM docs (`00`–`03`) are authored **under** the doc-lint / doc-structure-lint the Engineer stands up in step 1, with a literal `Derived from:` line on every doc. The Engineer authors each feature's `04` / `user-guide` / `README` / `reference` from the PM's `01`/`02`; the PM later **checks** the published user-guides for product accuracy.
