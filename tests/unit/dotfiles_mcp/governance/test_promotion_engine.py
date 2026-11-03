"""Unit tests for dotfiles_mcp/governance/promotion_engine.py (TestPromotionEngine).

Specification: docs/architecture/04_compaction_surface_and_promotion_engines.md
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
from dotfiles_mcp.core.constants import REPO_DIR
from dotfiles_mcp.governance.promotion_engine import (
    diff_project_against_layers,
    promote_project_asset_to_layer,
)
from dotfiles_mcp.mcp_node.server import DotfilesMCPServer

if TYPE_CHECKING:
    from pathlib import Path


class TestPromotionEngine:
    """Verify multi-layer pattern comparison, project diffing, and upward promotion."""

    def test_compare_project_patterns_multilayer_routes_novel_items_and_filters_materialized(
        self,
        tmp_path: Path,
    ) -> None:
        """Scan root and mounted layers, ignore layer-NN-*.md, and route novel promotions."""
        # Arrange
        for sub in (
            "system",
            "antigravity/.gemini/config/skills/root-sk",
            "templates/web-starter/rules",
            "templates/web-starter/skills/start",
            "templates/.hidden",
            "layers/dept-legal/system",
            "layers/dept-design/system",
            "layers/dept-design/templates/brand-ui/rules",
        ):
            (tmp_path / sub).mkdir(parents=True)
        for rel, txt in (
            (
                "system/mcp-layer.json",
                '{"schema_version":"mcp-layer-v1","layer_id":"acme-corp","layer_role":"corporate",'
                '"default_stack_templates":["web-starter"]}',
            ),
            (
                "antigravity/.gemini/config/skills/root-sk/SKILL.md",
                "---\nname: root-sk\ndescription: r\n---\n",
            ),
            ("templates/web-starter/rules/coding.md", "# Code\n"),
            (
                "templates/web-starter/skills/start/SKILL.md",
                "---\nname: start\ndescription: s\n---\n",
            ),
            ("templates/file.txt", "x"),
            (
                "layers/dept-legal/system/mcp-layer.json",
                '{"schema_version":"mcp-layer-v1","layer_id":"acme-legal","layer_role":"domain-policy",'
                '"surface_bindings":[{"binding_id":"gdpr-b","scopes":["*","checkout"],'
                '"traits":["*","pii"]}]}',
            ),
            (
                "layers/dept-design/system/mcp-layer.json",
                '{"schema_version":"mcp-layer-v1","layer_id":"ab-sec","layer_role":"department",'
                '"default_stack_templates":["brand-ui"]}',
            ),
        ):
            (tmp_path / rel).write_text(txt, encoding="utf-8")
        server = DotfilesMCPServer(repo_dir=tmp_path)

        # Act
        p_rules = [
            "coding.md",
            "layer-05-dept-legal.md",
            "checkout-pii.md",
            "sec-tokens.md",
            "ab-arch.md",
        ]
        all_resp = json.loads(
            server.call_tool(
                "compare_layer_patterns",
                {
                    "layer": "all",
                    "project_rules": p_rules,
                    "project_skills": ["start", "legal-audit", "global-helper"],
                },
            )["content"][0]["text"]
        )
        single_resp = json.loads(
            server.call_tool(
                "compare_layer_patterns",
                {
                    "layer": "dept-legal",
                    "project_rules": ["unmatched-rule.md"],
                    "project_skills": [],
                },
            )["content"][0]["text"]
        )

        # Assert
        assert all_resp["compared_against_layer"] == "all"
        assert all_resp["materialized_layer_rules"] == ["layer-05-dept-legal.md"]
        assert all_resp["already_in_layer_b_templates"]["rules"] == ["coding.md"]
        routes = {r["item"]: r for r in all_resp["promotion_routing"]}
        assert routes["checkout-pii.md"]["target_layer"] == "dept-legal"
        assert "AGENTS.md" in routes["checkout-pii.md"]["target_destination"]
        assert routes["sec-tokens.md"]["target_layer"] == "dept-design"
        assert "templates/brand-ui/rules/" in routes["sec-tokens.md"]["target_destination"]
        assert routes["ab-arch.md"]["target_layer"] == "root"
        assert routes["ab-arch.md"]["target_scope"] == "template-pack:root:web-starter"
        assert routes["legal-audit"]["target_layer"] == "dept-legal"
        assert routes["global-helper"]["target_scope"] == "global-skills-root"
        assert single_resp["compared_against_layer"] == "acme-legal"
        assert single_resp["promotion_routing"][0]["target_scope"] == "global-agents-root"

    def test_diff_project_against_layers_detects_in_sync_modified_and_novel(
        self,
        tmp_path: Path,
    ) -> None:
        """Compare SHA-256 hashes between consumer project .agents/ and fork layers."""
        # Arrange
        repo_dir, proj_dir = tmp_path / "fork", tmp_path / "proj"
        for sub in (
            "templates/base/rules",
            "templates/base/skills/sopen",
            "templates/base/assets/sub",
            "templates/.hidden",
            "antigravity/.gemini/config/skills/release",
            "layers/dept-legal/antigravity/.gemini/config",
            "layers/dept- sync/antigravity/.gemini/config",
            "layers/dept-sync/antigravity/.gemini/config",
            "layers/.hidden",
        ):
            (repo_dir / sub).mkdir(parents=True)
        for rel, txt in (
            ("templates/base/rules/coding.md", "v1\n"),
            ("templates/base/rules/testing.md", "t1\n"),
            ("templates/base/assets/sub/snippet.md", "asset-v1\n"),
            ("templates/base/skills/sopen/SKILL.md", "---\nname: sopen\ndescription: s\n---\n"),
            (
                "antigravity/.gemini/config/skills/release/SKILL.md",
                "---\nname: release\ndescription: r\n---\n",
            ),
            ("antigravity/.gemini/config/AGENTS.md", "# Root v1\n"),
            ("layers/dept-legal/antigravity/.gemini/config/AGENTS.md", "# Legal v1\n"),
            ("layers/dept-sync/antigravity/.gemini/config/AGENTS.md", "# Sync v1\n"),
        ):
            (repo_dir / rel).write_text(txt, encoding="utf-8")
        for sub in (
            ".agents/rules",
            ".agents/skills/sopen",
            ".agents/skills/release",
            ".agents/assets/base/sub",
        ):
            (proj_dir / sub).mkdir(parents=True)
        for rel, txt in (
            (".agents/rules/coding.md", "v1\n"),
            (".agents/rules/testing.md", "t2-modified\n"),
            (".agents/rules/layer-05-dept-legal.md", "# Legal v2 modified\n"),
            (
                ".agents/rules/layer-10-root.md",
                '---\ntrigger: always_on\ndescription: "Root v1"\n---\n# Root v1\n',
            ),
            (".agents/rules/layer-10-dept-sync.md", "# Sync v1\n"),
            (".agents/rules/layer-99-unmounted.md", "# Unmounted\n"),
            (".agents/rules/brand-new.md", "# Brand new\n"),
            (
                ".agents/rules/technical-base.md",
                (REPO_DIR / "templates/technical-base/rules/technical-base.md").read_text("utf-8"),
            ),
            (".agents/rules/business-base.md", "# Locally modified engine rule\n"),
            (".agents/assets/base/sub/snippet.md", "asset-v2-mod\n"),
            (".agents/skills/sopen/SKILL.md", "---\nname: sopen\ndescription: s\n---\n"),
            (".agents/skills/release/SKILL.md", "---\nname: release\ndescription: r\n---\n"),
        ):
            (proj_dir / rel).write_text(txt, encoding="utf-8")

        # Act
        diff = diff_project_against_layers(repo_dir, proj_dir)
        empty_diff = diff_project_against_layers(tmp_path / "empty_fork", tmp_path / "empty_proj")
        outside_secret = tmp_path / "outside_secret.md"
        outside_secret.write_text("# Secret\n", encoding="utf-8")
        (proj_dir / ".agents/rules/escape.md").symlink_to(outside_secret)
        with pytest.raises(ValueError, match="Outbound symlink escape denied"):
            diff_project_against_layers(repo_dir, proj_dir)

        # Assert
        in_sync_files = [x["file"] for x in diff["in_sync"]]
        mod_files = [x["file"] for x in diff["modified_in_project"]]
        assert "rules/coding.md" in in_sync_files
        assert "rules/technical-base.md" in in_sync_files
        assert "rules/layer-10-root.md" in in_sync_files
        assert "rules/layer-10-dept-sync.md" in in_sync_files
        assert "skills/sopen/SKILL.md" in in_sync_files
        assert "skills/release/SKILL.md" in in_sync_files
        assert "rules/testing.md" in mod_files
        assert "rules/business-base.md" in mod_files
        assert "rules/layer-05-dept-legal.md" in mod_files
        assert "assets/base/sub/snippet.md" in mod_files
        assert "rules/brand-new.md" in diff["novel_in_project"]
        assert "rules/layer-99-unmounted.md" in diff["novel_in_project"]
        assert empty_diff["in_sync"] == []

    def test_promote_project_asset_to_layer_validates_gates_and_copies_files(
        self,
        tmp_path: Path,
    ) -> None:
        """Promote rules, skills, trackers, and docs while enforcing budget/frontmatter."""
        # Arrange
        repo_dir, proj_dir = tmp_path / "fork", tmp_path / "proj"
        for sub in (
            "layers/dept-legal",
            "layers/dept-own/system",
            "layers/dept-own/templates/dept-own",
        ):
            (repo_dir / sub).mkdir(parents=True)
        (repo_dir / "layers/dept-own/system/mcp-layer.json").write_text(
            '{"layer_id":"dept-own","layer_role":"department"}', encoding="utf-8"
        )
        for sub in (
            ".agents/rules",
            ".agents/assets/gdpr-pack",
            ".agents/skills/good-skill",
            ".agents/skills/long-skill",
            ".agents/skills/bad-skill",
            ".agents/skills/no-fm",
            "roadmaps",
        ):
            (proj_dir / sub).mkdir(parents=True)
        for rel, txt in (
            (".agents/rules/legal.md", "# Legal Rule\n"),
            (".agents/rules/layer-05-dept-legal.md", "# Updated Dept Legal\n"),
            (".agents/assets/gdpr-pack/snippet.md", "<!-- asset -->\n"),
            (".agents/rules/huge.md", "X" * 18001),
            (".agents/rules/AGENTS.md", "Y" * 18000),
            (
                ".agents/skills/good-skill/SKILL.md",
                "---\nname: good-skill\ndescription: valid skill\n---\n" + ("# Guide\n" * 496),
            ),
            (
                ".agents/skills/long-skill/SKILL.md",
                "---\nname: long-skill\ndescription: too long\n---\n" + ("# Guide\n" * 497),
            ),
            (".agents/skills/bad-skill/SKILL.md", "---\nname: BAD_NAME\ndescription: x\n---\n"),
            (".agents/skills/no-fm/SKILL.md", "# No FM\n"),
            ("roadmaps/q4.md", "# Q4 Plan\n"),
            ("BACKLOG.md", "- [ ] Escalated item\n"),
        ):
            (proj_dir / rel).write_text(txt, encoding="utf-8")

        # Act
        def _prom(src: str, **kw: object) -> dict[str, object]:
            return promote_project_asset_to_layer(
                repo_dir,
                proj_dir,
                source_rel_path=src,
                **kw,  # type: ignore[arg-type]
            )

        dry_res = _prom(".agents/rules/legal.md", target_layer="dept-legal", dry_run=True)
        sub_rule_res = _prom(".agents/rules/legal.md", target_layer="dept-legal")
        auto_tpl_res = _prom(".agents/rules/legal.md", target_layer="dept-own")
        tpl_rule_res = _prom(".agents/rules/legal.md", target_template="fastapi-hexagonal")
        root_skill_res = _prom(".agents/skills/good-skill/SKILL.md")
        tpl_skill_res = _prom(
            ".agents/skills/good-skill/SKILL.md",
            target_layer="dept-legal",
            target_template="gdpr-pack",
        )
        asset_res = _prom(".agents/assets/gdpr-pack/snippet.md", target_layer="dept-legal")
        mat_update_res = _prom(".agents/rules/layer-05-dept-legal.md", target_layer="dept-legal")
        gov_dir_res = _prom("roadmaps/q4.md", target_layer="dept-own")
        trk_res_1 = _prom("BACKLOG.md", target_layer="dept-own")
        trk_res_2 = _prom("BACKLOG.md", target_layer="dept-own")
        exact_18k_res = _prom(
            ".agents/rules/AGENTS.md",
            target_layer="root",
            prepare_pr=True,
            actor_email="member@squad.acme.com",
            dry_run=True,
        )
        staged_pr_res = _prom(
            ".agents/rules/legal.md",
            target_template="fastapi-hexagonal",
            prepare_pr=True,
            actor_email="member@squad.acme.com",
        )
        upstream_res = _prom(
            ".agents/rules/legal.md",
            target_layer="dept-legal",
            target_template="gdpr-pack",
            upstream_dir=repo_dir / "layers" / "dept-legal",
            dry_run=True,
        )
        oss_root_dir = tmp_path / "oss-root"
        (oss_root_dir / "system").mkdir(parents=True)
        (oss_root_dir / "templates/business-base/rules").mkdir(parents=True)
        (oss_root_dir / "templates/business-base/assets").mkdir(parents=True)
        (oss_root_dir / "system/mcp-layer.json").write_text(
            '{"layer_id":"root","layer_role":"root"}', encoding="utf-8"
        )
        (proj_dir / "system").mkdir(parents=True, exist_ok=True)
        (proj_dir / "system/mcp-layer.json").write_text(
            '{"layer_id":"squad-a","layer_role":"corporate","upstream_layer":{"layer_id":"root"}}',
            encoding="utf-8",
        )
        (proj_dir / "templates/business-base/rules").mkdir(parents=True)
        (proj_dir / "templates/business-base/assets").mkdir(parents=True)
        (proj_dir / "templates/business-base/rules/business-base.md").write_text("# v2\n", "utf-8")
        (proj_dir / "templates/business-base/assets/a.md").write_text("# A\n", "utf-8")
        oss_tpl_res = _prom(
            "templates/business-base/rules/business-base.md",
            upstream_dir=oss_root_dir,
            dry_run=True,
        )
        oss_asset_res = _prom(
            "templates/business-base/assets/a.md",
            upstream_dir=oss_root_dir,
            dry_run=True,
        )

        # Assert
        assert dry_res["dry_run"] is True and sub_rule_res["subtree_push_command"] is not None
        assert (
            sub_rule_res["destination"] == "layers/dept-legal/antigravity/.gemini/config/AGENTS.md"
        )
        assert auto_tpl_res["destination"] == "layers/dept-own/templates/dept-own/rules/legal.md"
        assert mat_update_res["destination"] == sub_rule_res["destination"]
        assert asset_res["destination"] == "layers/dept-legal/templates/gdpr-pack/assets/snippet.md"
        assert (
            asset_res["target_template"] == "gdpr-pack"
            and tpl_rule_res["subtree_push_command"] is None
        )
        assert gov_dir_res["destination"] == "layers/dept-own/roadmaps/q4.md"
        assert trk_res_1["destination"] == "layers/dept-own/BACKLOG.md" == trk_res_2["destination"]
        assert (repo_dir / "layers/dept-own/BACKLOG.md").read_text("utf-8").count(
            "## Proposed from"
        ) == 2
        assert tpl_rule_res["destination"] == "templates/fastapi-hexagonal/rules/legal.md"
        assert staged_pr_res["staged_proposal"] is not None
        assert "promotion_pr_plan" in staged_pr_res
        assert (
            root_skill_res["destination"] == "antigravity/.gemini/config/skills/good-skill/SKILL.md"
        )
        assert (
            tpl_skill_res["destination"]
            == "layers/dept-legal/templates/gdpr-pack/skills/good-skill/SKILL.md"
        )
        assert exact_18k_res["destination"] == "antigravity/.gemini/config/AGENTS.md"
        assert exact_18k_res["promotion_pr_plan"]["proposer_email"] == "member@squad.acme.com"  # type: ignore[index]
        assert upstream_res["destination"] == "templates/gdpr-pack/rules/legal.md"
        assert "promotion_pr_plan" in upstream_res
        assert oss_tpl_res["target_template"] == "business-base"
        assert oss_asset_res["destination"] == "templates/business-base/assets/a.md"
        for src, bad_kw, err_pat in (
            (
                ".agents/rules/legal.md",
                {"target_layer": "dept-legal"},
                r"Refusing to overwrite existing AGENTS\.md",
            ),
            ("../outside.md", {}, "Invalid or missing project source file"),
            (".agents/rules/legal.md", {"target_layer": "nonexistent"}, "Target layer directory"),
            (".agents/rules/huge.md", {"target_layer": "root"}, "exceeds 18000-byte"),
            (".agents/skills/long-skill/SKILL.md", {}, "<= 500 lines"),
            (".agents/skills/no-fm/SKILL.md", {}, "YAML frontmatter"),
            (".agents/skills/bad-skill/SKILL.md", {}, "kebab-case name"),
            (".agents/rules/legal.md", {"target_template": "BAD_TEMPLATE"}, "Invalid target"),
        ):
            with pytest.raises(ValueError, match=err_pat):
                _prom(src, **bad_kw)
