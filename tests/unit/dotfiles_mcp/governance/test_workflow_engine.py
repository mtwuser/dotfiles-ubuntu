"""1:1 unit tests for scripts/dotfiles_mcp/governance/workflow_engine.py.

Specification: docs/architecture/06_layer_governance_and_promotion_engines.md
"""

from pathlib import Path

import pytest
from dotfiles_mcp.governance.workflow_engine import (
    _derive_branch_slug,
    complete_task_workflow,
    consult_layer_ephemeral,
    delegate_directive_to_child,
    start_task_workflow,
)


class TestWorkflowEngine:
    """Unit test suite for squad task-branch workflow onboarding and slug derivation."""

    def test_derive_branch_slug_normalizes_and_handles_empty_fallback(self) -> None:
        """Derive kebab-case branch slugs from decorated or empty task strings."""
        # Arrange
        delegated = (
            "**[P0 · LEGAL-2026-004 · Delegated from `dept-legal` (`department`)]**: Audit GDPR"
        )
        punct_only = "*** ``` ~~~"

        # Act
        slug_delegated = _derive_branch_slug(delegated, strip_ticket="LEGAL-2026-004")
        slug_raw = _derive_branch_slug(delegated)
        slug_empty = _derive_branch_slug(punct_only)

        # Assert
        assert slug_delegated == "audit-gdpr"
        assert slug_raw == "p0-legal-2026-004-audit-gdpr"
        assert slug_empty == "work-item"

    def test_start_task_workflow_claims_task_updates_session_and_validates(
        self, tmp_path: Path
    ) -> None:
        """Claim a WORKTASK.md item, mark it [/], update .agents/SESSION.md, and validate inputs."""
        # Arrange
        ws = tmp_path / "squad-web"
        (ws / "system").mkdir(parents=True)
        (ws / "system/mcp-layer.json").write_text(
            '{"layer_id":"squad-web","layer_role":"squad"}', encoding="utf-8"
        )
        (ws / "WORKTASK.md").write_text(
            "# Active Work Tasks — squad-web\n\n"
            "- [x] Initial bootstrap\n"
            "- [ ] **[P0 · TECH-042 · Delegated from `dept-tech` (`department`)]**: "
            "Build OAuth2 login\n"
            "  - [ ] Add PKCE verifier\n"
            "  - [ ] Write unit tests\n\n"
            "- [ ] Follow up `local` refactor\n",
            encoding="utf-8",
        )

        # Act
        dry_res = start_task_workflow(ws, task_query="TECH-042", dry_run=True)
        dry_session_exists = (ws / ".agents/SESSION.md").exists()
        live_res = start_task_workflow(ws, task_query="TECH-042", dry_run=False)
        second_res = start_task_workflow(
            ws, task_query="local refactor", ticket_id="WEB-101", dry_run=False
        )

        # Assert
        assert dry_res["dry_run"] is True and dry_session_exists is False
        assert live_res["layer_id"] == "squad-web" and live_res["layer_role"] == "squad"
        assert live_res["ticket_id"] == "TECH-042" and live_res["origin_layer_id"] == "dept-tech"
        assert live_res["branch_name"] == "feature/TECH-042-build-oauth2-login"
        assert (
            live_res["git_branch_command"] == "git checkout -b feature/TECH-042-build-oauth2-login"
        )
        assert live_res["subtasks"] == ["- [ ] Add PKCE verifier", "- [ ] Write unit tests"]
        wt_text = (ws / "WORKTASK.md").read_text(encoding="utf-8")
        assert (
            "- [/] **[P0" in wt_text and "- [/] **[WEB-101]** Follow up `local` refactor" in wt_text
        )
        session_text = (ws / ".agents/SESSION.md").read_text(encoding="utf-8")
        assert session_text.count("## Active Task") == 1
        assert "feature/WEB-101-follow-up-local-refactor" in session_text
        assert second_res["task_status"] == "in_progress" and second_res["ticket_id"] == "WEB-101"
        for bad_kw, err_pat in (
            ({"task_query": "   "}, "task_query must be a non-empty"),
            ({"task_query": "x", "tracker": "INVALID.md"}, "Invalid tracker"),
            ({"task_query": "x", "tracker": "BACKLOG.md"}, "Tracker file not found"),
            ({"task_query": "NONEXISTENT-999"}, "No task matching"),
        ):
            with pytest.raises(ValueError, match=err_pat):
                start_task_workflow(ws, **bad_kw)  # type: ignore[arg-type]

    def test_complete_task_workflow_updates_parent_and_stages_receipt(self, tmp_path: Path) -> None:
        """Complete a child task [x], update parent Outbound Delegations, or stage receipt."""
        # Arrange
        parent_dir, ws = tmp_path / "dept-tech", tmp_path / "squad-web"
        for d, lid, role in ((parent_dir, "dept-tech", "department"), (ws, "squad-web", "squad")):
            (d / "system").mkdir(parents=True)
            (d / "system/mcp-layer.json").write_text(
                f'{{"layer_id":"{lid}","layer_role":"{role}",'
                f'"upstream_layer":{{"layer_id":"dept-tech"}},'
                f'"layer_authority":{{"owner_role":"CTO","authorized_emails":["cto@acme.com"]}}}}',
                encoding="utf-8",
            )
        (parent_dir / "WORKTASK.md").write_text(
            "# Tasks — dept-tech\n\n## Outbound Delegations\n"
            "- [/] **[TECH-042 -> `squad-web` (`WORKTASK.md`, stage: `delegated`)]**: "
            "Build OAuth2 login\n",
            encoding="utf-8",
        )
        (ws / "WORKTASK.md").write_text(
            "# Active Work Tasks — squad-web\n"
            "- [/] **[P0 · TECH-042 · Delegated from `dept-tech` (`department`)]**: "
            "Build OAuth2 login\n"
            "- [/] **[P1 · TECH-043]**: Add PKCE tests\n",
            encoding="utf-8",
        )

        # Act
        dry_res = complete_task_workflow(
            ws,
            task_query="TECH-042",
            deliverable="src/auth.py",
            parent_dir=parent_dir,
            actor_email="cto@acme.com",
            dry_run=True,
        )
        auth_res = complete_task_workflow(
            ws,
            task_query="TECH-042",
            deliverable="src/auth.py",
            parent_dir=parent_dir,
            actor_email="cto@acme.com",
        )
        append_res = complete_task_workflow(
            ws,
            task_query="TECH-043",
            parent_dir=parent_dir,
            actor_email="cto@acme.com",
        )
        staged_res = complete_task_workflow(
            ws,
            task_query="TECH-042",
            actor_email="dev@acme.com",
            create_pr=True,
        )
        no_parent_res = complete_task_workflow(
            ws, task_query="TECH-042", parent_dir=tmp_path / "missing-parent"
        )

        # Assert
        assert dry_res["dry_run"] is True and auth_res["parent_tracker_updated"] is True
        assert append_res["parent_tracker_updated"] is True
        assert no_parent_res["parent_tracker_updated"] is False
        parent_txt = (parent_dir / "WORKTASK.md").read_text(encoding="utf-8")
        assert (
            "- [x] **[TECH-042 -> `squad-web` (`WORKTASK.md`, stage: `completed (pro)`)]**"
            in parent_txt
        )
        assert "TECH-043 -> `squad-web`" in parent_txt
        assert staged_res["staged_completion_receipt"] is not None
        assert Path(str(staged_res["staged_completion_receipt"])).is_file()
        for bad_kw, err_pat in (
            ({"task_query": " "}, "task_query must be a non-empty"),
            ({"task_query": "x", "tracker": "BAD.md"}, "Invalid tracker"),
            ({"task_query": "x", "tracker": "BACKLOG.md"}, "Tracker file not found"),
            ({"task_query": "MISSING-999"}, "No task matching"),
        ):
            with pytest.raises(ValueError, match=err_pat):
                complete_task_workflow(ws, **bad_kw)  # type: ignore[arg-type]

    def test_consult_layer_ephemeral_evaluates_and_auto_reaps(self, tmp_path: Path) -> None:
        """Spawn a one-shot strictly-read-only consultation fork, query rules, and auto-reap."""
        # Arrange
        root_dir, ws_dir = tmp_path / "root-repo", tmp_path / "workspace"
        dept_dir = ws_dir / "layers" / "dept-legal"
        for d, lid, role in (
            (root_dir, "oss-root", "workstation"),
            (ws_dir, "corp-root", "corporate"),
            (dept_dir, "dept-legal", "department"),
        ):
            (d / "system").mkdir(parents=True)
            (d / "system/mcp-layer.json").write_text(
                f'{{"layer_id":"{lid}","layer_role":"{role}","precedence":25,'
                f'"default_stack_templates":["business-base"],'
                f'"surface_bindings":[{{"binding_id":"legal-b","target_globs":["**"],'
                f'"rule_files":["templates/business-base/rules/legal.md"]}}]}}',
                encoding="utf-8",
            )
            (d / "templates/business-base/rules").mkdir(parents=True)
            (d / "templates/business-base/rules/legal.md").write_text(
                "# Legal Compliance\n\n## GDPR Retention\nAll PII must expire within 90 days.\n",
                encoding="utf-8",
            )

        # Act
        dry_res = consult_layer_ephemeral(
            root_dir, ws_dir, target_layer="dept-legal", query="GDPR", dry_run=True
        )
        parent_res = consult_layer_ephemeral(
            root_dir,
            dept_dir,
            target_layer="corp-root",
            query="GDPR",
            parent_dir=ws_dir,
            dry_run=True,
        )
        live_res = consult_layer_ephemeral(
            root_dir,
            ws_dir,
            target_layer="business-base",
            query="GDPR",
            target_path="corporate/policy.md",
            model_tier="flash",
            dry_run=False,
        )

        # Assert
        assert dry_res["dry_run"] is True and dry_res["auto_reaped"] is True
        assert dry_res["target_layer"] == "dept-legal"
        assert parent_res["resolved_target_dir"] == str(ws_dir.resolve())
        assert live_res["access_mode"] == "strictly-read-only"
        assert live_res["auto_reaped"] is True
        assert not Path(live_res["ephemeral_fork_id"]).exists()
        assert len(live_res["capsule_matches"]) == 1
        digest = live_res["four_channel_digest"]
        assert digest["channel_1_domain_state"]["access_mode"] == "strictly-read-only"
        assert digest["channel_4_actionable_delta"]["handback_contract"] == "4-channel-digest+rcap1"
        assert len(digest["channel_4_actionable_delta"]["capsule_tokens"]) == 1
        for bad_kw, err_pat in (
            ({"target_layer": "INVALID_ID", "query": "GDPR"}, "Invalid target_layer"),
            ({"target_layer": "dept-legal", "query": "   "}, "query must be a non-empty"),
            (
                {"target_layer": "dept-legal", "query": "GDPR", "model_tier": "ultra"},
                "Invalid model_tier",
            ),
            ({"target_layer": "unknown-layer", "query": "GDPR"}, "Target layer or template"),
        ):
            with pytest.raises(ValueError, match=err_pat):
                consult_layer_ephemeral(root_dir, ws_dir, **bad_kw)  # type: ignore[arg-type]

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
        (mnt_child / "system").mkdir(parents=True)
        (mnt_child / "system/mcp-layer.json").write_text(
            '{"layer_id":"dept-legal","layer_role":"department","precedence":30}',
            encoding="utf-8",
        )
        (sib_child / "system/mcp-layer.json").write_text("{}", encoding="utf-8")
        (sib_child / "WORKTASK.md").write_text("# Untouched Sibling", encoding="utf-8")

        # Act
        def _dlg(**kw: object) -> dict[str, object]:
            return delegate_directive_to_child(
                corp_dir,
                child_layer="dept-legal",
                actor_email="ceo@acme.com",
                **kw,  # type: ignore[arg-type]
            )

        dry_res = _dlg(directive="Audit Q3 compliance ledgers", priority="P0", dry_run=True)
        dry_existed = (mnt_child / "WORKTASK.md").exists()
        live_res = _dlg(
            directive="Audit Q3 compliance ledgers", source_rel_path="WORKROAD.md", priority="P0"
        )
        dup_res = _dlg(directive="Audit Q3 compliance ledgers", priority="P0")
        pr_res = _dlg(directive="Cross-owner directive", create_pr=True)
        road_dry = _dlg(source_rel_path="WORKROAD.md", tracker="roadmaps", dry_run=True)
        road_live = _dlg(source_rel_path="WORKROAD.md", tracker="roadmaps")
        road_staged = _dlg(source_rel_path="WORKROAD.md", tracker="roadmaps")
        road_forced = _dlg(source_rel_path="WORKROAD.md", tracker="roadmaps", force_overwrite=True)
        rule_dry = _dlg(directive="Enforce GDPR", tracker="rules", dry_run=True)
        rule_live = _dlg(directive="Enforce GDPR", tracker="rules")
        rule_staged = _dlg(directive="Enforce GDPR v2", tracker="rules")
        rule_forced = _dlg(directive="Enforce GDPR v2", tracker="rules", force_overwrite=True)
        (mnt_child / "system/mcp-layer.json").write_text(
            '{"layer_id":"dept-legal","layer_role":"department","precedence":30,'
            '"layer_authority":{"owner_role":"CLO","authorized_emails":["clo@acme.com"]}}',
            encoding="utf-8",
        )
        cross_owner = _dlg(directive="Separate owner directive")

        # Assert
        assert dry_res["dry_run"] is True and dry_existed is False
        assert road_dry["dry_run"] is True and rule_dry["dry_run"] is True
        assert len(live_res["updated_paths"]) == 1  # type: ignore[arg-type]
        assert live_res["delivery_mode"] == "direct_subtree"
        assert "Audit Q3 compliance ledgers" in (mnt_child / "WORKTASK.md").read_text("utf-8")
        assert (sib_child / "WORKTASK.md").read_text("utf-8") == "# Untouched Sibling"
        assert dup_res["delegated_entry"] == live_res["delegated_entry"]
        assert pr_res["delivery_mode"] == "proposal_pr" and len(pr_res["staged_proposals"]) == 1  # type: ignore[arg-type]
        assert cross_owner["actor_is_child_owner"] is False
        assert cross_owner["delivery_mode"] == "proposal_pr"
        assert (mnt_child / "roadmaps/WORKROAD.md").is_file() and road_live["tracker"] == "roadmaps"
        assert len(road_staged["staged_proposals"]) == 1  # type: ignore[arg-type]
        assert len(road_forced["updated_paths"]) == 1  # type: ignore[arg-type]
        assert (mnt_child / ".agents/rules/delegated-item.md").is_file() and rule_live[
            "tracker"
        ] == "rules"
        assert len(rule_staged["staged_proposals"]) == 1  # type: ignore[arg-type]
        assert len(rule_forced["updated_paths"]) == 2  # type: ignore[arg-type]
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
