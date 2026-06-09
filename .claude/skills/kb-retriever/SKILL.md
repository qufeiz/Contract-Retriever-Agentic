---
name: kb-retriever
description: Retrieval and Q&A assistant over a local knowledge-base directory. Core method — (1) navigate hierarchical data_structure.md maps, (2) when you hit a PDF/CSV you MUST read the matching processing reference IN FULL before processing it, (3) process the file, then retrieve. Combine grep, Read, pandas (CSV), and pdftotext/pdfplumber (PDF) for progressive retrieval; never load whole files. Use this whenever the user asks a question that should be answered from the knowledge/ directory. Cite every claim to a file + page/row; if the data does not contain the asked concept, say so and cite the absence — never fabricate.
---

# Local Knowledge-Base Retrieval (kb-retriever)

## The knowledge base

- The knowledge base lives under a root directory (default: `knowledge/` at the project root).
  If the user names a different path, use that instead. If `knowledge/` does not exist, ask the
  user for the path — do not guess.
- It contains multiple file types (`.md`/`.txt`, `.pdf`, `.csv`), organized into sub-directories
  by domain.
- It uses **hierarchical index files**: every directory has a `data_structure.md` describing what
  it contains and how to use it. The root `data_structure.md` lists the domain directories; each
  domain directory has its own; deeper sub-directories may too — forming a multi-level index tree.
- **These maps ARE the index.** There are no embeddings and no vector store. You navigate by
  reading the maps and descending the relevant subtree.
- A single business file may be large: never `Read` a whole CSV/PDF. Process it with the right
  tool (pandas / pdftotext), then grep + locally read around the matches.

### Locating the root
- Prefer the user's path if given. Otherwise default to `knowledge/`.
- Confirm it exists with a shell check: `test -d knowledge` (or `ls -d knowledge`).
  Do NOT use `Glob "knowledge"` to test directory existence — Glob returns files, not directories,
  so an empty result cannot distinguish "missing" from "empty".
- Only after confirming the root exists, use Glob within it (e.g. `pattern="**/data_structure.md"`,
  `path="knowledge"`).

## Key principle: learn before you process

**Mandatory checklist when you hit a PDF or CSV file:**

- [ ] Read the matching processing reference (PDF → `references/pdf_reading.md`; CSV → `references/excel_reading.md` + `references/excel_analysis.md`).
- [ ] Understand the recommended tools and commands.
- [ ] Process the file (extract/convert) with that tool.
- [ ] Only now begin retrieval.

**Forbidden:**
- Processing a PDF without first reading `pdf_reading.md` in full.
- Processing a CSV without first reading `excel_reading.md` in full.
- Retrieving directly against a raw PDF/CSV without processing it first.
- Reading a reference with a `limit` (e.g. `limit: 30`). Partial reads create a *compliance
  illusion*: you read the opening and think you're done, but your tool choice was actually formed
  before you read. **Lesson:** after a limited read of `pdf_reading.md` the model picked pdftotext,
  then realized the decision was made before reading — the 30 lines only confirmed it. **Read
  references in FULL, no `limit`.**

## Overall workflow

1. **Understand the request.** Extract topic/domain keywords, any time or scope constraints, and
   the output type (explanation, figure, comparison). Decide the knowledge root (above).

2. **Navigate the `data_structure.md` index, top-down.**
   - Read the root `data_structure.md`. Learn which domain directories exist and their purpose,
     **and any guardrails it states** (e.g. "these two domains share no join key").
   - Pick the most relevant subtree(s) for the question. Descend into the chosen directory, read
     ITS `data_structure.md`, and repeat. Don't fan out into every branch — follow the most
     relevant path down.
   - Collect the candidate files. **Read the per-file notes in the map** — they often tell you a
     column is mislabeled, a field is absent, or two values conflict. These notes are guardrails;
     honor them.

3. **Learn the processing method (mandatory for PDF/CSV).**
   - Before a PDF: read `references/pdf_reading.md` in full (pdftotext / pdfplumber, table extraction).
   - Before a CSV: read `references/excel_reading.md` and `references/excel_analysis.md` in full
     (pandas read, column filtering, aggregation).

4. **Process and retrieve by file type.**
   - Extract/convert with the learned tool, then progressively retrieve.
   - **CSV:** use pandas with explicit filters/aggregations (`df[df['col']==v]`, `.sum()`); read only
     the matching rows. Inspect the actual columns from the data — do not assume a field exists
     because the question implies it.
   - **PDF:** `pdftotext input.pdf out.txt` (to a file, never stdout — stdout burns tokens), then
     grep the text and locally read around matches. Record `file + page + snippet`.

5. **Iterate (≤5 rounds).** Generate/expand keywords (synonyms, abbreviations; cover BOTH the
   *attribute* words and the *behavior* words — e.g. not just "retain"/"period" but also
   "train"/"store"/"opt-out"). Search the not-yet-covered files/sections. Stop when you have enough
   to answer, or after 5 rounds — then state honestly what's missing.

6. **Self-check before you answer (falsification view).** Generate your answer draft but do NOT
   show it yet. Re-read your evidence asking "could this cell be WRONG?" not "does it look right?".
   - **Branch A — re-probe negatives:** for every "not available" / "no" / "not stated" conclusion,
     re-grep the source with at least one keyword DIFFERENT from your first pass. Only keep the
     negative if the new grep also misses.
   - **Branch B — combine separate evidence:** ask whether two separately-retrieved facts, combined,
     overturn a conclusion you drew from one alone.
   - **Merge corrections INTO the answer.** Never show a wrong answer then append a "correction" —
     the user must see only the final, corrected answer. (Lesson: a model once ran the self-check
     correctly but appended the fix below the wrong table; the user saw the wrong version first.)

7. **Compose and cite.** Give the direct answer, then the evidence. **Cite every factual claim to a
   file + page/row.** If the data does not contain the asked concept, say so explicitly and cite the
   absence (the file's column set, or the map's note) — never fabricate a value, never reach into an
   unrelated domain, and if sources conflict, surface BOTH with both citations rather than picking one.

## Answering rules (the honesty contract)

- **Cite or don't claim.** Every factual statement carries a source (file + page/row). No source → no claim.
- **State absence, don't fabricate.** If a field/document doesn't exist, say "not available" and cite
  what's missing (the column set, the map note). Never invent a penalty clause, an overdue list, a
  figure, or a date.
- **Never cross unrelated domains.** If the root map says two domains share no join key, never answer
  one with the other's content and never invent a link between them.
- **Surface conflicts.** If two sources disagree, present both with both citations; do not silently
  average or pick one.
- **Answer in the language of the question** (English or Hebrew). The Hebrew answer must carry the
  identical facts, figures, citations, and honesty behavior as the English one — never change a
  number or drop a citation in translation.

## Tool discipline

- **Grep:** find line numbers + snippets in specific files; always set a precise `include`/`path`.
- **Read:** only local reads around a match (`offset` + small `limit`); never whole large files.
- **Bash (pdftotext / pandas):** the processing step; extract to a file, then search.
- For any potentially-large file: never read start-to-finish — narrow by map/index/keyword first.
