# Agentic AI Business Knowledge Assistant

A free-form business question is answered by a **Claude Agent SDK loop** that **navigates a `knowledge/` tree via human-readable `data_structure.md` maps** (the index — **no embeddings**), reads the real CSV/PDF files, and returns a **grounded answer with inline citations + a visible trace** of which files it read. Every claim traces to a resolvable **file + page** (PDF) or **file + row natural-key** (CSV).

> This is the **agentic re-platforming** of `Contract-Retriever-RAG` (which used a router + hybrid SQL/vector-RAG). Same product, same data, same golden questions, same "Aletheia" citation UX — only the **retrieval engine** changed. It is **not** "upload PDFs into a vector DB and do semantic search" (the client rejected that); this build has **no embeddings at all**. The differentiators: the agent **navigates and reads the real files (visible in the trace)**, **grounded generation**, and **source attribution you can trust**.

- **Live demo:** _the agentic deployment gets its own Vercel project + URL — added when it deploys (the original product stays live + untouched at its own URL)._
- **Architecture + diagram:** [docs/architecture.md](docs/architecture.md)
- **The feature (design + golden bar + eval gates):** [docs/features/agentic-knowledge-assistant/](docs/features/agentic-knowledge-assistant/README.md)

## How it works (30 seconds)

```
question → AGENT navigates knowledge/ via data_structure.md maps (no embeddings)
        → reads the processing reference, extracts with pandas / pdftotext+pdfplumber (progressive grep)
        → self-check (falsification view) → grounded answer, a [F:file#locator] cite on every claim
        → returns { answer, evidence, trace, validation } → cited answer + source panel + agent-trace panel
```

There is **no router and no vector index** — the agent reads the `data_structure.md` maps (the maps name two domains and state they share **no join key**), picks the relevant subtree, and reads the real files. The maps ARE the index *and* the honesty guardrail. Multi-source answers are **composed and cited separately**, never merged on an invented join.

## Stack
- **Next.js** (App Router) — the copied "Aletheia" UI (citation chips + source panel + agent-trace panel), Vercel-deployable.
- **Python FastAPI** backend running the **Claude Agent SDK** (`ANTHROPIC_API_KEY`, env-only) — the agent loop + the forked `kb-retriever` skill (English, no LightRAG).
- Tools: `Read · Glob · Grep · Bash`; extraction via **pandas** (CSV) + **pdftotext/pdfplumber** (PDF). **No embeddings, no SQLite, no bundled index.**
- The **`knowledge/`** tree (CSV + PDF) read-only, with a `data_structure.md` map per directory.

## Run locally
```bash
# Frontend
npm install
cp .env.example .env.local        # fill in ANTHROPIC_API_KEY + AGENT_BACKEND_URL
npm run dev                       # http://localhost:3000

# Agent backend (Python)
pip install -r backend/requirements.txt
# run the FastAPI app (see docs/ops/environment.md for the exact command + ANTHROPIC_API_KEY)
```
Details + deploy (two units: Vercel frontend + a Python host for the agent): [docs/ops/environment.md](docs/ops/environment.md).

## Quality gates (the immune system)
| Gate | Run | Proves |
|---|---|---|
| `doc-lint` | `npm run doc-lint` | No broken doc links/refs; the screenshot/gate ledger. |
| `doc-structure-lint` | `npm run doc-structure-lint` | Every `user-guide.md` follows the how-to skeleton. |
| Agentic eval | the eval harness (N≥5) | The four golden questions answer correctly across repeated runs: deterministic answer-assertions (figures + resolvable citations + honest-refusal + conflict-surfaced + no cross-domain leak) + **trace inspection** (right files opened) + the skill self-check + an LLM-judge. → [docs/features/agentic-knowledge-assistant/03-tests.md](docs/features/agentic-knowledge-assistant/03-tests.md) |
| Journey | the UI journey suite | The full flow against the running app — cited answer, resolvable `[F:..]` citations, the trace panel. Removable-handler-proof. |

CI: [.github/workflows/ci.yml](.github/workflows/ci.yml).

## Repo map
- `backend/` — the Python FastAPI agent (Claude Agent SDK loop + the forked `kb-retriever` skill).
- `app/` — the Next.js "Aletheia" UI + the `/api/ask` proxy to the agent.
- `knowledge/` — the read-only CSV/PDF tree + a `data_structure.md` map per directory (the index).
- `scripts/` — the doc lints.
- `docs/` — architecture, the `agentic-knowledge-assistant/` umbrella feature, gotchas, log, the doc/test playbook; `docs/archive/` holds the superseded v1 docs (provenance).
- `data/` — the original source CSVs + PDFs (committed).

Start in [docs/README.md](docs/README.md) · landmines + conventions in [CLAUDE.md](CLAUDE.md).
