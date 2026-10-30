"""Unit tests for dotfiles_mcp/capsule_engine.py."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from dotfiles_mcp import capsule_engine

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

        # Assert
        assert empty_slug == "section"
        assert len(tags) == 5
        assert tags[0] == "resonant"

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

        # Assert
        assert "Core mandate quote" in skeleton
        assert "- Bullet 4" in skeleton
        assert "Bullet 5" not in skeleton
        assert "folded in rcap1:L1]" in skeleton
        assert "[+" not in unfolded_skeleton

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

        # Act
        parsed_hdr, signing_prefix, cipher_bytes, sig_hex = capsule_engine._parse_capsule_envelope(
            sealed
        )
        links = capsule_engine._extract_l3_links(
            docs_dir / "source.md",
            "See [Linked](linked.md) and [Web](https://example.com).",
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
