# 01 — Design: Case File Q&A

Derived from: 00-research.md (the two Carter documents, page-level facts, the corroboration + filing-date conflict, the Page-24 Final Judgment).

> **What it does:** answers free-form questions about the Carter case by **document-only RAG** over the two case PDFs, grounding every answer in a **specific file + page/section citation**; corroborating findings across **both** documents where they agree; **surfacing conflicts** (the filing-date discrepancy) rather than silently resolving them; and answering "**not stated in the case file**" for anything the documents don't contain. English and Hebrew.

---

## The visible outcome (what the user SEES when it works)

A readable answer to a case question, with **each fact carrying a citation to the document and page/section** it came from (e.g. *"$1,285/month — Court Case File, Page 24, Final Judgment"*), clickable to the cited passage. For a corroborated finding, **two citations**. For the filing-date question, the answer **shows both dates with both citations and notes the discrepancy**. For an out-of-scope question, "not stated in the case file."

## The single workflow (single-spine)

| Step | Who/what | What happens | Output | Citation |
|---|---|---|---|---|
| **1. Ask** | user | free-form NL case question (EN/HE) | raw question | — |
| **2. Route** | LLM router | classifies as **RAG / documents only** (no SQL side for the case) | routing decision (`sources: [docs]`) | loggable |
| **3. RAG retrieve** | engine | embed the question; retrieve the relevant **page/section span(s)** from one or both PDFs | the retrieved spans + their locations | each span → **file + page/section** |
| **4. Compose (grounded)** | LLM | answer from the spans; cite each fact; if two docs corroborate, cite both; if they **conflict**, surface both with both citations; if not found, say "not stated in the case file" | the answer text | citations preserved, per-fact |
| **5. Render (EN/HE)** | UI | show answer + clickable citations; same for Hebrew | what the user sees | citations visible |

**Single golden scenario for `02`:** the **Final Judgment question** (child support $1,285/mo + primary residence, cited to Page 24), plus the **grounds question** (corroborated across both docs) and the **filing-date question** (conflict surfaced).

## Decisions & deferrals

- **Decision — citation is per-fact, to page/section.** Not "this answer came from the case file" but "**$1,285/month → Page 24, Final Judgment**." A finding without a page-level citation fails the bar.
- **Decision — corroboration cites both documents.** When the grounds appear in both PDFs, the answer cites both — stronger attribution, and it demonstrates multi-document retrieval (not single-doc lookup).
- **Decision — conflicts are surfaced, never silently resolved.** The filing date (10 Feb on the court cover vs Feb 3 in both narratives) is presented **with both citations** and an explicit note that the sources differ. The system does not pick one and hide the other.
- **Decision — out-of-scope → "not stated."** A question whose answer isn't in either document is answered "not stated in the case file," never invented. (Same trust property as the other two features.)
- **Decision — page numbers come from the document's own pagination.** The court file labels its sections by page ("Page 24 – Final Judgment"); citations use those labels so a human can verify against the real PDF.
- **Deferral — the Exhibits (A–F).** The case file lists exhibits (property deed, bank statements, credit-card records, therapy reports) but their contents aren't in the corpus. Questions about exhibit *contents* are answered "the exhibit is referenced but its contents aren't in the provided documents" — listed as a deferral, not fabricated.
- **Deferral — cross-case search.** Only one case is in scope; multi-case retrieval is a future slice (the architecture's extensibility covers it).

## Phased plan

- **R1 (this slice):** document-only RAG over the two PDFs — per-fact page citations, multi-document corroboration, conflict surfacing, "not stated" honesty, EN/HE.
- **R2 (deferred):** exhibit-content retrieval (if exhibits are digitized); multi-case search.

## Security / authorization

- **MVP scope:** single-tenant; the case documents are the client's own; the file is a mock. No per-row/per-doc access control required by the spec.
- **The integrity rule in scope:** every fact is attributed to the **document + page** that contains it; the system never invents a holding, never conflates the two documents into a false merged fact, and never silently resolves a conflict. For a legal-document product this **is** the security property — a confidently miscited or hallucinated legal finding is the worst possible failure. Enforced by `validateCaseAnswer()` + the citation-resolvability and conflict-surfacing gates in `03`.
- **Future (extensibility note):** when a case-management system is added (the spec's named future integration), each case/document carries its own access scope; the per-fact citation model is what makes per-document authorization addable later.
