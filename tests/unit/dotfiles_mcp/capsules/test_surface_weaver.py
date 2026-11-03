"""Unit tests for dotfiles_mcp/capsules/surface_weaver.py.

Specification: docs/architecture/04_compaction_surface_and_promotion_engines.md
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from dotfiles_mcp.capsules import surface_weaver

if TYPE_CHECKING:
    from pathlib import Path


class TestSurfaceWeaver:
    """Verify stack-agnostic plane/scope inference, glob matching, and Lex Specialis scoring."""

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
        bindings = surface_weaver.collect_layer_effective_bindings(tmp_path, manifest)

        # Assert
        assert len(bindings) == 4
        assert bindings[0]["binding_id"] == "dup-id"
        assert bindings[0]["mode"] == "authoritative"
        assert bindings[2]["binding_id"] == "new-brand-id"

    def test_infer_plane_and_scope_from_path_across_stacks(self) -> None:
        """Infer architectural_plane and scope from relative project file paths."""
        # Arrange
        pres_path = "templates/checkout/partials/_summary.html"
        domain_path = "src/legal/service.py"
        root_file = "README.md"

        # Act
        pres_plane = surface_weaver._infer_plane_from_path(pres_path)
        pres_scope = surface_weaver._infer_scope_from_path(pres_path)
        dom_plane = surface_weaver._infer_plane_from_path(domain_path)
        dom_scope = surface_weaver._infer_scope_from_path(domain_path)
        root_plane = surface_weaver._infer_plane_from_path(root_file)
        root_scope = surface_weaver._infer_scope_from_path(root_file)

        # Assert
        assert pres_plane == "presentation"
        assert pres_scope == "checkout"
        assert dom_plane == "domain"
        assert dom_scope == "legal"
        assert root_plane == ""
        assert root_scope == ""

    def test_glob_matches_handles_wildcards_and_zero_intermediate_dirs(self) -> None:
        """Match universal '**', prefix '/**', and zero-or-more '/**/' glob patterns."""
        # Arrange
        nested_router = "src/checkout/v2/router.py"
        direct_router = "src/router.py"
        root_consent = "consent.html"

        # Act
        match_all = surface_weaver._glob_matches(nested_router, "**")
        match_prefix = surface_weaver._glob_matches(nested_router, "src/checkout/**")
        match_mid_nested = surface_weaver._glob_matches(nested_router, "src/**/router.py")
        match_mid_direct = surface_weaver._glob_matches(direct_router, "src/**/router.py")
        match_lead_root = surface_weaver._glob_matches(root_consent, "**/consent.html")
        mismatch = surface_weaver._glob_matches(nested_router, "templates/**")

        # Assert
        assert match_all is True
        assert match_prefix is True
        assert match_mid_nested is True
        assert match_mid_direct is True
        assert match_lead_root is True
        assert mismatch is False

    def test_binding_matches_surface_and_computes_lex_specialis_specificity(self) -> None:
        """Evaluate 4D selector conjunction and compute Lex Specialis specificity_score."""
        # Arrange
        generic_binding = {
            "target_globs": ["**"],
            "architectural_planes": ["*"],
            "scopes": ["*"],
            "traits": [],
        }
        specific_binding = {
            "target_globs": ["src/checkout/**"],
            "architectural_planes": ["domain"],
            "scopes": ["checkout"],
            "traits": ["financial", "pii"],
        }

        # Act
        gen_match = surface_weaver._binding_matches_surface(
            generic_binding, "src/checkout/service.py", "domain", "checkout", {"financial"}
        )
        spec_match = surface_weaver._binding_matches_surface(
            specific_binding, "src/checkout/service.py", "domain", "checkout", {"financial"}
        )
        gen_score = surface_weaver._compute_binding_specificity(generic_binding)
        spec_score = surface_weaver._compute_binding_specificity(specific_binding)

        # Assert
        assert gen_match is True
        assert spec_match is True
        assert gen_score == 0
        assert spec_score == 14

    def test_match_authoritative_surface_bindings_resolves_highest_precedence_owner(
        self, tmp_path: Path
    ) -> None:
        """Resolve authoritative layer bindings ordered by precedence and specificity."""
        # Arrange
        it_dir, legal_dir = tmp_path / "dept-it", tmp_path / "dept-legal"
        it_dir.mkdir()
        legal_dir.mkdir()
        nodes = [
            (
                "dept-it",
                it_dir,
                {
                    "precedence": 30,
                    "surface_bindings": [
                        {
                            "binding_id": "catch-all",
                            "mode": "authoritative",
                            "target_globs": ["**"],
                        },
                        {
                            "binding_id": "it-infra",
                            "mode": "authoritative",
                            "target_globs": ["infra/**", "static/**"],
                        },
                    ],
                },
            ),
            (
                "dept-legal",
                legal_dir,
                {
                    "precedence": 5,
                    "surface_bindings": [
                        {
                            "binding_id": "legal-pages",
                            "mode": "authoritative",
                            "target_globs": ["static/legal/**"],
                        },
                        {
                            "binding_id": "legal-adv",
                            "mode": "transversal",
                            "target_globs": ["infra/**"],
                        },
                    ],
                },
            ),
        ]

        # Act
        hits = surface_weaver.match_authoritative_surface_bindings(
            nodes, ["", "infra/deploy.sh", "static/legal/terms.html", "README.md"]
        )

        # Assert
        assert len(hits) == 2
        assert (hits[0]["target_path"], hits[0]["owning_layer_id"]) == (
            "infra/deploy.sh",
            "dept-it",
        )
        assert (hits[1]["target_path"], hits[1]["owning_layer_id"], hits[1]["precedence"]) == (
            "static/legal/terms.html",
            "dept-legal",
            5,
        )
