---
name: kb-retriever-lean
description: Cost-lean retrieval & Q&A over the local knowledge/ tree. SAME core as kb-retriever — navigate hierarchical data_structure.md maps (the maps ARE the index; no embeddings), process-don't-dump (pandas/pdftotext, never read whole files), and cite every claim to a file+page/row or state the absence — but the per-file processing recipe is INLINED (no mandatory full-reads of reference docs), the iterate loop is tighter (≤3 rounds), and the falsification self-check runs on REFUSALS (where a false-negative is the failure mode), not on every already-cited answer. Use whenever a question should be answered from knowledge/.
---

# Local Knowledge-Base Retrieval — lean

This is the cost-lean variant of `kb-retriever`. The honesty + navigation core is identical; the
ceremony the generic skill needs for an *unknown* corpus (re-reading "how to use pdftotext/pandas"
on every question) is removed, because this corpus is fixed and mapped.

## The knowledge base
- Root: `knowledge/` (use the user's path if named; if `knowledge/` is missing, **ask** — don't guess).
- File types: `.md`/`.txt`, `.pdf`, `.csv`, organized into domain sub-directories.
- **The maps ARE the index.** Every directory has a `data_structure.md`: the root lists the domain
  directories; each domain has its own; deeper dirs may too — a multi-level index tree. There are
  **no embeddings and no vector store**. You navigate by reading the maps and descending the
  relevant subtree.
- **Never `Read` a whole CSV/PDF.** Process it with the right tool, then grep + read around matches.
- Confirm the root with `test -d knowledge` (NOT `Glob "knowledge"` — Glob returns files, so it can't
  tell "missing" from "empty"). Only then Glob within it.

## Processing recipe (INLINED — no reference doc to read first)
Two known file types, fixed recipes — apply directly:
- **CSV → pandas.** `python3 -c "import pandas as pd; df=pd.read_csv('f.csv'); ..."`. **Inspect the
  REAL columns first** (`list(df.columns)`); never assume a field exists because the question implies
  it. Filter/aggregate explicitly (`df[df.col==v]`, `.sum()`) and read only the matching rows. Cite
  `file#row-N`.
- **PDF → pdftotext.** `pdftotext input.pdf out.txt` (to a **FILE**, never stdout — stdout burns
  tokens), then grep the text and read around the matches. Tables: add `-layout`. Cite
  `file#p<printed-page>`.

(If an unusual layout doesn't yield, the full processing references still live in the sibling
`kb-retriever` skill's `references/` — consult them only as a fallback, not by default.)

## Workflow
1. **Understand the request** — topic/domain keywords, any scope/time constraints, the output type
   (explanation, figure, comparison).
2. **Navigate the maps, top-down.** Read the root `data_structure.md` and note its **guardrails**
   (e.g. "these two domains share no join key"). Descend the most relevant subtree, read ITS map,
   repeat. Don't fan out into every branch. **Honor the per-file map notes** (a mislabeled column, an
   absent field, conflicting values) — they are guardrails.
3. **Process + retrieve** with the inlined recipe for each file type. Record `file + page/row + snippet`.
4. **Iterate (≤3 rounds).** Expand keywords (synonyms/abbreviations; cover BOTH the *attribute* words
   and the *behavior* words). Search the not-yet-covered files/sections. Stop when you can answer, or
   after 3 rounds — then state honestly what's missing.
5. **Self-check — falsification, focused on refusals.** Before answering, for every
   "not available"/"no"/"not stated" conclusion, **re-grep the source with a keyword DIFFERENT from
   your first pass**; keep the negative only if the re-grep also misses. Also ask whether two
   separately-retrieved facts, combined, overturn a conclusion drawn from one alone. **Merge any
   correction INTO the answer** — never show a wrong answer then a correction below it. (A positive
   answer whose citation already resolves does not need the full re-probe.)
6. **Compose + cite.** Direct answer, then the evidence. **Every factual claim → file + page/row.**
   If the data lacks the asked concept, say so and cite the absence (the column set, or the map note)
   — never fabricate, never reach into an unrelated domain, and if sources conflict surface BOTH with
   both citations.

## Answering rules (the honesty contract — unchanged)
- **Cite or don't claim.** Every factual statement carries a source (file + page/row). No source → no claim.
- **State absence, don't fabricate.** Field/document missing → "not available" + cite what's missing
  (the column set, the map note). Never invent a penalty clause, an overdue list, a figure, or a date.
- **Never cross unrelated domains.** If the root map says two domains share no join key, never answer
  one with the other's content and never invent a link between them.
- **Surface conflicts.** Two sources disagree → present both with both citations; never silently
  average or pick one.
- **Answer in the language of the question** (English or Hebrew) — identical facts, figures,
  citations, and honesty behavior in either language.

## Tool discipline
- **Grep:** precise `include`/`path`; returns line numbers + snippets.
- **Read:** only local reads around a match (`offset` + small `limit`); never whole large files.
- **Bash (pdftotext / pandas):** the processing step; extract to a file, then search.
