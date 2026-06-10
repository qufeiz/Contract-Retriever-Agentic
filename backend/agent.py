"""The agentic Q&A loop.

Unlike kb-retriever's two-phase table builder (propose-schema → fill-table), this is a single
conversational turn: a free-form business question in, the Aletheia output contract out
(`{answer, evidence, trace, validation}`). The agent runs the trimmed kb-retriever skill over the
real `knowledge/` tree — navigating `data_structure.md` maps, reading the processing reference,
extracting with pandas / pdftotext, self-checking, and citing every claim with a `[F:<file>#<loc>]`
token. We capture the SDK's tool-use stream into a structured `trace` so "did it open the right
file" is inspectable (Layer C of `03`).
"""
from __future__ import annotations

import json
import re
from typing import Awaitable, Callable, Optional

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    HookMatcher,
    ResultMessage,
    TextBlock,
    ThinkingBlock,
    ToolUseBlock,
    UserMessage,
    query,
)

from backend.config import MAX_QUESTION_CHARS, MAX_TURNS, MODEL, PROJECT_ROOT, KB_PATH
from backend.models import AskResponse, EvidenceItem, TraceStep, Validation
from backend.validate import validate

# The agent ends its turn with the two-block ANSWER/EVIDENCE form (see _extract_output). The skill
# governs HOW it retrieves; this prompt governs the OUTPUT SHAPE so the UI can consume it.
SYSTEM_PROMPT = f"""You are Aletheia, a grounded business-knowledge assistant. Answer the user's \
question using ONLY the local knowledge base at `knowledge/`, via the kb-retriever skill: navigate \
the data_structure.md maps, read the matching processing reference IN FULL before processing a \
PDF/CSV, extract progressively (pandas for CSV, pdftotext for PDF), run the falsification self-check, \
and cite every factual claim.

HARD RULES (the honesty contract):
- Cite every factual claim inline with a token `[F:<file>#<locator>]` where <file> is the path \
relative to `knowledge/` and <locator> is `p<N>` for a PDF printed PAGE-N label, or \
`row=<Vendor>|<EndDate>` for a contracts.csv row (keyed by Vendor + End Date because Contract ID is \
mislabeled), or a short section name.
- COMPUTE figures from the actual data file and cite THAT file — never quote a number from a \
data_structure.md map as if it were the source. The maps are guidance/index only; a quantitative \
claim (a count, a sum, a row value, a page fact) must be cited to the CSV/PDF you actually read and \
computed from (e.g. the $40,597 maintenance total must be cited to `maintenance.csv`, not to the \
map note). Cite a map ONLY for an absence statement (e.g. "no penalty column exists").
- If the data has no source for the asked concept, say "not available" and cite the absence (the \
file's column set or the map note). NEVER fabricate a value, penalty, overdue list, figure, or date.
- The two domains (school-operations vs carter-case) share NO join key. Never answer one with the \
other's content; never invent a link.
- If sources conflict, surface BOTH with both citations — do not silently pick one.
- When you must refuse a half of the question (a concept the data can't support), still deliver the \
half you CAN answer from the same data: after the honest "not available + why", PIVOT to a real, \
cited figure you can compute (e.g. if asked about overdue maintenance payments — which has no \
status field — still give the total maintenance spend and ticket count from maintenance.csv, cited).
- For a PDF citation, the <locator> MUST be `p<N>` using the document's printed "PAGE N" label \
(e.g. `#p24`, `#p1`) — NOT a prose phrase. Find the nearest preceding printed "📑 PAGE N" header for \
your fact and cite that N.
- Answer in the language of the question (English or Hebrew); Hebrew must carry identical facts + \
citations + honesty.
- Use the injected anchor date asOfDate = 2026-06-09 for any "expiring / next N days" computation \
(window = [asOfDate, asOfDate + 90d]), never the wall clock.
- When you list a set (e.g. expiring contracts), STATE THE AGGREGATES in the prose too — the COUNT \
and the SUM (e.g. "38 contracts expire ... with a combined annual cost of $18,924,883.79") — not \
just an itemized table. The reader needs the headline totals stated explicitly.
- LARGE RESULT SET — DO NOT enumerate a citation token for every row. Compute the whole set in ONE \
pandas pass (filter + count + sum), then in the ANSWER: (a) state the COUNT and SUM as the headline, \
cited ONCE to the file with a computed locator (e.g. `[F:school-operations/contracts.csv#expiring-90d]`, \
backed by one evidence item describing the pandas filter); (b) show a SMALL illustrative sample — the \
EARLIEST-expiring 5 rows, ordered `End Date ASC, Vendor ASC, then source-row-index ASC` — each as a \
real `row=<Vendor>|<ISO-date>` citation; (c) say explicitly "full <N>-row list available on request". \
Do NOT emit 30+ per-row citation tokens or a 30+-item evidence array — the headline aggregate + a \
5-row cited sample is the grounded form, and it must be COMPUTED in pandas, not hand-typed row by row \
(hand-typing invites a wrong row key, which fails validation).

After you have retrieved and self-checked, output your FINAL answer in EXACTLY this two-block \
format and NOTHING else (no prose before or after, no markdown fence). The ANSWER block is free \
prose (you may use quotes, $ signs, newlines freely); the EVIDENCE block is a JSON array whose \
string fields must NOT contain raw double-quotes (use single quotes inside snippets):

===ANSWER===
<your prose answer here, with inline [F:<file>#<loc>] tokens; quotes and newlines are fine>
===EVIDENCE===
[{{"file": "<path under knowledge/>", "loc": "<locator>", "snippet": "<short quote, single-quotes only>"}}]

Every [F:file#loc] token in the ANSWER block MUST have a matching evidence item (same file + loc) in \
the EVIDENCE block. The `trace` and `validation` are added by the harness — do not include them. \
Output BOTH block markers exactly as shown."""


def _trace_for_tool(name: str, inp: dict) -> TraceStep | None:
    """Map a tool-use block to a structured trace step (map read / file opened / grep / note)."""
    arg = json.dumps(inp)
    if name == "Read":
        path = str(inp.get("file_path", inp.get("path", "")))
        if path.endswith("data_structure.md"):
            return TraceStep(kind="map", detail=f"read map {path}")
        return TraceStep(kind="open", detail=f"read {path}")
    if name == "Grep":
        return TraceStep(kind="grep", detail=f"grep {inp.get('pattern','')} in {inp.get('path','')}")
    if name == "Glob":
        return TraceStep(kind="grep", detail=f"glob {inp.get('pattern','')}")
    if name == "Bash":
        cmd = str(inp.get("command", ""))
        if "pdftotext" in cmd or "pdfplumber" in cmd:
            return TraceStep(kind="open", detail=f"pdf extract: {cmd[:160]}")
        if "pandas" in cmd or "read_csv" in cmd or "python" in cmd:
            return TraceStep(kind="open", detail=f"pandas: {cmd[:160]}")
        return TraceStep(kind="note", detail=f"bash: {cmd[:160]}")
    return TraceStep(kind="note", detail=f"{name} {arg[:120]}")


def _balanced_object(text: str) -> str | None:
    """Return the first balanced {...} block, ignoring braces inside JSON strings."""
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        else:
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return text[start : i + 1]
    return None


def _escape_control_chars_in_strings(blob: str) -> str:
    """Escape raw newlines/tabs that appear INSIDE JSON string literals.

    Agents sometimes emit a multi-line answer with literal newlines inside the string value, which
    is invalid JSON. This walks the blob and converts control chars to their escaped form only when
    inside a string.
    """
    out = []
    in_str = False
    esc = False
    for ch in blob:
        if in_str:
            if esc:
                out.append(ch)
                esc = False
                continue
            if ch == "\\":
                out.append(ch)
                esc = True
                continue
            if ch == '"':
                in_str = False
                out.append(ch)
                continue
            if ch == "\n":
                out.append("\\n")
                continue
            if ch == "\r":
                out.append("\\r")
                continue
            if ch == "\t":
                out.append("\\t")
                continue
            out.append(ch)
        else:
            if ch == '"':
                in_str = True
            out.append(ch)
    return "".join(out)


ANSWER_MARK = "===ANSWER==="
EVIDENCE_MARK = "===EVIDENCE==="


def _parse_evidence_json(blob: str) -> list:
    """Parse the EVIDENCE JSON array defensively (balanced-bracket + control-char escape)."""
    blob = re.sub(r"^```(?:json)?\s*", "", blob.strip(), flags=re.MULTILINE)
    blob = re.sub(r"\s*```$", "", blob.strip(), flags=re.MULTILINE).strip()
    start = blob.find("[")
    end = blob.rfind("]")
    if start != -1 and end != -1 and end > start:
        blob = blob[start : end + 1]
    try:
        return json.loads(blob)
    except json.JSONDecodeError:
        return json.loads(_escape_control_chars_in_strings(blob))


def _extract_output(text: str) -> dict:
    """Parse the agent's final output.

    Primary format is the two-block ANSWER/EVIDENCE form — the ANSWER is raw prose (quotes/newlines
    are fine because it's NOT inside JSON), and only the small, prose-free EVIDENCE array is JSON.
    This sidesteps the "stray double-quote inside the answer string" break that one-object JSON hits.
    Falls back to the legacy single-JSON-object form for safety.
    """
    if ANSWER_MARK in text and EVIDENCE_MARK in text:
        after_answer = text.split(ANSWER_MARK, 1)[1]
        answer_part, evidence_part = after_answer.split(EVIDENCE_MARK, 1)
        answer = answer_part.strip()
        try:
            evidence = _parse_evidence_json(evidence_part)
        except Exception:
            evidence = []
        return {"answer": answer, "evidence": evidence}

    # Legacy fallback: a single JSON object.
    cleaned = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r"\s*```$", "", cleaned.strip(), flags=re.MULTILINE).strip()
    blob = _balanced_object(cleaned) or cleaned
    try:
        return json.loads(blob)
    except json.JSONDecodeError:
        pass
    try:
        return json.loads(_escape_control_chars_in_strings(blob))
    except json.JSONDecodeError:
        # Last resort: the agent answered in free prose without the contract
        # blocks (e.g. a hard refusal of a hijacked request). Don't 500 — return
        # the prose as an UN-grounded answer. validate() will mark it correctly:
        # if it makes uncited claims it fails the gate; a pure refusal passes.
        return {"answer": text.strip(), "evidence": []}


# ---------------------------------------------------------------------------
# Public-surface hardening (the agent is internet-exposed → a prompt-injection /
# RCE surface). The single enforcement point is the `_pre_tool_use` HOOK, which
# the SDK consults BEFORE every tool runs and which can hard-DENY a call (a
# denied tool never executes — the model sees the deny reason as the tool
# result). We verified empirically that on this SDK/CLI version the `can_use_tool`
# callback is NOT consulted on the query() path, but `PreToolUse` IS and a
# `permissionDecision: "deny"` genuinely blocks execution — so the hook, not the
# callback, is the real gate. (See docs/gotchas/agent-hardening-hook-not-callback.md.)
#
# Policy (ALLOW-LIST): only Read/Grep/Glob scoped to the `knowledge/` tree, and
# Bash limited to read-only extraction (pdftotext / a pandas python one-liner /
# grep & friends) over that tree. No Write/Edit, no network, no shell chaining
# beyond `&&`/`||` between allow-listed read-only programs, nothing that escapes
# `knowledge/`. Documented in 04-implementation.md (§Hardening) + docs/gotchas.
# ---------------------------------------------------------------------------

# `allowed_tools` only pre-approves which tools the model may attempt; it is NOT
# the security boundary (the CLI auto-approves these without escalating, so it
# can't enforce path/command scoping). The hook below is the boundary.
ALLOWED_TOOLS = ["Read", "Glob", "Grep", "Bash"]

# Read-only shell programs the agent may run (the kb-retriever skill's extract
# step: pdftotext for PDFs, a pandas/python one-liner for CSVs, plus harmless
# text inspection). EVERY program in a (possibly &&/||-chained) command must be
# one of these.
_ALLOWED_BASH_PROGRAMS = {
    "pdftotext", "python", "python3", "grep", "rg", "head", "tail",
    "cat", "wc", "ls", "find", "test", "sort", "uniq", "cut", "tr", "echo", "true",
}
# Hard-forbidden substrings: redirection to disk, command substitution, network
# clients, package managers, deploy CLIs, privilege/escape, and path escapes.
# These never appear in a legitimate read-only pdftotext/pandas/grep command.
_BASH_FORBIDDEN = (
    ">", "`", "$(", "${",
    "rm ", "mv ", "cp ", "chmod", "chown", "curl", "wget", "nc ", "netcat",
    "ssh", "scp", "git ", "pip ", "pip3", "npm ", "node ", "fly", "vercel",
    "/etc/", "/root", "sudo", "export ", "eval ",
    "-exec", "-delete", "-fprint",  # find's command-execution / write flags
)
# A path is in-scope iff it stays under the knowledge/ root after resolution.
_KB_ROOT = str(KB_PATH.resolve())


def _path_in_kb(raw: str) -> bool:
    """True iff `raw` resolves to a location inside the knowledge/ tree."""
    if not raw:
        return False
    try:
        from pathlib import Path as _P

        p = raw if raw.startswith("/") else str(PROJECT_ROOT / raw)
        resolved = str(_P(p).resolve())
    except Exception:
        return False
    return resolved == _KB_ROOT or resolved.startswith(_KB_ROOT + "/")


def _pattern_scoped_to_kb(pattern: str) -> bool:
    """True iff a Glob/Grep pattern is confined to the knowledge/ tree.

    Accepts a relative glob that starts at the knowledge root (e.g.
    'knowledge/**/*.csv') or an absolute path under it. Rejects a bare
    '**/*' that would scan the whole repo, and any '..' escape.
    """
    p = pattern.strip()
    if not p or ".." in p:
        return False
    if p.startswith("/"):
        # absolute: must sit under the knowledge root
        return p == _KB_ROOT or p.startswith(_KB_ROOT + "/")
    return p.startswith("knowledge/") or p == "knowledge"


def _python_oneliner_is_safe(cmd: str) -> bool:
    """A python/pandas extraction one-liner is safe iff it neither writes to disk
    nor shells out / networks. Reading CSVs with pandas is the intended use."""
    banned = (
        "os.system", "subprocess", "socket", "urllib", "requests", "shutil",
        "Path.write", ".write_text", ".write_bytes", ".to_csv", ".to_excel",
        "eval(", "exec(", "__import__", "open(",  # open() can write; pandas reads suffice
    )
    return not any(b in cmd for b in banned)


def _bash_is_readonly_kb(cmd: str) -> bool:
    """Vet a Bash command: read-only extraction confined to the knowledge/ tree.

    A command may chain allow-listed read-only programs with `&&`/`||`. It is
    allowed only when: (a) it contains no forbidden substring (redirection,
    command-substitution, network, package/deploy tools, privilege/escape),
    (b) every program token is allow-listed, (c) any python one-liner / heredoc
    is write-free and network-free, and (d) it references the knowledge/ tree
    (a bare `test -d knowledge` existence check is also fine).
    """
    c = cmd.strip()
    if not c:
        return False
    if any(tok in c for tok in _BASH_FORBIDDEN):
        return False
    # A python extraction (one-liner `python3 -c "..."` or a `python3 - <<'EOF'
    # ... EOF` heredoc) is vetted as a WHOLE and must be write/network-free. It
    # legitimately contains `;` inside its quoted body, so it is checked BEFORE
    # the pipe/semicolon guard below (which is for plain shell commands).
    if "python" in c.split()[0]:
        if not _python_oneliner_is_safe(c):
            return False
        return "knowledge" in c
    # No raw pipes/semicolons for plain shell (data exfil / transform chains).
    # `&&`/`||` are allowed and handled below; a lone `|` or `;` is not.
    stripped = c.replace("&&", " ").replace("||", " ")
    if "|" in stripped or ";" in stripped:
        return False
    # Split on the chain operators and require every segment's leading program
    # to be allow-listed.
    import re as _re

    for seg in _re.split(r"&&|\|\|", c):
        seg = seg.strip()
        if not seg:
            continue
        prog = seg.split()[0].rsplit("/", 1)[-1]
        if prog not in _ALLOWED_BASH_PROGRAMS:
            return False
        if prog in ("python", "python3") and not _python_oneliner_is_safe(seg):
            return False
    # Must actually be working over the knowledge tree (or an echo/test scaffold).
    if "knowledge" in c or c.split()[0] in ("echo", "test", "true", "ls"):
        return True
    return False


def _deny(reason: str) -> dict:
    """A PreToolUse hook result that hard-blocks the tool (model sees the reason)."""
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }


async def _pre_tool_use(input_data: dict, tool_use_id, context):
    """The real security boundary: deny anything outside the read-only KB policy.

    Returns {} to allow, or a deny decision the SDK enforces (the tool never
    runs). Verified: a deny here genuinely blocks execution on this SDK version.
    """
    name = input_data.get("tool_name", "")
    ti = input_data.get("tool_input", {}) or {}

    # Loading skill instructions is read-only (it injects the kb-retriever
    # methodology the agent already runs under) — allow it.
    if name in ("Skill", "TodoWrite"):
        return {}

    if name == "Read":
        path = str(ti.get("file_path") or ti.get("path") or "")
        if _path_in_kb(path):
            return {}
        return _deny(f"Reads are restricted to the knowledge/ tree; '{path}' is out of scope.")

    if name == "Glob":
        # Glob's file scope is the `pattern` (and an optional `path` root).
        path = str(ti.get("path") or "")
        pattern = str(ti.get("pattern") or "")
        if path:
            if _path_in_kb(path):
                return {}
            return _deny(f"Glob is restricted to the knowledge/ tree; '{path}' is out of scope.")
        if _pattern_scoped_to_kb(pattern):
            return {}
        return _deny(
            "Glob must be scoped to knowledge/ (set path='knowledge' or a "
            "'knowledge/...' pattern)."
        )

    if name == "Grep":
        # Grep's `pattern` is the search REGEX; the file scope is `path` and/or
        # the `glob` include filter. Require at least one to confine the search.
        path = str(ti.get("path") or "")
        glob = str(ti.get("glob") or "")
        if path:
            if _path_in_kb(path):
                return {}
            return _deny(f"Grep is restricted to the knowledge/ tree; '{path}' is out of scope.")
        if glob and _pattern_scoped_to_kb(glob):
            return {}
        return _deny(
            "Grep must be scoped to knowledge/ (set path='knowledge' or a "
            "glob='knowledge/...')."
        )

    if name == "Bash":
        cmd = str(ti.get("command", ""))
        if _bash_is_readonly_kb(cmd):
            return {}
        return _deny(
            "Only read-only extraction over knowledge/ is allowed (pdftotext / a "
            "pandas python one-liner / grep). No writes, no networking, no piping, "
            "no path escapes."
        )

    # Everything else (Write, Edit, WebFetch, WebSearch, Task, NotebookEdit, …).
    return _deny(f"Tool '{name}' is not permitted on this read-only knowledge assistant.")


async def _single_message_stream(question: str):
    """Wrap the question as the streaming-mode prompt the SDK consumes."""
    yield {
        "type": "user",
        "message": {"role": "user", "content": question},
    }


# A live-trace callback: invoked with each new TraceStep as the agent works, so a
# long run can stream progress (the async-job path uses this to show the agent's
# trace while it runs). Synchronous callers (the eval harness) pass None and just
# get the final trace on the returned AskResponse.
OnTrace = Callable[[TraceStep], Awaitable[None]]


async def answer_question(
    question: str, on_trace: Optional[OnTrace] = None
) -> AskResponse:
    """Run the agent for one question and return the Aletheia output contract.

    If `on_trace` is given, it is awaited with every TraceStep as it is produced —
    used by the async-job endpoint to stream the live agent trace to the UI while
    the (multi-minute) run is still in flight.
    """
    # Input guard: reject empty / over-long questions before spending an agent run.
    question = (question or "").strip()
    if not question:
        raise ValueError("question is empty")
    if len(question) > MAX_QUESTION_CHARS:
        raise ValueError(
            f"question too long ({len(question)} chars; max {MAX_QUESTION_CHARS})"
        )

    trace: list[TraceStep] = []
    result_text: str | None = None

    async def _emit(step: TraceStep) -> None:
        trace.append(step)
        if on_trace is not None:
            await on_trace(step)

    async for message in query(
        prompt=_single_message_stream(question),
        options=ClaudeAgentOptions(
            cwd=str(PROJECT_ROOT),
            setting_sources=["project"],   # load .claude/skills from the project
            skills=["kb-retriever"],
            allowed_tools=ALLOWED_TOOLS,
            permission_mode="bypassPermissions",  # the PreToolUse hook is the gate
            hooks={"PreToolUse": [HookMatcher(hooks=[_pre_tool_use])]},  # read-only enforcement
            add_dirs=[],                   # no extra roots beyond cwd
            system_prompt=SYSTEM_PROMPT,
            model=MODEL,
            max_turns=MAX_TURNS,
            thinking={"type": "adaptive", "display": "summarized"},
        ),
    ):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, ToolUseBlock):
                    step = _trace_for_tool(block.name, block.input)
                    if step:
                        await _emit(step)
                elif isinstance(block, ThinkingBlock) and block.thinking.strip():
                    # keep a compact note of reasoning checkpoints (self-check visibility)
                    t = block.thinking.strip()
                    if any(k in t.lower() for k in ("self-check", "re-grep", "conflict", "not available", "absence")):
                        await _emit(TraceStep(kind="note", detail=f"reasoning: {t[:200]}"))
        elif isinstance(message, ResultMessage):
            result_text = message.result

    if not result_text:
        raise RuntimeError("Agent returned empty result")

    parsed = _extract_output(result_text)
    answer = parsed.get("answer", "")
    evidence = [EvidenceItem(**e) for e in parsed.get("evidence", [])]

    ok, reasons = validate(answer, evidence, KB_PATH)

    return AskResponse(
        question=question,
        answer=answer,
        evidence=evidence,
        trace=trace,
        validation=Validation(ok=ok, reasons=reasons),
    )
