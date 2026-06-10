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


# ── Live-upload: citations resolve against a per-session uploads root ───────────
import shutil
import tempfile
from pathlib import Path as _Path

FIXTURES = _Path(__file__).resolve().parents[2] / "docs" / "features" / "live-upload" / "fixtures"


def _session_root_with_fixtures(tmp: _Path) -> _Path:
    """A fake session uploads root holding the two fixtures, like the runtime store."""
    shutil.copy(FIXTURES / "customers.csv", tmp / "customers.csv")
    shutil.copy(FIXTURES / "service-agreement.pdf", tmp / "service-agreement.pdf")
    return tmp


def test_uploaded_csv_ordinal_row_resolves():
    tmp = _Path(tempfile.mkdtemp())
    try:
        root = _session_root_with_fixtures(tmp)
        ans = "Contoso is overdue [F:customers.csv#row-3]."
        ev = [EvidenceItem(file="customers.csv", loc="row-3", snippet="Contoso")]
        ok, reasons = validate(ans, ev, [root, KB])  # session root FIRST, then knowledge/
        assert ok, reasons
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_uploaded_csv_out_of_range_row_rejected():
    tmp = _Path(tempfile.mkdtemp())
    try:
        root = _session_root_with_fixtures(tmp)
        ans = "[F:customers.csv#row-99]"  # 10-row file
        ev = [EvidenceItem(file="customers.csv", loc="row-99")]
        ok, reasons = validate(ans, ev, [root, KB])
        assert not ok and any("out of range" in r for r in reasons)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_uploaded_pdf_printed_page_resolves_and_invented_page_rejected():
    tmp = _Path(tempfile.mkdtemp())
    try:
        root = _session_root_with_fixtures(tmp)
        good = "Suspension clause [F:service-agreement.pdf#p3]."
        ev = [EvidenceItem(file="service-agreement.pdf", loc="p3", snippet="4.3")]
        ok, reasons = validate(good, ev, [root, KB])
        assert ok, reasons
        bad = "[F:service-agreement.pdf#p9]"  # no printed PAGE 9
        evb = [EvidenceItem(file="service-agreement.pdf", loc="p9")]
        okb, rb = validate(bad, evb, [root, KB])
        assert not okb and any("not a printed PAGE label" in r for r in rb)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_mixed_roots_knowledge_and_upload_both_resolve():
    """A composed cross-source answer cites BOTH an uploaded file and (hypothetically) a knowledge
    file — each must resolve against its own root."""
    tmp = _Path(tempfile.mkdtemp())
    try:
        root = _session_root_with_fixtures(tmp)
        ans = (
            "Overdue [F:customers.csv#row-3]; the case judgment "
            "[F:carter-case/family-court-case-file.pdf#p24]."
        )
        ev = [
            EvidenceItem(file="customers.csv", loc="row-3"),
            EvidenceItem(file="carter-case/family-court-case-file.pdf", loc="p24"),
        ]
        ok, reasons = validate(ans, ev, [root, KB])
        assert ok, reasons
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
