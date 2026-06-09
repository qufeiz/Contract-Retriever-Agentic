# 01 — Design: Contract Intelligence

Derived from: 00-research.md (the structured contract data + the verified 38-contract / $18.9M window at the pinned anchor date + the data defects + the fact that NO penalty source exists in the corpus).

> **What it does:** answers free-form questions about vendor-contract **expiry, vendor, and annual cost** by routing to **SQL** over `school data 1.csv`, composing a grounded answer with each fact **cited to its table row**; and, because **no penalty/termination document exists in the corpus**, it **explicitly states that penalty terms are not available** when asked the spec's Q1 — it does **not** fabricate penalties and does **not** answer a contract question with text from an unrelated document (the Carter case file). English and Hebrew.

> **Anchor date (pinned, deterministic):** the "next 90 days" window is computed from a single **injected `asOfDate = 2026-06-09`**, NOT the wall clock. The golden count (**38**) and the golden screenshot are pinned to this date. The window is `End Date ∈ [2026-06-09, 2026-09-07]`. `03` asserts the count holds only at this anchor (it would differ at any other date); the prod path may pass a real `asOfDate`, but the test fixture and the demo freeze it.

---

## The corpus reality that shapes this feature (read first)

The only documents loaded in this MVP are the **Carter family-court case file** and its **narrative story** — there are **no vendor-contract documents at all**, and `school data 1.csv` has **no penalty column** (see `00`). Therefore:
- The **expiry/vendor/cost** half of the spec's Q1 is fully answerable from SQL.
- The **penalty** half is **answerable from no source whatsoever**. The honest answer states this plainly.
- A contract question must **never** retrieve from the Carter documents to "find" a penalty — answering a contract penalty question with divorce-case text would be the worst-case cross-domain hallucination. This is a hard gate (`03` Part 4).

## The visible outcome (what the user SEES when it works)

The user asks the spec's Q1 and sees, within a few seconds, **one answer** that contains:
1. A **count and list** of expiring contracts ("**38 contracts expire between 2026-06-09 and 2026-09-07**", with sample rows: vendor, role label, end date, annual cost), each row carrying a **table/row citation**, plus the **combined annual value ($18,924,883.79)**.
2. An explicit, honest statement that **penalty/termination terms are not available** — there is no penalty field in the contract data and no contract documents are loaded — so the penalty half of the question cannot be answered, and **no penalty is invented**.

Not "a row count in the DB", not a fabricated penalty clause — a readable, cited answer a contract manager could act on, honest about its one limit.

## The single workflow (single-spine)

This feature is **single-spine**: one ordered sequence the user follows. Branches (Hebrew, a narrower window like 30 days) hang off it.

| Step | Who/what | What happens | State / output | Citation produced |
|---|---|---|---|---|
| **1. Ask** | user | free-form NL question, EN or HE, naming a horizon ("next 90 days") and (often) the penalty ask | the raw question | — |
| **2. Route** | LLM router | classifies: the expiry/cost part needs **SQL** over the contracts table; the penalty part maps to **no available source** → the **penalty-unavailable** branch. The router must NOT route a contract question to the Carter documents. | a routing decision (`sources: [sql]`, `penalty: unavailable`) | the routing decision is loggable |
| **3. SQL retrieve** | engine | query the contracts table for `End Date ∈ [asOfDate, asOfDate+90d]` (asOfDate=2026-06-09); return rows (vendor, role label, start, end, annual cost) + the count + SUM(annual cost) | the expiring-contract rowset (38 rows; total $18,924,883.79) | each row → **table + row key** |
| **4. Compose (grounded)** | LLM | summarize the rowset with cited rows + the count + total; **state that penalty terms are not available** (no penalty field, no contract documents); do not fabricate or cross-retrieve | the final answer text | row citations preserved; penalty explicitly "not available" |
| **5. Render (EN/HE)** | UI | show the answer with visible citations; same flow for a Hebrew question/answer | what the user sees | citations visible in the UI |

**Single golden scenario for `02`:** the spec's Q1 over the pinned window — "What contracts expire in the next 90 days and what penalties are defined in those contracts?" — producing the 38-contract list with row citations, the $18,924,883.79 total, **and the explicit "penalties not available" statement**.

## Decisions & deferrals

- **Decision — penalties are honestly unavailable, not fabricated and not cross-retrieved.** There is no penalty column and no contract document in the corpus, so the penalty half of Q1 is answered "not available." The system must **never** invent a penalty figure and must **never** surface Carter divorce-case text in a contract answer. → enforced in `03` (`validateContractAnswer` rule + the **cross-domain-leak** gate).
- **Decision — `Contract ID` is treated as a `role label`, not an identifier.** Rows are keyed by (Vendor + End Date) / row index. The UI must not call the job title a "contract number."
- **Decision — data defects are preserved and flagged, not cleaned.** End<Start rows stay in the dataset and remain answerable; the system may flag them but must not drop or silently correct them.
- **Decision — the 90-day window is computed from an injected `asOfDate = 2026-06-09`, frozen in the test fixture and the demo** so the golden count (38) and the screenshot are deterministic (see `03`).
- **Deferral — penalty/termination answering.** Genuinely answering "what's the penalty" requires vendor-contract **documents** (signed contracts with clauses) that **the corpus does not contain — there is no contract-terms document of any kind in `data/`** (verified: the only PDFs are the Carter case file + story). So in this slice the penalty half is **always** the honest "not available," never a document citation. *If* such documents are supplied in a future slice, this becomes a real RAG branch (penalty clause cited to its real document span) — the architecture's hybrid path already supports it. Deferred for **lack of source documents**, not lack of capability; **we do not synthesize a placeholder contract-terms document to fill the gap** (a fabricated source in a deliverable about honest grounding is itself a fabrication).
- **Deferral — auto-renewal/notice-window detection** (flagging contracts that auto-renew unless cancelled) — a real CLM feature, but needs renewal-term fields/clauses we don't have. Listed, not built.

## Phased plan

- **R1 (this slice):** route → SQL expiry list (count + total + cited rows) → grounded answer with the **honest penalty-unavailable** statement, EN/HE, over the pinned window (38 contracts).
- **R2 (deferred):** penalty/termination RAG branch (when vendor-contract documents exist); auto-renewal/notice detection; a 30/60/90 horizon selector.

## Security / authorization

- **MVP scope:** single-tenant client deliverable; no per-row access control required by the spec. The contract data is the client's own.
- **The integrity rules that ARE in scope:**
  1. The answer must never **attribute a fact to a source that doesn't contain it** (a fabricated penalty, a fabricated row).
  2. **No cross-domain leak** — a contract question must never be answered with text retrieved from the Carter case documents. A penalty question answered with divorce-case content is the worst-case hallucination and **must fail** (`03` Part 4). This makes contract-intelligence's trust story consistent with maintenance-spend's honest-refusal property: when the source for the asked concept doesn't exist, say so — never reach into an unrelated source.
- **Future (noted for architecture extensibility):** when CRM/email/cloud or real contract-document sources are added, each carries its own access scope and the router maps the penalty concept to its real source; the per-fact citation model is what makes per-source authorization and the leak-guard addable later.
