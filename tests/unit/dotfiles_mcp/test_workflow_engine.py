"""1:1 unit tests for scripts/dotfiles_mcp/workflow_engine.py.

Specification: docs/architecture/04_compaction_surface_and_promotion_engines.md
"""

from pathlib import Path

import pytest
from dotfiles_mcp.workflow_engine import _derive_branch_slug, start_task_workflow


class TestWorkflowEngine:
    """Unit test suite for squad task-branch workflow onboarding and slug derivation."""

    def test_derive_branch_slug_normalizes_and_handles_empty_fallback(self) -> None:
        """Derive kebab-case branch slugs from decorated or empty task strings."""
        # Arrange
        delegated = (
            "**[P0 · Delegated from `dept-legal` (`department`, `precedence: 25`)]**: "
            "[LEGAL-2026-004] Audit GDPR"
        )
        punct_only = "*** ``` ~~~"

        # Act
        slug_delegated = _derive_branch_slug(delegated)
        slug_empty = _derive_branch_slug(punct_only)

        # Assert
        assert slug_delegated == "p0-legal-2026-004-audit-gdpr"
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
            "- [ ] **[P0 · Delegated from `dept-tech` (`department`)]**: "
            "[TECH-042] Build OAuth2 login\n"
            "  - [ ] Add PKCE verifier\n"
            "  - [ ] Write unit tests\n\n"
            "- [ ] [TECH-043] Follow-up task\n",
            encoding="utf-8",
        )

        # Act
        dry_res = start_task_workflow(ws, task_query="TECH-042", dry_run=True)
        dry_session_exists = (ws / ".agents/SESSION.md").exists()
        live_res = start_task_workflow(ws, task_query="TECH-042", dry_run=False)
        second_res = start_task_workflow(ws, task_query="TECH-043", dry_run=False)

        # Assert
        assert dry_res["dry_run"] is True and dry_session_exists is False
        assert live_res["layer_id"] == "squad-web" and live_res["layer_role"] == "squad"
        assert live_res["branch_name"] == "task/p0-tech-042-build-oauth2-login"
        assert (
            live_res["git_branch_command"] == "git checkout -b task/p0-tech-042-build-oauth2-login"
        )
        assert live_res["subtasks"] == ["- [ ] Add PKCE verifier", "- [ ] Write unit tests"]
        wt_text = (ws / "WORKTASK.md").read_text(encoding="utf-8")
        assert "- [/] **[P0" in wt_text and "- [/] [TECH-043]" in wt_text
        session_text = (ws / ".agents/SESSION.md").read_text(encoding="utf-8")
        assert session_text.count("## Active Task") == 1
        assert "task/tech-043-follow-up-task" in session_text
        assert second_res["task_status"] == "in_progress"
        for bad_kw, err_pat in (
            ({"task_query": "   "}, "task_query must be a non-empty"),
            ({"task_query": "x", "tracker": "INVALID.md"}, "Invalid tracker"),
            ({"task_query": "x", "tracker": "BACKLOG.md"}, "Tracker file not found"),
            ({"task_query": "NONEXISTENT-999"}, "No task matching"),
        ):
            with pytest.raises(ValueError, match=err_pat):
                start_task_workflow(ws, **bad_kw)  # type: ignore[arg-type]
