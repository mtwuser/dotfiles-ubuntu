"""Unit tests for git_governance_engine (branch policy, env promotion, non-destructive staging).

Specification: docs/architecture/04_compaction_surface_and_promotion_engines.md
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

import pytest
from dotfiles_mcp.git_governance_engine import (
    configure_git_governance_policy,
    evaluate_environment_promotion,
    inspect_git_governance_state,
    manage_layer_roster,
    reconcile_template_pack_sync,
    record_governance_decision,
    record_governance_event,
    stage_non_destructive_proposal,
)


class TestGitGovernanceEngine:
    """Verify non-destructive proposal staging, branch policy, env gates, and audit ledger."""

    def test_record_event_and_stage_proposal_idempotency(self, tmp_path: Path) -> None:
        """Persist governance alerts to JSONL/SESSION.md and stage non-destructive proposals."""
        # Arrange
        ws = tmp_path / "dept-legal"
        (ws / "system").mkdir(parents=True)
        (ws / "system/mcp-layer.json").write_text('{"layer_id":"dept-legal"}', encoding="utf-8")

        # Act
        dry_ev = record_governance_event(
            ws, operation="release", status="blocked", message="Dry block", dry_run=True
        )
        ok_ev = record_governance_event(
            ws, operation="sync-layer", status="allowed", message="Allowed op"
        )
        blk_1 = record_governance_event(
            ws,
            operation="release",
            status="blocked",
            reason_code="NO_AUTH",
            message="Denied release",
        )
        (ws / ".agents/SESSION.md").write_text(
            (ws / ".agents/SESSION.md").read_text("utf-8") + "\nExtra note", encoding="utf-8"
        )
        blk_dup = record_governance_event(
            ws,
            operation="release",
            status="blocked",
            reason_code="NO_AUTH",
            message="Denied release",
        )
        dry_stg = stage_non_destructive_proposal(
            ws,
            scope_tag="from-root",
            file_name="dry-policy.md",
            content="# Dry",
            operation="delegate-to-child",
            dry_run=True,
        )
        (ws / "WORKTASK.md").write_text("# Tasks — dept-legal", encoding="utf-8")
        stg_1 = stage_non_destructive_proposal(
            ws,
            scope_tag="from-root",
            file_name="policy.md",
            content="# Live Policy\n",
            operation="delegate-to-child",
            actor_email="ceo@acme.com",
        )
        stg_dup = stage_non_destructive_proposal(
            ws,
            scope_tag="from-root",
            file_name="policy.md",
            content="# Live Policy\n",
            operation="delegate-to-child",
            actor_email="ceo@acme.com",
        )

        # Assert
        assert dry_ev["layer_id"] == "dept-legal" and ok_ev["status"] == "allowed"
        assert blk_1["reason_code"] == "NO_AUTH" and blk_dup["status"] == "blocked"
        assert not dry_stg.exists() and stg_1.is_file() and stg_1 == stg_dup
        session_txt = (ws / ".agents/SESSION.md").read_text(encoding="utf-8")
        assert session_txt.count("Denied release") == 1
        assert (ws / "WORKTASK.md").read_text(encoding="utf-8").count("Staged Governance") == 1
        log_lines = (ws / "logs/governance_audit.jsonl").read_text(encoding="utf-8").splitlines()
        assert len(log_lines) == 5

    def test_configure_and_inspect_git_governance_policy(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Configure branch protection + CODEOWNERS, manage roster, and inspect branch stages."""
        # Arrange
        ws = tmp_path / "squad-shm"
        ws.mkdir(parents=True)
        with pytest.raises(ValueError, match="Missing layer manifest"):
            configure_git_governance_policy(ws)
        with pytest.raises(ValueError, match="Missing layer manifest"):
            manage_layer_roster(ws)
        (ws / "system").mkdir(parents=True)
        (ws / "system/mcp-layer.json").write_text(
            json.dumps(
                {
                    "layer_id": "squad-shm",
                    "layer_authority": {"authorized_emails": ["lead@acme.com", "*@acme.com"]},
                }
            ),
            encoding="utf-8",
        )

        # Act
        dry_cfg = configure_git_governance_policy(ws, sync_codeowners=False, dry_run=True)
        no_co_cfg = configure_git_governance_policy(ws, sync_codeowners=False, dry_run=False)
        r_noop = manage_layer_roster(ws)
        cfg_res = configure_git_governance_policy(ws, sync_codeowners=True)
        r_dry = manage_layer_roster(
            ws, add_email="qa@acme.com", member_role="validator", dry_run=True
        )
        r_val = manage_layer_roster(ws, add_email="qa@acme.com", member_role="validator")
        r_maint = manage_layer_roster(ws, add_email="maint@acme.com", member_role="maintainer")
        r_own = manage_layer_roster(
            ws, add_email="arch@acme.com", member_role="owner", title="CTO", squad="core"
        )
        r_mem = manage_layer_roster(ws, add_email="dev@acme.com", member_role="member")
        r_rem = manage_layer_roster(ws, remove_email="dev@acme.com")
        st_fallback = inspect_git_governance_state(ws)
        (ws / ".git").mkdir()

        def fake_run(cmd: list[str], **_kw: object) -> subprocess.CompletedProcess[str]:
            assert "rev-parse" in cmd
            return subprocess.CompletedProcess(cmd, 0, stdout="feature/SHM-01-sensor\n", stderr="")

        monkeypatch.setattr(subprocess, "run", fake_run)
        st_git = inspect_git_governance_state(ws)
        st_tst = inspect_git_governance_state(ws, current_branch="env/tst")
        st_pre = inspect_git_governance_state(ws, current_branch="pre/rc1")
        st_pro = inspect_git_governance_state(ws, current_branch="release/v1.0.0")
        prop_file = stage_non_destructive_proposal(
            ws,
            scope_tag="to-root",
            file_name="rule.md",
            content="# Rule",
            operation="promote-from-project",
        )
        st_with_prop = inspect_git_governance_state(ws, current_branch="custom/branch")
        old_ts = time.time() - (15 * 86_400)
        os.utime(prop_file, (old_ts, old_ts))
        st_stale_prop = inspect_git_governance_state(ws, current_branch="custom/branch")

        # Assert
        assert dry_cfg["dry_run"] is True and no_co_cfg["codeowners_file"] is None
        assert r_noop["roster"]["owners"] == []
        assert cfg_res["codeowners_owners"] == "lead@acme.com"
        assert r_dry["dry_run"] is True and r_val["validator_emails"] == ["qa@acme.com"]
        assert r_maint["maintainer_emails"] == ["maint@acme.com"]
        assert "arch@acme.com" in r_own["authorized_emails"]
        assert len(r_mem["roster"]["members"]) == 1
        assert r_rem["roster"]["members"] == []
        assert "/WORKVALI.md" in (ws / ".github/CODEOWNERS").read_text(encoding="utf-8")
        with pytest.raises(ValueError, match="Invalid member_role"):
            manage_layer_roster(ws, add_email="x@acme.com", member_role="admin")
        assert (
            st_fallback["current_branch"],
            st_fallback["is_protected_branch"],
            st_fallback["active_process_stage"],
            st_fallback["active_environment"],
        ) == ("main", True, "protected-main", "pro")
        assert (
            st_git["current_branch"],
            st_git["active_process_stage"],
            st_git["active_environment"],
        ) == ("feature/SHM-01-sensor", "feature", "dev")
        assert st_tst["active_environment"] == "tst"
        assert st_pre["active_environment"] == "pre"
        assert st_pro["active_environment"] == "pro" and st_pro["is_protected_branch"] is False
        assert st_with_prop["staged_proposals"] == [".agents/proposals/to-root/rule.md"]
        assert st_with_prop["stale_proposals"] == []
        assert st_stale_prop["stale_proposals"] == [".agents/proposals/to-root/rule.md"]
        assert st_stale_prop["staleness_thresholds_days"] == {
            "proposals": 14,
            "modules_and_specs": 90,
            "policies": 180,
        }
        assert len(st_with_prop["recent_governance_alerts"]) == 1

    def test_evaluate_environment_promotion_and_record_decisions(self, tmp_path: Path) -> None:
        """Enforce dev -> tst -> pre -> pro promotion gates and record human review decisions."""
        # Arrange
        ws = tmp_path / "corp-root"
        (ws / "system").mkdir(parents=True)
        (ws / "system/mcp-layer.json").write_text(
            json.dumps(
                {
                    "layer_id": "corp-root",
                    "layer_role": "corporate",
                    "layer_authority": {
                        "authorized_emails": ["ceo@acme.com"],
                        "validator_emails": ["qa@acme.com"],
                    },
                }
            ),
            encoding="utf-8",
        )
        (ws / "WORKTASK.md").write_text("- [ ] **[P0]**: Fix blocker\n", encoding="utf-8")
        (ws / "WORKVALI.md").write_text("- [ ] Verify E2E suite\n", encoding="utf-8")

        # Act
        dev_ok = evaluate_environment_promotion(ws, target_env="dev")
        tst_fail = evaluate_environment_promotion(ws, target_env="tst")
        (ws / "WORKTASK.md").write_text("- [x] **[P0]**: Fix blocker", encoding="utf-8")
        tst_ok = evaluate_environment_promotion(ws, target_env="tst")
        pre_fail = evaluate_environment_promotion(
            ws, target_env="pre", actor_email="intruder@acme.com"
        )
        (ws / "WORKVALI.md").write_text("- [x] Verify E2E suite\n", encoding="utf-8")
        pre_ok = evaluate_environment_promotion(ws, target_env="pre", actor_email="qa@acme.com")
        pro_fail = evaluate_environment_promotion(ws, target_env="pro", actor_email="dev@acme.com")
        (ws / "CHANGELOG.md").write_text("# Changelog\n", encoding="utf-8")
        pro_ok = evaluate_environment_promotion(ws, target_env="pro", actor_email="ceo@acme.com")

        dec_dry = record_governance_decision(
            ws,
            item_ref=".agents/proposals/to-root/rule.md",
            decision="defer",
            reason="Wait for Q4",
            dry_run=True,
        )
        dec_app = record_governance_decision(
            ws,
            item_ref=".agents/proposals/to-root/rule.md",
            decision="approve",
            reason="Validated by architecture board",
            actor_email="ceo@acme.com",
        )
        dec_dup = record_governance_decision(
            ws,
            item_ref=".agents/proposals/to-root/rule.md",
            decision="approve",
            reason="Validated by architecture board",
            actor_email="ceo@acme.com",
        )
        dec_rej = record_governance_decision(
            ws,
            item_ref="roadmaps/q3.md",
            decision="reject",
            reason="Superseded by Q4 plan",
            tracker="NEW_TRACKER.md",
        )

        # Assert
        assert dev_ok["allowed"] is True and dev_ok["git_promotion_command"] == ""
        assert tst_fail["allowed"] is False and "OPEN_P0_WORKTASKS" in tst_fail["failed_gates"][0]
        assert tst_ok["allowed"] is True and tst_ok["required_branch"] == "env/tst"
        assert pre_fail["allowed"] is False and len(pre_fail["failed_gates"]) == 2
        assert pre_ok["allowed"] is True and "WORKVALI.md" in pre_ok["phase_semantics"]
        assert pro_fail["allowed"] is False and len(pro_fail["failed_gates"]) == 2
        assert pro_ok["allowed"] is True and pro_ok["required_branch"] == "main"
        assert dec_dry["dry_run"] is True and dec_app["status"] == "approved"
        assert dec_dup["recorded_entry"] == dec_app["recorded_entry"]
        assert dec_rej["status"] == "rejected" and (ws / "NEW_TRACKER.md").is_file()
        with pytest.raises(ValueError, match="Invalid target_env"):
            evaluate_environment_promotion(ws, target_env="prod")
        with pytest.raises(ValueError, match="Invalid decision"):
            record_governance_decision(ws, item_ref="x", decision="maybe", reason="r")
        with pytest.raises(ValueError, match="Both item_ref and reason"):
            record_governance_decision(ws, item_ref="  ", decision="approve", reason="r")

    def test_reconcile_template_pack_sync_supports_all_four_strategies(
        self, tmp_path: Path
    ) -> None:
        """Reconcile upstream vs local template packs via reconcile, keep-local, merge, accept."""
        # Arrange
        ws = tmp_path / "corp-root"
        (ws / "system").mkdir(parents=True)
        (ws / "system/mcp-layer.json").write_text(
            '{"schema_version": "1.0", "layer_id": "corp-root", "layer_role": "team"}',
            encoding="utf-8",
        )
        (ws / "Makefile").write_text(
            "# Role-Specialized Layer Makefile — corp-root\nhelp:\n\t@echo ok\n",
            encoding="utf-8",
        )
        src_tpl = tmp_path / "upstream/templates/business-base"
        dest_tpl = ws / "templates/business-base"
        (src_tpl / "rules").mkdir(parents=True)
        (dest_tpl / "rules").mkdir(parents=True)
        (src_tpl / "rules/business-base.md").write_text(
            "# Business Base\n\n## Core Rule\nUpstream v2.\n", encoding="utf-8"
        )
        (dest_tpl / "rules/business-base.md").write_text(
            "Preamble line\n# Business Base\n\n## Core Rule\nLocal v1.\n\n## Local Annex\nKeep.\n",
            encoding="utf-8",
        )
        (dest_tpl / "rules/same.md").write_text("## Shared\nSame.\n", encoding="utf-8")
        (src_tpl / "rules/same.md").write_text("## Shared\nSame.\n", encoding="utf-8")
        src_grouped = tmp_path / "upstream/templates/tech-stack/fastapi-hexagonal"
        (src_grouped / "rules").mkdir(parents=True)
        (src_grouped / "rules/coding.md").write_text("# Coding\n\n## Core\nUp.\n", encoding="utf-8")
        flat_leg = ws / "templates/fastapi-hexagonal"
        (flat_leg / "rules").mkdir(parents=True)
        (flat_leg / "rules/coding.md").write_text(
            "# Coding\n\n## Core\nOld.\n\n## Custom Hex\nLocal.\n", encoding="utf-8"
        )
        dest_grouped = ws / "templates/tech-stack/fastapi-hexagonal"

        # Act
        st_outdated = inspect_git_governance_state(ws)
        rec_copied, rec_conflicts = reconcile_template_pack_sync(
            ws,
            "business-base",
            src_tpl,
            dest_tpl,
            strategy="reconcile",
            is_local_newer=True,
        )
        keep_dry, _ = reconcile_template_pack_sync(
            ws,
            "business-base",
            src_tpl,
            dest_tpl,
            strategy="keep-local",
            is_local_newer=True,
            dry_run=True,
        )
        keep_live, _ = reconcile_template_pack_sync(
            ws,
            "business-base",
            src_tpl,
            dest_tpl,
            strategy="keep-local",
            is_local_newer=True,
        )
        reconcile_template_pack_sync(
            ws,
            "business-base",
            src_tpl,
            dest_tpl,
            strategy="reconcile",
            is_local_newer=True,
        )
        merge_copied, merge_conflicts = reconcile_template_pack_sync(
            ws,
            "business-base",
            src_tpl,
            dest_tpl,
            strategy="merge",
            is_local_newer=True,
        )
        merged_txt = (dest_tpl / "rules/business-base.md").read_text(encoding="utf-8")
        acc_copied, _ = reconcile_template_pack_sync(
            ws,
            "business-base",
            src_tpl,
            dest_tpl,
            strategy="accept-upstream",
            is_local_newer=True,
        )
        acc_txt = (dest_tpl / "rules/business-base.md").read_text(encoding="utf-8")
        grp_copied, _ = reconcile_template_pack_sync(
            ws,
            "fastapi-hexagonal",
            src_grouped,
            dest_grouped,
            strategy="merge",
            is_local_newer=True,
        )
        grp_txt = (dest_grouped / "rules/coding.md").read_text(encoding="utf-8")

        # Assert
        assert st_outdated["makefile_outdated"] is True
        assert st_outdated["manifest_contracts_outdated"] is True
        assert rec_copied is False and len(rec_conflicts) == 2
        assert keep_dry is False and keep_live is False
        assert not list((ws / ".agents/proposals/from-upstream").glob("*.md"))
        assert merge_copied is True and merge_conflicts == []
        assert "Upstream v2." in merged_txt and "## Local Annex" in merged_txt
        assert acc_copied is True and "## Local Annex" not in acc_txt
        assert grp_copied is True and not flat_leg.exists() and "## Custom Hex" in grp_txt
