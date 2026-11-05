"""Unit tests for dotfiles_mcp/capsules/capsule_engine.py.

Specification: docs/architecture/04_compaction_surface_and_promotion_engines.md
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from dotfiles_mcp.capsules import capsule_engine

if TYPE_CHECKING:
    from pathlib import Path


class TestCapsuleEngine:
    """Verify rcap1 codon/skeleton extraction, L3 link scanning, and cryptographic sealing."""

    def test_slugify_codon_and_extract_codon_tags_stop_at_five(self) -> None:
        """Slugify symbol-only headings to 'section' and cap extracted codon tags at 5."""
        # Arrange
        heading = "Resonant Section for the Resonant"
        body = "**alpha** **beta** **gamma** **delta** **epsilon** **zeta**"

        # Act
        empty_slug = capsule_engine._slugify_codon("!!!")
        tags = capsule_engine._extract_codon_tags(heading, body)
        short_tags = capsule_engine._extract_codon_tags("Alpha", "**beta**")
        dig = capsule_engine._compute_digest16("a", "b")

        # Assert
        assert empty_slug == "section"
        assert len(tags) == 5
        assert tags[0] == "resonant"
        assert short_tags == ["alpha", "beta"]
        assert len(dig) == 16

    def test_extract_axiom_skeleton_folds_tables_code_and_overflow_bullets(self) -> None:
        """Retain quotes, mandates, and up to 4 bullets while folding code and tables."""
        # Arrange
        lines = [
            "## Strict Architecture",
            '> *"Core mandate quote"*',
            "**Mandate:** Enforce clean boundaries.",
            "| Col A | Col B |",
            "|---|---|",
            "```python",
            "x = 1",
            "```",
            "- Bullet 1",
            "  - Indented Sub-Bullet 1a folded",
            "- Bullet 2",
            "- Bullet 3",
            "- Bullet 4",
            "- Bullet 5 overflow",
            "Trailing prose folded.",
        ]

        # Act
        skeleton = capsule_engine._extract_axiom_skeleton("Strict Architecture", lines)
        unfolded_skeleton = capsule_engine._extract_axiom_skeleton(
            "Short Section", ["## Short Section", "- Bullet 1", "- Bullet 2", "- Bullet 3"]
        )
        prose_first = capsule_engine._extract_axiom_skeleton(
            "Prose", ["## Prose", "First prose line.", "Second prose line."]
        )
        secs = capsule_engine._iter_markdown_sections(
            [
                "# Title",
                "Intro",
                "```markdown",
                "## Ignored In Code",
                "```",
                "## Sub 1",
                "Body 1",
                "### Sub 2",
                "Body 2",
            ],
            "Default",
        )
        empty_secs = capsule_engine._iter_markdown_sections([], "Default")
        hier_lines = [
            "# Root Title",
            "```bash",
            "# Ignored Code Comment",
            "```",
            "## Section A",
            "### Sub A1",
            "#### Deep A1a",
            "## Section B",
        ]
        d_deep, p_deep = capsule_engine._resolve_section_hierarchy(hier_lines, 7, "Deep A1a")
        d_reset, p_reset = capsule_engine._resolve_section_hierarchy(hier_lines, 8, "Section B")
        d_none, p_none = capsule_engine._resolve_section_hierarchy(["Plain line"], 1, "Fallback")

        # Assert
        assert "Core mandate quote" in skeleton
        assert "- Bullet 4" in skeleton
        assert "Indented Sub-Bullet 1a" not in skeleton
        assert "Bullet 5" not in skeleton
        assert "folded in rcap1:L1]" in skeleton
        assert "[+" not in unfolded_skeleton
        assert "First prose line." in prose_first
        assert len(secs) == 3 and empty_secs == []
        assert (d_deep, p_deep) == (4, "Root Title > Section A > Sub A1 > Deep A1a")
        assert (d_reset, p_reset) == (2, "Root Title > Section B")
        assert (d_none, p_none) == (1, "Fallback")

    def test_seal_and_parse_capsule_envelope_roundtrip_and_invalid_tokens(
        self,
        tmp_path: Path,
    ) -> None:
        """Seal an rcap1 capsule envelope and reject malformed or unsupported headers."""
        # Arrange
        key = capsule_engine._derive_chain_key(b"secret", "root", "L0", "ph1", "all")
        hdr = {"lvl": "L0", "next": "L1", "ph": "ph1"}
        inner = {"ph": "ph1", "f": "docs/spec.md"}
        sealed = capsule_engine._seal_single_capsule(hdr, inner, key)
        bad_lvl = f"rcap1.{capsule_engine._b64url_encode(b'{"lvl":"L9"}')}.YWJj.123456"
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        linked = docs_dir / "linked.md"
        linked.write_text("# Linked\n", encoding="utf-8")
        lib_ref = tmp_path / "layers/sci-physics/docs/reference"
        lib_ref.mkdir(parents=True)
        (lib_ref / "law.md").write_text("# Law\n", encoding="utf-8")
        (tmp_path / "secret.txt").write_text("deny\n", encoding="utf-8")

        # Act
        parsed_hdr, signing_prefix, cipher_bytes, sig_hex = capsule_engine._parse_capsule_envelope(
            sealed
        )
        links = capsule_engine._extract_l3_links(
            docs_dir / "source.md",
            "See [Linked](linked.md), [Dup](docs/linked.md), [Secret](secret.txt), "
            "[Missing](missing.md), `sci-physics::docs/reference/law.md#sec@11223344:E3`, "
            "and [Web](https://example.com).",
            tmp_path,
        )
        with pytest.raises(ValueError, match="Malformed rcap1"):
            capsule_engine._parse_capsule_envelope("invalid-token")
        with pytest.raises(ValueError, match="Invalid base64 or JSON"):
            capsule_engine._parse_capsule_envelope("rcap1.!!!.YWJj.123")
        with pytest.raises(ValueError, match="Invalid or unsupported rcap1"):
            capsule_engine._parse_capsule_envelope(bad_lvl)

        # Assert
        assert parsed_hdr["lvl"] == "L0"
        assert signing_prefix.startswith("rcap1.")
        assert len(cipher_bytes) > 0
        assert len(sig_hex) == 24
        assert [item["path"] for item in links] == [
            "docs/linked.md",
            "layers/sci-physics/docs/reference/law.md",
        ]

    def test_seal_and_unseal_ephemeral_digest_capsule_enforces_crypto_and_surface_gates(
        self,
    ) -> None:
        """Seal and unseal ephemeral 4-Channel Digests and guard against tampering or escape."""
        # Arrange
        valid_digest = {
            "channel_1_domain_state": "Clean",
            "channel_2_affected_surface": ["src/api/v1.py"],
            "channel_3_invariants_and_constraints": ["I1"],
            "channel_4_actionable_delta": ["D1"],
        }
        escaped_digest = {**valid_digest, "channel_2_affected_surface": ["secrets/prod.env"]}
        meta = {"session_resonance_key": "k-eph-1", "target_globs": ["src/api/**"]}

        # Act
        sealed = capsule_engine.seal_ephemeral_digest_capsule(
            "eph-1",
            "security-auditor-bot",
            "dept-sec",
            ["src/api/**"],
            valid_digest,
            session_key="k-eph-1",
        )
        unsealed = capsule_engine.unseal_ephemeral_digest_capsule(
            sealed["capsule_token"],
            expected_parent_layer_id="dept-sec",
            active_fork_meta=meta,
        )
        unsealed_wildcard = capsule_engine.unseal_ephemeral_digest_capsule(
            sealed["capsule_token"],
            expected_parent_layer_id="dept-sec",
            active_fork_meta={"session_resonance_key": "k-eph-1", "target_globs": ["**"]},
        )
        escaped_sealed = capsule_engine.seal_ephemeral_digest_capsule(
            "eph-1",
            "security-auditor-bot",
            "dept-sec",
            ["src/api/**"],
            escaped_digest,
            session_key="k-eph-1",
        )

        # Assert
        assert unsealed["verified"] is True and unsealed_wildcard["verified"] is True
        with pytest.raises(ValueError, match="Missing required 4-Channel"):
            capsule_engine.seal_ephemeral_digest_capsule(
                "eph-1", "bot", "dept-sec", ["**"], {}, session_key="k-eph-1"
            )
        with pytest.raises(ValueError, match="Missing session_resonance_key"):
            capsule_engine.seal_ephemeral_digest_capsule(
                "eph-1", "bot", "dept-sec", ["**"], valid_digest, session_key="   "
            )
        with pytest.raises(capsule_engine.CapsuleError, match="CAPSULE_ISSUER_MISMATCH"):
            capsule_engine.unseal_ephemeral_digest_capsule(
                sealed["capsule_token"],
                expected_parent_layer_id="wrong-parent",
                active_fork_meta=meta,
            )
        with pytest.raises(capsule_engine.CapsuleError, match="EPHEMERAL_LEASE_EXPIRED"):
            capsule_engine.unseal_ephemeral_digest_capsule(
                sealed["capsule_token"],
                expected_parent_layer_id="dept-sec",
                active_fork_meta=None,
            )
        with pytest.raises(capsule_engine.CapsuleError, match="CAPSULE_SIGNATURE_INVALID"):
            capsule_engine.unseal_ephemeral_digest_capsule(
                sealed["capsule_token"],
                expected_parent_layer_id="dept-sec",
                active_fork_meta={"session_resonance_key": "wrong-key"},
            )
        with pytest.raises(capsule_engine.CapsuleError, match="SURFACE_BOUNDARY_VIOLATION"):
            capsule_engine.unseal_ephemeral_digest_capsule(
                escaped_sealed["capsule_token"],
                expected_parent_layer_id="dept-sec",
                active_fork_meta=meta,
            )

    def test_seal_and_verify_dmcp_context_frame_enforces_lineage_ttl_and_fallback(
        self,
    ) -> None:
        """Seal and verify DMCP context frames and fail-closed to master on any violation."""
        # Arrange
        sealed = capsule_engine.seal_dmcp_context_frame(
            "dept-sec",
            "specialty/pci",
            "abc1234",
            "step-1",
            ["src/api/**"],
            now_epoch=1000.0,
            ttl_seconds=120,
            session_key="k-dmcp-1",
        )
        token = sealed["context_frame_token"]

        # Act
        ok_no_target = capsule_engine.verify_dmcp_context_frame(
            token, expected_repo_id="dept-sec", session_key="k-dmcp-1", now_epoch=1050.0
        )
        ok = capsule_engine.verify_dmcp_context_frame(
            token,
            expected_repo_id="dept-sec",
            session_key="k-dmcp-1",
            target_path="src/api/pay.py",
            expected_parent_frame_hash="genesis",
            now_epoch=1050.0,
        )
        bad_env = capsule_engine.verify_dmcp_context_frame(
            "not-a-capsule", expected_repo_id="dept-sec", session_key="k-dmcp-1"
        )
        bad_iss = capsule_engine.verify_dmcp_context_frame(
            token, expected_repo_id="wrong-repo", session_key="k-dmcp-1"
        )
        bad_hmac = capsule_engine.verify_dmcp_context_frame(
            token, expected_repo_id="dept-sec", session_key="wrong-key"
        )
        expired = capsule_engine.verify_dmcp_context_frame(
            token, expected_repo_id="dept-sec", session_key="k-dmcp-1", now_epoch=2000.0
        )
        bad_parent = capsule_engine.verify_dmcp_context_frame(
            token,
            expected_repo_id="dept-sec",
            session_key="k-dmcp-1",
            expected_parent_frame_hash="other-parent",
            now_epoch=1050.0,
        )
        escaped = capsule_engine.verify_dmcp_context_frame(
            token,
            expected_repo_id="dept-sec",
            session_key="k-dmcp-1",
            target_path="secrets/db.env",
            now_epoch=1050.0,
        )

        # Assert
        assert ok["verified"] is True and ok_no_target["verified"] is True
        assert ok["effective_branch_ref"] == "specialty/pci"
        for failed in (bad_env, bad_iss, bad_hmac, expired, bad_parent, escaped):
            assert failed["verified"] is False
            assert failed["error_code"] == "DMCP_CONTEXT_FRAME_INVALID"
            assert failed["effective_branch_ref"] == "master"
            assert failed["fallback_activated"] is True
        with pytest.raises(ValueError, match="Missing required DMCP"):
            capsule_engine.seal_dmcp_context_frame(
                "", "master", "sha", "step", [], session_key="k-dmcp-1"
            )
        with pytest.raises(ValueError, match="Missing session_resonance_key"):
            capsule_engine.seal_dmcp_context_frame(
                "dept-sec", "master", "sha", "step", [], session_key="   "
            )
