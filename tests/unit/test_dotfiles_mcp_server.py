"""Unit tests for dotfiles_mcp_server.py (Contextual Layer & System MCP Server)."""

from __future__ import annotations

import io
import json
import subprocess
from types import SimpleNamespace
from typing import TYPE_CHECKING

import dotfiles_mcp_server
import pytest
from dotfiles_mcp_server import DotfilesMCPServer

if TYPE_CHECKING:
    from pathlib import Path


def test_read_version_returns_default_when_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Arrange
    monkeypatch.setattr(dotfiles_mcp_server, "REPO_DIR", tmp_path)

    # Act
    version = dotfiles_mcp_server._read_version()

    # Assert
    assert version == "0.0.0"


def test_read_os_pretty_name_parses_os_release_or_falls_back(tmp_path: Path) -> None:
    # Arrange
    fake_os_release = tmp_path / "os-release"
    fake_os_release.write_text('NAME="Ubuntu"\nPRETTY_NAME="Ubuntu 26.04 LTS"\n', encoding="utf-8")

    # Act
    pretty = dotfiles_mcp_server._read_os_pretty_name(fake_os_release)
    default_pretty = dotfiles_mcp_server._read_os_pretty_name()

    # Assert
    assert pretty == "Ubuntu 26.04 LTS"
    assert len(default_pretty) > 0


def test_read_os_pretty_name_fallback_when_file_missing_or_without_key(tmp_path: Path) -> None:
    # Arrange
    fake_os_release = tmp_path / "os-release-no-pretty"
    fake_os_release.write_text("ID=ubuntu\n", encoding="utf-8")
    missing_os_release = tmp_path / "does-not-exist"

    # Act
    pretty_no_key = dotfiles_mcp_server._read_os_pretty_name(fake_os_release)
    pretty_missing = dotfiles_mcp_server._read_os_pretty_name(missing_os_release)

    # Assert
    assert len(pretty_no_key) > 0
    assert len(pretty_missing) > 0


def test_read_git_commit_handles_missing_git_and_oserror(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    monkeypatch.setattr("shutil.which", lambda _name: None)

    # Act
    no_git_result = dotfiles_mcp_server._read_git_commit()

    # Assert
    assert no_git_result == "unknown"


def test_read_git_commit_handles_nonzero_and_oserror_with_git_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    monkeypatch.setattr("shutil.which", lambda _name: "/usr/bin/git")
    fail_proc = subprocess.CompletedProcess(args=["git"], returncode=1, stdout="", stderr="fatal")
    monkeypatch.setattr("subprocess.run", lambda *_a, **_k: fail_proc)

    # Act
    nonzero_result = dotfiles_mcp_server._read_git_commit()

    def _raise_oserror(*_args: object, **_kwargs: object) -> None:
        raise OSError("failed to spawn")

    monkeypatch.setattr("subprocess.run", _raise_oserror)
    oserror_result = dotfiles_mcp_server._read_git_commit()

    # Assert
    assert nonzero_result == "unknown"
    assert oserror_result == "unknown"


def test_parse_skill_frontmatter_handles_missing_frontmatter_and_fields(
    tmp_path: Path,
) -> None:
    # Arrange
    skill_dir = tmp_path / "custom-skill"
    skill_dir.mkdir()
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text("# No frontmatter here\n", encoding="utf-8")
    partial_dir = tmp_path / "partial-skill"
    partial_dir.mkdir()
    partial_md = partial_dir / "SKILL.md"
    partial_md.write_text("---\nother: value\n---\n# Body\n", encoding="utf-8")
    unclosed_dir = tmp_path / "unclosed-skill"
    unclosed_dir.mkdir()
    unclosed_md = unclosed_dir / "SKILL.md"
    unclosed_md.write_text("---\nname: unclosed\n", encoding="utf-8")

    # Act
    old_repo = dotfiles_mcp_server.REPO_DIR
    dotfiles_mcp_server.REPO_DIR = tmp_path
    try:
        meta_none = dotfiles_mcp_server._parse_skill_frontmatter(skill_md)
        meta_partial = dotfiles_mcp_server._parse_skill_frontmatter(partial_md)
        meta_unclosed = dotfiles_mcp_server._parse_skill_frontmatter(unclosed_md)
    finally:
        dotfiles_mcp_server.REPO_DIR = old_repo

    # Assert
    assert meta_none["name"] == "custom-skill"
    assert meta_none["description"] == ""
    assert meta_partial["name"] == "partial-skill"
    assert meta_partial["description"] == ""
    assert meta_unclosed["name"] == "unclosed-skill"


def test_read_non_empty_lines_handles_missing_file_and_comments(tmp_path: Path) -> None:
    # Arrange
    sample = tmp_path / "packages.txt"
    sample.write_text("# comment\n\ncurl\ngit\n", encoding="utf-8")

    # Act
    missing_lines = dotfiles_mcp_server._read_non_empty_lines(tmp_path / "missing.txt")
    valid_lines = dotfiles_mcp_server._read_non_empty_lines(sample)

    # Assert
    assert missing_lines == []
    assert valid_lines == ["curl", "git"]


def test_load_layer_manifest_applies_overrides_and_handles_missing_file(
    tmp_path: Path,
) -> None:
    # Arrange
    server = DotfilesMCPServer(
        repo_dir=tmp_path,
        layer_id_override="acme-corp",
        layer_role_override="corporate",
    )

    # Act
    manifest = server._load_layer_manifest()

    # Assert
    assert manifest["layer_id"] == "acme-corp"
    assert manifest["layer_role"] == "corporate"


def test_load_layer_manifest_ignores_non_dict_json(tmp_path: Path) -> None:
    # Arrange
    sys_dir = tmp_path / "system"
    sys_dir.mkdir()
    (sys_dir / "mcp-layer.json").write_text("[1, 2, 3]", encoding="utf-8")
    server = DotfilesMCPServer(repo_dir=tmp_path)

    # Act
    manifest = server._load_layer_manifest()

    # Assert
    assert manifest["layer_id"] == "dotfiles-ubuntu-default"


def test_resolve_safe_path_blocks_invalid_paths_and_missing_files(
    tmp_path: Path,
) -> None:
    # Arrange
    server = DotfilesMCPServer(repo_dir=tmp_path)
    (tmp_path / "bootstrap.sh").write_text("#!/bin/sh\n", encoding="utf-8")
    outside_file = tmp_path.parent / "outside_secret.txt"
    outside_file.write_text("secret", encoding="utf-8")
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    escape_link = docs_dir / "escape.md"
    escape_link.symlink_to(outside_file)

    # Act
    with pytest.raises(ValueError, match="Invalid or forbidden"):
        server._resolve_safe_path("")
    with pytest.raises(ValueError, match="Invalid or forbidden"):
        server._resolve_safe_path("../outside.txt")
    with pytest.raises(ValueError, match="Path escapes repository root"):
        server._resolve_safe_path("docs/escape.md")
    with pytest.raises(ValueError, match="Access denied"):
        server._resolve_safe_path("bootstrap.sh")
    with pytest.raises(FileNotFoundError, match="Document not found"):
        server._resolve_safe_path("docs/missing.md")

    # Assert
    outside_file.unlink()
    assert escape_link.is_symlink()


def test_read_resource_handles_empty_nvm_and_templates_with_files(
    tmp_path: Path,
) -> None:
    # Arrange
    (tmp_path / "system").mkdir()
    tpl_root = tmp_path / "templates"
    tpl_root.mkdir()
    (tpl_root / "README.txt").write_text("not a dir", encoding="utf-8")
    server = DotfilesMCPServer(repo_dir=tmp_path)

    # Act
    manifests_res = json.loads(server.read_resource("dotfiles://system/manifests")["text"])
    templates_res = json.loads(server.read_resource("dotfiles://governance/templates")["text"])

    # Assert
    assert manifests_res["nvm_default"] == "none"
    assert templates_res["count"] == 0


def test_read_resource_handles_missing_templates_dir(tmp_path: Path) -> None:
    # Arrange
    server = DotfilesMCPServer(repo_dir=tmp_path)

    # Act
    templates_res = json.loads(server.read_resource("dotfiles://governance/templates")["text"])

    # Assert
    assert templates_res == {"count": 0, "templates": []}


def test_read_resource_raises_on_unknown_uri() -> None:
    # Arrange
    server = DotfilesMCPServer()

    # Act
    with pytest.raises(ValueError, match="Unknown resource URI"):
        server.read_resource("dotfiles://unknown/resource")

    # Assert
    assert server.repo_dir.is_dir()


def test_call_tool_audit_node_drift_handles_invalid_mode_and_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    server = DotfilesMCPServer()
    fail_proc = subprocess.CompletedProcess(
        args=["verify"], returncode=1, stdout="\x1b[31mFAIL\x1b[0m\n", stderr=""
    )
    monkeypatch.setattr("subprocess.run", lambda *_a, **_k: fail_proc)

    # Act
    with pytest.raises(ValueError, match="Invalid mode"):
        server.call_tool("audit_node_drift", {"mode": "invalid"})
    both_result = server.call_tool("audit_node_drift", {"mode": "both"})

    # Assert
    parsed = json.loads(both_result["content"][0]["text"])
    assert parsed["healthy"] is False
    assert parsed["checks"]["verify_repo"]["output"] == "FAIL"
    assert parsed["checks"]["system_audit"]["passed"] is False


def test_call_tool_audit_node_drift_supports_individual_modes_and_passing_checks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    server = DotfilesMCPServer()
    ok_proc = subprocess.CompletedProcess(args=["verify"], returncode=0, stdout="OK\n", stderr="")
    monkeypatch.setattr("subprocess.run", lambda *_a, **_k: ok_proc)

    # Act
    verify_only = server.call_tool("audit_node_drift", {"mode": "verify-repo"})
    audit_only = server.call_tool("audit_node_drift", {"mode": "system-audit"})

    # Assert
    v_parsed = json.loads(verify_only["content"][0]["text"])
    a_parsed = json.loads(audit_only["content"][0]["text"])
    assert v_parsed["healthy"] is True
    assert list(v_parsed["checks"].keys()) == ["verify_repo"]
    assert a_parsed["healthy"] is True
    assert list(a_parsed["checks"].keys()) == ["system_audit"]


def test_call_tool_query_governance_rules_handles_empty_query_and_missing_files(
    tmp_path: Path,
) -> None:
    # Arrange
    server = DotfilesMCPServer(repo_dir=tmp_path)
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    doc_file = docs_dir / "guide.md"
    doc_file.write_text(
        "Intro text without h1\n## Section One\nAlpha keyword\n### Section Two\nBeta\n",
        encoding="utf-8",
    )
    empty_doc = docs_dir / "empty.md"
    empty_doc.write_text("", encoding="utf-8")

    # Act
    with pytest.raises(ValueError, match="non-empty string"):
        server.call_tool("query_governance_rules", {"query": "   "})
    res_docs = server.call_tool("query_governance_rules", {"query": "alpha", "scope": "docs"})
    res_global = server.call_tool("query_governance_rules", {"query": "alpha", "scope": "global"})
    res_templates = server.call_tool(
        "query_governance_rules", {"query": "alpha", "scope": "templates"}
    )

    # Assert
    parsed = json.loads(res_docs["content"][0]["text"])
    assert parsed["match_count"] == 1
    assert parsed["matches"][0]["section"] == "Section One"
    assert json.loads(res_global["content"][0]["text"])["match_count"] == 0
    assert json.loads(res_templates["content"][0]["text"])["match_count"] == 0


def test_call_tool_discover_federated_mcps_with_filter() -> None:
    # Arrange
    server = DotfilesMCPServer()

    # Act
    matched = server.call_tool("discover_federated_mcps", {"filter_role": "documentation"})
    unmatched = server.call_tool("discover_federated_mcps", {"filter_role": "nonexistent-role"})
    env_filtered = server.call_tool(
        "discover_federated_mcps", {"environment": "pre", "layer": "root"}
    )
    with pytest.raises(ValueError, match="Invalid environment"):
        server.call_tool("discover_federated_mcps", {"environment": "staging-invalid"})

    # Assert
    assert json.loads(matched["content"][0]["text"])["federated_mcp_count"] == 1
    assert json.loads(unmatched["content"][0]["text"])["federated_mcp_count"] == 0
    env_payload = json.loads(env_filtered["content"][0]["text"])
    assert env_payload["active_environment"] == "pre"
    assert env_payload["environment_profile"]["access_mode"] == "strictly-read-only"


def test_mounted_subtree_layers_discovery_and_multi_layer_orchestration(
    tmp_path: Path,
) -> None:
    # Arrange
    root_sys = tmp_path / "system"
    root_sys.mkdir()
    (root_sys / "mcp-layer.json").write_text(
        json.dumps(
            {
                "layer_id": "corp-root",
                "layer_role": "corporate",
                "environments": {"pre": {"access_mode": "strictly-read-only"}},
                "federated_mcps": [
                    {
                        "mcp_id": "corp-sec-mcp",
                        "role": "security",
                        "environments": ["pre", "pro"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    layers_dir = tmp_path / "layers"
    layers_dir.mkdir()
    (layers_dir / ".hidden").mkdir()
    (layers_dir / "README.txt").write_text("ignore file", encoding="utf-8")

    dept_dir = layers_dir / "dept-data"
    (dept_dir / "system").mkdir(parents=True)
    (dept_dir / "VERSION").write_text("1.4.0\n", encoding="utf-8")
    (dept_dir / "docs").mkdir()
    (dept_dir / "docs" / "data_spec.md").write_text(
        "# Data Spec\n## BigQuery Rules\nPartition by date.\n", encoding="utf-8"
    )
    (dept_dir / "system" / "mcp-layer.json").write_text(
        json.dumps(
            {
                "layer_id": "acme-dept-data",
                "layer_role": "department",
                "federated_mcps": [
                    {
                        "mcp_id": "bq-catalog-mcp",
                        "role": "database",
                        "environments": ["dev", "tst"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    server = DotfilesMCPServer(repo_dir=tmp_path)

    # Act
    discovered = server._discover_mounted_layers()
    overview_sub = json.loads(
        server.call_tool("get_layer_overview", {"layer": "acme-dept-data"})["content"][0]["text"]
    )
    doc_sub = server.call_tool(
        "read_layer_document",
        {"relative_path": "docs/data_spec.md", "layer": "dept-data"},
    )["content"][0]["text"]
    query_all = json.loads(
        server.call_tool("query_governance_rules", {"query": "Partition", "layer": "all"})[
            "content"
        ][0]["text"]
    )
    query_sub = json.loads(
        server.call_tool("query_governance_rules", {"query": "Partition", "layer": "dept-data"})[
            "content"
        ][0]["text"]
    )
    mcps_all = json.loads(
        server.call_tool("discover_federated_mcps", {"layer": "all"})["content"][0]["text"]
    )
    mcps_tst = json.loads(
        server.call_tool("discover_federated_mcps", {"layer": "dept-data", "environment": "tst"})[
            "content"
        ][0]["text"]
    )
    with pytest.raises(ValueError, match="Unknown or unmounted layer"):
        server.call_tool("get_layer_overview", {"layer": "nonexistent-layer"})

    # Assert
    assert len(discovered) == 1
    assert discovered[0]["layer_id"] == "acme-dept-data"
    assert overview_sub["channel_1_node_and_system_state"]["layer_id"] == "acme-dept-data"
    assert overview_sub["channel_3_active_invariants_and_hooks"]["agents_md_bytes"] == 0
    assert "Partition by date" in doc_sub
    assert query_all["match_count"] == 1
    assert query_sub["match_count"] == 1
    assert mcps_all["federated_mcp_count"] == 2
    assert mcps_tst["federated_mcp_count"] == 1
    assert mcps_tst["federated_mcps"][0]["source_layer"] == "acme-dept-data"


def test_call_tool_compare_layer_patterns_without_templates_dir(
    tmp_path: Path,
) -> None:
    # Arrange
    skills_dir = tmp_path / "antigravity/.gemini/config/skills/sopen"
    skills_dir.mkdir(parents=True)
    (skills_dir / "SKILL.md").write_text(
        "---\nname: sopen\ndescription: open\n---\n", encoding="utf-8"
    )
    server = DotfilesMCPServer(repo_dir=tmp_path)

    # Act
    res = server.call_tool(
        "compare_layer_patterns",
        {"project_rules": ["coding.md"], "project_skills": ["sopen", "novel"]},
    )

    # Assert
    parsed = json.loads(res["content"][0]["text"])
    assert parsed["already_in_layer_a_skills"] == ["sopen"]
    assert parsed["candidates_for_upward_promotion"]["novel_skills"] == ["novel"]


def test_call_tool_raises_on_unknown_tool_and_unknown_prompt() -> None:
    # Arrange
    server = DotfilesMCPServer()

    # Act
    with pytest.raises(ValueError, match="Unknown tool name"):
        server.call_tool("nonexistent_tool", {})
    with pytest.raises(ValueError, match="Unknown prompt name"):
        server.get_prompt("nonexistent_prompt", {})

    # Assert
    assert len(server.list_prompts()) == 3


def test_handle_request_covers_notifications_ping_templates_and_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    server = DotfilesMCPServer()

    # Act
    notif_resp = server.handle_request({"jsonrpc": "2.0", "method": "notifications/initialized"})
    ping_resp = server.handle_request({"jsonrpc": "2.0", "id": 10, "method": "ping"})
    tpl_resp = server.handle_request(
        {"jsonrpc": "2.0", "id": 11, "method": "resources/templates/list"}
    )
    not_found_resp = server.handle_request({"jsonrpc": "2.0", "id": 12, "method": "unknown/method"})
    invalid_param_resp = server.handle_request(
        {
            "jsonrpc": "2.0",
            "id": 13,
            "method": "resources/read",
            "params": {"uri": "dotfiles://invalid"},
        }
    )

    def _boom() -> list[dict[str, object]]:
        raise RuntimeError("unexpected failure")

    monkeypatch.setattr(server, "list_resources", _boom)
    internal_err_resp = server.handle_request(
        {"jsonrpc": "2.0", "id": 14, "method": "resources/list"}
    )

    # Assert
    assert notif_resp is None
    assert ping_resp == {"jsonrpc": "2.0", "id": 10, "result": {}}
    assert tpl_resp == {"jsonrpc": "2.0", "id": 11, "result": {"resourceTemplates": []}}
    assert not_found_resp is not None and not_found_resp["error"]["code"] == -32601
    assert invalid_param_resp is not None and invalid_param_resp["error"]["code"] == -32602
    assert internal_err_resp is not None and internal_err_resp["error"]["code"] == -32603


def test_run_stdio_loop_processes_line_and_content_length_and_invalid_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    server = DotfilesMCPServer()
    line_req = b'{"jsonrpc": "2.0", "id": 1, "method": "ping"}\n'
    notif_req = b'{"jsonrpc": "2.0", "method": "notifications/initialized"}\n'
    bad_json = b"{not-valid-json}\n"
    cl_body = b'{"jsonrpc": "2.0", "id": 2, "method": "ping"}'
    cl_req = f"Content-Length: {len(cl_body)}\r\nX-Extra: 1\r\n\r\n".encode("ascii") + cl_body
    raw_input = b"\n" + line_req + notif_req + bad_json + cl_req
    stdin_buffer = io.BytesIO(raw_input)
    stdout_buffer = io.BytesIO()
    monkeypatch.setattr("sys.stdin", SimpleNamespace(buffer=stdin_buffer))
    monkeypatch.setattr("sys.stdout", SimpleNamespace(buffer=stdout_buffer))

    # Act
    dotfiles_mcp_server.run_stdio_loop(server)

    # Assert
    output = stdout_buffer.getvalue().decode("utf-8")
    assert '"id": 1' in output
    assert '"code": -32700' in output
    assert "Content-Length:" in output


def test_run_stdio_loop_handles_eof_during_headers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    server = DotfilesMCPServer()
    raw_input = b"Content-Length: 39\r\n"
    stdin_buffer = io.BytesIO(raw_input)
    stdout_buffer = io.BytesIO()
    monkeypatch.setattr("sys.stdin", SimpleNamespace(buffer=stdin_buffer))
    monkeypatch.setattr("sys.stdout", SimpleNamespace(buffer=stdout_buffer))

    # Act
    dotfiles_mcp_server.run_stdio_loop(server)

    # Assert
    assert b'"code": -32700' in stdout_buffer.getvalue()


def test_require_raises_runtime_error_when_false() -> None:
    # Arrange
    msg = "expected failure"

    # Act
    with pytest.raises(RuntimeError, match="expected failure"):
        dotfiles_mcp_server._require(False, msg)

    # Assert
    dotfiles_mcp_server._require(True, "ok")


def test_main_runs_self_test_and_stdio_loop(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    called_stdio: list[bool] = []
    monkeypatch.setattr(
        dotfiles_mcp_server,
        "run_stdio_loop",
        lambda _srv: called_stdio.append(True),
    )

    # Act
    rc_self_test = dotfiles_mcp_server.main(["--self-test"])
    rc_self_test_no_log = dotfiles_mcp_server.main(["--self-test", "--no-log"])
    rc_stdio = dotfiles_mcp_server.main(
        ["--layer-id", "test-layer", "--layer-role", "team", "--no-log"]
    )

    # Assert
    assert rc_self_test == 0
    assert rc_self_test_no_log == 0
    assert rc_stdio == 0
    assert called_stdio == [True]


def test_structured_logging_rotation_token_budget_and_fanout_warnings(
    tmp_path: Path,
) -> None:
    # Arrange
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    events_log = log_dir / "mcp_events.jsonl"
    events_log.write_text("X" * (dotfiles_mcp_server.MAX_LOG_FILE_BYTES + 10), encoding="utf-8")

    agents_file = tmp_path / "antigravity/.gemini/config/AGENTS.md"
    agents_file.parent.mkdir(parents=True)
    agents_file.write_text("A" * 18500, encoding="utf-8")

    root_sys = tmp_path / "system"
    root_sys.mkdir()
    (root_sys / "mcp-layer.json").write_text(
        json.dumps(
            {
                "layer_id": "corp-root",
                "layer_role": "corporate",
                "baseline_guardrails": ["root-guardrail"],
                "federated_mcps": [{"mcp_id": f"mcp-{i}", "role": f"role-{i}"} for i in range(4)],
            }
        ),
        encoding="utf-8",
    )

    sub_no_manifest = tmp_path / "layers" / "sub-no-manifest"
    sub_no_manifest.mkdir(parents=True)
    sub_empty_up = tmp_path / "layers" / "sub-empty-upstream" / "system"
    sub_empty_up.mkdir(parents=True)
    (sub_empty_up / "mcp-layer.json").write_text(
        json.dumps({"layer_id": "sub-empty", "upstream_layer": {}}),
        encoding="utf-8",
    )

    server = DotfilesMCPServer(repo_dir=tmp_path, log_dir=log_dir)

    # Act
    overview_resp = server.handle_request(
        {
            "jsonrpc": "2.0",
            "id": 100,
            "method": "tools/call",
            "params": {"name": "get_layer_overview", "arguments": {"layer": "root"}},
        }
    )
    fanout_resp = server.call_tool("discover_federated_mcps", {"layer": "root"})

    # Assert
    assert overview_resp is not None
    assert (log_dir / "mcp_events.jsonl.1").is_file()
    assert (log_dir / "mcp_events.jsonl").is_file()
    assert (log_dir / "mcp_alerts.jsonl").is_file()
    overview_data = json.loads(overview_resp["result"]["content"][0]["text"])
    codes = [w["code"] for w in overview_data["channel_3_active_invariants_and_hooks"]["warnings"]]
    assert "TOKEN_BUDGET_EXCEEDED" in codes
    assert "SUBTREE_LINEAGE_WARNING" in codes
    fanout_data = json.loads(fanout_resp["content"][0]["text"])
    assert fanout_data["warnings"][0]["code"] == "MCP_FANOUT_WARNING"
    assert "root-guardrail" in fanout_data["federated_mcps"][0]["effective_guardrails"]
