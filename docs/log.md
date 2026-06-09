# Project log — decisions & incidents

Append-only. **Newest first.** Format: `## [YYYY-MM-DD] type | title`, then a few lines + links.
Types: incident · decision · feat · fix · reorg.
> When something non-obvious happens, add an entry here and update the relevant doc in the same change.

---

## [2026-06-09] reorg | Forked into the AGENTIC rebuild — docs re-pointed, v1 docs archived
This repo (`Contract-Retriever-Agentic`) is a **fork** of the shipped `Contract-Retriever-RAG`, re-platformed from "router + hybrid SQL/vector-RAG + deterministic `validateAnswer()`" to an **agentic retriever** (Claude Agent SDK loop navigating a `knowledge/` tree via `data_structure.md` maps — **no embeddings**). Product/data/golden-questions/"Aletheia" UX unchanged; only the engine changed. The original product stays live + untouched at its own repo/URL. **Doc actions this change:** rewrote `architecture.md`, `CLAUDE.md`, `README.md`, `docs/README.md` for the agentic engine; authored the single umbrella feature `features/agentic-knowledge-assistant/` (`00`–`03` + README) — the per-domain goldens are now `02` sections, not separate folders (user-approved). **Archived** the v1 per-feature folders (`contract-intelligence`, `case-file-qa`, `maintenance-spend-intelligence`, `shared-engine`), the v1 `CLIENT-DELIVERABLE`, and the `sqlite-on-serverless` gotcha to `docs/archive/` (excluded from doc-lint) for provenance. **Seal-decay:** `sqlite-on-serverless.md` no longer applies — there is no SQLite/bundled index in the agentic build (the agent reads `knowledge/` files directly). Entries below this line are the **v1 product's** history, kept as the provenance of what was re-platformed.

## [2026-06-09] feat | Production-grade UI redesign ("Aletheia") + Hebrew figure fix
Redesigned the frontend with the frontend-design skill after researching Perplexity/Glean citation-forward patterns: an "editorial archive" aesthetic (warm paper-and-ink, Fraunces/Newsreader/JetBrains Mono, one teal accent — not AI-gray), color-coded per-feature entry cards, routing-transparency flow, **clickable inline citation chips that scroll to + highlight the exact source row/page**, readable source rows, all loading/empty/error/no-source states, RTL for Hebrew, responsive. All data-testids preserved → 13/13 journey tests still pass. Fixed a real reliability gap: Hebrew answers occasionally omitted the exact aggregate ($18.9M / $40,597) — made verified figures + the refusal pivot mandatory verbatim in every language (now contract-HE 5/5, maintenance-HE 4/4). Re-captured all 12 golden screenshots. Polished CLIENT-DELIVERABLE.md into a landing (hero + CTA + at-a-glance table). Product named **Aletheia** (truth/disclosure).

## [2026-06-09] feat | All 3 domain features shipped + client deliverable assembled
contract-intelligence (38 expiring/$18.9M/honest-no-penalties/leak-guard), case-file-qa (Page-24 $1,285/corroboration/conflict-surfacing), maintenance-spend-intelligence ($40,597 spend/honest-refusal). Each has its own 04/user-guide/README ledger + golden screenshots + per-feature content-fidelity gate + journey gates (13 total, green vs live). Assembled the single client-facing doc `CLIENT-DELIVERABLE.md` (pitch + Mermaid diagram + 3 capabilities + Data Quality Assessment of all 9 sources). 40 unit tests green.

## [2026-06-09] incident | Bundled SQLite returned 0 rows on first Vercel deploy
First prod deploy: every structured query returned empty (RAG/PDF path worked); `validateAnswer()` correctly rejected the ungrounded result. Cause: `better-sqlite3` can't open the traced bundled `.sqlite` on Lambda. Fix: copy bytes to `/tmp` and open from there + build with `journal_mode=DELETE`. Also pinned `ASSISTANT_TODAY=2026-06-09` for a deterministic demo. Sealed: `gotchas/sqlite-on-serverless.md`. META-MISS: tests were green on localhost — the journey suite now also runs against the live URL.

## [2026-06-09] decision | Design-approval gate convention recorded
The user approved the design + golden bar for this build (an AI Business Knowledge Assistant: routed, hybrid SQL+RAG, grounded+cited answers). **Convention for this repo:** no code/migration/test ships before a *written* design is *explicitly* approved — a prior "do it" on one feature never carries to the next. The PM owns the design + the golden bar; an independent Verifier grades; the Engineer never self-certifies.

## [2026-06-09] decision | Honest multi-source composition; no fabricated joins
The structured CSVs (→ SQLite) and the PDFs (Carter family-court case) share **no join key** — school vendors are unrelated to the Carter family case. Multi-source answers are **composed and cited separately**, never merged on an invented key. Also recorded: the contracts CSV (`school data 1.csv`) has **no penalty/terms column** and there are no vendor-contract PDFs, so "what penalties are defined in those contracts" must be answered honestly ("penalties are not present in the available sources") rather than fabricated. → `architecture.md`

## [2026-06-09] decision | LLM = DeepSeek; embeddings = LOCAL multilingual
DeepSeek (`deepseek-chat`, OpenAI-compatible) is the LLM (router + generation); the key is env-only, never committed. Embeddings are a **local** multilingual model (`Xenova/multilingual-e5-small`) computed at build time — no embeddings key, and it gives the Hebrew-readiness seam. Self-contained: a bundled read-only SQLite (CSVs) + an in-app vector index (PDF chunks). → `architecture.md`, `ops/environment.md`

## [2026-06-09] feat | Bootstrap — doc skeleton + immune system + CI
Greenfield repo stood up per the feature-system §A sequence: doc skeleton (CLAUDE.md, docs/README.md, this log, gotchas, architecture, meta playbook), the `doc-lint` + `doc-structure-lint` immune system wired as **required** CI steps, starter memory, and this approval-gate convention. The shared engine is the first worked example.
