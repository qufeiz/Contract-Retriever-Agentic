# Archive — v1 (vector + SQL) docs, superseded

These are the docs of the **original `Contract-Retriever-RAG`** product (router + hybrid SQL/vector-RAG + a deterministic `validateAnswer()`), kept for **provenance** because this repo is an **agentic re-platforming** of that shipped product. They describe an engine that **no longer exists here** — read them only to understand what was re-platformed, never as current truth.

The live, current docs are:
- [`../architecture.md`](../architecture.md) — the agentic architecture.
- [`../features/agentic-knowledge-assistant/`](../features/agentic-knowledge-assistant/README.md) — the single umbrella feature (design + golden bar + eval gates).

`docs/archive/` is excluded from `doc-lint` (see `scripts/doc-lint.config.mjs`), so these files are not part of the live doc surface and won't bounce the build.

| Archived | What it was | Superseded by |
|---|---|---|
| `contract-intelligence/`, `case-file-qa/`, `maintenance-spend-intelligence/` | The v1 per-domain feature folders (SQL/RAG, `[S:..]/[P:..]` tokens, `validateContractAnswer` etc.) | The single `agentic-knowledge-assistant/` umbrella (one engine, one golden bar, one eval harness; goldens kept as `02` sections). |
| `shared-engine/` | The v1 shared retrieval engine reference (loader, embeddings, router, `validateAnswer`, SQLite) | `architecture.md` + the agentic eval gates (`features/agentic-knowledge-assistant/03-tests.md`). |
| `sqlite-on-serverless.md` | A v1 gotcha about bundling SQLite on serverless | **Seal-decayed** — there is no SQLite in the agentic build (no embeddings, no bundled DB; the agent reads `knowledge/` files directly). |
| `CLIENT-DELIVERABLE.md` / `.pdf` | The v1 client-facing pitch (three SQL/RAG capabilities) | A new agentic client deliverable is a later task, not this slice. |
