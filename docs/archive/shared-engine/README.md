# Shared engine

The **infrastructure** every domain feature is built on — documented once, not per feature. This is not a user-facing capability with its own screenshot/gate ledger; it's the retrieval engine. (doc-lint exempts it from the feature ledger requirement for that reason — see `../../../scripts/doc-lint.config.mjs`.)

| Doc | What |
|---|---|
| [reference.md](reference.md) | Engine internals + runbook: the request loop, modules, the bundled index, data quality, prod debugging, extensibility. |
| [../../architecture.md](../../architecture.md) | The system-level explanation (why it's shaped this way) + the data-flow diagram. |

**Regression gate:** the engine's end-to-end behavior is guarded by the journey spec `tests/journeys/engine-grounded-answer.spec.ts` (see [../../testing/README.md](../../testing/README.md)) and the unit gate `tests/unit/validate-answer.test.mts` (content-fidelity: passes goldens, fails toys).
