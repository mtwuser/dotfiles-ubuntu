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
    packages: list[str],
    manifest_extra: dict[str, object],
) -> None:
    """Create a realistic dotfiles-ubuntu layer/node directory structure."""
    base_dir.mkdir(parents=True, exist_ok=True)
    (base_dir / "VERSION").write_text("1.4.0\n", encoding="utf-8")
    (base_dir / "system").mkdir(parents=True, exist_ok=True)
    (base_dir / "system" / "packages-manual.txt").write_text(
        "\n".join(packages) + "\n", encoding="utf-8"
    )
    for fname in (
        "snaps.txt",
        "npm-globals.txt",
        "nvm-default.txt",
        "external.txt",
        "gnome-extensions.txt",
    ):
        (base_dir / "system" / fname).write_text("", encoding="utf-8")

    agents_dir = base_dir / "antigravity" / ".gemini" / "config"
    (agents_dir / "skills" / "sopen").mkdir(parents=True, exist_ok=True)
    (agents_dir / "AGENTS.md").write_text(
        f"# {layer_id} Rules\n## Security Mandate\nAlways validate inputs.\n",
        encoding="utf-8",
    )
    (agents_dir / "hooks.json").write_text('{"hooks": {}}\n', encoding="utf-8")
    (agents_dir / "skills" / "sopen" / "SKILL.md").write_text(
        "---\nname: sopen\ndescription: open session\n---\n", encoding="utf-8"
    )

    docs_dir = base_dir / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    (docs_dir / "README.md").write_text(
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
        **manifest_extra,
    }
    (base_dir / "system" / "mcp-layer.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )


def _run_mcp_stdio_batch(
    repo_dir: Path,
    log_dir: Path,
    requests: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Run a batch of JSON-RPC requests against a live MCP server subprocess."""
    env = dict(os.environ)
    env["DOTFILES_MCP_LOG_DIR"] = str(log_dir)
    runner_code = (
        "import pathlib, sys; "
        f"sys.path.insert(0, {str(REPO_DIR / 'scripts')!r}); "
        "from dotfiles_mcp import server as m; "
        f"srv = m.DotfilesMCPServer(repo_dir=pathlib.Path({str(repo_dir)!r}), "
        f"log_dir=pathlib.Path({str(log_dir)!r})); "
        "m.run_stdio_loop(srv)"
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


class TestSurfaceAndCompactionE2E:
    """End-to-end test suite for rcap1 compaction and multi-layer surface governance weaving."""

    def test_e2e_resonant_chained_compaction_across_subtrees_and_agent_tiers(
        self, tmp_path: Path
    ) -> None:
        """Verify L0->L1->L2->L3 rcap1 capsule unfolding across subtrees and agent tiers."""
        # Arrange
        hub_dir = tmp_path / "resonant_hub"
        hub_logs = tmp_path / "resonant_logs"
        _create_node_fixture(
            hub_dir,
            layer_id="acme-corp-hub",
            layer_role="corporate",
            packages=["curl", "git", "python3"],
            manifest_extra={
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
            layer_id="acme-dept-security",
            layer_role="department",
            packages=["curl"],
            manifest_extra={"baseline_guardrails": ["dept-zero-trust-guard"]},
        )
        (dept_sub / "docs" / "crypto_policy.md").write_text(
            "# Crypto Policy\n"
            "## Webhook HMAC Verification\n"
            '> *"Verify every webhook signature before parsing payload"*\n'
            "**Mandate:** Enforce **HMAC-SHA256** using "
            "`antigravity/.gemini/config/skills/sopen/SKILL.md`.\n"
            "- Step 1: Extract signature header\n"
            "- Step 2: Compute digest\n"
            "| Header | Algorithm |\n"
            "|---|---|\n"
            "| X-Sig | SHA256 |\n",
            encoding="utf-8",
        )

        # Act
        step1_resp = _run_mcp_stdio_batch(
            hub_dir,
            hub_logs,
            [
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {
                        "name": "query_governance_rules",
                        "arguments": {
                            "query": "Webhook",
                            "layer": "all",
                            "resolution": "L0",
                            "environment": "pre",
                            "resonance_key": "mesh-key-42",
                        },
                    },
                }
            ],
        )
        q_l0_payload = json.loads(step1_resp[0]["result"]["content"][0]["text"])  # type: ignore[index]
        l0_capsule = q_l0_payload["matches"][0]["capsule_token"]

        step2_resp = _run_mcp_stdio_batch(
            hub_dir,
            hub_logs,
            [
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {
                        "name": "unfold_context_capsule",
                        "arguments": {
                            "capsule_token": l0_capsule,
                            "target_level": "L1",
                            "agent_tier": "flash",
                            "environment": "pre",
                            "resonance_key": "mesh-key-42",
                        },
                    },
                },
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {
                        "name": "unfold_context_capsule",
                        "arguments": {
                            "capsule_token": l0_capsule,
                            "target_level": "L2",
                            "agent_tier": "flash",
                            "environment": "pre",
                            "resonance_key": "mesh-key-42",
                        },
                    },
                },
            ],
        )
        l1_unfolded = json.loads(step2_resp[0]["result"]["content"][0]["text"])  # type: ignore[index]
        flash_blocked = step2_resp[1]
        l1_capsule = l1_unfolded["next_capsule_token"]

        step3_resp = _run_mcp_stdio_batch(
            hub_dir,
            hub_logs,
            [
                {
                    "jsonrpc": "2.0",
                    "id": 4,
                    "method": "tools/call",
                    "params": {
                        "name": "unfold_context_capsule",
                        "arguments": {
                            "capsule_token": l1_capsule,
                            "target_level": "L3",
                            "agent_tier": "pro",
                            "environment": "pre",
                            "resonance_key": "mesh-key-42",
                        },
                    },
                }
            ],
        )
        l3_unfolded = json.loads(step3_resp[0]["result"]["content"][0]["text"])  # type: ignore[index]

        # Assert
        assert q_l0_payload["resolution"] == "L0"
        assert q_l0_payload["matches"][0]["layer"] == "dept-security"
        assert l1_unfolded["unfolded_level"] == "L1"
        assert "Verify every webhook signature" in l1_unfolded["content"]["axiom_skeleton"]
        assert "error" in flash_blocked
        assert l3_unfolded["unfolded_level"] == "L3"
        assert l3_unfolded["unfold_chain"] == ["L1->L2", "L2->L3"]
        assert len(l3_unfolded["content"]["linked_l3_documents"]) == 1
        assert l3_unfolded["content"]["effective_guardrails"] == [
            "corp-baseline-guard",
            "dept-zero-trust-guard",
            "pre-read-only-guard",
        ]

    def test_e2e_agnostic_multi_layer_surface_projection_and_template_unfolding(
        self, tmp_path: Path
    ) -> None:
        """Verify 0..N layer surface weaving, precedence ordering, pruning, and L3 unfolding."""
        # Arrange
        hub_dir = tmp_path / "enterprise_hub"
        hub_logs = tmp_path / "enterprise_logs"
        _create_node_fixture(
            hub_dir,
            layer_id="acme-corp-engineering",
            layer_role="corporate",
            packages=["git", "python3"],
            manifest_extra={
                "precedence": 10,
                "baseline_guardrails": ["corp-clean-architecture-gate"],
                "surface_bindings": [
                    {
                        "binding_id": "corp-presentation-baseline",
                        "target_globs": ["templates/**"],
                        "architectural_planes": ["presentation"],
                        "scopes": ["*"],
                        "traits": [],
                        "mode": "transversal",
                        "rule_files": ["antigravity/.gemini/config/AGENTS.md"],
                        "canonical_templates": [],
                        "invariants": ["Zero inline style blocks in HTML templates"],
                    }
                ],
            },
        )

        legal_sub = hub_dir / "layers" / "statutory-compliance"
        _create_node_fixture(
            legal_sub,
            layer_id="acme-statutory-compliance",
            layer_role="domain-policy",
            packages=[],
            manifest_extra={
                "precedence": 5,
                "baseline_guardrails": ["statutory-gdpr-eu-2016-679"],
                "surface_bindings": [
                    {
                        "binding_id": "statutory-checkout-disclosure",
                        "target_globs": ["templates/checkout/**"],
                        "architectural_planes": ["presentation"],
                        "scopes": ["checkout"],
                        "traits": ["pii", "financial"],
                        "mode": "authoritative",
                        "rule_files": ["docs/checkout_disclosure.md"],
                        "canonical_templates": ["templates/legal/withdrawal_notice.html"],
                        "invariants": [
                            "EU Consumer Rights Directive 14-day withdrawal disclosure required"
                        ],
                    }
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
            layer_id="acme-design-brand",
            layer_role="department",
            packages=[],
            manifest_extra={
                "precedence": 30,
                "baseline_guardrails": ["brand-a11y-wcag-aa"],
                "surface_bindings": [
                    {
                        "binding_id": "brand-design-tokens",
                        "target_globs": ["templates/**"],
                        "architectural_planes": ["presentation"],
                        "scopes": ["*"],
                        "traits": [],
                        "mode": "transversal",
                        "rule_files": ["antigravity/.gemini/config/AGENTS.md"],
                        "canonical_templates": [],
                        "invariants": ["Use semantic design tokens and 4.5:1 contrast"],
                    }
                ],
            },
        )

        logistics_sub = hub_dir / "layers" / "warehouse-logistics"
        _create_node_fixture(
            logistics_sub,
            layer_id="acme-warehouse-logistics",
            layer_role="department",
            packages=[],
            manifest_extra={
                "precedence": 40,
                "surface_bindings": [
                    {
                        "binding_id": "warehouse-fulfillment-domain",
                        "target_globs": ["src/fulfillment/**"],
                        "architectural_planes": ["domain"],
                        "scopes": ["fulfillment"],
                        "traits": [],
                        "mode": "authoritative",
                        "rule_files": ["antigravity/.gemini/config/AGENTS.md"],
                    }
                ],
            },
        )

        # Act
        batch_resp = _run_mcp_stdio_batch(
            hub_dir,
            hub_logs,
            [
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {
                        "name": "resolve_surface_governance",
                        "arguments": {
                            "target_path": "templates/checkout/summary.html",
                            "traits": ["pii", "financial"],
                        },
                    },
                }
            ],
        )
        proj = json.loads(batch_resp[0]["result"]["content"][0]["text"])  # type: ignore[index]
        legal_capsule = proj["resolved_bindings"][0]["sections"][1]["capsule_token"]

        unfold_resp = _run_mcp_stdio_batch(
            hub_dir,
            hub_logs,
            [
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {
                        "name": "unfold_context_capsule",
                        "arguments": {
                            "capsule_token": legal_capsule,
                            "target_level": "L3",
                            "agent_tier": "inherit",
                        },
                    },
                }
            ],
        )
        unfolded_l3 = json.loads(unfold_resp[0]["result"]["content"][0]["text"])  # type: ignore[index]

        # Assert
        assert proj["participating_layers_count"] == 3
        assert proj["pruned_layers_count"] == 1
        assert proj["pruned_layers"][0]["layer"] == "warehouse-logistics"
        assert [b["layer"] for b in proj["resolved_bindings"]] == [
            "statutory-compliance",
            "root",
            "design-brand",
        ]
        assert [b["precedence"] for b in proj["resolved_bindings"]] == [5, 10, 30]
        assert [b["resolution"] for b in proj["resolved_bindings"]] == ["L2", "L1", "L1"]
        assert proj["canonical_templates"] == [
            "statutory-compliance:templates/legal/withdrawal_notice.html"
        ]
        assert unfolded_l3["unfolded_level"] == "L3"
        assert (
            "14-day statutory right of withdrawal"
            in unfolded_l3["content"]["linked_l3_documents"][0]["excerpt"]
        )
