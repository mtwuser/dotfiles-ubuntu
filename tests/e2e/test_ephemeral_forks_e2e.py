"""End-to-end tests for Ephemeral Scoped Forks and Department Bots (MCP + CLI)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from dotfiles_mcp.server import DotfilesMCPServer

REPO_DIR = Path(__file__).resolve().parents[2]


def test_e2e_surface_advisory_to_ephemeral_department_bot_and_capsule_unfold(
    tmp_path: Path,
) -> None:
    """Validate advisory detection -> ephemeral fork evaluation -> rcap1 capsule unfolding."""
    # Arrange
    eph_root = tmp_path / "ephemeral_forks"
    consumer_proj = tmp_path / "osa_vertical_shop"
    (consumer_proj / ".agents" / "rules").mkdir(parents=True)
    (consumer_proj / ".agents" / "rules" / "shop-domain.md").write_text(
        '# Shop Domain Rules\n\n## Cart Invariants\n\n> *"Never allow negative quantities"*\n\n'
        "- Cart totals must use Decimal.\n",
        encoding="utf-8",
    )
    server = DotfilesMCPServer(repo_dir=REPO_DIR, log_dir=tmp_path / "logs")

    # Act — Step 1: Resolve surface governance and receive Department Bot advisories
    surf_resp = server.call_tool(
        "resolve_surface_governance",
        {"target_path": "src/shop/service.py"},
    )
    surf_data = json.loads(surf_resp["content"][0]["text"])
    advisories = surf_data["ephemeral_delegation_advisories"]

    # Act — Step 2: Run one-shot Department Bot evaluation with cross-project bridge
    import os

    import pytest
    from dotfiles_mcp.capsule_engine import CapsuleError

    old_env = os.environ.get("DOTFILES_EPHEMERAL_ROOT")
    os.environ["DOTFILES_EPHEMERAL_ROOT"] = str(eph_root)
    try:
        eval_resp = server.call_tool(
            "orchestrate_ephemeral_fork",
            {
                "action": "evaluate",
                "bot_role": advisories[0]["bot_role"],
                "target_path": "src/shop/service.py",
                "mount_templates": advisories[0]["mount_templates"],
                "mount_project_rules_from": str(consumer_proj),
                "model_tier": advisories[0]["model_tier"],
                "access_mode": advisories[0]["access_mode"],
                "resolution": "L2",
                "one_shot": True,
            },
        )
        eval_data = json.loads(eval_resp["content"][0]["text"])
        fid = eval_data["fork_id"]
        fork_dir = eph_root / fid
        bridge_cap = next(
            c["capsule_token"]
            for c in eval_data["ephemeral_capsules"]
            if c["layer"] == "ephemeral-project-bridge" and "Cart Invariants" in c["section"]
        )
        unfold_root_resp = server.call_tool(
            "unfold_context_capsule",
            {
                "capsule_token": eval_data["ephemeral_capsule"],
                "target_level": "L3",
                "agent_tier": "inherit",
                "resonance_key": eval_data["session_resonance_key"],
            },
        )
        unfold_bridge_resp = server.call_tool(
            "unfold_context_capsule",
            {
                "capsule_token": bridge_cap,
                "target_level": "L3",
                "agent_tier": "inherit",
                "resonance_key": eval_data["session_resonance_key"],
            },
        )
        reap_resp = server.call_tool(
            "orchestrate_ephemeral_fork",
            {"action": "reap", "fork_id": fid},
        )
        with pytest.raises(CapsuleError, match="Cross-node capsule mismatch"):
            server.call_tool(
                "unfold_context_capsule",
                {
                    "capsule_token": bridge_cap,
                    "target_level": "L2",
                    "agent_tier": "inherit",
                    "resonance_key": eval_data["session_resonance_key"],
                },
            )
    finally:
        if old_env is None:
            os.environ.pop("DOTFILES_EPHEMERAL_ROOT", None)
        else:
            os.environ["DOTFILES_EPHEMERAL_ROOT"] = old_env

    # Assert
    assert len(advisories) >= 1
    assert advisories[0]["bot_role"] == "dept-hexagonal-architect"
    assert eval_data["auto_reaped"] is True
    assert not fork_dir.exists()
    assert eval_data["bridged_project_files"] == [".agents/rules/shop-domain.md"]
    assert len(eval_data["subagent_invocation_brief"]["handback_channels"]) == 4
    assert not unfold_root_resp["isError"]
    assert not unfold_bridge_resp["isError"]
    bridge_unfolded = json.loads(unfold_bridge_resp["content"][0]["text"])
    assert "Cart totals must use Decimal." in bridge_unfolded["content"]["full_section"]
    assert json.loads(reap_resp["content"][0]["text"])["reaped_forks"] == [fid]


def test_e2e_cli_layer_config_ephemeral_subcommands(tmp_path: Path) -> None:
    """Verify layer-config.sh spawn-ephemeral, inspect-ephemeral, and reap-ephemeral CLI."""
    # Arrange
    script = str(REPO_DIR / "scripts" / "layer-config.sh")
    env = {
        "PATH": "/usr/bin:/bin",
        "DOTFILES_REPO_DIR": str(REPO_DIR),
        "DOTFILES_EPHEMERAL_ROOT": str(tmp_path / "cli_eph"),
    }

    # Act
    spawn_proc = subprocess.run(
        [
            script,
            "spawn-ephemeral",
            "--role",
            "dept-qa-bot",
            "--templates",
            "fastapi-hexagonal",
            "--globs",
            "tests/**",
            "--tier",
            "flash",
            "--ttl",
            "120",
        ],
        cwd=REPO_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    spawn_out = json.loads(spawn_proc.stdout)
    inspect_proc = subprocess.run(
        [script, "inspect-ephemeral", "--id", spawn_out["fork_id"]],
        cwd=REPO_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    reap_proc = subprocess.run(
        [script, "reap-ephemeral", "--id", "all"],
        cwd=REPO_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    # Assert
    assert spawn_proc.returncode == 0
    assert spawn_out["bot_role"] == "dept-qa-bot"
    assert inspect_proc.returncode == 0
    assert json.loads(inspect_proc.stdout)["active_count"] == 1
    assert reap_proc.returncode == 0
    assert spawn_out["fork_id"] in json.loads(reap_proc.stdout)["reaped_forks"]
