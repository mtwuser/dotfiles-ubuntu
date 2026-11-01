"""1:1 unit tests for scripts/dotfiles_mcp/workflow_engine.py.

Specification: docs/architecture/04_compaction_surface_and_promotion_engines.md
"""

from pathlib import Path

import pytest
from dotfiles_mcp.workflow_engine import (
    _derive_branch_slug,
    _parse_markdown_sections_map,
    compare_upstream_templates,
    complete_task_workflow,
    consult_layer_ephemeral,
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
            "- [ ] Follow up local refactor\n",
            encoding="utf-8",
        )

        # Act
        dry_res = start_task_workflow(ws, task_query="TECH-042", dry_run=True)
        dry_session_exists = (ws / ".agents/SESSION.md").exists()
        live_res = start_task_workflow(ws, task_query="TECH-042", dry_run=False)
        second_res = start_task_workflow(ws, task_query="local refactor", dry_run=False)

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
        assert "- [/] **[P0" in wt_text and "- [/] Follow up local refactor" in wt_text
        session_text = (ws / ".agents/SESSION.md").read_text(encoding="utf-8")
        assert session_text.count("## Active Task") == 1
        assert "feature/follow-up-local-refactor" in session_text
        assert second_res["task_status"] == "in_progress" and second_res["ticket_id"] == ""
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

    def test_parse_markdown_sections_map_and_compare_upstream_templates(
        self, tmp_path: Path
    ) -> None:
        """Compare upstream vs local sections and safely apply upstream-only additions."""
        # Arrange
        up_dir, ws_dir = tmp_path / "upstream", tmp_path / "workspace"
        for d, lid in ((up_dir, "oss-root"), (ws_dir, "corp-root")):
            (d / "system").mkdir(parents=True)
            (d / "system/mcp-layer.json").write_text(
                f'{{"layer_id":"{lid}","default_stack_templates":["business-base","missing-tpl"]}}',
                encoding="utf-8",
            )
            (d / "templates/business-base/rules").mkdir(parents=True)
        (up_dir / "templates/business-base/rules/sync.md").write_text(
            "---\ntrigger: always_on\n---\n# Sync\nSame body\n", encoding="utf-8"
        )
        (ws_dir / "templates/business-base/rules/sync.md").write_text(
            "# Sync\nSame body\n", encoding="utf-8"
        )
        (up_dir / "templates/business-base/rules/up-only.md").write_text(
            "Preamble line\n# New Upstream File\nBody\n", encoding="utf-8"
        )
        (ws_dir / "templates/business-base/rules/loc-only.md").write_text(
            "# Local File\nLocal body\n", encoding="utf-8"
        )
        (up_dir / "templates/business-base/rules/mixed.md").write_text(
            "# Core\nSame\n\n## Diverged\nUpstream v2\n\n## Upstream Added\nNew rule\n",
            encoding="utf-8",
        )
        (ws_dir / "templates/business-base/rules/mixed.md").write_text(
            "# Core\nSame\n\n## Diverged\nLocal v1\n\n## Local Custom\nCustom rule\n",
            encoding="utf-8",
        )
        (up_dir / "templates/business-base/rules/add-only.md").write_text(
            "# Base\nSame\n\n## Extra\nAdded\n", encoding="utf-8"
        )
        (ws_dir / "templates/business-base/rules/add-only.md").write_text(
            "# Base\nSame\n", encoding="utf-8"
        )
        (up_dir / "templates/business-base/rules/loc-sec.md").write_text(
            "# Base\nSame\n", encoding="utf-8"
        )
        (ws_dir / "templates/business-base/rules/loc-sec.md").write_text(
            "# Base\nSame\n\n## Local Sec\nCustom\n", encoding="utf-8"
        )

        # Act
        empty_secs = _parse_markdown_sections_map("")
        ro_cmp = compare_upstream_templates(up_dir, ws_dir, apply_upstream_only=False)
        dry_cmp = compare_upstream_templates(
            up_dir,
            ws_dir,
            template_filter="business-base",
            apply_upstream_only=True,
            dry_run=True,
        )
        dry_up_existed = (ws_dir / "templates/business-base/rules/up-only.md").exists()
        live_cmp = compare_upstream_templates(
            up_dir, ws_dir, apply_upstream_only=True, dry_run=False
        )

        # Assert
        assert empty_secs == [] and ro_cmp["safe_applied_files"] == []
        assert dry_cmp["dry_run"] is True and dry_up_existed is False
        assert live_cmp["summary"]["files_compared"] == 6
        assert live_cmp["summary"]["in_sync_files"] == 1
        assert (ws_dir / "templates/business-base/rules/up-only.md").is_file()
        mixed_txt = (ws_dir / "templates/business-base/rules/mixed.md").read_text(encoding="utf-8")
        assert "## Upstream Added" in mixed_txt and "## Local Custom" in mixed_txt
        assert "Local v1" in mixed_txt
        by_file = {f["rule_file"].split("/")[-1]: f for f in live_cmp["file_comparisons"]}
        assert by_file["sync.md"]["recommended_action"] == "none"
        assert by_file["mixed.md"]["recommended_action"] == "review_diverged_sections"
        assert by_file["add-only.md"]["recommended_action"] == "adopt_upstream_sections"
        assert by_file["loc-sec.md"]["recommended_action"] == "keep_local_or_promote"

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
