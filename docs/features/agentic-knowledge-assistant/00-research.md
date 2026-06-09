# 00 — Research: Agentic Knowledge Assistant

Derived from: the parent product's shipped golden bar (`Contract-Retriever-RAG/docs/features/*/02-examples.md` + `docs/product/data-quality-assessment.md` + `architecture.md`) + first-hand study of the user's proven agentic pattern (`github.com/qufeiz/kb-retriever`: `backend/agent.py`, `.claude/skills/kb-retriever/SKILL.md` + references, the `knowledge/` + `data_structure.md` tree) + re-verification of every golden figure against the raw `data/`.

> **The domain truth for this rebuild: the PRODUCT does not change — a free-form business question still returns a grounded answer with click-to-source citations and visible reasoning. Only the RETRIEVAL ENGINE changes, from "router → SQL + vector-RAG → grounded gen → deterministic `validateAnswer()`" to "a Claude Agent SDK loop that NAVIGATES a `knowledge/` tree via human-readable `data_structure.md` maps (the index — no embeddings), reads a processing reference before touching a CSV/PDF, then uses pandas / pdftotext+pdfplumber with progressive grep + local reads, self-checks against a falsification view, and emits a cited answer." The honesty differentiator survives verbatim: cite every claim to a resolvable file+page/section, state absence instead of fabricating, surface conflicts, never invent a cross-source join. What we knowingly trade is the deterministic unit gate — an agent is non-deterministic — for a strong-but-statistical agentic guarantee (see `03`).**

---

## 1. What we are re-platforming (the parent product, unchanged in intent)

The shipped `Contract-Retriever-RAG` is an **AI Business Knowledge Assistant**: a free-form question is **routed** to the relevant source(s), answered by **hybrid SQL + RAG retrieval**, and returned as a **grounded answer with inline citations**. The client explicitly rejected the naive "upload PDFs into a vector DB + semantic search" pattern; the differentiators are **query routing**, **grounded generation**, and **source attribution you can trust** — every factual claim traces to a resolvable source (a SQLite row id or a PDF page).

That product is **live and verified**. This rebuild is a **copy** that keeps the product, the data, the four golden questions, and the "Aletheia" citation UX **identical**, and swaps only the retrieval engine for the user's own agentic pattern. It is a **re-platforming**, not a new product and not a superset of features. The parent repo + its Vercel deployment stay untouched.

## 2. How the user's agentic pattern actually works (studied, not assumed)

From `github.com/qufeiz/kb-retriever` (default branch `master`):

- **The harness (`backend/agent.py`)** runs the **Claude Agent SDK** (`claude_agent_sdk.query` + `ClaudeAgentOptions`) with the tools `Read, Glob, Grep, Bash` and the `kb-retriever` skill enabled. In kb-retriever it is a **two-phase table builder**: `propose_schema()` (explore the KB, propose columns) → `fill_table()` (fill every cell), each returning JSON. **Our adaptation:** we reuse the SDK-loop scaffolding and the skill, but the agent's output contract changes from "JSON rows" to a **grounded prose answer + a structured citation/evidence list + a trace** — the exact shape the Aletheia UI already consumes. The retrieval *method* is reused unchanged; only the *harness output* is adapted.

- **The method (`.claude/skills/kb-retriever/SKILL.md`)** is the heart of it:
  1. **Hierarchical `data_structure.md` navigation.** The knowledge base lives under `knowledge/`. Each directory holds a `data_structure.md` describing its subdirectories/files and their purpose. The agent reads the root map, picks the most relevant subtree, descends, and repeats — a multi-level human-readable index. **There are NO embeddings; the maps ARE the index.** (kb-retriever's leaf maps are literal tables with a Notes column — e.g. each privacy-policy PDF tagged with its company + a one-line note.)
  2. **Learn-before-you-process (a hard checklist).** On hitting a PDF the agent **must** first read `references/pdf_reading.md`; on hitting Excel/CSV, `references/excel_reading.md` + `excel_analysis.md` — **before** any extraction. The SKILL.md is emphatic that the reference must be read *in full, without a `limit`* (a logged lesson: a partial read produced a "compliance illusion" where the tool choice had already been made before reading).
  3. **Progressive grep + local reads, never whole-file.** `pdftotext file.pdf out.txt` then grep the output; pandas with `nrows`/filters; for each hit, read only the surrounding lines. Save "filename + location + snippet".
  4. **Multi-round iterative retrieval** (≤5 rounds), covering both **attribute** and **behavior** keywords (a logged lesson: searching only "retain"/"period" missed "train"/"opt-out").
  5. **A falsification-view self-check before output.** Re-read results asking "could this cell be **wrong**?" not "does it look right?"; for every negative/"not stated" conclusion, **re-grep with a different keyword** (Branch A) and **combine separately-retrieved evidence** (Branch B) before accepting it. The self-check is a **separate step**, and its corrections are merged into the answer — never appended as a "corrections" list the user sees after the wrong version.

- **What does NOT apply to us** (must be dropped when we fork the skill — full spec in `02`):
  - A **LightRAG pre-exploration step** (a `curl http://localhost:9621/...` vector service) baked into `pdf_reading.md` and the SKILL.md checklist. We have no such service and want **no embeddings** — drop it entirely.
  - The SKILL.md and references are **bilingual (Chinese-primary)**. We fork an **English** trimmed skill.

## 3. What our data actually is (the verdicts carried forward, re-verified)

The data is the **same `data/`** as the parent: 7 school CSVs + 2 Carter PDFs. We carry forward the parent's row-level data-quality verdict verbatim (`docs/product/data-quality-assessment.md`): **4 of 9 sources usable, 5 vetted-and-dropped with named defects.** This judgment is not re-litigated — it is the product. In the agentic system it becomes the **content of the `data_structure.md` maps**, so the agent inherits the same guardrails by *navigation* instead of by a loader.

| Source | Role | Verdict | The defect/boundary the map must state |
|---|---|---|---|
| `school data 1.csv` → `contracts.csv` | vendor contracts | ✅ USABLE | `Contract ID` holds **job titles**, not ids; many `End Date` precede `Start Date`; **no penalty/termination column**, and **no contract documents exist** → penalty terms have no source. |
| `school data 3.csv` → `maintenance.csv` | maintenance tickets | ✅ USABLE (honesty boundary) | **No payment-status / due-date / paid field**; vendors are **who we pay**, not customers who owe us; **no service-agreement doc** → "overdue/suspension" is unanswerable. |
| `📄 FAMILY COURT CASE FILE (MOCK) – FINAL VERSION.pdf` → `family-court-case-file.pdf` | court file (24pp) | ✅ USABLE | The **Final Judgment is on Page 24** (child support **$1,285/month**, primary residence **Joni Carter**). Cover sheet's filing date **conflicts** with the body. |
| `story if the Carters .pdf` → `case-story.pdf` | narrative (3pp) | ✅ USABLE (corroborating) | Corroborates the grounds; states filing date **February 3, 2026** (conflicts with the cover's "10 February 2026"). |
| `school data 2.csv` (enrollment) | — | ❌ DROPPED | `term_name` is 100% a Ruby error string; `status` holds gender values — header/data misaligned. |
| `school data 4.csv` + `6.csv` (payroll) | — | ⚠️ DROPPED | `pay_method`/`payroll_notes` are error strings; `pay_month` ranges 1–100; two irreconcilable schemas. |
| `school data 5.csv` (invoice volume) | — | ❌ DROPPED | All 788 rows identical (zero variance). |
| `school data .csv` (people) | — | ❌ OUT OF SCOPE | Generic PII directory; no spec question touches it. |

The dropped five are **kept in the tree but mapped as DROPPED with the exact defect** (under a `_dropped/` folder) so the agent is told *not to build on them* — the data-intake honesty is preserved as navigation guidance.

## 4. The golden figures (re-verified against the raw data, not copied on faith)

Every number the golden bar pins was re-computed from `data/` at the pinned anchor `asOfDate = 2026-06-09`:

- **Contracts:** `End Date ∈ [2026-06-09, 2026-09-07]` → **38 rows**, `SUM(Annual Cost) = $18,924,883.79`. The **illustrative "earliest-expiring" top-5 is pinned to a deterministic order — `End Date ASC, Vendor ASC, id ASC`** (id = source CSV row index; matches v1) because several rows share an End Date (two on 2026-06-11, two on 2026-06-17). Under that order the top-5 is: Dental Hygienist/Edgepulse 2026-06-11 $779,823.65 · Paralegal/Voomm 2026-06-11 $95,103.45 · Geological Engineer/Realbuzz 2026-06-12 $133,353.76 · Quality Engineer/Brainsphere 2026-06-17 $844,932.35 · Occupational Therapist/Fanoodle 2026-06-17 $132,126.71. (The count and sum are order-independent; only the illustrative rows depend on the tie-break — see `02` G-1 and the `03` F-G1 assertion.) Note `contracts.csv` also contains **End<Start** anomalies (e.g. Staff Scientist/Feedfish, Start 2026-06-26 / End 2026-06-17) that are preserved, not cleaned.
- **Maintenance:** total spend **$40,597.00 across 750 tickets**; 2026 **$13,485.66 across 248 tickets**; top vendor **Oyoba $949.94 (3 tickets)**, then Voolith $783.67, Photobug $549.90, Zoovu $525.54. **No payment-status field exists** (columns are only Ticket ID, Vendor, Invoice, Labor/Parts/Total Cost, Completion Date).
- **Carter Page 24 (verified by `pdftotext`):** "📑 PAGE 24 – FINAL JUDGMENT" → Marriage dissolved · Joint custody granted · **Primary residence: Joni Carter** · Asset division: equal split · **Child support: $1,285/month** · Home sale ordered within 12 months.
- **Filing-date conflict (real, verified):** the court file cover sheet says **"Filed: 10 February 2026"**; the court file's grounds narrative and `case-story.pdf` both say Joni **"filed for divorce on February 3, 2026."** The conflict is genuine, not contrived.

These are the numbers `02-examples.md` builds on and `03-tests.md` pins.

## 5. What "complete" means vs. a toy slice (the bar the rebuild must clear)

A **toy** agentic re-platforming would: build a chat over an embeddings index of the PDFs (the rejected pattern); answer "what expires soon" with a vague "several contracts" (no count, no real rows); fabricate a penalty clause or an "overdue customers" list; cite "the case file" without a page; silently pick one filing date; or — worst — answer a contract question with Carter divorce-case text. Each is exactly what the client said disqualifies a vendor.

**Complete** means the agentic engine clears the **same four-question golden bar** as the shipped product, with the added agentic requirement that it **demonstrably navigated and read the right files** (the trace), and does so **honestly**: the count is 38 (real, cited rows + the $18.9M total), the penalty/overdue halves are an honest "not available + why" (citing the schema/absence), the Carter judgment is **$1,285/Page 24**, the filing-date **conflict is surfaced with both citations**, and **no cross-source join is ever fabricated** (school data and the Carter case share no key). English-first, Hebrew-ready.

## 6. Implications for design (handed to `01`)

1. **Runtime = Python FastAPI backend** (approved) running the kb-retriever Agent SDK loop + the **Python** skill (pdftotext/pdfplumber/pandas) verbatim; the **copied Aletheia Next.js frontend** calls `/api/ask`. Faithful reuse of the user's proven tooling; the only cost is a second deploy target.
2. **The `data_structure.md` maps ARE the guardrail.** The honesty discipline (no penalty source, no payment-status field, the two domains share no join key, the dropped five) lives in the maps the agent navigates — not in a validator bolted on afterward. Their exact content is a design deliverable (`02`).
3. **The citation UX is preserved**; only the citation **target** changes (SQLite row id → file + page/section). The routing panel becomes the **agent trace**.
4. **The deterministic `validateAnswer()` does not transfer.** Its replacement is a golden eval set + deterministic answer-assertions (which DO survive non-determinism) + trace inspection + the skill self-check + repeated-N runs + an LLM judge (`03`). This is consciously a looser-but-strong guarantee, accepted by the user.
5. **The four golden questions and the pinned anchor (`asOfDate = 2026-06-09`)** are unchanged, so the count **38** stays deterministic for the demo and the eval fixtures.
