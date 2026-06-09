# 04 — Implementation: Case File Q&A

Derived from: 01-design.md (workflow steps 1–5 + decisions/deferrals) + 03-tests.md (the gate list this build satisfies).

The build doc: the document model the feature reads, the build order, and the deploy gate. Shared engine internals: [../shared-engine/reference.md](../shared-engine/reference.md).

## Document model (RAG, not SQL)

Two PDFs are chunked + locally embedded into the vector index (`scripts/build-index.mts` via `lib/engine/pdf.ts` + `documents.ts`):

| `doc` id | File | Citation form | Notes |
|---|---|---|---|
| `family-court` | `📄 FAMILY COURT CASE FILE (MOCK) – FINAL VERSION.pdf` | `[P:family-court#<page>]` | Cited by the document's **own printed page** (e.g. Page 24 = Final Judgment), not the physical pdftotext page |
| `carter-story` | `story if the Carters .pdf` | `[P:carter-story#<page>]` | The narrative; has no printed pagination → physical pages |

**Printed-page citations (the key build detail):** the court file prints `PAGE N – SECTION` headers. `pdfToChunks()` re-segments the extracted text on those markers so a chunk's `page` is the **document's own page number** — the number a human verifies against the real PDF. The $1,285 Final Judgment is on printed **Page 24**, so it cites `[P:family-court#24]`, not the physical page (6) where pdftotext placed it.

## Build order (R1 — this slice)

1. **PDF chunking** (`lib/engine/pdf.ts`) — `splitByPrintedPages()` cites the document's printed page; the story (no printed pages) falls back to physical pages.
2. **Retrieval** (`lib/engine/answer.ts`) — case (document-only) turns retrieve across **both** PDFs (no doc filter) and `diversifyByDoc()` guarantees cross-document coverage, so corroboration and conflict-surfacing are possible (locking to one doc would defeat both).
3. **Grounding** (`lib/engine/answer.ts`) — the prompt instructs: cite each fact to its page; **corroborate** across documents where they agree; **surface conflicts** (the Feb-10 cover vs Feb-3 narrative filing date) instead of silently picking one; answer "not stated in the case file" when absent.
4. **Feature gate** (`lib/engine/validate-case-answer.ts`) — `validateCaseAnswer()`: page citation present, no `[S:]` tokens (document-only), no hallucinated holding (spousal support / sole custody stop-list), conflict-not-corroborated. Merged into the response `validation`.

## Tests this build satisfies (from `03`)

- **Unit:** `tests/unit/validate-case-answer.test.mts` (passes A–D goldens; fails toys: uncited finding, hallucinated spousal support, silently-resolved conflict, `[S:]` token) + `tests/unit/pdf-pagination.test.mts` (Page 24 has $1,285; the story PDF does not — C2 no-misattribution).
- **Journey (permanent gate):** `tests/journeys/case-file-qa.spec.ts` — F-A ($1,285 + Joni Carter, `[P:family-court#24]`), F-B (grounds cited to both docs), F-C (filing-date conflict surfaced), F-D (Hebrew). Runs against the live deploy.

## Deploy / migration gate

- **PDF text is pre-extracted** to `data/pdf-pages.json` (committed) so the poppler-less Vercel build can chunk + embed without `pdftotext`. Re-run `scripts/extract-pdf-text.mts` if the source PDFs change. → [../../gotchas/sqlite-on-serverless.md](../../gotchas/sqlite-on-serverless.md) (the same deploy-build constraint).
- **The vector index** (`data-index/vectors.json`) is rebuilt at deploy by `build:index`. The printed-page chunking must run before the read path — it's all in the same build step.
- **Post-deploy verify:** run `03` Part 5's runbook (Final Judgment EN/HE; grounds → both docs; filing date → conflict; click a citation; out-of-scope → "not stated").
