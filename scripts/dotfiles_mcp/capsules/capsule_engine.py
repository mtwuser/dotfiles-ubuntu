"""Resonant Chained Context Compaction (rcap1) cryptographic and markdown engine.

Specification: docs/architecture/04_compaction_surface_and_promotion_engines.md
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import time
import zlib
from pathlib import Path, PurePosixPath
from typing import Any

from dotfiles_mcp.core.constants import (
    ALLOWED_READ_PREFIXES,
    ALLOWED_ROOT_FILES,
    BACKTICK_PATH_RE,
    BOLD_TERM_RE,
    CAPSULE_DIGEST_HEX_LEN,
    CAPSULE_HMAC_HEX_LEN,
    CAPSULE_PREFIX,
    CHARS_PER_TOKEN_ESTIMATE,
    CITATION_RECEIPT_REF_RE,
    CODON_MAX_SEMANTIC_TAGS,
    CODON_SLUG_MAX_CHARS,
    CODON_STOPWORDS,
    DEFAULT_EPHEMERAL_TTL_SECONDS,
    DIGEST_REQUIRED_CHANNELS,
    EPOCH_DECIMAL_PLACES,
    EXON_BULLET_MAX_CHARS,
    EXON_HEADING_MAX_CHARS,
    EXON_MAX_BULLETS,
    MAX_EPHEMERAL_TTL_SECONDS,
    MD_LINK_RE,
    MIN_EPHEMERAL_TTL_SECONDS,
    NEXT_LEVEL_MAP,
    SHA256_BLOCK_BYTES,
    WORD_TOKEN_RE,
    ZLIB_MAX_COMPRESSION_LEVEL,
)


class CapsuleError(ValueError):
    """Raised when an rcap1 context capsule fails verification and has already emitted an alert."""


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64url_decode(token: str) -> bytes:
    padding = "=" * ((4 - len(token) % 4) % 4)
    return base64.urlsafe_b64decode((token + padding).encode("ascii"))


def _slugify_codon(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:CODON_SLUG_MAX_CHARS]
    return slug or "section"


def _extract_codon_tags(heading: str, body_text: str) -> list[str]:
    candidates = [heading, *BOLD_TERM_RE.findall(body_text)]
    tags: list[str] = []
    for chunk in candidates:
        for word in WORD_TOKEN_RE.findall(chunk.lower()):
            if word not in CODON_STOPWORDS and word not in tags:
                tags.append(word)
                if len(tags) == CODON_MAX_SEMANTIC_TAGS:
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
            exons.append(stripped[:EXON_HEADING_MAX_CHARS])
        elif not raw.startswith(("  ", "\t")) and (
            stripped.startswith(("- ", "* ")) or re.match(r"^\d+\.\s", stripped)
        ):
            if bullets < EXON_MAX_BULLETS:
                exons.append(stripped[:EXON_BULLET_MAX_CHARS])
                bullets += 1
            else:
                folded += 1
        elif len(exons) == 1:
            exons.append(stripped[:EXON_HEADING_MAX_CHARS])
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
    section_lines: list[str] = []
    current_heading, section_start, in_code = default_heading, 1, False
    for idx, line in enumerate(lines, start=1):
        if line.strip().startswith("```"):
            in_code = not in_code
        if not in_code and line.startswith(("## ", "### ", "#### ")) and section_lines:
            sections.append((current_heading, section_start, idx - 1, section_lines))
            current_heading = line.lstrip("#").strip()
            section_start = idx
            section_lines = [line]
        else:
            if not in_code and line.startswith("# ") and idx == 1:
                current_heading = line.lstrip("#").strip()
            section_lines.append(line)
    if section_lines:
        sections.append((current_heading, section_start, len(lines), section_lines))
    return sections


def _resolve_section_hierarchy(
    lines: list[str],
    start_line: int,
    heading: str,
) -> tuple[int, str]:
    """Return (heading_depth 1..4, hierarchical 'H1 > H2 > H3 > H4' section_path)."""
    ancestors: dict[int, str] = {}
    depth = 1
    in_code = False
    for line in lines[: max(0, start_line)]:
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code = not in_code
            continue
        if not in_code and line.startswith(("# ", "## ", "### ", "#### ")):
            lvl = len(line) - len(line.lstrip("#"))
            ancestors[lvl] = line.lstrip("#").strip()
            for deeper in range(lvl + 1, 5):
                ancestors.pop(deeper, None)
            depth = lvl
    crumb = " > ".join(ancestors[k] for k in sorted(ancestors))
    return depth, crumb or heading


def _extract_l3_links(
    source_file: Path,
    section_text: str,
    layer_root: Path,
) -> list[dict[str, Any]]:
    raw_refs = [m.group(2).split("#")[0].strip() for m in MD_LINK_RE.finditer(section_text)]
    raw_refs.extend(m.group(1).strip() for m in BACKTICK_PATH_RE.finditer(section_text))
    for cm in CITATION_RECEIPT_REF_RE.finditer(section_text):
        raw_refs.extend((f"layers/{cm.group(1)}/{cm.group(2)}", cm.group(2)))
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
                    links.append({
                        "path": rel_str,
                        "bytes": size,
                        "estimated_tokens": max(1, size // CHARS_PER_TOKEN_ESTIMATE),
                        "sha256": hashlib.sha256(raw_bytes).hexdigest()[:CAPSULE_DIGEST_HEX_LEN],
                    })  # fmt: skip
                break
    return links


def _compute_digest16(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:CAPSULE_DIGEST_HEX_LEN]


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
    n_bytes = len(data)
    blocks = (n_bytes + SHA256_BLOCK_BYTES - 1) // SHA256_BLOCK_BYTES
    stream = b"".join(
        hashlib.sha256(key + ctr.to_bytes(4, "big")).digest() for ctr in range(blocks)
    )
    return (int.from_bytes(data, "big") ^ int.from_bytes(stream[:n_bytes], "big")).to_bytes(
        n_bytes, "big"
    )


def _seal_single_capsule(
    header: dict[str, Any],
    inner_payload: dict[str, Any],
    chain_key: bytes,
) -> str:
    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    raw_inner = json.dumps(inner_payload, separators=(",", ":")).encode("utf-8")
    compressed = zlib.compress(raw_inner, level=ZLIB_MAX_COMPRESSION_LEVEL)
    encrypted = _xor_keystream(compressed, chain_key)
    cipher_b64 = _b64url_encode(encrypted)
    signing_input = f"{CAPSULE_PREFIX}.{header_b64}.{cipher_b64}".encode("ascii")
    sig_hex = hmac.new(chain_key, signing_input, hashlib.sha256).hexdigest()[:CAPSULE_HMAC_HEX_LEN]
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


def seal_ephemeral_digest_capsule(
    fork_id: str,
    bot_role: str,
    parent_layer_id: str,
    surface_globs: list[str],
    digest_channels: dict[str, Any],
    *,
    session_key: str,
) -> dict[str, Any]:
    """Seal an Ephemeral Bot's 4-Channel Executive Digest into an rcap1 return capsule."""
    missing = [ch for ch in DIGEST_REQUIRED_CHANNELS if ch not in digest_channels]
    if missing:
        raise ValueError(f"Missing required 4-Channel Executive Digest fields: {missing}")
    clean_key = session_key.strip()
    if not clean_key:
        raise ValueError("Missing session_resonance_key for ephemeral digest sealing")
    raw_digest = json.dumps(digest_channels, sort_keys=True, separators=(",", ":"))
    digest_hash = _compute_digest16(fork_id, bot_role, parent_layer_id, raw_digest)
    chain_key = _derive_chain_key(
        clean_key.encode("utf-8"), fork_id, "L1", digest_hash, parent_layer_id
    )
    header = {
        "v": 1, "lvl": "L1", "next": "L2", "kind": "ephemeral-digest",
        "iss": fork_id, "parent_iss": parent_layer_id, "role": bot_role, "ph": digest_hash,
    }  # fmt: skip
    inner = {
        "fork_id": fork_id, "bot_role": bot_role, "parent_layer_id": parent_layer_id,
        "surface_globs": list(surface_globs), "digest_sha256": digest_hash,
        "digest": digest_channels,
    }  # fmt: skip
    token = _seal_single_capsule(header, inner, chain_key)
    return {
        "capsule_token": token, "fork_id": fork_id, "bot_role": bot_role,
        "parent_layer_id": parent_layer_id, "digest_sha256": digest_hash,
        "surface_globs": list(surface_globs),
    }  # fmt: skip


def unseal_ephemeral_digest_capsule(
    capsule_token: str,
    *,
    expected_parent_layer_id: str,
    active_fork_meta: dict[str, Any] | None,
) -> dict[str, Any]:
    """Verify and decapsulate an Ephemeral Bot's rcap1 return digest while its lease is active."""
    header, signing_prefix, cipher_bytes, sig_hex = _parse_capsule_envelope(capsule_token)
    if header.get("kind") != "ephemeral-digest" or header.get("parent_iss") != (
        expected_parent_layer_id
    ):
        raise CapsuleError("CAPSULE_ISSUER_MISMATCH: invalid ephemeral digest parent issuer")
    if active_fork_meta is None or not str(active_fork_meta.get("session_resonance_key", "")):
        raise CapsuleError(
            "EPHEMERAL_LEASE_EXPIRED_OR_SHREDDED: ephemeral fork lease is inactive; "
            "session resonance key has been crypto-shredded"
        )
    fork_id = str(header.get("iss", ""))
    bot_role = str(header.get("role", ""))
    digest_hash = str(header.get("ph", ""))
    session_key = str(active_fork_meta["session_resonance_key"]).strip()
    chain_key = _derive_chain_key(
        session_key.encode("utf-8"), fork_id, "L1", digest_hash, expected_parent_layer_id
    )
    expected_sig = hmac.new(chain_key, signing_prefix.encode("ascii"), hashlib.sha256).hexdigest()[
        :CAPSULE_HMAC_HEX_LEN
    ]
    if not hmac.compare_digest(sig_hex, expected_sig):
        raise CapsuleError("CAPSULE_SIGNATURE_INVALID: ephemeral digest HMAC verification failed")
    inner = json.loads(zlib.decompress(_xor_keystream(cipher_bytes, chain_key)).decode("utf-8"))
    allowed_globs = list(active_fork_meta.get("target_globs") or inner.get("surface_globs") or [])
    ch2 = inner.get("digest", {}).get("channel_2_affected_surface", [])
    files = ch2 if isinstance(ch2, list) else []
    if allowed_globs and "**" not in allowed_globs:
        for fpath in files:
            p = PurePosixPath(str(fpath).lstrip("/"))
            if not any(p.match(g) or str(p).startswith(g.rstrip("/*")) for g in allowed_globs):
                raise CapsuleError(
                    f"SURFACE_BOUNDARY_VIOLATION: reported file {fpath!r} escapes leased "
                    f"surface_globs {allowed_globs}"
                )
    return {
        "verified": True,
        "fork_id": fork_id,
        "bot_role": bot_role,
        "parent_layer_id": expected_parent_layer_id,
        "digest_sha256": digest_hash,
        "surface_globs": allowed_globs,
        "digest": inner["digest"],
    }


def seal_dmcp_context_frame(
    repo_id: str,
    branch_ref: str,
    commit_sha: str,
    task_step_id: str,
    surface_globs: list[str],
    *,
    parent_frame_hash: str = "genesis",
    ttl_seconds: int = DEFAULT_EPHEMERAL_TTL_SECONDS,
    now_epoch: float | None = None,
    session_key: str,
) -> dict[str, Any]:
    """Seal a DMCP Decision-Tree Context Frame into an HMAC-signed rcap1 token."""
    clean_repo = repo_id.strip()
    clean_branch = branch_ref.strip()
    clean_sha = commit_sha.strip()
    clean_step = task_step_id.strip()
    if not (clean_repo and clean_branch and clean_sha and clean_step):
        raise ValueError("Missing required DMCP context frame identifiers")
    clean_key = session_key.strip()
    if not clean_key:
        raise ValueError("Missing session_resonance_key for DMCP context frame sealing")
    now = now_epoch if now_epoch is not None else time.time()
    bounded_ttl = max(MIN_EPHEMERAL_TTL_SECONDS, min(ttl_seconds, MAX_EPHEMERAL_TTL_SECONDS))
    ttl_epoch = round(now + bounded_ttl, EPOCH_DECIMAL_PLACES)
    globs = list(surface_globs) if surface_globs else ["**"]
    parent_hash = parent_frame_hash.strip() or "genesis"
    frame_hash = _compute_digest16(
        clean_repo, clean_branch, clean_sha, clean_step, parent_hash, ",".join(globs)
    )
    chain_key = _derive_chain_key(
        clean_key.encode("utf-8"), clean_repo, "L1", frame_hash, clean_branch
    )
    header = {
        "v": 1, "lvl": "L1", "next": "L2", "kind": "dmcp-context-frame",
        "iss": clean_repo, "br": clean_branch, "step": clean_step, "ph": frame_hash,
    }  # fmt: skip
    inner = {
        "repo_id": clean_repo, "branch_ref": clean_branch, "commit_sha": clean_sha,
        "task_step_id": clean_step, "parent_frame_hash": parent_hash,
        "frame_hash": frame_hash, "surface_globs": globs, "ttl_epoch": ttl_epoch,
    }  # fmt: skip
    token = _seal_single_capsule(header, inner, chain_key)
    return {
        "context_frame_token": token, "frame_hash": frame_hash,
        "parent_frame_hash": parent_hash, "repo_id": clean_repo,
        "branch_ref": clean_branch, "commit_sha": clean_sha,
        "task_step_id": clean_step, "surface_globs": globs, "ttl_epoch": ttl_epoch,
    }  # fmt: skip


def verify_dmcp_context_frame(
    context_frame_token: str,
    *,
    expected_repo_id: str,
    session_key: str,
    target_path: str = "",
    expected_parent_frame_hash: str | None = None,
    now_epoch: float | None = None,
    fallback_branch: str = "master",
) -> dict[str, Any]:
    """Verify a DMCP rcap1 context_frame_token or fail-closed to fallback_branch."""

    def _fail(reason: str) -> dict[str, Any]:
        return {
            "verified": False, "error_code": "DMCP_CONTEXT_FRAME_INVALID",
            "reason": reason, "effective_branch_ref": fallback_branch, "fallback_activated": True,
        }  # fmt: skip

    try:
        header, signing_prefix, cipher_bytes, sig_hex = _parse_capsule_envelope(context_frame_token)
    except ValueError as exc:
        return _fail(str(exc))
    clean_key = session_key.strip()
    if (
        header.get("kind") != "dmcp-context-frame"
        or header.get("iss") != expected_repo_id.strip()
        or not clean_key
    ):
        return _fail("DMCP frame issuer, kind, or session key mismatch")
    chain_key = _derive_chain_key(
        clean_key.encode("utf-8"),
        str(header["iss"]),
        "L1",
        str(header.get("ph", "")),
        str(header.get("br", "")),
    )
    expected_sig = hmac.new(chain_key, signing_prefix.encode("ascii"), hashlib.sha256).hexdigest()[
        :CAPSULE_HMAC_HEX_LEN
    ]
    if not hmac.compare_digest(sig_hex, expected_sig):
        return _fail("DMCP context frame HMAC signature verification failed")
    inner = json.loads(zlib.decompress(_xor_keystream(cipher_bytes, chain_key)).decode("utf-8"))
    now = now_epoch if now_epoch is not None else time.time()
    if now > float(inner.get("ttl_epoch", 0.0)):
        return _fail("DMCP context frame TTL expired")
    if expected_parent_frame_hash is not None and (
        str(inner.get("parent_frame_hash", "")) != expected_parent_frame_hash.strip()
    ):
        return _fail("DMCP parent_frame_hash lineage mismatch")
    allowed_globs = list(inner.get("surface_globs") or ["**"])
    clean_target = target_path.strip().lstrip("/")
    if clean_target and "**" not in allowed_globs and "*" not in allowed_globs:
        p = PurePosixPath(clean_target)
        if not any(p.match(g) or str(p).startswith(g.rstrip("/*")) for g in allowed_globs):
            return _fail(f"Target path {target_path!r} escapes frame surface_globs {allowed_globs}")
    return {
        "verified": True, "error_code": None, "reason": "verified",
        "effective_branch_ref": str(inner["branch_ref"]), "fallback_activated": False,
        "repo_id": str(inner["repo_id"]), "commit_sha": str(inner["commit_sha"]),
        "task_step_id": str(inner["task_step_id"]), "frame_hash": str(inner["frame_hash"]),
        "parent_frame_hash": str(inner["parent_frame_hash"]),
        "surface_globs": allowed_globs, "ttl_epoch": float(inner["ttl_epoch"]),
    }  # fmt: skip
