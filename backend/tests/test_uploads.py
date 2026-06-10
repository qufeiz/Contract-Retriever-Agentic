"""Unit tests for the per-session upload store (backend/uploads.py).

Pure-ish (filesystem only, no agent run): they lock the upload-time guards — filename
sanitization, accepted types, size caps, PDF pre-extract + corrupt rejection, CSV/xlsx
column inspection, the auto-generated session map, and session creation/isolation/TTL —
as a permanent regression gate so a future edit can't silently widen the boundary.
"""
import io

import pytest

from backend import uploads
from backend.uploads import (
    UploadError,
    create_session,
    finalize_session_map,
    prune_session_now,
    session_root,
    store_upload,
)

FIXTURES = uploads.PROJECT_ROOT / "docs" / "features" / "live-upload" / "fixtures"
CSV_BYTES = (FIXTURES / "customers.csv").read_bytes()
PDF_BYTES = (FIXTURES / "service-agreement.pdf").read_bytes()


@pytest.fixture
def session():
    s = create_session()
    yield s
    prune_session_now(s.session_id)


def test_session_id_is_unguessable_and_unique():
    a = create_session()
    b = create_session()
    try:
        assert a.session_id != b.session_id
        assert len(a.session_id) >= 24  # token_urlsafe(24) → ~32 chars
        assert a.dir.exists() and b.dir.exists()
    finally:
        prune_session_now(a.session_id)
        prune_session_now(b.session_id)


def test_store_csv_inspects_columns_and_rows(session):
    uf = store_upload(session, "customers.csv", CSV_BYTES)
    assert uf.kind == "csv"
    assert uf.rows == 10
    assert uf.columns == [
        "customer", "invoice_id", "amount_due", "invoice_date", "due_date", "status",
    ]
    assert (session.dir / "customers.csv").exists()


def test_store_pdf_pre_extracts_text_and_counts_pages(session):
    uf = store_upload(session, "service-agreement.pdf", PDF_BYTES)
    assert uf.kind == "pdf"
    assert uf.pages == 4  # printed PAGE 1..4 labels
    # the pre-extracted .txt sits alongside, inside the session dir (so it's in read scope)
    txt = session.dir / "service-agreement.txt"
    assert txt.exists() and txt.stat().st_size > 0
    body = txt.read_text()
    # the §4.3 suspension clause text is present in the pre-extracted file (the golden citation)
    assert "SERVICE SUSPENSION" in body
    assert "thirty (30) days" in body


def test_filename_sanitized_no_traversal(session):
    # A client filename with a path component keeps ONLY the basename — never escapes the dir.
    uf = store_upload(session, "../../etc/customers.csv", CSV_BYTES)
    assert uf.name == "customers.csv"
    assert (session.dir / "customers.csv").exists()
    assert not (session.dir.parent / "etc").exists()


def test_reject_unsupported_type(session):
    with pytest.raises(UploadError):
        store_upload(session, "evil.exe", b"MZ binary")
    with pytest.raises(UploadError):
        store_upload(session, "notes.txt", b"hello")  # .txt is not an accepted UPLOAD type


def test_reject_empty_and_oversize(session, monkeypatch):
    with pytest.raises(UploadError):
        store_upload(session, "empty.csv", b"")
    # shrink the per-file cap to force the oversize path deterministically
    monkeypatch.setattr(uploads, "UPLOAD_MAX_FILE_BYTES", 10)
    with pytest.raises(UploadError):
        store_upload(session, "big.csv", CSV_BYTES)


def test_reject_corrupt_pdf(session):
    # Bytes with a .pdf name that pdftotext can't extract → rejected AT upload, not mid-answer.
    with pytest.raises(UploadError):
        store_upload(session, "broken.pdf", b"%PDF-1.4 not really a pdf body")
    # nothing half-stored
    assert not (session.dir / "broken.pdf").exists()
    assert not (session.dir / "broken.txt").exists()


def test_duplicate_name_rejected(session):
    store_upload(session, "customers.csv", CSV_BYTES)
    with pytest.raises(UploadError):
        store_upload(session, "customers.csv", CSV_BYTES)


def test_session_map_lists_files_with_columns_and_pages(session):
    store_upload(session, "customers.csv", CSV_BYTES)
    store_upload(session, "service-agreement.pdf", PDF_BYTES)
    finalize_session_map(session)
    text = (session.dir / "data_structure.md").read_text()
    # the map names both files, the CSV's columns, and the row/page locator grammar
    assert "customers.csv" in text and "service-agreement.pdf" in text
    assert "due_date" in text and "status" in text  # detected CSV columns
    assert "#row-" in text and "#p<N>" in text  # the citation locators the agent must use
    assert "never fabricate" in text.lower()  # the honesty boundary is carried into the map


def test_session_root_resolves_and_isolates():
    a = create_session()
    b = create_session()
    try:
        ra = session_root(a.session_id)
        rb = session_root(b.session_id)
        assert ra is not None and rb is not None and ra != rb
        # an unknown / expired id grants no scope
        assert session_root("nope-not-a-real-session") is None
        assert session_root(None) is None
    finally:
        prune_session_now(a.session_id)
        prune_session_now(b.session_id)


def test_prune_removes_dir_and_registry():
    s = create_session()
    sid = s.session_id
    assert s.dir.exists()
    prune_session_now(sid)
    assert not s.dir.exists()
    assert session_root(sid) is None
