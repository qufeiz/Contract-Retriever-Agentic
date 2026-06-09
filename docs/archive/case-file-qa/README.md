# Case File Q&A

Answers free-form questions about the Carter family-court case by document-only RAG over the two case PDFs, citing every fact to a **specific document + page** ( `[P:family-court#24]` = the Final Judgment), corroborating across both documents where they agree, **surfacing conflicts** (the filing-date discrepancy) rather than resolving them silently, and answering "not stated in the case file" for anything absent.

## Docs
- [00-research.md](00-research.md) · [01-design.md](01-design.md) · [02-examples.md](02-examples.md) · [03-tests.md](03-tests.md) · [04-implementation.md](04-implementation.md)
- [user-guide.md](user-guide.md) — the how-to.

## Screenshot / gate ledger

One row per capability → its golden screenshot (captured from the live app) → the journey gate that proves it.

| Capability | Screenshot | Gate (proves it works) |
|---|---|---|
| Final Judgment ($1,285 + Joni Carter), Page-24 cited | `images/case-final-judgment-answer.png` | `case-file-qa.spec.ts` (F-A) |
| Grounds corroborated across BOTH documents | `images/case-grounds-corroborated.png` | `case-file-qa.spec.ts` (F-B) |
| Filing-date conflict surfaced (Feb 10 vs Feb 3) | `images/case-filing-date-conflict.png` | `case-file-qa.spec.ts` (F-C) |
| Same Final Judgment answer in Hebrew | `images/case-hebrew-judgment.png` | `case-file-qa.spec.ts` (F-D) |

**Golden facts:** child support **$1,285/month** + primary residence **Joni Carter** on **Page 24** (Final Judgment); grounds corroborated across both PDFs; filing date conflicts (10 Feb cover vs 3 Feb narratives) — surfaced, not resolved. The Final Judgment is cited only to the court file, never the story PDF (C2).
