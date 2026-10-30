"""Unit tests for dotfiles_mcp/ephemeral_fork_engine.py."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from dotfiles_mcp.ephemeral_fork_engine import (
    _copy_zero_copy,
    build_subagent_invocation_brief,
    default_ephemeral_root,
    extract_ephemeral_advisories,
    inspect_ephemeral_forks,
    reap_ephemeral_fork,
    reap_expired_ephemeral_forks,
    spawn_ephemeral_fork,
)


class TestEphemeralForkEngine:
    """Verify ephemeral fork lifecycle, advisories, bridging, and TTL garbage collection."""

    def test_default_ephemeral_root_resolves_explicit_env_and_default(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Resolve ephemeral root from explicit path, DOTFILES_EPHEMERAL_ROOT, or logs/."""
        # Arrange
        explicit = tmp_path / "custom_eph"
        env_dir = tmp_path / "env_eph"

        # Act
        res_explicit = default_ephemeral_root(tmp_path, explicit)
        monkeypatch.setenv("DOTFILES_EPHEMERAL_ROOT", str(env_dir))
        res_env = default_ephemeral_root(tmp_path)
        monkeypatch.delenv("DOTFILES_EPHEMERAL_ROOT", raising=False)
        res_default = default_ephemeral_root(tmp_path)
        ro_repo = tmp_path / "ro_repo"
        ro_repo.mkdir()
        monkeypatch.setattr(
            os,
            "access",
            lambda p, _m: not str(p).startswith(str(ro_repo)),
        )
        res_tmp_fallback = default_ephemeral_root(ro_repo)
        monkeypatch.setattr(os, "access", lambda _p, _m: False)
        res_both_ro = default_ephemeral_root(ro_repo)

        # Assert
        assert res_explicit == explicit.resolve()
        assert res_env == env_dir.resolve()
        assert res_default == (tmp_path / "logs" / "ephemeral_forks").resolve()
        assert res_tmp_fallback.name == "dotfiles_ephemeral_forks"
        assert res_both_ro == (ro_repo / "logs" / "ephemeral_forks").resolve()

    def test_extract_ephemeral_advisories_deduplicates_and_skips_missing(self) -> None:
        """Extract unique Department Bot advisories from resolved surface bindings."""
        # Arrange
        bindings: list[dict[str, object]] = [
            {"binding_id": "no-policy", "layer": "root"},
            {
                "binding_id": "empty-role",
                "layer": "root",
                "ephemeral_fork_policy": {"bot_role": "   "},
            },
            {
                "binding_id": "hex-arch",
                "layer": "root",
                "ephemeral_fork_policy": {
                    "bot_role": "dept-hexagonal-architect",
                    "trigger": "on_surface_match",
                    "model_tier": "inherit",
                    "access_mode": "strictly-read-only",
                    "mount_templates": ["fastapi-hexagonal"],
                    "resolution": "L2",
                    "ttl_seconds": 180,
                },
            },
            {
                "binding_id": "dup-arch",
                "layer": "team",
                "ephemeral_fork_policy": {"bot_role": "dept-hexagonal-architect"},
            },
        ]

        # Act
        advisories = extract_ephemeral_advisories(bindings, "src/orders/service.py")

        # Assert
        assert len(advisories) == 1
        assert advisories[0]["bot_role"] == "dept-hexagonal-architect"
        assert advisories[0]["recommended_mcp_call"]["arguments"]["target_path"] == (
            "src/orders/service.py"
        )

    def test_spawn_inspect_and_reap_ephemeral_fork_with_project_bridge(
        self, tmp_path: Path
    ) -> None:
        """Spawn an ephemeral fork with symlinked assets, mounted layers, and bridged rules."""
        # Arrange
        repo = tmp_path / "repo"
        (repo / "antigravity" / ".gemini" / "config").mkdir(parents=True)
        (repo / "antigravity" / ".gemini" / "config" / "AGENTS.md").write_text(
            "# Global Rules\n", encoding="utf-8"
        )
        (repo / "docs").mkdir()
        (repo / "VERSION").write_text("1.7.0\n", encoding="utf-8")
        tpl_rules = repo / "templates" / "fastapi-hexagonal" / "rules"
        tpl_rules.mkdir(parents=True)
        (tpl_rules / "coding.md").write_text("# Coding\n", encoding="utf-8")
        (repo / "layers" / "dept-sec").mkdir(parents=True)
        (repo / "layers" / "dept-ignored").mkdir(parents=True)
        (repo / "layers" / "README.txt").write_text("note\n", encoding="utf-8")

        proj = tmp_path / "consumer_proj"
        proj_rules = proj / ".agents" / "rules"
        proj_rules.mkdir(parents=True)
        (proj_rules / "vertical.md").write_text("# Vertical Rule\n", encoding="utf-8")

        base_manifest = {
            "layer_id": "acme-root",
            "default_stack_templates": ["fastapi-hexagonal", "missing-tpl"],
            "baseline_guardrails": ["G1"],
            "environments": {"dev": {"access_mode": "read-write-local"}},
        }

        # Act
        spawned = spawn_ephemeral_fork(
            repo,
            base_manifest,
            bot_role="dept-sec-bot",
            target_globs=["src/**"],
            architectural_planes=["domain"],
            mount_layers=["dept-sec"],
            mount_project_rules_from=proj,
            model_tier="inherit",
            access_mode="read-write-scoped",
            resolution="L2",
            ttl_seconds=120,
            now_epoch=1000.0,
        )
        inspected = inspect_ephemeral_forks(repo, fork_id=spawned["fork_id"], now_epoch=1050.0)
        reaped_dry = reap_ephemeral_fork(repo, spawned["fork_id"], dry_run=True)
        reaped_real = reap_ephemeral_fork(repo, spawned["fork_id"], dry_run=False)

        # Assert
        assert spawned["bridged_project_files"] == [".agents/rules/vertical.md"]
        fork_dir = repo / "logs" / "ephemeral_forks" / spawned["fork_id"]
        assert not fork_dir.exists()
        assert inspected["active_count"] == 1
        assert inspected["forks"][0]["remaining_ttl_seconds"] == 70.0
        assert reaped_dry["reaped_forks"] == [spawned["fork_id"]]
        assert reaped_real["reaped_forks"] == [spawned["fork_id"]]

    def test_spawn_validation_errors_and_capacity_limit(self, tmp_path: Path) -> None:
        """Reject invalid arguments, missing bridge dir, and capacity limit overflow."""
        # Arrange
        repo = tmp_path / "repo"
        repo.mkdir()
        eph_root = repo / "logs" / "ephemeral_forks"
        for idx in range(16):
            fdir = eph_root / f"eph-bot-{idx}" / "system"
            fdir.mkdir(parents=True)
            (fdir / "mcp-layer.json").write_text(
                json.dumps({"ephemeral_metadata": {"expires_at_epoch": 9999999999.0}}),
                encoding="utf-8",
            )

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid bot_role"):
            spawn_ephemeral_fork(repo, {}, bot_role="BAD_ROLE")
        with pytest.raises(ValueError, match="Invalid model_tier"):
            spawn_ephemeral_fork(repo, {}, bot_role="ok-bot", model_tier="ultra")
        with pytest.raises(ValueError, match="Invalid access_mode"):
            spawn_ephemeral_fork(repo, {}, bot_role="ok-bot", access_mode="root-all")
        with pytest.raises(ValueError, match="Invalid resolution"):
            spawn_ephemeral_fork(repo, {}, bot_role="ok-bot", resolution="L9")
        with pytest.raises(ValueError, match="Invalid ttl_seconds"):
            spawn_ephemeral_fork(repo, {}, bot_role="ok-bot", ttl_seconds=5)
        with pytest.raises(ValueError, match="Invalid architectural_plane"):
            spawn_ephemeral_fork(
                repo, {}, bot_role="ok-bot", architectural_planes=["invalid-plane"]
            )
        with pytest.raises(ValueError, match="Invalid mount_template"):
            spawn_ephemeral_fork(repo, {}, bot_role="ok-bot", mount_templates=["../escape"])
        with pytest.raises(ValueError, match="Invalid mount_layer"):
            spawn_ephemeral_fork(repo, {}, bot_role="ok-bot", mount_layers=["../escape"])
        with pytest.raises(ValueError, match="EPHEMERAL_FORK_LIMIT_REACHED"):
            spawn_ephemeral_fork(repo, {}, bot_role="ok-bot", now_epoch=100.0)

        reap_ephemeral_fork(repo, "all", dry_run=True)
        reap_ephemeral_fork(repo, "all", dry_run=False)
        with pytest.raises(FileNotFoundError, match="mount_project_rules_from"):
            spawn_ephemeral_fork(
                repo,
                {},
                bot_role="ok-bot",
                mount_project_rules_from=tmp_path / "nonexistent_proj",
            )
        outside_secret = tmp_path / "outside_secret.md"
        outside_secret.write_text("# Secret\n", encoding="utf-8")
        hostile_proj = tmp_path / "hostile_proj"
        (hostile_proj / ".agents" / "rules").mkdir(parents=True)
        (hostile_proj / ".agents" / "rules" / "escape.md").symlink_to(outside_secret)
        with pytest.raises(ValueError, match="Outbound symlink escape denied"):
            spawn_ephemeral_fork(
                repo,
                {},
                bot_role="ok-bot",
                mount_project_rules_from=hostile_proj,
            )

    def test_reap_expired_and_inspect_edge_cases(self, tmp_path: Path) -> None:
        """Reap corrupted, manifest-less, and expired forks and handle inspect/reap errors."""
        # Arrange
        repo = tmp_path / "repo"
        eph_root = repo / "logs" / "ephemeral_forks"
        eph_root.mkdir(parents=True)
        (eph_root / "stray.txt").write_text("ignore\n", encoding="utf-8")
        (eph_root / "eph-no-manifest").mkdir()
        corrupt_dir = eph_root / "eph-corrupt" / "system"
        corrupt_dir.mkdir(parents=True)
        (corrupt_dir / "mcp-layer.json").write_text("{bad-json", encoding="utf-8")
        expired_dir = eph_root / "eph-expired" / "system"
        expired_dir.mkdir(parents=True)
        (expired_dir / "mcp-layer.json").write_text(
            json.dumps({"ephemeral_metadata": {"expires_at_epoch": 50.0}}), encoding="utf-8"
        )
        active_dir = eph_root / "eph-active" / "system"
        active_dir.mkdir(parents=True)
        (active_dir / "mcp-layer.json").write_text(
            json.dumps(
                {
                    "default_stack_templates": ["t1"],
                    "ephemeral_metadata": {"bot_role": "active-bot", "expires_at_epoch": 500.0},
                }
            ),
            encoding="utf-8",
        )

        # Act
        with pytest.raises(FileNotFoundError, match="EPHEMERAL_FORK_EXPIRED"):
            inspect_ephemeral_forks(repo, fork_id="eph-expired", now_epoch=100.0)
        with pytest.raises(FileNotFoundError, match="not found"):
            inspect_ephemeral_forks(repo, fork_id="eph-missing", now_epoch=100.0)
        with pytest.raises(ValueError, match="Invalid fork_id"):
            reap_ephemeral_fork(repo, "INVALID_ID")
        with pytest.raises(FileNotFoundError, match="not found"):
            reap_ephemeral_fork(repo, "eph-missing")
        all_active = inspect_ephemeral_forks(repo, now_epoch=100.0)
        empty_inspect = inspect_ephemeral_forks(tmp_path / "no_repo")
        empty_reap_all = reap_ephemeral_fork(tmp_path / "no_repo", "all")
        reap_ephemeral_fork(repo, "all")
        empty_reap = reap_expired_ephemeral_forks(tmp_path / "no_repo")

        # Assert
        assert all_active["active_count"] == 1
        assert all_active["forks"][0]["fork_id"] == "eph-active"
        assert empty_inspect["active_count"] == 0
        assert empty_reap_all["reaped_forks"] == []
        assert empty_reap == []

    def test_spawn_dry_run_and_project_without_rules_dir_and_brief(self, tmp_path: Path) -> None:
        """Support dry_run spawn, empty project bridge, and brief with or without capsule."""
        # Arrange
        repo = tmp_path / "repo"
        (repo / "layers" / "l1").mkdir(parents=True)
        proj_empty = tmp_path / "empty_proj"
        proj_empty.mkdir()

        # Act
        dry_res = spawn_ephemeral_fork(
            repo,
            {},
            bot_role="dry-bot",
            mount_templates=["custom-tpl"],
            dry_run=True,
        )
        live_res = spawn_ephemeral_fork(
            repo,
            {},
            bot_role="bridge-bot",
            mount_project_rules_from=proj_empty,
            dry_run=False,
        )
        brief_no_cap = build_subagent_invocation_brief(
            dry_res["manifest"], "", {"effective_invariants": ["I1"]}, None
        )
        brief_with_cap = build_subagent_invocation_brief(
            live_res["manifest"], "src/a.py", {"effective_invariants": ["I1"]}, "rcap1.tok"
        )

        # Assert
        assert dry_res["dry_run"] is True
        assert not Path(dry_res["fork_dir"]).exists()
        assert live_res["bridged_project_files"] == []
        assert brief_no_cap["capsule_token"] is None
        assert "Sealed Context Capsule" in brief_with_cap["prompt"]

    def test_copy_zero_copy_falls_back_to_copy2_on_cross_device_oserror(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Fall back to shutil.copy2 when os.link raises OSError (e.g. EXDEV cross-device)."""
        # Arrange
        src_file = tmp_path / "source.txt"
        dst_file = tmp_path / "dest.txt"
        src_file.write_text("cross-device-payload\n", encoding="utf-8")

        def _raise_exdev(_src: str, _dst: str) -> None:
            raise OSError(18, "Invalid cross-device link")

        monkeypatch.setattr(os, "link", _raise_exdev)

        # Act
        _copy_zero_copy(src_file, dst_file)

        # Assert
        assert dst_file.read_text(encoding="utf-8") == "cross-device-payload\n"
