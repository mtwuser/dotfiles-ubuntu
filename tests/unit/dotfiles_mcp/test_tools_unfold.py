"""Unit tests for dotfiles_mcp/tools_unfold.py."""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import TYPE_CHECKING

import pytest
from dotfiles_mcp import capsule_engine
from dotfiles_mcp.server import DotfilesMCPServer

if TYPE_CHECKING:
    from pathlib import Path


class TestUnfoldToolsMixin:
    """Verify progressive rcap1 capsule unfolding (L0->L1->L2->L3) and security gates."""

    def test_unfold_context_capsule_progressive_l0_l1_l2_l3_and_diagnostics(
        self,
        tmp_path: Path,
    ) -> None:
        """Unfold rcap1 capsules sequentially from L0 through L3 and record diagnostics."""
        # Arrange
        (tmp_path / "VERSION").write_text("1.7.0\n", encoding="utf-8")
        sys_dir = tmp_path / "system"
        sys_dir.mkdir()
        (sys_dir / "mcp-layer.json").write_text(
            json.dumps(
                {
                    "layer_id": "corp-root",
                    "baseline_guardrails": ["root-guard"],
                    "environments": {
                        "pre": {
                            "access_mode": "strictly-read-only",
                            "default_guardrails": ["pre-guard"],
                        }
                    },
                }
            ),
            encoding="utf-8",
        )
        tpl_rules = tmp_path / "templates" / "fastapi-hexagonal" / "rules"
        tpl_rules.mkdir(parents=True)
        (tpl_rules / "coding.md").write_text("# Coding Rule\nStrict typing.\n", encoding="utf-8")
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "spec.md").write_text(
            "# Main Spec\n## Resonant Section\n"
            "- See [Coding](../templates/fastapi-hexagonal/rules/coding.md)\n"
            + ("Padding text " * 650)
            + "\n",
            encoding="utf-8",
        )
        server = DotfilesMCPServer(repo_dir=tmp_path, log_dir=tmp_path / "logs")

        # Act
        q_l0_resp = (
            server.handle_request(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {
                        "name": "query_governance_rules",
                        "arguments": {
                            "query": "Resonant",
                            "scope": "docs",
                            "resolution": "L0",
                            "environment": "pre",
                            "resonance_key": "secret-123",
                        },
                    },
                }
            )
            or {}
        )
        cap_l0 = json.loads(q_l0_resp["result"]["content"][0]["text"])["matches"][0][
            "capsule_token"
        ]
        inspect_l0 = json.loads(
            server.call_tool(
                "unfold_context_capsule",
                {
                    "capsule_token": cap_l0,
                    "target_level": "L0",
                    "environment": "pre",
                    "resonance_key": "secret-123",
                },
            )["content"][0]["text"]
        )
        unfold_l1_resp = (
            server.handle_request(
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {
                        "name": "unfold_context_capsule",
                        "arguments": {
                            "capsule_token": cap_l0,
                            "agent_tier": "flash",
                            "environment": "pre",
                            "resonance_key": "secret-123",
                        },
                    },
                }
            )
            or {}
        )
        unfold_l1 = json.loads(unfold_l1_resp["result"]["content"][0]["text"])
        unfold_l2 = json.loads(
            server.call_tool(
                "unfold_context_capsule",
                {
                    "capsule_token": unfold_l1["next_capsule_token"],
                    "target_level": "L2",
                    "agent_tier": "inherit",
                    "environment": "pre",
                    "resonance_key": "secret-123",
                },
            )["content"][0]["text"]
        )
        unfold_l3 = json.loads(
            server.call_tool(
                "unfold_context_capsule",
                {
                    "capsule_token": cap_l0,
                    "target_level": "L3",
                    "agent_tier": "pro",
                    "environment": "pre",
                    "resonance_key": "secret-123",
                },
            )["content"][0]["text"]
        )
        diag = json.loads(server.read_resource("dotfiles://mcp/diagnostics")["text"])

        # Assert
        assert inspect_l0["unfolded_level"] == "L0"
        assert inspect_l0["decrypted_hops"] == 0
        assert unfold_l1["unfolded_level"] == "L1"
        assert unfold_l1["unfold_chain"] == ["L0->L1"]
        assert unfold_l2["unfolded_level"] == "L2"
        assert unfold_l2["truncated"] is True
        assert len(unfold_l2["content"]["l3_links"]) == 1
        assert unfold_l3["unfolded_level"] == "L3"
        assert unfold_l3["unfold_chain"] == ["L0->L1", "L1->L2", "L2->L3"]
        assert len(unfold_l3["content"]["linked_l3_documents"]) == 1
        assert "pre-guard" in unfold_l3["content"]["effective_guardrails"]
        assert diag["resonance_compaction_summary"]["queries_by_resolution"]["L0"] == 1
        assert diag["resonance_compaction_summary"]["unfolds_by_target_level"]["L1"] == 1

    def test_unfold_context_capsule_capability_environment_and_tamper_gates(
        self,
        tmp_path: Path,
    ) -> None:
        """Enforce capability tiers, environment bindings, HMAC integrity, and TOCTOU relocation."""
        # Arrange
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        linked_md = docs_dir / "linked.md"
        linked_md.write_text("# Linked L3 Spec\nOriginal L3 body.\n", encoding="utf-8")
        doc_md = docs_dir / "gate.md"
        doc_md.write_text("# Gate\n## !!!\nBody line with [Linked](linked.md).\n", encoding="utf-8")
        server = DotfilesMCPServer(repo_dir=tmp_path, log_dir=tmp_path / "logs")

        q_pro = json.loads(
            server.call_tool(
                "query_governance_rules",
                {
                    "query": "Body",
                    "scope": "docs",
                    "resolution": "L0",
                    "environment": "pro",
                    "resonance_key": "pro-key",
                },
            )["content"][0]["text"]
        )
        cap_pro_l0 = q_pro["matches"][0]["capsule_token"]
        q_default = json.loads(
            server.call_tool(
                "query_governance_rules",
                {"query": "Body", "scope": "docs", "resolution": "L0"},
            )["content"][0]["text"]
        )
        cap_l0_default = q_default["matches"][0]["capsule_token"]

        secret = server._resolve_resonance_secret()
        ck = capsule_engine._derive_chain_key(secret, "root", "L0", "ph1", "all")
        bad_zlib_cipher = capsule_engine._b64url_encode(
            capsule_engine._xor_keystream(b"not-valid-zlib", ck)
        )
        hdr_ph1 = capsule_engine._b64url_encode(
            b'{"lvl":"L0","next":"L1","lyr":"root","env":"all","ph":"ph1"}'
        )
        sig_bad_zlib = hmac.new(
            ck, f"rcap1.{hdr_ph1}.{bad_zlib_cipher}".encode("ascii"), hashlib.sha256
        ).hexdigest()[:24]
        corrupt_zlib_token = f"rcap1.{hdr_ph1}.{bad_zlib_cipher}.{sig_bad_zlib}"

        bad_ph_token = capsule_engine._seal_single_capsule(
            {"lvl": "L0", "next": "L1", "lyr": "root", "env": "all", "ph": "ph1"},
            {"ph": "different-ph"},
            ck,
        )

        # Act
        with pytest.raises(ValueError, match="Malformed rcap1"):
            server.call_tool("unfold_context_capsule", {"capsule_token": "invalid-token"})
        with pytest.raises(ValueError, match="Invalid target_level"):
            server.call_tool(
                "unfold_context_capsule", {"capsule_token": cap_l0_default, "target_level": "L9"}
            )
        with pytest.raises(ValueError, match="Invalid agent_tier"):
            server.call_tool(
                "unfold_context_capsule", {"capsule_token": cap_l0_default, "agent_tier": "invalid"}
            )
        with pytest.raises(ValueError, match="Invalid environment"):
            server.call_tool(
                "unfold_context_capsule",
                {"capsule_token": cap_l0_default, "environment": "invalid"},
            )
        with pytest.raises(ValueError, match="bound to environment"):
            server.call_tool(
                "unfold_context_capsule",
                {"capsule_token": cap_pro_l0, "environment": "dev", "resonance_key": "pro-key"},
            )
        with pytest.raises(ValueError, match="requires an explicit resonance_key"):
            server.call_tool(
                "unfold_context_capsule",
                {"capsule_token": cap_pro_l0, "environment": "pro"},
            )
        with pytest.raises(ValueError, match="signature verification failed"):
            server.call_tool(
                "unfold_context_capsule",
                {"capsule_token": cap_pro_l0, "environment": "pro", "resonance_key": "wrong-key"},
            )
        l1_unfolded = json.loads(
            server.call_tool(
                "unfold_context_capsule", {"capsule_token": cap_l0_default, "target_level": "L1"}
            )["content"][0]["text"]
        )
        cap_l1 = l1_unfolded["next_capsule_token"]
        with pytest.raises(ValueError, match="must be deeper than capsule level"):
            server.call_tool(
                "unfold_context_capsule", {"capsule_token": cap_l1, "target_level": "L1"}
            )
        with pytest.raises(ValueError, match="Agent tier 'flash' is insufficient"):
            server.call_tool(
                "unfold_context_capsule",
                {"capsule_token": cap_l1, "target_level": "L2", "agent_tier": "flash"},
            )
        with pytest.raises(ValueError, match="Agent tier 'inherit' is insufficient"):
            server.call_tool(
                "unfold_context_capsule",
                {
                    "capsule_token": cap_pro_l0,
                    "target_level": "L3",
                    "agent_tier": "inherit",
                    "environment": "pro",
                    "resonance_key": "pro-key",
                },
            )
        with pytest.raises(ValueError, match="Failed to decompress"):
            server.call_tool("unfold_context_capsule", {"capsule_token": corrupt_zlib_token})
        with pytest.raises(ValueError, match="parent hash mismatch"):
            server.call_tool("unfold_context_capsule", {"capsule_token": bad_ph_token})

        doc_md.write_text(
            "# Gate\n\nInserted intro line 1.\nInserted intro line 2.\n## !!!\n"
            "Body line with [Linked](linked.md).\n",
            encoding="utf-8",
        )
        relocated_l1 = json.loads(
            server.call_tool("unfold_context_capsule", {"capsule_token": cap_l0_default})[
                "content"
            ][0]["text"]
        )
        other_node = DotfilesMCPServer(
            repo_dir=tmp_path, layer_id_override="other-service-node", log_dir=tmp_path / "logs"
        )
        err_rpc = (
            other_node.handle_request(
                {
                    "jsonrpc": "2.0",
                    "id": 99,
                    "method": "tools/call",
                    "params": {
                        "name": "unfold_context_capsule",
                        "arguments": {"capsule_token": cap_l0_default},
                    },
                }
            )
            or {}
        )
        linked_md.write_text("# Linked L3 Spec\nMutated L3 content!\n", encoding="utf-8")
        l2_still_ok = json.loads(
            server.call_tool(
                "unfold_context_capsule", {"capsule_token": cap_l1, "target_level": "L2"}
            )["content"][0]["text"]
        )
        with pytest.raises(ValueError, match="chain digest mismatch at L2->L3"):
            server.call_tool(
                "unfold_context_capsule",
                {"capsule_token": l2_still_ok["next_capsule_token"], "target_level": "L3"},
            )
        alerts_text = (tmp_path / "logs" / "mcp_alerts.jsonl").read_text(encoding="utf-8")

        # Assert
        assert relocated_l1["line_drift_relocated"] is True
        assert "Cross-node capsule mismatch" in err_rpc["error"]["message"]
        assert l2_still_ok["unfolded_level"] == "L2"
        assert "CAPSULE_CHAIN_BROKEN" in alerts_text
        assert "CAPSULE_RESONANCE_DENIED" in alerts_text
        assert "CAPSULE_CAPABILITY_INSUFFICIENT" in alerts_text
