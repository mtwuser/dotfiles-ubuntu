"""End-to-end tests for downward fork projection and upward promotion via CLI and MCP."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest
from dotfiles_mcp.promotion_engine import (
    diff_project_against_layers,
    promote_project_asset_to_layer,
)
from dotfiles_mcp.server import DotfilesMCPServer

REPO_DIR = Path(__file__).resolve().parents[2]
LAYER_CONFIG_SCRIPT = REPO_DIR / "scripts" / "layer-config.sh"
BOOTSTRAP_SCRIPT = REPO_DIR / "bootstrap.sh"
AUDIT_GLOBAL_SCRIPT = REPO_DIR / "scripts" / "audit-global-config.sh"


def _create_node_fixture(
    base_dir: Path,
    layer_id: str,
    layer_role: str,
    manifest_extra: dict[str, object],
) -> None:
    """Create a minimal dotfiles-ubuntu layer directory structure for CLI and MCP E2E tests."""
    base_dir.mkdir(parents=True, exist_ok=True)
    (base_dir / "VERSION").write_text("1.8.0\n", encoding="utf-8")
    (base_dir / "system").mkdir(parents=True, exist_ok=True)
    for fname in (
        "packages-manual.txt",
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
        f"# {layer_id} Rules\n\n## Core Security Mandate\n\nAlways validate inputs.\n",
        encoding="utf-8",
    )
    (agents_dir / "hooks.json").write_text('{"hooks": {}}\n', encoding="utf-8")
    (agents_dir / "skills" / "sopen" / "SKILL.md").write_text(
        "---\nname: sopen\ndescription: open session\n---\n", encoding="utf-8"
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
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )


def _run_layer_config(fork_dir: Path, *args: str) -> dict[str, object]:
    """Execute scripts/layer-config.sh against fork_dir and parse its JSON stdout."""
    env = {
        **os.environ,
        "DOTFILES_REPO_DIR": str(fork_dir),
    }
    proc = subprocess.run(
        [str(LAYER_CONFIG_SCRIPT), *args],
        cwd=fork_dir,
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
        check=True,
    )
    return json.loads(proc.stdout)  # type: ignore[no-any-return]


def test_e2e_cli_and_mcp_downward_projection_to_upward_promotion_cycle(
    tmp_path: Path,
) -> None:
    """Validate init-fork -> scaffold -> apply -> compare -> diff -> promote -> in_sync."""
    # Arrange
    fork_dir = tmp_path / "fintech_fork"
    proj_dir = tmp_path / "checkout_app"
    _create_node_fixture(
        fork_dir,
        layer_id="acme-fintech-fork",
        layer_role="domain-policy",
        manifest_extra={"default_stack_templates": ["fastapi-hexagonal"]},
    )
    _create_node_fixture(
        fork_dir / "layers" / "dept-security",
        layer_id="acme-dept-security",
        layer_role="department",
        manifest_extra={"precedence": 20, "surface_bindings": []},
    )

    # Act — Step 1: Parameterize fork and scaffold template pack with surface binding via CLI
    init_res = _run_layer_config(
        fork_dir,
        "init-fork",
        "--id",
        "acme-fintech-fork",
        "--role",
        "domain-policy",
        "--precedence",
        "15",
        "--prune-default-templates",
    )
    scaffold_res = _run_layer_config(
        fork_dir,
        "scaffold-template",
        "pci-compliance",
        "--kind",
        "domain-policy-pack",
        "--register-binding",
    )
    apply_res = _run_layer_config(
        fork_dir,
        "apply-project",
        str(proj_dir),
        "--template",
        "pci-compliance",
        "--layers",
        "all",
    )

    # Act — Step 2: Modify materialized rules and create novel rule & skill in consumer project
    (proj_dir / ".agents" / "rules" / "policy.md").write_text(
        "# PCI Compliance Rules (Updated in Project)\n\n"
        "## Core Mandate\n\n"
        '> *"Tokenize PAN before logging"* \n',
        encoding="utf-8",
    )
    (proj_dir / ".agents" / "rules" / "layer-20-dept-security.md").write_text(
        "# acme-dept-security Rules\n\n## Core Security Mandate\n\nEnforce mTLS + HMAC.\n",
        encoding="utf-8",
    )
    (proj_dir / ".agents" / "rules" / "security-webhook.md").write_text(
        "# Security Webhook Policy\n\n## Signature Gate\n\nVerify X-Signature header.\n",
        encoding="utf-8",
    )
    novel_skill_dir = proj_dir / ".agents" / "skills" / "pci-audit-flow"
    novel_skill_dir.mkdir(parents=True, exist_ok=True)
    (novel_skill_dir / "SKILL.md").write_text(
        "---\n"
        "name: pci-audit-flow\n"
        'description: "Audit PCI-DSS tokenization flows across services."\n'
        "---\n\n"
        "# PCI Audit Flow\n\n"
        "1. Verify PAN masking.\n",
        encoding="utf-8",
    )

    # Act — Step 3: Compare patterns via MCP and diff/promote back to layers via CLI
    mcp_srv = DotfilesMCPServer(repo_dir=fork_dir, log_dir=tmp_path / "mcp_logs")
    cmp_resp = json.loads(
        mcp_srv.call_tool(
            "compare_layer_patterns",
            {
                "layer": "all",
                "project_rules": [
                    "policy.md",
                    "layer-20-dept-security.md",
                    "security-webhook.md",
                ],
                "project_skills": ["pci-compliance-guide", "pci-audit-flow"],
            },
        )["content"][0]["text"]
    )
    diff_before = _run_layer_config(fork_dir, "diff-project", str(proj_dir))
    prom_policy = _run_layer_config(
        fork_dir,
        "promote-from-project",
        str(proj_dir),
        "--source",
        ".agents/rules/policy.md",
        "--to-layer",
        "root",
        "--to-template",
        "pci-compliance",
    )
    prom_dept = _run_layer_config(
        fork_dir,
        "promote-from-project",
        str(proj_dir),
        "--source",
        ".agents/rules/layer-20-dept-security.md",
        "--to-layer",
        "dept-security",
    )
    prom_webhook = _run_layer_config(
        fork_dir,
        "promote-from-project",
        str(proj_dir),
        "--source",
        ".agents/rules/security-webhook.md",
        "--to-layer",
        "root",
        "--to-template",
        "pci-compliance",
    )
    prom_skill = _run_layer_config(
        fork_dir,
        "promote-from-project",
        str(proj_dir),
        "--source",
        ".agents/skills/pci-audit-flow/SKILL.md",
        "--to-layer",
        "root",
        "--to-template",
        "pci-compliance",
    )
    diff_after = _run_layer_config(fork_dir, "diff-project", str(proj_dir))

    # Assert
    assert init_res["manifest"]["precedence"] == 15  # type: ignore[index]
    assert scaffold_res["binding_registered"] is True
    assert apply_res["applied_template"] == "pci-compliance"
    assert apply_res["participating_layers"] == ["root", "dept-security"]
    assert cmp_resp["materialized_layer_rules"] == ["layer-20-dept-security.md"]
    assert cmp_resp["candidates_for_upward_promotion"] == {
        "novel_rules": ["security-webhook.md"],
        "novel_skills": ["pci-audit-flow"],
    }
    routing_by_item = {r["item"]: r for r in cmp_resp["promotion_routing"]}
    assert routing_by_item["security-webhook.md"]["target_layer"] == "dept-security"
    assert routing_by_item["pci-audit-flow"]["target_layer"] == "root"
    assert [m["file"] for m in diff_before["modified_in_project"]] == [  # type: ignore[attr-defined]
        "rules/layer-20-dept-security.md",
        "rules/policy.md",
    ]
    assert diff_before["novel_in_project"] == [
        "rules/security-webhook.md",
        "skills/pci-audit-flow/SKILL.md",
    ]
    assert prom_policy["destination"] == "templates/pci-compliance/rules/policy.md"
    assert prom_dept["destination"] == "layers/dept-security/antigravity/.gemini/config/AGENTS.md"
    assert prom_webhook["destination"] == "templates/pci-compliance/rules/security-webhook.md"
    assert prom_skill["destination"] == "templates/pci-compliance/skills/pci-audit-flow/SKILL.md"
    assert diff_after["modified_in_project"] == []
    assert diff_after["novel_in_project"] == []
    assert len(diff_after["in_sync"]) == 7  # type: ignore[arg-type]


def test_e2e_gnu_stow_bootstrap_antigravity_and_audit_global_config(
    tmp_path: Path,
) -> None:
    """Validate bootstrap.sh --antigravity tree unfolding, backups, and audit-global-config.sh."""
    # Arrange
    fake_home = tmp_path / "fake_home"
    cfg_dir = fake_home / ".gemini" / "config"
    (cfg_dir / "scripts").mkdir(parents=True, exist_ok=True)
    (cfg_dir / "AGENTS.md").write_text("# Old Local AGENTS\n", encoding="utf-8")
    (cfg_dir / "scripts" / "legacy.py").write_text("# old\n", encoding="utf-8")
    env = {**os.environ, "HOME": str(fake_home)}

    # Act
    boot_proc = subprocess.run(
        [str(BOOTSTRAP_SCRIPT), "--antigravity"],
        cwd=REPO_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
        check=True,
    )
    audit_ok = subprocess.run(
        [str(AUDIT_GLOBAL_SCRIPT)],
        cwd=REPO_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    (cfg_dir / "untracked_orphan.md").write_text("# Orphan\n", encoding="utf-8")
    (cfg_dir / "dangling_link.md").symlink_to(tmp_path / "nonexistent_target.md")
    audit_drift = subprocess.run(
        [str(AUDIT_GLOBAL_SCRIPT)],
        cwd=REPO_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )

    # Assert
    assert boot_proc.returncode == 0
    assert (cfg_dir / "AGENTS.md").is_symlink()
    assert not (cfg_dir / "skills").is_symlink()
    assert (cfg_dir / "skills" / "sopen").is_symlink()
    assert len(list(cfg_dir.glob("AGENTS.md.backup.*"))) == 1
    assert len(list(cfg_dir.glob("scripts.backup.*"))) == 1
    assert audit_ok.returncode == 0
    assert "All global config is properly persisted" in audit_ok.stdout
    assert audit_drift.returncode == 1
    assert "ORPHAN: untracked_orphan.md" in audit_drift.stdout
    assert "BROKEN: dangling_link.md" in audit_drift.stdout


def test_e2e_ro_template_apply_idempotency_and_promotion_symlink_containment(
    tmp_path: Path,
) -> None:
    """Verify idempotent apply-project from 0o444 templates and symlink escape guards."""
    # Arrange
    fork_dir = tmp_path / "ro_tpl_fork"
    _create_node_fixture(fork_dir, "acme-sec-fork", "department", {"precedence": 20})
    _run_layer_config(fork_dir, "scaffold-template", "pci-pack", "--kind", "domain-policy-pack")
    tpl_dir = fork_dir / "templates" / "pci-pack"
    (tpl_dir / "governance").mkdir(parents=True, exist_ok=True)
    (tpl_dir / "governance" / "SECURITY_POLICY.md").write_text("# Sec Policy\n", encoding="utf-8")
    for f in tpl_dir.rglob("*"):
        if f.is_file():
            f.chmod(0o444)
    proj_dir = tmp_path / "idempotent_proj"
    proj_dir.mkdir(parents=True, exist_ok=True)
    outside_secret = tmp_path / "outside_secret.md"
    outside_secret.write_text("# Secret\n", encoding="utf-8")
    (fork_dir / "scripts").mkdir(parents=True, exist_ok=True)
    verify_sh = fork_dir / "scripts" / "verify-repo.sh"
    verify_sh.write_text("#!/bin/sh\necho 'VERIFY_OK'\nexit 0\n", encoding="utf-8")
    verify_sh.chmod(0o755)
    audit_sh = fork_dir / "audit.sh"
    audit_sh.write_text("#!/bin/sh\necho 'DRIFT_FOUND'\nexit 1\n", encoding="utf-8")
    audit_sh.chmod(0o755)

    # Act
    drift_res = json.loads(
        DotfilesMCPServer(repo_dir=fork_dir, log_dir=None).call_tool(
            "audit_node_drift", {"mode": "both"}
        )["content"][0]["text"]
    )
    apply_first = _run_layer_config(
        fork_dir, "apply-project", str(proj_dir), "--template", "pci-pack"
    )
    apply_second = _run_layer_config(
        fork_dir, "apply-project", str(proj_dir), "--template", "pci-pack"
    )
    escape_link = proj_dir / ".agents" / "rules" / "escape.md"
    escape_link.symlink_to(outside_secret)
    with pytest.raises(ValueError, match="Outbound symlink escape denied in project_dir"):
        diff_project_against_layers(fork_dir, proj_dir)
    escape_link.unlink()

    (proj_dir / ".agents" / "rules" / "policy.md").chmod(0o444)
    prom_first = promote_project_asset_to_layer(
        fork_dir,
        proj_dir,
        source_rel_path=".agents/rules/policy.md",
        target_layer="root",
        target_template="pci-pack",
    )
    prom_second = promote_project_asset_to_layer(
        fork_dir,
        proj_dir,
        source_rel_path=".agents/rules/policy.md",
        target_layer="root",
        target_template="pci-pack",
    )
    with pytest.raises(ValueError, match="Invalid target_template"):
        promote_project_asset_to_layer(
            fork_dir,
            proj_dir,
            source_rel_path=".agents/rules/policy.md",
            target_layer="root",
            target_template="../../escape",
        )

    # Assert
    assert drift_res["healthy"] is False
    assert drift_res["checks"]["verify_repo"]["passed"] is True
    assert drift_res["checks"]["system_audit"]["output"] == "DRIFT_FOUND"
    assert apply_first["applied_template"] == "pci-pack"
    assert apply_second["applied_template"] == "pci-pack"
    assert (proj_dir / "SECURITY_POLICY.md").is_file()
    assert prom_first["destination"] == "templates/pci-pack/rules/policy.md"
    assert prom_second["destination"] == "templates/pci-pack/rules/policy.md"
