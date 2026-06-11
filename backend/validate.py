"""validateAnswer() — the content-fidelity gate, ported to the agentic build.

A factual answer is GROUNDED only if every inline citation token resolves to a
real source. This is the enforcement point for the project's core honesty
landmine: "a factual claim with no resolvable citation must be REJECTED, not
shipped." It is pure (no I/O beyond a filesystem existence check against the
knowledge tree) so it is unit-testable in isolation.

A token `[F:<file>#<loc>]` resolves iff:
  1. it appears in the answer prose, AND
  2. a matching evidence item (same file + loc) was returned, AND
  3. the cited file actually exists under knowledge/, AND
  4. for `#p<N>` the page is within the PDF's page count; for `#row-<N>` the row
     is within the CSV's row count. (Bounds-checked so a hallucinated page/row is
     caught even if the file exists.)

`validate()` returns (ok, reasons). It NEVER raises on a bad answer — it reports.
"""
from __future__ import annotations

import re
from pathlib import Path

from backend.models import EvidenceItem

TOKEN_RE = re.compile(r"\[F:([^\]#]+)#([^\]]+)\]")
PAGE_RE = re.compile(r"^p(\d+)$")
# CSV row natural-key locator: `row=<Vendor>|<EndDate>` (Contract ID is mislabeled, so rows are
# keyed by Vendor + End Date). Also tolerate a plain `row-<N>` ordinal form.
ROWKEY_RE = re.compile(r"^row=(.+)$")
ROWORD_RE = re.compile(r"^row-(\d+)$")
# Printed page header inside the PDF text, e.g. "📑 PAGE 24 – FINAL JUDGMENT".
PRINTED_PAGE_RE = re.compile(r"PAGE\s+(\d+)", re.IGNORECASE)


def extract_tokens(answer: str) -> list[tuple[str, str]]:
    """Return [(file, loc), ...] for every [F:file#loc] in the prose.

    A single token sometimes BUNDLES several locators the agent combined into one cite, e.g.
    `[F:customers.xlsx#row-2, #row-3, #row-4]`. Split those into separate (file, loc) pairs so each
    is validated independently — a bundled cite is still fully grounded, and a fabricated row inside
    it still fails. Split ONLY when every comma-part is a simple ordinal/page locator (`row-N`/`pN`),
    so a natural-key loc that legitimately contains a comma (`row=Acme, Inc|2026-06-11`) is untouched.
    """
    out: list[tuple[str, str]] = []
    for m in TOKEN_RE.finditer(answer):
        file, raw = m.group(1), m.group(2)
        if "," in raw:
            parts = [p for p in (s.strip().lstrip("#").strip() for s in raw.split(",")) if p]
            if parts and all(ROWORD_RE.match(p) or PAGE_RE.match(p) for p in parts):
                out.extend((file, p) for p in parts)
                continue
        out.append((file, raw))
    return out


def _pdf_printed_page_labels(path: Path) -> set[int] | None:
    """The set of printed PAGE-N labels in the document text (what a reader cites against).

    The PDFs print "📑 PAGE N – TITLE" headers; pdftotext packs them into fewer physical pages, so
    a citation `#p24` is bound-checked against these PRINTED labels, not the physical page count.
    Falls back to the physical page count when no printed labels are present.
    """
    try:
        import pdfplumber

        labels: set[int] = set()
        physical = 0
        with pdfplumber.open(path) as pdf:
            physical = len(pdf.pages)
            for page in pdf.pages:
                text = page.extract_text() or ""
                for m in PRINTED_PAGE_RE.finditer(text):
                    labels.add(int(m.group(1)))
        if labels:
            return labels
        return set(range(1, physical + 1))
    except Exception:
        return None


def _csv_rowkeys(path: Path) -> tuple[set[str], int] | None:
    """Return (natural-key set, data-row count).

    The natural key is `<Vendor>|<EndDate>` built from the `Vendor` + `End Date` columns when both
    exist (contracts.csv); otherwise an empty key set with just the row count (ordinal fallback).

    An uploaded .xlsx has no CSV text form, so its data-row count is read via pandas (ordinal-only —
    uploaded customer data has no Vendor|End Date natural key). Needs openpyxl at runtime.
    """
    if path.suffix.lower() in (".xlsx", ".xls"):
        try:
            import pandas as pd

            df = pd.read_excel(path, sheet_name=0, dtype=str)
            return set(), int(len(df))
        except Exception:
            return None
    try:
        import csv as _csv

        with path.open(encoding="utf-8", errors="replace", newline="") as fh:
            reader = _csv.reader(fh)
            header = next(reader, [])
            keys: set[str] = set()
            n = 0
            vi = header.index("Vendor") if "Vendor" in header else None
            ei = header.index("End Date") if "End Date" in header else None
            for row in reader:
                n += 1
                if vi is not None and ei is not None and len(row) > max(vi, ei):
                    keys.add(f"{row[vi].strip()}|{_norm_date(row[ei].strip())}")
            return keys, n
    except Exception:
        return None


def _norm_date(s: str) -> str:
    """Normalize a date string to YYYY-MM-DD so M/D/YYYY tokens match the CSV's stored form."""
    s = s.strip()
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%-m/%-d/%Y"):
        try:
            from datetime import datetime

            return datetime.strptime(s, fmt).date().isoformat()
        except Exception:
            continue
    return s


def _norm_rowkey(raw: str) -> str:
    """Normalize a `row=Vendor|EndDate` payload's date half so M/D/YYYY matches the CSV form."""
    parts = raw.split("|", 1)
    if len(parts) == 2:
        return f"{parts[0].strip()}|{_norm_date(parts[1])}"
    return raw.strip()


def _resolve_under_roots(file: str, roots: list[Path]) -> tuple[Path | None, str | None]:
    """Resolve a cited `file` under the FIRST allowed root that contains it.

    Returns (resolved_path, None) on success, or (None, reason) when the file
    either escapes every root (a `..`/absolute path that climbs out) or does not
    exist under any. The roots are tried in order; for the live-upload feature the
    caller passes [session_uploads_root, knowledge_root] so an uploaded-file
    citation (e.g. `customers.csv`) resolves against the session dir while a
    `knowledge/...` citation still resolves against the committed tree.
    """
    escaped_all = True
    for root in roots:
        root_r = root.resolve()
        full = (root_r / file).resolve()
        if not str(full).startswith(str(root_r)):
            continue  # escapes THIS root — try the next
        escaped_all = False
        if full.exists():
            return full, None
    if escaped_all:
        return None, f"cited file escapes the allowed roots: {file}"
    return None, f"cited file does not exist: {file}"


def validate(
    answer: str,
    evidence: list[EvidenceItem],
    kb_root: Path | list[Path],
) -> tuple[bool, list[str]]:
    """Validate every [F:file#loc] token against one or more allowed source roots.

    `kb_root` is a single Path (the committed knowledge/ tree — the original,
    unchanged behavior) OR a list of roots (the live-upload path: the per-session
    uploads root FIRST, then knowledge/). A token resolves if the cited file exists
    under one of the roots and the page/row is in bounds there.
    """
    roots = kb_root if isinstance(kb_root, list) else [kb_root]
    reasons: list[str] = []
    tokens = extract_tokens(answer)

    # An answer that makes no claims (pure honest refusal with no citations) is
    # allowed ONLY when it carries no citation tokens. If it cites, every cite
    # must resolve.
    evidence_index = {(e.file, e.loc) for e in evidence}

    for file, loc in tokens:
        # 2. token must be backed by a returned evidence item
        if (file, loc) not in evidence_index:
            reasons.append(f"cited [F:{file}#{loc}] has no matching evidence item")
            continue

        # 3. file must exist under one of the allowed roots
        full, reason = _resolve_under_roots(file, roots)
        if full is None:
            reasons.append(reason or f"cited file does not exist: {file}")
            continue

        # 4. bounds-check the locator
        page_m = PAGE_RE.match(loc)
        rowkey_m = ROWKEY_RE.match(loc)
        roword_m = ROWORD_RE.match(loc)
        if page_m:
            n = int(page_m.group(1))
            labels = _pdf_printed_page_labels(full)
            if labels is not None and n not in labels:
                reasons.append(
                    f"cited page {n} not a printed PAGE label in {file}"
                )
        elif rowkey_m:
            key = _norm_rowkey(rowkey_m.group(1))
            info = _csv_rowkeys(full)
            if info is not None:
                keys, _ = info
                # only enforce when the file actually has a (Vendor,End Date) key space
                if keys and key not in keys:
                    reasons.append(
                        f"cited row key {rowkey_m.group(1)!r} not found in {file}"
                    )
        elif roword_m:
            n = int(roword_m.group(1))
            info = _csv_rowkeys(full)
            if info is not None and not (1 <= n <= info[1]):
                reasons.append(
                    f"cited row {n} out of range for {file} (1..{info[1]})"
                )
        # a non-page, non-row loc (e.g. a named section) is accepted as long as
        # the file exists and an evidence item backs it.

    return (len(reasons) == 0, reasons)
