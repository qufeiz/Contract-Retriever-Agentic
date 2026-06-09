# PDF Reading & Extraction

> Read this in full BEFORE you process a PDF in the knowledge base. It tells you how to extract
> text/tables so you can grep and locally read, instead of loading the whole PDF into context.

## Quick decision table

| Situation | Tool | Why | Command / code |
|---|---|---|---|
| Plain text (most common) | `pdftotext` | fastest, simplest | `pdftotext input.pdf output.txt` |
| Preserve layout | `pdftotext -layout` | keeps original layout | `pdftotext -layout input.pdf output.txt` |
| Extract tables | pdfplumber | strong table detection | `page.extract_tables()` |
| Metadata | pypdf | lightweight | `reader.metadata` |

## Recommended: pdftotext

> **Important:** write the output to a FILE, never to stdout — stdout dumps the whole document into
> context and burns tokens.

```bash
pdftotext input.pdf output.txt              # extract all text to a file
pdftotext -layout input.pdf output.txt      # preserve layout
pdftotext -f 1 -l 5 input.pdf output.txt    # only pages 1–5
```

Workflow:
1. `pdftotext input.pdf out.txt`
2. `grep -n` the extracted text for your keywords.
3. `Read` only the matched region (offset + small limit) — never the whole `out.txt`.
4. Record `file + page + snippet` for each hit.

## Page numbers — printed labels vs physical pages

Some documents print their own page headers (e.g. `📑 PAGE 24 – FINAL JUDGMENT`). After
`pdftotext`, the text may be packed into fewer *physical* pages than the printed labels suggest.
**Cite the printed PAGE label** that heads the section your retrieved text falls under — that is what
a reader verifies against when they open the document. Find the label that immediately precedes your
matched text:

```bash
grep -nE 'PAGE [0-9]+' out.txt       # list the printed page headers and their line numbers
grep -n 'child support' out.txt      # find your fact; cite the nearest preceding PAGE label
```

## pdfplumber (tables / layout)

```python
import pdfplumber

with pdfplumber.open("document.pdf") as pdf:
    page = pdf.pages[0]
    text = page.extract_text()
    tables = page.extract_tables()
```

## Conflicts across documents

If two PDFs (or a cover sheet vs. a body section) state different values for the same fact, do NOT
pick one. Extract from BOTH, cite BOTH pages, and surface the conflict in your answer.
