# Data Quality Assessment — all 9 provided sources

Derived from: first-hand, row-level inspection of every file in `data/` (the 7 CSVs + 2 PDFs), cross-checked against the spec's three example questions in `JOB_DESCRIPTION.md`.

> **Why this is in the client deliverable (not a footnote).** The client's single most-stated fear is naive work — *"someone who simply uploads PDFs into a vector database and performs semantic search."* The antidote is **source-vetting judgment**: knowing what your data can and cannot honestly answer *before* you build. This document is that judgment, made explicit. We evaluated all 9 sources, built features only where a source can ground a **real, cited** answer, and **deliberately dropped** the sources that can't — naming the exact defect for each. **That discipline is the product**, and it is exactly what separates a trustworthy retrieval system from a confident-but-fabricating one.

---

## At a glance

| # | Source file | Intended domain | Verdict | Used in |
|---|---|---|---|---|
| 1 | `school data 1.csv` (1000 rows) | vendor contracts | ✅ **USABLE** | `contract-intelligence` |
| 2 | `school data 3.csv` (750 rows) | maintenance tickets / invoices | ✅ **USABLE** (with an honesty boundary) | `maintenance-spend-intelligence` |
| 3 | `📄 FAMILY COURT CASE FILE (MOCK) – FINAL VERSION.pdf` (24 pp) | legal case file | ✅ **USABLE** | `case-file-qa` |
| 4 | `story if the Carters .pdf` (3 pp) | legal case narrative | ✅ **USABLE** (corroborating doc) | `case-file-qa` |
| 5 | `school data 2.csv` (1000 rows) | course enrollment | ❌ **UNUSABLE** | — (dropped) |
| 6 | `school data 4.csv` (235 rows) | payroll | ⚠️ **PARTIAL → dropped** | — (deferred) |
| 7 | `school data 6.csv` (720 rows) | payroll (alt) | ⚠️ **PARTIAL → dropped** | — (deferred) |
| 8 | `school data 5.csv` (788 rows) | invoice totals | ❌ **UNUSABLE** | — (dropped) |
| 9 | `school data .csv` (1000 rows) | (generic person list) | ❌ **OUT OF SCOPE** | — (dropped) |

**Result:** 4 of 9 sources support real, grounded, cited features; 5 were vetted and dropped for the specific defects below. **We did not force a feature out of broken data** — a fabricated feature on bad data is the exact failure mode the client wants to avoid.

---

## USABLE sources (what we built on)

### 1. `school data 1.csv` — vendor contracts ✅
- **Columns:** `Contract ID, Vendor, Start Date, End Date, Annual Cost` (1000 rows).
- **Why usable:** `Vendor`, `End Date`, and `Annual Cost` are clean and analytically rich — they support the spec's headline question (expiry exposure) with verifiable SQL. **38 contracts expire in the 90 days after 2026-06-09**, combined annual value **$18,924,883.79** (verified).
- **Defects we noted and handle honestly (not hidden):**
  - `Contract ID` is **mislabeled** — it holds **job titles** (Registered Nurse, Staff Scientist…), not identifiers. We treat it as a `role label` and key rows by (Vendor + End Date).
  - Many `End Date` values **precede** their `Start Date` (e.g. Staff Scientist/Feedfish: Start 2026-06-26, End 2026-06-17). We **preserve and can flag** these — we do not silently "clean" or drop them.
  - **No penalty/termination column**, and **no contract documents exist** in the corpus. So the spec's penalty sub-question has **no source** — the feature answers it honestly as *"penalty terms not available,"* never fabricating one. (Detail: `docs/features/agentic-knowledge-assistant/02-examples.md` §G-1.)

### 2. `school data 3.csv` — maintenance tickets / invoices ✅ (with an honesty boundary)
- **Columns:** `Ticket ID, Vendor, Invoice, Labor Cost, Parts Cost, Total Cost, Completion Date` (750 rows).
- **Why usable:** the cost fields are clean (Labor + Parts always equals Total) and support real spend analysis — **total maintenance spend $40,597.00 / 750 tickets**, **2026 $13,485.66 / 248 tickets**, top vendor **Oyoba $949.94** (verified).
- **The honesty boundary (the most important judgment in this whole assessment):** the spec's Q2 asks for **overdue payments + service-suspension terms**. This data has **no payment-status, due-date, or paid/unpaid field**, the vendors are **who we pay** (not customers who owe us), and there is **no service-agreement document**. So Q2 as literally phrased is **not answerable** — and the feature is built to **say so and cite the schema as evidence**, rather than invent an "overdue" list. (`Ticket ID` is also mislabeled — it holds product/category names.) Detail: `docs/features/agentic-knowledge-assistant/02-examples.md` §G-3.

### 3–4. The two Carter PDFs — legal case ✅
- `📄 FAMILY COURT CASE FILE (MOCK) – FINAL VERSION.pdf` is a structured, **page-numbered** court file (Case FC-2026-10458) with a citable **Final Judgment on Page 24** (child support **$1,285/month**, primary residence Joni Carter). `story if the Carters .pdf` is a corroborating narrative of the same case.
- **Why usable:** rich, page-level, citable content — ideal for document-grounded Q&A with **per-fact page citations**, **multi-document corroboration** (the grounds appear in both), and a **real conflict to surface** (filing date reads "10 February 2026" on the court cover but "February 3, 2026" in both narratives). Detail: `docs/features/agentic-knowledge-assistant/02-examples.md` §G-2/§G-4.

---

## UNUSABLE / DROPPED sources (vetted, then dropped — with the exact named defect)

These were not skipped for time. Each was inspected at the row level and dropped for a **specific, verifiable** defect. Dropping them is the responsible call — building on them would produce confident, fabricated answers.

### 5. `school data 2.csv` — course enrollment ❌ UNUSABLE
- **Defect (structural corruption):** the `term_name` column is **100% a Ruby error string** — every row reads `error: undefined method 'first' for nil:NilClass`. The `status` column (which should be active/dropped/etc.) contains **gender values** (Female, Male, Non-binary, Genderfluid…) — header and data are **misaligned**. The columns the feature would need are not just sparse, they're the **wrong data entirely**.
- **Why no feature:** there is no real value to retrieve or cite; any "enrollment" answer would be built on corrupted columns.
- **Un-blocked by:** a re-export where `term_name` and `status` carry their real values.

### 6 & 7. `school data 4.csv` + `school data 6.csv` — payroll ⚠️ PARTIAL → dropped
- **Defect:** salary/gross/net figures are real, **but** `school data 4`'s `pay_method` **and** `payroll_notes` are **100% error strings**, and `school data 6`'s `pay_month` ranges **1–100** (impossible for a month), its `payment_method` is a **random integer**, and currency is a free-for-all of 80+ codes. The two files **disagree in schema** and can't be reconciled into one payroll view, and the headline payroll fields are corrupt.
- **Why no feature:** aggregates are *technically* computable, but a golden example would rest on broken columns and an un-joinable pair — not a defensible "real, cited" answer.
- **Un-blocked by:** a single clean payroll export with valid pay periods and methods. (Then this is a strong SQL feature — it slots into the same engine.)

### 8. `school data 5.csv` — invoice totals ❌ UNUSABLE
- **Defect (degenerate):** **all 788 rows are identical** — `students=180, invoices_per_student_per_year=6, total_invoices=1080`. There is **zero variance** to analyze; every "insight" is the same constant.
- **Why no feature:** nothing to retrieve, compare, or cite that isn't the same single fact.
- **Un-blocked by:** a real per-entity invoice-count export with actual variation.

### 9. `school data .csv` — generic person list ❌ OUT OF SCOPE
- **What it is:** `id, first_name, last_name, email, gender, ip_address` — a generic directory of people, not a business domain.
- **Why no feature:** **no question in the spec touches it**; there is no business intelligence to ground here. (It also carries PII-shaped fields — emails, IPs — that a real deployment would scope and protect; out of scope for this MVP.)
- **Un-blocked by:** a business question that genuinely needs it (none in the spec).

---

## The takeaway for the client

This assessment is the difference between a demo and a system you can trust. We **mined the four sources that hold real, citable value**, built features that **ground every answer and cite its source**, and **honestly dropped the five that don't** — naming each defect so you can re-supply clean data and slot those domains into the same engine later. The system is built to **say "I can't answer that from this data"** when the source isn't there (the maintenance-overdue and contract-penalty cases) rather than fabricate — which is precisely the trust property you asked for, applied not just at answer time but at **data-intake time**.
