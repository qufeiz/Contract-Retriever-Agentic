# Live File Upload

Lets a client **upload their own CSV / PDF / xlsx live** in the demo UI and ask a **cross-source** question over it — e.g. *"Which customers have overdue payments, and what does their contract say about service suspension?"* The same agent that answers the committed corpus now answers over the uploaded files: **per-session, isolated, read-only**, navigating an auto-generated `data_structure.md` map, computing with pandas/pdftotext, and **citing every claim to the exact uploaded row/page** (`[F:customers.csv#row-3]`, `[F:service-agreement.pdf#p3]`) — with the honesty contract and the read-only hardening fully intact (no fabricated join; honest "not available" when a file lacks the field).

This **extends** the [agentic-knowledge-assistant](../agentic-knowledge-assistant/README.md) (the same agent loop + `_pre_tool_use` boundary + async-job transport); the committed-corpus path is unchanged.

## Docs
- **PM-authored (the design + golden bar):** [01-design.md](01-design.md) · [02-examples.md](02-examples.md) · [fixtures/](fixtures/) (the discriminating CSV + suspension-clause PDF)
- **Engineer-authored (build):** [04-implementation.md](04-implementation.md) · [user-guide.md](user-guide.md)

## Screenshot / gate ledger

One row per capability → its golden screenshot (captured by the Engineer from the live app at the pinned anchor `2026-06-09`) → the eval gate that proves it. The screenshots + the runnable eval harness (`backend/eval/upload_run.py`) are **Engineer deliverables**; the rows below are the bar the PM set in `02`.

| Capability | Screenshot | Gate (proves it works) |
|---|---|---|
| Upload `customers.csv` + `service-agreement.pdf`, ask the cross-source question → 3 customers / 4 invoices / **$18,965.50**, each cited to the CSV rows (2,3,4,7), **§4.3** cited to `service-agreement.pdf#p3`, Contoso (51d) the only suspension-eligible | `images/u1-upload-cross-source-answer.png` | eval `U-1` (exact rows + figures + `#p3` + validate + both files opened) |
| A citation chip resolves to the real uploaded CSV row / contract page | `images/u1-citation-resolves.png` | eval `U-1` (validate against the session uploads root) |
| Honest absence on uploaded data: only the CSV uploaded (no contract) → lists overdue customers, **refuses the penalty rate** ("not available", cites the column set), fabricates nothing | `images/u2-honest-absence.png` | eval `U-2-absent` |
| Per-session isolation + injection-inert (hardening survives uploads) | — (proven by tests, not a screenshot) | `backend/tests/test_hardening.py` (two-session deny, injection-inside-a-file inert, escapes) |
| Cost-lean **retrieval-skill toggle** (full ⇄ lean) renders, defaults to full, and flips | `images/skill-toggle.png` | journey `skill-toggle.spec.ts` (render + `aria-checked` flip) + unit `test_skill_select.py` |
| The **lean** variant selected in the toggle (slimmer kb-retriever-lean prompt) — UI→wire | `images/skill-toggle-lean.png` | journey `skill-toggle.spec.ts` (`skill:"lean"` sent on the ask). NOTE: proves the SWITCH; the lean skill's answer quality is the cap-blocked live eval. |

**Golden facts pinned at `asOfDate=2026-06-09`** (independently re-derived in `02`): overdue invoices **4** (rows 2,3,4,7), overdue customers **3**, total overdue **$18,965.50**; the only **>30-day** (suspension-eligible) invoice is **Contoso INV-1055 (51 days)**; the suspension clause is **§4.3 on printed PAGE 3**. The trap rows (paid-but-past-due, due-today, future-due) must **not** be cited as overdue.

> **Model:** the upload path runs on **`claude-sonnet-4-6`** (`UPLOAD_MODEL`). Per `01`'s model note we tested **Haiku first**; Haiku got the substance right but **mis-cited the uploaded CSV rows off by one** (counting the header), so the upload path escalated to Sonnet, which produces the exact golden. The committed-corpus path stays on the default `AGENT_MODEL`.
