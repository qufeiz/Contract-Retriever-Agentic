"""Unit tests for validateAnswer() — the content-fidelity gate (Layer F citation-resolvability).

Pure, deterministic, runs every time. Mirrors the part of the parent's validateAnswer() that ports
directly: every [F:file#loc] token must resolve to a real file + real page/row.
"""
from pathlib import Path

from backend.models import EvidenceItem
from backend.validate import validate, extract_tokens

KB = Path(__file__).resolve().parents[2] / "knowledge"


def test_extract_tokens():
    a = "38 contracts [F:school-operations/contracts.csv#row=Voomm|2026-06-11] expire."
    assert extract_tokens(a) == [("school-operations/contracts.csv", "row=Voomm|2026-06-11")]


def test_real_pdf_printed_page_resolves():
    ans = "Child support is $1,285/month [F:carter-case/family-court-case-file.pdf#p24]."
    ev = [EvidenceItem(file="carter-case/family-court-case-file.pdf", loc="p24", snippet="$1,285")]
    ok, reasons = validate(ans, ev, KB)
    assert ok, reasons


def test_real_contract_rowkey_resolves():
    ans = "Voomm expires [F:school-operations/contracts.csv#row=Voomm|2026-06-11]."
    ev = [EvidenceItem(file="school-operations/contracts.csv", loc="row=Voomm|2026-06-11")]
    ok, reasons = validate(ans, ev, KB)
    assert ok, reasons


def test_fabricated_page_rejected():
    ans = "Per the judgment [F:carter-case/family-court-case-file.pdf#p999]."
    ev = [EvidenceItem(file="carter-case/family-court-case-file.pdf", loc="p999")]
    ok, reasons = validate(ans, ev, KB)
    assert not ok and any("p999".replace("p", "") in r or "999" in r for r in reasons)


def test_fabricated_rowkey_rejected():
    ans = "[F:school-operations/contracts.csv#row=NoSuchVendor|2099-01-01]"
    ev = [EvidenceItem(file="school-operations/contracts.csv", loc="row=NoSuchVendor|2099-01-01")]
    ok, reasons = validate(ans, ev, KB)
    assert not ok and any("not found" in r for r in reasons)


def test_token_without_evidence_rejected():
    ans = "Penalty is $5000 [F:school-operations/contracts.csv#row=Voomm|2026-06-11]."
    ok, reasons = validate(ans, [], KB)  # no evidence item backs the token
    assert not ok and any("no matching evidence" in r for r in reasons)


def test_nonexistent_file_rejected():
    ans = "[F:school-operations/penalties.csv#row-1]"
    ev = [EvidenceItem(file="school-operations/penalties.csv", loc="row-1")]
    ok, reasons = validate(ans, ev, KB)
    assert not ok and any("does not exist" in r for r in reasons)


def test_honest_refusal_with_no_tokens_passes():
    ans = "Penalty terms are not available — contracts.csv has no penalty column."
    ok, reasons = validate(ans, [], KB)
    assert ok, reasons  # an answer that makes no cited claims is valid
