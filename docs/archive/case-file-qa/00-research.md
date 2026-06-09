# 00 — Research: Case File Q&A

Derived from: the problem (JOB_DESCRIPTION.md example question 3's *shape* — "summarize from documentation, with risks/findings, cited" — and the "source attribution" requirement) + first-hand inspection of `data/📄 FAMILY COURT CASE FILE (MOCK).pdf` and `data/story if the Carters.pdf`.

> **The domain truth: legal/case Q&A is the canonical document-grounded retrieval problem — the answer is a *specific finding on a specific page*, and being wrong about which page (or conflating two documents) is the whole failure mode. This is pure RAG (no SQL side), with citation-to-page as the non-negotiable bar, plus multi-document corroboration and honest surfacing of conflicting sources.**

---

## 1. Why this feature exists (mapping spec Q3's shape onto the data we have)

Spec Q3: *"Show all active projects and summarize the risks mentioned in their documentation."* We have **no projects table** and **no per-project risk documents** — so Q3 can't be answered literally. But its *shape* — **retrieve from documents, summarize, attribute risks/findings to their source** — is exactly served by the **only rich document set we were given: the Carter family-court case file.** So `case-file-qa` delivers Q3's capability (document-grounded, cited summarization of findings/risks) over the real documents we have. (The choice and its rationale are recorded in `docs/product/feature-map.md`.)

## 2. The two documents (inspected page by page)

We have **two documents about the same case**, which is ideal — it lets us demonstrate **multi-document corroboration** and **conflict surfacing**, not just single-doc lookup:

**A. `📄 FAMILY COURT CASE FILE (MOCK) – FINAL VERSION.pdf`** (the exact filename — cite it in full, including "– FINAL VERSION") — a structured, **page-numbered** court file (Maricopa County, AZ; Case No. **FC-2026-10458**). **This is the ONLY document that contains the Final Judgment (Page 24); the story PDF does NOT.** Sections are explicitly paginated:
- Cover (Case No., **"Filed: 10 February 2026"**, Judge Hon. Rebecca Lawson)
- Page 3 Case Summary; Pages 4–5 Parties (Joni Carter, 44, Marketing Consultant, Petitioner; Michel Carter, 46, Construction Project Manager, Respondent)
- Page 6 Children (Emma 11, Noah 8, Olivia 5)
- Pages 11–14 Grounds (2018 gambling discovery → 2019–2023 addiction escalation → 2023 alcohol + **domestic incident** → failed recovery → 2026 decision to separate)
- Page 15 Financial Disclosure (Joni $95,000; Michel $130,000)
- Pages 16–18 Assets (Home $620,000; Savings $74,500; Investments $112,000; Vehicles $50,000)
- Page 19 Debt (Mortgage $280,000; Credit $11,850; Loans $9,400)
- Pages 20–21 Parenting Plan; Page 22 Child Impact; Page 23 Court Findings (draft)
- **Page 24 Final Judgment** — *Marriage dissolved; Joint custody; Primary residence Joni Carter; Asset division equal split; **Child support $1,285/month**; Home sale ordered within 12 months.*
- Exhibits A–F.

**B. `story if the Carters .pdf`** (exact filename — note the space before `.pdf`) — a 3-page **narrative** of the same case with extra biographical detail: marriage **June 14, 2014** in Phoenix; children Emma (2015), Noah (2018), Olivia (2021); the same grounds timeline with quotes from Joni; the **five enumerated reasons for divorce**; the **decision to file on February 3, 2026**; locations (family home 2458 Desert Willow Drive; Phoenix Recovery Center / Desert Horizon Therapy; Desert Ridge Elementary).

## 3. The corroboration + conflict findings (the reason two documents matter)

- **Corroboration:** the grounds (gambling addiction → escalation → alcohol → domestic incident → failed recovery) appear in **both** documents — a real document-QA system can cite *both* sources for a corroborated finding, which is stronger than one.
- **A real conflict to surface (the discriminating golden detail):** the **filing date** differs — the court file cover says **"Filed: 10 February 2026"**, while both the court file's own grounds narrative ("Joni Carter filed for divorce on February 3, 2026") and the story PDF ("On February 3, 2026… Joni filed") say **February 3, 2026**. A trustworthy system **surfaces the discrepancy and cites both**, rather than silently picking one. This is a high-value test of "source attribution you can trust."

## 4. How legal/case document Q&A works in the real world

- **Legal-research / e-discovery tools** (Everlaw, Relativity, Casetext/CoCounsel) ground every answer in a **specific document + page/section** and let the user jump to the cited passage — citation-to-passage is the entire trust model; an uncited legal "answer" is useless and dangerous.
- **The failure modes they guard against** are exactly ours: (a) stating a finding with **no page citation**; (b) **conflating** two documents into one false fact; (c) **hallucinating** a holding the document doesn't contain; (d) silently resolving a **conflict** between sources. Each maps to a gate in `03`.
- This is **pure RAG** — there is no structured table for the case; the answer is a retrieved-and-grounded document span, never a SQL row.

## 5. Implications for design (handed to `01`)

1. Document-only RAG over the two PDFs; **every answer cites file + page/section.**
2. **Multi-document corroboration**: a corroborated finding cites **both** documents.
3. **Conflict surfacing**: the filing-date discrepancy must be surfaced and dual-cited, not silently resolved.
4. **No hallucination**: a fact not in either document is answered "not stated in the case file," never invented — the same trust property as the other two features.
5. The headline golden fact is the **Final Judgment on Page 24** (child support **$1,285/month**, primary residence Joni) — the most-cited, most-verifiable fact in the corpus.
