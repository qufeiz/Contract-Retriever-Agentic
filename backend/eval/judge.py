"""The LLM-as-judge (Layer E, prose layer) — scores the genuinely-judgment part.

The deterministic gates (B/C/D/F) catch missing figures, bad citations, leaks, and wrong traces.
They cannot judge *is the refusal honest and specific?* or *is the conflict surfaced vs. buried?*.
A cheap model scores each answer against the fixture's golden rubric, returning PASS/FAIL + reason.
A judge FAIL on any run is a red the engineer must fix by improving the answer — never by weakening
the rubric. Uses claude-haiku (cheap) per the cost guidance.
"""
from __future__ import annotations

import json
import re

from claude_agent_sdk import AssistantMessage, ResultMessage, TextBlock, ClaudeAgentOptions, query

from backend.eval.fixtures import Fixture
from backend.models import AskResponse

JUDGE_MODEL = "claude-haiku-4-5"

JUDGE_PROMPT = """You are a strict evaluation judge. Given a QUESTION, a golden RUBRIC describing \
the required answer, and the assistant's ANSWER, decide whether the answer satisfies the rubric.

Be strict about honesty: if the rubric requires an honest "not available" and the answer fabricates \
a value, FAIL. If the rubric requires surfacing a conflict and the answer picks one side silently, \
FAIL. If a required figure or citation is missing or wrong, FAIL.

Output ONLY a JSON object: {{"verdict": "PASS" | "FAIL", "reason": "<one sentence>"}}

QUESTION:
{question}

RUBRIC (the golden bar):
{rubric}

ANSWER:
{answer}
"""


def _extract(text: str) -> dict:
    cleaned = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r"\s*```$", "", cleaned.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if m:
            return json.loads(m.group(0))
        raise


async def judge(fx: Fixture, resp: AskResponse) -> tuple[bool, str]:
    """Return (passed, reason). No tools — a pure prose judgment call."""
    prompt = JUDGE_PROMPT.format(question=fx.question, rubric=fx.judge_rubric, answer=resp.answer)
    result_text = None
    async for message in query(
        prompt=prompt,
        options=ClaudeAgentOptions(model=JUDGE_MODEL, allowed_tools=[], max_turns=1),
    ):
        if isinstance(message, ResultMessage):
            result_text = message.result
        elif isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock) and block.text.strip():
                    result_text = block.text
    if not result_text:
        return False, "judge returned empty"
    try:
        parsed = _extract(result_text)
    except Exception as e:
        return False, f"judge output unparseable: {e}"
    return parsed.get("verdict") == "PASS", parsed.get("reason", "")
