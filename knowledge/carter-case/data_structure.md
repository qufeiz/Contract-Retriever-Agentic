# Carter Family-Court Case — documents (PDF)

| File | What it is | Notes (read before you answer) |
|---|---|---|
| `family-court-case-file.pdf` | The MOCK family-court case file (Case FC-2026-10458), 24 pages, page-numbered | The ONLY document containing the **Final Judgment on Page 24** (child support **$1,285/month**, primary residence **Joni Carter**, joint custody, equal asset split, home sale within 12 months). The **cover sheet (Page 1)** lists "Filed: 10 February 2026". |
| `case-story.pdf` | A 3-page narrative of the same case | Corroborates the grounds for divorce; states Joni filed on **February 3, 2026** ("Decision to File for Divorce"). |

## Known facts to cite precisely
- The **Final Judgment lives ONLY in `family-court-case-file.pdf` Page 24** — never cite it to the story PDF.
- **FILING-DATE CONFLICT (real):** the cover sheet says "10 February 2026" but the court file's grounds narrative AND `case-story.pdf` say "February 3, 2026". **If asked the filing date, you MUST open AND read BOTH `family-court-case-file.pdf` AND `case-story.pdf`** — the conflict can only be confirmed by checking both documents, and the answer must cite both. Do not answer the filing date from the court file alone. SURFACE BOTH dates; do not silently pick one. **Cite the conflict as:** the cover-sheet date → `family-court-case-file.pdf` **printed PAGE 1 (the cover sheet)** `#p1`; and the February 3 date → **`case-story.pdf`** (the corroborating narrative). The court file's grounds-narrative Feb-3 text sits between printed labels and has NO printed PAGE label of its own — so do NOT cite it to an invented court-file page number; cite the story PDF for Feb 3 instead.
- Use `pdftotext` then grep; cite file + page. The document labels its pages with printed
  "📑 PAGE N – TITLE" headers; **only cite a `#p<N>` that is an ACTUAL printed PAGE-N label** you
  saw in the extracted text (e.g. `#p24` for the Final Judgment, `#p1` for the cover). If your fact
  falls under a printed label, cite that N; if it has no printed label of its own, cite the file/
  document that DOES carry a clean page (e.g. the story PDF) — never invent a page number.
