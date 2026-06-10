"""Per-session upload store for the live-upload feature.

The committed `knowledge/` tree is the fixed demo corpus. This module adds a SECOND,
ephemeral source root: a client uploads their own CSV/PDF/xlsx live, and the agent
answers over THOSE files for the duration of a session — isolated per session, read-only,
and pruned on a TTL. It is the same "maps ARE the index" model as `knowledge/`: every
session dir gets an auto-generated `data_structure.md` so the agent navigates uploads the
same way it navigates the committed tree.

Layout (under PROJECT_ROOT, gitignored):

    uploads/<session_id>/                  # session_id is an unguessable token
        data_structure.md                 # auto-generated map (one row per uploaded file)
        <sanitized-original-name>          # the uploaded artifact (CSV / PDF / xlsx)
        <pdf-stem>.txt                     # pre-extracted PDF text (pdftotext), kept alongside

Security stance (the files are attacker-controlled — see 01-design §Security):
  - The `session_id` is an unguessable `secrets.token_urlsafe` so one client can't reach
    another's dir by guessing.
  - Filenames are SANITIZED to a basename with a safe charset — no path-traversal via the
    stored name (`../`, absolute paths, NUL all stripped/rejected).
  - Type + size are enforced AT UPLOAD, before any agent run is spent: only CSV/PDF/xlsx,
    each under a per-file cap and a per-session total cap.
  - A corrupt/encrypted PDF is rejected at upload (pdftotext can't extract it), not mid-answer.
The READ-ONLY agent boundary that keeps a session bound to its own dir lives in
`backend/agent.py` (`_pre_tool_use`); this module only WRITES the store. Nothing here is
ever executed — uploaded files are data the agent reads, never instructions it follows.
"""
from __future__ import annotations

import re
import secrets
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

from backend.config import (
    PROJECT_ROOT,
    UPLOAD_MAX_FILE_BYTES,
    UPLOAD_MAX_SESSION_BYTES,
    UPLOAD_MAX_FILES,
    UPLOAD_TTL_SEC,
)

# The store root. Lives under the project root so the agent (cwd=PROJECT_ROOT) can reach a
# session dir via `add_dirs`, but it is OUTSIDE `knowledge/` so the committed corpus stays
# untouched. Gitignored — uploaded client data is never committed.
UPLOADS_ROOT = PROJECT_ROOT / "uploads"

# Accepted upload types, keyed by lowercased extension. CSV + PDF + xlsx per the approved
# design (the kb-retriever skill already has a pandas/excel path). Anything else is rejected
# at upload with a clear error, before an agent run is spent.
_ALLOWED_EXTS = {".csv", ".pdf", ".xlsx"}

# A sanitized stored filename: keep the basename's word chars, dot, dash; collapse the rest.
# This is defense-in-depth ON TOP OF taking only the basename — a stored name can never carry
# a path separator or a traversal sequence.
_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


class UploadError(ValueError):
    """A bad upload (wrong type, too big, unreadable, corrupt PDF). Carries an HTTP-friendly
    message; the endpoint maps it to a 4xx so the client sees WHY, before any agent run."""


@dataclass
class UploadedFile:
    """One stored file in a session (returned to the client + used to build the map)."""

    name: str  # the sanitized stored basename (what citations reference: customers.csv)
    kind: str  # "csv" | "pdf" | "xlsx"
    size: int  # bytes on disk
    columns: list[str] = field(default_factory=list)  # detected columns (CSV/xlsx) — [] for PDF
    pages: int | None = None  # printed/physical page count (PDF) — None for CSV/xlsx
    rows: int | None = None  # data-row count (CSV/xlsx) — None for PDF


@dataclass
class Session:
    """A per-client upload session: an unguessable id, its dir, the stored files, a creation
    stamp for TTL pruning."""

    session_id: str
    files: list[UploadedFile] = field(default_factory=list)
    created: float = field(default_factory=time.monotonic)

    @property
    def dir(self) -> Path:
        return UPLOADS_ROOT / self.session_id


# In-process session registry (single-instance Fly app — same assumption as the job store and
# the rate limiter). A machine restart drops sessions; the demo re-uploads. A durable
# multi-tenant store is explicitly out of scope (01-design §Deferrals).
_SESSIONS: dict[str, Session] = {}


def _sanitize_filename(raw: str) -> str:
    """Reduce an arbitrary client filename to a safe stored basename.

    Takes ONLY the basename (drops any directory part a client tried to smuggle in), then keeps
    a safe charset. Rejects a name that sanitizes to empty or has no usable stem.
    """
    base = Path(raw).name  # strips any path component — "../../etc/passwd" -> "passwd"
    base = base.replace("\x00", "")
    safe = _SAFE_NAME_RE.sub("_", base).strip("._")
    if not safe or safe in (".", ".."):
        raise UploadError(f"unusable filename: {raw!r}")
    return safe


def _kind_for(name: str) -> str:
    """Map a sanitized name's extension to its kind, or reject an unsupported type."""
    ext = Path(name).suffix.lower()
    if ext not in _ALLOWED_EXTS:
        raise UploadError(
            f"unsupported file type {ext or '(none)'!r} for {name!r}; "
            f"accepted: {', '.join(sorted(_ALLOWED_EXTS))}"
        )
    return {".csv": "csv", ".pdf": "pdf", ".xlsx": "xlsx"}[ext]


def _inspect_csv(path: Path) -> tuple[list[str], int]:
    """(columns, data-row-count) for a CSV, read defensively. A CSV that pandas can't parse at
    all is rejected (it's the client's bad file, surfaced at upload, not mid-answer)."""
    try:
        import pandas as pd

        # Read as strings: we only need the shape + column names here, not typed values, and
        # this never crashes on a mixed/odd column the way dtype inference can.
        df = pd.read_csv(path, dtype=str, keep_default_na=False)
        return [str(c) for c in df.columns.tolist()], int(len(df))
    except Exception as e:  # malformed CSV — reject at upload with the real reason
        raise UploadError(f"could not read CSV {path.name!r}: {e}") from e


def _inspect_xlsx(path: Path) -> tuple[list[str], int]:
    """(columns, data-row-count) for the FIRST sheet of an .xlsx. Same shape as a CSV so the
    agent treats it identically (the skill's excel path). Reject an unreadable workbook."""
    try:
        import pandas as pd

        df = pd.read_excel(path, sheet_name=0, dtype=str)
        return [str(c) for c in df.columns.tolist()], int(len(df))
    except Exception as e:
        raise UploadError(f"could not read xlsx {path.name!r}: {e}") from e


def _pre_extract_pdf(path: Path) -> int:
    """Pre-extract a PDF's text with pdftotext (already in the container) so the first ask
    doesn't pay extraction in-loop, and a corrupt/encrypted PDF is rejected HERE, not mid-answer.

    Writes `<stem>.txt` ALONGSIDE the pdf (inside the session dir, so it stays in read scope).
    Returns the printed/physical page count for the map. Raises UploadError if the PDF can't be
    extracted (encrypted, corrupt, not really a PDF).
    """
    txt_path = path.with_suffix(".txt")
    try:
        # pdftotext writes the .txt itself (no shell redirection); -q stays quiet on warnings.
        subprocess.run(
            ["pdftotext", "-q", str(path), str(txt_path)],
            check=True,
            capture_output=True,
            timeout=30,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
        raise UploadError(
            f"could not extract text from PDF {path.name!r} "
            f"(it may be encrypted, corrupt, or image-only): {e}"
        ) from e
    if not txt_path.exists() or txt_path.stat().st_size == 0:
        # pdftotext "succeeded" but produced nothing — an image-only/encrypted scan. Reject so a
        # client doesn't upload an un-citable PDF and then get an empty answer.
        raise UploadError(
            f"PDF {path.name!r} produced no extractable text "
            f"(image-only or encrypted PDFs are not supported)."
        )
    # Page count for the map: prefer the printed "PAGE N" labels (what citations resolve
    # against), else the physical page count. Best-effort — a missing count never fails upload.
    try:
        import pdfplumber

        labels: set[int] = set()
        physical = 0
        with pdfplumber.open(path) as pdf:
            physical = len(pdf.pages)
            for page in pdf.pages:
                for m in re.finditer(r"PAGE\s+(\d+)", page.extract_text() or "", re.IGNORECASE):
                    labels.add(int(m.group(1)))
        return max(labels) if labels else physical
    except Exception:
        return 0


def _write_session_map(session: Session) -> None:
    """(Re)generate `data_structure.md` for the session dir — the agent's index into the uploads.

    Mirrors the committed maps' shape (a per-file table + an honesty note) so the agent navigates
    uploaded files exactly as it navigates `knowledge/`: it sees the column set (to answer or
    refuse honestly) and the page count, and it is told these files are the CLIENT's uploaded data,
    separate from the committed corpus and from each other (no fabricated join).
    """
    lines: list[str] = [
        "# Uploaded files (this session)",
        "",
        "These are the files the user uploaded for THIS session. Answer the user's question from",
        "THESE files (and, only if relevant, the committed `knowledge/` tree) — citing every claim",
        "to a file + page/row. Cite an uploaded file by its name, e.g.",
        "`[F:customers.csv#row-3]` for a CSV/xlsx row (1-based ordinal) or",
        "`[F:service-agreement.pdf#p3]` for a printed PDF page. If the uploaded files lack the asked",
        "concept, say so and cite the column set as evidence of absence — never fabricate.",
        "",
        "## Files",
        "| File | Type | Detail (read before you answer) |",
        "|---|---|---|",
    ]
    for f in session.files:
        if f.kind in ("csv", "xlsx"):
            cols = ", ".join(f.columns) if f.columns else "(no header row detected)"
            detail = (
                f"{f.rows} data rows. Columns: `{cols}`. "
                f"Cite a row as `#row-<N>`: a 1-based ordinal that EXCLUDES the header — the first "
                f"DATA row is `#row-1` (in pandas, `df.iloc[i]` is `#row-<i+1>`). Confirm the Nth "
                f"data row is the one you mean before citing (an off-by-one cites the wrong row). "
                f"Inspect the columns before answering — do not assume a field the question implies."
            )
        else:  # pdf
            pages = f"{f.pages} pages" if f.pages else "page count unknown"
            detail = (
                f"{pages}. Pre-extracted to `{Path(f.name).stem}.txt` (read that, or pdftotext the "
                f"PDF). Cite a fact to its printed `#p<N>` page label — never an invented page."
            )
        lines.append(f"| `{f.name}` | {f.kind} | {detail} |")
    lines += [
        "",
        "## Honesty boundary",
        "- These uploaded files and the committed `knowledge/` corpus share NO join key, and the",
        "  uploaded files do not share a join key with each other unless a column literally matches.",
        "  Compose any cross-source answer SEPARATELY — cite each fact to its own file; never merge",
        "  on an invented key.",
        "- If a question asks for a field none of these files contain, state that it is not available",
        "  and cite the column set / the document's absence. Never invent a value, rate, clause, or date.",
        "",
    ]
    (session.dir / "data_structure.md").write_text("\n".join(lines), encoding="utf-8")


def prune_sessions() -> None:
    """Drop sessions past their TTL (dir + registry entry) so neither the disk nor the dict grows
    unbounded, and one client's data isn't retained indefinitely (01-design §Lifecycle)."""
    now = time.monotonic()
    stale = [sid for sid, s in _SESSIONS.items() if now - s.created > UPLOAD_TTL_SEC]
    for sid in stale:
        s = _SESSIONS.pop(sid, None)
        if s is not None:
            shutil.rmtree(s.dir, ignore_errors=True)


def prune_session_now(session_id: str) -> None:
    """Drop one session immediately (dir + registry). Used to discard a half-built session when an
    upload in a batch fails, so a client never half-uploads."""
    s = _SESSIONS.pop(session_id, None)
    if s is not None:
        shutil.rmtree(s.dir, ignore_errors=True)


def create_session() -> Session:
    """Mint a new session with an unguessable id and an empty, freshly-created dir."""
    prune_sessions()
    session_id = secrets.token_urlsafe(24)  # ~32 chars, unguessable
    session = Session(session_id=session_id)
    session.dir.mkdir(parents=True, exist_ok=True)
    _SESSIONS[session_id] = session
    return session


def get_session(session_id: str) -> Session | None:
    """Look up a live (un-pruned) session, or None. Prunes stale sessions first so a TTL-expired
    id is treated as unknown (its dir is gone too)."""
    prune_sessions()
    return _SESSIONS.get(session_id)


def session_root(session_id: str | None) -> Path | None:
    """The on-disk read root for a session's uploads, or None if there is no live session.

    This is the SECOND allowed read root (besides `knowledge/`) that the agent's `_pre_tool_use`
    hook is widened to accept. Returns the resolved dir only for a known, live session — an
    unknown/expired id yields None (no extra read scope is granted).
    """
    if not session_id:
        return None
    s = get_session(session_id)
    if s is None:
        return None
    return s.dir.resolve()


def store_upload(session: Session, raw_filename: str, data: bytes) -> UploadedFile:
    """Validate + store one uploaded file into the session dir, returning its descriptor.

    Enforces (at upload, before any agent run): a safe filename, an accepted type, the per-file
    size cap, and the per-session total cap. Pre-extracts a PDF (rejecting a corrupt/encrypted one)
    and inspects a CSV/xlsx's columns. Does NOT (re)write the session map — the caller writes it
    once after a batch (see `finalize_session_map`).
    """
    name = _sanitize_filename(raw_filename)
    kind = _kind_for(name)

    if len(data) == 0:
        raise UploadError(f"{name!r} is empty.")
    if len(data) > UPLOAD_MAX_FILE_BYTES:
        raise UploadError(
            f"{name!r} is too large ({len(data)} bytes; max {UPLOAD_MAX_FILE_BYTES})."
        )
    existing = sum(f.size for f in session.files)
    if existing + len(data) > UPLOAD_MAX_SESSION_BYTES:
        raise UploadError(
            f"session upload total would exceed the cap ({UPLOAD_MAX_SESSION_BYTES} bytes)."
        )
    if len(session.files) >= UPLOAD_MAX_FILES:
        raise UploadError(f"too many files in this session (max {UPLOAD_MAX_FILES}).")
    if any(f.name == name for f in session.files):
        raise UploadError(f"a file named {name!r} was already uploaded in this session.")

    dest = session.dir / name
    dest.write_bytes(data)

    columns: list[str] = []
    pages: int | None = None
    rows: int | None = None
    try:
        if kind == "csv":
            columns, rows = _inspect_csv(dest)
        elif kind == "xlsx":
            columns, rows = _inspect_xlsx(dest)
        else:  # pdf
            pages = _pre_extract_pdf(dest)
    except UploadError:
        # A bad file: remove the partial artifact so it can't be read, and re-raise so the client
        # learns WHY at upload time (never a half-stored file lingering in the session).
        dest.unlink(missing_ok=True)
        dest.with_suffix(".txt").unlink(missing_ok=True)
        raise

    uf = UploadedFile(name=name, kind=kind, size=len(data), columns=columns, pages=pages, rows=rows)
    session.files.append(uf)
    return uf


def finalize_session_map(session: Session) -> None:
    """Write the session's `data_structure.md` reflecting all stored files. Call once after a
    batch of `store_upload`s so the agent has a current map of the session's uploads."""
    _write_session_map(session)
