"""Regression tests for the agent's final-output parser.

Real agent output is messy. The PRIMARY format is the two-block ANSWER/EVIDENCE form (prose +
prose-free JSON array) which sidesteps the stray-quote break; the parser also keeps a legacy
single-JSON-object fallback. Each case below is a failure observed in a real run.
"""
from backend.agent import _extract_output


# ── Primary: the two-block ANSWER/EVIDENCE format ──────────────────────────────
def test_block_format_basic():
    raw = (
        "===ANSWER===\n"
        "38 contracts expire [F:school-operations/contracts.csv#row=Voomm|6/11/2026].\n"
        "===EVIDENCE===\n"
        '[{"file": "school-operations/contracts.csv", "loc": "row=Voomm|6/11/2026", "snippet": "Voomm"}]'
    )
    d = _extract_output(raw)
    assert "38 contracts" in d["answer"]
    assert len(d["evidence"]) == 1
    assert d["evidence"][0]["file"] == "school-operations/contracts.csv"


def test_block_answer_may_contain_double_quotes():
    # the exact G-4 break: a quoted date inside the prose answer — fine in block format
    raw = (
        "===ANSWER===\n"
        'The cover sheet records "Filed: 10 February 2026." [F:carter-case/family-court-case-file.pdf#p1]\n'
        "===EVIDENCE===\n"
        '[{"file": "carter-case/family-court-case-file.pdf", "loc": "p1", "snippet": "Filed: 10 February 2026"}]'
    )
    d = _extract_output(raw)
    assert '"Filed: 10 February 2026."' in d["answer"]
    assert d["evidence"][0]["loc"] == "p1"


def test_block_answer_multiline_preserved():
    raw = "===ANSWER===\nline one\nline two\nline three\n===EVIDENCE===\n[]"
    d = _extract_output(raw)
    assert d["answer"].count("\n") == 2


def test_block_prose_before_markers_ignored():
    raw = "I now run my self-check.\n\n===ANSWER===\nDone [F:a#p1]\n===EVIDENCE===\n[]"
    d = _extract_output(raw)
    assert d["answer"] == "Done [F:a#p1]"


# ── Legacy fallback: a single JSON object ──────────────────────────────────────
def test_legacy_plain_object():
    d = _extract_output('{"answer": "hi", "evidence": []}')
    assert d["answer"] == "hi"


def test_legacy_prose_before_object():
    raw = 'Composing the final JSON now.\n\n{"answer": "x", "evidence": []}'
    d = _extract_output(raw)
    assert d["answer"] == "x"


def test_legacy_literal_newlines_inside_string():
    raw = '{"answer": "line one\nline two", "evidence": []}'
    d = _extract_output(raw)
    assert d["answer"].count("\n") == 1


# ── Last-resort: free prose with no blocks and no JSON (a hard refusal) ─────────
def test_free_prose_refusal_does_not_crash():
    # A hijacked request the agent refuses comes back as free prose — no
    # ANSWER/EVIDENCE blocks, no JSON. It must NOT raise; the prose is returned
    # as an un-grounded answer (validate() then scores it: a pure refusal with
    # no citations passes, an uncited claim fails).
    text = "I can't run that command — this assistant only reads the knowledge base."
    out = _extract_output(text)
    assert out["answer"] == text
    assert out["evidence"] == []
