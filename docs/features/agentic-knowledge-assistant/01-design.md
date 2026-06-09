# 01 — Design: Agentic Knowledge Assistant

Derived from: 00-research.md (the re-platforming intent, the studied kb-retriever pattern, the carried-forward data-quality verdicts, the re-verified golden figures) + the three user-approved decisions (Python backend · preserve the citation UX · `knowledge/` reorg).

> **What it does:** answers a free-form business question (EN/HE) by running a **Claude Agent SDK loop** that navigates a `knowledge/` tree via human-readable `data_structure.md` maps, reads a processing reference before touching a CSV/PDF, extracts with **pandas** (CSV) / **pdftotext + pdfplumber** (PDF) using **progressive grep + local reads**, runs a **falsification-view self-check**, and returns a **grounded answer with inline citation chips** plus a **visible trace** of which files it consulted — rendered in the copied "Aletheia" UI. Every claim cites a resolvable **file + page/section**; absent facts are an honest "not available + why"; conflicts are surfaced; a cross-source join is never fabricated.

> **Anchor date (pinned, deterministic):** the contract "next 90 days" window is computed from a single **injected `asOfDate = 2026-06-09`**, NOT the wall clock. The golden count (**38**) and the golden screenshots are pinned to it. `03` asserts the count holds only at this anchor; prod may pass a real `asOfDate`, but the eval fixtures and the demo freeze it.

---

## The visible outcome (what the user SEES when it works)

Identical to the shipped product, by design. The user types a question and, within the agent's run, sees **one answer** containing:
1. The **grounded answer** — readable prose (or a small table) with an **inline citation chip on every factual claim**.
2. A **source panel** — each cited chip resolves (click → highlight + scroll) to the exact source: a CSV row (file + natural key + the pandas-extracted values) or a PDF page (file + page + the pdftotext snippet).
3. An **agent-trace panel** (the re-labeled "routing" panel) — which `data_structure.md` maps the agent read and which files it opened, so "the agent navigated the knowledge tree and read the real files" is **visible**, the way routing transparency was visible before.

Not an embeddings-similarity blob, not a fabricated clause, not "the case file says…" with no page — a cited, traceable answer a business user can act on and verify, honest about what the data can't support.

## Architecture (the agentic engine)

```
  ┌─────────────────────────────────────────── Next.js (copied "Aletheia" UI) ──────────────────────────────────┐
  │  ask box → POST /api/ask {question}  →  renders: answer + citation chips + source panel + AGENT-TRACE panel   │
  └───────────────────────────────────────────────────────┬──────────────────────────────────────────────────────┘
                                                           │  (CORS; the only call the frontend makes)
                                                           ▼
  ┌──────────────────────────────────────── Python FastAPI backend ────────────────────────────────────────────┐
  │  POST /api/ask  →  answer_question(question)                                                                 │
  │     Claude Agent SDK loop  (claude_agent_sdk.query + ClaudeAgentOptions)                                     │
  │        tools: Read · Glob · Grep · Bash         skill: kb-retriever (forked, English, LightRAG removed)       │
  │        cwd = project root containing knowledge/                                                              │
  │     ── the skill's method ──                                                                                 │
  │        1. read knowledge/data_structure.md  →  pick the relevant subtree  →  descend, read its map           │
  │        2. on a CSV/PDF: FIRST read references/{excel,pdf}_reading.md   (no `limit`)                          │
  │        3. extract: pandas (CSV) / pdftotext+pdfplumber (PDF)  ·  progressive grep + local reads (≤5 rounds)   │
  │        4. falsification-view self-check (re-grep negatives w/ a new keyword; combine evidence)               │
  │        5. compose a grounded answer; attach a citation token to every claim; record the trace               │
  │  →  returns { answer, evidence[], trace[], validation }   (the shape the Aletheia UI consumes)               │
  └──────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
                                                           │  reads (never writes)
                                                           ▼
  knowledge/   data_structure.md (root: TWO domains, NO join key)
    school-operations/  data_structure.md  →  contracts.csv · maintenance.csv · _dropped/ (5 files, mapped DROPPED + defect)
    carter-case/        data_structure.md  →  family-court-case-file.pdf · case-story.pdf
```

The retrieval *method* is the user's kb-retriever skill, reused. The harness output is adapted from "JSON table rows" to the `{answer, evidence, trace, validation}` contract the UI already consumes (see Decision A).

## The three decisions (as approved — locked)

### Decision A — Runtime: **Python FastAPI backend + copied Next.js frontend** *(approved)*
Reuse `backend/agent.py`'s Agent SDK loop and the **Python** skill (pdftotext/pdfplumber/pandas) verbatim; the copied Aletheia frontend calls `/api/ask`. Two deploy units (Vercel frontend + a Python host — Vercel Python Functions with a 300s timeout, or Render/Fly), accepted for faithful reuse of the user's proven tooling. **Harness adaptation (the one real code change to the pattern):** the agent's output contract goes from kb-retriever's two-phase JSON-table builder to a **single conversational call returning `{answer, evidence[], trace[], validation}`**. The retrieval method is untouched; only the harness shape changes.

### Decision B — Citation model + UI: **preserve the chip→source-panel UX; only the citation TARGET changes** *(approved)*
- **Citation token grammar:** `[F:<file>#<locator>]` where the locator is a **page** for PDFs (`[F:family-court#p24]`) or a **row natural-key** for CSVs (`[F:contracts.csv#row=(Skalith,2026-07-09)]`). The PDF case is essentially the old `[P:doc#page]`; the structured case moves from a SQLite row id to the **source file + the row's natural key** — pointing at the real CSV the agent read (more honest than a generated DB id).
- **Source panel:** each cited token resolves to a panel entry showing file, page/section/row, and the **exact extracted snippet** (the grep hit / pandas-filtered row / pdftotext page text). The chip→highlight→scroll behavior is byte-for-byte the parent's.
- **Agent-trace panel:** the old routing panel, re-labeled — shows the `data_structure.md` maps read + the files opened. This *is* the preserved transparency, adapted to an agent.

### Decision C — Knowledge mapping: **`data/` → `knowledge/` with `data_structure.md` maps carrying the verdicts** *(approved)*
The tree in the architecture diagram above. The maps are the **entire index** (no embeddings); their exact content — the root "no join" statement and the per-file defect notes — is specified in `02` because **those maps ARE the agent's guardrail**.

## The single workflow (single-spine)

One ordered sequence; branches (Hebrew, a narrower window, a single contract) hang off it. The steps below are the **agentic analogue** of the parent's route→retrieve→ground→validate.

| Step | Who/what | What happens | State / output | Citation / trace produced |
|---|---|---|---|---|
| **1. Ask** | user | free-form NL question, EN or HE | the raw question | — |
| **2. Navigate** | agent (skill) | read `knowledge/data_structure.md` → choose the relevant subtree(s) from the maps → descend, reading each level's `data_structure.md` | the chosen file set + *why* (from the maps) | **trace:** maps read, subtree chosen |
| **3. Learn-then-extract** | agent (skill) | for each chosen file, FIRST read the matching reference (`pdf_reading.md` / `excel_reading.md`+`excel_analysis.md`, no `limit`), THEN extract: pandas filter/aggregate (CSV) or `pdftotext`→grep→local-read (PDF) | the extracted rows/pages + snippets | **trace:** files opened, tools used |
| **4. Iterate + self-check** | agent (skill) | progressive grep (≤5 rounds, attribute+behavior keywords); then the **falsification-view self-check** — re-grep each negative/"not available" with a new keyword, combine separate evidence, before accepting | the vetted evidence set | — |
| **5. Compose (grounded)** | agent | write the answer **only** from the evidence; attach a `[F:…]` citation to **every** factual claim; for an unavailable concept, state "not available + why" citing the absence; for a conflict, surface both with both citations; **never** join across the two domains | the final answer text | citation tokens + the evidence list |
| **6. Render (EN/HE)** | UI | show the answer with citation chips, the source panel, and the agent-trace panel | what the user sees | chips + panel + trace visible |

**Single golden scenario set for `02`:** the four approved questions (contract expiry+penalty · Carter Final Judgment · maintenance overdue refusal · filing-date conflict), each producing its golden answer **and** the expected trace (which files it must / must not open). Hebrew variants hang off the EN spine. When the contract answer lists "earliest-expiring" rows, it must request the **pinned tie-break order `End Date ASC, Vendor ASC, id ASC`** so the illustrative rows are deterministic (see `02`/`03`).

## Decisions & deferrals

- **Decision — the maps are the guardrail, not a post-hoc validator.** The honesty discipline (no penalty source, no payment-status field, the two domains share no join key, the five dropped sources) is written into the `data_structure.md` maps the agent reads in step 2, so the agent is *told* the boundary before it answers. `03`'s checks then verify the answer obeyed it. (Belt and suspenders: guide the agent **and** gate the output.)
- **Decision — the kb-retriever skill is forked and trimmed, not used as-is.** We drop the **LightRAG pre-exploration** (no `localhost:9621` service, no embeddings) and translate the **Chinese** SKILL.md + references to an English trimmed skill, keeping hierarchical nav · learn-before-process · progressive grep · pandas/pdftotext · the falsification self-check. Exact keep/drop list in `02`.
- **Decision — the harness becomes conversational Q&A, not a table builder.** kb-retriever's propose-schema→fill-table JSON contract is replaced by one `answer_question()` returning `{answer, evidence, trace, validation}`. The retrieval method is unchanged.
- **Decision — `Contract ID` is a `role label`; data defects (End<Start) are preserved, not cleaned** — same as the parent. The map states this; the agent must not relabel job titles as ids or drop anomalous rows.
- **Decision — the 90-day window uses an injected `asOfDate = 2026-06-09`**, frozen in the eval fixtures and the demo, so the golden count (38) is deterministic; and the earliest-expiring rows use the pinned tie-break `End Date ASC, Vendor ASC, id ASC`.
- **Decision — the deterministic `validateAnswer()` is replaced, not ported.** See `03`: deterministic answer-assertions + trace inspection + self-check + repeated-N + LLM-judge. A consciously looser-but-strong agentic guarantee.
- **Deferral — penalty/termination answering & overdue/suspension answering** stay the honest "not available": no penalty column / no contract documents, and no payment-status field / vendors-aren't-customers / no service-agreement doc. **We do not synthesize a placeholder document** to fill either gap (a fabricated source in a deliverable about honest grounding is itself a fabrication). They become real branches only if such sources are supplied.
- **Deferral — the 5 dropped sources** stay dropped (mapped DROPPED with their defect); un-blocked only by clean re-exports.
- **Deferral — Hebrew is English-first with a seam** (the question normalization point + the agent's language-of-question answering); RTL UI polish and HE eval fixtures beyond the golden variants are deferred.

## Phased plan

- **R1 (this slice):** the agentic engine clearing the four-question golden bar (answer + trace, EN/HE) over the `knowledge/` tree, in the copied UI, with the `03` eval gates green across repeated runs.
- **R2 (deferred):** penalty/overdue RAG branches if source documents arrive; the dropped domains on clean data; deeper Hebrew; a 30/60/90 horizon selector.

## Security / authorization

- **MVP scope:** single-tenant client deliverable over the client's own data; no per-row access control required by the spec.
- **The integrity rules in scope (the honesty contract):**
  1. **No fabricated attribution** — never attribute a fact to a file/page that doesn't contain it (no invented penalty, no invented overdue list, no fabricated row/page).
  2. **No cross-domain leak / no fabricated join** — a school-operations question is never answered with Carter case text and vice-versa; the two domains share no key and the agent must never invent one. The worst-case hallucination (a contract penalty answered with divorce content) **must fail** the eval (`03`).
  3. **Honest absence + surfaced conflict** — say "not available + why" when the source for a concept doesn't exist; surface a conflict with both citations rather than silently resolving it.
- **Agent-execution safety (new, because the agent runs tools):** the agent's `Bash` is used only for read-only extraction (`pdftotext`, `test -d`, pandas reads) over the bundled `knowledge/` tree; it **never writes** to `knowledge/` and has no network egress need (no LightRAG, no web). The `ANTHROPIC_API_KEY` is **env-only**, never committed; `.env*` (except `.env.example`) is gitignored — the parent's landmine carries over. The backend exposes only `/api/ask` and accepts only the question string.
- **Future (extensibility):** added sources (CRM/email/cloud/contract documents) each register as a new subtree with its own `data_structure.md` + access scope; the per-fact citation model is what makes per-source authorization and the leak-guard addable without touching the answer layer.
