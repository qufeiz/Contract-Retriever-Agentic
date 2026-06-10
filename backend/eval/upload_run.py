"""The live-upload eval harness (the U-1/U-2 acceptance gate) — the committed regression gate for
the live-upload feature, mirroring backend/eval/run.py for the committed-corpus goldens.

It uploads the real fixtures (docs/features/live-upload/fixtures/) into a per-session store, runs
the REAL agent scoped to that session, and asserts the U-1/U-2 golden bar from 02-examples:
  - U-1: 3 overdue customers / 4 invoices / $18,965.50, each cited to the uploaded CSV rows; the
    §4.3 suspension clause cited to service-agreement.pdf#p3; composed cross-source (separate
    citations, no fabricated join); Contoso (51d) flagged as the only >30-day, suspension-eligible.
    The trace must show the agent opening BOTH uploaded files; validate() must pass against the
    session uploads root; the paid/future/due-today trap rows must NOT be listed as overdue.
  - U-2: honest absence still fires — when the asked field isn't in the uploaded files, refuse and
    cite the column set, fabricating nothing.

Like run.py: a fixture passes only if ALL N runs pass (flaky == fail). Exit 0 iff all green.

Usage:
    python -m backend.eval.upload_run            # N=3, all upload fixtures
    EVAL_N=1 python -m backend.eval.upload_run   # one run (cheap smoke)
    UPLOAD_MODEL=claude-sonnet-4-6 python -m backend.eval.upload_run   # escalate the upload path
"""
from __future__ import annotations

import asyncio
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from backend.agent import answer_question
from backend.eval.judge import judge
from backend.models import AskResponse
from backend.uploads import (
    create_session,
    finalize_session_map,
    prune_session_now,
    store_upload,
)
from backend.validate import extract_tokens

N = int(os.environ.get("EVAL_N", "3"))
# Per-run model for the UPLOAD path: defaults to the configured MODEL (Haiku); set
# UPLOAD_MODEL=claude-sonnet-4-6 to escalate if Haiku proves unreliable on uploaded data.
UPLOAD_MODEL = os.environ.get("UPLOAD_MODEL") or None
FIXTURES = Path(__file__).resolve().parents[2] / "docs" / "features" / "live-upload" / "fixtures"


@dataclass
class UploadFixture:
    """One upload-eval case: which fixtures to upload + the U-x acceptance bar."""

    id: str
    question: str
    upload: list[str]  # fixture filenames to upload into the session
    required_facts: list[str] = field(default_factory=list)  # substrings that MUST appear
    required_citations: list[tuple[str, str]] = field(default_factory=list)  # (file_substr, loc_re)
    must_open: list[str] = field(default_factory=list)  # filenames the trace MUST show opened
    forbidden: list[str] = field(default_factory=list)  # substrings that must be ABSENT
    behavior: list[str] = field(default_factory=list)  # "cross_source" | "honest_refusal"
    # The golden rubric for the LLM judge (Layer E) — the prose-level judgment a deterministic gate
    # can't make: whether the OVERDUE SET is exactly right and no trap row is COUNTED as overdue (a
    # paid/future/due-today row may be NAMED to explain its exclusion — that is honest, not a fail).
    judge_rubric: str = ""


UPLOAD_FIXTURES: list[UploadFixture] = [
    UploadFixture(
        id="U-1",
        question=(
            "Which customers have overdue payments, and what does their contract say about "
            "service suspension?"
        ),
        upload=["customers.csv", "service-agreement.pdf"],
        # 3 customers / 4 invoices / $18,965.50; the >30-day suspension-eligible one is Contoso (51d).
        required_facts=["18,965.50", "Contoso", "51"],
        # The overdue invoices are DATA rows 2,3,4,7 (header excluded). Requiring these EXACT row
        # locators catches the off-by-one (counting the header) that points citations at wrong rows.
        # The §4.3 suspension clause is on printed PAGE 3.
        required_citations=[
            ("customers.csv", r"^row-2$"),
            ("customers.csv", r"^row-3$"),
            ("customers.csv", r"^row-4$"),
            ("customers.csv", r"^row-7$"),
            ("service-agreement.pdf", r"^p3$"),
        ],
        must_open=["customers.csv", "service-agreement.pdf"],
        # No fabricated contract term.
        forbidden=["suspended immediately"],
        behavior=["cross_source"],
        judge_rubric=(
            "The answer must present EXACTLY these four invoices as overdue (unpaid AND past their "
            "due date as of 2026-06-09): Northwind Traders INV-1071, Contoso Ltd INV-1055, Contoso "
            "Ltd INV-1088, Adatum Corp INV-1077 — 3 distinct customers, 4 invoices, total "
            "$18,965.50. It MUST NOT count any other row as overdue: NOT the paid invoices "
            "(Northwind INV-1042, Fabrikam INV-1063, Tailspin INV-1081), NOT Fabrikam INV-1090 "
            "which is due exactly on 2026-06-09 (due-today is NOT yet overdue), and NOT the "
            "future-due Wingtip INV-1099 / Litware INV-1102. It MAY name those rows to explain why "
            "they are excluded (that is honest) — but counting any of them as overdue is a FAIL. It "
            "must identify Contoso INV-1055 (51 days) as the only invoice over the contract's "
            ">30-day §4.3 suspension threshold, and must NOT fabricate a join between the two files."
        ),
    ),
    UploadFixture(
        id="U-2-absent",
        question=(
            "Which customers have overdue payments, and what's the penalty interest rate if they "
            "don't pay?"
        ),
        # Only the CSV (no rate column); the contract is ABSENT → must refuse the rate honestly.
        upload=["customers.csv"],
        required_facts=["not available"],
        required_citations=[("customers.csv", r"row-\d+")],
        must_open=["customers.csv"],
        forbidden=["1.5%", "1.5 percent", "service-agreement.pdf"],  # no fabricated/foreign rate
        behavior=["honest_refusal"],
        judge_rubric=(
            "Only customers.csv was uploaded (no contract). The answer must list overdue customers "
            "from the CSV, then HONESTLY REFUSE the penalty-interest-rate question — stating no "
            "rate/penalty column exists in customers.csv and no agreement document was uploaded, "
            "citing the CSV's column set as the evidence of absence. It must FABRICATE NO rate (no "
            "'1.5%', no invented figure) and must not pull a rate from any other source."
        ),
    ),
]


def _opened(resp: AskResponse) -> str:
    return " ".join(t.detail for t in resp.trace if t.kind in ("open", "map", "grep"))


def _score_upload(fx: UploadFixture, resp: AskResponse) -> list[str]:
    """Deterministic U-x gates over one response (empty list = pass)."""
    fails: list[str] = []
    low = resp.answer.lower()

    for fact in fx.required_facts:
        if fact.lower() not in low:
            fails.append(f"[{fx.id}] missing required fact: {fact!r}")

    tokens = extract_tokens(resp.answer)
    for file_sub, loc_re in fx.required_citations:
        if not any(file_sub in f and re.search(loc_re, loc) for f, loc in tokens):
            fails.append(
                f"[{fx.id}] no citation file~{file_sub!r} loc~/{loc_re}/ "
                f"(saw {[f'[F:{f}#{l}]' for f, l in tokens][:8]})"
            )

    # NOTE: whether a TRAP row (paid / due-today / future-due) is wrongly COUNTED as overdue is a
    # PROSE judgment — a correct answer may CITE a trap row to make an honest meta-point (e.g. row-1
    # to say "the CSV has only paid/unpaid status, no overdue label" or "no join key exists"). A
    # blunt "trap row cited → fail" gate punishes that honest use. So the trap-row discrimination is
    # the LLM judge's job (Layer E, fx.judge_rubric), not a deterministic token check here. The
    # deterministic gates below assert the unambiguous POSITIVE requirements (the golden rows ARE
    # cited, the figures/clause are right, validate passes, the right files were opened).

    if not resp.validation.ok:
        fails.append(f"[{fx.id}] validate() rejected: {'; '.join(resp.validation.reasons)}")

    # The agent reads an uploaded PDF via its PRE-EXTRACTED .txt (the design pre-extracts at upload),
    # so match a required file by its STEM — `service-agreement.pdf` is satisfied by opening
    # `service-agreement.txt` or the .pdf itself.
    blob = _opened(resp)
    for f in fx.must_open:
        stem = f.rsplit(".", 1)[0]
        if stem not in blob:
            fails.append(f"[{fx.id}] required uploaded file not opened in trace: {f}")

    for bad in fx.forbidden:
        if bad.lower() in low:
            fails.append(f"[{fx.id}] forbidden content present: {bad!r}")

    # No fabricated cross-corpus answer: an uploads answer must not be BUILT FROM the committed
    # knowledge/ data. The real failure is (a) CITING a committed-corpus file in the answer, or
    # (b) actually READING (`open`) a committed DATA file. A harmless transient PROBE (`grep`/`glob`/
    # `test`) over knowledge/ that finds nothing and isn't cited is NOT a leak — the agent sometimes
    # checks whether a contract exists before refusing, which is fine and read-only. So we check the
    # CITATIONS + the `open` steps only, not every grep.
    cited_knowledge = any(
        ("carter-case" in f) or ("school-operations" in f) or ("knowledge/" in f)
        for f, _ in tokens
    )
    opened_knowledge_data = any(
        t.kind == "open" and any(d in t.detail.lower() for d in ("carter-case", "school-operations"))
        for t in resp.trace
    )
    if cited_knowledge or opened_knowledge_data:
        fails.append(f"[{fx.id}] built the uploads answer from the committed knowledge/ corpus (leak)")

    return fails


async def _run_once(fx: UploadFixture) -> tuple[bool, list[str]]:
    """Upload the fixtures into a fresh session, run the agent scoped to it, score the gates."""
    session = create_session()
    try:
        for name in fx.upload:
            store_upload(session, name, (FIXTURES / name).read_bytes())
        finalize_session_map(session)
        try:
            resp = await answer_question(
                fx.question, session_id=session.session_id, model=UPLOAD_MODEL
            )
        except Exception as e:
            return False, [f"[{fx.id}] agent raised: {e}"]
        fails = _score_upload(fx, resp)
        # Layer E — the LLM judge does the prose-level judgment (trap rows not counted as overdue;
        # honest refusal not fabricated). A judge FAIL is a red the engineer fixes by improving the
        # answer/prompt, never by weakening the rubric.
        if fx.judge_rubric:
            judged_ok, reason = await judge(fx, resp)
            if not judged_ok:
                fails.append(f"[{fx.id}] LLM-judge FAIL: {reason}")
        return (len(fails) == 0), fails
    finally:
        prune_session_now(session.session_id)


async def main(selected: list[str]) -> int:
    fixtures = [f for f in UPLOAD_FIXTURES if not selected or f.id in selected]
    if not fixtures:
        print(f"no upload fixtures match {selected}", file=sys.stderr)
        return 2
    print(f"=== Live-upload eval — {len(fixtures)} fixtures × N={N} runs ===\n")
    overall_ok = True
    for fx in fixtures:
        results, all_fails = [], []
        for i in range(N):
            ok, fails = await _run_once(fx)
            results.append(ok)
            if not ok:
                all_fails.extend(f"  run {i + 1}: {x}" for x in fails)
        passed = sum(results)
        fx_ok = passed == N
        overall_ok = overall_ok and fx_ok
        print(f"{'✓' if fx_ok else '✗'} {fx.id}: {passed}/{N} runs passed" + ("" if fx_ok else "  (RED)"))
        for line in all_fails:
            print(line)
        print()
    print("=== RESULT:", "ALL GREEN" if overall_ok else "RED — see failures above", "===")
    return 0 if overall_ok else 1


if __name__ == "__main__":
    selected = [a for a in sys.argv[1:] if not a.startswith("-")]
    raise SystemExit(asyncio.run(main(selected)))
