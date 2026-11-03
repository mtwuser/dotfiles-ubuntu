"""Unit tests for horizon_engine (1-hop horizon radar, section diffing, and sync reconciliation).

Specification: docs/architecture/06_layer_governance_and_promotion_engines.md
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from dotfiles_mcp.core import manifest_helpers
from dotfiles_mcp.governance.git_governance_engine import inspect_git_governance_state
from dotfiles_mcp.governance.horizon_engine import (
    _parse_markdown_sections_map,
    compare_upstream_templates,
    inspect_layer_horizon,
    reconcile_template_pack_sync,
)
from dotfiles_mcp.governance.promotion_engine import promote_project_asset_to_layer

if TYPE_CHECKING:
    from pathlib import Path


class TestHorizonEngine:
    """Verify 1-hop horizon radar, section-level template diffing, and sync reconciliation."""

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
        _, rec_after_keep = reconcile_template_pack_sync(
            ws,
            "business-base",
            src_tpl,
            dest_tpl,
            strategy="reconcile",
            is_local_newer=True,
        )
        (src_tpl / "rules/business-base.md").write_text(
            "# Business Base\n\n## Core Rule\nUpstream v2.\n", encoding="utf-8"
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
        acc_dry, _ = reconcile_template_pack_sync(
            ws,
            "business-base",
            src_tpl,
            dest_tpl,
            strategy="accept-upstream",
            is_local_newer=True,
            dry_run=True,
        )
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
        assert rec_copied is False and len(rec_conflicts) == 1
        assert keep_dry is False and keep_live is False
        assert rec_after_keep == []
        assert not (ws / ".agents/proposals/from-upstream").exists()
        assert "Staged Governance Proposal" not in (ws / "WORKTASK.md").read_text(encoding="utf-8")
        assert "UPSTREAM_TEMPLATE_CONFLICT" not in (ws / ".agents/SESSION.md").read_text(
            encoding="utf-8"
        )
        assert merge_copied is True and merge_conflicts == []
        assert "Upstream v2." in merged_txt and "## Local Annex" in merged_txt
        assert acc_dry is True and acc_copied is True and "## Local Annex" not in acc_txt
        assert grp_copied is True and not flat_leg.exists() and "## Custom Hex" in grp_txt

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

    def test_inspect_layer_horizon_detects_upward_and_downward_drift(self, tmp_path: Path) -> None:
        """Inspect 1-hop horizon across OSS and internal parent layers with mtime cut-points."""
        # Arrange
        repo_dir, proj_dir, oss_dir = tmp_path / "fork", tmp_path / "proj", tmp_path / "oss"
        for sub in ("system", "templates/business-base/rules", "templates/business-base/assets"):
            (oss_dir / sub).mkdir(parents=True)
            (proj_dir / sub).mkdir(parents=True)
            (repo_dir / sub).mkdir(parents=True)
        (oss_dir / "VERSION").write_text("2.0.0\n", encoding="utf-8")
        (oss_dir / "system/mcp-layer.json").write_text(
            '{"layer_id":"root","layer_role":"root"}', encoding="utf-8"
        )
        for name, txt in (("business-base.md", "# v1\n"), ("same.md", "# s\n"), ("p.md", "# v1\n")):
            (oss_dir / "templates/business-base/rules" / name).write_text(txt, encoding="utf-8")
        (proj_dir / "VERSION").write_text("0.2.0\n", encoding="utf-8")
        (proj_dir / "system/mcp-layer.json").write_text(
            '{"layer_id":"corp-zyxwvut-root","layer_role":"corporate",'
            '"default_stack_templates":["business-base"],"upstream_layer":{"layer_id":"root"}}',
            encoding="utf-8",
        )
        for name, txt in (
            ("business-base.md", "# v2 universal\n"),
            ("same.md", "# s\n"),
            ("p.md", "# Mentions zyxwvut\n"),
        ):
            rf = proj_dir / "templates/business-base/rules" / name
            rf.write_text(txt, encoding="utf-8")
            ts = (oss_dir / "templates/business-base/rules" / name).stat().st_mtime_ns
            os.utime(rf, ns=(ts, ts))
        up_p_sha = manifest_helpers._sha256_file(oss_dir / "templates/business-base/rules/p.md")
        (proj_dir / "templates/business-base/template.json").write_text(
            f'{{"reconciled_upstream_sha256": {{"p.md": "{up_p_sha}"}}}}', encoding="utf-8"
        )
        (proj_dir / "templates/business-base/assets/a.md").write_text("# A\n", encoding="utf-8")
        (proj_dir / "WORKTASK.md").write_text(
            "- [ ] **[P1 · Delegated from `root`]**: Review policy\n"
            "- [/] **[P1]**: Local active task\n\n"
            "## Outbound Delegations\n"
            "- [x] **[TKT-1 -> `dept-legal` (`WORKTASK.md`, stage: `completed (pro)`)]**: Done\n",
            encoding="utf-8",
        )
        child_wt = proj_dir / "layers/dept-legal/WORKTASK.md"
        child_wt.parent.mkdir(parents=True)
        child_wt.write_text(
            "- [x] **[P1 · Delegated from `corp-zyxwvut-root`]**: Child done\n", encoding="utf-8"
        )

        # Act
        oss_tpl_res = promote_project_asset_to_layer(
            oss_dir, proj_dir, source_rel_path="templates/business-base/rules/business-base.md",
            upstream_dir=oss_dir, dry_run=True,
        )  # fmt: skip
        oss_asset_res = promote_project_asset_to_layer(
            oss_dir, proj_dir, source_rel_path="templates/business-base/assets/a.md",
            upstream_dir=oss_dir, dry_run=True,
        )  # fmt: skip
        hz_oss = inspect_layer_horizon(oss_dir, proj_dir)
        hz_int = inspect_layer_horizon(repo_dir, proj_dir, parent_dir=repo_dir)
        new_sk = oss_dir / "templates/business-base/skills/new-sk/SKILL.md"
        new_sk.parent.mkdir(parents=True)
        new_sk.write_text('---\nname: new-sk\ndescription: "ok"\n---\n', encoding="utf-8")
        hz_miss_sk = inspect_layer_horizon(oss_dir, proj_dir)
        up_b = oss_dir / "templates/business-base/rules/business-base.md"
        up_b.write_text("# v3 upstream\n", encoding="utf-8")
        os.utime(up_b, ns=(ts + 1_000_000, ts + 1_000_000))
        hz_after_up = inspect_layer_horizon(oss_dir, proj_dir)

        # Assert
        assert (
            oss_tpl_res["target_template"] == "business-base"
            and oss_asset_res["destination"] == "templates/business-base/assets/a.md"
        )
        assert (
            hz_oss["is_oss_community_horizon"],
            hz_oss["downward_sync_needed"],
            len(hz_oss["upward_promotion_suggestions"]),
        ) == (True, False, 1)
        assert hz_oss["oss_contrib_dir"] is not None and hz_int["is_oss_community_horizon"] is False
        assert (
            hz_int["oss_contrib_dir"] is None and len(hz_int["upward_promotion_suggestions"]) >= 1
        )
        assert (
            hz_miss_sk["downward_sync_needed"] is True
            and hz_after_up["downward_sync_needed"] is True
        )
