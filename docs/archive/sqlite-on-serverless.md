# Bundled SQLite fails to open on Vercel serverless ("unable to open database file")

> **Confirmation status: SEALED (2026-06-09).** The first prod deploy returned 0
> rows for EVERY structured query (the RAG/PDF path worked); `validateAnswer()`
> correctly rejected the resulting ungrounded answer. Root cause + fix verified by
> the live API returning the 38-contract / 788-invoice goldens after redeploy.
> Tested via `tests/journeys/engine-grounded-answer.spec.ts` (structured route)
> against the running app. Re-open if structured queries return empty in prod.

**The lesson:** on Vercel/Lambda, a bundled `*.sqlite` is reachable with
`readFileSync` (it traces like a static asset, which is why the prebuilt
`vectors.json` worked) **but `better-sqlite3`'s read-only file-open of that same
traced path fails** with `SQLITE_CANTOPEN` / "unable to open database file". And
`new Database(buffer)` is NOT supported (the constructor only takes a path or
`:memory:`; there is no static `deserialize`).

**The fix (in `lib/engine/retrieval.ts`):** read the bundled bytes with
`readFileSync` (which forces the file to be traced into the function), write them
to the writable `/tmp`, and open `better-sqlite3` from there.

**Also required:** build the DB with `journal_mode = DELETE`, not `WAL`
(`lib/engine/loader.ts`). A WAL DB copied as a single file without its `-wal`
sidecar can be missing rows; DELETE keeps the `.sqlite` self-contained so the
copy is complete.

**Why the green checks didn't catch it (META-MISS):** the unit + journey suites
ran against the **local** server, where the plain file-open works — so they were
green while prod was broken. The enforcement that now catches it: the journey
suite is the prod gate, and the final pass runs it with
`JOURNEY_BASE_URL=<vercel-url>` so the structured route is asserted **against the
deployed function**, not just localhost. (See `docs/testing/README.md`.)

**Enforced by:** the structured-route journey gate run against the live URL +
this gotcha. Linked both ways.
