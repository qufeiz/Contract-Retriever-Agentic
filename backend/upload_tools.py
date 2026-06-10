"""Scoped data-reader tools for the UPLOAD path — the constrained toolset (Option 1).

The deployed Claude Agent SDK does NOT reliably honor a `PreToolUse` deny (local↔live divergence),
so we cannot rely on a hook to sandbox raw `Read`/`Bash`/`Glob`/`Grep`. Instead the upload-path
agent is given NO raw filesystem tools at all — only these in-process MCP tools, each of which:

  - accepts a FILENAME (or a `kb/<relative>` path for the committed corpus), never a raw absolute
    path the caller controls;
  - resolves it against ONLY the allowed roots (the per-request run dir + `knowledge/`) and REFUSES
    anything that escapes (absolute paths, `..`, another session's dir) — airtight by construction,
    no hook to bypass;
  - is read-only (returns data; never writes/executes/networks).

So a cross-session read is impossible: there is no tool that takes `/home/app/.../<victim>` and reads
it. The allowed roots are bound per-request via the `_TOOL_ROOTS` contextvar (set in agent.py for the
duration of one run), exactly like the hook's scope — but here it's the ONLY way to touch the FS.

The four tools cover what the kb-retriever flow needs: list the available files, read a CSV (as
records, so the model can filter/aggregate — e.g. the U-1 $18,965.50 overdue total), read a PDF's
text by printed page, and grep within the allowed files.
"""
from __future__ import annotations

import io
import re
from contextvars import ContextVar
from pathlib import Path
from typing import Any, Optional

from claude_agent_sdk import create_sdk_mcp_server, tool

# The allowed read roots for the CURRENT run: [run_dir (uploads), knowledge_root]. Set per-request
# in agent.py. Empty/unset → no FS access (the tools refuse everything), which is correct for a run
# with no session (the committed-corpus path keeps the raw kb-retriever tools instead).
_TOOL_ROOTS: ContextVar[list[Path]] = ContextVar("upload_tool_roots", default=[])

# Logical prefixes the agent uses to address a root without ever naming an absolute path:
#   <filename>            → the per-request UPLOADS run dir (root[0])
#   kb/<relative path>    → the committed knowledge/ tree    (root[1])
_KB_PREFIX = "kb/"


def set_tool_roots(uploads_root: Optional[Path], kb_root: Path):
    """Bind the allowed roots for this run. Returns the contextvar token (reset in a finally)."""
    roots: list[Path] = []
    if uploads_root is not None:
        roots.append(uploads_root.resolve())
    roots.append(kb_root.resolve())
    return _TOOL_ROOTS.set(roots)


def reset_tool_roots(token) -> None:
    _TOOL_ROOTS.reset(token)


class _ScopeError(Exception):
    """A requested path escaped the allowed roots — refused."""


def _resolve(name: str) -> Path:
    """Resolve an agent-supplied logical name to a real path UNDER an allowed root, or refuse.

    `name` is either a bare filename/relative path within the uploads run dir, or `kb/<rel>` for the
    committed tree. We REJECT anything with an absolute path, a `..` segment, or a leading slash —
    the agent never gets to name a raw FS path. The resolved path must stay inside the chosen root.
    """
    roots = _TOOL_ROOTS.get()
    if not roots:
        raise _ScopeError("no files are available in this context.")
    raw = (name or "").strip().strip("'\"")
    if not raw:
        raise _ScopeError("a filename is required.")
    # No absolute paths, no traversal, no NUL — the agent addresses files by name only.
    if raw.startswith("/") or raw.startswith("~") or ".." in raw.split("/") or "\x00" in raw:
        raise _ScopeError(
            f"'{raw}' is not an allowed filename — address files by name only "
            f"(or 'kb/<path>' for the knowledge base); absolute/parent paths are refused."
        )
    if raw.startswith(_KB_PREFIX):
        # kb/<rel> → the knowledge root (the LAST root)
        root = roots[-1]
        rel = raw[len(_KB_PREFIX):]
    else:
        # a bare name → the uploads run dir (the FIRST root) if a session is present, else knowledge
        root = roots[0]
        rel = raw
    full = (root / rel).resolve()
    if not (str(full) == str(root) or str(full).startswith(str(root) + "/")):
        raise _ScopeError(f"'{raw}' resolves outside the allowed files — refused.")
    if not full.exists():
        raise _ScopeError(f"'{raw}' does not exist among the available files.")
    return full


def _err(msg: str) -> dict:
    return {"content": [{"type": "text", "text": f"REFUSED: {msg}"}], "is_error": True}


def _ok(text: str) -> dict:
    return {"content": [{"type": "text", "text": text}]}


# ---------------------------------------------------------------------------
# The tools. Each is read-only and path-scoped via _resolve().
# ---------------------------------------------------------------------------

@tool(
    "list_files",
    "List the files available to answer this question (the user's uploaded files for this session, "
    "and the committed knowledge base under the 'kb/' prefix). Returns each file's name, type, and "
    "for a CSV its columns + row count.",
    {},
)
async def list_files(args: dict[str, Any]) -> dict[str, Any]:
    roots = _TOOL_ROOTS.get()
    if not roots:
        return _err("no files are available in this context.")
    lines: list[str] = []
    # uploads run dir = roots[0] when a session is present (i.e. >1 root)
    if len(roots) > 1:
        up = roots[0]
        lines.append("UPLOADED files (address by bare name):")
        for p in sorted(up.iterdir()):
            if p.is_file():
                lines.append(f"  - {p.name}")
    kb = roots[-1]
    lines.append("KNOWLEDGE BASE (address with the 'kb/' prefix, e.g. kb/data_structure.md):")
    for p in sorted(kb.glob("**/*")):
        if p.is_file() and p.suffix.lower() in (".md", ".csv", ".pdf", ".txt"):
            lines.append(f"  - kb/{p.relative_to(kb)}")
    return _ok("\n".join(lines))


@tool(
    "read_text",
    "Read a small text/markdown file (e.g. a data_structure.md map, or a CSV previewed as text) "
    "from the available files. Address an uploaded file by its bare name, or the knowledge base "
    "with 'kb/<path>'. Returns the file's text (truncated if very large).",
    {"name": str},
)
async def read_text(args: dict[str, Any]) -> dict[str, Any]:
    try:
        full = _resolve(str(args.get("name", "")))
    except _ScopeError as e:
        return _err(str(e))
    try:
        text = full.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return _err(f"could not read '{args.get('name')}': {e}")
    return _ok(text[:20000] + ("\n…(truncated)…" if len(text) > 20000 else ""))


@tool(
    "read_csv",
    "Read a CSV (or xlsx) from the available files and return its rows as records so you can filter "
    "and aggregate (e.g. compute overdue invoices and a total). Address an uploaded file by its bare "
    "name, or the knowledge base with 'kb/<path>'. Returns the header + every data row, numbered "
    "1-based (row 1 = the first DATA row, header excluded — that ordinal is the #row-<N> citation).",
    {"name": str},
)
async def read_csv(args: dict[str, Any]) -> dict[str, Any]:
    try:
        full = _resolve(str(args.get("name", "")))
    except _ScopeError as e:
        return _err(str(e))
    try:
        import pandas as pd

        if full.suffix.lower() == ".xlsx":
            df = pd.read_excel(full, sheet_name=0, dtype=str)
        else:
            df = pd.read_csv(full, dtype=str, keep_default_na=False)
    except Exception as e:
        return _err(f"could not read CSV '{args.get('name')}': {e}")
    cols = list(df.columns)
    out = io.StringIO()
    out.write(f"columns: {cols}\nrow_count: {len(df)}\n")
    out.write("rows (1-based ordinal = #row-<N>, header excluded):\n")
    for i, rec in enumerate(df.to_dict(orient="records"), start=1):
        out.write(f"  #row-{i}: {rec}\n")
        if i >= 2000:  # safety cap for a huge upload
            out.write(f"  …(only first 2000 of {len(df)} rows shown)…\n")
            break
    return _ok(out.getvalue())


@tool(
    "read_pdf_pages",
    "Extract a PDF's text by printed page from the available files. Address an uploaded PDF by its "
    "bare name, or the knowledge base with 'kb/<path>'. Returns each printed 'PAGE N' block so you "
    "can cite a fact to '#p<N>'. (Reads the pre-extracted .txt if present.)",
    {"name": str},
)
async def read_pdf_pages(args: dict[str, Any]) -> dict[str, Any]:
    name = str(args.get("name", ""))
    # Prefer the pre-extracted .txt sitting next to the PDF (created at upload).
    try:
        full = _resolve(name)
    except _ScopeError as e:
        return _err(str(e))
    txt_path = full.with_suffix(".txt")
    text: Optional[str] = None
    if txt_path.exists():
        text = txt_path.read_text(encoding="utf-8", errors="replace")
    else:
        try:
            import subprocess

            r = subprocess.run(
                ["pdftotext", "-q", str(full), "-"], capture_output=True, timeout=30, check=True
            )
            text = r.stdout.decode("utf-8", errors="replace")
        except Exception as e:
            return _err(f"could not extract PDF '{name}': {e}")
    return _ok(text[:40000] + ("\n…(truncated)…" if len(text) > 40000 else ""))


@tool(
    "grep_files",
    "Search for a regex/keyword across the available files (uploaded + knowledge base) and return "
    "matching lines with their file + line number. Use this to locate a clause/term before reading "
    "the surrounding block. Read-only; scoped to the available files only.",
    {"pattern": str},
)
async def grep_files(args: dict[str, Any]) -> dict[str, Any]:
    pattern = str(args.get("pattern", "")).strip()
    if not pattern:
        return _err("a search pattern is required.")
    try:
        rx = re.compile(pattern, re.IGNORECASE)
    except re.error as e:
        return _err(f"invalid pattern: {e}")
    roots = _TOOL_ROOTS.get()
    if not roots:
        return _err("no files are available in this context.")
    hits: list[str] = []
    searched: list[tuple[Path, str]] = []
    for ri, root in enumerate(roots):
        label = "" if (ri == 0 and len(roots) > 1) else _KB_PREFIX
        for p in sorted(root.glob("**/*")):
            if p.is_file() and p.suffix.lower() in (".md", ".csv", ".txt"):
                rel = p.name if not label else f"kb/{p.relative_to(root)}"
                searched.append((p, rel))
    for p, rel in searched:
        try:
            for ln, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                if rx.search(line):
                    hits.append(f"{rel}:{ln}: {line.strip()[:200]}")
                    if len(hits) >= 200:
                        break
        except Exception:
            continue
        if len(hits) >= 200:
            break
    return _ok("\n".join(hits) if hits else "(no matches)")


# The in-process MCP server bundling the scoped readers. Tool names the agent calls are
# `mcp__data__<tool>` (the SDK namespaces them by server name "data").
def build_upload_tools_server():
    return create_sdk_mcp_server(
        name="data",
        version="1.0.0",
        tools=[list_files, read_text, read_csv, read_pdf_pages, grep_files],
    )


# The fully-qualified tool names to put on `allowed_tools` for the upload path (and NOTHING else —
# no Read/Bash/Glob/Grep/Write/Edit, so there is no raw FS access at all).
UPLOAD_ALLOWED_TOOLS = [
    "mcp__data__list_files",
    "mcp__data__read_text",
    "mcp__data__read_csv",
    "mcp__data__read_pdf_pages",
    "mcp__data__grep_files",
]
