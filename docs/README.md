# Docs index

The load-on-demand home for everything that doesn't belong in the always-loaded `../CLAUDE.md`. Start with `architecture.md` to understand the system, then read the area your task touches.

## Index
| Doc | What it is |
|---|---|
| [architecture.md](architecture.md) | The shape of the system: the agentic engine (navigation → retrieval → grounding/citation), the honesty contract, the data model, verification, the Hebrew seam. **Start here.** |
| [features/agentic-knowledge-assistant/](features/agentic-knowledge-assistant/README.md) | **The single (umbrella) feature** — design + golden bar (the four questions) + the `data_structure.md` map contents + the trimmed-skill spec + the eval gate list + the screenshot/gate ledger. |
| [product/data-quality-assessment.md](product/data-quality-assessment.md) | The canonical row-level evaluation of all 9 sources (usable vs dropped + the exact defect each). Carried forward from v1; the maps embed these verdicts. |
| [product/feature-map.md](product/feature-map.md) | Which capabilities the usable sources support, and which are deferred + why. |
| [log.md](log.md) | Append-only decisions & incidents, newest first. The "why is it like this" trail. |
| [ops/environment.md](ops/environment.md) | Env vars (`ANTHROPIC_API_KEY`, `AGENT_BACKEND_URL`), secrets hygiene, local run (frontend + Python agent), deploy. |
| [testing/README.md](testing/README.md) | The test suites + the agentic eval discipline (the gate list lives in the feature's `03-tests.md`). |
| [gotchas/README.md](gotchas/README.md) | Sealed postmortems (footguns). Teaches the "seal" convention. |
| [meta/ai-native-docs-playbook.md](meta/ai-native-docs-playbook.md) | The portable doc/test methodology this repo is built on. |
| [archive/](archive/README.md) | The superseded **v1 (vector+SQL)** docs — provenance only, excluded from doc-lint. |

## Feature docs
This product is **one engine** answering all four golden questions, so it is documented as a **single umbrella feature** (not per-domain folders). The per-domain goldens live as sections inside its `02-examples.md`.

| Feature | Folder |
|---|---|
| Agentic Knowledge Assistant (the whole engine) | [features/agentic-knowledge-assistant/](features/agentic-knowledge-assistant/README.md) — `00`–`03` + `README` ledger; the Engineer adds `04-implementation.md` + `user-guide.md`. |

## Maintaining these docs

**The anti-drift rule:** every active doc must stay true to the code/data in the *same change* that alters it. `doc-lint` catches broken links and dead references; it cannot catch a stale *description* — that's on you.

### Which doc to update when
| When you change… | Update… |
|---|---|
| Any incident / decision / non-obvious fix | `log.md` — always |
| System structure / navigation / retrieval / the honesty contract | `architecture.md` |
| The golden bar, the `data_structure.md` map contents, the skill spec, or the eval gates | `features/agentic-knowledge-assistant/` (`00`–`03`) |
| The `knowledge/` tree (a file added/moved/dropped, a defect found) | the relevant `knowledge/**/data_structure.md` map **and** the feature's `02-examples.md` map spec (they must agree) |
| What the feature *does* (a user-facing capability) | the feature's `user-guide.md` + a golden screenshot + the `README.md` ledger row |
| An env var | `ops/environment.md` (+ `.env.example`) |
| A sealed footgun | a `gotchas/` file (+ a `log.md` one-liner) |

### Doc types (Diátaxis)
Every page is one of: **how-to** (`features/*/user-guide.md` — numbered, action-first steps), **reference** (facts/internals), **explanation** (`architecture.md`). The per-page contract and the how-to skeleton are enforced by `../scripts/doc-structure-lint.mjs`.
