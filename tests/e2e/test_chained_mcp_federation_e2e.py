"""End-to-end tests for chained multi-node MCP federation and git subtree orchestration."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from dotfiles_mcp.fork_configurator import (
    apply_fork_to_project,
    configure_fork_manifest,
    scaffold_template_pack,
)
from dotfiles_mcp.promotion_engine import (
    diff_project_against_layers,
    promote_project_asset_to_layer,
)
from dotfiles_mcp.server import DotfilesMCPServer

REPO_DIR = Path(__file__).resolve().parents[2]
MCP_SERVER = REPO_DIR / "scripts" / "dotfiles_mcp_server.py"
SUBTREE_SCRIPT = REPO_DIR / "scripts" / "layer-subtree.sh"


def _create_node_fixture(
    base_dir: Path,
    layer_id: str,
    layer_role: str,
    packages: list[str],
    manifest_extra: dict[str, object],
) -> None:
    """Create a realistic dotfiles-ubuntu layer/node directory structure."""
    base_dir.mkdir(parents=True, exist_ok=True)
    (base_dir / "VERSION").write_text("1.4.0\n", encoding="utf-8")
    (base_dir / "system").mkdir(parents=True, exist_ok=True)
    (base_dir / "system" / "packages-manual.txt").write_text(
        "\n".join(packages) + "\n", encoding="utf-8"
    )
    for fname in (
        "snaps.txt",
        "npm-globals.txt",
        "nvm-default.txt",
        "external.txt",
        "gnome-extensions.txt",
    ):
        (base_dir / "system" / fname).write_text("", encoding="utf-8")

    agents_dir = base_dir / "antigravity" / ".gemini" / "config"
    (agents_dir / "skills" / "sopen").mkdir(parents=True, exist_ok=True)
    (agents_dir / "AGENTS.md").write_text(
        f"# {layer_id} Rules\n## Security Mandate\nAlways validate inputs.\n",
        encoding="utf-8",
    )
    (agents_dir / "hooks.json").write_text('{"hooks": {}}\n', encoding="utf-8")
    (agents_dir / "skills" / "sopen" / "SKILL.md").write_text(
        "---\nname: sopen\ndescription: open session\n---\n", encoding="utf-8"
    )

    docs_dir = base_dir / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    (docs_dir / "README.md").write_text(
        f"# Documentation Index — {layer_id}\n## Overview\nNode docs for {layer_id}.\n",
        encoding="utf-8",
    )

    manifest = {
        "schema_version": "1.2",
        "layer_id": layer_id,
        "layer_role": layer_role,
        "description": f"E2E node {layer_id}",
        "upstream_layer": {
            "layer_id": "mtwuser/dotfiles-ubuntu",
            "repository": "https://github.com/mtwuser/dotfiles-ubuntu.git",
            "branch": "master",
        },
        **manifest_extra,
    }
    (base_dir / "system" / "mcp-layer.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )


def _run_mcp_stdio_batch(
    repo_dir: Path,
    log_dir: Path,
    requests: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Run a batch of JSON-RPC requests against a live MCP server subprocess."""
    env = dict(os.environ)
    env["DOTFILES_MCP_LOG_DIR"] = str(log_dir)
    runner_code = (
        "import pathlib, sys; "
        f"sys.path.insert(0, {str(REPO_DIR / 'scripts')!r}); "
        "from dotfiles_mcp import server as m; "
        f"srv = m.DotfilesMCPServer(repo_dir=pathlib.Path({str(repo_dir)!r}), "
        f"log_dir=pathlib.Path({str(log_dir)!r})); "
        "m.run_stdio_loop(srv)"
    )
    stdin_payload = "".join(json.dumps(req) + "\n" for req in requests).encode("utf-8")
    proc = subprocess.run(
        [sys.executable, "-c", runner_code],
        input=stdin_payload,
        capture_output=True,
        timeout=15,
        check=True,
        env=env,
    )
    return [json.loads(line) for line in proc.stdout.decode("utf-8").splitlines() if line.strip()]


class TestChainedMCPFederationE2E:
    """End-to-end test suite for chained multi-node MCP federation and git subtree sync."""

    def test_e2e_chained_hub_mcp_to_downstream_service_node_mcp(self, tmp_path: Path) -> None:
        """Verify chained stdio MCP discovery and invocation from Hub MCP to Service Node MCP."""
        # Arrange
        hub_dir = tmp_path / "corp_hub"
        node_dir = tmp_path / "svc_checkout_node"
        hub_logs = tmp_path / "hub_logs"
        node_logs = tmp_path / "node_logs"

        _create_node_fixture(
            hub_dir,
            layer_id="acme-corp-hub",
            layer_role="corporate",
            packages=["curl", "git", "python3", "stow"],
            manifest_extra={
                "baseline_guardrails": ["corp-zero-secret-policy"],
                "environments": {
                    "pre": {
                        "access_mode": "strictly-read-only",
                        "requirements_file": "requirements-pre.txt",
                        "default_guardrails": ["pre-env-read-only-guard"],
                    }
                },
                "federated_mcps": [],
            },
        )
        dept_sub = hub_dir / "layers" / "dept-security"
        _create_node_fixture(
            dept_sub,
            layer_id="acme-dept-security",
            layer_role="department",
            packages=["curl", "git"],
            manifest_extra={
                "baseline_guardrails": ["dept-pci-dss-audit"],
                "federated_mcps": [
                    {
                        "mcp_id": "svc-checkout-node-mcp",
                        "role": "service-node",
                        "layer": "service-node",
                        "environments": ["pre", "pro"],
                        "description": "Checkout container node MCP endpoint",
                        "target_node_path": str(node_dir),
                        "required_guardrails": ["checkout-db-no-ddl"],
                    }
                ],
            },
        )
        (dept_sub / "docs" / "pci.md").write_text(
            "# Security Policy\n## PCI-DSS Webhook Rule\nVerify HMAC-SHA256 signatures.\n",
            encoding="utf-8",
        )

        _create_node_fixture(
            node_dir,
            layer_id="acme-svc-checkout-node",
            layer_role="service-node",
            packages=["curl", "git", "libpq5", "python3"],
            manifest_extra={"baseline_guardrails": ["node-local-guard"]},
        )

        hub_requests: list[dict[str, object]] = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "prompts/get",
                "params": {
                    "name": "orchestrate-federated-mcps",
                    "arguments": {"workflow_goal": "Audit pre-production checkout container"},
                },
            },
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "discover_federated_mcps",
                    "arguments": {"layer": "all", "environment": "pre"},
                },
            },
            {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call",
                "params": {
                    "name": "query_governance_rules",
                    "arguments": {"query": "PCI-DSS", "layer": "all"},
                },
            },
            {
                "jsonrpc": "2.0",
                "id": 5,
                "method": "resources/read",
                "params": {"uri": "dotfiles://mcp/diagnostics"},
            },
        ]

        # Act
        hub_responses = _run_mcp_stdio_batch(hub_dir, hub_logs, hub_requests)
        discovered_payload = json.loads(hub_responses[2]["result"]["content"][0]["text"])  # type: ignore[index]
        discovered_mcp = discovered_payload["federated_mcps"][0]
        chained_node_path = Path(discovered_mcp["target_node_path"])

        node_requests: list[dict[str, object]] = [
            {"jsonrpc": "2.0", "id": 10, "method": "initialize", "params": {}},
            {
                "jsonrpc": "2.0",
                "id": 11,
                "method": "tools/call",
                "params": {"name": "get_layer_overview", "arguments": {}},
            },
            {
                "jsonrpc": "2.0",
                "id": 12,
                "method": "resources/read",
                "params": {"uri": "dotfiles://system/manifests"},
            },
            {
                "jsonrpc": "2.0",
                "id": 13,
                "method": "tools/call",
                "params": {
                    "name": "read_layer_document",
                    "arguments": {"relative_path": "docs/README.md"},
                },
            },
            {
                "jsonrpc": "2.0",
                "id": 14,
                "method": "resources/read",
                "params": {"uri": "dotfiles://mcp/diagnostics"},
            },
        ]
        node_responses = _run_mcp_stdio_batch(chained_node_path, node_logs, node_requests)

        # Assert
        assert discovered_mcp["mcp_id"] == "svc-checkout-node-mcp"
        assert discovered_mcp["activation_policy"] == "on-demand"
        assert discovered_mcp["effective_guardrails"] == [
            "corp-zero-secret-policy",
            "dept-pci-dss-audit",
            "pre-env-read-only-guard",
            "checkout-db-no-ddl",
        ]
        rules_payload = json.loads(hub_responses[3]["result"]["content"][0]["text"])  # type: ignore[index]
        assert rules_payload["match_count"] == 1
        assert "HMAC-SHA256" in rules_payload["matches"][0]["excerpt"]
        node_overview = json.loads(node_responses[1]["result"]["content"][0]["text"])  # type: ignore[index]
        assert (
            node_overview["channel_1_node_and_system_state"]["layer_id"] == "acme-svc-checkout-node"
        )
        node_manifests = json.loads(node_responses[2]["result"]["contents"][0]["text"])  # type: ignore[index]
        assert "libpq5" in node_manifests["apt_manual_packages"]
        hub_diag = json.loads(hub_responses[4]["result"]["contents"][0]["text"])  # type: ignore[index]
        node_diag = json.loads(node_responses[4]["result"]["contents"][0]["text"])  # type: ignore[index]
        assert hub_diag["events_summary"] == {
            **hub_diag["events_summary"],
            "total_events": 4,
            "error_events": 0,
        }
        assert node_diag["events_summary"] == {
            **node_diag["events_summary"],
            "total_events": 4,
            "error_events": 0,
        }

    def test_e2e_git_subtree_add_and_pull_all_with_live_mcp_discovery(self, tmp_path: Path) -> None:
        """Verify git subtree add and pull-all across local repositories with live MCP discovery."""
        # Arrange
        dept_repo = tmp_path / "dept_security_repo"
        team_repo = tmp_path / "team_backend_repo"
        dept_repo.mkdir()
        team_repo.mkdir()
        git_env = {
            **os.environ,
            "GIT_AUTHOR_NAME": "Test Bot",
            "GIT_AUTHOR_EMAIL": "bot@example.com",
            "GIT_COMMITTER_NAME": "Test Bot",
            "GIT_COMMITTER_EMAIL": "bot@example.com",
        }
        subprocess.run(["git", "init", "-b", "master"], cwd=dept_repo, env=git_env, check=True)
        _create_node_fixture(
            dept_repo,
            "acme-dept-security",
            "department",
            ["curl"],
            {
                "upstream_layer": {
                    "layer_id": "acme-dept-security",
                    "repository": str(dept_repo),
                    "branch": "master",
                },
                "federated_mcps": [{"mcp_id": "vault-mcp", "role": "security"}],
            },
        )
        subprocess.run(["git", "add", "-A"], cwd=dept_repo, env=git_env, check=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=dept_repo, env=git_env, check=True)
        subprocess.run(["git", "init", "-b", "master"], cwd=team_repo, env=git_env, check=True)
        _create_node_fixture(team_repo, "acme-team-backend", "team", ["git", "python3"], {})
        subprocess.run(["git", "add", "-A"], cwd=team_repo, env=git_env, check=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=team_repo, env=git_env, check=True)
        subtree_env = {**git_env, "DOTFILES_REPO_DIR": str(team_repo)}

        # Act
        add_proc = subprocess.run(
            [str(SUBTREE_SCRIPT), "add", "dept-security", str(dept_repo), "master"],
            cwd=team_repo,
            env=subtree_env,
            capture_output=True,
            text=True,
            check=True,
        )
        (dept_repo / "docs" / "zero_trust.md").write_text(
            "# Zero Trust\n## mTLS Mandate\nAll service-to-service traffic must use mTLS.\n",
            encoding="utf-8",
        )
        subprocess.run(["git", "add", "-A"], cwd=dept_repo, env=git_env, check=True)
        subprocess.run(["git", "commit", "-m", "mTLS"], cwd=dept_repo, env=git_env, check=True)
        pull_all_proc = subprocess.run(
            [str(SUBTREE_SCRIPT), "pull-all"],
            cwd=team_repo,
            env=subtree_env,
            capture_output=True,
            text=True,
            check=True,
        )
        mcp_server = DotfilesMCPServer(repo_dir=team_repo, log_dir=tmp_path / "team_logs")
        rule_search = json.loads(
            mcp_server.call_tool(
                "query_governance_rules", {"query": "mTLS", "layer": "dept-security"}
            )["content"][0]["text"]
        )
        mcp_discovery = json.loads(
            mcp_server.call_tool("discover_federated_mcps", {"layer": "all"})["content"][0]["text"]
        )

        # Assert
        assert add_proc.returncode == 0
        assert pull_all_proc.returncode == 0
        assert rule_search["match_count"] == 1
        assert "service-to-service traffic must use mTLS" in rule_search["matches"][0]["excerpt"]
        assert mcp_discovery["federated_mcp_count"] == 1
        assert mcp_discovery["federated_mcps"][0]["mcp_id"] == "vault-mcp"

    def test_e2e_full_fork_lifecycle_downward_projection_mcp_and_upward_promotion(
        self,
        tmp_path: Path,
    ) -> None:
        """Verify end-to-end fork setup, MCP surface projection, static apply, and promotion."""
        # Arrange
        fork_dir, proj_dir = tmp_path / "fork_repo", tmp_path / "consumer_project"
        _create_node_fixture(
            fork_dir,
            "acme-eu-fork",
            "domain-policy",
            ["git", "python3"],
            {"default_stack_templates": ["fastapi-hexagonal"]},
        )
        _create_node_fixture(
            fork_dir / "layers" / "dept-security",
            "acme-dept-security",
            "department",
            ["curl"],
            {"precedence": 20, "surface_bindings": []},
        )

        # Act
        configure_fork_manifest(
            fork_dir,
            layer_id="acme-eu-fork",
            layer_role="domain-policy",
            precedence=5,
            prune_default_templates=True,
        )
        scaffold_template_pack(
            fork_dir,
            template_name="gdpr-eu",
            kind="domain-policy-pack",
            register_binding=False,
            scopes=["checkout"],
        )
        mcp_srv = DotfilesMCPServer(repo_dir=fork_dir, log_dir=tmp_path / "fork_logs")
        surf_resp = json.loads(
            mcp_srv.call_tool(
                "resolve_surface_governance", {"target_path": "src/checkout/service.py"}
            )["content"][0]["text"]
        )
        apply_res = apply_fork_to_project(fork_dir, proj_dir, template_ref="gdpr-eu")
        (proj_dir / ".agents/assets/gdpr-eu/canonical_snippet.md").write_text(
            "<!-- Updated GDPR snippet -->\n", encoding="utf-8"
        )
        (proj_dir / ".agents/rules/layer-20-dept-security.md").write_text(
            "# Dept Security Updated\n## Zero Trust\nEnforce mTLS.\n", encoding="utf-8"
        )
        (proj_dir / ".agents/rules/security-audit.md").write_text("# Audit\n", encoding="utf-8")
        cmp_resp = json.loads(
            mcp_srv.call_tool(
                "compare_layer_patterns",
                {
                    "layer": "all",
                    "project_rules": [
                        "policy.md",
                        "layer-20-dept-security.md",
                        "security-audit.md",
                    ],
                    "project_skills": ["gdpr-eu-guide"],
                },
            )["content"][0]["text"]
        )
        diff_before = diff_project_against_layers(fork_dir, proj_dir)
        promote_project_asset_to_layer(
            fork_dir,
            proj_dir,
            source_rel_path=".agents/assets/gdpr-eu/canonical_snippet.md",
            target_layer="root",
        )
        promote_project_asset_to_layer(
            fork_dir,
            proj_dir,
            source_rel_path=".agents/rules/layer-20-dept-security.md",
            target_layer="dept-security",
        )
        promote_project_asset_to_layer(
            fork_dir,
            proj_dir,
            source_rel_path=".agents/rules/security-audit.md",
            target_layer="root",
            target_template="gdpr-eu",
        )
        diff_after = diff_project_against_layers(fork_dir, proj_dir)

        # Assert
        assert surf_resp["resolved_bindings"][0]["binding_id"] == "gdpr-eu-surface-binding"
        assert apply_res["applied_template"] == "gdpr-eu"
        lineage_md = (proj_dir / ".agents/LAYER_LINEAGE.md").read_text(encoding="utf-8")
        assert "| `5` | `root` | `acme-eu-fork` | `domain-policy` | `1` |" in lineage_md
        assert cmp_resp["materialized_layer_rules"] == ["layer-20-dept-security.md"]
        assert cmp_resp["promotion_routing"][0]["target_layer"] == "dept-security"
        assert len(diff_before["modified_in_project"]) == 2
        assert diff_before["novel_in_project"] == ["rules/security-audit.md"]
        assert diff_after["modified_in_project"] == []
        assert diff_after["novel_in_project"] == []
