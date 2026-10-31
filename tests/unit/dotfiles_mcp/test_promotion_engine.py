"""Unit tests for dotfiles_mcp/promotion_engine.py (TestPromotionEngine)."""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING

import pytest
from dotfiles_mcp.promotion_engine import (
    collect_layer_effective_bindings,
    diff_project_against_layers,
    inspect_layer_horizon,
    promote_project_asset_to_layer,
)
from dotfiles_mcp.server import DotfilesMCPServer

if TYPE_CHECKING:
    from pathlib import Path


class TestPromotionEngine:
    """Verify multi-layer pattern comparison, project diffing, and upward promotion."""

    def test_collect_layer_effective_bindings_merges_and_deduplicates_template_bindings(
        self,
        tmp_path: Path,
    ) -> None:
        """Merge manifest surface_bindings with template.json recommended_surface_bindings."""
        # Arrange
        tpl_dir = tmp_path / "templates" / "brand-pack"
        tpl_dir.mkdir(parents=True)
        (tpl_dir / "template.json").write_text(
            json.dumps(
                {
                    "recommended_surface_bindings": [
                        "invalid-entry",
                        {"binding_id": "dup-id", "mode": "transversal"},
                        {"binding_id": "new-brand-id", "mode": "transversal"},
                        {"mode": "advisory"},
                    ]
                }
            ),
            encoding="utf-8",
        )
        bad_tpl = tmp_path / "templates" / "bad-json-pack"
        bad_tpl.mkdir(parents=True)
        (bad_tpl / "template.json").write_text("[]", encoding="utf-8")
        manifest: dict[str, object] = {
            "default_stack_templates": ["brand-pack", "bad-json-pack", "missing-pack"],
            "surface_bindings": [
                "not-a-dict",
                {"binding_id": "dup-id", "mode": "authoritative"},
                {"mode": "transversal"},
            ],
        }

        # Act
        bindings = collect_layer_effective_bindings(tmp_path, manifest)

        # Assert
        assert len(bindings) == 4
        assert bindings[0]["binding_id"] == "dup-id"
        assert bindings[0]["mode"] == "authoritative"
        assert bindings[2]["binding_id"] == "new-brand-id"

    def test_compare_project_patterns_multilayer_routes_novel_items_and_filters_materialized(
        self,
        tmp_path: Path,
    ) -> None:
        """Scan root and mounted layers, ignore layer-NN-*.md, and route novel promotions."""
        # Arrange
        (tmp_path / "system").mkdir(parents=True)
        (tmp_path / "system/mcp-layer.json").write_text(
            '{"schema_version":"1.2","layer_id":"acme-corp","layer_role":"corporate",'
            '"default_stack_templates":["web-starter"]}',
            encoding="utf-8",
        )
        (tmp_path / "templates/web-starter/rules").mkdir(parents=True)
        (tmp_path / "templates/web-starter/rules/coding.md").write_text(
            "# Code\n", encoding="utf-8"
        )
        (tmp_path / "templates/web-starter/skills/start").mkdir(parents=True)
        (tmp_path / "templates/web-starter/skills/start/SKILL.md").write_text(
            "---\nname: start\ndescription: s\n---\n", encoding="utf-8"
        )
        (tmp_path / "templates/.hidden").mkdir(parents=True)
        (tmp_path / "templates/file.txt").write_text("x", encoding="utf-8")

        legal_dir = tmp_path / "layers/dept-legal"
        (legal_dir / "system").mkdir(parents=True)
        (legal_dir / "system/mcp-layer.json").write_text(
            '{"schema_version":"1.2","layer_id":"acme-legal","layer_role":"domain-policy",'
            '"surface_bindings":[{"binding_id":"gdpr-b","scopes":["*","checkout"],"traits":["*","pii"]}]}',
            encoding="utf-8",
        )
        design_dir = tmp_path / "layers/dept-design"
        (design_dir / "system").mkdir(parents=True)
        (design_dir / "templates/brand-ui/rules").mkdir(parents=True)
        (design_dir / "system/mcp-layer.json").write_text(
            '{"schema_version":"1.2","layer_id":"ab-sec","layer_role":"department",'
            '"default_stack_templates":["brand-ui"]}',
            encoding="utf-8",
        )
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
        repo_dir = tmp_path / "fork"
        (repo_dir / "templates/base/rules").mkdir(parents=True)
        (repo_dir / "templates/base/skills/sopen").mkdir(parents=True)
        (repo_dir / "templates/base/assets/sub").mkdir(parents=True)
        (repo_dir / "templates/.hidden").mkdir(parents=True)
        (repo_dir / "templates/base/rules/coding.md").write_text("v1\n", encoding="utf-8")
        (repo_dir / "templates/base/rules/testing.md").write_text("t1\n", encoding="utf-8")
        (repo_dir / "templates/base/assets/sub/snippet.md").write_text(
            "asset-v1\n", encoding="utf-8"
        )
        (repo_dir / "templates/base/skills/sopen/SKILL.md").write_text(
            "---\nname: sopen\ndescription: s\n---\n", encoding="utf-8"
        )
        (repo_dir / "antigravity/.gemini/config").mkdir(parents=True)
        (repo_dir / "antigravity/.gemini/config/AGENTS.md").write_text(
            "# Root v1\n", encoding="utf-8"
        )
        legal_sub = repo_dir / "layers/dept-legal/antigravity/.gemini/config"
        legal_sub.mkdir(parents=True)
        (legal_sub / "AGENTS.md").write_text("# Legal v1\n", encoding="utf-8")
        (repo_dir / "layers/dept- sync/antigravity/.gemini/config").mkdir(parents=True)
        (repo_dir / "layers/dept-sync/antigravity/.gemini/config").mkdir(parents=True)
        (repo_dir / "layers/dept-sync/antigravity/.gemini/config/AGENTS.md").write_text(
            "# Sync v1\n", encoding="utf-8"
        )
        (repo_dir / "layers/.hidden").mkdir(parents=True)

        proj_dir = tmp_path / "proj"
        (proj_dir / ".agents/rules").mkdir(parents=True)
        (proj_dir / ".agents/skills/sopen").mkdir(parents=True)
        (proj_dir / ".agents/rules/coding.md").write_text("v1\n", encoding="utf-8")
        (proj_dir / ".agents/rules/testing.md").write_text("t2-modified\n", encoding="utf-8")
        (proj_dir / ".agents/rules/layer-05-dept-legal.md").write_text(
            "# Legal v2 modified\n", encoding="utf-8"
        )
        (proj_dir / ".agents/rules/layer-10-root.md").write_text("# Root v1\n", encoding="utf-8")
        (proj_dir / ".agents/rules/layer-10-dept-sync.md").write_text(
            "# Sync v1\n", encoding="utf-8"
        )
        (proj_dir / ".agents/rules/layer-99-unmounted.md").write_text(
            "# Unmounted\n", encoding="utf-8"
        )
        (proj_dir / ".agents/rules/brand-new.md").write_text("# Brand new\n", encoding="utf-8")
        (proj_dir / ".agents/assets/base/sub").mkdir(parents=True)
        (proj_dir / ".agents/assets/base/sub/snippet.md").write_text(
            "asset-v2-mod\n", encoding="utf-8"
        )
        (proj_dir / ".agents/skills/sopen/SKILL.md").write_text(
            "---\nname: sopen\ndescription: s\n---\n", encoding="utf-8"
        )

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
        assert "rules/layer-10-root.md" in in_sync_files
        assert "rules/layer-10-dept-sync.md" in in_sync_files
        assert "skills/sopen/SKILL.md" in in_sync_files
        assert "rules/testing.md" in mod_files
        assert "rules/layer-05-dept-legal.md" in mod_files
        assert "assets/base/sub/snippet.md" in mod_files
        assert "rules/brand-new.md" in diff["novel_in_project"]
        assert "rules/layer-99-unmounted.md" in diff["novel_in_project"]
        assert empty_diff["in_sync"] == []

    def test_promote_project_asset_to_layer_validates_gates_and_copies_files(
        self,
        tmp_path: Path,
    ) -> None:
        """Promote rules and skills to root or subtree layers while enforcing budget/frontmatter."""
        # Arrange
        repo_dir = tmp_path / "fork"
        (repo_dir / "layers/dept-legal").mkdir(parents=True)
        proj_dir = tmp_path / "proj"
        (proj_dir / ".agents/rules").mkdir(parents=True)
        (proj_dir / ".agents/skills/good-skill").mkdir(parents=True)
        (proj_dir / ".agents/skills/bad-skill").mkdir(parents=True)
        (proj_dir / ".agents/skills/no-fm").mkdir(parents=True)

        (proj_dir / ".agents/rules/legal.md").write_text("# Legal Rule\n", encoding="utf-8")
        (proj_dir / ".agents/rules/layer-05-dept-legal.md").write_text(
            "# Updated Dept Legal\n", encoding="utf-8"
        )
        (proj_dir / ".agents/assets/gdpr-pack").mkdir(parents=True)
        (proj_dir / ".agents/assets/gdpr-pack/snippet.md").write_text(
            "<!-- asset -->\n", encoding="utf-8"
        )
        (proj_dir / ".agents/rules/huge.md").write_text("X" * 18001, encoding="utf-8")
        (proj_dir / ".agents/rules/AGENTS.md").write_text("Y" * 18000, encoding="utf-8")
        (proj_dir / ".agents/skills/good-skill/SKILL.md").write_text(
            "---\nname: good-skill\ndescription: valid skill\n---\n" + ("# Guide\n" * 496),
            encoding="utf-8",
        )
        (proj_dir / ".agents/skills/long-skill").mkdir(parents=True)
        (proj_dir / ".agents/skills/long-skill/SKILL.md").write_text(
            "---\nname: long-skill\ndescription: too long\n---\n" + ("# Guide\n" * 497),
            encoding="utf-8",
        )
        (proj_dir / ".agents/skills/bad-skill/SKILL.md").write_text(
            "---\nname: BAD_NAME\ndescription: x\n---\n",
            encoding="utf-8",
        )
        (proj_dir / ".agents/skills/no-fm/SKILL.md").write_text("# No FM\n", encoding="utf-8")

        # Act
        dry_res = promote_project_asset_to_layer(
            repo_dir,
            proj_dir,
            source_rel_path=".agents/rules/legal.md",
            target_layer="dept-legal",
            dry_run=True,
        )
        sub_rule_res = promote_project_asset_to_layer(
            repo_dir, proj_dir, source_rel_path=".agents/rules/legal.md", target_layer="dept-legal"
        )
        tpl_rule_res = promote_project_asset_to_layer(
            repo_dir,
            proj_dir,
            source_rel_path=".agents/rules/legal.md",
            target_template="fastapi-hexagonal",
        )
        root_skill_res = promote_project_asset_to_layer(
            repo_dir, proj_dir, source_rel_path=".agents/skills/good-skill/SKILL.md"
        )
        tpl_skill_res = promote_project_asset_to_layer(
            repo_dir,
            proj_dir,
            source_rel_path=".agents/skills/good-skill/SKILL.md",
            target_layer="dept-legal",
            target_template="gdpr-pack",
        )
        asset_res = promote_project_asset_to_layer(
            repo_dir,
            proj_dir,
            source_rel_path=".agents/assets/gdpr-pack/snippet.md",
            target_layer="dept-legal",
        )
        mat_update_res = promote_project_asset_to_layer(
            repo_dir,
            proj_dir,
            source_rel_path=".agents/rules/layer-05-dept-legal.md",
            target_layer="dept-legal",
        )
        exact_18k_res = promote_project_asset_to_layer(
            repo_dir,
            proj_dir,
            source_rel_path=".agents/rules/AGENTS.md",
            target_layer="root",
            prepare_pr=True,
            actor_email="member@squad.acme.com",
            dry_run=True,
        )
        upstream_res = promote_project_asset_to_layer(
            repo_dir,
            proj_dir,
            source_rel_path=".agents/rules/legal.md",
            target_layer="dept-legal",
            target_template="gdpr-pack",
            upstream_dir=repo_dir / "layers" / "dept-legal",
            dry_run=True,
        )

        # Assert
        assert dry_res["dry_run"] is True
        assert (
            sub_rule_res["destination"] == "layers/dept-legal/antigravity/.gemini/config/AGENTS.md"
        )
        assert (
            mat_update_res["destination"]
            == "layers/dept-legal/antigravity/.gemini/config/AGENTS.md"
        )
        assert asset_res["destination"] == "layers/dept-legal/templates/gdpr-pack/assets/snippet.md"
        assert asset_res["target_template"] == "gdpr-pack"
        assert sub_rule_res["subtree_push_command"] is not None
        assert tpl_rule_res["destination"] == "templates/fastapi-hexagonal/rules/legal.md"
        assert tpl_rule_res["subtree_push_command"] is None
        assert root_skill_res["destination"] == (
            "antigravity/.gemini/config/skills/good-skill/SKILL.md"
        )
        assert tpl_skill_res["destination"] == (
            "layers/dept-legal/templates/gdpr-pack/skills/good-skill/SKILL.md"
        )
        assert exact_18k_res["destination"] == "antigravity/.gemini/config/AGENTS.md"
        assert exact_18k_res["promotion_pr_plan"]["proposer_email"] == "member@squad.acme.com"
        assert upstream_res["destination"] == "templates/gdpr-pack/rules/legal.md"
        assert "promotion_pr_plan" in upstream_res
        for bad_kwargs, err_pat in (
            (
                {"source_rel_path": ".agents/rules/legal.md", "target_layer": "dept-legal"},
                r"Refusing to overwrite existing AGENTS\.md",
            ),
            ({"source_rel_path": "../outside.md"}, "Invalid or missing project source file"),
            (
                {"source_rel_path": ".agents/rules/legal.md", "target_layer": "nonexistent"},
                "Target layer directory not found",
            ),
            (
                {"source_rel_path": ".agents/rules/huge.md", "target_layer": "root"},
                "exceeds 18000-byte token budget cap",
            ),
            ({"source_rel_path": ".agents/skills/long-skill/SKILL.md"}, "<= 500 lines"),
            ({"source_rel_path": ".agents/skills/no-fm/SKILL.md"}, "YAML frontmatter"),
            ({"source_rel_path": ".agents/skills/bad-skill/SKILL.md"}, "kebab-case name"),
            (
                {"source_rel_path": ".agents/rules/legal.md", "target_template": "BAD_TEMPLATE"},
                "Invalid target_template",
            ),
        ):
            with pytest.raises(ValueError, match=err_pat):
                promote_project_asset_to_layer(repo_dir, proj_dir, **bad_kwargs)  # type: ignore[arg-type]

    def test_inspect_layer_horizon_detects_upward_and_downward_drift(
        self,
        tmp_path: Path,
    ) -> None:
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
        (proj_dir / "templates/business-base/assets/a.md").write_text("# A\n", encoding="utf-8")

        # Act
        oss_tpl_res = promote_project_asset_to_layer(
            oss_dir,
            proj_dir,
            source_rel_path="templates/business-base/rules/business-base.md",
            upstream_dir=oss_dir,
            dry_run=True,
        )
        oss_asset_res = promote_project_asset_to_layer(
            oss_dir,
            proj_dir,
            source_rel_path="templates/business-base/assets/a.md",
            upstream_dir=oss_dir,
            dry_run=True,
        )
        hz_oss = inspect_layer_horizon(oss_dir, proj_dir)
        hz_int = inspect_layer_horizon(repo_dir, proj_dir, parent_dir=repo_dir)
        up_b = oss_dir / "templates/business-base/rules/business-base.md"
        up_b.write_text("# v3 upstream\n", encoding="utf-8")
        os.utime(up_b, ns=(ts + 1_000_000, ts + 1_000_000))
        hz_after_up = inspect_layer_horizon(oss_dir, proj_dir)

        # Assert
        assert oss_tpl_res["target_template"] == "business-base"
        assert oss_asset_res["destination"] == "templates/business-base/assets/a.md"
        assert (
            hz_oss["is_oss_community_horizon"],
            hz_oss["downward_sync_needed"],
            len(hz_oss["upward_promotion_suggestions"]),
        ) == (True, False, 1)
        assert hz_oss["oss_contrib_dir"] is not None
        assert hz_int["is_oss_community_horizon"] is False
        assert hz_int["oss_contrib_dir"] is None
        assert len(hz_int["upward_promotion_suggestions"]) >= 1
        assert hz_after_up["downward_sync_needed"] is True
