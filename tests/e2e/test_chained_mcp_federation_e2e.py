"""End-to-end tests for chained multi-node MCP federation and git subtree orchestration."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from dotfiles_mcp_server import DotfilesMCPServer

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
        "schema_version": "1.1",
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
        "import dotfiles_mcp_server as m; "
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


def test_e2e_chained_hub_mcp_to_downstream_service_node_mcp(tmp_path: Path) -> None:
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
    assert node_overview["channel_1_node_and_system_state"]["layer_id"] == "acme-svc-checkout-node"
    node_manifests = json.loads(node_responses[2]["result"]["contents"][0]["text"])  # type: ignore[index]
    assert "libpq5" in node_manifests["apt_manual_packages"]
    hub_diag = json.loads(hub_responses[4]["result"]["contents"][0]["text"])  # type: ignore[index]
    node_diag = json.loads(node_responses[4]["result"]["contents"][0]["text"])  # type: ignore[index]
    assert hub_diag["events_summary"]["total_events"] == 4
    assert hub_diag["events_summary"]["error_events"] == 0
    assert node_diag["events_summary"]["total_events"] == 4
    assert node_diag["events_summary"]["error_events"] == 0


def test_e2e_git_subtree_add_and_pull_all_with_live_mcp_discovery(
    tmp_path: Path,
) -> None:
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
        layer_id="acme-dept-security",
        layer_role="department",
        packages=["curl"],
        manifest_extra={
            "upstream_layer": {
                "layer_id": "acme-dept-security",
                "repository": str(dept_repo),
                "branch": "master",
            },
            "federated_mcps": [{"mcp_id": "vault-mcp", "role": "security"}],
        },
    )
    subprocess.run(["git", "add", "-A"], cwd=dept_repo, env=git_env, check=True)
    subprocess.run(
        ["git", "commit", "-m", "chore: initial dept security layer"],
        cwd=dept_repo,
        env=git_env,
        check=True,
    )

    subprocess.run(["git", "init", "-b", "master"], cwd=team_repo, env=git_env, check=True)
    _create_node_fixture(
        team_repo,
        layer_id="acme-team-backend",
        layer_role="team",
        packages=["git", "python3"],
        manifest_extra={},
    )
    subprocess.run(["git", "add", "-A"], cwd=team_repo, env=git_env, check=True)
    subprocess.run(
        ["git", "commit", "-m", "chore: initial team backend layer"],
        cwd=team_repo,
        env=git_env,
        check=True,
    )

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
    subprocess.run(
        ["git", "commit", "-m", "feat: add mTLS mandate"],
        cwd=dept_repo,
        env=git_env,
        check=True,
    )
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
            "query_governance_rules",
            {"query": "mTLS", "layer": "dept-security"},
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


def test_e2e_resonant_chained_compaction_across_subtrees_and_agent_tiers(
    tmp_path: Path,
) -> None:
    # Arrange
    hub_dir = tmp_path / "resonant_hub"
    hub_logs = tmp_path / "resonant_logs"
    _create_node_fixture(
        hub_dir,
        layer_id="acme-corp-hub",
        layer_role="corporate",
        packages=["curl", "git", "python3"],
        manifest_extra={
            "baseline_guardrails": ["corp-baseline-guard"],
            "environments": {
                "pre": {
                    "access_mode": "strictly-read-only",
                    "default_guardrails": ["pre-read-only-guard"],
                }
            },
        },
    )
    dept_sub = hub_dir / "layers" / "dept-security"
    _create_node_fixture(
        dept_sub,
        layer_id="acme-dept-security",
        layer_role="department",
        packages=["curl"],
        manifest_extra={"baseline_guardrails": ["dept-zero-trust-guard"]},
    )
    (dept_sub / "docs" / "crypto_policy.md").write_text(
        "# Crypto Policy\n"
        "## Webhook HMAC Verification\n"
        '> *"Verify every webhook signature before parsing payload"*\n'
        "**Mandate:** Enforce **HMAC-SHA256** using "
        "`antigravity/.gemini/config/skills/sopen/SKILL.md`.\n"
        "- Step 1: Extract signature header\n"
        "- Step 2: Compute digest\n"
        "| Header | Algorithm |\n"
        "|---|---|\n"
        "| X-Sig | SHA256 |\n",
        encoding="utf-8",
    )

    # Act
    step1_resp = _run_mcp_stdio_batch(
        hub_dir,
        hub_logs,
        [
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "query_governance_rules",
                    "arguments": {
                        "query": "Webhook",
                        "layer": "all",
                        "resolution": "L0",
                        "environment": "pre",
                        "resonance_key": "mesh-key-42",
                    },
                },
            }
        ],
    )
    q_l0_payload = json.loads(step1_resp[0]["result"]["content"][0]["text"])  # type: ignore[index]
    l0_capsule = q_l0_payload["matches"][0]["capsule_token"]

    step2_resp = _run_mcp_stdio_batch(
        hub_dir,
        hub_logs,
        [
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "unfold_context_capsule",
                    "arguments": {
                        "capsule_token": l0_capsule,
                        "target_level": "L1",
                        "agent_tier": "flash",
                        "environment": "pre",
                        "resonance_key": "mesh-key-42",
                    },
                },
            },
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "unfold_context_capsule",
                    "arguments": {
                        "capsule_token": l0_capsule,
                        "target_level": "L2",
                        "agent_tier": "flash",
                        "environment": "pre",
                        "resonance_key": "mesh-key-42",
                    },
                },
            },
        ],
    )
    l1_unfolded = json.loads(step2_resp[0]["result"]["content"][0]["text"])  # type: ignore[index]
    flash_blocked = step2_resp[1]
    l1_capsule = l1_unfolded["next_capsule_token"]

    step3_resp = _run_mcp_stdio_batch(
        hub_dir,
        hub_logs,
        [
            {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call",
                "params": {
                    "name": "unfold_context_capsule",
                    "arguments": {
                        "capsule_token": l1_capsule,
                        "target_level": "L3",
                        "agent_tier": "pro",
                        "environment": "pre",
                        "resonance_key": "mesh-key-42",
                    },
                },
            }
        ],
    )
    l3_unfolded = json.loads(step3_resp[0]["result"]["content"][0]["text"])  # type: ignore[index]

    # Assert
    assert q_l0_payload["resolution"] == "L0"
    assert q_l0_payload["matches"][0]["layer"] == "dept-security"
    assert l1_unfolded["unfolded_level"] == "L1"
    assert "Verify every webhook signature" in l1_unfolded["content"]["axiom_skeleton"]
    assert "error" in flash_blocked
    assert l3_unfolded["unfolded_level"] == "L3"
    assert l3_unfolded["unfold_chain"] == ["L1->L2", "L2->L3"]
    assert len(l3_unfolded["content"]["linked_l3_documents"]) == 1
    assert l3_unfolded["content"]["effective_guardrails"] == [
        "corp-baseline-guard",
        "dept-zero-trust-guard",
        "pre-read-only-guard",
    ]
