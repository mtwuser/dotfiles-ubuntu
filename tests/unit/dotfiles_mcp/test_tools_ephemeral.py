"""Unit tests for dotfiles_mcp/tools_ephemeral.py."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
from dotfiles_mcp.server import DotfilesMCPServer

if TYPE_CHECKING:
    from pathlib import Path


class TestMCPToolsEphemeral:
    """Verify orchestrate_ephemeral_fork across spawn, inspect, evaluate, and reap actions."""

    def test_orchestrate_ephemeral_fork_spawn_inspect_evaluate_and_reap(
        self, tmp_path: Path
    ) -> None:
        """Execute full spawn -> inspect -> evaluate (existing fork) -> reap lifecycle."""
        # Arrange
        repo = tmp_path / "repo"
        cfg = repo / "antigravity" / ".gemini" / "config"
        cfg.mkdir(parents=True)
        (cfg / "AGENTS.md").write_text(
            '# Global Rules\n\n## 1. Domain Purity\n\n> *"Keep domain pure"*\n\n- Zero I/O.\n',
            encoding="utf-8",
        )
        (repo / "system").mkdir()
        (repo / "system" / "mcp-layer.json").write_text(
            json.dumps(
                {
                    "schema_version": "1.2",
                    "layer_id": "acme-root",
                    "layer_role": "corporate",
                    "precedence": 10,
                    "default_stack_templates": ["fastapi-hexagonal"],
                    "baseline_guardrails": ["Baseline G1"],
                    "surface_bindings": [],
                    "environments": {},
                    "federated_mcps": [],
                }
            ),
            encoding="utf-8",
        )
        proj = tmp_path / "proj"
        (proj / ".agents" / "rules").mkdir(parents=True)
        (proj / ".agents" / "rules" / "custom.md").write_text(
            "## Custom Rule\n\nEnforce custom contract.\n", encoding="utf-8"
        )
        server = DotfilesMCPServer(repo_dir=repo, log_dir=repo / "logs")

        # Act
        spawn_resp = server.call_tool(
            "orchestrate_ephemeral_fork",
            {
                "action": "spawn",
                "bot_role": "dept-arch-bot",
                "target_globs": ["src/**"],
                "architectural_planes": ["domain"],
                "mount_templates": ["fastapi-hexagonal"],
                "mount_layers": [],
                "mount_project_rules_from": str(proj),
                "model_tier": "inherit",
                "access_mode": "strictly-read-only",
                "resolution": "L2",
                "ttl_seconds": 300,
            },
        )
        spawn_data = json.loads(spawn_resp["content"][0]["text"])
        fid = spawn_data["fork_id"]

        inspect_resp = server.call_tool(
            "orchestrate_ephemeral_fork", {"action": "inspect", "fork_id": fid}
        )
        eval_existing_resp = server.call_tool(
            "orchestrate_ephemeral_fork",
            {
                "action": "evaluate",
                "fork_id": fid,
                "target_path": "src/orders/service.py",
                "one_shot": False,
            },
        )
        eval_data = json.loads(eval_existing_resp["content"][0]["text"])
        fresh_server = DotfilesMCPServer(repo_dir=repo, log_dir=None)
        unfold_from_disk = fresh_server.call_tool(
            "unfold_context_capsule",
            {
                "capsule_token": eval_data["ephemeral_capsule"],
                "target_level": "L3",
                "agent_tier": "inherit",
                "resonance_key": eval_data["session_resonance_key"],
            },
        )
        other_server = DotfilesMCPServer(
            repo_dir=repo, layer_id_override="unrelated-node", log_dir=None
        )
        from dotfiles_mcp.capsule_engine import CapsuleError

        with pytest.raises(CapsuleError, match="Cross-node capsule mismatch"):
            other_server.call_tool(
                "unfold_context_capsule",
                {
                    "capsule_token": eval_data["ephemeral_capsule"],
                    "target_level": "L3",
                    "agent_tier": "inherit",
                    "resonance_key": eval_data["session_resonance_key"],
                },
            )
        reap_resp = server.call_tool(
            "orchestrate_ephemeral_fork", {"action": "reap", "fork_id": fid}
        )

        # Assert
        assert json.loads(inspect_resp["content"][0]["text"])["active_count"] == 1
        assert not unfold_from_disk["isError"]
        assert eval_data["auto_reaped"] is False
        assert eval_data["ephemeral_capsule"].startswith("rcap1.")
        assert eval_data["subagent_invocation_brief"]["subagent_type"] == "research"
        assert json.loads(reap_resp["content"][0]["text"])["reaped_forks"] == [fid]

    def test_orchestrate_ephemeral_fork_oneshot_evaluate_and_empty_sections(
        self, tmp_path: Path
    ) -> None:
        """Auto-reap one-shot evaluate forks and handle empty rule sections gracefully."""
        # Arrange
        repo = tmp_path / "repo"
        (repo / "system").mkdir(parents=True)
        (repo / "system" / "mcp-layer.json").write_text(
            json.dumps({"schema_version": "1.2", "layer_id": "empty-root"}), encoding="utf-8"
        )
        server = DotfilesMCPServer(repo_dir=repo, log_dir=repo / "logs")

        # Act
        eval_resp = server.call_tool(
            "orchestrate_ephemeral_fork",
            {
                "action": "evaluate",
                "bot_role": "dept-empty-bot",
                "target_path": "src/a.py",
                "one_shot": True,
            },
        )
        eval_data = json.loads(eval_resp["content"][0]["text"])

        # Assert
        assert eval_data["auto_reaped"] is True
        assert eval_data["ephemeral_capsule"] is None

    def test_orchestrate_ephemeral_fork_error_and_warning_branches(self, tmp_path: Path) -> None:
        """Emit EPHEMERAL_FORK_EXPIRED and EPHEMERAL_FORK_LIMIT_REACHED warnings on failure."""
        # Arrange
        repo = tmp_path / "repo"
        (repo / "system").mkdir(parents=True)
        (repo / "system" / "mcp-layer.json").write_text(
            json.dumps({"schema_version": "1.2", "layer_id": "err-root"}), encoding="utf-8"
        )
        eph_root = repo / "logs" / "ephemeral_forks"
        exp_dir = eph_root / "eph-expired-1" / "system"
        exp_dir.mkdir(parents=True)
        (exp_dir / "mcp-layer.json").write_text(
            json.dumps({"ephemeral_metadata": {"expires_at_epoch": 1.0}}), encoding="utf-8"
        )
        server = DotfilesMCPServer(repo_dir=repo, log_dir=repo / "logs")

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid action"):
            server.call_tool("orchestrate_ephemeral_fork", {"action": "invalid"})
        with pytest.raises(ValueError, match="Missing required 'fork_id'"):
            server.call_tool("orchestrate_ephemeral_fork", {"action": "reap"})
        with pytest.raises(ValueError, match="EPHEMERAL_FORK_EXPIRED"):
            server.call_tool(
                "orchestrate_ephemeral_fork", {"action": "inspect", "fork_id": "eph-expired-1"}
            )
        with pytest.raises(ValueError, match="not found"):
            server.call_tool(
                "orchestrate_ephemeral_fork", {"action": "inspect", "fork_id": "eph-missing"}
            )

        (exp_dir).mkdir(parents=True, exist_ok=True)
        (exp_dir / "mcp-layer.json").write_text(
            json.dumps({"ephemeral_metadata": {"expires_at_epoch": 1.0}}), encoding="utf-8"
        )
        with pytest.raises(ValueError, match="EPHEMERAL_FORK_EXPIRED"):
            server.call_tool(
                "orchestrate_ephemeral_fork", {"action": "evaluate", "fork_id": "eph-expired-1"}
            )

        for idx in range(16):
            fdir = eph_root / f"eph-cap-{idx}" / "system"
            fdir.mkdir(parents=True)
            (fdir / "mcp-layer.json").write_text(
                json.dumps({"ephemeral_metadata": {"expires_at_epoch": 9999999999.0}}),
                encoding="utf-8",
            )
        with pytest.raises(ValueError, match="EPHEMERAL_FORK_LIMIT_REACHED"):
            server.call_tool(
                "orchestrate_ephemeral_fork", {"action": "spawn", "bot_role": "overflow-bot"}
            )
        with pytest.raises(ValueError, match="Invalid bot_role"):
            server.call_tool(
                "orchestrate_ephemeral_fork", {"action": "spawn", "bot_role": "INVALID_BOT"}
            )

    def test_orchestrate_ephemeral_fork_read_only_filesystem_fallback(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Support full spawn, inspect, evaluate, unfold, and reap in read-only containers."""
        # Arrange
        import dotfiles_mcp.tools_ephemeral as te_mod
        from dotfiles_mcp.ephemeral_fork_engine import spawn_ephemeral_fork as orig_spawn

        repo = tmp_path / "repo"
        cfg = repo / "antigravity" / ".gemini" / "config"
        cfg.mkdir(parents=True)
        (cfg / "AGENTS.md").write_text(
            '# Global Rules\n\n## 1. Security\n\n> *"Stay secure"*\n\n- Zero leaks.\n',
            encoding="utf-8",
        )
        (repo / "layers" / "dept-sec" / "system").mkdir(parents=True)
        (repo / "layers" / "dept-sec" / "system" / "mcp-layer.json").write_text(
            json.dumps({"schema_version": "1.2", "layer_id": "dept-sec"}), encoding="utf-8"
        )
        (repo / "system").mkdir(parents=True)
        (repo / "system" / "mcp-layer.json").write_text(
            json.dumps({"schema_version": "1.2", "layer_id": "ro-root"}), encoding="utf-8"
        )

        def _spawn_ro(*args: object, **kwargs: object) -> dict[str, object]:
            if not kwargs.get("dry_run"):
                raise OSError(30, "Read-only file system")
            return orig_spawn(*args, **kwargs)  # type: ignore[arg-type]

        monkeypatch.setattr(te_mod, "spawn_ephemeral_fork", _spawn_ro)
        server = DotfilesMCPServer(repo_dir=repo, log_dir=None)

        # Act
        eval_resp = server.call_tool(
            "orchestrate_ephemeral_fork",
            {"action": "evaluate", "bot_role": "dept-ro-bot", "target_path": "src/a.py"},
        )
        eval_data = json.loads(eval_resp["content"][0]["text"])
        spawn_resp = server.call_tool(
            "orchestrate_ephemeral_fork",
            {
                "action": "spawn",
                "bot_role": "dept-ro-spawn",
                "mount_layers": ["dept-sec"],
            },
        )
        ro_fid = json.loads(spawn_resp["content"][0]["text"])["fork_id"]
        server.call_tool(
            "orchestrate_ephemeral_fork",
            {"action": "spawn", "bot_role": "dept-ro-second"},
        )
        insp_single = json.loads(
            server.call_tool(
                "orchestrate_ephemeral_fork", {"action": "inspect", "fork_id": ro_fid}
            )["content"][0]["text"]
        )
        insp_all = json.loads(
            server.call_tool("orchestrate_ephemeral_fork", {"action": "inspect"})["content"][0][
                "text"
            ]
        )
        eval_ro_existing = json.loads(
            server.call_tool(
                "orchestrate_ephemeral_fork",
                {
                    "action": "evaluate",
                    "fork_id": ro_fid,
                    "target_path": "src/a.py",
                    "one_shot": False,
                },
            )["content"][0]["text"]
        )
        reap_single = json.loads(
            server.call_tool("orchestrate_ephemeral_fork", {"action": "reap", "fork_id": ro_fid})[
                "content"
            ][0]["text"]
        )

        # Assert
        assert eval_data["auto_reaped"] is True
        assert eval_data["bot_role"] == "dept-ro-bot"
        assert insp_single["active_count"] == 1
        assert insp_all["active_count"] == 2
        assert eval_ro_existing["fork_id"] == ro_fid
        assert reap_single["reaped_forks"] == [ro_fid]
        with pytest.raises(FileNotFoundError, match="not found"):
            server.call_tool("orchestrate_ephemeral_fork", {"action": "reap", "fork_id": ro_fid})

        server._ephemeral_memory_store["eph-exp-mem"] = {
            "fork_id": "eph-exp-mem",
            "expires_at_epoch": 1.0,
            "active": True,
            "in_memory_only": True,
        }
        with pytest.raises(ValueError, match="EPHEMERAL_FORK_EXPIRED"):
            server.call_tool(
                "orchestrate_ephemeral_fork", {"action": "inspect", "fork_id": "eph-exp-mem"}
            )
        server._ephemeral_memory_store["eph-exp-mem2"] = {
            "fork_id": "eph-exp-mem2",
            "expires_at_epoch": 1.0,
            "active": True,
            "in_memory_only": True,
        }
        with pytest.raises(ValueError, match="EPHEMERAL_FORK_EXPIRED"):
            server.call_tool(
                "orchestrate_ephemeral_fork", {"action": "evaluate", "fork_id": "eph-exp-mem2"}
            )
        for idx in range(14):
            server._ephemeral_memory_store[f"eph-mem-{idx}"] = {
                "fork_id": f"eph-mem-{idx}",
                "expires_at_epoch": 9999999999.0,
                "active": True,
                "in_memory_only": True,
            }
        sixteenth_spawn = json.loads(
            server.call_tool(
                "orchestrate_ephemeral_fork", {"action": "spawn", "bot_role": "dept-ro-16th"}
            )["content"][0]["text"]
        )
        assert sixteenth_spawn["bot_role"] == "dept-ro-16th"
        with pytest.raises(ValueError, match="EPHEMERAL_FORK_LIMIT_REACHED"):
            server.call_tool(
                "orchestrate_ephemeral_fork", {"action": "spawn", "bot_role": "dept-ro-over"}
            )
        reap_all = json.loads(
            server.call_tool("orchestrate_ephemeral_fork", {"action": "reap", "fork_id": "all"})[
                "content"
            ][0]["text"]
        )
        assert len(reap_all["reaped_forks"]) == 16
