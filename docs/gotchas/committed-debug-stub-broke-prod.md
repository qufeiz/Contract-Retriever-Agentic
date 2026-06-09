# A removable-handler probe stub got committed + deployed, forcing every answer to "Rejected"

> **Confirmation status: SEALED (2026-06-09).** Root cause = a `return { ok: false, … "FORCED: simulated broken citation" }` early-return left at the top of `validateAnswer()` from a removable-handler probe, committed in b66d88e and deployed. It forced EVERY answer to render "✗ Rejected by validateAnswer()" on the live deploy → all four feature journeys would have failed against that deploy. Fixed in 93b7921 (stub removed); confirmed by 50/50 unit + 13/13 journey tests vs the live deploy after redeploy. Re-open if a `FORCED:`/`SIMULATED` marker ever reaches `main`.

**The lesson (two of them).**

1. **A removable-handler probe is a temporary, local experiment — it must NEVER be committed.** When you flip a gate to "always fail" (or a handler to a no-op) to prove a test bites, **revert it before you stage**. A committed probe stub silently breaks the exact thing the gate protects.

2. **META-MISS — the real failure was declaring done without re-running the journey suite against the FRESH deploy.** Two things masked the stub locally: (a) a **stale `.next`** made `npm run build` + the local journey run pass against an old bundle, and (b) I deployed and reported "done" before running the journey suite against the *new* production URL. The probe only manifested on the live deploy, where I hadn't looked.

**Enforcement (strongest-fitting):**
- **CI / test (mechanical):** `doc-lint` now scans `lib/` for a forbidden-marker stop-list (`FORCED:`, `SIMULATED`, `simulated broken`, `removable-handler probe`) and **fails the build** if one reaches a tracked source file. A debug stub can't be merged. (See `scripts/doc-lint.config.mjs` → `forbiddenSourceMarkers`.)
- **Process (the META-MISS fix):** the build is "done" only after the **journey suite runs GREEN against the freshly-deployed production URL** — not against localhost, and not against a possibly-stale `.next`. Always `rm -rf .next` before a release build when in doubt, and always run `JOURNEY_BASE_URL=<prod> npx playwright test` *after* `vercel --prod`.

**Enforced by:** the `doc-lint` forbidden-marker check + this gotcha + the post-deploy journey-vs-live step in `docs/testing/README.md`. Linked both ways.
