# 02 — Golden Examples: Agentic Knowledge Assistant

Derived from: 01-design.md §workflow (the single-spine 6 steps + the four golden scenarios) + 00-research.md §4 (every figure re-verified against the raw `data/`) + the parent product's three shipped `02-examples.md` (the golden answers we preserve).

> **This is the acceptance bar.** Every example is built from **real data** re-verified at the pinned anchor **`asOfDate = 2026-06-09`**, and each specifies BOTH the golden **answer** AND the expected **trace** (which files the agent must / must not open) — because in an agentic system "did it actually read the right file" is part of correctness. The toy-vs-real contrast defines the line. `03`'s eval gates must pass every golden answer+trace here and fail every toy/leaking/lucky-guess answer.

> **Citation format (the locked locator grammar).** Examples write citations in readable prose (*[source: …, Page 24]*); the **engine renders them as inline `[F:<path>#<locator>]` tokens**. The locator depends on the source:
> - **PDF with printed "📑 PAGE N" labels** (the court file) → `#p<printed-label-N>`, e.g. `[F:carter-case/family-court-case-file.pdf#p24]`. The validator bounds-checks N against the **printed PAGE-N headers** parsed from the text, NOT the 8 physical pdftotext pages (so `#p24` is valid even though there are only 8 physical pages).
> - **PDF with NO printed labels** (`case-story.pdf`) → `#p<physical-page>`, e.g. `[F:carter-case/case-story.pdf#p2]`.
> - **CSV row** → `#row=<Vendor>|<ISO-date>`, e.g. `[F:school-operations/contracts.csv#row=Voomm|2026-06-11]`. The validator resolves it to **exactly one** row (by matching the natural key — `(Vendor, End Date)` for contracts, since `Contract ID` is mislabeled) or the citation **fails**; a positional row index is NOT used (it would break on re-sort).
>
> Same citation, two forms: prose for readability here, the token in the engine's answer + screenshots, with `03` asserting the token resolves to a real file+page/row. An honest "not available" cites the **absence** (the file's column set / the map note) and carries **no** fabricated locator.

---

## Golden Example G-1 — Contract expiry + penalty (the headline; honest-refusal half), EN

**Question:** *"What contracts expire in the next 90 days and what penalties are defined in those contracts?"*  ·  **Pinned anchor:** `asOfDate = 2026-06-09` → window end **2026-09-07**.

### The grounded answer the system must produce
> **38 contracts expire between 2026-06-09 and 2026-09-07** (next 90 days), with a combined annual value of **$18,924,883.79**. *[source: `contracts.csv`, `End Date BETWEEN 2026-06-09 AND 2026-09-07` → 38 rows]*
>
> The earliest to expire:
> | Role label | Vendor | End Date | Annual Cost |
> |---|---|---|---|
> | Dental Hygienist | Edgepulse | 2026-06-11 | $779,823.65 |
> | Paralegal | Voomm | 2026-06-11 | $95,103.45 |
> | Geological Engineer | Realbuzz | 2026-06-12 | $133,353.76 |
> | Quality Engineer | Brainsphere | 2026-06-17 | $844,932.35 |
> | Occupational Therapist | Fanoodle | 2026-06-17 | $132,126.71 |
> *[source: `contracts.csv`, rows keyed by (Vendor + End Date); full 38-row list available]*

> **Pinned tie-break (the illustrative top-5 is deterministic).** Several rows share an End Date (two on 2026-06-11, two on 2026-06-17), so "earliest-expiring" is ambiguous unless an order is pinned. The golden order — and what the eval (`03` F-G1) and the screenshot assert — is **`End Date ASC, Vendor ASC, id ASC`** (id = source CSV row index; matches v1). Under it the top-5 is exactly the five rows above: Edgepulse before Voomm (E < V on 2026-06-11); Brainsphere before Fanoodle (B < F on 2026-06-17). The **count (38)** and **sum ($18,924,883.79)** are exact regardless of order; only the illustrative rows depend on the tie-break, so the eval asserts this exact ordering, not just "some 5 rows".
>
> **On penalties:** I can't provide penalty or termination terms for these contracts — **`contracts.csv` has no penalty/termination column, and no vendor-contract documents are loaded** in this knowledge base. So I can tell you exactly *what* expires and its annual value, but the *penalty* terms aren't available from any source here. I won't guess them.

### The expected trace (the agentic requirement)
- Reads `knowledge/data_structure.md` → sees the contract question maps to **`school-operations/`** (not `carter-case/`).
- Reads `school-operations/data_structure.md` → selects **`contracts.csv`**; the map already tells it **no penalty column / no contract documents exist**.
- Reads `references/excel_reading.md` (CSV), then uses **pandas** to filter `End Date ∈ [2026-06-09, 2026-09-07]` → 38 rows, `SUM(Annual Cost)`.
- **Does NOT open the Carter PDFs.** The penalty half is refused from the map+schema, not by reaching into an unrelated document.

### Why this is golden
Every claim traces (38 = pandas count; $18,924,883.79 = pandas sum; each row a real `contracts.csv` line). The penalty statement is an honest "not available" citing the **absence** (no column, no document) — not a fabricated clause and not Carter text. The trace proves it consulted `contracts.csv` only.

---

## Golden Example G-2 — Carter Final Judgment (page-cited document QA), EN

**Question:** *"What was the final child support amount, and who got primary residence in the Carter case?"*

### The grounded answer
> Per the **Final Judgment**, the court ordered **child support of $1,285/month**, with **primary residence to Joni Carter** and **joint legal custody**. The marriage was dissolved, assets divided as an **equal split**, and a **home sale ordered within 12 months**. *[source: `family-court-case-file.pdf`, **Page 24 – Final Judgment** → `[F:carter-case/family-court-case-file.pdf#p24]`]*

### The expected trace
- Root map → the case question maps to **`carter-case/`**.
- Reads `carter-case/data_structure.md` → the map notes the **Final Judgment is on Page 24** of `family-court-case-file.pdf` (not in the story).
- Reads `references/pdf_reading.md`, then `pdftotext family-court-case-file.pdf out.txt`, greps `child support` / `primary residence` / `custody`, local-reads the Page-24 block.
- Cites the **court file**, never `case-story.pdf` (the judgment isn't in it).

### Why this is golden
The exact figure (**$1,285/month**) and residence (**Joni Carter**) are real Page-24 findings, page-cited so a human can open and verify. The trace proves it read the court file (not just the narrative) and used the page reference.

---

## Golden Example G-3 — Maintenance overdue: HONEST REFUSAL + pivot (the trust demo), EN

**Question:** *"Which customers have overdue payments and what does the agreement say about service suspension?"*

### The grounded answer
> I can't determine **overdue payments** or **service-suspension terms** from this data, and here's exactly why:
> - `maintenance.csv` has **no payment-status, due-date, or paid/unpaid field** — its columns are only *Ticket ID, Vendor, Invoice, Labor Cost, Parts Cost, Total Cost, Completion Date*. A completed ticket is not a paid (or overdue) invoice. *[source: `maintenance.csv` — the listed columns are the complete set]*
> - The vendors here (e.g. Oyoba, Voolith) are **maintenance providers we pay**, not customers who owe us — so there's no "customer overdue" relationship in this data either.
> - There is **no service-agreement document** on file defining suspension terms.
>
> So I won't guess an "overdue" list — that would be fabricated. **What I can tell you from this data:** total maintenance spend is **$40,597.00 across 750 tickets**, and I can break it down by vendor, period, or category. *[source: `maintenance.csv`, SUM(Total Cost) over 750 rows]* Want the top vendors by spend, or a specific year?

### The expected trace
- Root map → `school-operations/` → reads `school-operations/data_structure.md`; the map flags **`maintenance.csv`: no payment-status field; vendors are who we pay; no service-agreement doc.**
- Reads `references/excel_reading.md`, uses pandas to **inspect the columns** (confirming no status field from the data itself, not just the map) and to compute the **$40,597.00 / 750** pivot it *can* deliver.
- Refuses the unanswerable half citing the schema/absence; pivots to the real cited figure.

### Why this is golden
It refuses honestly with the *specific reason*, cites the **schema** as evidence of absence, fabricates no overdue name/figure, and pivots to a real cited number. The trace proves it actually inspected `maintenance.csv`'s columns rather than assuming.

---

## Golden Example G-4 — Filing-date conflict: surface, don't resolve (the discriminating example), EN

**Question:** *"When did Joni Carter file for divorce?"*

### The grounded answer
> The sources **disagree on the exact filing date**:
> - The **court case file cover sheet** lists **"Filed: 10 February 2026."** *[source: `family-court-case-file.pdf`, Page 1 – Cover Sheet → `[F:carter-case/family-court-case-file.pdf#p1]`]*
> - However, the **case narrative** states Joni filed on **February 3, 2026** — and the court file's own grounds narrative says the same. *[source: `case-story.pdf`, "Decision to File for Divorce" → `[F:carter-case/case-story.pdf#p2]`]*
> I'm surfacing both rather than picking one, since the provided documents conflict.

### The citation rule (precise — the two PDFs differ in how they paginate)
- **Required (the deterministic conflict pair, both cleanly resolvable):**
  - Feb 10 → **`[F:carter-case/family-court-case-file.pdf#p1]`** (the printed "PAGE 1 – COVER SHEET" carries "Filed: 10 February 2026").
  - Feb 3 → **`[F:carter-case/case-story.pdf#p2]`** (the corroborating narrative; `case-story.pdf` has **no printed PAGE labels**, so it uses the **physical page** `#p2`).
- **Optional corroboration (prose, NOT a pinned assertion):** the answer may add that the **court file's own grounds narrative also states Feb 3**. That line physically sits between the printed "PAGE 6" and "PAGE 15" headers with **no printed "PAGE 11" of its own**, so it is **not** cleanly page-pinnable; if the agent cites it, it cites the nearest preceding printed label `#p6`, but the golden bar does **not** require it. The honesty point (cover-vs-body conflict, narrative corroborates Feb 3) is carried in prose; the two **required** citations are the resolvable pair above.

> **Locator grammar (locked with the engineer):** PDF tokens are `#p<N>` where N is the **printed "📑 PAGE N" label** for a label-bearing file (the court file — validator bounds-checks N against the parsed PAGE-N headers, not the 8 physical pages) and the **physical page** for a label-less file (`case-story.pdf`). CSV tokens are `#row=<Vendor>|<ISO-date>` (e.g. `#row=Voomm|2026-06-11`), resolving to exactly one row or the citation fails.

### The expected trace
- Root map → `carter-case/`; the map **notes the filing-date conflict** (cover vs. body).
- Reads `pdf_reading.md`, `pdftotext`s **both** PDFs, greps the filing date in each, finds "10 February 2026" (cover, printed Page 1) and "February 3, 2026" (court-file body + `case-story.pdf`).
- Surfaces **both** with the two required citations; opens **both** documents.

### Why this is golden
A trustworthy document-QA agent **surfaces the discrepancy and cites both sources** instead of averaging or guessing. It's a real conflict in the actual documents. The trace proves it read both PDFs (a single-file read could not have found the conflict).

---

## Hebrew variants (the EN spine, translated — facts + citations + honesty identical)

Each golden example has a Hebrew twin carrying the **identical** facts, figures, citations, and honesty behavior — the Hebrew path must neither change a number nor drop a citation nor fabricate.

- **G-1 (HE):** *"אילו חוזים יפוגו ב-90 הימים הקרובים ומהם הקנסות המוגדרים באותם חוזים?"* → 38 חוזים, $18,924,883.79, same earliest rows, **same honest "penalty terms not available"** (no column, no documents).
- **G-2 (HE):** *"מה היה סכום המזונות הסופי ולמי ניתנה המשמורת העיקרית בתיק קרטר?"* → **$1,285 לחודש**, מגורים עיקריים אצל **ג'וני קרטר**, cited to **עמוד 24 – פסק דין סופי**.
- **G-3 (HE):** *"אילו לקוחות מאחרים בתשלומים ומה אומר ההסכם על השעיית שירות?"* → same honest refusal (no payment-status field, vendors aren't customers, no agreement doc) + the **$40,597.00** pivot.
- **G-4 (HE):** *"מתי ג'וני קרטר הגישה לגירושין?"* → surfaces **both** 10 February 2026 (cover) and 3 February 2026 (body+story) with both citations.

---

## Toy-vs-real contrast (the line the eval gates enforce)

| Aspect | ❌ Toy / sub-par / dangerous answer | ✅ Real / golden answer |
|---|---|---|
| **Engine** | Embeddings index over the PDFs + semantic search (the rejected pattern). | An agent **navigating `data_structure.md`** and **reading the real files** — the trace shows it. |
| **Contract count** | "Several contracts are expiring soon." | "**38 contracts** expire between 2026-06-09 and 2026-09-07" — a real pandas count at the pinned anchor, cited rows + **$18,924,883.79** total. |
| **Penalty** | "Penalties typically include early-termination fees…" *(generic, ungrounded)* — OR a fabricated clause — OR Carter case text. | "**Penalty terms are not available** — no penalty column, no contract documents." Cites the absence; invents nothing; opens no unrelated file. |
| **Cross-domain leak** | Answers the penalty question with divorce-case content ("…home sale within 12 months…"). **Catastrophic.** | **Never** surfaces Carter text in a contract answer; the trace shows the Carter PDFs were never opened. |
| **Carter judgment** | "Some child support; custody to the mother." *(vague, uncited, or citing the story PDF.)* | "**$1,285/month**, **primary residence Joni Carter**, joint custody" cited to **Page 24** of the court file. |
| **Overdue** | "Oyoba and Voolith have overdue payments totaling $1,733." *(fabricated — vendors, not customers; no status field.)* | "**No payment-status field** in this data; vendors are who we pay; no agreement doc — I won't guess," + the **$40,597.00** pivot. |
| **Conflict** | "She filed February 3, 2026." *(silently picks one; hides the cover's Feb 10.)* | **Surfaces both** Feb 10 (cover) and Feb 3 (body+story) with **both** citations. |
| **Trace** | Right answer, wrong/no file opened (lucky guess / memorized). | The trace shows the **right files opened** (and the wrong ones NOT opened). |
| **Hebrew** | Changes a number, drops a citation, or fabricates. | **Identical** facts + citations + honesty in HE. |

**The one-line acceptance bar:** *a golden answer is composed only from files the trace shows the agent actually navigated-to and read; it states verifiable figures cited to a resolvable file+page/row, honestly says "not available + why" (citing the absence) for unsupported concepts, surfaces conflicts with both citations, never fabricates a penalty/overdue/clause and never crosses the school↔Carter domains — in both English and Hebrew.*

---

## Golden screenshots this feature needs (for the Engineer's `user-guide` + README ledger)

All captured at the pinned `asOfDate = 2026-06-09` so **38** is stable. Each must show the agent **doing real work** — never an empty form, a "no results" state, or a toy.

| # | Screenshot | What it must show |
|---|---|---|
| 1 | `g1-contract-90day-answer.png` | G-1: the **38 / $18,924,883.79** answer, the earliest-expiring rows with **row citations**, the honest **"penalties not available"** statement, AND the **agent-trace panel** showing `contracts.csv` opened and the Carter PDFs NOT opened. |
| 2 | `g1-citation-resolves.png` | A citation chip clicked → the source panel highlights the real `contracts.csv` row (proving citations resolve). |
| 3 | `g2-final-judgment-answer.png` | G-2: **$1,285/month** + **primary residence Joni Carter** with the **Page 24 – Final Judgment** citation, trace showing the court file (not the story) opened. |
| 4 | `g3-overdue-honest-refusal.png` | G-3: the **honest refusal** (schema-citation evidence visible) + the **$40,597.00** pivot. Clearly labeled as the *honesty/trust* demonstration. |
| 5 | `g4-filing-date-conflict.png` | G-4: **both** Feb 10 and Feb 3 with **both** citations, trace showing **both** PDFs opened. *(the trust demonstration.)* |
| 6 | `g2-hebrew-judgment.png` | G-2 (HE): the same **$1,285 / Page-24** answer in Hebrew with the citation intact. |

The headline shots (1, 3) show the engine **working on real data**; the refusal/conflict shots (4, 5) are trust demonstrations and must be **clearly labeled** so the README/user-guide doesn't read as "the product can't do anything." Per the self-check discipline: a refusal is a fine *separate* shot, but the headline must show real work.

---

## The EXACT `data_structure.md` map contents (the agent's guardrail — author these verbatim)

These maps **are the index** (no embeddings) and **are where the honesty discipline lives** — the agent reads them in workflow step 2 and is thereby *told* the boundaries before it answers. The engineer writes these files into `knowledge/` exactly as specified. The defect notes are carried verbatim from the parent's data-quality assessment.

### `knowledge/data_structure.md` (root)
```markdown
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
```

### `knowledge/school-operations/data_structure.md` (leaf)
```markdown
# School Operations — structured CSV data

| File | Domain | Notes (read before you answer) |
|---|---|---|
| `contracts.csv` | Vendor contracts (1000 rows) | Columns: `Contract ID, Vendor, Start Date, End Date, Annual Cost`. **`Contract ID` is MISLABELED — it holds job titles** (Registered Nurse, Staff Scientist…), NOT identifiers; treat it as a role label, key rows by (Vendor + End Date). Many `End Date` values **precede** their `Start Date` — preserve and may flag these; do NOT drop or "fix" them. **NO penalty / termination / notice column, and NO vendor-contract documents exist anywhere in this knowledge base** → penalty/termination terms have NO source; answer "not available", never fabricate, never reach into carter-case/. |
| `maintenance.csv` | Maintenance tickets / invoices (750 rows) | Columns: `Ticket ID, Vendor, Invoice, Labor Cost, Parts Cost, Total Cost, Completion Date` (Labor + Parts = Total). Supports real spend analysis (total $40,597.00 / 750; 2026 $13,485.66 / 248; top vendor Oyoba $949.94). **HONESTY BOUNDARY: there is NO payment-status, due-date, or paid/unpaid field**; the vendors are providers we PAY, not customers who owe us; there is **no service-agreement document**. So "overdue payments" / "service suspension" are NOT answerable — say so and cite the column set as evidence of absence; never fabricate an overdue list. `Ticket ID` also holds product/category names, not ids. |

`_dropped/` — five sources vetted and DROPPED for specific defects (see its data_structure.md). Do NOT build answers on them.
```

### `knowledge/school-operations/_dropped/data_structure.md` (leaf — the dropped sources, kept honest)
```markdown
# Dropped sources — vetted, then dropped (do NOT answer from these)

These were inspected at the row level and dropped for a specific, named defect. Building on them
would produce confident, fabricated answers. If asked about their domain, state it's unavailable
because the source is defective (name the defect) — do not retrieve from these files.

| File | Intended domain | Verdict & exact defect |
|---|---|---|
| `enrollment.csv` (school data 2) | course enrollment | UNUSABLE — `term_name` is 100% a Ruby error string; `status` holds gender values. Header/data misaligned. |
| `payroll_v1.csv` (school data 4) | payroll | DROPPED — `pay_method` & `payroll_notes` are 100% error strings. |
| `payroll_v2.csv` (school data 6) | payroll (alt) | DROPPED — `pay_month` ranges 1–100; `payment_method` is a random integer; 80+ currency codes; irreconcilable with payroll_v1. |
| `invoice_volume.csv` (school data 5) | invoice totals | UNUSABLE — all 788 rows identical (students=180, invoices_per_student=6, total=1080). Zero variance. |
| `people.csv` (school data) | person directory | OUT OF SCOPE — generic id/name/email/gender/ip list; no business question; PII-shaped. |
```

### `knowledge/carter-case/data_structure.md` (leaf)
```markdown
# Carter Family-Court Case — documents (PDF)

| File | What it is | Notes (read before you answer) |
|---|---|---|
| `family-court-case-file.pdf` | The MOCK family-court case file (Case FC-2026-10458), 24 pages, page-numbered | The ONLY document containing the **Final Judgment on Page 24** (child support **$1,285/month**, primary residence **Joni Carter**, joint custody, equal asset split, home sale within 12 months). The **cover sheet (Page 1)** lists "Filed: 10 February 2026". |
| `case-story.pdf` | A 3-page narrative of the same case | Corroborates the grounds for divorce; states Joni filed on **February 3, 2026** ("Decision to File for Divorce"). |

## Known facts to cite precisely
- The **Final Judgment lives ONLY in `family-court-case-file.pdf` Page 24** — never cite it to the story PDF.
- **FILING-DATE CONFLICT (real):** the cover sheet says "10 February 2026" but the court file's grounds narrative AND `case-story.pdf` say "February 3, 2026". If asked the filing date, SURFACE BOTH with both citations — do not silently pick one.
- Use `pdftotext` then grep; cite file + page. Physical pdftotext page numbers may differ from the printed "PAGE N" labels — cite the page that resolves to the retrieved text.
```

---

## The trimmed-skill spec (fork kb-retriever's SKILL.md — what to KEEP vs DROP)

The engineer forks `github.com/qufeiz/kb-retriever`'s `.claude/skills/kb-retriever/` into the new repo and produces an **English, trimmed** skill. This table is the spec.

| From kb-retriever | KEEP / DROP | Why |
|---|---|---|
| **Hierarchical `data_structure.md` navigation** (root → leaf maps, descend the relevant subtree) | **KEEP** | This is the core method and our entire index. |
| **Learn-before-you-process checklist** (read `pdf_reading.md` before a PDF; `excel_reading.md` + `excel_analysis.md` before a CSV) — **read the reference in FULL, no `limit`** | **KEEP** (incl. the "no `limit`" lesson) | Prevents the "compliance illusion" tool-choice bug; ensures correct extraction. |
| **Progressive grep + local reads, never whole-file** (`pdftotext`→grep→local read; pandas with filters) | **KEEP** | The token-efficient, verifiable retrieval discipline. |
| **Multi-round iterative retrieval (≤5), attribute + behavior keywords** | **KEEP** | Coverage discipline; the "also search behavior words" lesson applies. |
| **Falsification-view self-check before output** (Branch A: re-grep negatives with a NEW keyword; Branch B: combine separate evidence; corrections merged INTO the answer, never appended) | **KEEP** — this is critical for our honest-refusal and conflict examples | It's what makes "not available" a *probed* conclusion (G-3) and surfaces the conflict (G-4) rather than a first-guess. `03` checks it ran. |
| **No-fabrication / cite-your-source / language-of-the-question answering** | **KEEP** | The honesty differentiator + the Hebrew requirement. |
| **LightRAG pre-exploration** (`curl http://localhost:9621/health` then `/query/data`, in `pdf_reading.md` and the SKILL.md checklist) | **DROP entirely** | No such service; we want NO embeddings. Remove the step from the checklist AND the `pdf_reading.md` "LightRAG 关键词预探索" section. |
| **The two-phase table-builder framing** (propose-schema → fill-table, JSON `{"rows":...}` output) | **DROP** | Our harness is conversational Q&A returning `{answer, evidence, trace, validation}`, not a table. (This is a harness/`agent.py` change, not a skill-method change.) |
| **Chinese-primary prose** throughout SKILL.md + references | **DROP / translate** | Fork an **English** trimmed skill; keep every retained rule, drop the Chinese duplicates. |
| **`privacy-policy-analysis.md` reference** (bilingual-domain keyword strategy for ToS/policy docs) | **DROP** | Domain-specific to kb-retriever's privacy-policy corpus; irrelevant to contracts/court files. (A `legal-document-reading.md` could be added later if the Carter corpus needs domain keywords — defer.) |

**Net:** the forked skill keeps the *method* (navigate → learn → progressively extract → self-check → cite) and drops the *embeddings dependency*, the *table-builder framing*, and the *Chinese/irrelevant references*. The retrieval discipline the user proved is preserved; the parts that don't fit a no-embeddings, conversational, English contract-QA product are removed.
