"""Unit tests for dotfiles_mcp_server.py (Contextual Layer & System MCP Server)."""

from __future__ import annotations

import hashlib
import hmac
import io
import json
import subprocess
import tempfile
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
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    monkeypatch.setattr("shutil.which", lambda _name: None)
    monkeypatch.delenv("DOTFILES_GIT_COMMIT", raising=False)
    fake_marker = tmp_path / ".dockerenv"
    fake_marker.write_text("", encoding="utf-8")

    # Act
    no_git_result = dotfiles_mcp_server._read_git_commit()
    monkeypatch.setenv("DOTFILES_GIT_COMMIT", "abc1234")
    env_fallback_result = dotfiles_mcp_server._read_git_commit()
    in_container_true = dotfiles_mcp_server._is_running_in_container(fake_marker)
    in_container_false = dotfiles_mcp_server._is_running_in_container(tmp_path / "missing")

    # Assert
    assert no_git_result == "unknown"
    assert env_fallback_result == "abc1234"
    assert in_container_true is True
    assert in_container_false is False


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

    def _raise_ro_oserror(*_args: object, **_kwargs: object) -> object:
        raise OSError("Read-only file system")

    # Act
    rc_self_test = dotfiles_mcp_server.main(["--self-test"])
    rc_self_test_no_log = dotfiles_mcp_server.main(["--self-test", "--no-log"])
    monkeypatch.setattr(tempfile, "TemporaryDirectory", _raise_ro_oserror)
    rc_self_test_ro = dotfiles_mcp_server.main(["--self-test"])
    rc_stdio = dotfiles_mcp_server.main(
        ["--layer-id", "test-layer", "--layer-role", "team", "--no-log"]
    )

    # Assert
    assert rc_self_test == 0
    assert rc_self_test_no_log == 0
    assert rc_self_test_ro == 0
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
        json.dumps(
            {
                "layer_id": "sub-empty",
                "upstream_layer": {},
                "environments": {
                    "pre": {
                        "access_mode": "strictly-read-only",
                        "default_guardrails": ["subtree-pre-guardrail"],
                    }
                },
                "federated_mcps": [{"mcp_id": "sub-mcp", "role": "db", "environments": ["pre"]}],
            }
        ),
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
    sub_env_resp = server.call_tool(
        "discover_federated_mcps", {"layer": "sub-empty-upstream", "environment": "pre"}
    )

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
    sub_env_data = json.loads(sub_env_resp["content"][0]["text"])
    assert sub_env_data["environment_profile"]["access_mode"] == "strictly-read-only"
    assert "subtree-pre-guardrail" in sub_env_data["federated_mcps"][0]["effective_guardrails"]


def test_resonant_chained_compaction_l0_l1_l2_l3_unfolding_and_links(
    tmp_path: Path,
) -> None:
    # Arrange
    (tmp_path / "VERSION").write_text("1.6.4\n", encoding="utf-8")
    sys_dir = tmp_path / "system"
    sys_dir.mkdir()
    (sys_dir / "mcp-layer.json").write_text(
        json.dumps(
            {
                "layer_id": "corp-root",
                "baseline_guardrails": ["root-guard"],
                "environments": {
                    "pre": {
                        "access_mode": "strictly-read-only",
                        "default_guardrails": ["pre-guard"],
                    },
                    "pro": {
                        "access_mode": "strictly-read-only-audited",
                        "default_guardrails": ["pro-guard"],
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "bootstrap.sh").write_text("#!/bin/sh\n", encoding="utf-8")
    tpl_rules = tmp_path / "templates" / "fastapi-hexagonal" / "rules"
    tpl_rules.mkdir(parents=True)
    linked_rule = tpl_rules / "coding.md"
    linked_rule.write_text("# Coding Rule\nStrict typing required.\n", encoding="utf-8")

    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    spec_md = docs_dir / "spec.md"
    spec_md.write_text(
        "# Main Spec\n"
        "##1.6.4\n"
        "Lead prose line for symbol-only heading.\n"
        "## Resonant Section for the Resonant\n"
        '> *"Core resonance quote"*\n'
        "**Mandate:** Reuse existing helpers and "
        "**alpha** **beta** **gamma** **delta** **epsilon** **zeta**.\n"
        "| Col A | Col B |\n"
        "|---|---|\n"
        "```python\n"
        "x = 1\n"
        "```\n"
        "- Bullet 1 with [Web](https://example.com) and [Anchor](#top)\n"
        "- Bullet 2 with [Forbidden](../bootstrap.sh) and [Missing](missing.md)\n"
        "- Bullet 3 with [Coding](../templates/fastapi-hexagonal/rules/coding.md)\n"
        "- Bullet 4 with duplicate `templates/fastapi-hexagonal/rules/coding.md`\n"
        "- Bullet 5 folded overflow\n"
        "Extra trailing prose line.\n" + ("Padding text " * 650) + "\n",
        encoding="utf-8",
    )
    server = DotfilesMCPServer(repo_dir=tmp_path, log_dir=tmp_path / "logs")

    # Act
    q_l0_resp = (
        server.handle_request(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "query_governance_rules",
                    "arguments": {
                        "query": "Resonance",
                        "scope": "docs",
                        "resolution": "L0",
                        "environment": "pre",
                        "resonance_key": "secret-123",
                    },
                },
            }
        )
        or {}
    )
    q_l0 = json.loads(q_l0_resp["result"]["content"][0]["text"])
    q_l1 = json.loads(
        server.call_tool(
            "query_governance_rules",
            {
                "query": "Resonance",
                "scope": "docs",
                "resolution": "L1",
                "include_capsules": False,
            },
        )["content"][0]["text"]
    )
    q_l2 = json.loads(
        server.call_tool(
            "query_governance_rules",
            {"query": "Lead prose", "scope": "all", "resolution": "L2"},
        )["content"][0]["text"]
    )
    q_l2_trunc = json.loads(
        server.call_tool(
            "query_governance_rules",
            {"query": "Resonance", "scope": "docs", "resolution": "L2"},
        )["content"][0]["text"]
    )
    cap_l0 = q_l0["matches"][0]["capsule_token"]
    inspect_l0 = json.loads(
        server.call_tool(
            "unfold_context_capsule",
            {
                "capsule_token": cap_l0,
                "target_level": "L0",
                "environment": "pre",
                "resonance_key": "secret-123",
            },
        )["content"][0]["text"]
    )
    unfold_l1_resp = (
        server.handle_request(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "unfold_context_capsule",
                    "arguments": {
                        "capsule_token": cap_l0,
                        "agent_tier": "flash",
                        "environment": "pre",
                        "resonance_key": "secret-123",
                    },
                },
            }
        )
        or {}
    )
    unfold_l1 = json.loads(unfold_l1_resp["result"]["content"][0]["text"])
    unfold_l2 = json.loads(
        server.call_tool(
            "unfold_context_capsule",
            {
                "capsule_token": unfold_l1["next_capsule_token"],
                "target_level": "L2",
                "agent_tier": "inherit",
                "environment": "pre",
                "resonance_key": "secret-123",
            },
        )["content"][0]["text"]
    )
    unfold_l3 = json.loads(
        server.call_tool(
            "unfold_context_capsule",
            {
                "capsule_token": cap_l0,
                "target_level": "L3",
                "agent_tier": "pro",
                "environment": "pre",
                "resonance_key": "secret-123",
            },
        )["content"][0]["text"]
    )
    diag = json.loads(server.read_resource("dotfiles://mcp/diagnostics")["text"])

    # Assert
    assert q_l0["resolution"] == "L0"
    assert q_l0["token_compaction_metrics"]["savings_pct"] > 0
    assert "surface_preview" in q_l0["matches"][0]
    assert q_l1["resolution"] == "L1"
    assert q_l1["include_capsules"] is False
    assert q_l1["matches"][0]["capsule_token"] is None
    assert q_l1["token_compaction_metrics"]["capsule_overhead_tokens"] == 0
    assert "folded in rcap1:L1" in q_l1["matches"][0]["axiom_skeleton"]
    assert q_l2["match_count"] == 1
    assert q_l2_trunc["truncated"] is True
    assert inspect_l0["unfolded_level"] == "L0"
    assert inspect_l0["decrypted_hops"] == 0
    assert unfold_l1["unfolded_level"] == "L1"
    assert unfold_l1["unfold_chain"] == ["L0->L1"]
    assert unfold_l2["unfolded_level"] == "L2"
    assert unfold_l2["truncated"] is True
    assert len(unfold_l2["content"]["l3_links"]) == 1
    assert unfold_l3["unfolded_level"] == "L3"
    assert unfold_l3["unfold_chain"] == ["L0->L1", "L1->L2", "L2->L3"]
    assert len(unfold_l3["content"]["linked_l3_documents"]) == 1
    assert "pre-guard" in unfold_l3["content"]["effective_guardrails"]
    assert diag["resonance_compaction_summary"]["queries_by_resolution"]["L0"] == 1
    assert diag["resonance_compaction_summary"]["unfolds_by_target_level"]["L1"] == 1


def test_unfold_context_capsule_capability_environment_and_tamper_gates(
    tmp_path: Path,
) -> None:
    # Arrange
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    linked_md = docs_dir / "linked.md"
    linked_md.write_text("# Linked L3 Spec\nOriginal L3 body.\n", encoding="utf-8")
    doc_md = docs_dir / "gate.md"
    doc_md.write_text("# Gate\n## !!!\nBody line with [Linked](linked.md).\n", encoding="utf-8")
    server = DotfilesMCPServer(repo_dir=tmp_path, log_dir=tmp_path / "logs")

    q_pro = json.loads(
        server.call_tool(
            "query_governance_rules",
            {
                "query": "Body",
                "scope": "docs",
                "resolution": "L0",
                "environment": "pro",
                "resonance_key": "pro-key",
            },
        )["content"][0]["text"]
    )
    cap_pro_l0 = q_pro["matches"][0]["capsule_token"]
    q_default = json.loads(
        server.call_tool(
            "query_governance_rules",
            {"query": "Body", "scope": "docs", "resolution": "L0"},
        )["content"][0]["text"]
    )
    cap_l0_default = q_default["matches"][0]["capsule_token"]

    bad_lvl_hdr = dotfiles_mcp_server._b64url_encode(b'{"lvl":"L9"}')
    bad_lvl_token = f"rcap1.{bad_lvl_hdr}.YWJj.123456"

    secret = server._resolve_resonance_secret()
    ck = dotfiles_mcp_server._derive_chain_key(secret, "root", "L0", "ph1", "all")
    bad_zlib_cipher = dotfiles_mcp_server._b64url_encode(
        dotfiles_mcp_server._xor_keystream(b"not-valid-zlib", ck)
    )
    hdr_ph1 = dotfiles_mcp_server._b64url_encode(
        b'{"lvl":"L0","next":"L1","lyr":"root","env":"all","ph":"ph1"}'
    )
    sig_bad_zlib = hmac.new(
        ck, f"rcap1.{hdr_ph1}.{bad_zlib_cipher}".encode("ascii"), hashlib.sha256
    ).hexdigest()[:24]
    corrupt_zlib_token = f"rcap1.{hdr_ph1}.{bad_zlib_cipher}.{sig_bad_zlib}"

    bad_ph_token = dotfiles_mcp_server._seal_single_capsule(
        {"lvl": "L0", "next": "L1", "lyr": "root", "env": "all", "ph": "ph1"},
        {"ph": "different-ph"},
        ck,
    )

    # Act
    with pytest.raises(ValueError, match="Invalid resolution"):
        server.call_tool("query_governance_rules", {"query": "Body", "resolution": "L9"})
    with pytest.raises(ValueError, match="Invalid environment"):
        server.call_tool("query_governance_rules", {"query": "Body", "environment": "bad"})
    with pytest.raises(ValueError, match="Malformed rcap1"):
        server.call_tool("unfold_context_capsule", {"capsule_token": "invalid-token"})
    with pytest.raises(ValueError, match="Invalid base64 or JSON"):
        server.call_tool("unfold_context_capsule", {"capsule_token": "rcap1.!!!.YWJj.123"})
    with pytest.raises(ValueError, match="Invalid or unsupported rcap1"):
        server.call_tool("unfold_context_capsule", {"capsule_token": bad_lvl_token})
    with pytest.raises(ValueError, match="Invalid target_level"):
        server.call_tool(
            "unfold_context_capsule", {"capsule_token": cap_l0_default, "target_level": "L9"}
        )
    with pytest.raises(ValueError, match="Invalid agent_tier"):
        server.call_tool(
            "unfold_context_capsule", {"capsule_token": cap_l0_default, "agent_tier": "invalid"}
        )
    with pytest.raises(ValueError, match="Invalid environment"):
        server.call_tool(
            "unfold_context_capsule", {"capsule_token": cap_l0_default, "environment": "invalid"}
        )
    with pytest.raises(ValueError, match="bound to environment"):
        server.call_tool(
            "unfold_context_capsule",
            {"capsule_token": cap_pro_l0, "environment": "dev", "resonance_key": "pro-key"},
        )
    with pytest.raises(ValueError, match="requires an explicit resonance_key"):
        server.call_tool(
            "unfold_context_capsule",
            {"capsule_token": cap_pro_l0, "environment": "pro"},
        )
    with pytest.raises(ValueError, match="signature verification failed"):
        server.call_tool(
            "unfold_context_capsule",
            {"capsule_token": cap_pro_l0, "environment": "pro", "resonance_key": "wrong-key"},
        )
    l1_unfolded = json.loads(
        server.call_tool(
            "unfold_context_capsule", {"capsule_token": cap_l0_default, "target_level": "L1"}
        )["content"][0]["text"]
    )
    cap_l1 = l1_unfolded["next_capsule_token"]
    with pytest.raises(ValueError, match="must be deeper than capsule level"):
        server.call_tool("unfold_context_capsule", {"capsule_token": cap_l1, "target_level": "L1"})
    with pytest.raises(ValueError, match="Agent tier 'flash' is insufficient"):
        server.call_tool(
            "unfold_context_capsule",
            {"capsule_token": cap_l1, "target_level": "L2", "agent_tier": "flash"},
        )
    with pytest.raises(ValueError, match="Agent tier 'inherit' is insufficient"):
        server.call_tool(
            "unfold_context_capsule",
            {
                "capsule_token": cap_pro_l0,
                "target_level": "L3",
                "agent_tier": "inherit",
                "environment": "pro",
                "resonance_key": "pro-key",
            },
        )
    with pytest.raises(ValueError, match="Failed to decompress"):
        server.call_tool("unfold_context_capsule", {"capsule_token": corrupt_zlib_token})
    with pytest.raises(ValueError, match="parent hash mismatch"):
        server.call_tool("unfold_context_capsule", {"capsule_token": bad_ph_token})

    # Inserting lines above section ## !!! triggers line_drift_relocated=True
    doc_md.write_text(
        "# Gate\n\nInserted intro line 1.\nInserted intro line 2.\n## !!!\n"
        "Body line with [Linked](linked.md).\n",
        encoding="utf-8",
    )
    relocated_l1 = json.loads(
        server.call_tool("unfold_context_capsule", {"capsule_token": cap_l0_default})["content"][0][
            "text"
        ]
    )

    # Cross-node issuer mismatch check via another server instance with different layer_id
    other_node = DotfilesMCPServer(
        repo_dir=tmp_path, layer_id_override="other-service-node", log_dir=tmp_path / "logs"
    )
    err_rpc = (
        other_node.handle_request(
            {
                "jsonrpc": "2.0",
                "id": 99,
                "method": "tools/call",
                "params": {
                    "name": "unfold_context_capsule",
                    "arguments": {"capsule_token": cap_l0_default},
                },
            }
        )
        or {}
    )

    # Mutating linked L3 file preserves L1 & L2 unfolding, but breaks L3!
    linked_md.write_text("# Linked L3 Spec\nMutated L3 content!\n", encoding="utf-8")
    l2_still_ok = json.loads(
        server.call_tool("unfold_context_capsule", {"capsule_token": cap_l1, "target_level": "L2"})[
            "content"
        ][0]["text"]
    )
    with pytest.raises(ValueError, match="chain digest mismatch at L2->L3"):
        server.call_tool(
            "unfold_context_capsule",
            {"capsule_token": l2_still_ok["next_capsule_token"], "target_level": "L3"},
        )
    alerts_text = (tmp_path / "logs" / "mcp_alerts.jsonl").read_text(encoding="utf-8")

    # Assert
    assert relocated_l1["line_drift_relocated"] is True
    assert "Cross-node capsule mismatch" in err_rpc["error"]["message"]
    assert l2_still_ok["unfolded_level"] == "L2"
    assert "CAPSULE_CHAIN_BROKEN" in alerts_text
    assert "CAPSULE_RESONANCE_DENIED" in alerts_text
    assert "CAPSULE_CAPABILITY_INSUFFICIENT" in alerts_text


def test_resolve_surface_governance_across_zero_to_n_arbitrary_layers(
    tmp_path: Path,
) -> None:
    # Arrange
    agents_dir = tmp_path / "antigravity/.gemini/config"
    agents_dir.mkdir(parents=True)
    (agents_dir / "AGENTS.md").write_text(
        "# Global Engineering Rules\n"
        "## Reusability First\n"
        '> *"Scan workspace before creating duplicates"*\n'
        "- Reuse shared helpers\n"
        "- Keep functions small\n"
        "```python\n"
        "x = 1\n"
        "```\n",
        encoding="utf-8",
    )
    (tmp_path / "system").mkdir()
    (tmp_path / "system/mcp-layer.json").write_text(
        json.dumps(
            {
                "layer_id": "corp-it-baseline",
                "layer_role": "corporate",
                "precedence": 10,
                "baseline_guardrails": ["corp-type-safety"],
                "environments": {"pre": {"default_guardrails": ["pre-read-only"]}},
            }
        ),
        encoding="utf-8",
    )

    # Mount 3 arbitrary layers: statutory-privacy (5), design-tokens (30), internal-hr (50, pruned)
    priv_dir = tmp_path / "layers/statutory-privacy"
    (priv_dir / "system").mkdir(parents=True)
    (priv_dir / "docs").mkdir()
    (priv_dir / "templates/legal").mkdir(parents=True)
    (priv_dir / "templates/legal/consent.html").write_text(
        "<div class='consent'>GDPR Consent</div>\n", encoding="utf-8"
    )
    (priv_dir / "docs/privacy_rules.md").write_text(
        "# Statutory Privacy Rules\n"
        "## Explicit Consent Gate\n"
        "Every PII form must render `templates/legal/consent.html`.\n",
        encoding="utf-8",
    )
    (priv_dir / "system/mcp-layer.json").write_text(
        json.dumps(
            {
                "layer_id": "org-statutory-privacy",
                "layer_role": "domain-policy",
                "precedence": 5,
                "baseline_guardrails": ["gdpr-art-25-by-design"],
                "surface_bindings": [
                    {
                        "binding_id": "pii-consent-mandate",
                        "target_globs": ["templates/**"],
                        "architectural_planes": ["presentation"],
                        "scopes": ["checkout", "legal"],
                        "traits": ["pii"],
                        "mode": "authoritative",
                        "rule_files": ["docs/privacy_rules.md", "docs/missing_rule.md"],
                        "canonical_templates": ["templates/legal/consent.html"],
                        "invariants": ["Explicit opt-in checkbox required before submit"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    design_dir = tmp_path / "layers/design-tokens"
    (design_dir / "system").mkdir(parents=True)
    (design_dir / "docs").mkdir()
    (design_dir / "docs/ui_tokens.md").write_text(
        "# Design System Tokens\n"
        "## Semantic CSS Tokens\n"
        '> *"Never hardcode hex colors"*\n'
        "- Use semantic CSS variables\n",
        encoding="utf-8",
    )
    (design_dir / "system/mcp-layer.json").write_text(
        json.dumps(
            {
                "layer_id": "org-design-tokens",
                "layer_role": "department",
                "precedence": 30,
                "surface_bindings": [
                    {
                        "binding_id": "ui-token-consistency",
                        "target_globs": ["templates/**", "*.html"],
                        "architectural_planes": ["presentation"],
                        "scopes": ["*"],
                        "traits": [],
                        "mode": "transversal",
                        "rule_files": ["docs/ui_tokens.md"],
                        "canonical_templates": [],
                        "invariants": ["WCAG 2.1 AA contrast >= 4.5:1"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    hr_dir = tmp_path / "layers/internal-hr"
    (hr_dir / "system").mkdir(parents=True)
    (hr_dir / "system/mcp-layer.json").write_text(
        json.dumps(
            {
                "layer_id": "org-internal-hr",
                "layer_role": "department",
                "precedence": 50,
                "surface_bindings": [
                    {
                        "binding_id": "hr-payroll-only",
                        "target_globs": ["src/payroll/**"],
                        "architectural_planes": ["domain"],
                        "scopes": ["payroll"],
                        "traits": ["internal"],
                        "mode": "authoritative",
                        "rule_files": [],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    server = DotfilesMCPServer(repo_dir=tmp_path, log_dir=tmp_path / "logs")

    # Act
    with pytest.raises(ValueError, match="At least one surface selector"):
        server.call_tool("resolve_surface_governance", {})
    with pytest.raises(ValueError, match="Invalid architectural_plane"):
        server.call_tool("resolve_surface_governance", {"architectural_plane": "unknown-plane"})
    with pytest.raises(ValueError, match="Invalid environment"):
        server.call_tool(
            "resolve_surface_governance", {"target_path": "README.md", "environment": "bad-env"}
        )
    with pytest.raises(ValueError, match="Invalid resolution_override"):
        server.call_tool(
            "resolve_surface_governance",
            {"target_path": "README.md", "resolution_override": "L9"},
        )

    adaptive_rpc = (
        server.handle_request(
            {
                "jsonrpc": "2.0",
                "id": 50,
                "method": "tools/call",
                "params": {
                    "name": "resolve_surface_governance",
                    "arguments": {
                        "target_path": "templates/checkout/summary.html",
                        "traits": ["pii"],
                        "environment": "pre",
                    },
                },
            }
        )
        or {}
    )
    adaptive_res = json.loads(adaptive_rpc["result"]["content"][0]["text"])
    l0_no_cap_res = json.loads(
        server.call_tool(
            "resolve_surface_governance",
            {
                "target_path": "README.md",
                "resolution_override": "L0",
                "include_capsules": False,
            },
        )["content"][0]["text"]
    )

    # Assert
    assert adaptive_res["surface_query"]["effective_plane"] == "presentation"
    assert adaptive_res["surface_query"]["effective_scope"] == "checkout"
    assert adaptive_res["participating_layers_count"] == 3
    assert [p["layer"] for p in adaptive_res["participating_layers"]] == [
        "statutory-privacy",
        "root",
        "design-tokens",
    ]
    assert adaptive_res["pruned_layers_count"] == 1
    assert adaptive_res["pruned_layers"][0]["layer"] == "internal-hr"
    assert [b["binding_id"] for b in adaptive_res["resolved_bindings"]] == [
        "pii-consent-mandate",
        "root-default-baseline",
        "ui-token-consistency",
    ]
    assert adaptive_res["resolved_bindings"][0]["resolution"] == "L2"
    assert adaptive_res["resolved_bindings"][1]["resolution"] == "L1"
    assert adaptive_res["resolved_bindings"][2]["resolution"] == "L1"
    assert adaptive_res["canonical_templates"] == ["statutory-privacy:templates/legal/consent.html"]
    assert any(w["code"] == "SURFACE_ASSET_MISSING" for w in adaptive_res["warnings"])
    assert "gdpr-art-25-by-design" in adaptive_res["effective_invariants"]
    assert "pre-read-only" in adaptive_res["effective_invariants"]
    assert l0_no_cap_res["surface_query"]["effective_plane"] == "all"
    assert l0_no_cap_res["surface_query"]["effective_scope"] == "all"
    assert l0_no_cap_res["resolved_bindings"][0]["sections"][0]["capsule_token"] is None
    assert "surface_preview" in l0_no_cap_res["resolved_bindings"][0]["sections"][0]
    assert l0_no_cap_res["token_compaction_metrics"]["capsule_overhead_tokens"] == 0


def test_resolve_surface_governance_precedence_collision_lex_specialis_and_validation_gates(
    tmp_path: Path,
) -> None:
    # Arrange
    root_dir = tmp_path / "collision_repo"
    (root_dir / "system").mkdir(parents=True)
    (root_dir / "docs").mkdir(parents=True)
    long_body = "A" * 1600
    (root_dir / "docs/many_sections.md").write_text(
        f"# Title\n## Sec 1\n{long_body}\n## Sec 2\nB\n## Sec 3\nC\n## Sec 4\nD\n",
        encoding="utf-8",
    )
    (root_dir / "system/mcp-layer.json").write_text(
        json.dumps(
            {
                "schema_version": "1.2",
                "layer_id": "corp-root",
                "layer_role": "corporate",
                "precedence": 20,
                "surface_bindings": [
                    {
                        "binding_id": "generic-checkout-owner",
                        "target_globs": ["**"],
                        "architectural_planes": ["*"],
                        "scopes": ["*"],
                        "traits": [],
                        "mode": "authoritative",
                        "rule_files": ["docs/many_sections.md"],
                        "canonical_templates": ["templates/missing_tpl.html"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    # Second layer at identical precedence=20 and mode='authoritative', but higher specificity_score
    fin_dir = root_dir / "layers/financial-ledger"
    (fin_dir / "system").mkdir(parents=True)
    (fin_dir / "docs").mkdir(parents=True)
    (fin_dir / "docs/ledger.md").write_text(
        "# Ledger\n## Double Entry\nEnforce double-entry ledger invariants.\n",
        encoding="utf-8",
    )
    (fin_dir / "system/mcp-layer.json").write_text(
        json.dumps(
            {
                "schema_version": "1.2",
                "layer_id": "org-financial-ledger",
                "layer_role": "domain-policy",
                "precedence": 20,
                "surface_bindings": [
                    {
                        "binding_id": "specific-checkout-ledger",
                        "target_globs": ["src/checkout/**"],
                        "architectural_planes": ["domain"],
                        "scopes": ["checkout"],
                        "traits": ["financial"],
                        "mode": "authoritative",
                        "rule_files": ["docs/ledger.md"],
                        "canonical_templates": [],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    server = DotfilesMCPServer(repo_dir=root_dir, log_dir=tmp_path / "logs")

    bad_schema_dir = tmp_path / "bad_schema"
    (bad_schema_dir / "system").mkdir(parents=True)
    (bad_schema_dir / "system/mcp-layer.json").write_text(
        json.dumps({"schema_version": "1.0"}), encoding="utf-8"
    )
    bad_layer_prec_dir = tmp_path / "bad_layer_prec"
    (bad_layer_prec_dir / "system").mkdir(parents=True)
    (bad_layer_prec_dir / "system/mcp-layer.json").write_text(
        json.dumps({"schema_version": "1.2", "precedence": 150}), encoding="utf-8"
    )
    bad_bind_prec_dir = tmp_path / "bad_bind_prec"
    (bad_bind_prec_dir / "system").mkdir(parents=True)
    (bad_bind_prec_dir / "system/mcp-layer.json").write_text(
        json.dumps(
            {
                "schema_version": "1.2",
                "surface_bindings": [{"binding_id": "b1", "precedence": -1}],
            }
        ),
        encoding="utf-8",
    )
    bad_mode_dir = tmp_path / "bad_mode"
    (bad_mode_dir / "system").mkdir(parents=True)
    (bad_mode_dir / "system/mcp-layer.json").write_text(
        json.dumps(
            {
                "schema_version": "1.2",
                "surface_bindings": [{"binding_id": "b1", "mode": "invalid-mode"}],
            }
        ),
        encoding="utf-8",
    )

    # Act
    res = json.loads(
        server.call_tool(
            "resolve_surface_governance",
            {"target_path": "src/checkout/service.py", "traits": ["financial"]},
        )["content"][0]["text"]
    )
    with pytest.raises(ValueError, match="Unsupported"):
        DotfilesMCPServer(repo_dir=bad_schema_dir)._load_layer_manifest()
    with pytest.raises(ValueError, match="Invalid layer precedence"):
        DotfilesMCPServer(repo_dir=bad_layer_prec_dir).call_tool(
            "resolve_surface_governance", {"target_path": "src/a.py"}
        )
    with pytest.raises(ValueError, match="Invalid binding precedence"):
        DotfilesMCPServer(repo_dir=bad_bind_prec_dir).call_tool(
            "resolve_surface_governance", {"target_path": "src/a.py"}
        )
    with pytest.raises(ValueError, match="Invalid surface_binding mode"):
        DotfilesMCPServer(repo_dir=bad_mode_dir).call_tool(
            "resolve_surface_governance", {"target_path": "src/a.py"}
        )

    # Assert
    # Lex Specialis: specific-checkout-ledger (score=10) beats generic-checkout-owner (score=0)
    assert [b["binding_id"] for b in res["resolved_bindings"]] == [
        "specific-checkout-ledger",
        "generic-checkout-owner",
    ]
    assert res["resolved_bindings"][0]["specificity_score"] == 10
    assert res["resolved_bindings"][1]["specificity_score"] == 0
    assert res["truncated"] is True
    warning_codes = [w["code"] for w in res["warnings"]]
    assert "SURFACE_PRECEDENCE_COLLISION" in warning_codes
    assert "SURFACE_ASSET_MISSING" in warning_codes
    assert "RESPONSE_TRUNCATED" in warning_codes
