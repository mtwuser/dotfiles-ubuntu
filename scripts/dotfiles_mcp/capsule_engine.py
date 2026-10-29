"""Resonant Chained Context Compaction (rcap1) cryptographic and markdown engine.

Specification: docs/architecture/04_compaction_surface_and_promotion_engines.md
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import zlib
from pathlib import Path
from typing import Any

from dotfiles_mcp.constants import (
    ALLOWED_READ_PREFIXES,
    ALLOWED_ROOT_FILES,
    BACKTICK_PATH_RE,
    BOLD_TERM_RE,
    CAPSULE_PREFIX,
    CODON_STOPWORDS,
    MD_LINK_RE,
    NEXT_LEVEL_MAP,
    WORD_TOKEN_RE,
)


class CapsuleError(ValueError):
    """Raised when an rcap1 context capsule fails verification and has already emitted an alert."""


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64url_decode(token: str) -> bytes:
    padding = "=" * ((4 - len(token) % 4) % 4)
    return base64.urlsafe_b64decode((token + padding).encode("ascii"))


def _slugify_codon(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:36]
    return slug or "section"


def _extract_codon_tags(heading: str, body_text: str) -> list[str]:
    candidates = [heading, *BOLD_TERM_RE.findall(body_text)]
    tags: list[str] = []
    for chunk in candidates:
        for word in WORD_TOKEN_RE.findall(chunk.lower()):
            if word not in CODON_STOPWORDS and word not in tags:
                tags.append(word)
                if len(tags) == 5:
                    return tags
    return tags


def _extract_axiom_skeleton(heading: str, body_lines: list[str]) -> str:
    exons: list[str] = [f"## {heading}"]
    bullets = 0
    folded = 0
    in_code = False
    for raw in body_lines:
        stripped = raw.strip()
        if stripped.startswith("```"):
            in_code = not in_code
            folded += 1
            continue
        if in_code or not stripped or stripped.startswith(("#", "|", "---")):
            if stripped and not stripped.startswith("#"):
                folded += 1
            continue
        if stripped.startswith(">") or stripped.startswith(("**Mandate", "**Description")):
            exons.append(stripped[:160])
        elif stripped.startswith(("- ", "* ")) or re.match(r"^\d+\.\s", stripped):
            if bullets < 4:
                exons.append(stripped[:120])
                bullets += 1
            else:
                folded += 1
        elif len(exons) == 1:
            exons.append(stripped[:160])
        else:
            folded += 1
    if folded > 0:
        exons.append(f"[+{folded} detail/table/code lines folded in rcap1:L1]")
    return "\n".join(exons)


def _iter_markdown_sections(
    lines: list[str],
    default_heading: str,
) -> list[tuple[str, int, int, list[str]]]:
    sections: list[tuple[str, int, int, list[str]]] = []
    current_heading = default_heading
    section_start = 1
    section_lines: list[str] = []
    for idx, line in enumerate(lines, start=1):
        if line.startswith(("## ", "### ", "#### ")) and section_lines:
            sections.append((current_heading, section_start, idx - 1, section_lines))
            current_heading = line.lstrip("#").strip()
            section_start = idx
            section_lines = [line]
        else:
            if line.startswith("# ") and idx == 1:
                current_heading = line.lstrip("#").strip()
            section_lines.append(line)
    if section_lines:
        sections.append((current_heading, section_start, len(lines), section_lines))
    return sections


def _extract_l3_links(
    source_file: Path,
    section_text: str,
    layer_root: Path,
) -> list[dict[str, Any]]:
    raw_refs = [m.group(2).split("#")[0].strip() for m in MD_LINK_RE.finditer(section_text)]
    raw_refs.extend(m.group(1).strip() for m in BACKTICK_PATH_RE.finditer(section_text))
    seen: set[str] = set()
    links: list[dict[str, Any]] = []
    root_resolved = layer_root.resolve()
    for ref in raw_refs:
        if not ref or ref.startswith(("http://", "https://", "mailto:")):
            continue
        for base in (source_file.parent, root_resolved):
            cand = (base / ref).resolve()
            if cand.is_file() and cand.is_relative_to(root_resolved):
                rel_str = str(cand.relative_to(root_resolved)).replace("\\", "/")
                if rel_str not in seen and (
                    rel_str in ALLOWED_ROOT_FILES
                    or any(rel_str.startswith(p) for p in ALLOWED_READ_PREFIXES)
                ):
                    seen.add(rel_str)
                    raw_bytes = cand.read_bytes()
                    size = len(raw_bytes)
                    links.append(
                        {
                            "path": rel_str,
                            "bytes": size,
                            "estimated_tokens": max(1, size // 4),
                            "sha256": hashlib.sha256(raw_bytes).hexdigest()[:16],
                        }
                    )
                break
    return links


def _compute_digest16(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16]


def _derive_chain_key(
    secret: bytes,
    layer_name: str,
    level: str,
    parent_hash: str,
    env_scope: str,
) -> bytes:
    ctx = f"rcap1-key:{layer_name}:{level}:{parent_hash}:{env_scope}".encode()
    return hmac.new(secret, ctx, hashlib.sha256).digest()


def _xor_keystream(data: bytes, key: bytes) -> bytes:
    out = bytearray(len(data))
    offset = 0
    counter = 0
    while offset < len(data):
        block = hashlib.sha256(key + counter.to_bytes(4, "big")).digest()
        chunk_len = min(32, len(data) - offset)
        for idx in range(chunk_len):
            out[offset + idx] = data[offset + idx] ^ block[idx]
        offset += chunk_len
        counter += 1
    return bytes(out)


def _seal_single_capsule(
    header: dict[str, Any],
    inner_payload: dict[str, Any],
    chain_key: bytes,
) -> str:
    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    raw_inner = json.dumps(inner_payload, separators=(",", ":")).encode("utf-8")
    compressed = zlib.compress(raw_inner, level=9)
    encrypted = _xor_keystream(compressed, chain_key)
    cipher_b64 = _b64url_encode(encrypted)
    signing_input = f"{CAPSULE_PREFIX}.{header_b64}.{cipher_b64}".encode("ascii")
    sig_hex = hmac.new(chain_key, signing_input, hashlib.sha256).hexdigest()[:24]
    return f"{CAPSULE_PREFIX}.{header_b64}.{cipher_b64}.{sig_hex}"


def _parse_capsule_envelope(capsule_token: str) -> tuple[dict[str, Any], str, bytes, str]:
    parts = capsule_token.strip().split(".")
    if len(parts) != 4 or parts[0] != CAPSULE_PREFIX:
        raise ValueError("Malformed rcap1 context capsule envelope")
    _, header_b64, cipher_b64, sig_hex = parts
    try:
        header = json.loads(_b64url_decode(header_b64).decode("utf-8"))
        cipher_bytes = _b64url_decode(cipher_b64)
    except Exception as exc:
        raise ValueError(f"Invalid base64 or JSON in rcap1 capsule header: {exc}") from exc
    if not isinstance(header, dict) or header.get("lvl") not in NEXT_LEVEL_MAP:
        raise ValueError("Invalid or unsupported rcap1 capsule header level")
    return header, f"{CAPSULE_PREFIX}.{header_b64}.{cipher_b64}", cipher_bytes, sig_hex
