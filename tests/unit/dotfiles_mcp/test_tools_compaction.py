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
        assert q_l2_short["truncated"] is False
        assert q_l2_trunc["truncated"] is True

    def test_query_governance_rules_exact_boundary_cutpoints_for_excerpt_and_match_cap(
        self,
        tmp_path: Path,
    ) -> None:
        """Verify 1500 vs 1501 L2 char cap and 15 vs 16 match cap truncation cut-points."""
        # Arrange
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        exact_1500 = "exact1500 " + ("x" * (1500 - len("## Exact1500\nexact1500 ")))
        over_1501 = "over1501 " + ("y" * (1501 - len("## Over1501\nover1501 ")))
        sections_15 = "".join(f"## Cap15 Sec {i}\ncap15word\n" for i in range(15))
        sections_16 = "".join(f"## Cap16 Sec {i}\ncap16word\n" for i in range(16))
        (docs_dir / "bounds.md").write_text(
            f"# Bounds\n## Exact1500\n{exact_1500}\n## Over1501\n{over_1501}\n"
            + sections_15
            + sections_16,
            encoding="utf-8",
        )
        server = DotfilesMCPServer(repo_dir=tmp_path)

        # Act
        res_1500 = json.loads(
            server.call_tool(
                "query_governance_rules",
                {"query": "exact1500", "scope": "docs", "resolution": "L2"},
            )["content"][0]["text"]
        )
        res_1501 = json.loads(
            server.call_tool(
                "query_governance_rules",
                {"query": "over1501", "scope": "docs", "resolution": "L2"},
            )["content"][0]["text"]
        )
        res_15_matches = json.loads(
            server.call_tool(
                "query_governance_rules",
                {"query": "cap15word", "scope": "docs", "resolution": "L0"},
            )["content"][0]["text"]
        )
        res_16_matches = json.loads(
            server.call_tool(
                "query_governance_rules",
                {"query": "cap16word", "scope": "docs", "resolution": "L0"},
            )["content"][0]["text"]
        )

        # Assert
        assert len(res_1500["matches"][0]["excerpt"]) == 1500
        assert res_1500["truncated"] is False
        assert res_1500["warnings"] == []
        assert res_1501["truncated"] is True
        assert res_1501["warnings"][0]["code"] == "RESPONSE_TRUNCATED"
        assert res_15_matches["total_matches_found"] == 15
        assert res_15_matches["truncated"] is False
        assert res_15_matches["warnings"] == []
        assert res_16_matches["total_matches_found"] == 16
        assert res_16_matches["truncated"] is True
        assert res_16_matches["warnings"][0]["code"] == "RESPONSE_TRUNCATED"
