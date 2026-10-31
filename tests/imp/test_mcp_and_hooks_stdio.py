"""Implementation/integration tests for MCP server and lifecycle hooks over stdio."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parents[2]
MCP_SERVER = REPO_DIR / "scripts" / "dotfiles_mcp_server.py"
HOOKS_DIR = REPO_DIR / "antigravity" / ".gemini" / "config" / "scripts"


def test_mcp_server_stdio_line_delimited_and_content_length_roundtrip(
    tmp_path: Path,
) -> None:
    # Arrange
    log_dir = tmp_path / "mcp_logs"
    line_req = (
        json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": "get_layer_overview", "arguments": {}},
            }
        )
        + "\n"
        + json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "query_governance_rules", "arguments": {"query": "e"}},
            }
        )
        + "\n"
    )
    body = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "discover_federated_mcps",
                "arguments": {"filter_role": "documentation"},
            },
        }
    ).encode("utf-8")
    framed_req = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii") + body

    # Act
    proc_line = subprocess.run(
        [sys.executable, str(MCP_SERVER), "--log-dir", str(log_dir)],
        input=line_req.encode("utf-8"),
        capture_output=True,
        timeout=10,
        check=True,
    )
    proc_framed = subprocess.run(
        [sys.executable, str(MCP_SERVER), "--log-dir", str(log_dir)],
        input=framed_req,
        capture_output=True,
        timeout=10,
        check=True,
    )

    # Assert
    resp_line = json.loads(proc_line.stdout.decode("utf-8").strip().splitlines()[0])
    overview = json.loads(resp_line["result"]["content"][0]["text"])
    assert "channel_1_node_and_system_state" in overview
    assert proc_framed.stdout.startswith(b"Content-Length:")
    _, payload = proc_framed.stdout.split(b"\r\n\r\n", 1)
    resp_framed = json.loads(payload.decode("utf-8"))
    fed = json.loads(resp_framed["result"]["content"][0]["text"])
    assert fed["federated_mcp_count"] == 1
    assert (log_dir / "mcp_events.jsonl").is_file()
    assert (log_dir / "mcp_alerts.jsonl").is_file()


def test_pre_tool_guard_subprocess_denies_git_push_and_allows_pytest() -> None:
    # Arrange
    guard_script = HOOKS_DIR / "pre_tool_guard.py"
    deny_payload = json.dumps(
        {
            "toolCall": {
                "name": "run_command",
                "args": {"CommandLine": "git push origin master"},
            }
        }
    )
    allow_payload = json.dumps(
        {
            "toolCall": {
                "name": "run_command",
                "args": {"CommandLine": "pytest -q"},
            }
        }
    )

    # Act
    deny_proc = subprocess.run(
        [sys.executable, str(guard_script)],
        input=deny_payload,
        capture_output=True,
        text=True,
        timeout=5,
        check=True,
    )
    allow_proc = subprocess.run(
        [sys.executable, str(guard_script)],
        input=allow_payload,
        capture_output=True,
        text=True,
        timeout=5,
        check=True,
    )

    # Assert
    assert json.loads(deny_proc.stdout)["decision"] == "deny"
    assert json.loads(allow_proc.stdout)["decision"] == "allow"
