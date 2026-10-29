"""Unit tests for dotfiles_mcp/tools_compaction.py."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
from dotfiles_mcp.server import DotfilesMCPServer

if TYPE_CHECKING:
    from pathlib import Path


class TestCompactionToolsMixin:
    """Verify query_governance_rules multi-resolution compaction and rcap1 capsule minting."""

    def test_call_tool_query_governance_rules_handles_empty_query_and_missing_files(
        self,
        tmp_path: Path,
    ) -> None:
        """Reject blank queries and handle missing global/template files gracefully."""
        # Arrange
        server = DotfilesMCPServer(repo_dir=tmp_path)
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        doc_file = docs_dir / "guide.md"
        doc_file.write_text(
            "Intro text without h1\n## Section One\nAlpha keyword\n### Section Two\nBeta\n",
            encoding="utf-8",
        )
        empty_doc = docs_dir / "empty.md"
        empty_doc.write_text("", encoding="utf-8")

        # Act
        with pytest.raises(ValueError, match="non-empty string"):
            server.call_tool("query_governance_rules", {"query": "   "})
        with pytest.raises(ValueError, match="Invalid resolution"):
            server.call_tool("query_governance_rules", {"query": "alpha", "resolution": "L9"})
        with pytest.raises(ValueError, match="Invalid environment"):
            server.call_tool("query_governance_rules", {"query": "alpha", "environment": "bad"})
        res_docs = server.call_tool("query_governance_rules", {"query": "alpha", "scope": "docs"})
        res_global = server.call_tool(
            "query_governance_rules", {"query": "alpha", "scope": "global"}
        )
        res_templates = server.call_tool(
            "query_governance_rules", {"query": "alpha", "scope": "templates"}
        )

        # Assert
        parsed = json.loads(res_docs["content"][0]["text"])
        assert parsed["match_count"] == 1
        assert parsed["matches"][0]["section"] == "Section One"
        assert json.loads(res_global["content"][0]["text"])["match_count"] == 0
        assert json.loads(res_templates["content"][0]["text"])["match_count"] == 0

    def test_query_governance_rules_compaction_resolutions_and_truncation_alerts(
        self,
        tmp_path: Path,
    ) -> None:
        """Mint L0, L1, and L2 capsules and emit RESPONSE_TRUNCATED on >1,500-char L2 sections."""
        # Arrange
        (tmp_path / "VERSION").write_text("1.7.0\n", encoding="utf-8")
        (tmp_path / "bootstrap.sh").write_text("#!/bin/sh\n", encoding="utf-8")
        tpl_rules = tmp_path / "templates" / "fastapi-hexagonal" / "rules"
        tpl_rules.mkdir(parents=True)
        (tpl_rules / "coding.md").write_text("# Coding\nStrict typing.\n", encoding="utf-8")
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        spec_md = docs_dir / "spec.md"
        spec_md.write_text(
            "# Main Spec\n"
            "##1.7.0\n"
            "Lead prose line for symbol-only heading.\n"
            "## Resonant Section for the Resonant\n"
            '> *"Core resonance quote"*\n'
            "**Mandate:** Reuse existing helpers and "
            "**alpha** **beta** **gamma** **delta** **epsilon** **zeta**.\n"
            "| Col A | Col B |\n"
            "|---|---|\n"
            "```python\n"
            "x = 1\n"
            "```\n"
            "- Bullet 1 with [Web](https://example.com) and [Anchor](#top)\n"
            "- Bullet 2 with [Forbidden](../bootstrap.sh) and [Missing](missing.md)\n"
            "- Bullet 3 with [Coding](../templates/fastapi-hexagonal/rules/coding.md)\n"
            "- Bullet 4 with duplicate `templates/fastapi-hexagonal/rules/coding.md`\n"
            "- Bullet 5 folded overflow\n"
            "Extra trailing prose line.\n" + ("Padding text " * 650) + "\n",
            encoding="utf-8",
        )
        server = DotfilesMCPServer(repo_dir=tmp_path, log_dir=tmp_path / "logs")

        # Act
        q_l0 = json.loads(
            server.call_tool(
                "query_governance_rules",
                {
                    "query": "Resonance",
                    "scope": "docs",
                    "resolution": "L0",
                    "environment": "pre",
                    "resonance_key": "secret-123",
                },
            )["content"][0]["text"]
        )
        q_l1 = json.loads(
            server.call_tool(
                "query_governance_rules",
                {
                    "query": "Resonance",
                    "scope": "docs",
                    "resolution": "L1",
                    "include_capsules": False,
                },
            )["content"][0]["text"]
        )
        q_l2_short = json.loads(
            server.call_tool(
                "query_governance_rules",
                {"query": "Lead prose", "scope": "all", "resolution": "L2"},
            )["content"][0]["text"]
        )
        q_l2_trunc = json.loads(
            server.call_tool(
                "query_governance_rules",
                {"query": "Resonance", "scope": "docs", "resolution": "L2"},
            )["content"][0]["text"]
        )

        # Assert
        assert q_l0["resolution"] == "L0"
        assert q_l0["token_compaction_metrics"]["savings_pct"] > 0
        assert "surface_preview" in q_l0["matches"][0]
        assert q_l1["resolution"] == "L1"
        assert q_l1["include_capsules"] is False
        assert q_l1["matches"][0]["capsule_token"] is None
        assert q_l1["token_compaction_metrics"]["capsule_overhead_tokens"] == 0
        assert "folded in rcap1:L1" in q_l1["matches"][0]["axiom_skeleton"]
        assert q_l2_short["match_count"] == 1
        assert q_l2_trunc["truncated"] is True
