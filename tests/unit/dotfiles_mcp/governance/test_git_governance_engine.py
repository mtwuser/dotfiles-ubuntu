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
from dotfiles_mcp.governance.git_governance_engine import (
    configure_git_governance_policy,
    evaluate_environment_promotion,
    inspect_git_governance_state,
    manage_layer_roster,
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

        def _fake_run(cmd: list[str], **_kw: object) -> subprocess.CompletedProcess[str]:
            assert "rev-parse" in cmd
            return subprocess.CompletedProcess(cmd, 0, stdout="feature/SHM-01-sensor\n", stderr="")

        monkeypatch.setattr(subprocess, "run", _fake_run)
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
