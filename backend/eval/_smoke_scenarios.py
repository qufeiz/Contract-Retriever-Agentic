"""One-off SMOKE validation of the MAIN user scenarios (NOT the full N=5 acceptance gate), with
per-query cost. Run ONCE = 2 real agent calls:
  A) committed-corpus, LEAN skill, a real query (G-1 contracts-expiring) — proves kb-retriever-lean
     answers a real user question, grounded + cited.
  B) live upload of PDF + Excel(.xlsx), the client cross-source question (overdue + suspension) —
     proves the PDF+Excel combo end to end (upload -> agent -> cross-source cited answer).
Captures the SDK's total_cost_usd + token usage per query so we know what each query costs.

    PYTHONPATH=. .venv/bin/python -m backend.eval._smoke_scenarios
"""
import asyncio
import os
import traceback
from pathlib import Path

from backend.agent import answer_question
from backend.uploads import create_session, finalize_session_map, prune_session_now, store_upload
from backend.validate import extract_tokens

FIX = Path("docs/features/live-upload/fixtures")
OUT = open("/tmp/smoke_results.txt", "w")


def emit(*a):
    line = " ".join(str(x) for x in a)
    print(line, flush=True)
    OUT.write(line + "\n")
    OUT.flush()


def _ug(u, k):
    if u is None:
        return None
    return u.get(k) if isinstance(u, dict) else getattr(u, k, None)


def cost_line(s):
    c = s.get("total_cost_usd")
    u = s.get("usage")
    dur = (s.get("duration_ms") or 0) / 1000
    cstr = f"${c:.4f}" if isinstance(c, (int, float)) else str(c)
    return (
        f"COST {cstr} | model={s.get('model')} | turns={s.get('num_turns')} | {dur:.0f}s | "
        f"in={_ug(u,'input_tokens')} out={_ug(u,'output_tokens')} "
        f"cache_read={_ug(u,'cache_read_input_tokens')} cache_write={_ug(u,'cache_creation_input_tokens')}"
    )


async def scenario_A():
    emit("\n===== SCENARIO A: committed-corpus, LEAN skill (G-1 contracts expiring) =====")
    s = {}
    resp = await answer_question(
        "What contracts expire in the next 90 days and what penalties are defined in those contracts?",
        skill="lean",
        stats=s,
    )
    facts = {"38 contracts": "38" in resp.answer, "$18,924,883.79": "18,924,883.79" in resp.answer}
    emit("validation.ok:", resp.validation.ok, "| reasons:", resp.validation.reasons[:3])
    emit("facts:", facts)
    emit("answer[:500]:", resp.answer[:500].replace("\n", " "))
    emit(cost_line(s))
    return all(facts.values()) and resp.validation.ok, s


async def scenario_B():
    emit("\n===== SCENARIO B: UPLOAD PDF + EXCEL(.xlsx) cross-source (overdue + suspension) =====")
    session = create_session()
    try:
        for name in ["customers.xlsx", "service-agreement.pdf"]:
            store_upload(session, name, (FIX / name).read_bytes())
        finalize_session_map(session)
        s = {}
        resp = await answer_question(
            "Which customers have overdue payments, and what does their contract say about service suspension?",
            session_id=session.session_id,
            model=os.environ.get("UPLOAD_MODEL", "claude-sonnet-4-6"),
            stats=s,
        )
        toks = extract_tokens(resp.answer)
        opened = " ".join(t.detail for t in resp.trace if t.kind in ("open", "map", "grep"))
        facts = {
            "$18,965.50": "18,965.50" in resp.answer,
            "Contoso": "Contoso" in resp.answer,
            "xlsx row cite": any("customers.xlsx" in f for f, _ in toks),
            "pdf #p3 cite": any("service-agreement" in f and "p3" in l for f, l in toks),
            "opened both files": ("customers" in opened) and ("service-agreement" in opened),
        }
        emit("validation.ok:", resp.validation.ok, "| reasons:", resp.validation.reasons[:3])
        emit("facts:", facts)
        emit("citations:", [f"[F:{f}#{l}]" for f, l in toks][:12])
        emit("answer[:700]:", resp.answer[:700].replace("\n", " "))
        emit(cost_line(s))
        return all(facts.values()) and resp.validation.ok, s
    finally:
        prune_session_now(session.session_id)


async def main():
    only = os.environ.get("ONLY", "")
    results = {}
    _pairs = [("A", scenario_A), ("B", scenario_B)]
    for name, fn in ([(k, f) for k, f in _pairs if k == only] if only else _pairs):
        try:
            ok, s = await fn()
            results[name] = (ok, s.get("total_cost_usd"))
        except Exception as e:
            emit(f"SCENARIO {name} RAISED:", repr(e))
            emit(traceback.format_exc())
            results[name] = (False, None)
    emit("\n===== SUMMARY =====")
    total = 0.0
    for k, (ok, c) in results.items():
        emit(f"Scenario {k}: {'PASS' if ok else 'FAIL'} | cost={c}")
        if isinstance(c, (int, float)):
            total += c
    emit(f"TOTAL COST (2 queries): ${total:.4f}")
    OUT.close()


asyncio.run(main())
