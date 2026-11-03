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
            ["# Title", "Intro", "## Sub 1", "Body 1", "### Sub 2", "Body 2"], "Default"
        )
        empty_secs = capsule_engine._iter_markdown_sections([], "Default")

        # Assert
        assert "Core mandate quote" in skeleton
        assert "- Bullet 4" in skeleton
        assert "Bullet 5" not in skeleton
        assert "folded in rcap1:L1]" in skeleton
        assert "[+" not in unfolded_skeleton
        assert "First prose line." in prose_first
        assert len(secs) == 3 and empty_secs == []

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
        (tmp_path / "secret.txt").write_text("deny\n", encoding="utf-8")

        # Act
        parsed_hdr, signing_prefix, cipher_bytes, sig_hex = capsule_engine._parse_capsule_envelope(
            sealed
        )
        links = capsule_engine._extract_l3_links(
            docs_dir / "source.md",
            "See [Linked](linked.md), [Dup](docs/linked.md), [Secret](secret.txt), "
            "[Missing](missing.md), and [Web](https://example.com).",
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
        assert len(links) == 1
        assert links[0]["path"] == "docs/linked.md"

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
