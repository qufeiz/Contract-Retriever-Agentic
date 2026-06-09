# 03 — Acceptance Gates: Agentic Knowledge Assistant

Derived from: 01-design.md §workflow (the 6 single-spine steps → a gate per step) + 02-examples.md (G-1…G-4 + Hebrew → a fixture per example, plus the `data_structure.md` maps + the trimmed-skill spec) + the user-approved verification strategy (deterministic answer-assertions + trace inspection + self-check + repeated-N + LLM-judge).

> **This is the gate list — *what* to assert, not the runnable test.** The Engineer writes the runnable **eval harness** at build and commits it as the permanent regression gate; the Verifier runs it independently. Every gate is **toy-proof**: if the agent is stubbed to a no-op or a plausible toy (vague answer, fabricated penalty/overdue, wrong/no file opened, silent conflict-resolution, a cross-domain leak), the gate must go **red**.

> **The honest framing (read first).** The parent product's gate was a **deterministic pure function** (`validateAnswer()` / `validateContractAnswer()` …) + fixed-seed journey tests — same input, same output. **An agent is non-deterministic** (file order, phrasing, run-to-run variance), so that exact unit gate does **not** transfer. This `03` is the **approved replacement** and is consciously a **looser-but-strong** guarantee. It rests on five layers: **(A)** a golden eval set, **(B)** deterministic answer-assertions that DO survive non-determinism, **(C)** trace inspection, **(D)** the skill's self-check, **(E)** repeated-N runs + an LLM-judge. (A)+(B)+(C) are deterministic and run every time; (E) makes a flaky pass red.

> **Pinned anchor:** all contract-expiry assertions use the injected **`asOfDate = 2026-06-09`** (window `[2026-06-09, 2026-09-07]`). The count **38** holds ONLY at this anchor; the fixture freezes it.

---

## Layer A — The golden eval set (the fixtures)

A committed eval set: each of **G-1, G-2, G-3, G-4** (EN) + their **Hebrew** twins + the **single-contract** variant (Skalith, expiry 2026-07-09, $25,629.50, penalty "not available"). Each fixture carries:
- the **required facts** (the figures/findings that must appear),
- the **required citations** (which file + page/row each fact must cite),
- the **required behavior** (honest-refusal fires / conflict surfaced),
- the **forbidden content** (fabrications + cross-domain tokens that must be absent),
- the **expected trace** (files that must be opened, and files that must NOT be opened).

The eval harness drives the **real** agent over the **real** `knowledge/` tree (no mocked retrieval) and scores each fixture against layers B–E.

## Layer B — A gate per workflow step (from `01`) + a fixture per example (from `02`) — deterministic, survives non-determinism

These are **pure checks over the agent's final answer + structured evidence + trace**, independent of phrasing/order. This is the agentic analogue of the parent's `validateAnswer()` — and it keeps most of the old guarantee, because the non-determinism is in *how* the agent arrives, not in *whether the final answer obeys these rules*.

### B.1 — A gate per `01` workflow step

| # | `01` step | Gate — what it asserts | Toy-proof (break this → red) |
|---|---|---|---|
| **G-step1 Ask** | 1. Ask | An EN question and its HE twin are both accepted and reach the agent (no language-based rejection). | Reject HE input → red. |
| **G-step2 Navigate** | 2. Navigate | The trace shows the agent read `knowledge/data_structure.md` and descended into the **correct** subtree (`school-operations/` for G-1/G-3; `carter-case/` for G-2/G-4) and **not** the wrong one. | Route the contract question into `carter-case/` → red (cross-domain). |
| **G-step3 Learn-extract** | 3. Learn-then-extract | The trace shows the matching **reference was read before extraction** (pdf/excel) and the **right file opened** with the right tool (pandas for CSV; pdftotext for PDF). | Skip the reference / open no file / open the wrong file → red. |
| **G-step4 Self-check** | 4. Iterate+self-check | For each fixture with a negative/"not available"/conflict conclusion, the trace shows the **falsification self-check ran** (a re-grep with a new keyword and/or evidence-combination before the conclusion). | Emit "not available" with no re-probe in the trace → red (see Layer D). |
| **G-step5 Compose** | 5. Compose | The answer carries a `[F:…]` citation on **every** factual claim; unavailable concepts are the "not available + why" statement (no fabricated locator); conflicts carry **both** citations; **no** cross-domain content. | Drop a citation / fabricate a penalty / leak Carter text → red. |
| **G-step6 Render** | 6. Render EN/HE | The HE answer carries the **same figures + citations + honesty** as the EN answer. | HE drops a citation, changes a number, or fabricates → red. |

### B.2 — A fixture per golden example

| # | Fixture | Assertion (figures + citations + behavior) | Toy-proof |
|---|---|---|---|
| **F-G1** | G-1 (EN) | Answer states **"38"** + **$18,924,883.79**; lists the **deterministically-pinned top-5 earliest-expiring rows** (order **`End Date ASC, Vendor ASC, id ASC`** → Edgepulse, Voomm, Realbuzz, Brainsphere, Fanoodle — see `02` G-1), each cited to a `contracts.csv` row; AND states **penalty terms not available** (no column, no documents). Contains **no** penalty figure and **no** Carter token. | "Several contracts… penalties typically include fees" → fail; a fabricated penalty or any Carter text → fail; the top-5 in any other tie-break order (rows flap) → fail. |
| **F-G2** | G-2 (EN) | Answer states **$1,285/month** + **primary residence Joni Carter** (+ joint custody) cited to **`family-court-case-file.pdf` Page 24**. | "Some child support, custody to the mother" (vague), uncited, or cited to the story PDF → fail. |
| **F-G3** | G-3 (EN) | Answer is an **honest refusal** citing the **column set** as absence-evidence, states vendors-aren't-customers + no agreement doc, fabricates **no** overdue list, AND pivots to the **$40,597.00 / 750** figure cited. | A fabricated overdue list/figure → fail; a refusal with no pivot is acceptable but the pivot is the golden bar. |
| **F-G4** | G-4 (EN) | Answer **surfaces both** "10 February 2026" cited to **`[F:carter-case/family-court-case-file.pdf#p1]`** (cover) AND "February 3, 2026" cited to **`[F:carter-case/case-story.pdf#p2]`** (the two **required**, cleanly-resolvable citations); surfaces the conflict; does **not** silently pick one. A court-file-body Feb-3 corroboration (`#p6`) is **optional** (prose), not required — the body line has no clean printed PAGE label. | Stating only one date → fail; dropping either required citation → fail. |
| **F-G1-HE … F-G4-HE** | Hebrew twins | Identical figures + citations + honesty behavior as their EN fixture. | Any number change / dropped citation / fabrication in HE → fail. |
| **F-single** | Single-contract variant | Skalith expiry **2026-07-09** + **$25,629.50** cited to its row AND **penalty not available**; no fabricated penalty, no Carter text. | Inventing a Skalith penalty or pulling Carter text → fail. |

## Layer C — Trace inspection (the agentic gate the parent had no need for)

For each fixture, assert the agent **actually did the work** — catching "right answer, wrong/no retrieval" (a lucky guess or memorized fact), which a pure answer-check can't:

| # | Trace gate | Assertion |
|---|---|---|
| **T1** | Right files opened | G-1 opens `contracts.csv`; G-2 opens `family-court-case-file.pdf`; G-3 opens `maintenance.csv` (and inspects its columns); G-4 opens **both** Carter PDFs. The trace records each `Read`/`Bash pdftotext`/pandas access. |
| **T2** | Wrong files NOT opened (the leak guard at the source) | G-1/G-3 (school-operations) **never open** `carter-case/` files; G-2/G-4 **never open** `school-operations/` files. A trace that opened the wrong domain → **red** — this is the worst-case leak caught at retrieval, not just at output. |
| **T3** | Reference-before-process | A PDF access is preceded in the trace by reading `pdf_reading.md`; a CSV access by `excel_reading.md`. (Enforces the skill's hard checklist.) |
| **T4** | Dropped sources not used | No answer is composed from any `_dropped/` file; if asked a dropped-domain question, the answer states unavailable-because-defective (names the defect), trace shows no extraction from the dropped file. |

## Layer D — The self-check ran (the skill's falsification discipline)

The eval asserts that **negative / "not available" / conflict** conclusions were **probed, not first-guessed**:
- For **G-3** (overdue refusal) and the **G-1 penalty** half: the trace shows the agent **inspected the actual columns / confirmed absence** (a pandas column read or a re-grep with a different keyword) before refusing — not a refusal asserted from the map alone.
- For **G-4** (conflict): the trace shows the date was searched in **both** documents (the conflict could only be found by checking both).
- The self-check's corrections are **merged into the single answer**, never appended as a visible "correction" after a wrong version (the parent skill's logged lesson). Assert the user-visible answer is the corrected one.

## Layer E — Robustness against non-determinism (repeated-N + LLM-judge)

Because layers B–D run over a non-deterministic agent, a **single green run is NOT acceptance**:
- **Repeated-N:** run the full eval set **N times** (default **N = 5**). Acceptance requires **all N runs** pass the deterministic gates (B) and trace gates (C). A fixture that passes 4/5 is a **red** (flaky = fail) — the engineer hardens the skill/maps until it's consistently green.
- **LLM-as-judge (the prose layer):** for the part that is genuine judgment — *is the refusal honest and specific?*, *is the conflict surfaced clearly vs. buried?*, *is the answer grounded only in the cited evidence?* — an LLM judge scores each answer against the fixture's golden rubric. The judge is **advisory-plus**: a judge failure on any run is a red that the engineer must resolve (by improving the answer, not by weakening the rubric). The hard gates (B/C) always run regardless of the judge.
- **Determinism note:** the `asOfDate` is injected (frozen to 2026-06-09) so the **38** count is stable across all N runs; a fixture asserting "38" against the wall clock would rot — assert the pinned anchor, and assert the **mechanism** (count = rows where End ∈ [asOfDate, asOfDate+90d]) for any other date.
- **Tie-break note (illustrative rows):** the contract goldens share End-Date ties (two on 2026-06-11, two on 2026-06-17), so the "earliest-expiring" top-5 is ambiguous unless ordered. The eval pins **`End Date ASC, Vendor ASC, id ASC`** (id = source CSV row index; matches v1) and asserts F-G1 against **exactly** that ordered set (Edgepulse, Voomm, Realbuzz, Brainsphere, Fanoodle). The count (38) and sum ($18,924,883.79) are order-independent; only the illustrative rows need the pin, so the agent's prompt/skill must request the same deterministic ordering when it lists "earliest-expiring" rows.

## Layer F — Generic SWE + prod-verify

- **Data presence:** an eval-setup helper asserts the `knowledge/` tree exists with the four usable files + the four `data_structure.md` maps + the `_dropped/` map; **no graceful skips** if data is missing — a missing file is a red, not a skipped test.
- **Citation resolvability (pure):** a unit-level check that every `[F:file#locator]` token in a golden answer resolves — the file exists in `knowledge/`, the page exists in the PDF, or the row natural-key exists in the CSV. A token to a nonexistent file/page/row → red. (This is the part of `validateAnswer()` that **does** port directly.)
- **Cross-domain stop-list (pure):** a contract/maintenance answer contains **zero** Carter-case tokens (child support / custody / Joni / Michel / Final Judgment / divorce / home sale); a Carter answer contains zero school-operations tokens (contract / maintenance / vendor spend). Any leak → red.
- **Map-as-guardrail check:** a test asserts the `data_structure.md` maps contain the required guardrail lines (root "no join key"; `contracts.csv` "no penalty column"; `maintenance.csv` "no payment-status field"; the Carter "filing-date conflict" + "Page 24 Final Judgment" notes). If a map loses its guardrail line, the agent loses its guidance → red.
- **End<Start preserved:** a check asserts the contract data still contains End<Start rows (e.g. Staff Scientist/Feedfish) and the agent does not silently drop them from a count claiming to be "all expiring."

### Prod-verify runbook (post-deploy, on the new Vercel project)
1. Open the deployed assistant; ask **G-1** (pinned anchor) → confirm **38**, the **$18,924,883.79** total, cited rows, the honest **"penalty terms not available"** statement, and the **trace** shows `contracts.csv` opened and the Carter PDFs NOT opened.
2. Ask **G-2** → confirm **$1,285/month** + **Joni Carter** cited to **Page 24** (court file, not story).
3. Ask **G-3** → confirm the honest refusal + the **$40,597.00** pivot; trace shows `maintenance.csv` columns inspected.
4. Ask **G-4** → confirm **both** Feb 10 and Feb 3 with both citations; trace shows **both** PDFs opened.
5. Ask each in **Hebrew** → confirm identical figures + citations + honesty.
6. Click a citation chip → confirm it resolves to the real file row/page in the source panel.

---

## Why these gates are the agentic `validateAnswer()` (the toy-proof summary)

- **Removable-handler proof** (parent discipline, ported): stub the agent to a no-op or a plausible toy and **every** B/C/F gate goes red — a vague answer (no "38"), a fabricated penalty/overdue (caught by the stop-list + fixture), a wrong/no file opened (caught by trace T1–T3), a silent conflict-resolution (F-G4), a cross-domain leak (T2 + stop-list).
- **What we keep from the deterministic world:** citation-resolvability, required-figure-presence, forbidden-token-absence, honest-refusal-fires, conflict-surfaced — all **pure**, all run every time.
- **What's genuinely new (and necessary for an agent):** trace inspection (T1–T4), the self-check audit (D), and repeated-N + LLM-judge (E) — these cover the failure modes a non-deterministic system introduces (lucky guess, first-guess refusal, flaky pass) that a single pure function over one output could not.
- **The honest limit, stated:** this is a strong **statistical** guarantee (consistent green across N real runs + pure gates + trace audit), not a *provably* deterministic one. That trade was made consciously at Phase 0 and approved by the user. The way it stays strong is **breadth of independent checks + repetition**, and the Verifier runs them independently of the Engineer.
