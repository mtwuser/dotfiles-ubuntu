"""Unit tests for dotfiles_mcp/tools_federation.py."""

from __future__ import annotations

import json
import subprocess
from typing import TYPE_CHECKING

import pytest
from dotfiles_mcp import constants
from dotfiles_mcp.server import DotfilesMCPServer

if TYPE_CHECKING:
    from pathlib import Path


class TestFederationToolsMixin:
    """Verify node overview, drift audit, document reading, federation, and pattern comparison."""

    def test_call_tool_audit_node_drift_handles_invalid_mode_and_failures(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Emit NODE_DRIFT_DETECTED warning and strip ANSI codes when drift scripts fail."""
        # Arrange
        server = DotfilesMCPServer()
        recorded_cmds: list[list[str]] = []
        fail_proc = subprocess.CompletedProcess(
            args=["verify"], returncode=1, stdout="\x1b[31mFAIL\x1b[0m\n", stderr=""
        )

        def _fake_fail(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
            recorded_cmds.append(list(cmd))
            return fail_proc

        monkeypatch.setattr("subprocess.run", _fake_fail)

        # Act
        with pytest.raises(ValueError, match="Invalid mode"):
            server.call_tool("audit_node_drift", {"mode": "invalid"})
        both_result = server.call_tool("audit_node_drift", {"mode": "both"})

        # Assert
        parsed = json.loads(both_result["content"][0]["text"])
        assert parsed["healthy"] is False
        assert parsed["checks"]["verify_repo"]["output"] == "FAIL"
        assert parsed["checks"]["system_audit"]["passed"] is False
        assert len(recorded_cmds) == 2
        assert recorded_cmds[0][0].endswith("scripts/verify-repo.sh")
        assert recorded_cmds[1][0].endswith("audit.sh")

    def test_call_tool_audit_node_drift_supports_individual_modes_and_passing_checks(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Execute verify-repo and system-audit modes individually when checks pass."""
        # Arrange
        server = DotfilesMCPServer()
        recorded_cmds: list[list[str]] = []
        ok_proc = subprocess.CompletedProcess(
            args=["verify"], returncode=0, stdout="OK\n", stderr=""
        )

        def _fake_ok(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
            recorded_cmds.append(list(cmd))
            return ok_proc

        monkeypatch.setattr("subprocess.run", _fake_ok)

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
        assert [c[0].rsplit("/", 1)[-1] for c in recorded_cmds] == ["verify-repo.sh", "audit.sh"]

    def test_call_tool_discover_federated_mcps_with_filter(self) -> None:
        """Filter federated MCPs by role and environment and reject invalid environments."""
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
        self,
        tmp_path: Path,
    ) -> None:
        """Discover mounted git subtrees under layers/* and query docs/MCPs across layers."""
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
            server.call_tool("get_layer_overview", {"layer": "acme-dept-data"})["content"][0][
                "text"
            ]
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
            server.call_tool(
                "query_governance_rules", {"query": "Partition", "layer": "dept-data"}
            )["content"][0]["text"]
        )
        mcps_all = json.loads(
            server.call_tool("discover_federated_mcps", {"layer": "all"})["content"][0]["text"]
        )
        mcps_tst = json.loads(
            server.call_tool(
                "discover_federated_mcps", {"layer": "dept-data", "environment": "tst"}
            )["content"][0]["text"]
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

    def test_structured_logging_rotation_token_budget_and_fanout_warnings(
        self,
        tmp_path: Path,
    ) -> None:
        """Rotate JSONL logs and emit token budget, subtree lineage, and fan-out alerts."""
        # Arrange
        log_dir = tmp_path / "logs"
        log_dir.mkdir()
        events_log = log_dir / "mcp_events.jsonl"
        events_log.write_text("X" * (constants.MAX_LOG_FILE_BYTES + 10), encoding="utf-8")

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
                    "federated_mcps": [
                        {"mcp_id": f"mcp-{i}", "role": f"role-{i}"} for i in range(4)
                    ],
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
                    "federated_mcps": [
                        {"mcp_id": "sub-mcp", "role": "db", "environments": ["pre"]}
                    ],
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
        codes = [
            w["code"] for w in overview_data["channel_3_active_invariants_and_hooks"]["warnings"]
        ]
        assert "TOKEN_BUDGET_EXCEEDED" in codes
        assert "SUBTREE_LINEAGE_WARNING" in codes
        fanout_data = json.loads(fanout_resp["content"][0]["text"])
        assert fanout_data["warnings"][0]["code"] == "MCP_FANOUT_WARNING"
        assert "root-guardrail" in fanout_data["federated_mcps"][0]["effective_guardrails"]
        sub_env_data = json.loads(sub_env_resp["content"][0]["text"])
        assert sub_env_data["environment_profile"]["access_mode"] == "strictly-read-only"
        assert "subtree-pre-guardrail" in sub_env_data["federated_mcps"][0]["effective_guardrails"]

    def test_call_tool_compare_layer_patterns_without_templates_dir(
        self,
        tmp_path: Path,
    ) -> None:
        """Compare consumer project rules/skills when templates/ directory is absent."""
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
