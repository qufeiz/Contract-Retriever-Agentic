// doc-lint config — the PROJECT MAP (which dirs are active, what's exempt and WHY).
// The engine (doc-lint.mjs) stays generic; the taxonomy lives here.
// Every exemption MUST carry its rationale — an exemption with no rationale is how rot hides.

export default {
  // Active markdown roots: linted for broken links + dead references.
  // A frozen archive (none yet) would be excluded here.
  activeTopLevelDocs: ["CLAUDE.md", "README.md"],
  activeDirs: ["docs"],

  // Dirs never linked-checked (frozen history / generated). None yet.
  excludeDirs: [".git", "node_modules", ".next", "dist", "data-index", "docs/archive"],

  // ── Journey-spec coverage ───────────────────────────────────────────────
  // Every *.spec.ts under this dir must be documented in the testing doc, and
  // vice-versa, so a new journey can't ship undocumented.
  journeySpecDir: "tests/journeys",
  testingDoc: "docs/testing/README.md",

  // ── Screenshot / gate ledger ────────────────────────────────────────────
  // Each feature folder's README.md is a ledger. doc-lint fails the build if a
  // shipped screenshot (images/*.png) isn't in the ledger, or a feature gate
  // (a *<feature>*.spec.ts) isn't listed.
  // Armed now that the first real feature (contract-intelligence) ships a ledger +
  // golden screenshots (bootstrap §A Step 5). A feature folder with no captured
  // screenshots yet (still being authored) is not held to the ledger; the moment it
  // ships a screenshot, a ledgered README is required.
  // The shared-engine folder is INFRASTRUCTURE, not a user-facing feature with a
  // capability/screenshot ledger — it is exempt.
  requireFeatureLedger: true,
  featuresDir: "docs/features",
  ledgerExemptFeatures: ["shared-engine"], // infrastructure ref doc, not a capability ledger

  // ── Forbidden source markers (anti debug-stub) ──────────────────────────
  // A removable-handler probe (flipping a gate to "always fail" to prove it bites)
  // is a LOCAL experiment that must be reverted before staging. One got committed +
  // deployed once and forced every answer to "Rejected" in prod
  // (docs/gotchas/committed-debug-stub-broke-prod.md). This scans tracked source for
  // those markers and fails the build, so a debug stub can't be merged.
  sourceDirs: ["backend", "app", "scripts"],
  forbiddenSourceMarkers: [
    "FORCED:",
    "SIMULATED:",
    "simulated broken",
    "removable-handler probe",
    "// FORCE FAIL",
  ],
};
