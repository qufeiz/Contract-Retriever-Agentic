# Knowledge Base Root

Free-form business questions are answered by navigating this tree, reading the real
files, and citing every claim to a file + page/row. There are NO embeddings — these
data_structure.md maps ARE the index.

## Directory structure
| Directory | Domain | Purpose |
|---|---|---|
| `school-operations/` | School vendor operations | Structured CSV business data: vendor contracts and maintenance tickets. |
| `carter-case/` | Carter family-court case | A page-numbered court case file + a corroborating narrative (PDFs). |

## CRITICAL — the two domains share NO join key
`school-operations/` (a school's vendors) and `carter-case/` (the Carter family divorce)
are UNRELATED. There is no shared key. NEVER join or cross-reference them — never answer a
school-operations question with case content, or vice versa, and never invent a link between
a contract row and the case file. Cross-domain questions are composed and cited SEPARATELY.

## How to navigate
Read this map, pick the relevant subtree from the table, descend and read ITS data_structure.md
before opening any file. Before processing a CSV read the excel reference; before a PDF read the
pdf reference. Cite every claim to a file + page/row; if the data doesn't contain the asked
concept, say so and cite the absence — never fabricate.
