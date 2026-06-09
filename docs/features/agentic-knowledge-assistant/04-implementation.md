# 04 — Implementation: Agentic Knowledge Assistant

Derived from: 01-design.md §workflow (the 6 single-spine steps → the build order) + 02-examples.md (the `data_structure.md` maps + the trimmed-skill spec, authored verbatim into the repo) + 03-tests.md (the gate list → the eval harness + the validator unit tests).

> This is the **engineer's build record**: the data model (the `knowledge/` tree + the agent output contract), the build order, and the deploy gate. It documents what was actually built, in the repo, to satisfy `01`–`03`.

---

## Data model

There is **no database and no vector index** — the model is a file tree plus a structured response.

### The knowledge tree (the "index" is human-readable maps)

```
knowledge/
├── data_structure.md                         ← root map: the two domains + the NO-join-key guardrail
├── school-operations/
│   ├── data_structure.md                     ← per-file notes (mislabeled Contract ID, absent fields)
│   ├── contracts.csv                          (1000 rows; cols: Contract ID*, Vendor, Start/End Date, Annual Cost)
│   ├── maintenance.csv                        (750 rows; cols: Ticket ID*, Vendor, Invoice, Labor/Parts/Total Cost, Completion Date)
│   └── _dropped/
│       └── data_structure.md                 ← five vetted-then-dropped sources + the named defect each
│           (enrollment.csv, payroll_v1.csv, payroll_v2.csv, invoice_volume.csv, people.csv)
└── carter-case/
    ├── data_structure.md                     ← Final Judgment Page 24; the real filing-date conflict
    ├── family-court-case-file.pdf            (the page-labelled court file; Final Judgment on printed PAGE 24)
    └── case-story.pdf                         (the 3-page corroborating narrative)
```

`*` `Contract ID` / `Ticket ID` are **mislabeled** (they hold role titles / category names). Contract rows are keyed by **(Vendor, End Date)**, not the id column. The maps state this so the agent reads it before answering — the maps **are** the guardrail (`03` Layer F asserts the guardrail lines survive).

### The agent output contract (`backend/models.py`)

Every `/api/ask` response — the exact shape the Aletheia UI consumes:

```jsonc
{
  "question": "...",
  "answer": "prose with inline [F:<file>#<locator>] citation tokens",
  "evidence": [ { "file": "<path under knowledge/>", "loc": "<locator>", "snippet": "..." } ],
  "trace":    [ { "kind": "map|open|grep|note", "detail": "..." } ],
  "validation": { "ok": true, "reasons": [] }
}
```

**Citation locator grammar** (`[F:<file>#<locator>]`):
- PDF page → `p<N>` where **N is the document's printed "PAGE N" label** (e.g. `p24`), not the physical pdftotext page. The validator bounds-checks against the printed labels.
- CSV row → `row=<Vendor>|<End Date>` (the natural key, since `Contract ID` is mislabeled).
- A computed aggregate or column-set citation → a short section name (`#computed`, `#columns`). Used for "the total spend" or an absence statement; the file must exist and an evidence item must back it.

`validation` comes from `validateAnswer()` (`backend/validate.py`) — the **content-fidelity gate**: every inline token must resolve to a real file + real printed-page / real row-key, or the answer is flagged rejected. This is the part of the parent's `validateAnswer()` that ports directly (`03` Layer F).

---

## Build order (mirrors `01`'s 6 workflow steps)

1. **Fork + tree.** Copied the parent repo into `Contract-Retriever-Agentic`, kept the Aletheia frontend, removed `lib/engine` (the vector+SQL engine), built the `knowledge/` tree + the four `data_structure.md` maps verbatim from `02`.
2. **The trimmed skill** (`.claude/skills/kb-retriever/`). Forked kb-retriever's skill, **English + no-LightRAG + no table-builder**, per `02`'s keep/drop table. Kept: hierarchical map navigation, read-the-reference-before-processing (in full, no `limit`), progressive grep + local reads, pandas/pdftotext, the falsification self-check, the honesty/cite/Hebrew rules. References: `pdf_reading.md`, `excel_reading.md`, `excel_analysis.md`.
3. **The agent loop** (`backend/agent.py`). A single conversational turn (not propose-schema→fill-table): the Claude Agent SDK `query()` runs the skill over `knowledge/`; the SDK tool-use stream is captured into the structured `trace`; the agent's final JSON is parsed **defensively** (see the gotcha) into `{answer, evidence}`; `validate()` adds `validation`.
4. **The API** (`backend/main.py`). FastAPI `/api/ask` (+ `/health`). Returns 503 if no key — never fabricates. The Next.js `app/api/ask/route.ts` is a thin proxy to it.
5. **The UI adaptation** (`app/page.tsx`). Kept the Aletheia masthead / ask form / citation chips / click-to-source / validation panel. Adapted: citation grammar `[S/P:..#n]` → `[F:..#loc]`; the routing panel → the **agent TRACE** panel (the maps read + files opened); `evidence.rows/chunks` → a single `evidence[]`.
6. **The gates** (`backend/validate.py` + `backend/eval/`). The validator unit tests (`backend/tests/`) + the repeated-N golden eval harness (`backend/eval/run.py`).

### Model + cost

Default agent model `claude-sonnet-4-6` (`AGENT_MODEL` env). The LLM-judge in the eval uses `claude-haiku-4-5` (cheap). The key lives only in the gitignored `.env` (+ the Vercel env) — never committed.

---

## Deploy / migration gate

There is **no schema migration** (no DB). The "migration" is the data placement + the deploy wiring:

- **Data presence is a hard gate** (`03` Layer F): the `knowledge/` tree must contain the four usable files + the four `data_structure.md` maps + the `_dropped/` map. A missing file is a RED, not a skipped test.
- **Deploy topology:** the Next.js frontend on Vercel proxies `/api/ask` to the Python FastAPI backend (`AGENT_BACKEND_URL`). `poppler-utils` (`pdftotext`) and the Python deps must be present wherever the backend runs.
- **Keyless CI gate** (`.github/workflows/ci.yml`): `doc-lint` + `doc-structure-lint` + `typecheck` + `npm run test:agent` (the validator unit tests). The **eval harness** (`eval:agent`) calls the real Anthropic API and runs as a separate **key-gated** job — see [docs/testing/README.md](../../testing/README.md).
- **Prod-verify runbook:** the post-deploy G-1…G-4 + Hebrew + citation-chip checks from `03` §Prod-verify, run against the new Vercel URL.

> The current parent project (`Contract-Retriever-RAG`) stays **live and untouched** — all of the above is in the new fork only.

## Screenshots & journey-suite (environment note)

The 6 golden screenshots (the README ledger / user-guide images) and the Playwright **journey suite**
(`tests/journeys/agentic-knowledge-assistant.spec.ts`) both require a working headless browser to
drive the live UI. In the build environment the Playwright Chromium install would not complete
(the 173 MB download finished but extraction did not persist a runnable binary across several clean
retries — an environment limitation, not a code issue). Consequently the screenshots were **not
captured** here and the journey suite was **not run locally**.

This was flagged honestly rather than faking the artifacts. The **content is fully proven by the
eval harness** (`backend/eval/run.py`) — the stronger gate — which drives the real agent over the
real `knowledge/` tree and asserts the same facts/citations/traces the screenshots would show.
**To capture the screenshots + run the journey suite** (in an environment with a browser):

```bash
npx playwright install chromium            # provision the browser
npm run start &                            # frontend :3000
python -m uvicorn backend.main:app &       # backend :8000  (needs ANTHROPIC_API_KEY in .env)
node scripts/capture-golden-screenshots.mjs   # writes the 6 PNGs into images/
npm run test:journeys                       # the live journey gate
```

The capture script and the journey spec are committed and ready; only the browser provisioning is
the gap. The user-guide image lines are marked "capture pending" until then.
