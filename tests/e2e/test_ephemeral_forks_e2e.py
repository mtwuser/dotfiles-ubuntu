"""End-to-end tests for Ephemeral Scoped Forks and Department Bots (MCP + CLI)."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import pytest
from dotfiles_mcp.capsule_engine import CapsuleError
from dotfiles_mcp.constants import MAX_ACTIVE_EPHEMERAL_FORKS
from dotfiles_mcp.server import DotfilesMCPServer

REPO_DIR = Path(__file__).resolve().parents[2]
MCP_ENTRYPOINT = REPO_DIR / "scripts" / "dotfiles_mcp_server.py"


def _set_tree_permissions(root: Path, dir_mode: int, file_mode: int) -> None:
    """Recursively set directory and file permissions on a path tree without following symlinks."""
    if dir_mode & 0o200:
        root.chmod(dir_mode)
    for p in sorted(root.rglob("*"), reverse=not bool(dir_mode & 0o200)):
        if p.is_dir(follow_symlinks=False):
            p.chmod(dir_mode)
        elif p.is_file(follow_symlinks=False):
            p.chmod(file_mode)
    if not (dir_mode & 0o200):
        root.chmod(dir_mode)


def _send_rpc(proc: subprocess.Popen[str], req_id: int, method: str, params: dict[str, Any]) -> Any:
    """Send a JSON-RPC 2.0 request to a live stdio MCP process and return the parsed response."""
    assert proc.stdin is not None and proc.stdout is not None
    proc.stdin.write(
        json.dumps({"jsonrpc": "2.0", "id": req_id, "method": method, "params": params}) + "\n"
    )
    proc.stdin.flush()
    return json.loads(proc.stdout.readline())


def _send_tool(
    proc: subprocess.Popen[str], req_id: int, name: str, **arguments: Any
) -> dict[str, Any]:
    """Send a tools/call JSON-RPC request to a live stdio MCP process."""
    return _send_rpc(proc, req_id, "tools/call", {"name": name, "arguments": arguments})  # type: ignore[no-any-return]


def _create_ro_container_fixture(ro_repo: Path) -> None:
    """Populate a minimal container repo fixture with scripts/ and a mounted dept-security layer."""
    for rel in (
        "antigravity/.gemini/config",
        "scripts",
        "system",
        "templates/fastapi-hexagonal/rules",
        "layers/dept-security/antigravity/.gemini/config",
        "layers/dept-security/system",
    ):
        (ro_repo / rel).mkdir(parents=True, exist_ok=True)
    shutil.copy2(MCP_ENTRYPOINT, ro_repo / "scripts" / "dotfiles_mcp_server.py")
    shutil.copytree(
        REPO_DIR / "scripts" / "dotfiles_mcp",
        ro_repo / "scripts" / "dotfiles_mcp",
        dirs_exist_ok=True,
    )
    (ro_repo / "VERSION").write_text("1.8.0\n", encoding="utf-8")
    (ro_repo / "antigravity/.gemini/config/AGENTS.md").write_text(
        '# RO Container Rules\n\n## Immutable Root\n\n> *"Never mutate container rootfs"*\n',
        encoding="utf-8",
    )
    (ro_repo / "templates/fastapi-hexagonal/rules/coding.md").write_text(
        '# Coding Rules\n\n## Hexagonal Ports\n\n> *"Ports must be Protocols"*\n',
        encoding="utf-8",
    )
    (ro_repo / "system/mcp-layer.json").write_text(
        json.dumps(
            {
                "schema_version": "1.2",
                "layer_id": "acme-ro-container-node",
                "layer_role": "service-node",
                "default_stack_templates": ["fastapi-hexagonal"],
                "baseline_guardrails": ["ro-container-guard"],
            }
        ),
        encoding="utf-8",
    )
    (ro_repo / "layers/dept-security/antigravity/.gemini/config/AGENTS.md").write_text(
        '# Dept Security\n\n## Zero Trust Gate\n\n> *"Enforce mTLS on every RPC"*\n',
        encoding="utf-8",
    )
    (ro_repo / "layers/dept-security/system/mcp-layer.json").write_text(
        json.dumps(
            {
                "schema_version": "1.2",
                "layer_id": "acme-dept-security",
                "layer_role": "department",
                "precedence": 15,
                "baseline_guardrails": ["dept-mtls-guard"],
            }
        ),
        encoding="utf-8",
    )


def test_e2e_surface_advisory_to_ephemeral_department_bot_and_capsule_unfold(
    tmp_path: Path,
) -> None:
    """Validate advisory detection -> ephemeral fork evaluation -> rcap1 capsule unfolding."""
    # Arrange
    eph_root = tmp_path / "ephemeral_forks"
    consumer_proj = tmp_path / "checkout_service_app"
    (consumer_proj / ".agents" / "rules").mkdir(parents=True)
    (consumer_proj / ".agents" / "rules" / "shop-domain.md").write_text(
        '# Shop Domain Rules\n\n## Cart Invariants\n\n> *"Never allow negative quantities"*\n\n'
        "- Cart totals must use Decimal.\n",
        encoding="utf-8",
    )
    server = DotfilesMCPServer(repo_dir=REPO_DIR, log_dir=tmp_path / "logs")

    # Act — Step 1: Resolve surface governance and receive Department Bot advisories
    surf_resp = server.call_tool(
        "resolve_surface_governance", {"target_path": "src/shop/service.py"}
    )
    advisories = json.loads(surf_resp["content"][0]["text"])["ephemeral_delegation_advisories"]

    # Act — Step 2: Run one-shot Department Bot evaluation with cross-project bridge
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
            "orchestrate_ephemeral_fork", {"action": "reap", "fork_id": fid}
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
        diag = json.loads(server.read_resource("dotfiles://mcp/diagnostics")["text"])
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
    assert "CAPSULE_RESONANCE_DENIED" in diag["alerts_summary"]["by_code"]


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


def test_e2e_read_only_container_mount_stdio_tmp_fallback_and_post_reap_denial(
    tmp_path: Path,
) -> None:
    """Simulate a chmod 555 :ro container mount with --no-log over stdio and /tmp fallback."""
    # Arrange
    ro_repo = tmp_path / "ro_container_repo"
    _create_ro_container_fixture(ro_repo)
    ext_ro_dir = tmp_path / "ext_ro_target"
    ext_ro_dir.mkdir(parents=True)
    ext_ro_dir.chmod(0o555)
    (ro_repo / "layers/dept-security/ext_link").symlink_to(ext_ro_dir)
    consumer_proj = tmp_path / "ro_consumer_app"
    (consumer_proj / ".agents" / "rules").mkdir(parents=True)
    (consumer_proj / ".agents" / "rules" / "ledger.md").write_text(
        '# Ledger Rules\n\n## Double Entry\n\n> *"Every debit requires a matching credit"*\n',
        encoding="utf-8",
    )
    tmp_eph_root = Path(tempfile.gettempdir()).resolve() / "dotfiles_ephemeral_forks"
    stdio_env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "PYTHONDONTWRITEBYTECODE": "1"}
    _set_tree_permissions(ro_repo, 0o555, 0o444)

    # Act
    proc = subprocess.Popen(
        [sys.executable, str(ro_repo / "scripts" / "dotfiles_mcp_server.py"), "--no-log"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=stdio_env,
    )
    spawned_ids: list[str] = []
    try:
        r_spawn = _send_tool(
            proc,
            1,
            "orchestrate_ephemeral_fork",
            action="spawn",
            bot_role="dept-ro-auditor",
            mount_layers=["dept-security"],
            mount_project_rules_from=str(consumer_proj),
        )
        spawn_data = json.loads(r_spawn["result"]["content"][0]["text"])
        fid_spawn = str(spawn_data["fork_id"])
        spawned_ids.append(fid_spawn)

        r_inspect = _send_tool(
            proc, 2, "orchestrate_ephemeral_fork", action="inspect", fork_id=fid_spawn
        )
        inspect_data = json.loads(r_inspect["result"]["content"][0]["text"])

        r_eval = _send_tool(
            proc,
            3,
            "orchestrate_ephemeral_fork",
            action="evaluate",
            bot_role="dept-ro-evaluator",
            target_path="src/ledger/service.py",
            mount_layers=["dept-security"],
            mount_project_rules_from=str(consumer_proj),
            one_shot=False,
        )
        eval_data = json.loads(r_eval["result"]["content"][0]["text"])
        spawned_ids.append(str(eval_data["fork_id"]))

        r_unfold_ok = _send_tool(
            proc,
            4,
            "unfold_context_capsule",
            capsule_token=eval_data["ephemeral_capsule"],
            target_level="L3",
            agent_tier="inherit",
            resonance_key=eval_data["session_resonance_key"],
        )
        unfolded_l3 = json.loads(r_unfold_ok["result"]["content"][0]["text"])

        (Path(spawn_data["fork_dir"]) / "antigravity").chmod(0o555)
        r_reap = _send_tool(proc, 5, "orchestrate_ephemeral_fork", action="reap", fork_id="all")
        reap_data = json.loads(r_reap["result"]["content"][0]["text"])

        r_unfold_denied = _send_tool(
            proc,
            6,
            "unfold_context_capsule",
            capsule_token=eval_data["ephemeral_capsule"],
            target_level="L2",
            agent_tier="inherit",
            resonance_key=eval_data["session_resonance_key"],
        )
        r_diag = _send_rpc(proc, 7, "resources/read", {"uri": "dotfiles://mcp/diagnostics"})
        diag_data = json.loads(r_diag["result"]["contents"][0]["text"])
    finally:
        if proc.stdin:
            proc.stdin.close()
        proc.wait(timeout=5)
        _set_tree_permissions(ro_repo, 0o755, 0o644)
        ext_ro_mode = ext_ro_dir.stat().st_mode & 0o777
        ext_ro_dir.chmod(0o755)
        for sid in spawned_ids:
            shutil.rmtree(tmp_eph_root / sid, ignore_errors=True)

    # Assert
    assert Path(spawn_data["fork_dir"]).parent == tmp_eph_root
    assert not Path(spawn_data["fork_dir"]).exists()
    assert ext_ro_mode == 0o555
    assert not (ro_repo / "logs").exists()
    assert inspect_data["active_count"] == 1
    assert eval_data["bridged_project_files"] == [".agents/rules/ledger.md"]
    assert [p["layer"] for p in eval_data["surface_projection"]["participating_layers"]] == [
        "dept-security",
        "root",
        "ephemeral-project-bridge",
    ]
    assert unfolded_l3["unfolded_level"] == "L3"
    assert set(spawned_ids).issubset(set(reap_data["reaped_forks"]))
    assert "Cross-node capsule mismatch" in r_unfold_denied["error"]["message"]
    assert diag_data["logging_enabled"] is False


def test_e2e_ephemeral_fork_capacity_limit_ttl_expiration_and_symlink_escape(
    tmp_path: Path,
) -> None:
    """Verify MAX_ACTIVE_EPHEMERAL_FORKS=16 limit, TTL expiry, and symlink escape blocking."""
    # Arrange
    eph_root = tmp_path / "ephemeral_limits"
    outside_secret = tmp_path / "outside_secret.md"
    outside_secret.write_text("# Top Secret\n", encoding="utf-8")
    escape_proj = tmp_path / "escape_project"
    (escape_proj / ".agents" / "rules").mkdir(parents=True)
    (escape_proj / ".agents" / "rules" / "escape.md").symlink_to(outside_secret)
    server = DotfilesMCPServer(repo_dir=REPO_DIR, log_dir=tmp_path / "limit_logs")

    # Act & Assert
    old_env = os.environ.get("DOTFILES_EPHEMERAL_ROOT")
    os.environ["DOTFILES_EPHEMERAL_ROOT"] = str(eph_root)
    try:
        with pytest.raises(
            ValueError, match="Outbound symlink escape denied in mount_project_rules_from"
        ):
            server.call_tool(
                "orchestrate_ephemeral_fork",
                {
                    "action": "spawn",
                    "bot_role": "dept-escape-bot",
                    "mount_project_rules_from": str(escape_proj),
                },
            )

        ttl_resp = server.call_tool(
            "orchestrate_ephemeral_fork",
            {"action": "spawn", "bot_role": "dept-ttl-bot", "ttl_seconds": 30},
        )
        ttl_fid = json.loads(ttl_resp["content"][0]["text"])["fork_id"]
        ttl_m_path = eph_root / ttl_fid / "system" / "mcp-layer.json"
        ttl_manifest = json.loads(ttl_m_path.read_text(encoding="utf-8"))
        ttl_manifest["ephemeral_metadata"]["expires_at_epoch"] = time.time() - 60.0
        ttl_m_path.write_text(json.dumps(ttl_manifest, indent=2), encoding="utf-8")
        server._ephemeral_memory_store[ttl_fid]["expires_at_epoch"] = time.time() - 60.0

        with pytest.raises(ValueError, match="EPHEMERAL_FORK_EXPIRED"):
            server.call_tool(
                "orchestrate_ephemeral_fork", {"action": "inspect", "fork_id": ttl_fid}
            )

        for idx in range(MAX_ACTIVE_EPHEMERAL_FORKS):
            server.call_tool(
                "orchestrate_ephemeral_fork",
                {"action": "spawn", "bot_role": f"dept-cap-bot-{idx}"},
            )
        with pytest.raises(ValueError, match="EPHEMERAL_FORK_LIMIT_REACHED"):
            server.call_tool(
                "orchestrate_ephemeral_fork",
                {"action": "spawn", "bot_role": "dept-cap-bot-overflow"},
            )
        reap_all = json.loads(
            server.call_tool("orchestrate_ephemeral_fork", {"action": "reap", "fork_id": "all"})[
                "content"
            ][0]["text"]
        )
    finally:
        if old_env is None:
            os.environ.pop("DOTFILES_EPHEMERAL_ROOT", None)
        else:
            os.environ["DOTFILES_EPHEMERAL_ROOT"] = old_env

    diag = json.loads(server.read_resource("dotfiles://mcp/diagnostics")["text"])
    assert "EPHEMERAL_FORK_EXPIRED" in diag["alerts_summary"]["by_code"]
    assert "EPHEMERAL_FORK_LIMIT_REACHED" in diag["alerts_summary"]["by_code"]
    assert len(reap_all["reaped_forks"]) == MAX_ACTIVE_EPHEMERAL_FORKS
