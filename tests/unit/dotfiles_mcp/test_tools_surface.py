"""Unit tests for dotfiles_mcp/tools_surface.py."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
from dotfiles_mcp.server import DotfilesMCPServer

if TYPE_CHECKING:
    from pathlib import Path


class TestSurfaceToolsMixin:
    """Verify resolve_surface_governance across 0..N layers, Lex Specialis, and alerts."""

    def test_resolve_surface_governance_across_zero_to_n_arbitrary_layers(
        self,
        tmp_path: Path,
    ) -> None:
        """Weave matching layers by precedence (0..100), prune non-matching, and verify assets."""
        # Arrange
        agents_dir = tmp_path / "antigravity/.gemini/config"
        agents_dir.mkdir(parents=True)
        (agents_dir / "AGENTS.md").write_text(
            "# Global Engineering Rules\n"
            "## Reusability First\n"
            '> *"Scan workspace before creating duplicates"*\n'
            "- Reuse shared helpers\n"
            "- Keep functions small\n"
            "```python\n"
            "x = 1\n"
            "```\n",
            encoding="utf-8",
        )
        (tmp_path / "system").mkdir()
        (tmp_path / "system/mcp-layer.json").write_text(
            json.dumps(
                {
                    "layer_id": "corp-it-baseline",
                    "layer_role": "corporate",
                    "precedence": 10,
                    "baseline_guardrails": ["corp-type-safety"],
                    "environments": {"pre": {"default_guardrails": ["pre-read-only"]}},
                }
            ),
            encoding="utf-8",
        )

        priv_dir = tmp_path / "layers/statutory-privacy"
        (priv_dir / "system").mkdir(parents=True)
        (priv_dir / "docs").mkdir()
        (priv_dir / "templates/legal").mkdir(parents=True)
        (priv_dir / "templates/legal/consent.html").write_text(
            "<div class='consent'>GDPR Consent</div>\n", encoding="utf-8"
        )
        (priv_dir / "docs/privacy_rules.md").write_text(
            "# Statutory Privacy Rules\n"
            "## Explicit Consent Gate\n"
            "Every PII form must render `templates/legal/consent.html`.\n",
            encoding="utf-8",
        )
        (priv_dir / "system/mcp-layer.json").write_text(
            json.dumps(
                {
                    "layer_id": "org-statutory-privacy",
                    "layer_role": "domain-policy",
                    "precedence": 5,
                    "baseline_guardrails": ["gdpr-art-25-by-design"],
                    "surface_bindings": [
                        {
                            "binding_id": "pii-consent-mandate",
                            "target_globs": ["templates/**"],
                            "architectural_planes": ["presentation"],
                            "scopes": ["checkout", "legal"],
                            "traits": ["pii"],
                            "mode": "authoritative",
                            "rule_files": ["docs/privacy_rules.md", "docs/missing_rule.md"],
                            "canonical_templates": ["templates/legal/consent.html"],
                            "invariants": ["Explicit opt-in checkbox required before submit"],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        design_dir = tmp_path / "layers/design-tokens"
        (design_dir / "system").mkdir(parents=True)
        (design_dir / "docs").mkdir()
        (design_dir / "docs/ui_tokens.md").write_text(
            "# Design System Tokens\n"
            "## Semantic CSS Tokens\n"
            '> *"Never hardcode hex colors"*\n'
            "- Use semantic CSS variables\n",
            encoding="utf-8",
        )
        (design_dir / "system/mcp-layer.json").write_text(
            json.dumps(
                {
                    "layer_id": "org-design-tokens",
                    "layer_role": "department",
                    "precedence": 30,
                    "surface_bindings": [
                        {
                            "binding_id": "ui-token-consistency",
                            "target_globs": ["templates/**", "*.html"],
                            "architectural_planes": ["presentation"],
                            "scopes": ["*"],
                            "traits": [],
                            "mode": "transversal",
                            "rule_files": ["docs/ui_tokens.md"],
                            "canonical_templates": [],
                            "invariants": ["WCAG 2.1 AA contrast >= 4.5:1"],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        hr_dir = tmp_path / "layers/internal-hr"
        (hr_dir / "system").mkdir(parents=True)
        (hr_dir / "system/mcp-layer.json").write_text(
            json.dumps(
                {
                    "layer_id": "org-internal-hr",
                    "layer_role": "department",
                    "precedence": 50,
                    "surface_bindings": [
                        {
                            "binding_id": "hr-payroll-only",
                            "target_globs": ["src/payroll/**"],
                            "architectural_planes": ["domain"],
                            "scopes": ["payroll"],
                            "traits": ["internal"],
                            "mode": "authoritative",
                            "rule_files": [],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        server = DotfilesMCPServer(repo_dir=tmp_path, log_dir=tmp_path / "logs")

        # Act
        with pytest.raises(ValueError, match="At least one surface selector"):
            server.call_tool("resolve_surface_governance", {})
        with pytest.raises(ValueError, match="Invalid architectural_plane"):
            server.call_tool("resolve_surface_governance", {"architectural_plane": "unknown-plane"})
        with pytest.raises(ValueError, match="Invalid environment"):
            server.call_tool(
                "resolve_surface_governance", {"target_path": "README.md", "environment": "bad-env"}
            )
        with pytest.raises(ValueError, match="Invalid resolution_override"):
            server.call_tool(
                "resolve_surface_governance",
                {"target_path": "README.md", "resolution_override": "L9"},
            )

        adaptive_rpc = (
            server.handle_request(
                {
                    "jsonrpc": "2.0",
                    "id": 50,
                    "method": "tools/call",
                    "params": {
                        "name": "resolve_surface_governance",
                        "arguments": {
                            "target_path": "templates/checkout/summary.html",
                            "traits": ["pii"],
                            "environment": "pre",
                        },
                    },
                }
            )
            or {}
        )
        adaptive_res = json.loads(adaptive_rpc["result"]["content"][0]["text"])
        l0_no_cap_res = json.loads(
            server.call_tool(
                "resolve_surface_governance",
                {
                    "target_path": "README.md",
                    "resolution_override": "L0",
                    "include_capsules": False,
                },
            )["content"][0]["text"]
        )

        # Assert
        assert adaptive_res["surface_query"]["effective_plane"] == "presentation"
        assert adaptive_res["surface_query"]["effective_scope"] == "checkout"
        assert adaptive_res["participating_layers_count"] == 3
        assert [p["layer"] for p in adaptive_res["participating_layers"]] == [
            "statutory-privacy",
            "root",
            "design-tokens",
        ]
        assert adaptive_res["pruned_layers_count"] == 1
        assert adaptive_res["pruned_layers"][0]["layer"] == "internal-hr"
        assert [b["binding_id"] for b in adaptive_res["resolved_bindings"]] == [
            "pii-consent-mandate",
            "root-default-baseline",
            "ui-token-consistency",
        ]
        assert adaptive_res["resolved_bindings"][0]["resolution"] == "L2"
        assert adaptive_res["resolved_bindings"][1]["resolution"] == "L1"
        assert adaptive_res["resolved_bindings"][2]["resolution"] == "L1"
        assert adaptive_res["canonical_templates"] == [
            "statutory-privacy:templates/legal/consent.html"
        ]
        assert any(w["code"] == "SURFACE_ASSET_MISSING" for w in adaptive_res["warnings"])
        assert "gdpr-art-25-by-design" in adaptive_res["effective_invariants"]
        assert "pre-read-only" in adaptive_res["effective_invariants"]
        assert l0_no_cap_res["surface_query"]["effective_plane"] == "all"
        assert l0_no_cap_res["surface_query"]["effective_scope"] == "all"
        assert l0_no_cap_res["resolved_bindings"][0]["sections"][0]["capsule_token"] is None
        assert "surface_preview" in l0_no_cap_res["resolved_bindings"][0]["sections"][0]
        assert l0_no_cap_res["token_compaction_metrics"]["capsule_overhead_tokens"] == 0

    def test_resolve_surface_governance_precedence_collision_lex_specialis_and_validation_gates(
        self,
        tmp_path: Path,
    ) -> None:
        """Break precedence ties via Lex Specialis score and emit collision/truncation alerts."""
        # Arrange
        root_dir = tmp_path / "collision_repo"
        (root_dir / "system").mkdir(parents=True)
        (root_dir / "docs").mkdir(parents=True)
        long_body = "A" * 1600
        (root_dir / "docs/many_sections.md").write_text(
            f"# Title\n## Sec 1\n{long_body}\n## Sec 2\nB\n## Sec 3\nC\n## Sec 4\nD\n",
            encoding="utf-8",
        )
        (root_dir / "system/mcp-layer.json").write_text(
            json.dumps(
                {
                    "schema_version": "1.2",
                    "layer_id": "corp-root",
                    "layer_role": "corporate",
                    "precedence": 20,
                    "surface_bindings": [
                        {
                            "binding_id": "generic-checkout-owner",
                            "target_globs": ["**"],
                            "architectural_planes": ["*"],
                            "scopes": ["*"],
                            "traits": [],
                            "mode": "authoritative",
                            "rule_files": ["docs/many_sections.md"],
                            "canonical_templates": ["templates/missing_tpl.html"],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        fin_dir = root_dir / "layers/financial-ledger"
        (fin_dir / "system").mkdir(parents=True)
        (fin_dir / "docs").mkdir(parents=True)
        (fin_dir / "docs/ledger.md").write_text(
            "# Ledger\n## Double Entry\nEnforce double-entry ledger invariants.\n",
            encoding="utf-8",
        )
        (fin_dir / "system/mcp-layer.json").write_text(
            json.dumps(
                {
                    "schema_version": "1.2",
                    "layer_id": "org-financial-ledger",
                    "layer_role": "domain-policy",
                    "precedence": 20,
                    "surface_bindings": [
                        {
                            "binding_id": "specific-checkout-ledger",
                            "target_globs": ["src/checkout/**"],
                            "architectural_planes": ["domain"],
                            "scopes": ["checkout"],
                            "traits": ["financial"],
                            "mode": "authoritative",
                            "rule_files": ["docs/ledger.md"],
                            "canonical_templates": [],
                            "ephemeral_fork_policy": {"bot_role": "dept-ledger-bot"},
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        server = DotfilesMCPServer(repo_dir=root_dir, log_dir=tmp_path / "logs")

        bad_layer_prec_dir = tmp_path / "bad_layer_prec"
        (bad_layer_prec_dir / "system").mkdir(parents=True)
        (bad_layer_prec_dir / "system/mcp-layer.json").write_text(
            json.dumps({"schema_version": "1.2", "precedence": 150}), encoding="utf-8"
        )
        bad_bind_prec_dir = tmp_path / "bad_bind_prec"
        (bad_bind_prec_dir / "system").mkdir(parents=True)
        (bad_bind_prec_dir / "system/mcp-layer.json").write_text(
            json.dumps(
                {
                    "schema_version": "1.2",
                    "surface_bindings": [{"binding_id": "b1", "precedence": -1}],
                }
            ),
            encoding="utf-8",
        )
        bad_mode_dir = tmp_path / "bad_mode"
        (bad_mode_dir / "system").mkdir(parents=True)
        (bad_mode_dir / "system/mcp-layer.json").write_text(
            json.dumps(
                {
                    "schema_version": "1.2",
                    "surface_bindings": [{"binding_id": "b1", "mode": "invalid-mode"}],
                }
            ),
            encoding="utf-8",
        )

        # Act
        res = json.loads(
            server.call_tool(
                "resolve_surface_governance",
                {"target_path": "src/checkout/service.py", "traits": ["financial"]},
            )["content"][0]["text"]
        )
        with pytest.raises(ValueError, match="Invalid layer precedence"):
            DotfilesMCPServer(repo_dir=bad_layer_prec_dir).call_tool(
                "resolve_surface_governance", {"target_path": "src/a.py"}
            )
        with pytest.raises(ValueError, match="Invalid binding precedence"):
            DotfilesMCPServer(repo_dir=bad_bind_prec_dir).call_tool(
                "resolve_surface_governance", {"target_path": "src/a.py"}
            )
        with pytest.raises(ValueError, match="Invalid surface_binding mode"):
            DotfilesMCPServer(repo_dir=bad_mode_dir).call_tool(
                "resolve_surface_governance", {"target_path": "src/a.py"}
            )

        # Assert
        assert [b["binding_id"] for b in res["resolved_bindings"]] == [
            "specific-checkout-ledger",
            "generic-checkout-owner",
        ]
        assert res["resolved_bindings"][0]["specificity_score"] == 10
        assert res["resolved_bindings"][0]["ephemeral_fork_policy"] == {
            "bot_role": "dept-ledger-bot"
        }
        assert res["resolved_bindings"][1]["specificity_score"] == 0
        assert res["truncated"] is True
        warning_codes = [w["code"] for w in res["warnings"]]
        assert "SURFACE_PRECEDENCE_COLLISION" in warning_codes
        assert "SURFACE_ASSET_MISSING" in warning_codes
        assert "RESPONSE_TRUNCATED" in warning_codes
