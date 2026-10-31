"""1:1 unit tests for scripts/dotfiles_mcp/authority_engine.py."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from dotfiles_mcp.authority_engine import (
    build_upward_promotion_pr_plan,
    configure_layer_authority,
    resolve_git_user_email,
    verify_layer_operation_authority,
)


class TestAuthorityEngine:
    """Unit test suite for layer authority verification and upward PR promotion planning."""

    def test_resolve_git_user_email_handles_env_git_and_oserror(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Resolve git user.email from env override, subprocess git config, or fallback to empty."""
        # Arrange
        monkeypatch.setenv("DOTFILES_GIT_USER_EMAIL", "override@acme.com")
        mock_ok = MagicMock(spec=subprocess.CompletedProcess)
        mock_ok.returncode = 0
        mock_ok.stdout = "gituser@acme.com\n"
        mock_empty = MagicMock(spec=subprocess.CompletedProcess)
        mock_empty.returncode = 1
        mock_empty.stdout = ""

        # Act
        from_env = resolve_git_user_email(tmp_path)
        monkeypatch.delenv("DOTFILES_GIT_USER_EMAIL", raising=False)
        with patch("dotfiles_mcp.authority_engine.subprocess.run", return_value=mock_ok):
            from_git = resolve_git_user_email(tmp_path)
        with patch("dotfiles_mcp.authority_engine.subprocess.run", return_value=mock_empty):
            from_fail = resolve_git_user_email(tmp_path)
        with patch(
            "dotfiles_mcp.authority_engine.subprocess.run",
            side_effect=OSError("git missing"),
        ):
            from_oserror = resolve_git_user_email(tmp_path)

        # Assert
        assert from_env == "override@acme.com"
        assert from_git == "gituser@acme.com"
        assert from_fail == ""
        assert from_oserror == ""

    def test_configure_layer_authority_writes_and_validates_manifest(
        self,
        tmp_path: Path,
    ) -> None:
        """Configure layer_authority block with default or explicit escalation_contact."""
        # Arrange
        layer_dir = tmp_path / "dept-tech"
        (layer_dir / "system").mkdir(parents=True)
        (layer_dir / "system/mcp-layer.json").write_text(
            json.dumps({"schema_version": "1.2", "layer_id": "dept-tech"}),
            encoding="utf-8",
        )

        # Act
        dry_res = configure_layer_authority(
            layer_dir,
            owner_role="Chief Technology Officer",
            authorized_emails=["cto@acme.com", "ceo@acme.com"],
            dry_run=True,
        )
        live_res = configure_layer_authority(
            layer_dir,
            owner_role="Chief Technology Officer",
            authorized_emails=["cto@acme.com"],
            escalation_contact="CTO Office <cto@acme.com>",
            dry_run=False,
        )
        empty_emails_res = configure_layer_authority(
            layer_dir,
            owner_role="Open Maintainer",
            authorized_emails=[],
            dry_run=True,
        )

        # Assert
        assert dry_res["dry_run"] is True
        assert (
            dry_res["layer_authority"]["escalation_contact"]
            == "Chief Technology Officer (dept-tech) <cto@acme.com>"
        )
        assert live_res["layer_authority"]["escalation_contact"] == "CTO Office <cto@acme.com>"
        assert (
            empty_emails_res["layer_authority"]["escalation_contact"]
            == "Open Maintainer (dept-tech)"
        )
        saved = json.loads((layer_dir / "system/mcp-layer.json").read_text(encoding="utf-8"))
        assert saved["layer_authority"]["owner_role"] == "Chief Technology Officer"
        with pytest.raises(ValueError, match="Missing layer manifest"):
            configure_layer_authority(
                tmp_path / "missing",
                owner_role="CTO",
                authorized_emails=[],
            )
        with pytest.raises(ValueError, match="owner_role must be a non-empty"):
            configure_layer_authority(
                layer_dir,
                owner_role="   ",
                authorized_emails=[],
            )

    def test_verify_layer_operation_authority_enforces_immutability_and_email_gates(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Block inherited asset edits and unauthorized owner ops with constructive remediation."""
        # Arrange
        monkeypatch.setenv("DOTFILES_GIT_USER_EMAIL", "dev@squad.acme.com")
        squad_dir = tmp_path / "squad-web"
        (squad_dir / "system").mkdir(parents=True)
        (squad_dir / "templates/dept-tech/rules").mkdir(parents=True)
        (squad_dir / "templates/dept-tech/rules/tech.md").write_text("# Tech\n", encoding="utf-8")
        (squad_dir / "templates/dept-tech/skills/tech-guide").mkdir(parents=True)
        (squad_dir / "templates/dept-tech/skills/tech-guide/SKILL.md").write_text(
            "---\nname: tech-guide\ndescription: x\n---\n", encoding="utf-8"
        )
        (squad_dir / "templates/squad-web/rules").mkdir(parents=True)
        (squad_dir / "templates/squad-web/rules/squad-web.md").write_text(
            "# Squad\n", encoding="utf-8"
        )
        (squad_dir / "system/mcp-layer.json").write_text(
            json.dumps(
                {
                    "schema_version": "1.2",
                    "layer_id": "squad-web",
                    "layer_role": "team",
                    "upstream_layer": {"layer_id": "dept-tech"},
                    "default_stack_templates": ["dept-tech", "squad-web"],
                    "layer_authority": {
                        "owner_role": "Squad Lead",
                        "authorized_emails": ["lead@squad.acme.com", "*@managers.acme.com"],
                        "escalation_contact": "Squad Lead <lead@squad.acme.com>",
                    },
                }
            ),
            encoding="utf-8",
        )
        non_dict_dir = tmp_path / "non-dict"
        (non_dict_dir / "system").mkdir(parents=True)
        (non_dict_dir / "system/mcp-layer.json").write_text("[]", encoding="utf-8")
        bad_auth_dir = tmp_path / "bad-auth"
        (bad_auth_dir / "system").mkdir(parents=True)
        (bad_auth_dir / "system/mcp-layer.json").write_text(
            json.dumps(
                {
                    "layer_id": "bad-auth",
                    "upstream_layer": "invalid",
                    "layer_authority": "invalid",
                }
            ),
            encoding="utf-8",
        )

        # Act
        block_layer_rule = verify_layer_operation_authority(
            squad_dir,
            operation="edit-asset",
            target_rel_path="./.agents/rules/layer-25-dept-tech.md",
        )
        block_tpl_dir = verify_layer_operation_authority(
            squad_dir,
            operation="edit-asset",
            target_rel_path="templates/dept-tech/rules/tech.md",
        )
        block_agent_rule = verify_layer_operation_authority(
            squad_dir,
            operation="edit-asset",
            target_rel_path=".agents/rules/tech.md",
        )
        block_agent_skill = verify_layer_operation_authority(
            squad_dir,
            operation="edit-asset",
            target_rel_path=".agents/skills/tech-guide/SKILL.md",
        )
        allow_own_rule = verify_layer_operation_authority(
            squad_dir,
            operation="diff-project",
            target_rel_path=".agents/rules/squad-web.md",
        )
        block_unauth_release = verify_layer_operation_authority(
            squad_dir,
            operation="release",
        )
        allow_owner_release = verify_layer_operation_authority(
            squad_dir,
            operation="release",
            actor_email="lead@squad.acme.com",
        )
        allow_glob_release = verify_layer_operation_authority(
            squad_dir,
            operation="release",
            actor_email="director@managers.acme.com",
        )
        allow_open_layer = verify_layer_operation_authority(
            non_dict_dir,
            operation="release",
            actor_email="anyone@acme.com",
        )
        allow_bad_auth = verify_layer_operation_authority(
            bad_auth_dir,
            operation="release",
            actor_email="anyone@acme.com",
        )

        # Assert
        assert block_layer_rule["allowed"] is False
        assert block_layer_rule["reason_code"] == "INHERITED_UPSTREAM_ASSET_IMMUTABLE"
        assert "promote-from-project" in block_layer_rule["remediation"]
        assert block_tpl_dir["origin_source"] == "dept-tech"
        assert block_agent_rule["origin_source"] == "dept-tech"
        assert block_agent_skill["origin_source"] == "dept-tech"
        assert allow_own_rule["allowed"] is True
        assert allow_own_rule["reason_code"] == "CONSUMER_OPERATION_ALLOWED"
        assert block_unauth_release["allowed"] is False
        assert block_unauth_release["reason_code"] == "UNAUTHORIZED_ACTOR_EMAIL"
        assert "Squad Lead <lead@squad.acme.com>" in block_unauth_release["remediation"]
        assert allow_owner_release["allowed"] is True
        assert allow_owner_release["reason_code"] == "OWNER_AUTHORIZED"
        assert allow_glob_release["allowed"] is True
        assert allow_open_layer["allowed"] is True
        assert allow_bad_auth["allowed"] is True

    def test_build_upward_promotion_pr_plan_captures_child_layer_context(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Generate a Pull Request plan anchored in the originating child layer's context."""
        # Arrange
        monkeypatch.setenv("DOTFILES_GIT_USER_EMAIL", "member@squad.acme.com")
        squad_dir = tmp_path / "squad-shm"
        (squad_dir / "system").mkdir(parents=True)
        (squad_dir / "system/mcp-layer.json").write_text(
            json.dumps(
                {
                    "layer_id": "squad-shm",
                    "layer_role": "team",
                    "precedence": 50,
                }
            ),
            encoding="utf-8",
        )
        dept_dir = tmp_path / "dept-tech"
        (dept_dir / "system").mkdir(parents=True)
        (dept_dir / "system/mcp-layer.json").write_text(
            json.dumps(
                {
                    "layer_id": "dept-tech",
                    "layer_role": "department",
                    "precedence": 25,
                    "layer_authority": {
                        "owner_role": "CTO",
                        "escalation_contact": "CTO <cto@acme.com>",
                    },
                }
            ),
            encoding="utf-8",
        )
        raw_proj = tmp_path / "Plain_Project"
        raw_proj.mkdir()
        raw_target = tmp_path / "raw_target"
        (raw_target / "system").mkdir(parents=True)
        (raw_target / "system/mcp-layer.json").write_text(
            json.dumps({"layer_id": "raw-target", "layer_authority": "invalid"}),
            encoding="utf-8",
        )

        # Act
        plan = build_upward_promotion_pr_plan(
            squad_dir,
            dept_dir,
            source_rel=".agents/rules/shm-sensor.md",
            dest_rel="templates/tech-pack/rules/shm-sensor.md",
            target_layer="dept-tech",
            target_template="tech-pack",
            sha256="abc12345",
        )
        fallback_plan = build_upward_promotion_pr_plan(
            raw_proj,
            raw_target,
            source_rel=".agents/rules/###.md",
            dest_rel="antigravity/.gemini/config/AGENTS.md",
            target_layer="root",
            target_template=None,
            sha256="def67890",
            actor_email="explicit@acme.com",
        )

        # Assert
        assert plan["origin_layer_id"] == "squad-shm"
        assert plan["origin_layer_role"] == "team"
        assert plan["proposer_email"] == "member@squad.acme.com"
        assert plan["target_layer_id"] == "dept-tech"
        assert plan["reviewer_contact"] == "CTO <cto@acme.com>"
        assert plan["branch_name"] == "promote/squad-shm/shm-sensor"
        assert len(plan["git_pr_commands"]) == 4
        assert "gh pr create" in plan["git_pr_commands"][3]
        assert fallback_plan["branch_name"] == "promote/plain-project/asset"
        assert fallback_plan["proposer_email"] == "explicit@acme.com"
