# 00 — Research: Contract Intelligence

Derived from: the problem (JOB_DESCRIPTION.md example question 1 + the "hybrid RAG+SQL, source attribution" requirement) + first-hand inspection of `data/school data 1.csv`.

> **The domain truth for contract intelligence: expiry and cost are structured facts; obligations, penalties, and termination terms are document facts. A real answer to "what expires and what are the penalties" needs BOTH — but in THIS corpus the document side does not exist: there is no penalty column AND no vendor-contract documents are loaded. So the honest feature answers the structured half from SQL and explicitly says the penalty half has no source — it does not fabricate penalties and does not reach into the only documents present (the unrelated Carter case file).**

---

## 1. How contract management works in the real world

Organizations track vendor/supplier contracts in a **Contract Lifecycle Management (CLM)** discipline. The facts split cleanly into two kinds, and that split is the whole reason this is a RAG+SQL problem and not a SQL report:

| Fact kind | Examples | Where it lives in the real world | Where it lives in OUR data |
|---|---|---|---|
| **Structured / tabular** | counterparty, start date, **end/renewal date**, annual value, status | a contracts database / CLM register | `school data 1.csv` (Vendor, Start Date, **End Date**, Annual Cost) |
| **Unstructured / document** | **penalty clauses**, termination-for-convenience terms, auto-renewal/notice windows, SLAs, indemnities | the signed contract PDF/Word document | **NOT in our CSV — and NO contract document exists in this corpus at all** (the only PDFs loaded are the unrelated Carter divorce case) → penalty terms have **no source here** |

The questions a contract manager actually asks (from CLM product docs — Ironclad, DocuSign CLM, Icertis, and AP/procurement practice):
- **Expiry/renewal exposure:** *"What's expiring in the next 30/60/90 days?"* — the single most common report, because an auto-renewing contract you forget to cancel costs money and a lapsing one you forget to renew breaks operations. **90 days is the canonical notice window** (most termination/non-renewal clauses require 30–90 days' written notice).
- **Penalty/termination exposure:** *"If we exit this contract early, what does it cost us?"* — this is **document** knowledge: early-termination fees, notice periods, liquidated-damages clauses.
- **The combined question (the spec's Q1):** *"What expires soon AND what are the penalties?"* — in a full system the *list* is a SQL query and each *penalty* is a document lookup. **In our corpus only the SQL half has a source; the penalty half has none** (see §3), so the honest answer delivers the list and states the penalty terms are unavailable.

## 2. What competitors / prior art do

- **CLM platforms (Ironclad, Icertis, DocuSign CLM)** keep a structured register for dates/values **and** an AI "clause extraction" layer that pulls penalty/termination/renewal language *from the document text* and links it to the register row. The link is an explicit reference, not a merged record — you always know which clause came from which document. **The precondition is that the contract documents exist; ours don't, so we don't claim penalties.**
- **AP/procurement tools** surface expiry dashboards from structured data only; they **do not** claim to know penalties unless the contract document has been parsed. A tool that printed a penalty figure with no document behind it would be a liability — which is exactly why our honest answer says "penalty terms not available" rather than inventing one.
- **The anti-pattern the client explicitly rejects:** "upload PDFs into a vector DB and semantic-search." A pure-RAG system can't reliably answer "what expires in 90 days" (dates are a structured filter, not a similarity match); a pure-SQL system can't answer "what's the penalty" (it's prose in a document). **Only the hybrid does both** — which is precisely the capability the client says they're hiring for.

## 3. What our data actually is (inspected, not assumed)

`school data 1.csv` — 1000 rows, header `Contract ID,Vendor,Start Date,End Date,Annual Cost`. Real, usable — and **realistically messy**, which sets the honesty bar:

- **`Contract ID` is not an ID — it holds job titles** (`Registered Nurse`, `Product Engineer`, `Staff Scientist`, …). A real analyst notices immediately that the column is mislabeled; the system must **not** present these as contract identifiers. We treat them as a `role/label` field and identify rows by (Vendor + End Date) or row index.
- **Many `End Date` values precede their `Start Date`.** Verified examples: `Registered Nurse / Avaveo` (Start 11/11/2025, **End 5/9/2024**), `Research Nurse / Rhynyx` (Start 2/23/2025, **End 10/13/2024**). Even inside our 90-day window: `Staff Scientist / Feedfish` (Start **6/26/2026**, End **6/17/2026** — end before start). A real system **preserves and can flag** this anomaly; it does not silently "fix" or drop the row.
- **There is NO penalty, termination, or notice column.** This is the decisive fact: **the structured data cannot answer the penalty half of the question at all.** And **no contract document exists in the corpus** to supply it either (the only PDFs are the unrelated Carter case). So the penalty half has **no source whatsoever** — the honest answer is "expiry and cost known; **penalty terms not available** (no penalty field, no contract documents loaded)."
- **Annual Cost is real numeric** ($1,780.44 – $998,528.37).

## 4. The window math (the headline number, verified)

"Next 90 days" from the **pinned anchor `asOfDate = 2026-06-09`** = `End Date` in **[2026-06-09, 2026-09-07]**. Verified directly against the CSV:
- **38 contracts** fall in that window.
- Their **combined Annual Cost = $18,924,883.79**.

This 38 is the golden number `02-examples.md` is built on, and the fixture `03-tests.md` pins. **It is date-relative — it holds ONLY at `asOfDate = 2026-06-09`** (different at any other date), so the design injects a single deterministic `asOfDate` rather than reading the wall clock, the test freezes it, and the golden screenshot is captured at it. See `01` and `03`.

## 5. Implications for design (handed to `01`)

1. The feature is **SQL-only in this slice** — the expiry list, count, and total come from SQL; the penalty half has no source and is answered "not available." (It becomes hybrid only when vendor-contract documents are supplied — a deferral, not this slice.)
2. The integrity bar is **honesty about the missing source**: state penalty terms are unavailable rather than fabricating them, and **never answer a contract question with text from the Carter case documents** — a cross-domain leak is the worst-case hallucination (enforced by the leak gate in `03`).
3. The data's defects (job-title mislabel, End<Start) are **part of the golden bar** — the toy-vs-real line includes "doesn't pretend the data is clean."
4. The window is **pinned to `asOfDate = 2026-06-09`** so the golden count (38) and the screenshot are deterministic — never the wall clock.
