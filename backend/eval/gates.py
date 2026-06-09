"""The deterministic gates (Layers B/C/D/F of 03) — pure checks over one agent response.

These survive the agent's non-determinism because they assert the FINAL answer + evidence + trace
obey the rules, regardless of phrasing/order. Each gate returns a list of failure strings (empty =
pass). `score_fixture` aggregates them for one run.
"""
from __future__ import annotations

import re

from backend.eval.fixtures import (
    Fixture,
    CARTER_TOKENS,
    SCHOOL_TOKENS,
    DROPPED_TOKENS,
    DROPPED_FILES,
)
from backend.models import AskResponse
from backend.validate import extract_tokens


def _answer_lower(resp: AskResponse) -> str:
    return resp.answer.lower()


def gate_required_facts(fx: Fixture, resp: AskResponse) -> list[str]:
    """Layer B.2 — required figures/findings present (exact + any-of alternates)."""
    fails = []
    low = _answer_lower(resp)
    for fact in fx.required_facts:
        if fact.lower() not in low:
            fails.append(f"[{fx.id}] missing required fact: {fact!r}")
    for alternates in fx.required_facts_any:
        if not any(alt.lower() in low for alt in alternates):
            fails.append(f"[{fx.id}] missing required fact (any of): {alternates}")
    return fails


def gate_required_citations(fx: Fixture, resp: AskResponse) -> list[str]:
    """Layer B.2 / F — at least one cited token matches each (file, loc-regex) requirement."""
    fails = []
    tokens = extract_tokens(resp.answer)
    for file_sub, loc_re in fx.required_citations:
        ok = any(file_sub in f and re.search(loc_re, loc) for f, loc in tokens)
        if not ok:
            fails.append(
                f"[{fx.id}] no citation matching file~{file_sub!r} loc~/{loc_re}/ "
                f"(saw: {[f'[F:{f}#{l}]' for f, l in tokens][:8]})"
            )
    return fails


def gate_validation(fx: Fixture, resp: AskResponse) -> list[str]:
    """Layer F — validateAnswer() must pass (every token resolves to a real file+page/row)."""
    if not resp.validation.ok:
        return [f"[{fx.id}] validateAnswer rejected: {'; '.join(resp.validation.reasons)}"]
    return []


def gate_forbidden(fx: Fixture, resp: AskResponse) -> list[str]:
    """Layer B / F — fabrications + cross-domain leaks must be absent."""
    fails = []
    low = _answer_lower(resp)
    for bad in fx.forbidden:
        if bad.lower() in low:
            fails.append(f"[{fx.id}] forbidden content present: {bad!r}")
    return fails


def gate_cross_domain(fx: Fixture, resp: AskResponse) -> list[str]:
    """Layer F — the stop-list: a school answer has zero Carter tokens, and vice versa."""
    low = _answer_lower(resp)
    fails = []
    # Decide the fixture's domain from which files it must open.
    school = any("school-operations" in f for f in fx.must_open)
    carter = any("carter-case" in f for f in fx.must_open)
    if school and not carter:
        for t in CARTER_TOKENS:
            if t in low:
                fails.append(f"[{fx.id}] cross-domain LEAK — Carter token in a school answer: {t!r}")
    if carter and not school:
        for t in SCHOOL_TOKENS:
            if t in low:
                fails.append(f"[{fx.id}] cross-domain LEAK — school token in a Carter answer: {t!r}")
    # A dropped-source token (payroll/enrollment) should appear in NO answer.
    for t in DROPPED_TOKENS:
        if t in low:
            fails.append(f"[{fx.id}] DROPPED-source token leaked into answer: {t!r}")
    return fails


def _opened_paths(resp: AskResponse) -> str:
    """All file paths mentioned in open/map/grep trace steps, joined for substring search."""
    return " ".join(t.detail for t in resp.trace if t.kind in ("open", "map", "grep"))


def gate_trace_opened(fx: Fixture, resp: AskResponse) -> list[str]:
    """Layer C / T1 — the right files were opened."""
    fails = []
    blob = _opened_paths(resp)
    for f in fx.must_open:
        # match by basename so absolute vs relative paths both resolve
        base = f.split("/")[-1]
        if base not in blob:
            fails.append(f"[{fx.id}] T1: required file not opened in trace: {f}")
    return fails


def gate_trace_not_opened(fx: Fixture, resp: AskResponse) -> list[str]:
    """Layer C / T2 + T4 — wrong-domain files NOT opened, and NO dropped source ever opened."""
    fails = []
    blob = _opened_paths(resp)
    for f in fx.must_not_open:
        base = f.split("/")[-1]
        if base in blob:
            fails.append(f"[{fx.id}] T2: forbidden file OPENED in trace (leak at source): {f}")
    # T4: a dropped/quarantined source must never be opened by ANY answer.
    for f in DROPPED_FILES:
        base = f.split("/")[-1]
        if base in blob:
            fails.append(f"[{fx.id}] T4: DROPPED source opened in trace (must not be used): {f}")
    return fails


def gate_self_check(fx: Fixture, resp: AskResponse) -> list[str]:
    """Layer D — negative/conflict conclusions were probed, not first-guessed.

    For honest_refusal: the trace shows the agent actually inspected the data (a pandas column read
    / grep) before refusing — not a refusal asserted from the map alone.
    For conflict: the date was searched in BOTH documents (only way to find the conflict).
    """
    fails = []
    blob = _opened_paths(resp).lower()
    if "honest_refusal" in fx.behavior:
        inspected = any(
            k in blob for k in ("pandas", "read_csv", "columns", "grep", "pdftotext")
        )
        if not inspected:
            fails.append(f"[{fx.id}] D: honest-refusal not probed — no data inspection in trace")
    if "conflict" in fx.behavior:
        # both Carter PDFs must appear in the trace
        if "family-court-case-file" not in blob or "case-story" not in blob:
            fails.append(f"[{fx.id}] D: conflict not probed across both documents")
    return fails


def gate_pivot(fx: Fixture, resp: AskResponse) -> list[str]:
    """Layer B — a pivot answer cites the pivot figure to the data file (not the map)."""
    if "pivot" not in fx.behavior:
        return []
    tokens = extract_tokens(resp.answer)
    cited_csv = any("maintenance.csv" in f for f, _ in tokens)
    if not cited_csv:
        return [f"[{fx.id}] pivot figure not cited to maintenance.csv"]
    return []


ALL_GATES = [
    gate_required_facts,
    gate_required_citations,
    gate_validation,
    gate_forbidden,
    gate_cross_domain,
    gate_trace_opened,
    gate_trace_not_opened,
    gate_self_check,
    gate_pivot,
]


def score_fixture(fx: Fixture, resp: AskResponse) -> list[str]:
    """Run every deterministic gate; return the aggregated failure list (empty = pass)."""
    fails: list[str] = []
    for gate in ALL_GATES:
        fails.extend(gate(fx, resp))
    return fails
