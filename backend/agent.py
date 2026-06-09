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

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    ThinkingBlock,
    ToolUseBlock,
    UserMessage,
    query,
)

from backend.config import MAX_TURNS, MODEL, PROJECT_ROOT, KB_PATH
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
        return json.loads(_escape_control_chars_in_strings(blob))


ALLOWED_TOOLS = ["Read", "Glob", "Grep", "Bash"]


async def answer_question(question: str) -> AskResponse:
    """Run the agent for one question and return the Aletheia output contract."""
    trace: list[TraceStep] = []
    result_text: str | None = None

    async for message in query(
        prompt=question,
        options=ClaudeAgentOptions(
            cwd=str(PROJECT_ROOT),
            setting_sources=["project"],   # load .claude/skills from the project
            skills=["kb-retriever"],
            allowed_tools=ALLOWED_TOOLS,
            permission_mode="bypassPermissions",   # headless backend: no interactive prompts
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
                        trace.append(step)
                elif isinstance(block, ThinkingBlock) and block.thinking.strip():
                    # keep a compact note of reasoning checkpoints (self-check visibility)
                    t = block.thinking.strip()
                    if any(k in t.lower() for k in ("self-check", "re-grep", "conflict", "not available", "absence")):
                        trace.append(TraceStep(kind="note", detail=f"reasoning: {t[:200]}"))
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
