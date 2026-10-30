"""End-to-end tests for rcap1 resonant compaction and multi-layer surface governance weaving."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parents[2]


def _create_node_fixture(
    base_dir: Path,
    layer_id: str,
    layer_role: str,
    packages: list[str] | None = None,
    manifest_extra: dict[str, object] | None = None,
) -> None:
    """Create a realistic dotfiles-ubuntu layer/node directory structure."""
    for rel in ("system", "antigravity/.gemini/config/skills/sopen", "docs"):
        (base_dir / rel).mkdir(parents=True, exist_ok=True)
    (base_dir / "VERSION").write_text("1.4.0\n", encoding="utf-8")
    (base_dir / "system/packages-manual.txt").write_text(
        "\n".join(packages or []) + "\n", encoding="utf-8"
    )
    for fname in (
        "snaps.txt",
        "npm-globals.txt",
        "nvm-default.txt",
        "external.txt",
        "gnome-extensions.txt",
    ):
        (base_dir / "system" / fname).write_text("", encoding="utf-8")
    agents_dir = base_dir / "antigravity/.gemini/config"
    (agents_dir / "AGENTS.md").write_text(
        f"# {layer_id} Rules\n## Security Mandate\nAlways validate inputs.\n", encoding="utf-8"
    )
    (agents_dir / "hooks.json").write_text('{"hooks": {}}\n', encoding="utf-8")
    (agents_dir / "skills/sopen/SKILL.md").write_text(
        "---\nname: sopen\ndescription: open session\n---\n", encoding="utf-8"
    )
    (base_dir / "docs/README.md").write_text(
        f"# Documentation Index — {layer_id}\n## Overview\nNode docs for {layer_id}.\n",
        encoding="utf-8",
    )
    manifest = {
        "schema_version": "1.2",
        "layer_id": layer_id,
        "layer_role": layer_role,
        "description": f"E2E node {layer_id}",
        "upstream_layer": {
            "layer_id": "mtwuser/dotfiles-ubuntu",
            "repository": "https://github.com/mtwuser/dotfiles-ubuntu.git",
            "branch": "master",
        },
        **(manifest_extra or {}),
    }
    (base_dir / "system/mcp-layer.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )


def _make_binding(
    binding_id: str, globs: list[str], mode: str = "transversal", **extra: object
) -> dict[str, object]:
    """Build a surface_binding dictionary for E2E manifest fixtures."""
    return {
        "binding_id": binding_id,
        "target_globs": globs,
        "architectural_planes": extra.get("planes", ["*"]),
        "scopes": extra.get("scopes", ["*"]),
        "traits": extra.get("traits", []),
        "mode": mode,
        "rule_files": extra.get("rule_files", ["antigravity/.gemini/config/AGENTS.md"]),
        "canonical_templates": extra.get("canonical_templates", []),
        "invariants": extra.get("invariants", []),
    }


def _rpc_tool(req_id: int, name: str, **arguments: object) -> dict[str, object]:
    """Build a JSON-RPC 2.0 tools/call request envelope."""
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "method": "tools/call",
        "params": {"name": name, "arguments": arguments},
    }


def _run_mcp_stdio_batch(
    repo_dir: Path, log_dir: Path, requests: list[dict[str, object]]
) -> list[dict[str, object]]:
    """Run a batch of JSON-RPC requests against a live MCP server subprocess."""
    env = {**os.environ, "DOTFILES_MCP_LOG_DIR": str(log_dir)}
    runner_code = (
        f"import pathlib, sys; sys.path.insert(0, {str(REPO_DIR / 'scripts')!r}); "
        "from dotfiles_mcp import server as m; "
        f"srv = m.DotfilesMCPServer(repo_dir=pathlib.Path({str(repo_dir)!r}), "
        f"log_dir=pathlib.Path({str(log_dir)!r})); m.run_stdio_loop(srv)"
    )
    stdin_payload = "".join(json.dumps(req) + "\n" for req in requests).encode("utf-8")
    proc = subprocess.run(
        [sys.executable, "-c", runner_code],
        input=stdin_payload,
        capture_output=True,
        timeout=15,
        check=True,
        env=env,
    )
    return [json.loads(line) for line in proc.stdout.decode("utf-8").splitlines() if line.strip()]


def _call_stdio_tool(
    repo_dir: Path, log_dir: Path, name: str, **arguments: object
) -> dict[str, object]:
    """Execute a single MCP tool call over stdio and parse the JSON text payload."""
    resp = _run_mcp_stdio_batch(repo_dir, log_dir, [_rpc_tool(1, name, **arguments)])
    return json.loads(resp[0]["result"]["content"][0]["text"])  # type: ignore[index,no-any-return]


class TestSurfaceAndCompactionE2E:
    """End-to-end test suite for rcap1 compaction and multi-layer surface governance weaving."""

    def test_e2e_resonant_chained_compaction_across_subtrees_and_agent_tiers(
        self, tmp_path: Path
    ) -> None:
        """Verify L0->L1->L2->L3 rcap1 capsule unfolding across subtrees and agent tiers."""
        # Arrange
        hub_dir, hub_logs = tmp_path / "resonant_hub", tmp_path / "resonant_logs"
        _create_node_fixture(
            hub_dir,
            "acme-corp-hub",
            "corporate",
            ["curl", "git", "python3"],
            {
                "baseline_guardrails": ["corp-baseline-guard"],
                "environments": {
                    "pre": {
                        "access_mode": "strictly-read-only",
                        "default_guardrails": ["pre-read-only-guard"],
                    }
                },
            },
        )
        dept_sub = hub_dir / "layers" / "dept-security"
        _create_node_fixture(
            dept_sub,
            "acme-dept-security",
            "department",
            ["curl"],
            {"baseline_guardrails": ["dept-zero-trust-guard"]},
        )
        ext_leak = tmp_path / "external_webhook_leak.md"
        ext_leak.write_text("# Leak\n## Webhook Secret Leak\nSecret\n", encoding="utf-8")
        (dept_sub / "docs" / "escape.md").symlink_to(ext_leak)
        (dept_sub / "docs" / "crypto_policy.md").write_text(
            "# Crypto Policy\n## Webhook HMAC Verification\n"
            '> *"Verify every webhook signature before parsing payload"*\n'
            "**Mandate:** Enforce **HMAC-SHA256** using "
            "`antigravity/.gemini/config/skills/sopen/SKILL.md`.\n"
            "- Step 1: Extract signature header\n- Step 2: Compute digest\n"
            "| Header | Algorithm |\n|---|---|\n| X-Sig | SHA256 |\n",
            encoding="utf-8",
        )

        # Act
        q_l0_payload = _call_stdio_tool(
            hub_dir,
            hub_logs,
            "query_governance_rules",
            query="Webhook",
            layer="all",
            resolution="L0",
            environment="pre",
            resonance_key="mesh-key-42",
        )
        l0_capsule = q_l0_payload["matches"][0]["capsule_token"]  # type: ignore[index]

        step2_resp = _run_mcp_stdio_batch(
            hub_dir,
            hub_logs,
            [
                _rpc_tool(
                    2,
                    "unfold_context_capsule",
                    capsule_token=l0_capsule,
                    target_level="L1",
                    agent_tier="flash",
                    environment="pre",
                    resonance_key="mesh-key-42",
                ),
                _rpc_tool(
                    3,
                    "unfold_context_capsule",
                    capsule_token=l0_capsule,
                    target_level="L2",
                    agent_tier="flash",
                    environment="pre",
                    resonance_key="mesh-key-42",
                ),
            ],
        )
        l1_unfolded = json.loads(step2_resp[0]["result"]["content"][0]["text"])  # type: ignore[index]
        flash_blocked = step2_resp[1]

        l3_unfolded = _call_stdio_tool(
            hub_dir,
            hub_logs,
            "unfold_context_capsule",
            capsule_token=l1_unfolded["next_capsule_token"],
            target_level="L3",
            agent_tier="pro",
            environment="pre",
            resonance_key="mesh-key-42",
        )

        # Assert
        assert q_l0_payload["resolution"] == "L0"
        assert q_l0_payload["match_count"] == 1
        assert q_l0_payload["matches"][0]["layer"] == "dept-security"  # type: ignore[index]
        assert l1_unfolded["unfolded_level"] == "L1"
        assert "Verify every webhook signature" in l1_unfolded["content"]["axiom_skeleton"]
        assert "error" in flash_blocked
        assert l3_unfolded["unfolded_level"] == "L3"
        assert l3_unfolded["unfold_chain"] == ["L1->L2", "L2->L3"]
        assert len(l3_unfolded["content"]["linked_l3_documents"]) == 1  # type: ignore[index]
        assert l3_unfolded["content"]["effective_guardrails"] == [  # type: ignore[index]
            "corp-baseline-guard",
            "dept-zero-trust-guard",
            "pre-read-only-guard",
        ]

    def test_e2e_agnostic_multi_layer_surface_projection_and_template_unfolding(
        self, tmp_path: Path
    ) -> None:
        """Verify 0..N layer surface weaving, precedence ordering, pruning, and L3 unfolding."""
        # Arrange
        hub_dir, hub_logs = tmp_path / "enterprise_hub", tmp_path / "enterprise_logs"
        _create_node_fixture(
            hub_dir,
            "acme-corp-engineering",
            "corporate",
            ["git", "python3"],
            {
                "precedence": 10,
                "baseline_guardrails": ["corp-clean-architecture-gate"],
                "surface_bindings": [
                    _make_binding(
                        "corp-presentation-baseline",
                        ["templates/**"],
                        planes=["presentation"],
                        invariants=["Zero inline style blocks in HTML templates"],
                    )
                ],
            },
        )
        legal_sub = hub_dir / "layers" / "statutory-compliance"
        _create_node_fixture(
            legal_sub,
            "acme-statutory-compliance",
            "domain-policy",
            [],
            {
                "precedence": 5,
                "baseline_guardrails": ["statutory-gdpr-eu-2016-679"],
                "surface_bindings": [
                    _make_binding(
                        "statutory-checkout-disclosure",
                        ["templates/checkout/**"],
                        mode="authoritative",
                        planes=["presentation"],
                        scopes=["checkout"],
                        traits=["pii", "financial"],
                        rule_files=["docs/checkout_disclosure.md"],
                        canonical_templates=["templates/legal/withdrawal_notice.html"],
                        invariants=["EU Consumer Rights Directive 14-day withdrawal disclosure"],
                    )
                ],
            },
        )
        (legal_sub / "templates/legal").mkdir(parents=True)
        (legal_sub / "templates/legal/withdrawal_notice.html").write_text(
            "<aside id='eu-withdrawal-notice'>14-day statutory right of withdrawal</aside>\n",
            encoding="utf-8",
        )
        (legal_sub / "docs/checkout_disclosure.md").write_text(
            "# Statutory Checkout Disclosure\n"
            "## Mandatory Withdrawal Notice\n"
            "Embed `templates/legal/withdrawal_notice.html` before the payment trigger.\n",
            encoding="utf-8",
        )
        design_sub = hub_dir / "layers" / "design-brand"
        _create_node_fixture(
            design_sub,
            "acme-design-brand",
            "department",
            [],
            {
                "precedence": 30,
                "baseline_guardrails": ["brand-a11y-wcag-aa"],
                "surface_bindings": [
                    _make_binding(
                        "brand-design-tokens",
                        ["templates/**"],
                        planes=["presentation"],
                        invariants=["Use semantic design tokens and 4.5:1 contrast"],
                    )
                ],
            },
        )
        logistics_sub = hub_dir / "layers" / "warehouse-logistics"
        _create_node_fixture(
            logistics_sub,
            "acme-warehouse-logistics",
            "department",
            [],
            {
                "precedence": 40,
                "surface_bindings": [
                    _make_binding(
                        "warehouse-fulfillment-domain",
                        ["src/fulfillment/**"],
                        mode="authoritative",
                        planes=["domain"],
                        scopes=["fulfillment"],
                    )
                ],
            },
        )

        # Act
        proj = _call_stdio_tool(
            hub_dir,
            hub_logs,
            "resolve_surface_governance",
            target_path="templates/checkout/summary.html",
            traits=["pii", "financial"],
        )
        legal_capsule = proj["resolved_bindings"][0]["sections"][1]["capsule_token"]  # type: ignore[index]
        unfolded_l3 = _call_stdio_tool(
            hub_dir,
            hub_logs,
            "unfold_context_capsule",
            capsule_token=legal_capsule,
            target_level="L3",
            agent_tier="inherit",
        )

        # Assert
        assert proj["participating_layers_count"] == 3
        assert proj["pruned_layers_count"] == 1
        assert proj["pruned_layers"][0]["layer"] == "warehouse-logistics"  # type: ignore[index]
        assert [b["layer"] for b in proj["resolved_bindings"]] == [  # type: ignore[attr-defined]
            "statutory-compliance",
            "root",
            "design-brand",
        ]
        assert [b["precedence"] for b in proj["resolved_bindings"]] == [5, 10, 30]  # type: ignore[attr-defined]
        assert [b["resolution"] for b in proj["resolved_bindings"]] == ["L2", "L1", "L1"]  # type: ignore[attr-defined]
        assert proj["canonical_templates"] == [
            "statutory-compliance:templates/legal/withdrawal_notice.html"
        ]
        assert unfolded_l3["unfolded_level"] == "L3"
        assert (
            "14-day statutory right of withdrawal"
            in unfolded_l3["content"]["linked_l3_documents"][0]["excerpt"]  # type: ignore[index]
        )

    def test_e2e_surface_collision_missing_assets_toctou_relocation_and_l3_mutation_guard(
        self, tmp_path: Path
    ) -> None:
        """Verify SURFACE_PRECEDENCE_COLLISION, SURFACE_ASSET_MISSING, TOCTOU, and L3 drift."""
        # Arrange
        hub_dir, hub_logs = tmp_path / "collision_hub", tmp_path / "collision_logs"
        _create_node_fixture(hub_dir, "acme-corp", "corporate", ["git"], {"precedence": 50})
        alpha_sub, beta_sub = hub_dir / "layers/dept-alpha", hub_dir / "layers/dept-beta"
        alpha_b = _make_binding(
            "alpha-payments-auth",
            ["src/payments/**"],
            mode="authoritative",
            rule_files=["docs/payment_rules.md", "docs/missing_rule.md"],
            canonical_templates=["templates/missing_snippet.html"],
        )
        beta_b = _make_binding("beta-payments-auth", ["src/payments/**"], mode="authoritative")
        _create_node_fixture(
            alpha_sub,
            "acme-dept-alpha",
            "department",
            manifest_extra={"precedence": 20, "surface_bindings": [alpha_b]},
        )
        _create_node_fixture(
            beta_sub,
            "acme-dept-beta",
            "department",
            manifest_extra={"precedence": 20, "surface_bindings": [beta_b]},
        )
        l3_doc = alpha_sub / "docs/l3_settlement_spec.md"
        l3_doc.write_text("# Settlement Ledger Spec v1\nUse idempotent keys.\n", encoding="utf-8")
        rule_doc = alpha_sub / "docs/payment_rules.md"
        long_sec = (
            "Payment Settlement Rule for Idempotent Distributed Ledger Reconciliation Gateways"
        )
        rule_body = (
            f"## {long_sec}\n"
            '> *"Settle every transaction idempotently"*\n'
            "Follow `docs/l3_settlement_spec.md` for ledger reconciliation.\n"
        )
        rule_doc.write_text(f"# Payment Governance\n{rule_body}", encoding="utf-8")

        # Act
        surf_data = _call_stdio_tool(
            hub_dir, hub_logs, "resolve_surface_governance", target_path="src/payments/processor.py"
        )
        alpha_cap = next(
            s["capsule_token"]
            for b in surf_data["resolved_bindings"]  # type: ignore[attr-defined]
            if b["layer"] == "dept-alpha"
            for s in b["sections"]
            if s["section"] == long_sec
        )
        rule_doc.write_text(
            f"# Payment Governance\n\n<!-- Drift 1 -->\n<!-- Drift 2 -->\n\n{rule_body}",
            encoding="utf-8",
        )
        relocated_data = _call_stdio_tool(
            hub_dir,
            hub_logs,
            "unfold_context_capsule",
            capsule_token=alpha_cap,
            target_level="L3",
            agent_tier="inherit",
        )
        l3_doc.write_text("# Settlement Ledger Spec v2 (MUTATED)\nChanged!\n", encoding="utf-8")
        broken_resp = _run_mcp_stdio_batch(
            hub_dir,
            hub_logs,
            [
                _rpc_tool(
                    3,
                    "unfold_context_capsule",
                    capsule_token=alpha_cap,
                    target_level="L3",
                    agent_tier="inherit",
                ),
                {
                    "jsonrpc": "2.0",
                    "id": 4,
                    "method": "resources/read",
                    "params": {"uri": "dotfiles://mcp/diagnostics"},
                },
            ],
        )
        diag_data = json.loads(broken_resp[1]["result"]["contents"][0]["text"])  # type: ignore[index]

        # Assert
        warn_codes = [w["code"] for w in surf_data["warnings"]]  # type: ignore[attr-defined]
        assert "SURFACE_PRECEDENCE_COLLISION" in warn_codes
        assert "SURFACE_ASSET_MISSING" in warn_codes
        assert relocated_data["unfolded_level"] == "L3"
        assert relocated_data["line_drift_relocated"] is True
        assert "Capsule chain digest mismatch at L2->L3" in broken_resp[0]["error"]["message"]  # type: ignore[index]
        assert "CAPSULE_CHAIN_BROKEN" in diag_data["alerts_summary"]["by_code"]
