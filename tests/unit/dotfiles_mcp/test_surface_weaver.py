"""Unit tests for dotfiles_mcp/surface_weaver.py."""

from __future__ import annotations

from dotfiles_mcp import surface_weaver


class TestSurfaceWeaver:
    """Verify stack-agnostic plane/scope inference, glob matching, and Lex Specialis scoring."""

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
