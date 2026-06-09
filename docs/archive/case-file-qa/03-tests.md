# 03 — Acceptance Gates: Case File Q&A

Derived from: 01-design.md §workflow (steps 1–5 → one gate per step) + 02-examples.md (Examples A/B/C/D → one fixture per example).

> **The gate list — *what* to assert.** The Engineer writes the runnable tests at build. Every gate is **removable-handler-proof**: stub the retriever/composer to a no-op or to a plausible hallucination and the gate must go **red**. The defining gates here are **citation-resolvability** and **conflict-surfacing** — the trust properties of a legal-document product.

---

## Part 1 — A gate per workflow step (from `01`)

| # | Workflow step | Gate — what it asserts | Removable-handler proof |
|---|---|---|---|
| **G1** | 1. Ask | EN and HE case questions are accepted and reach the router. | Reject HE → G1 red. |
| **G2** | 2. Route | A case question routes to **`docs` only** (no SQL side). | Make it route to SQL / return a table row → G2 red. |
| **G3** | 3. RAG retrieve | The Final-Judgment question retrieves the **Page 24** span; the grounds question retrieves spans from **both** documents. | Stub retrieval to empty → G3 red. Stub it to return only one doc for grounds → corroboration gate (F-B) red. |
| **G4** | 4. Compose (grounded) | The answer states the exact finding, **cites file + page/section per fact**, corroborates across both docs where they agree, and **surfaces the filing-date conflict with both citations**. | Replace compose with an uncited summary, or one that picks a single filing date → G4 red. |
| **G5** | 5. Render EN/HE | The HE answer carries the **same finding + Page-24 citation** as EN. | HE path drops the citation or changes $1,285 → G5 red. |

## Part 2 — A fixture per golden example (from `02`)

| # | Fixture | Assertion | Removable-handler proof |
|---|---|---|---|
| **F-A** | Example A (Final Judgment, EN) | Answer contains **"$1,285"** (per month) + **"primary residence … Joni Carter"** + a **Page 24 / Final Judgment** citation. | A vague "some child support, custody to the mother" answer fails F-A. |
| **F-B** | Example B (corroborated grounds) | Answer cites **both** the court file (Pages 11–14) **and** the story PDF for the grounds. | A single-source or uncited grounds answer fails F-B. |
| **F-C** | Example C (conflict) | Answer surfaces **both** "10 February 2026" (cover) **and** "February 3, 2026" (narratives) with **both citations**, and notes the conflict. | An answer giving only one filing date fails F-C. |
| **F-D** | Example D (HE Final Judgment) | The HE answer contains **$1,285** + the **Page-24** citation. | A HE answer that drops the citation or changes the figure fails F-D. |

## Part 3 — `validateCaseAnswer()` — the content-fidelity gate

A **pure function** the Engineer builds, run in the answer path, pinned by a unit test that **passes every golden answer (A–D) and fails every toy answer**. Rules:

1. **Per-fact page citation** — every stated case finding carries a **document + page/section** citation; a finding with no page-level citation fails. *(no "according to the case file" without a page.)*
2. **No hallucinated holding** — a checklist of facts NOT in the documents (e.g. "spousal support", an invented dollar figure) must NOT appear as stated findings. A small adversarial set of "not in the documents" claims is asserted absent.
3. **Corroboration distinctness** — when two documents are cited, they are cited as **two distinct sources**, not merged into one.
4. **Conflict surfacing** — for the filing-date question, BOTH dates and BOTH citations are present; an answer with only one filing date fails.
5. **"Not stated" honesty** — an out-of-scope question (e.g. an exhibit's contents) yields a "not stated in the case file" response, not an invented fact.

> **Why this gate (separate from removable-handler):** removable-handler proves the retriever ran; it **passes** a fluent hallucination ("spousal support $2,000/month") and a citation-free summary. For a legal-document product, an uncited or hallucinated holding is the catastrophic failure. `validateCaseAnswer()` makes "cited and not hallucinated" a **red unit test**. **Required.**

## Part 4 — Citation-integrity gate (cross-cutting)

| # | Gate | Assertion |
|---|---|---|
| **C1** | Resolvability | Every citation resolves to a real **file + page/section** in the corpus — the **exact filename** (`📄 FAMILY COURT CASE FILE (MOCK) – FINAL VERSION.pdf` or `story if the Carters .pdf`) and a page label that exists in that PDF. A citation to a nonexistent page or a wrong/abbreviated filename → gate red. |
| **C2** | No document conflation / correct-source | A fact from the story PDF is not attributed to the court file (or vice-versa); each citation matches the document the span actually came from. **In particular, the Final Judgment (Page 24, child support $1,285) must be cited to `📄 FAMILY COURT CASE FILE (MOCK) – FINAL VERSION.pdf`, NEVER to the story PDF** (the story does not contain the Final Judgment). An answer citing the Final Judgment to the story → gate red. |
| **C3** | Conflict not silently resolved | The filing-date discrepancy is surfaced (covered by F-C) — a regression that starts auto-picking one date trips this gate. |

## Part 5 — Generic SWE + prod-verify

- **PDF-pagination unit test:** assert the page labels the citations use (e.g. "Page 24 – Final Judgment", "Pages 11–14 – Grounds") exist in the parsed document, so a citation can't point at a page the document doesn't have.
- **Retrieval determinism on the golden Qs:** the Final-Judgment question reliably retrieves the Page-24 span (assert the retrieved span contains "$1,285").
- **Journey test (Phase 5, committed permanently):** drive the real UI — ask the Final-Judgment question → assert the rendered answer shows **$1,285**, **Joni Carter**, and a clickable **Page 24** citation; ask the grounds question → assert **two** citations; ask the filing-date question → assert **both** dates surfaced; repeat the Final-Judgment question in Hebrew. Seed the document corpus via `ensure*`; **no graceful skips**.

### Prod-verify runbook (post-deploy)
1. Ask the Final-Judgment question (EN) → confirm $1,285/month, primary residence Joni Carter, Page-24 citation.
2. Ask the grounds question → confirm both documents cited.
3. Ask the filing-date question → confirm both Feb 10 and Feb 3 surfaced with citations.
4. Ask the Final-Judgment question in Hebrew → confirm $1,285 + Page-24 citation.
5. Click each citation → confirm it opens/points to the real page.
6. Ask an out-of-scope question (e.g. "what's in Exhibit C?") → confirm "not stated", no fabricated contents.
7. If any finding lacks a page citation, any citation 404s, the filing-date conflict is silently resolved, or any hallucinated holding appears → **fail**, do not sign off.
