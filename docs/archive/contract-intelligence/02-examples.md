# 02 — Golden Examples: Contract Intelligence

Derived from: 01-design.md §workflow (steps 1–5, the single golden scenario: spec Q1 over the pinned 90-day window) + the verified data in 00-research.md + the corpus reality that NO penalty source exists.

> **This is the acceptance bar.** Every example here is built from **real rows in `data/school data 1.csv`** at the pinned anchor date **2026-06-09**. Because the corpus contains **no vendor-contract documents and no penalty column**, the golden answer to the penalty half is an **honest "not available"** — never a fabricated clause, never text pulled from the unrelated Carter case file. The toy-vs-real contrast defines the line; `validateContractAnswer()` + the cross-domain-leak gate in `03` must pass every golden answer and fail every toy/leaking answer.

> **Citation format.** The examples below write citations in a readable prose form (*[source: `contracts` table, row …]*); the **engine renders them as inline tokens `[S:contracts#<id>]`** (structured rows) and `[P:<doc>#<page>]` (document pages). These are the same citation — the prose form is for the acceptance bar's readability; the **engine's golden answer and screenshots use the `[S:…]` token form**, and `03`'s gates assert the token resolves to a real row. Contract answers use **only `[S:contracts#…]`** tokens (no `[P:…]` document tokens — penalties have no document source).

---

## Golden Example A — the spec's headline question (EN)

**Question:** *"What contracts expire in the next 90 days and what penalties are defined in those contracts?"*

**Pinned anchor:** `asOfDate = 2026-06-09` → window end **2026-09-07**.

### The grounded answer the system must produce

> **38 contracts expire between 2026-06-09 and 2026-09-07** (next 90 days), with a combined annual value of **$18,924,883.79**. *[source: `contracts` table (`school data 1.csv`), `End Date BETWEEN 2026-06-09 AND 2026-09-07` → 38 rows]*
>
> The earliest to expire:
> | Role label | Vendor | End Date | Annual Cost |
> |---|---|---|---|
> | Dental Hygienist | Edgepulse | 2026-06-11 | $779,823.65 |
> | Paralegal | Voomm | 2026-06-11 | $95,103.45 |
> | Geological Engineer | Realbuzz | 2026-06-12 | $133,353.76 |
> | Occupational Therapist | Fanoodle | 2026-06-17 | $132,126.71 |
> | Quality Engineer | Brainsphere | 2026-06-17 | $844,932.35 |
> *[source: `contracts` table, rows keyed by (Vendor + End Date); full 38-row list available]*
>
> **On penalties:** I can't provide penalty or termination terms for these contracts — **the contract dataset has no penalty/termination field, and no vendor-contract documents are loaded** in this system. So while I can tell you exactly *what* expires and its annual value, the *penalty* terms aren't available from any source here. I won't guess them.

### Why this is golden (every claim traces; the limit is honest)

- **"38 contracts"** → SQL `COUNT(*)` over `End Date ∈ [2026-06-09, 2026-09-07]` — verified against the raw CSV at the pinned anchor.
- **"$18,924,883.79"** → SQL `SUM(Annual Cost)` over those 38 rows — verified.
- **Each table row** (Edgepulse 2026-06-11 $779,823.65, etc.) → a real line in `school data 1.csv`, cited to the **table + row key**.
- **The penalty statement** → an honest "not available", citing the **absence** (no penalty field, no contract documents) — NOT a fabricated clause and NOT text from the Carter PDFs.

> **Why penalties are unavailable (stated for the record):** the corpus's only documents are the Carter divorce case file and its story — there are **no vendor-contract documents**, and `school data 1.csv` has no penalty column. Penalty terms therefore have **no source**. The honest feature says so. (If vendor-contract documents are supplied later, the penalty half becomes a real RAG branch — see `01` deferrals.)

---

## Golden Example B — the same question in Hebrew (HE)

**Question:** *"אילו חוזים יפוגו ב-90 הימים הקרובים ומהם הקנסות המוגדרים באותם חוזים?"*

**The grounded answer (Hebrew), same facts, same honesty:**

> **38 חוזים יפוגו בין 2026-06-09 ל-2026-09-07** (90 הימים הקרובים), בערך שנתי כולל של **$18,924,883.79**. *[מקור: טבלת `contracts` (`school data 1.csv`)]*
> … (earliest-expiring table, same 5 rows) …
> **לגבי קנסות:** לא ניתן לספק תנאי קנס או סיום עבור חוזים אלה — **אין שדה קנס/סיום בנתוני החוזים, ולא נטענו מסמכי חוזה** במערכת. אדווח על התפוגה והעלות בלבד, ולא אנחש קנסות.

**Why this is golden:** the **numbers and citations are identical** to Example A (38, $18,924,883.79, the same rows) and the **honest penalty-unavailable statement survives translation** — the Hebrew path neither fabricates a penalty nor drops the honesty.

---

## Golden Example C — narrower window, single contract (still no penalty source)

**Question:** *"Tell me about the Skalith Project Manager contract expiring in July, including any early-termination penalty."*

**The grounded answer:**

> The **Project Manager / Skalith** contract expires **2026-07-09** with an annual value of **$25,629.50**. *[source: `contracts` table, row (Skalith, 2026-07-09)]*
> There is **no early-termination penalty information available** — the contract data has no penalty field and no contract document is loaded for this (or any) contract. I can report its dates and value, but not its penalty terms.

**Why this is golden:** it returns the **real structured facts** (expiry + value, cited to the row) and is **honest about the penalty gap** for an individual contract — neither fabricating a figure nor reaching into an unrelated document. Same trust property as `maintenance-spend-intelligence`'s no-fabrication gate.

---

## Toy-vs-real contrast (the line the gates enforce)

| Aspect | ❌ Toy / sub-par answer | ✅ Real / golden answer |
|---|---|---|
| **The count** | "Several contracts are expiring soon." | "**38 contracts** expire between 2026-06-09 and 2026-09-07." — a verifiable count from a real SQL filter at the pinned anchor. |
| **The rows** | "Various vendors including some healthcare and tech contracts." | Named rows with **vendor, role label, end date, annual cost**, each cited to a table row (Edgepulse 2026-06-11 $779,823.65 …). |
| **The penalty** | "Penalties typically include early-termination fees and notice periods." *(generic, ungrounded — the failure mode the client rejects)* — OR worse, a fabricated clause, OR text lifted from the Carter case file. | "**Penalty terms are not available** — no penalty field, no contract documents loaded." Honest about the absence; invents nothing; reaches into no unrelated source. |
| **Cross-domain leak** | Answers the penalty question with divorce-case content ("...the agreement orders a home sale within 12 months..."). **Catastrophic.** | **Never** surfaces Carter case text in a contract answer; the leak gate fails any answer that does. |
| **The defect** | Silently drops or "fixes" the End<Start rows; calls the job title a "Contract ID". | Treats the job title as a **role label**, **preserves** End<Start rows (e.g. Staff Scientist/Feedfish Start 2026-06-26 / End 2026-06-17), can flag the anomaly. |
| **Hebrew** | Hebrew answer changes the numbers or invents a penalty. | Hebrew answer carries the **identical** facts and the same honest penalty-unavailable statement. |
| **Determinism** | Count drifts day to day (wall clock). | Count is **38** at the pinned `asOfDate = 2026-06-09`; the screenshot pins to it. |

**The one-line acceptance bar:** *a golden contract answer states a verifiable count (38 at the pinned anchor) and lists real rows cited to the table with the correct total, **honestly states that penalty terms are not available** (no penalty field, no contract documents) rather than fabricating or cross-retrieving them, preserves the data's real defects, and does all of this in both English and Hebrew — never surfacing Carter case-file text.*

---

## Golden screenshots this feature needs (for the Engineer's `user-guide` + README ledger)

All screenshots are captured at the pinned `asOfDate = 2026-06-09` so the **38** count is stable.

| # | Screenshot | What it must show (golden data, not a toy) |
|---|---|---|
| 1 | `contract-90day-answer.png` | The assistant answering Example A: the **"38 contracts"** count, the **$18,924,883.79** total, the earliest-expiring rows table with **row citations**, and the **honest "penalties not available"** statement — all in one answer. |
| 2 | `contract-citations-expanded.png` | The citation panel/popover showing a **table-row citation** resolving to the real CSV row (proving citations are real and verifiable). |
| 3 | `contract-hebrew-answer.png` | Example B — the **same 38-count answer in Hebrew** with citations and the honest penalty statement intact. |
| 4 | `contract-single-no-penalty.png` | Example C — the single-contract answer (Skalith, $25,629.50, cited row) with the honest **"no penalty information available"** statement. |

Each must show the system **doing real work on the golden data** — never an empty form, a "no results" state, or a toy contract. The penalty-unavailable statement is part of the **working** headline answer (1), not a separate failure screen — the feature works and is honest about its one limit.
