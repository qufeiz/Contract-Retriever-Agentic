#!/usr/bin/env node
// doc-structure-lint — enforces the how-to section skeleton over every
// docs/features/<f>/user-guide.md (Diátaxis how-to contract, doc-structure.md §2b).
// Mechanical subset only; "is the screenshot golden?" stays an author self-check.
import { readFileSync, readdirSync, statSync, existsSync } from "node:fs";
import { join } from "node:path";

const ROOT = process.cwd();
const FEATURES = join(ROOT, "docs", "features");

// ── The skeleton config (keep in sync with doc-structure.md §2b) ──────────
const REQUIRED_FRONTMATTER = ["title", "type", "feature", "summary"];
const REQUIRED_TYPE = "how-to";
const MAX_STEPS = 10;
const PLACEHOLDER_TOKENS = [/\blorem ipsum\b/i, /\bTODO\b/, /\bTBD\b/, /\bFIXME\b/, /<placeholder>/i];

const bad = [];

function lintGuide(path, label) {
  const src = readFileSync(path, "utf8");

  // 1. Frontmatter present & valid
  const fm = src.match(/^---\n([\s\S]*?)\n---/);
  if (!fm) {
    bad.push(`${label}  missing frontmatter block`);
  } else {
    const body = fm[1];
    for (const key of REQUIRED_FRONTMATTER) {
      if (!new RegExp(`^${key}\\s*:`, "m").test(body)) {
        bad.push(`${label}  frontmatter missing key → ${key}`);
      }
    }
    const typeMatch = body.match(/^type\s*:\s*(.+)$/m);
    if (typeMatch && typeMatch[1].trim().replace(/['"]/g, "") !== REQUIRED_TYPE) {
      bad.push(`${label}  frontmatter type must be "${REQUIRED_TYPE}" (got "${typeMatch[1].trim()}")`);
    }
  }

  const afterFm = fm ? src.slice(fm[0].length) : src;
  const lines = afterFm.split("\n");

  // 2. Exactly one H1, followed by a one-line summary block (blockquote or italic)
  const h1s = lines.filter((l) => /^#\s+\S/.test(l));
  if (h1s.length !== 1) {
    bad.push(`${label}  must have exactly one H1 (found ${h1s.length})`);
  } else {
    const h1Idx = lines.findIndex((l) => /^# \s*\S/.test(l) || /^# \S/.test(l));
    let j = h1Idx + 1;
    while (j < lines.length && lines[j].trim() === "") j++;
    const next = (lines[j] || "").trim();
    if (!(next.startsWith(">") || /^[*_].+[*_]$/.test(next))) {
      bad.push(`${label}  H1 must be immediately followed by a one-line summary (blockquote or italic)`);
    }
  }

  // 3. An Overview (H2) before the first numbered step
  const headings = lines
    .map((l, i) => ({ i, m: l.match(/^##\s+(.+)$/) }))
    .filter((x) => x.m)
    .map((x) => ({ i: x.i, text: x.m[1].trim() }));
  const firstStepIdx = headings.findIndex((h) => /^\d+\.?\s/.test(h.text));
  const overviewIdx = headings.findIndex((h) => /overview|what it does/i.test(h.text));
  if (overviewIdx === -1) {
    bad.push(`${label}  missing an Overview (H2) section`);
  } else if (firstStepIdx !== -1 && overviewIdx > firstStepIdx) {
    bad.push(`${label}  Overview must come before the first numbered step`);
  }

  // 4. At least one numbered step; step count <= MAX_STEPS
  const stepHeadings = headings.filter((h) => /^\d+\.?\s/.test(h.text));
  if (stepHeadings.length === 0) {
    bad.push(`${label}  must have at least one numbered step section (## 1. ...)`);
  }
  if (stepHeadings.length > MAX_STEPS) {
    bad.push(`${label}  too many steps (${stepHeadings.length} > ${MAX_STEPS})`);
  }

  // 5. Each numbered UI step has a screenshot OR code block (no wall of prose).
  //    Steps named Result/Verify/Success are exempt.
  for (let s = 0; s < stepHeadings.length; s++) {
    const h = stepHeadings[s];
    if (/result|verify|success/i.test(h.text)) continue;
    const start = h.i;
    const end = s + 1 < stepHeadings.length ? stepHeadings[s + 1].i : lines.length;
    const block = lines.slice(start, end).join("\n");
    const hasImage = /!\[[^\]]*\]\([^)]+\)/.test(block);
    const hasCode = /```/.test(block);
    if (!hasImage && !hasCode) {
      bad.push(`${label}  step "${h.text}" has no screenshot or code block (no-wall-of-prose rule)`);
    }
  }

  // 6. No placeholder/lorem stub tokens
  for (const tok of PLACEHOLDER_TOKENS) {
    if (tok.test(src)) {
      bad.push(`${label}  contains a placeholder/stub token → ${tok}`);
    }
  }
}

if (existsSync(FEATURES)) {
  for (const feat of readdirSync(FEATURES)) {
    const featDir = join(FEATURES, feat);
    if (!statSync(featDir).isDirectory()) continue;
    const guide = join(featDir, "user-guide.md");
    if (existsSync(guide)) lintGuide(guide, `docs/features/${feat}/user-guide.md`);
  }
}

if (bad.length) {
  console.error("✗ doc-structure-lint:\n" + bad.map((b) => "  " + b).join("\n"));
  process.exit(1);
}
console.log("✓ doc-structure-lint: all user-guides follow the how-to skeleton");
