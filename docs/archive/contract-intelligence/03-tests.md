# 03 — Acceptance Gates: Contract Intelligence

Derived from: 01-design.md §workflow (steps 1–5 → one gate per step) + 02-examples.md (Examples A/B/C → one fixture per example).

> **This is the gate list — *what* to assert, not the runnable test.** The Engineer writes the runnable journey/unit tests at build (Phase 5) and commits them as permanent regression gates. Every gate below is **removable-handler-proof**: if the handler it covers is stubbed to a no-op (or to a plausible toy), the gate must go **red**. A gate that still passes against a gutted/fabricated answer is not a gate.

> **Pinned anchor:** all expiry assertions use the injected **`asOfDate = 2026-06-09`** (window `[2026-06-09, 2026-09-07]`). The count **38** holds ONLY at this anchor; the fixture freezes it.

---

## Part 1 — A gate per workflow step (from `01`)

| # | Workflow step (`01`) | Gate — what it asserts | Removable-handler proof (break this → gate goes red) |
|---|---|---|---|
| **G1** | 1. Ask | A free-form EN question and its HE equivalent are both accepted and reach the router (no language-based rejection). | Force HE input to error → G1 red. |
| **G2** | 2. Route | The router classifies the spec Q1 as needing **`sql`** for expiry/cost and marks penalty **unavailable** (`{sources: [sql], penalty: "unavailable"}`). It must NOT route the contract question to the Carter documents. | Make the router send the contract question to `docs` / the Carter corpus → G2 red (cross-domain leak). |
| **G3** | 3. SQL retrieve | SQL over the contracts table for `End Date ∈ [2026-06-09, 2026-09-07]` (injected `asOfDate`) returns **exactly 38 rows** and `SUM(Annual Cost) = 18924883.79`. | Change the window filter, drop the `asOfDate` injection, or return all rows → count ≠ 38 → G3 red. |
| **G4** | 4. Compose (grounded) | The composed answer contains **the count (38)**, **the $18,924,883.79 total**, **≥1 cited table row**, and an explicit **"penalty terms not available"** statement. It contains **no fabricated penalty** and **no Carter case-file text**. | Replace compose with "Several contracts are expiring" (no count) → G4 red. Inject a fabricated penalty or any Carter text → G4 red (via Part 3 + Part 4). |
| **G5** | 5. Render EN/HE | The HE answer carries the **same numbers and citations** and the **same honest penalty-unavailable statement** as the EN answer (38, $18,924,883.79, the same row citations). | Make the HE path drop citations, change the count, or fabricate a penalty → G5 red. |

## Part 2 — A fixture per golden example (from `02`)

| # | Fixture (golden example) | Assertion | Removable-handler proof |
|---|---|---|---|
| **F-A** | Example A (EN headline) | Answer states **"38 contracts"**, the **$18,924,883.79** total, lists ≥5 real rows each cited to a table row, AND states **penalty terms are not available** (no penalty field, no contract documents). Contains **no** penalty figure and **no** Carter case-file text. | A toy answer ("several contracts, penalties typically include fees") fails F-A; an answer that invents a penalty or quotes the divorce case fails F-A. |
| **F-B** | Example B (Hebrew) | The HE answer asserts the **identical** 38 / $18,924,883.79 / same row citations and the same honest penalty-unavailable statement. | A HE answer that changes a number, drops a citation, or fabricates a penalty fails F-B. |
| **F-C** | Example C (single contract, no penalty source) | For the Skalith contract, the answer returns the **real expiry (2026-07-09) + value ($25,629.50) cited to the row** AND says **penalty information is not available**; it contains **no** fabricated penalty figure and **no** cross-domain text. | An answer that invents a penalty number for Skalith, or pulls Carter text, fails F-C. |

## Part 3 — The content-fidelity gate (`validateContractAnswer()`) — the toy-vs-real enforcer

A **pure function** the Engineer builds (template: the RFI `validateX` pair) that encodes the `02` acceptance bar, run in the answer path and pinned by a unit test that **passes every golden answer (A/B/C) and fails every toy answer**. Rules (domain-specific, structural):

1. **Verifiable count present** — the answer about expiry contains a specific integer count, not a vague quantifier ("several", "various", "some"). *(stop-list of vague quantifiers when a count is expected.)*
2. **Row citations present** — ≥1 listed contract carries a table+row citation; listed vendors/dates/costs must match real CSV rows (no invented vendor).
3. **Penalty is honestly unavailable** — any penalty/termination mention is the **"not available"** statement (no penalty field, no contract documents). A penalty **figure or clause** of any kind **fails** (there is no source for it) — this covers both the generic-prose failure ("penalties typically include…") and any fabricated specific clause.
4. **No cross-domain content** — the answer contains **no** text/entities from the Carter case corpus (e.g. "child support", "Joni", "custody", "Final Judgment", "home sale within 12 months"). A contract answer carrying divorce-case content fails. *(stop-list of Carter-case tokens.)*
5. **Defect honesty** — the answer does not relabel the role/job-title field as a "Contract ID"; End<Start rows are not silently dropped from a count that claims to be "all expiring."

> **Why this gate exists (separate from removable-handler):** removable-handler proves the handler *did something*; it **passes** for a real-but-generic answer ("penalties typically include early-termination fees") and even for a confident cross-domain hallucination. Those are exactly what the client rejects. `validateContractAnswer()` makes "real, honest, no leak" a **red unit test** instead of a judgment call. **Required** — this feature transmits human-read content.

## Part 4 — The cross-domain-leak + citation-integrity gate

| # | Gate | Assertion |
|---|---|---|
| **J1** | **No cross-domain leak (the worst-case gate)** | A contract question must **never** be answered with content retrieved from the Carter case documents. A test asks the penalty question and asserts the answer contains **zero** Carter-case tokens (child support / custody / Joni / Michel / Final Judgment / divorce). Answering a contract penalty question with divorce content → gate red. This is the worst-case hallucination and is the single most important contract gate. |
| **J2** | Citation resolvability | Every citation resolves to a real artifact: a table+row key that exists in `school data 1.csv`. A citation to a nonexistent row → gate red. (No document citations exist in this slice — penalties are "not available.") |
| **J3** | No-source honesty | The penalty half is always the **"not available"** statement and contains **zero** penalty figures or clauses attributed to any source — verified by F-A/F-C and `validateContractAnswer()` rules 3–4. |
| **J4** | **No contract-terms document citation (none exists)** | A contract answer must cite **no contract-terms / agreement / clause document at all** — `data/` contains **no such file** (verified: only `school data 1.csv` + the two Carter PDFs). A test asserts no contract answer references a `*contract*.pdf` / `*terms*.pdf` / `*agreement*.pdf` source (or any document for a penalty). Any such citation → gate red. This directly prevents the "cite an invented document" failure. |

## Part 5 — Generic SWE + prod-verify

- **Anchor-date determinism:** the `asOfDate` for the 90-day window is **injected** (fixed to 2026-06-09 in the test) so the golden count stays **38**; the prod path may pass a real `asOfDate`. A test asserting "38" against the wall clock would rot — assert the **pinned anchor** in CI, and assert the **mechanism** (count = rows where End ∈ [asOfDate, asOfDate+90d]) for any other date.
- **Ingestion preserves defects:** a unit test asserts End<Start rows survive ingestion (count of such rows > 0) and are not auto-corrected.
- **Journey test (Phase 5, committed permanently):** drive the real UI at the pinned anchor — type Q1, assert the rendered answer shows "38", the $18,924,883.79 total, a cited row, the "penalty not available" statement, and **no Carter content**; repeat for the Hebrew question (F-B) and the single-contract case (F-C). Seed the contract data via an `ensure*` helper; **no graceful skips**.

### Prod-verify runbook (post-deploy)
1. Open the deployed assistant; ask the EN Q1 (at the pinned anchor) → confirm "38", the total, cited rows, and the honest "penalty terms not available" statement.
2. Ask the HE Q1 → confirm identical numbers + citations + honest penalty statement.
3. Ask Example C's Skalith question → confirm real expiry + value cited, "penalty not available", no fabricated figure.
4. Click a citation → confirm it resolves to the real CSV row.
5. **Leak check:** confirm none of the contract answers contain any Carter case-file content.
6. If any citation 404s, any count ≠ 38 at the pinned anchor, any penalty figure/clause appears, or any Carter content leaks into a contract answer → **fail**, do not sign off.
