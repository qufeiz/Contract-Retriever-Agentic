# Agentic Knowledge Assistant

Answers a free-form business question (EN/HE) by running a **Claude Agent SDK loop** that navigates a `knowledge/` tree via human-readable `data_structure.md` maps (the index — **no embeddings**), reads a processing reference before touching a CSV/PDF, extracts with **pandas / pdftotext+pdfplumber** (progressive grep + local reads), runs a **falsification-view self-check**, and returns a **grounded answer with inline citation chips** + a **visible trace** of which files it consulted — in the copied "Aletheia" UI. Cite every claim to a resolvable file+page/section; honest "not available" instead of fabricating; surface conflicts; never join the school↔Carter domains.

This is a **re-platforming** of the shipped `Contract-Retriever-RAG` onto the user's kb-retriever agentic pattern — same product, same data, same four golden questions, same UX; only the retrieval engine changes. The parent repo + deployment stay live and untouched.

## Docs
- **PM-authored (the design + golden bar + gate list):** [00-research.md](00-research.md) · [01-design.md](01-design.md) · [02-examples.md](02-examples.md) · [03-tests.md](03-tests.md)
- **Engineer-authored (build):** [04-implementation.md](04-implementation.md) · [user-guide.md](user-guide.md)

## Screenshot / gate ledger

One row per capability → its golden screenshot (captured by the Engineer from the live app at the pinned anchor `2026-06-09`) → the eval gate that proves it. The screenshots and the runnable eval harness are **Engineer deliverables**; the rows below are the bar the PM set in `02`/`03`.

| Capability | Screenshot | Gate (proves it works) |
|---|---|---|
| Contract expiry: 38 / $18,924,883.79, cited rows, honest "penalties not available", trace shows `contracts.csv` only | `images/g1-contract-90day-answer.png` | eval `F-G1` + trace `T1/T2` |
| A citation chip resolves to the real `contracts.csv` row | `images/g1-citation-resolves.png` | eval `F` citation-resolvability |
| Carter Final Judgment: $1,285/mo + primary residence Joni Carter, cited Page 24 | `images/g2-final-judgment-answer.png` | eval `F-G2` |
| Maintenance overdue: honest refusal (schema-cited) + $40,597.00 pivot | `images/g3-overdue-honest-refusal.png` | eval `F-G3` |
| Filing-date conflict surfaced: both Feb 10 and Feb 3, both cited, both PDFs opened | `images/g4-filing-date-conflict.png` | eval `F-G4` + trace `T1` |
| Carter judgment in Hebrew — identical $1,285 / Page-24 | `images/g2-hebrew-judgment.png` | eval `F-G2-HE` |

**Golden facts pinned at `asOfDate=2026-06-09`:** 38 contracts expiring, combined annual value **$18,924,883.79**; maintenance total **$40,597.00 / 750**; Carter child support **$1,285/month** (Page 24); filing-date conflict **Feb 10 (cover) vs Feb 3 (body+story)**. The cross-domain trace guard (`T2`) + stop-list keep the two domains from ever leaking into each other's answers.
