# Architecture — Agentic AI Business Knowledge Assistant

Start here to understand the system. This is the **explanation** doc (why it's shaped this way); the feature design + golden bar + gates live in [features/agentic-knowledge-assistant/](features/agentic-knowledge-assistant/README.md).

> **This project is the AGENTIC re-platforming of `Contract-Retriever-RAG`.** The product is unchanged — a free-form business question returns a grounded, click-to-source-cited answer with visible reasoning. Only the **retrieval engine** changed: from a router + hybrid SQL/vector-RAG + a deterministic `validateAnswer()` to a **Claude Agent SDK loop** that navigates a `knowledge/` tree and reads the real files. The original product stays live and untouched; this is a separate repo + deployment.

## What it is (and is not)

A free-form business question is answered by an **agent** that **navigates a `knowledge/` tree via human-readable `data_structure.md` maps** (the index — **no embeddings**), **reads a processing reference before touching a CSV/PDF**, extracts with **pandas** (CSV) / **pdftotext + pdfplumber** (PDF) using **progressive grep + local reads** (never whole-file), runs a **falsification-view self-check**, and returns a **grounded answer with inline citations** + a **visible trace** of which files it consulted. Every factual claim traces back to a resolvable source — a **file + page** (PDF) or a **file + row natural-key** (CSV).

It is **NOT** "upload PDFs into a vector DB and do semantic search" — the client rejected that explicitly, and this rebuild contains **no embeddings at all**. The differentiators are preserved: **the agent navigates and reads the real files (visible in the trace)**, **grounded generation**, and **source attribution you can trust** — with an **extensible** architecture (a future CRM / email / cloud-storage / case-management source registers as a new `knowledge/` subtree with its own `data_structure.md`).

## Stack

| Layer | Choice | Why |
|---|---|---|
| App / UI | **Next.js** (App Router) — the copied "Aletheia" ask box → answer + citation chips + source panel + agent-trace panel | Reuses the parent's valued citation UX verbatim; deploys to Vercel |
| Agent runtime | **Python FastAPI** backend running the **Claude Agent SDK** (`claude_agent_sdk.query` + `ClaudeAgentOptions`) | Faithful reuse of the user's proven kb-retriever loop + the Python skill (pdftotext/pdfplumber/pandas) |
| LLM | **Anthropic Claude** (Claude Agent SDK; `ANTHROPIC_API_KEY`, env-only) | The agent's reasoning + grounded generation |
| Retrieval method | The forked **`kb-retriever` skill** (English, LightRAG removed) + tools `Read · Glob · Grep · Bash` | Hierarchical map navigation + learn-before-process + progressive grep + self-check |
| Index | **`data_structure.md` maps** (one per directory) — human-readable, **no embeddings**, no vector store | The maps ARE the index *and* the agent's honesty guardrail |
| Documents / data | The bundled **`knowledge/` tree** (CSV + PDF), read-only | The agent reads the real files; citations point at them |

## Data flow

```
   NL question (EN/HE)
        │  POST /api/ask {question}
        ▼
   ┌───────────────────────── Python FastAPI · Claude Agent SDK loop ─────────────────────────┐
   │ 1. NAVIGATE   read knowledge/data_structure.md → pick subtree → descend, read its map      │
   │ 2. LEARN      on a CSV/PDF: FIRST read references/{excel,pdf}_reading.md  (in full)        │
   │ 3. EXTRACT    pandas (CSV) / pdftotext+pdfplumber (PDF) · progressive grep + local reads   │
   │ 4. SELF-CHECK falsification view: re-grep negatives w/ a new keyword; combine evidence     │
   │ 5. COMPOSE    answer ONLY from evidence; a [F:file#locator] citation on every claim        │
   └───────────────────────────────────────────────┬───────────────────────────────────────────┘
                                                    │  returns { answer, evidence[], trace[], validation }
                                                    ▼
   answer + citation chips  ·  source panel (file/page/row + snippet)  ·  agent-trace panel (maps read, files opened)
```

The full workflow, the citation grammar, the map contents, and the eval gates are in [features/agentic-knowledge-assistant/](features/agentic-knowledge-assistant/README.md) (`00`–`03`).

## Navigation — the differentiator, done agentically

There is **no router and no embeddings**. The agent reads `knowledge/data_structure.md` (the root map), which names two domains — **`school-operations/`** (vendor contracts + maintenance) and **`carter-case/`** (the Carter family-court PDFs) — and **states they share no join key**. The agent picks the relevant subtree from the map's purpose column, descends into that directory's `data_structure.md`, and selects the files to read. *"What contracts expire in 90 days?"* navigates to `school-operations/contracts.csv`; *"What did the court decide?"* navigates to `carter-case/family-court-case-file.pdf`. The chosen path is recorded in the **trace** and shown in the UI — navigation is visible, not hidden.

## Retrieval — the agent reads the real files

- **CSV side** — the agent reads `references/excel_reading.md`, then uses **pandas** to filter/aggregate (e.g. `End Date ∈ [asOfDate, asOfDate+90d]`); each returned row carries its **file + natural key**, which becomes the citation `[F:contracts.csv#row=(Vendor,EndDate)]`.
- **PDF side** — the agent reads `references/pdf_reading.md`, runs `pdftotext`, greps the extracted text, and local-reads around hits; each fact carries its **file + page**, which becomes `[F:<doc>#p<page>]`.
- **No join across domains** — `school-operations/` and `carter-case/` are unrelated; the agent never merges them on an invented key. Cross-domain questions are composed and cited **separately**.

## Grounded generation + citation + the self-check

The agent answers **only** from the evidence it extracted and attaches an inline `[F:…]` citation to **every** factual claim. Before output it runs the skill's **falsification-view self-check**: it re-reads its conclusions asking "could this be wrong?", re-greps each negative/"not available" with a *different* keyword, and combines separately-found evidence — so a "not available" or a surfaced conflict is a *probed* conclusion, not a first guess. The corrections are merged into the single answer the user sees (never appended afterward).

## The honesty contract (the trust property, preserved verbatim)

- **Cite every claim** to a resolvable file + page/row; an unresolvable claim is rejected, not shipped.
- **State absence, don't fabricate** — when the data lacks the asked concept (penalty terms; overdue/payment status), say so and cite the absence (the column set / the map note); never invent a clause or a debtor list.
- **Surface conflicts** — when sources disagree (the Carter filing date: cover "10 February 2026" vs. body/story "February 3, 2026"), surface both with both citations rather than silently picking one.
- **Never fabricate a cross-source join** — the school data and the Carter case share no key; the agent never links them.

## Data model (the `knowledge/` tree)

```
knowledge/
  data_structure.md                 root map: two domains, NO join key
  school-operations/
    data_structure.md               per-file map (defects named)
    contracts.csv                    vendor contracts — no penalty column; Contract ID = job titles; End<Start preserved
    maintenance.csv                  maintenance tickets — NO payment-status field (honesty boundary)
    _dropped/                        the 5 vetted-and-dropped sources, mapped DROPPED + the exact defect
  carter-case/
    data_structure.md               maps the two PDFs; notes Page-24 judgment + the filing-date conflict
    family-court-case-file.pdf       24pp court file; Final Judgment on Page 24 (child support $1,285/mo)
    case-story.pdf                   3pp corroborating narrative
```

The maps **are the index and the guardrail**; their exact required content is specified in [features/agentic-knowledge-assistant/02-examples.md](features/agentic-knowledge-assistant/02-examples.md). The four usable sources / five dropped sources verdict is carried forward from [product/data-quality-assessment.md](product/data-quality-assessment.md).

## Verification — a looser-but-strong agentic guarantee

An agent is **non-deterministic**, so the parent's deterministic `validateAnswer()` unit gate does **not** transfer. The replacement (full spec in [features/agentic-knowledge-assistant/03-tests.md](features/agentic-knowledge-assistant/03-tests.md)) is: a **golden eval set** + **deterministic answer-assertions** (citation-resolvability, required figures present, forbidden-token absence, honest-refusal fires, conflict surfaced — all pure, run every time) + **trace inspection** (did it open the right file and NOT the wrong one) + the skill's **self-check** + **repeated-N runs** (flaky = fail) + an **LLM-judge** for the prose layer. This is consciously a **statistical** guarantee, not a provably deterministic one — accepted at design time; kept strong by breadth of independent checks + repetition, run by an independent verifier.

## The Hebrew seam (EN-first, architecturally ready)

The agent answers in the language of the question, so a Hebrew question yields a Hebrew answer with the **same figures + citations + honesty** as its English twin (the golden bar includes Hebrew variants). Deferred for the MVP: RTL UI polish and Hebrew eval fixtures beyond the golden variants. The seam (question normalization + language-of-question answering) means adding Hebrew depth is content work, not re-architecture.

## Honest rough edges (decisions & deferrals)

- **No join between the two domains.** The school vendors and the Carter case are unrelated; the agent never fabricates a join. Cross-source questions are composed, each fact cited to its own source.
- **Penalties / overdue are honestly unavailable.** `contracts.csv` has no penalty column and no contract documents exist; `maintenance.csv` has no payment-status field and vendors aren't customers. Both are answered "not available + why," never fabricated. We do **not** synthesize a placeholder document to fill the gap.
- **Data defects are preserved, not cleaned** — `Contract ID` holds job titles (treated as a role label); End<Start rows are kept and may be flagged; malformed sources are dropped (mapped with their defect), never silently "fixed."
- **Two deploy units** — the Next.js frontend (Vercel) + the Python agent backend (Vercel Python Functions / Render / Fly), the accepted cost of faithfully reusing the user's Python skill.
