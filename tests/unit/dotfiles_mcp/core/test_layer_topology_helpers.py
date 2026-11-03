"""Unit tests for layer_topology_helpers (parent/child resolution, Makefile, and subtree sync).

Specification: docs/architecture/03_contextual_mcp_and_federation.md
"""

from __future__ import annotations

import os
import subprocess
from typing import TYPE_CHECKING

from dotfiles_mcp.core import layer_topology_helpers, manifest_helpers

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


class TestLayerTopologyHelpers:
    """Verify parent/child topology discovery, Makefile rendering, and mounted subtree sync."""

    def test_is_dest_template_newer_and_mounted_child_drift_sync(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Detect newer destination templates and synchronize mounted child layers from siblings."""
        # Arrange
        src_tpl = tmp_path / "src_repo/templates/src_tpl"
        dest_tpl = tmp_path / "dest_tpl"
        newer_missing = layer_topology_helpers._is_dest_template_newer(src_tpl, dest_tpl)
        (src_tpl / "rules").mkdir(parents=True)
        (dest_tpl / "rules").mkdir(parents=True)
        src_rf = src_tpl / "rules/base.md"
        dest_rf = dest_tpl / "rules/base.md"
        (dest_tpl / "rules/extra.md").write_text("# extra\n", encoding="utf-8")
        src_rf.write_text("# v1\n", encoding="utf-8")
        dest_rf.write_text("# v2\n", encoding="utf-8")
        os.utime(src_rf, ns=(1_000_000_000, 1_000_000_000))
        os.utime(dest_rf, ns=(2_000_000_000, 2_000_000_000))
        newer_true = layer_topology_helpers._is_dest_template_newer(src_tpl, dest_tpl)
        os.utime(dest_rf, ns=(1_000_000_000, 1_000_000_000))
        newer_equal = layer_topology_helpers._is_dest_template_newer(src_tpl, dest_tpl)
        (tmp_path / "src_repo/.git").mkdir(parents=True)
        monkeypatch.setattr(
            subprocess,
            "run",
            lambda cmd, **kw: subprocess.CompletedProcess(cmd, returncode=0),
        )
        newer_git_historical = layer_topology_helpers._is_dest_template_newer(src_tpl, dest_tpl)
        monkeypatch.setattr(
            subprocess,
            "run",
            lambda cmd, **kw: subprocess.CompletedProcess(cmd, returncode=1),
        )
        newer_git_local_blob = layer_topology_helpers._is_dest_template_newer(src_tpl, dest_tpl)
        src_sha = manifest_helpers._sha256_file(src_rf)
        (dest_tpl / "template.json").write_text(
            f'{{"reconciled_upstream_sha256": {{"base.md": "{src_sha}"}}}}',
            encoding="utf-8",
        )
        newer_reconciled = layer_topology_helpers._is_dest_template_newer(src_tpl, dest_tpl)

        parent_ws = tmp_path / "corp-root"
        (parent_ws / "system").mkdir(parents=True)
        (parent_ws / "system/mcp-layer.json").write_text(
            '{"layer_id": "corp-root"}', encoding="utf-8"
        )
        (parent_ws / "templates/business-base/rules").mkdir(parents=True)
        (parent_ws / "templates/business-base/rules/business-base.md").write_text(
            "# Parent v2\n", encoding="utf-8"
        )
        (parent_ws / "templates/business-base/rules/extra-policy.md").write_text(
            "# Extra\n", encoding="utf-8"
        )
        mounted_child = parent_ws / "layers/dept-alpha"
        (mounted_child / "system").mkdir(parents=True)
        (mounted_child / "system/mcp-layer.json").write_text(
            '{"schema_version": "1.0", "layer_id": "dept-alpha"}', encoding="utf-8"
        )
        (mounted_child / "Makefile").write_text(
            "# Role-Specialized Layer Makefile — dept-alpha (department)\nstatus:\n\t@true\n",
            encoding="utf-8",
        )
        (mounted_child / "templates/business-base/rules").mkdir(parents=True)
        (mounted_child / "templates/business-base/template.json").write_text(
            '{"schema_version": "1.0"}', encoding="utf-8"
        )
        (mounted_child / "templates/business-base/rules/business-base.md").write_text(
            "# Old v1\n", encoding="utf-8"
        )
        (mounted_child / "templates/dept-alpha/rules").mkdir(parents=True)
        (mounted_child / ".agents/rules").mkdir(parents=True)
        (mounted_child / ".agents/rules/business-base.md").write_text(
            "# Old v1\n", encoding="utf-8"
        )

        org_child = tmp_path / "corp-root-org/dept-beta-repo"
        (org_child / "system").mkdir(parents=True)
        (org_child / "system/mcp-layer.json").write_text(
            '{"layer_id": "dept-beta"}', encoding="utf-8"
        )
        (org_child / "WORKTASK.md").write_text("# Untouched External Repo\n", encoding="utf-8")
        direct_sib = tmp_path / "dept-direct"
        (direct_sib / "system").mkdir(parents=True)
        (direct_sib / "system/mcp-layer.json").write_text(
            '{"layer_id": "dept-direct"}', encoding="utf-8"
        )
        mounted_entries: list[object] = [
            "invalid",
            {"name": ""},
            {"name": "dept-missing"},
            {"name": "dept-alpha", "branch": "master"},
        ]

        # Act
        missing_resolved = layer_topology_helpers._resolve_mounted_child_dir(
            parent_ws, "dept-missing"
        )
        direct_resolved = layer_topology_helpers._resolve_mounted_child_dir(
            parent_ws, "dept-direct"
        )
        beta_resolved = layer_topology_helpers._resolve_mounted_child_dir(parent_ws, "dept-beta")
        explicit_parent = layer_topology_helpers._resolve_default_parent_dir(
            mounted_child, parent_ws
        )
        mounted_parent = layer_topology_helpers._resolve_default_parent_dir(mounted_child, None)
        (org_child / "Makefile").write_text(f"PARENT_DIR ?= {parent_ws}\n", encoding="utf-8")
        mk_parent = layer_topology_helpers._resolve_default_parent_dir(org_child, None)
        (direct_sib / "Makefile").write_text(f"PARENT_DIR ?= {direct_sib}\n", encoding="utf-8")
        self_parent = layer_topology_helpers._resolve_default_parent_dir(direct_sib, None)
        drifts_before = layer_topology_helpers._inspect_mounted_children_drifts(
            parent_ws, mounted_entries
        )
        dry_synced = layer_topology_helpers._sync_mounted_children_into_parent(
            parent_ws, mounted_entries, dry_run=True
        )
        rule_after_dry = (
            mounted_child / "templates/business-base/rules/business-base.md"
        ).read_text(encoding="utf-8")
        live_synced = layer_topology_helpers._sync_mounted_children_into_parent(
            parent_ws, mounted_entries, dry_run=False
        )
        drifts_after = layer_topology_helpers._inspect_mounted_children_drifts(
            parent_ws, mounted_entries
        )
        (mounted_child / "templates/business-base/rules/business-base.md").write_text(
            "# Old v1\n", encoding="utf-8"
        )
        layer_topology_helpers._sync_mounted_children_into_parent(
            parent_ws, mounted_entries, dry_run=False
        )

        # Assert
        assert newer_missing is False
        assert newer_true is True
        assert newer_equal is False
        assert newer_git_historical is False
        assert newer_git_local_blob is True
        assert newer_reconciled is True
        assert missing_resolved is None
        assert direct_resolved == direct_sib.resolve()
        assert beta_resolved == org_child.resolve()
        assert explicit_parent == parent_ws
        assert mounted_parent == parent_ws.resolve()
        assert mk_parent == parent_ws.resolve()
        assert self_parent is None
        assert len(drifts_before) == 1
        assert "system/mcp-layer.json" in drifts_before[0]["drift_files"]
        assert "Makefile" in drifts_before[0]["drift_files"]
        assert "templates/business-base/template.json" in drifts_before[0]["drift_files"]
        assert "templates/business-base/rules/business-base.md" in drifts_before[0]["drift_files"]
        assert (
            drifts_before[0]["subtree_push_command"]
            == "./scripts/layer-subtree.sh push dept-alpha master"
        )
        assert dry_synced == ["dept-alpha"]
        assert rule_after_dry == "# Old v1\n"
        assert live_synced == ["dept-alpha"]
        assert "--strategy $(STRATEGY)" in (mounted_child / "Makefile").read_text(encoding="utf-8")
        assert (mounted_child / "templates/business-base/rules/business-base.md").read_text(
            encoding="utf-8"
        ) == "# Parent v2\n"
        assert (mounted_child / ".agents/rules/business-base.md").read_text(
            encoding="utf-8"
        ) == "# Parent v2\n"
        assert (org_child / "WORKTASK.md").read_text(
            encoding="utf-8"
        ) == "# Untouched External Repo\n"
        assert drifts_after == []

    def test_render_layer_onboarding_readme_and_lineage_markdown_cover_all_tiers(
        self, tmp_path: Path
    ) -> None:
        """Render role-specific Layer Setup Blueprints and Level 4 Project Lineage prompts."""
        # Arrange
        corp_args = ("corp-root", "corporate", 10, "corp-root", ["business-base"], None)
        dept_args: tuple[str, str, int, str, list[str], str] = (
            "dept-eng",
            "department",
            30,
            "dept-eng",
            [],
            "corp-root",
        )
        squad_args = ("squad-api", "squad", 50, "squad-api", ["technical-base"], "dept-eng")

        # Act
        corp_md = layer_topology_helpers._render_layer_onboarding_readme(*corp_args)
        dept_md = layer_topology_helpers._render_layer_onboarding_readme(*dept_args)
        squad_md = layer_topology_helpers._render_layer_onboarding_readme(*squad_args)
        lineage_md = layer_topology_helpers._render_lineage_markdown(
            "technical-base", ["| `50` | `root` | `squad-api` | `squad` | `1` |"]
        )
        missing_child = layer_topology_helpers._resolve_mounted_child_dir(
            tmp_path / "nonexistent-sub/nonexistent-ws", "missing-child"
        )

        # Assert
        assert missing_child is None
        assert "Level 1 — Root 0" in corp_md
        assert "`open-source-root`" in corp_md
        assert "Human-Stack Profile (Optional)" in corp_md
        assert "Level 2 — Department" in dept_md
        assert "`none`" in dept_md
        assert "Level 3 — Squad, Case & Operational Unit Governance" in squad_md
        assert "apply-project commands" in squad_md
        assert "Project Setup Blueprint (Level 4" in lineage_md
        assert "Human-Stack Profile (Optional)" in lineage_md
        assert "Initial Chat Kickoff Prompt" in lineage_md

    def test_match_manifest_actor_role_and_hierarchical_actor_profile(self, tmp_path: Path) -> None:
        """Resolve local/upstream roles, read-only inheritance, and hierarchical authority."""
        # Arrange
        parent_ws, child_ws = tmp_path / "dept-it", tmp_path / "squad-web"
        for d in (parent_ws, child_ws):
            (d / "system").mkdir(parents=True)
        (parent_ws / "system/mcp-layer.json").write_text(
            '{"layer_id": "dept-it", "layer_role": "department", "precedence": 30, '
            '"layer_authority": {"authorized_emails": ["lead@it.acme.com"]}}',
            encoding="utf-8",
        )
        (child_ws / "system/mcp-layer.json").write_text(
            '{"layer_id": "squad-web", "layer_role": "squad", "precedence": 50, '
            '"layer_authority": {"roster": {"members": [{"email": "dev@web.acme.com"}]}}}',
            encoding="utf-8",
        )

        # Act
        p_member = layer_topology_helpers._resolve_hierarchical_actor_profile(
            child_ws, actor_email="dev@web.acme.com", parent_dir=parent_ws
        )
        p_up_owner = layer_topology_helpers._resolve_hierarchical_actor_profile(
            child_ws, actor_email="lead@it.acme.com", parent_dir=parent_ws
        )
        p_consumer = layer_topology_helpers._resolve_hierarchical_actor_profile(
            child_ws, actor_email="", parent_dir=parent_ws
        )
        oss_parent = tmp_path / "oss-root"
        (oss_parent / "system").mkdir(parents=True)
        (oss_parent / "system/mcp-layer.json").write_text(
            '{"layer_id": "root", "layer_role": "root"}', encoding="utf-8"
        )
        p_oss_parent = layer_topology_helpers._resolve_hierarchical_actor_profile(
            child_ws, actor_email="lead@it.acme.com", parent_dir=oss_parent
        )

        # Assert
        assert p_oss_parent["hierarchical_authority_granted"] is False
        assert (
            p_member["local_role"],
            p_member["upstream_role"],
            p_member["upstream_read_only"],
            p_member["hierarchical_authority_granted"],
            p_member["effective_role"],
            p_member["allowed_environments"],
        ) == ("member", "consumer", True, False, "member", ["dev", "tst"])
        assert (
            p_up_owner["local_role"],
            p_up_owner["upstream_role"],
            p_up_owner["upstream_read_only"],
            p_up_owner["hierarchical_authority_granted"],
            p_up_owner["effective_role"],
            p_up_owner["allowed_environments"],
        ) == ("consumer", "owner", False, True, "owner", ["dev", "tst", "pre", "pro"])
        assert (
            p_consumer["effective_role"] == "consumer" and p_consumer["allowed_environments"] == []
        )
