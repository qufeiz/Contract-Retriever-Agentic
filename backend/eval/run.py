"""The repeatable eval harness (Layer E driver) — the committed regression gate.

Runs the REAL agent over the REAL knowledge/ tree for every fixture, N times (default N=5). A
fixture passes acceptance only if ALL N runs pass the deterministic gates (B/C/D/F) AND the
LLM-judge (E). A fixture that passes 4/5 is a RED — flaky == fail; the engineer hardens the
skill/maps until it's consistently green.

Usage:
    python -m backend.eval.run            # N=5, all fixtures
    EVAL_N=3 python -m backend.eval.run   # override N
    python -m backend.eval.run F-G1 F-G3  # a subset

Exit code 0 iff every fixture passes all N runs (gates + judge). Non-zero otherwise.
"""
from __future__ import annotations

import asyncio
import os
import sys

from backend.agent import answer_question
from backend.eval.fixtures import FIXTURES, Fixture
from backend.eval.gates import score_fixture
from backend.eval.judge import judge

N = int(os.environ.get("EVAL_N", "5"))


async def run_fixture_once(fx: Fixture) -> tuple[bool, list[str]]:
    """One real agent run → (passed, failures)."""
    try:
        resp = await answer_question(fx.question)
    except Exception as e:
        return False, [f"[{fx.id}] agent raised: {e}"]
    fails = score_fixture(fx, resp)
    judged_ok, reason = await judge(fx, resp)
    if not judged_ok:
        fails.append(f"[{fx.id}] LLM-judge FAIL: {reason}")
    return (len(fails) == 0), fails


async def main(selected: list[str]) -> int:
    fixtures = [f for f in FIXTURES if not selected or f.id in selected]
    if not fixtures:
        print(f"no fixtures match {selected}", file=sys.stderr)
        return 2

    print(f"=== Agentic eval harness — {len(fixtures)} fixtures × N={N} runs ===\n")
    overall_ok = True
    for fx in fixtures:
        run_results = []
        all_fails: list[str] = []
        for i in range(N):
            ok, fails = await run_fixture_once(fx)
            run_results.append(ok)
            if not ok:
                all_fails.extend(f"  run {i + 1}: {x}" for x in fails)
        passed_n = sum(run_results)
        fixture_ok = passed_n == N  # flaky == fail
        overall_ok = overall_ok and fixture_ok
        mark = "✓" if fixture_ok else "✗"
        print(f"{mark} {fx.id}: {passed_n}/{N} runs passed" + ("" if fixture_ok else "  (RED — flaky/failing)"))
        for line in all_fails:
            print(line)
        print()

    print("=== RESULT:", "ALL GREEN" if overall_ok else "RED — see failures above", "===")
    return 0 if overall_ok else 1


if __name__ == "__main__":
    selected = [a for a in sys.argv[1:] if not a.startswith("-")]
    raise SystemExit(asyncio.run(main(selected)))
