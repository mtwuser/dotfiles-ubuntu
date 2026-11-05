"""Unit tests for dotfiles_mcp/capsules/tools_compaction.py.

Specification: docs/architecture/04_compaction_surface_and_promotion_engines.md
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
from dotfiles_mcp.capsules.tools_compaction import (
    infer_epistemic_grade,
    verify_epistemic_context_claims,
)
from dotfiles_mcp.mcp_node.server import DotfilesMCPServer

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
        tpl_skills = tmp_path / "templates" / "fastapi-hexagonal" / "skills" / "start"
        tpl_skills.mkdir(parents=True)
        (tpl_skills / "SKILL.md").write_text("# Start Skill\nBoot uvicorn.\n", encoding="utf-8")
        (tmp_path / "README.md").write_text(
            "# Root Readme\n## Topology Overview\nDirect 3-tier hierarchy.\n", encoding="utf-8"
        )
        corp_dir = tmp_path / "corporate"
        corp_dir.mkdir()
        (corp_dir / "ledger.md").write_text("# Ledger\n## Patent Asset\nPAT-01\n", encoding="utf-8")
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
                {
                    "query": "Lead prose",
                    "scope": "all",
                    "resolution": "L2",
                    "target_path": "README.md",
                },
            )["content"][0]["text"]
        )
        q_readme = json.loads(
            server.call_tool(
                "query_governance_rules",
                {
                    "query": "Topology hierarchy absentword",
                    "scope": "all",
                    "resolution": "L2",
                    "target_path": "README.md",
                },
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
        assert q_readme["match_count"] == 1 and q_readme["matches"][0]["file"] == "README.md"
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
        res_multi_kw = json.loads(
            server.call_tool(
                "query_governance_rules",
                {"query": "Cap15 and cap15word", "scope": "docs", "resolution": "L0"},
            )["content"][0]["text"]
        )
        res_multi_miss = json.loads(
            server.call_tool(
                "query_governance_rules",
                {
                    "query": "Cap15 and absentkeyword",
                    "scope": "docs",
                    "resolution": "L0",
                    "layer": "root",
                },
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
        assert res_multi_kw["total_matches_found"] == 15
        assert res_multi_miss["total_matches_found"] == 0

    def test_query_governance_rules_with_dmcp_branch_ref_projection(self) -> None:
        """Query governance rules from a Git branch_ref with zero checkout via DMCP."""
        # Arrange
        server = DotfilesMCPServer()

        # Act
        res_branch = json.loads(
            server.call_tool(
                "query_governance_rules",
                {
                    "query": "AAA",
                    "scope": "global",
                    "resolution": "L0",
                    "branch_ref": "HEAD",
                },
            )["content"][0]["text"]
        )

        # Assert
        assert res_branch["match_count"] >= 1
        assert res_branch["dmcp_projection"]["branch_ref"] == "HEAD"
        assert res_branch["dmcp_projection"]["zero_checkout"] is True
        assert len(res_branch["dmcp_projection"]["commit_sha"]) >= 7

    def test_infer_epistemic_grade_and_verify_epistemic_context_claims(
        self,
        tmp_path: Path,
    ) -> None:
        """Infer E3..E0 grades, filter by min_epistemic_grade, and verify epistemic claims."""
        # Arrange
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        l3_file = docs_dir / "substrate.md"
        l3_file.write_text("# Deep Substrate\nFormula: x <= 10.\n", encoding="utf-8")
        (docs_dir / "mixed.md").write_text(
            "# Mixed\n"
            "## Draft Idea [E0]\nepword draft\n"
            "## Contextual Guide\nepword guide\n"
            "## Protocol Contract\nSpecification: docs/substrate.md\nepword [L3](substrate.md)\n"
            "## Core Invariant\n**Mandate:** epword axiom\n",
            encoding="utf-8",
        )
        (docs_dir / "guides").mkdir()
        (docs_dir / "guides/tutor.md").write_text(
            "# Tutor Guide\n## Intro Lesson\nepword socratic lesson\n", encoding="utf-8"
        )
        server = DotfilesMCPServer(repo_dir=tmp_path)

        # Act
        g_e0, _ = infer_epistemic_grade("BACKLOG.md", "Item", "body")
        g_e3, _ = infer_epistemic_grade("AGENTS.md", "Rule", "body")
        g_e2, _ = infer_epistemic_grade("docs/reference/01.md", "Sec", "body")
        g_e1, _ = infer_epistemic_grade("docs/guides/01.md", "Overview", "body")
        res_all = json.loads(
            server.call_tool(
                "query_governance_rules",
                {"query": "epword", "scope": "docs", "resolution": "L0"},
            )["content"][0]["text"]
        )
        (tmp_path / ".agents").mkdir(exist_ok=True)
        (tmp_path / ".agents/SESSION.md").write_text(
            "# Session\n- **Human-Stack**: domain-physics:M1\n", encoding="utf-8"
        )
        res_acad = json.loads(
            server.call_tool(
                "query_governance_rules",
                {"query": "epword", "scope": "docs", "resolution": "L0"},
            )["content"][0]["text"]
        )
        (tmp_path / ".agents/SESSION.md").unlink()
        res_e2 = json.loads(
            server.call_tool(
                "query_governance_rules",
                {
                    "query": "epword",
                    "scope": "docs",
                    "resolution": "L0",
                    "min_epistemic_grade": "E2",
                },
            )["content"][0]["text"]
        )
        l3_targets = res_e2["matches"][1]["l3_targets"]
        proof_ok = verify_epistemic_context_claims(
            [
                {
                    "claim_id": "c-ok",
                    "epistemic_grade": "E3",
                    "overrides_grade": "E1",
                    "l3_targets": l3_targets,
                    "cut_point": 10.0,
                    "observed_value": 10.0,
                },
                {"claim_id": "c-minimal", "epistemic_grade": "E2"},
            ],
            tmp_path,
        )
        proof_fail = verify_epistemic_context_claims(
            [
                {
                    "claim_id": "c-bad",
                    "epistemic_grade": "E1",
                    "overrides_grade": "E3",
                    "l3_targets": [{"path": "docs/missing.md", "sha256_prefix": "deadbeef"}],
                    "cut_point": 10.0,
                    "observed_value": 11.0,
                    "citation_receipt": "gov-es::docs/mixed.md#CORE@11112222:E3",
                    "official_digest": "99998888",
                }
            ],
            tmp_path,
        )

        # Assert
        assert (g_e3, g_e2, g_e1, g_e0) == ("E3", "E2", "E1", "E0")
        assert res_all["consumer_viewpoint"] == "professional-scientific-m3-m4"
        assert [m["epistemic_grade"] for m in res_all["matches"]] == ["E3", "E2", "E1", "E1", "E0"]
        assert res_acad["consumer_viewpoint"] == "academic-tutor-m1-m2"
        assert res_acad["matches"][0]["file"] == "docs/guides/tutor.md"
        assert [m["epistemic_grade"] for m in res_e2["matches"]] == ["E3", "E2"]
        assert "citation_receipt" in res_e2["matches"][0]
        assert l3_targets[0]["path"] == "docs/substrate.md"
        assert proof_ok["verified"] is True and proof_ok["error_code"] is None
        assert proof_fail["verified"] is False
        assert [v["code"] for v in proof_fail["violations"]] == [
            "EPISTEMIC_PRECEDENCE_VIOLATION",
            "PRIMARY_SOURCE_HASH_MISMATCH",
            "CUT_POINT_BOUNDARY_VIOLATION",
            "CITATION_DRIFT_DETECTED",
        ]
        with pytest.raises(ValueError, match="Invalid min_epistemic_grade"):
            server.call_tool(
                "query_governance_rules", {"query": "epword", "min_epistemic_grade": "E9"}
            )
