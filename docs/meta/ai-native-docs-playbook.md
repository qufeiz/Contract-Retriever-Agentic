# AI-native docs — a portable playbook

**What this is:** the methodology behind how these docs are structured — distilled to be **copied into other repos**. It's repo-agnostic. The goal of "AI-native docs" is simple: a fresh agent (or human) gets correctly oriented fast, can't break prod by accident, and the docs **can't silently drift** from the code.

**How to use it:** read the Principles, copy the Templates into a new repo, wire the doc-lint, then run the Cold-Onboard test to find what's missing.

---

## Principles

1. **Budget the always-loaded surface; `CLAUDE.md` is a map + landmines, not a manual.** `CLAUDE.md` (and equivalents) load into *every* session, so their length is a **per-session token tax** paid before any work starts — this is *the* constraint that makes docs AI-native rather than just good. Size and order it so an agent absorbs the minimum it needs to act safely, and push the rest to **load-on-demand** (`docs/`, read just-in-time). Concretely: lead with the *landmines* (the few actions that cause irreversible damage), then a "where things are" table, then terse conventions that **point** to detail. Depth lives in `docs/`, not here.

2. **Progressive disclosure.** index → folder READMEs → detail doc → code. Each folder self-describes; agents read **just-in-time** (only the area their task touches). Link to a folder's `README.md`, not the folder — an agent following a bare dir link gets a listing, not content.

3. **State → Enforce → Reinforce, for every rule.** *State* it where it's seen (CLAUDE.md / README). *Enforce* the mechanizable part in CI (a lint). *Reinforce* the judgment part with a named convention + an example. **A rule nobody enforces decays.** This is the core move.

4. **An append-only decision log.** One file, newest-first, `[date] type | title` + a few lines + links. It gives an agent *causality* ("why is auth like this") — exactly what a context-limited agent can't infer from code. Teach its format in its own header.

5. **The confirmation gate ("seal").** Only document a fix as *solved* once it's **tested AND user-confirmed**. Postmortems carry a labeled `Confirmation status: SEALED (date — who/how)` line, or list what's verified vs. still open. **A wrong "it's fixed" doc is worse than none** — the next agent trusts it. The seal certifies correctness *at write time*, not forever: treat an old gotcha as a hypothesis, and if a doc names a file/flag, confirm it still exists before relying on it.

6. **Teach the practice, not the instance.** One example isn't a convention. If you want a pattern reproduced, *name it* as a rule (e.g. "every postmortem opens with a Confirmation status line"), don't leave a single instance to be reverse-engineered.

7. **One authoritative home per concern; everything else points to it.** Duplication is drift waiting to happen. When tempted to add a doc that restates existing rules, **consolidate + link** instead.

8. **Add structure only where it pays for itself.** Distinguish *reference* folders (fixed set, edited) from *append-driven* ones (new files over time). Authoring instructions belong only in append-driven folders with a non-obvious format. Don't template every folder; don't hand-write what can be generated; don't lint a frozen archive.

9. **Tooling must match the docs' claims.** If a doc calls a test suite "the source of truth," there must be a one-command way to run it *and* it must be in the gate. Docs that promise rigor the pipeline doesn't enforce are lying — and an agent will believe them.

10. **Generated beats hand-written for anything that mirrors code.** Schema dictionaries, API lists, type tables — generate them or skip them. A hand-maintained mirror of the code drifts the moment the code changes and no lint can catch it.

11. **Make failures self-describing; don't trust laggy logs.** Put the diagnostic *in the error text* the user reads back. For aggregated/platform logs that lag minutes, document a real-time signal instead (a direct API call, a session inspector). (A debugging-method lesson, but it belongs in the docs.)

12. **Access ≠ a key.** Tell agents which platform access is self-serve (a token/env var they can set) vs. an **interactive login they can't do** (browser/device-code) and must hand to the user. Without this, an agent burns turns failing at `gcloud auth login`.

---

## The structure (a starting layout)

```
CLAUDE.md                  # auto-loaded: landmines + "where things are" + terse conventions → points to docs/
AGENTS.md                  # (optional) pointer to CLAUDE.md for other tools
.env.example               # all dev var NAMES + placeholders (no secrets)
docs/
  README.md                # the index + the "maintaining these docs" conventions (the single home)
  architecture.md          # how it fits together: stack, data flow, the model — "start here to understand"
  log.md                   # append-only decisions/incidents, newest first
  ops/README.md            # platform reference + landmines + an Access/auth matrix
  gotchas/README.md        # postmortems; teaches the "seal" convention
  testing/README.md        # what suites exist + how to run + points to the authoring guide
  archive/README.md        # frozen history — "do not treat as current", not linted
  meta/                    # this playbook lives here (portable, not project content)
scripts/doc-lint.mjs       # the immune system (CI)
.github/workflows/ci.yml   # runs doc-lint + typecheck + build on every push/PR
```

---

## Copyable templates

> Take what fits. The `CLAUDE.md` / `log.md` / seal / "which doc when" / access-matrix / doc-lint templates are **universal**. Anything naming a test taxonomy (journey/action specs, Playwright configs) is **this repo's choice** — adapt it to your stack. And keep the **one-source, many-pointers** rule: write the rules once in `CLAUDE.md`, then let `AGENTS.md`, `.cursorrules`, `.github/copilot-instructions.md` be thin pointers to it — never parallel copies.

### `CLAUDE.md` skeleton
```markdown
# <Project> — agent guide
Auto-loaded every session. Map + landmines. Detail in docs/ — read docs/README.md and docs/log.md first.

## 🚨 Landmines — do not get these wrong
1. <the action that causes irreversible damage> → <doc>
2. <push to main auto-deploys? one DB? build-time env?> → <doc>

## Where things are
| Need | Doc |
|---|---|
| Understand the app | docs/architecture.md |
| Run it locally · env vars | README.md · docs/ops/environment.md |
| Tests | docs/testing/ |
| Decisions & incidents | docs/log.md |

## Working conventions
- When something non-obvious happens → add a docs/log.md entry + update the relevant doc, same change.
- Keep active docs true to the code. Which doc? → the "Which doc to update when" table in docs/README.md.
- <test rule: a passing test must mean the user can actually use the feature>
```

### `log.md` header (teaches its own format)
```markdown
# Project log — decisions & incidents
Append-only. **Newest first.** Format: `## [YYYY-MM-DD] type | title`, then a few lines + links.
Types: incident · decision · feat · fix · reorg.
> When something non-obvious happens, add an entry here and update the relevant doc.
```

### Postmortem "seal" block (top of every `gotchas/*` file)
```markdown
> **Confirmation status: SEALED (YYYY-MM-DD).** <what's verified> — tested via <regression test>
> AND <who> confirmed on <what environment>. Root cause closed.
> (If not sealed: list what's verified vs. open, and "re-open if X recurs".)
```

### "Which doc to update when" table (in `docs/README.md`)
```markdown
| When you change… | Update… |
|---|---|
| Any incident / decision / non-obvious fix | log.md — always |
| App structure / data flow / a table | architecture.md |
| What a feature *does* | the area doc + run the feature-design process |
| A platform's keys / deploy / access | the ops/ file |
| An env var | ops/environment.md (+ .env.example) |
| A sealed footgun | a gotchas/ file (+ a log.md one-liner) |
```

### Access / auth matrix (in `ops/README.md`)
```markdown
| Platform | How access works | Agent self-serve? |
|---|---|---|
| <CLI> | token in .env | ✅ if set, else `! <cli> login` |
| GitHub | push over creds | ⚠️ workflow files need `workflow` scope |
| <cloud> | interactive login | ❌ → `! <cloud> auth login` |
Rule: if a command opens a browser / device-code prompt, hand it to the user via `! <command>`.
```

### The immune system — `doc-lint` (the one template you must not skip)
A small, zero-dependency Node script that **fails CI** on broken relative links and references to deleted files. It catches *mechanical* drift only — stale prose is still human judgment. Add project-specific checks as you need them. The usual progression of checks:

1. **Broken relative links** — every relative markdown link (`[text]` followed by `(target)`) resolves to a file that exists (the core below).
2. **Dead config/spec references** — a doc that names a config or spec file fails if that file is gone.
3. **Spec coverage** — every test spec on disk is documented in the testing doc (and vice versa), so a new journey can't ship undocumented.
4. **The gate/screenshot ledger** — when a feature claims a *gate* or a *golden screenshot*, lint that the named artifact exists (the spec file, the image), so "documented as gated" can't drift from "actually gated." This is the check that turns a feature-design self-check into a *mechanical* one.
5. **Per-page structure** — sort each doc into a Diátaxis content type (how-to / reference / explanation / tutorial), give the how-to a *fixed section skeleton*, and lint that skeleton so guides can't drift to ad-hoc layouts. The worked contract + validator: the `feature-design` skill's `doc-structure.md` + `doc-structure-lint`. ([diataxis.fr](https://diataxis.fr/))

Exclude genuinely frozen dirs (an `archive/`); **don't** reflexively exclude illustrative ones — keeping this very playbook under the lint is what would have caught the two self-description bugs an earlier draft shipped.

**The enforcement ladder — for any rule, reach for the strongest rung that fits: CI/test > forcing self-check > prose.** doc-lint is the CI rung for doc drift; a generated schema/API list is the CI rung for code-mirroring docs; a feature-design self-check is the middle rung for judgment a lint can't see ("is this the golden screenshot?"); prose is the floor, used only when the rule genuinely can't be mechanized. Prose is hope — climb as high as the rule allows.

**The ratchet — the floor only goes up.** When a real miss slips through *despite* a green check, don't just fix the symptom: strengthen **that check** so the miss can't recur, then link the gotcha and the enforcement both ways (the gotcha names where it's now caught; the check points back to the why). A specific miss should happen at most once. Don't manufacture a rule to look thorough — a new rung earns its place only when a real miss demands it.

A self-contained core to paste and grow:
```js
import { readFileSync, readdirSync, statSync, existsSync } from "node:fs";
import { join, dirname, normalize, relative } from "node:path";
const ROOT = process.cwd(), bad = [];
const walk = (d, a = []) => { for (const n of readdirSync(d)) {
  if ([".git","node_modules","dist"].includes(n)) continue;
  const p = join(d, n); statSync(p).isDirectory() ? walk(p, a) : n.endsWith(".md") && a.push(p);
} return a; };
const active = (f) => { const r = relative(ROOT, f).replaceAll("\\","/");
  return !r.startsWith("docs/archive/") && (r.startsWith("docs/") || ["CLAUDE.md","AGENTS.md","README.md"].includes(r)); };
const LINK = /\[[^\]]*\]\(([^)]+)\)/g;
for (const f of walk(ROOT).filter(active))
  readFileSync(f, "utf8").split("\n").forEach((line, i) => {
    for (const m of line.matchAll(LINK)) { const t = m[1].trim().split("#")[0].split("?")[0];
      if (/^(https?:|#|mailto:|tel:|data:)/.test(m[1].trim()) || !t) continue;
      if (!existsSync(normalize(join(dirname(f), t)))) bad.push(`${relative(ROOT,f)}:${i+1}  broken link → ${m[1]}`); } });
if (bad.length) { console.error("✗ doc-lint:\n" + bad.join("\n")); process.exit(1); }
console.log("✓ doc-lint: links OK");
```

---

## Techniques

- **The Cold-Onboard test.** Spawn a fresh agent, tell it to onboard from `CLAUDE.md` only and follow the trail, then **critique** it (X/10, where did the trail break, what couldn't you find). Removes author bias and finds the real gaps — it's how this repo found its missing run-script and the "which doc when" gap.
- **Delegation by pointer.** Good docs make subagents cheap: hand a worker *"read CLAUDE.md, the top log entry, architecture.md"* instead of re-explaining. You spend a few lines, not your context — then **verify the result independently** (run the build/tests yourself; don't trust the report).
- **State/Enforce/Reinforce in practice.** Want "docs stay true"? *State* it in CLAUDE.md, *enforce* the linkable part with doc-lint, *reinforce* the judgment with a "keep docs true in the same change" convention. Want "fixes are real"? *State* the seal gate, *enforce* nothing (can't), *reinforce* with the Confirmation-status convention + a template.

---

## Anti-patterns (what we deliberately did *not* do)

- **A second/third file restating the same rules.** Consolidate into one home + point. (We almost added a standalone "doc maintenance" file — the need was real, the form was wrong.)
- **A hand-written schema/data dictionary.** It mirrors the migrations and drifts instantly; generate or skip.
- **"How to write files here" in every folder.** Reference folders don't need it; only append-driven ones do.
- **Linting the archive.** Frozen history is allowed to reference old paths; exclude it.
- **Trusting "it works on my machine."** Reproduce on a real environment before declaring a fix sealed.
- **Green CI that checks nothing.** We found a `tsc --noEmit` that type-checked *zero* files. Verify your gates actually gate.
