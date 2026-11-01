"""Unit tests for dotfiles_mcp.workspace_bootstrapper.

Specification: docs/architecture/04_compaction_surface_and_promotion_engines.md
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from dotfiles_mcp.constants import AGENTS_MD_MAX_BYTES
from dotfiles_mcp.workspace_bootstrapper import (
    bootstrap_layer_workspace,
    inspect_workspace_status,
    register_mounted_subtree,
    set_global_agents_profile,
    sync_layer_workspace,
)


class TestWorkspaceBootstrapper:
    """1:1 unit test suite for workspace_bootstrapper.py."""

    def test_set_global_agents_profile_supports_all_profiles_and_stow(self, tmp_path: Path) -> None:
        """Compose human-core, technical, business, and full profiles cleanly."""
        # Arrange
        for tpl_id, fname, body in (
            (
                "human-core",
                "human-core.md",
                "---\ntrigger: always_on\n---\n# Human Core\n\n> Base quote\n\n---\n\nCore rule 1.",
            ),
            (
                "technical-base",
                "technical-base.md",
                "---\ntrigger: always_on\n---\n# Tech Base\n\n> Tech quote\n\n---\n\nTech rule 1.",
            ),
            (
                "business-base",
                "business-base.md",
                "# Business Base\n\n> Biz quote\n\n---\n\nBiz rule 1.",
            ),
        ):
            rdir = tmp_path / "templates" / tpl_id / "rules"
            rdir.mkdir(parents=True)
            (rdir / fname).write_text(body, encoding="utf-8")

        # Act
        dry_res = set_global_agents_profile(tmp_path, "human-core", dry_run=True)
        tech_res = set_global_agents_profile(tmp_path, "technical", run_stow=False)
        biz_res = set_global_agents_profile(tmp_path, "business", run_stow=False)
        with patch("dotfiles_mcp.workspace_bootstrapper.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            full_res = set_global_agents_profile(
                tmp_path, "full", run_stow=True, home_dir=tmp_path / "home"
            )

        # Assert
        assert dry_res["dry_run"] is True
        assert dry_res["stow_executed"] is False
        assert tech_res["profile"] == "technical"
        assert len(tech_res["source_files"]) == 2
        assert biz_res["profile"] == "business"
        assert full_res["profile"] == "full"
        assert full_res["stow_executed"] is True
        written = (tmp_path / "antigravity/.gemini/config/AGENTS.md").read_text(encoding="utf-8")
        assert "Core rule 1." in written
        assert "Tech rule 1." in written
        assert "Biz rule 1." in written
        assert not written.startswith("---")
        assert "trigger: always_on" not in written
        assert "# Tech Base" not in written
        assert "# Business Base" not in written

    def test_set_global_agents_profile_validates_inputs_and_exact_budget_boundary(
        self, tmp_path: Path
    ) -> None:
        """Accept exact 18,000-byte AGENTS.md cap and reject 18,001 bytes or invalid profiles."""
        # Arrange
        rdir = tmp_path / "templates" / "human-core" / "rules"
        rdir.mkdir(parents=True)
        exact_text = "A" * (AGENTS_MD_MAX_BYTES - 1)
        (rdir / "human-core.md").write_text(exact_text, encoding="utf-8")

        # Act
        exact_res = set_global_agents_profile(tmp_path, "human-core")
        (rdir / "human-core.md").write_text("A" * AGENTS_MD_MAX_BYTES, encoding="utf-8")

        # Assert
        assert exact_res["size_bytes"] == AGENTS_MD_MAX_BYTES
        assert exact_res["headroom_bytes"] == 0
        with pytest.raises(ValueError, match="exceeds 18000-byte cap"):
            set_global_agents_profile(tmp_path, "human-core")
        with pytest.raises(ValueError, match="Invalid global profile"):
            set_global_agents_profile(tmp_path, "unknown-profile")
        with pytest.raises(ValueError, match="Missing profile template rule file"):
            set_global_agents_profile(tmp_path, "technical")

    def test_register_mounted_subtree_upserts_and_sorts_by_precedence(self, tmp_path: Path) -> None:
        """Upsert mounted_layers entries in system/mcp-layer.json sorted by ascending precedence."""
        # Arrange
        sys_dir = tmp_path / "system"
        sys_dir.mkdir(parents=True)
        (sys_dir / "mcp-layer.json").write_text(
            json.dumps(
                {
                    "schema_version": "1.2",
                    "layer_id": "corp-root",
                    "mounted_layers": [
                        {
                            "name": "dept-brand",
                            "layer_id": "dept-brand",
                            "layer_role": "department",
                            "precedence": 30,
                            "repository": "https://example.com/old-brand.git",
                            "branch": "master",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        legal_sys = tmp_path / "layers" / "dept-legal" / "system"
        legal_sys.mkdir(parents=True)
        (legal_sys / "mcp-layer.json").write_text(
            json.dumps(
                {
                    "layer_id": "dept-legal-ip",
                    "layer_role": "domain-policy",
                    "precedence": 5,
                }
            ),
            encoding="utf-8",
        )

        # Act
        dry_res = register_mounted_subtree(
            tmp_path, "dept-legal", "https://example.com/legal.git", "main", dry_run=True
        )
        res1 = register_mounted_subtree(
            tmp_path, "dept-legal", "https://example.com/legal.git", "main"
        )
        res2 = register_mounted_subtree(
            tmp_path, "dept-brand", "https://example.com/new-brand.git", "master"
        )

        # Assert
        assert dry_res["dry_run"] is True
        assert res1["registered_layer"]["precedence"] == 5
        assert res2["total_mounted_layers"] == 2
        saved = json.loads((sys_dir / "mcp-layer.json").read_text(encoding="utf-8"))
        assert [m["name"] for m in saved["mounted_layers"]] == ["dept-legal", "dept-brand"]
        assert saved["mounted_layers"][1]["repository"] == "https://example.com/new-brand.git"
        with pytest.raises(ValueError, match="Invalid layer_name"):
            register_mounted_subtree(tmp_path, "BAD NAME", "https://example.com/x.git")
        with pytest.raises(ValueError, match="Missing root manifest"):
            register_mounted_subtree(tmp_path / "empty", "dept-x", "https://example.com/x.git")

    def test_bootstrap_layer_workspace_initializes_department_and_respects_existing_files(
        self, tmp_path: Path
    ) -> None:
        """Bootstrap and sync hierarchical corporate, department, and squad layer workspaces."""
        # Arrange
        repo_dir = tmp_path / "platform"
        bdir = repo_dir / "templates" / "business-base" / "rules"
        bdir.mkdir(parents=True)
        (repo_dir / "templates" / "business-base" / "template.json").write_text(
            '{"schema_version": "1.0", "template_id": "business-base", '
            '"kind": "domain-policy-pack"}',
            encoding="utf-8",
        )
        (bdir / "business-base.md").write_text("# Business Base\n", encoding="utf-8")
        hdir = repo_dir / "templates" / "human-core" / "rules"
        hdir.mkdir(parents=True)
        (repo_dir / "templates" / "human-core" / "template.json").write_text(
            '{"schema_version": "1.0", "template_id": "human-core", "kind": "domain-policy-pack"}',
            encoding="utf-8",
        )
        (hdir / "human-core.md").write_text("# Human Core\n", encoding="utf-8")
        target_dir = tmp_path / "dept-legal-ip"
        (target_dir / "templates" / "business-base").mkdir(parents=True)
        (target_dir / "VERSION").write_text("0.1.0\n", encoding="utf-8")

        # Act
        dry_res = bootstrap_layer_workspace(
            repo_dir,
            tmp_path / "dry-ws",
            layer_id="squad-alpha",
            layer_role="squad",
            templates=["business-base", "local-only-tpl"],
            scaffold_own_template=False,
            dry_run=True,
        )
        (repo_dir / "system").mkdir(parents=True)
        (repo_dir / "system" / "mcp-layer.json").write_text(
            '{"schema_version": "1.2", "layer_id": "workstation-root", '
            '"layer_role": "workstation"}',
            encoding="utf-8",
        )
        live_res = bootstrap_layer_workspace(
            repo_dir,
            target_dir,
            layer_id="dept-legal-ip",
            layer_role="domain-policy",
            precedence=5,
            upstream_repo="https://example.com/root.git",
            templates=["business-base", "human-core"],
            scaffold_own_template=True,
            dry_run=False,
        )
        squad_pre_git = bootstrap_layer_workspace(
            repo_dir,
            tmp_path / "squad-pre-git",
            layer_id="squad-pre-git",
            layer_role="squad",
            parent_dir=target_dir,
            scaffold_own_template=False,
            dry_run=True,
        )
        subprocess.run(
            ["/usr/bin/git", "init", "-q"],
            cwd=target_dir,
            check=True,
        )
        subprocess.run(
            [
                "/usr/bin/git",
                "remote",
                "add",
                "origin",
                "https://example.com/dept-legal-ip.git",
            ],
            cwd=target_dir,
            check=True,
        )
        squad_dir = tmp_path / "squad-patent-ops"
        squad_res = bootstrap_layer_workspace(
            repo_dir,
            squad_dir,
            layer_id="squad-patent-ops",
            layer_role="squad",
            parent_dir=target_dir,
            templates=["human-core"],
            scaffold_own_template=True,
            dry_run=False,
        )
        (bdir / "business-base.md").write_text("# Business Base v2\n", encoding="utf-8")
        (squad_dir / "templates/local-only").mkdir(parents=True)
        sync_dry = sync_layer_workspace(
            repo_dir, target_dir, templates=["human-core"], dry_run=True
        )
        sync_dept = sync_layer_workspace(repo_dir, target_dir, dry_run=False)
        sync_squad = sync_layer_workspace(repo_dir, squad_dir, parent_dir=target_dir, dry_run=False)
        bare_layer = tmp_path / "bare-layer"
        (bare_layer / "system").mkdir(parents=True)
        (bare_layer / "system/mcp-layer.json").write_text(
            '{"schema_version": "1.2", "layer_id": "bare-layer", '
            '"layer_role": "corporate", "default_stack_templates": []}',
            encoding="utf-8",
        )
        sync_bare = sync_layer_workspace(repo_dir, bare_layer, templates=[""], dry_run=False)
        sync_bare_add = sync_layer_workspace(
            repo_dir, bare_layer, templates=["business-base"], dry_run=False
        )
        (target_dir / ".agents/SESSION.md").write_text(
            "## Session Log\n- Conv: 3fcd5708-4b9b-4d2b-b187-f224a76165de\n",
            encoding="utf-8",
        )
        ws_status = inspect_workspace_status(repo_dir, repo_dir)
        dept_status = inspect_workspace_status(repo_dir, target_dir)
        proj_status = inspect_workspace_status(repo_dir, tmp_path / "empty-proj")

        # Assert
        assert ws_status["is_oss_dev_workspace"] is True
        assert "setup-dev" in ws_status["available_makefile_targets"]
        assert dept_status["is_oss_dev_workspace"] is False
        assert "setup-dev" not in dept_status["available_makefile_targets"]
        assert dry_res["dry_run"] is True
        assert squad_pre_git["dry_run"] is True
        assert dry_res["scaffolded_template"] is None
        assert dry_res["precedence"] == 50
        assert live_res["precedence"] == 5
        assert live_res["copied_templates"] == ["business-base", "human-core"]
        assert live_res["scaffolded_template"] == "dept-legal-ip"
        assert "VERSION" not in live_res["baseline_files_created"]
        assert "Makefile" in live_res["baseline_files_created"]
        assert "make horizon" in (target_dir / "Makefile").read_text(encoding="utf-8")
        assert "make status" in (target_dir / "Makefile").read_text(encoding="utf-8")
        assert "make env-gate" in (target_dir / "Makefile").read_text(encoding="utf-8")
        assert str(target_dir.resolve()) in (squad_dir / "Makefile").read_text(encoding="utf-8")
        assert "CONTRIB_REPO ?=" in (bare_layer / "Makefile").read_text(encoding="utf-8")
        assert ".agents/rules/business-base.md" in live_res["files_materialized"]
        assert ".agents/rules/dept-legal-ip.md" in live_res["files_materialized"]
        assert ".agents/SESSION.md" in live_res["files_materialized"]
        assert ".agents/rules/layer-05-root.md" not in live_res["files_materialized"]
        assert squad_res["precedence"] == 50
        assert squad_res["manifest"]["upstream_layer"]["layer_id"] == "dept-legal-ip"
        assert (
            squad_res["manifest"]["upstream_layer"]["repository"]
            == "https://example.com/dept-legal-ip.git"
        )
        assert ".agents/rules/business-base.md" in squad_res["files_materialized"]
        assert ".agents/rules/dept-legal-ip.md" in squad_res["files_materialized"]
        assert ".agents/rules/squad-patent-ops.md" in squad_res["files_materialized"]
        assert ".agents/rules/layer-50-root.md" not in squad_res["files_materialized"]
        assert sync_dry["dry_run"] is True
        assert "business-base" in sync_dept["synced_templates"]
        assert "business-base" in sync_squad["synced_templates"]
        assert (squad_dir / ".agents/rules/business-base.md").read_text(encoding="utf-8") == (
            '---\ntrigger: always_on\ndescription: "Business Base v2"\n---\n# Business Base v2\n'
        )
        assert sync_bare["synced_templates"] == []
        assert sync_bare_add["synced_templates"] == ["business-base"]
        assert dept_status["workspace_mode"] == "business"
        assert dept_status["git_state"]["is_git_repo"] is True
        assert dept_status["session_state"]["last_conversation_id"] == (
            "3fcd5708-4b9b-4d2b-b187-f224a76165de"
        )
        assert dept_status["priority_state"]["active_tracker"] == "WORKTASK.md"
        assert dept_status["git_governance"]["active_environment"] == "dev"
        assert dept_status["horizon"] is not None
        assert proj_status["workspace_mode"] == "technical"
        assert proj_status["git_state"]["is_git_repo"] is False
        assert proj_status["session_state"]["last_conversation_id"] is None
        assert proj_status["horizon"] is None
        with pytest.raises(ValueError, match="Missing target layer manifest"):
            sync_layer_workspace(repo_dir, tmp_path / "missing-layer")
        with pytest.raises(ValueError, match="Invalid layer_id"):
            bootstrap_layer_workspace(repo_dir, target_dir, layer_id="BAD_ID")
        with pytest.raises(ValueError, match="Invalid layer_role"):
            bootstrap_layer_workspace(
                repo_dir, target_dir, layer_id="dept-ok", layer_role="invalid"
            )
