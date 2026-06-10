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
4. **The API** (`backend/main.py`). FastAPI: the synchronous `/api/ask`, the **async-job** pair `POST /api/ask/jobs` + `GET /api/ask/jobs/{id}` (submit→poll, see the Deploy gate's async-job note), and `/health`. Returns 503 if no key — never fabricates. The Next.js `app/api/ask/route.ts` + `app/api/ask/jobs/[…]/route.ts` are thin proxies to them.
5. **The UI adaptation** (`app/page.tsx`). Kept the Aletheia masthead / ask form / citation chips / click-to-source / validation panel. Adapted: citation grammar `[S/P:..#n]` → `[F:..#loc]`; the routing panel → the **agent TRACE** panel (the maps read + files opened), now **streamed live** while an async job runs; `evidence.rows/chunks` → a single `evidence[]`. The ask handler submits to `/api/ask/jobs` then polls for the live trace + final answer.
6. **The gates** (`backend/validate.py` + `backend/eval/`). The validator unit tests (`backend/tests/`) + the repeated-N golden eval harness (`backend/eval/run.py`).

### Model + cost

Default agent model `claude-sonnet-4-6` (`AGENT_MODEL` env). The LLM-judge in the eval uses `claude-haiku-4-5` (cheap). The key lives only in the gitignored `.env` (locally) and as a **Fly secret** in prod (+ the Vercel env for the proxy URL) — never committed, never baked into the image.

---

## Hardening (the public surface)

The deployed `/api/ask` is internet-exposed, so the agent loop is a prompt-injection / RCE surface (it shells out to `pdftotext` + a pandas one-liner under `bypassPermissions`). Two layers contain it:

**1. The read-only tool gate — a `PreToolUse` hook (`backend/agent.py::_pre_tool_use`).** This is the security boundary. The SDK consults it before every tool call and a `permissionDecision: "deny"` genuinely blocks execution (the tool never runs; the model sees the deny reason). The allow-list:
- `Read`/`Glob`/`Grep` only when scoped under `knowledge/` (a path or a `knowledge/…` pattern).
- `Bash` only for read-only extraction over `knowledge/`: `pdftotext`, a **write-and-network-free** `python` pandas one-liner, `grep`/`find`(no `-exec`)/`head`/`cat`/etc. — with **no** redirection (`>`), command-substitution (`` ` ``/`$(`), pipes, package/deploy tools, or path escape (`..`, `/etc`).
- Everything else (`Write`, `Edit`, `WebFetch`, `WebSearch`, `Task`, …) is **denied**.

> ⚠️ **Why a hook, not `can_use_tool` or `allowed_tools`.** On this SDK/CLI version `allowed_tools` only pre-approves which tools the model may attempt (the CLI auto-approves them — not a boundary), and the `can_use_tool` callback was verified to be **never invoked** on the `query()` path (a spy logged zero decisions). Only the `PreToolUse` hook reliably fires and blocks. See [docs/gotchas/public-agent-hardening-hook-not-callback.md](../../gotchas/public-agent-hardening-hook-not-callback.md).

**2. Input guards (`backend/main.py` + `config.py`).** A length cap (`MAX_QUESTION_CHARS=600` → HTTP 413) and a per-IP rolling rate limit (`RATE_LIMIT_MAX` per `RATE_LIMIT_WINDOW_SEC` → HTTP 429) so an abusive caller can't bleed agent runs. CORS is restricted to the demo origin via `ALLOWED_ORIGINS`.

A hard refusal of a hijacked prompt comes back as free prose (no contract blocks); `_extract_output` returns it as an un-grounded answer rather than 500-ing. **Locked by `backend/tests/test_hardening.py`** (the allow/deny matrix) + `test_extract_json.py::test_free_prose_refusal_does_not_crash`, and verified live: an `/etc/passwd` + key-print injection against the deployed app returns no system data and no key.

---

## Deploy / migration gate

There is **no schema migration** (no DB). The "migration" is the data placement + the deploy wiring:

- **Data presence is a hard gate** (`03` Layer F): the `knowledge/` tree must contain the four usable files + the four `data_structure.md` maps + the `_dropped/` map. A missing file is a RED, not a skipped test.
- **Deploy topology (LIVE):** the Next.js frontend on **Vercel** (`https://aletheia-agentic-demo.vercel.app`) proxies `/api/ask` to the Python FastAPI backend on **Fly.io** (`https://aletheia-agentic.fly.dev`, set via `AGENT_BACKEND_URL`). The backend needs a real container — the Claude Agent SDK spawns the `claude` CLI and the kb-retriever skill shells out to `pdftotext` — so it runs the bundled [`Dockerfile`](../../../Dockerfile) (Python 3.12 + Node + `poppler-utils` + the pinned `@anthropic-ai/claude-code` CLI; `knowledge/` + `.claude/skills/` + `backend/` baked in), serving uvicorn on Fly port 8080. [`fly.toml`](../../../fly.toml) wires the HTTP service + a `/health` check; the key is a **Fly secret** (`fly secrets set ANTHROPIC_API_KEY=…`), never in the image. Single machine (the in-process rate limiter assumes one instance).
- **Keyless CI gate** (`.github/workflows/ci.yml`): `doc-lint` + `doc-structure-lint` + `typecheck` + `npm run test:agent` (the validator unit tests). The **eval harness** (`eval:agent`) calls the real Anthropic API and runs as a separate **key-gated** job — see [docs/testing/README.md](../../testing/README.md).
- **Resolved constraint — the Vercel request cap vs. agent latency (async-job path).** Vercel's serverless function ceiling is a hard **300s**, but the heaviest query — **G-1, the 38-row contract table — takes several minutes** end-to-end, so a *synchronous* `/api/ask` proxy **504s** on it (`FUNCTION_INVOCATION_TIMEOUT`). The fix, now live, is an **async-job transport** that keeps the long run off the request path:
  - `POST /api/ask/jobs` creates a job and returns a `job_id` **immediately** (well under any cap); the agent runs in a **background task on Fly** (no request ceiling).
  - The frontend then **polls** `GET /api/ask/jobs/{id}` (short requests, ~1.5s cadence), streaming the **live agent trace** as it works and reading the final cited answer when `status` is `done`. The job store is in-process (single-machine Fly, same assumption as the rate limiter); finished jobs are pruned after `JOB_TTL_SEC` (default 15 min). Locked by [`backend/tests/test_async_jobs.py`](../../../backend/tests/test_async_jobs.py) (lifecycle: submit→202, poll streams trace, final poll carries the full Aletheia contract, errors surface as `status:error`, overlong → 413, unknown id → 404).
  - The **synchronous** `POST /api/ask` is kept for direct-to-Fly / back-compat callers (no proxy in front, no cap). The async path is what the **public Vercel demo** uses, so **no golden query 504s** — including G-1.
- **Prod-verify runbook:** the post-deploy G-1…G-4 + Hebrew + citation-chip checks from `03` §Prod-verify, run against the **public Vercel URL** (G-1 now completes there via the async path — no 504).

> The current parent project (`Contract-Retriever-RAG`) stays **live and untouched** — all of the above is in the new fork only.

## Screenshots & journey-suite

The 6 golden screenshots (the README ledger / user-guide images) were captured by
[`scripts/capture-golden-screenshots.mjs`](../../../scripts/capture-golden-screenshots.mjs) driving
the **live demo** (`CAPTURE_BASE_URL=https://aletheia-agentic-demo.vercel.app`) — real agent
round-trips, not mocks — and committed to
[`docs/features/agentic-knowledge-assistant/images/`](images/). Each shot is pinned to
`asOfDate=2026-06-09` so the "38 contracts" count is stable. To re-capture (browser already in the
Playwright cache):

```bash
CAPTURE_BASE_URL=https://aletheia-agentic-demo.vercel.app \
  node scripts/capture-golden-screenshots.mjs        # writes the 6 PNGs into images/
```

Against a **local** stack instead, run `npm run start` (frontend :3000) + uvicorn (backend :8000,
needs `ANTHROPIC_API_KEY`) and omit `CAPTURE_BASE_URL`.

The Playwright **journey suite** (`tests/journeys/agentic-knowledge-assistant.spec.ts`) is the
behavioral gate (`npm run test:journeys`) — it asserts the real cited answer + resolvable `[F:..]`
chips + the trace panel, removable-handler-proof. The **content** is independently proven by the
eval harness (`backend/eval/run.py`), the stronger gate, which drives the real agent over the real
`knowledge/` tree across N runs.
