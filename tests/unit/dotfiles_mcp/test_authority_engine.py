"""1:1 unit tests for scripts/dotfiles_mcp/authority_engine.py.

Specification: docs/architecture/04_compaction_surface_and_promotion_engines.md
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from dotfiles_mcp.authority_engine import (
    build_upward_promotion_pr_plan,
    configure_layer_authority,
    delegate_directive_to_child,
    resolve_git_user_email,
    verify_layer_operation_authority,
    verify_oss_promotion_agnosticism,
    verify_single_hop_upstream,
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
        assert (from_env, from_git, from_fail, from_oserror) == (
            "override@acme.com",
            "gituser@acme.com",
            "",
            "",
        )

    def test_configure_layer_authority_writes_and_validates_manifest(self, tmp_path: Path) -> None:
        """Configure layer_authority block with default or explicit escalation_contact."""
        # Arrange
        layer_dir = tmp_path / "dept-tech"
        (layer_dir / "system").mkdir(parents=True)
        (layer_dir / "system/mcp-layer.json").write_text(
            json.dumps({"schema_version": "1.2", "layer_id": "dept-tech"}), encoding="utf-8"
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
            layer_dir, owner_role="Open Maintainer", authorized_emails=[], dry_run=True
        )

        # Assert
        assert dry_res["dry_run"] is True
        assert dry_res["layer_authority"]["escalation_contact"] == (
            "Chief Technology Officer (dept-tech) <cto@acme.com>"
        )
        assert live_res["layer_authority"]["escalation_contact"] == "CTO Office <cto@acme.com>"
        assert empty_emails_res["layer_authority"]["escalation_contact"] == (
            "Open Maintainer (dept-tech)"
        )
        saved = json.loads((layer_dir / "system/mcp-layer.json").read_text(encoding="utf-8"))
        assert saved["layer_authority"]["owner_role"] == "Chief Technology Officer"
        with pytest.raises(ValueError, match="Missing layer manifest"):
            configure_layer_authority(tmp_path / "missing", owner_role="CTO", authorized_emails=[])
        with pytest.raises(ValueError, match="owner_role must be a non-empty"):
            configure_layer_authority(layer_dir, owner_role="   ", authorized_emails=[])

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
            '{"schema_version":"1.2","layer_id":"squad-web","layer_role":"squad",'
            '"upstream_layer":{"layer_id":"dept-tech"},'
            '"default_stack_templates":["dept-tech","squad-web"],'
            '"layer_authority":{"owner_role":"Squad Lead",'
            '"authorized_emails":["lead@squad.acme.com","*@managers.acme.com"],'
            '"maintainer_emails":["maint@squad.acme.com"],'
            '"escalation_contact":"Squad Lead <lead@squad.acme.com>"}}',
            encoding="utf-8",
        )
        non_dict_dir, bad_auth_dir = tmp_path / "non-dict", tmp_path / "bad-auth"
        (non_dict_dir / "system").mkdir(parents=True)
        (non_dict_dir / "system/mcp-layer.json").write_text("[]", encoding="utf-8")
        (bad_auth_dir / "system").mkdir(parents=True)
        (bad_auth_dir / "system/mcp-layer.json").write_text(
            '{"layer_id":"bad-auth","upstream_layer":"invalid","layer_authority":"invalid"}',
            encoding="utf-8",
        )

        # Act
        b_lr = verify_layer_operation_authority(
            squad_dir,
            operation="edit-asset",
            target_rel_path="./.agents/rules/layer-25-dept-tech.md",
        )
        b_td = verify_layer_operation_authority(
            squad_dir, operation="edit-asset", target_rel_path="templates/dept-tech"
        )
        b_ar = verify_layer_operation_authority(
            squad_dir, operation="edit-asset", target_rel_path=".agents/rules/tech.md"
        )
        b_as = verify_layer_operation_authority(
            squad_dir, operation="edit-asset", target_rel_path=".agents/skills/tech-guide/SKILL.md"
        )
        ok_own = verify_layer_operation_authority(
            squad_dir, operation="diff-project", target_rel_path=".agents/rules/squad-web.md"
        )
        b_rel = verify_layer_operation_authority(squad_dir, operation="release")
        ok_own_rel = verify_layer_operation_authority(
            squad_dir, operation="release", actor_email="lead@squad.acme.com"
        )
        ok_maint = verify_layer_operation_authority(
            squad_dir, operation="delegate-to-child", actor_email="maint@squad.acme.com"
        )
        ok_glob = verify_layer_operation_authority(
            squad_dir, operation="release", actor_email="director@managers.acme.com"
        )
        ok_open = verify_layer_operation_authority(
            non_dict_dir, operation="release", actor_email="anyone@acme.com"
        )
        ok_bad = verify_layer_operation_authority(
            bad_auth_dir, operation="release", actor_email="anyone@acme.com"
        )

        # Assert
        assert (
            b_lr["allowed"] is False and b_lr["reason_code"] == "INHERITED_UPSTREAM_ASSET_IMMUTABLE"
        )
        assert "promote-from-project" in b_lr["remediation"]
        assert (b_td["origin_source"], b_ar["origin_source"], b_as["origin_source"]) == (
            "dept-tech",
            "dept-tech",
            "dept-tech",
        )
        assert ok_own["allowed"] is True and ok_own["reason_code"] == "CONSUMER_OPERATION_ALLOWED"
        assert b_rel["allowed"] is False and b_rel["reason_code"] == "UNAUTHORIZED_ACTOR_EMAIL"
        assert "Squad Lead <lead@squad.acme.com>" in b_rel["remediation"]
        assert ok_own_rel["reason_code"] == "OWNER_AUTHORIZED"
        assert ok_maint["reason_code"] == "OWNER_AUTHORIZED"
        assert all(x["allowed"] for x in (ok_own_rel, ok_maint, ok_glob, ok_open, ok_bad))

    def test_build_upward_promotion_pr_plan_captures_child_layer_context(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Generate a Pull Request plan anchored in the originating child layer's context."""
        # Arrange
        monkeypatch.setenv("DOTFILES_GIT_USER_EMAIL", "member@squad.acme.com")
        squad_dir, dept_dir = tmp_path / "squad-shm", tmp_path / "dept-tech"
        (squad_dir / "system").mkdir(parents=True)
        (squad_dir / "system/mcp-layer.json").write_text(
            json.dumps({"layer_id": "squad-shm", "layer_role": "squad", "precedence": 50}),
            encoding="utf-8",
        )
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
        raw_proj, raw_target = tmp_path / "Plain_Project", tmp_path / "raw_target"
        raw_proj.mkdir()
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
        assert (plan["origin_layer_id"], plan["origin_layer_role"], plan["proposer_email"]) == (
            "squad-shm",
            "squad",
            "member@squad.acme.com",
        )
        assert (plan["target_layer_id"], plan["reviewer_contact"], plan["branch_name"]) == (
            "dept-tech",
            "CTO <cto@acme.com>",
            "promote/squad-shm/shm-sensor",
        )
        assert len(plan["git_pr_commands"]) == 4 and "gh pr create" in plan["git_pr_commands"][3]
        assert (
            fallback_plan["branch_name"],
            fallback_plan["proposer_email"],
            plan["oss_anonymized"],
        ) == ("promote/plain-project/asset", "explicit@acme.com", False)

    def test_oss_agnosticism_single_hop_and_anonymized_pr_plan(self, tmp_path: Path) -> None:
        """Enforce single-hop boundary, OSS agnosticism gate, and OSS PR anonymization."""
        # Arrange
        oss_root, corp_dir, squad_dir = (
            tmp_path / "oss-root",
            tmp_path / "corp-zyxwvut-root",
            tmp_path / "squad-alpha",
        )
        for d in (oss_root, corp_dir, squad_dir):
            (d / "system").mkdir(parents=True)
        (oss_root / "system/mcp-layer.json").write_text(
            '{"layer_id":"root","layer_role":"root","precedence":10}', encoding="utf-8"
        )
        (corp_dir / "system/mcp-layer.json").write_text(
            '{"layer_id":"corp-zyxwvut-root","layer_role":"corporate","precedence":10,'
            '"upstream_layer":{"layer_id":"root"},'
            '"mounted_layers":[{"name":"dept-quantum","layer_id":"dept-quantum"},"invalid"],'
            '"layer_authority":{"owner_role":"CEO","authorized_emails":'
            '["ceo@zyxwvut.io","dev@users.noreply.github.com","no-at-sign",123]}}',
            encoding="utf-8",
        )
        (squad_dir / "system/mcp-layer.json").write_text(
            '{"layer_id":"squad-alpha","layer_role":"squad",'
            '"upstream_layer":{"layer_id":"dept-quantum"}}',
            encoding="utf-8",
        )

        # Act
        verify_oss_promotion_agnosticism(
            corp_dir, "# Universal Rule\nPure universal content.\n", "rules/base.md"
        )
        verify_single_hop_upstream(corp_dir, oss_root, actor_email="ceo@zyxwvut.io")
        pr_kw = {
            "source_rel": "templates/business-base/rules/business-base.md",
            "dest_rel": "templates/business-base/rules/business-base.md",
            "target_layer": "root",
            "target_template": "business-base",
            "sha256": "12345678",
            "actor_email": "ceo@zyxwvut.io",
        }
        oss_plan = build_upward_promotion_pr_plan(corp_dir, oss_root, **pr_kw)
        credited_plan = build_upward_promotion_pr_plan(
            corp_dir,
            oss_root,
            **pr_kw,
            contributing_org="Acme Industrial Group",
            contributors="CLO, CTO, Principal Architect",
            validation_context="Root 0 + 5 Department layers + Squads",
        )

        # Assert
        with pytest.raises(ValueError, match="OSS_AGNOSTICISM_VIOLATION"):
            verify_oss_promotion_agnosticism(
                corp_dir, "# Rule\nMentions zyxwvut and quantum.\n", "rules/base.md"
            )
        with pytest.raises(ValueError, match="CROSS_TIER_PROMOTION_BYPASS"):
            verify_single_hop_upstream(squad_dir, oss_root, actor_email="ceo@zyxwvut.io")
        with pytest.raises(ValueError, match="UNAUTHORIZED_OSS_PROMOTION"):
            verify_single_hop_upstream(corp_dir, oss_root, actor_email="intruder@other.org")
        assert (
            oss_plan["oss_anonymized"] is True
            and oss_plan["origin_layer_id"] == "enterprise-root-0"
        )
        assert oss_plan["proposer_email"] == "oss-contributor"
        assert oss_plan["contributing_org"] == "Anonymous Organization (default)"
        assert oss_plan["branch_name"] == "promote/oss/business-base"
        assert "Community Attribution & Real-World Validation (Optional)" in oss_plan["pr_body"]
        assert "zyxwvut" not in oss_plan["pr_body"]
        assert credited_plan["contributing_org"] == "Acme Industrial Group"
        assert credited_plan["contributors"] == "CLO, CTO, Principal Architect"
        assert "Acme Industrial Group" in credited_plan["pr_body"]

    def test_delegate_directive_to_child_appends_and_validates(self, tmp_path: Path) -> None:
        """Delegate a 1-hop downward directive or file across all child governance surfaces."""
        # Arrange
        corp_dir, sib_child = tmp_path / "corp-root", tmp_path / "dept-legal"
        for d in (corp_dir, sib_child):
            (d / "system").mkdir(parents=True)
        (corp_dir / "system/mcp-layer.json").write_text(
            '{"layer_id":"corp-root","layer_role":"corporate","precedence":10,'
            '"layer_authority":{"owner_role":"CEO","authorized_emails":["ceo@acme.com"]}}',
            encoding="utf-8",
        )
        (corp_dir / "WORKROAD.md").write_text("# Corp Roadmap\n- Phase 1", encoding="utf-8")
        mnt_child = corp_dir / "layers" / "dept-legal"
        mnt_child.mkdir(parents=True)
        (sib_child / "system/mcp-layer.json").write_text("{}", encoding="utf-8")
        (sib_child / "WORKTASK.md").write_text("# Tasks", encoding="utf-8")

        # Act
        def dlg(**kw: object) -> dict[str, object]:
            return delegate_directive_to_child(
                corp_dir,
                child_layer="dept-legal",
                actor_email="ceo@acme.com",
                **kw,  # type: ignore[arg-type]
            )

        dry_res = dlg(directive="Audit Q3 compliance ledgers", priority="P0", dry_run=True)
        dry_existed = (mnt_child / "WORKTASK.md").exists()
        live_res = dlg(
            directive="Audit Q3 compliance ledgers", source_rel_path="WORKROAD.md", priority="P0"
        )
        dup_res = dlg(directive="Audit Q3 compliance ledgers", priority="P0")
        road_dry = dlg(source_rel_path="WORKROAD.md", tracker="roadmaps", dry_run=True)
        road_live = dlg(source_rel_path="WORKROAD.md", tracker="roadmaps")
        road_staged = dlg(source_rel_path="WORKROAD.md", tracker="roadmaps")
        road_forced = dlg(source_rel_path="WORKROAD.md", tracker="roadmaps", force_overwrite=True)
        rule_dry = dlg(directive="Enforce GDPR", tracker="rules", dry_run=True)
        rule_live = dlg(directive="Enforce GDPR", tracker="rules")
        rule_staged = dlg(directive="Enforce GDPR v2", tracker="rules")
        rule_forced = dlg(directive="Enforce GDPR v2", tracker="rules", force_overwrite=True)

        # Assert
        assert dry_res["dry_run"] is True and dry_existed is False
        assert road_dry["dry_run"] is True and rule_dry["dry_run"] is True
        assert len(live_res["updated_paths"]) == 2  # type: ignore[arg-type]
        assert "Audit Q3 compliance ledgers" in (mnt_child / "WORKTASK.md").read_text("utf-8")
        assert (sib_child / "WORKTASK.md").read_text("utf-8").count("Audit Q3") == 1
        assert dup_res["delegated_entry"] == live_res["delegated_entry"]
        assert (sib_child / "roadmaps/WORKROAD.md").is_file() and road_live["tracker"] == "roadmaps"
        assert len(road_staged["staged_proposals"]) == 2  # type: ignore[arg-type]
        assert len(road_forced["updated_paths"]) == 2  # type: ignore[arg-type]
        assert (sib_child / ".agents/rules/delegated-item.md").is_file() and rule_live[
            "tracker"
        ] == "rules"
        assert len(rule_staged["staged_proposals"]) == 2  # type: ignore[arg-type]
        assert len(rule_forced["updated_paths"]) == 4  # type: ignore[arg-type]
        assert "Delivered to `dept-legal`" in (corp_dir / "WORKROAD.md").read_text("utf-8")
        assert "## Outbound Delegations" in (corp_dir / "WORKTASK.md").read_text("utf-8")
        assert live_res["ticket_id"] == "CORP-ROOT-DEPT-LEGAL-01"
        for bad_kw, err_pat in (
            ({"child_layer": "Bad Name", "directive": "x"}, "must be kebab-case"),
            ({"child_layer": "dept-legal", "directive": "  "}, "directive must be a non-empty"),
            ({"child_layer": "dept-legal", "source_rel_path": "../x.md"}, "source_rel_path"),
            ({"child_layer": "dept-legal", "directive": "x", "priority": "P9"}, "Invalid priority"),
            ({"child_layer": "dept-legal", "directive": "x", "tracker": "X.md"}, "Invalid tracker"),
            (
                {"child_layer": "dept-legal", "directive": "x", "actor_email": "no@acme.com"},
                "DELEGATION_AUTHORITY_DENIED",
            ),
            (
                {"child_layer": "dept-missing", "directive": "x", "actor_email": "ceo@acme.com"},
                "Target 1-hop child layer not found",
            ),
        ):
            with pytest.raises(ValueError, match=err_pat):
                delegate_directive_to_child(corp_dir, **bad_kw)  # type: ignore[arg-type]
