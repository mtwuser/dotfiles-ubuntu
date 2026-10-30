"""Multi-resolution governance rule search and rcap1 capsule minting.

Specification: docs/architecture/04_compaction_surface_and_promotion_engines.md
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from dotfiles_mcp.capsule_engine import (
    _compute_digest16,
    _derive_chain_key,
    _extract_axiom_skeleton,
    _extract_codon_tags,
    _extract_l3_links,
    _iter_markdown_sections,
    _seal_single_capsule,
    _slugify_codon,
)
from dotfiles_mcp.constants import (
    LEVEL_MIN_TIER,
    NEXT_LEVEL_MAP,
    VALID_ENVIRONMENTS,
    VALID_RESOLUTIONS,
)
from dotfiles_mcp.manifest_helpers import _read_version
from dotfiles_mcp.node_base import MCPNodeBase


class CompactionToolsMixin(MCPNodeBase):
    """Implements capsule minting and query_governance_rules tool."""

    def _resolve_resonance_secret(self, explicit_key: str | None = None) -> bytes:
        raw_key = (
            (explicit_key or "").strip()
            or os.environ.get("DOTFILES_RESONANCE_KEY", "").strip()
            or f"dotfiles-resonance-v1:{_read_version(self.repo_dir)}"
        )
        return raw_key.encode("utf-8")

    def _build_section_capsule(
        self,
        *,
        resolution: str,
        layer_name: str,
        rel_in_layer: str,
        heading: str,
        start_line: int,
        end_line: int,
        scope: str,
        l1_skeleton: str,
        l2_excerpt: str,
        l2_full: str,
        l3_links: list[dict[str, Any]],
        env_scope: str,
        secret: bytes,
        key_required: bool = False,
    ) -> tuple[dict[str, Any], str]:
        l0_summary = f"[{layer_name}] {rel_in_layer} :: {heading}"
        l3_tokens = sum(int(item["estimated_tokens"]) for item in l3_links) + 60
        cost_map = {
            "L0": max(1, len(l0_summary) // 4),
            "L1": max(1, len(l1_skeleton) // 4),
            "L2": max(1, len(l2_excerpt) // 4),
            "L3": l3_tokens,
        }
        tags = _extract_codon_tags(heading, l2_excerpt)
        promoter_codon = {
            "codon": f"AUG:{scope}:{_slugify_codon(heading)}:UAA",
            "layer": layer_name,
            "tags": tags,
            "l3_links_count": len(l3_links),
            "token_estimates": cost_map,
        }
        l3_paths = [str(item["path"]) for item in l3_links]
        h0 = _compute_digest16(layer_name, rel_in_layer, heading)
        h1 = _compute_digest16(h0, l1_skeleton)
        h2 = _compute_digest16(h1, l2_full)
        h3 = _compute_digest16(
            h2,
            *(f"{item['path']}:{item['sha256']}" for item in l3_links),
        )
        digest_by_level = {"L0": h0, "L1": h1, "L2": h2, "L3": h3}
        issuer_id = str(self._load_layer_manifest().get("layer_id", "root"))
        base_meta = {
            "lyr": layer_name,
            "sc": scope,
            "f": rel_in_layer,
            "s": start_line,
            "e": end_line,
            "env": env_scope,
            "h1": h1,
        }
        next_cap: str | None = None
        capsules_by_level: dict[str, str] = {}
        for lvl in ("L2", "L1", "L0"):
            nxt = NEXT_LEVEL_MAP[lvl]
            ph = digest_by_level[lvl]
            min_tier = "pro" if (env_scope == "pro" and nxt == "L3") else LEVEL_MIN_TIER[nxt]
            hdr = {
                "v": 1,
                "lvl": lvl,
                "next": nxt,
                "iss": issuer_id,
                "lyr": layer_name,
                "sec": heading[:80],
                "codon": promoter_codon["codon"],
                "tags": tags,
                "cost": cost_map,
                "cap": min_tier,
                "env": env_scope,
                "kr": key_required,
                "ph": ph,
            }
            inner_lvl: dict[str, Any] = {
                **base_meta,
                "ph": ph,
                "h_cur": ph,
                "h_next": digest_by_level[nxt],
            }
            if lvl == "L2":
                inner_lvl["l3"] = l3_paths
            else:
                inner_lvl["next_cap"] = next_cap
            ck = _derive_chain_key(secret, layer_name, lvl, ph, env_scope)
            next_cap = _seal_single_capsule(hdr, inner_lvl, ck)
            capsules_by_level[lvl] = next_cap
        return promoter_codon, capsules_by_level[resolution]

    def _tool_query_governance_rules(self, args: dict[str, Any]) -> dict[str, Any]:
        query = str(args.get("query", "")).strip()
        if not query:
            raise ValueError("'query' must be a non-empty string")
        scope = str(args.get("scope", "all"))
        resolution = str(args.get("resolution", "L2")).strip().upper() or "L2"
        if resolution not in VALID_RESOLUTIONS:
            raise ValueError(
                f"Invalid resolution {resolution!r}: must be one of {VALID_RESOLUTIONS}"
            )
        env_arg = str(args.get("environment", "")).strip().lower()
        if env_arg and env_arg not in VALID_ENVIRONMENTS:
            raise ValueError(
                f"Invalid environment {env_arg!r}: must be one of {VALID_ENVIRONMENTS}"
            )
        env_scope = env_arg or "all"
        include_capsules = bool(args.get("include_capsules", True))
        explicit_key = (
            str(args["resonance_key"]).strip() if args.get("resonance_key") is not None else ""
        )
        key_required = bool(explicit_key or os.environ.get("DOTFILES_RESONANCE_KEY", "").strip())
        secret = self._resolve_resonance_secret(explicit_key or None)
        layer_arg = str(args.get("layer", "all")).strip() or "all"
        if layer_arg == "all":
            layer_dirs = [
                self.repo_dir,
                *(self.repo_dir / str(m["relative_path"]) for m in self._discover_mounted_layers()),
            ]
        else:
            layer_dirs = [self._resolve_layer_dir(layer_arg)]

        candidate_files: list[tuple[str, Path, Path]] = []
        for ldir in layer_dirs:
            lname = "root" if ldir == self.repo_dir else ldir.name
            if scope in ("all", "global"):
                candidate_files.append((lname, ldir, ldir / "antigravity/.gemini/config/AGENTS.md"))
            if scope in ("all", "templates"):
                for tf in sorted((ldir / "templates").glob("*/rules/*.md")):
                    candidate_files.append((lname, ldir, tf))
            if scope in ("all", "docs"):
                for df in sorted((ldir / "docs").rglob("*.md")):
                    candidate_files.append((lname, ldir, df))

        matches: list[dict[str, Any]] = []
        excerpt_truncated = False
        q_lower = query.lower()
        for lname, ldir, file_path in candidate_files:
            if not file_path.is_file() or not file_path.resolve().is_relative_to(ldir.resolve()):
                continue
            lines = file_path.read_text(encoding="utf-8").splitlines()
            for heading, start_line, end_line, body in _iter_markdown_sections(
                lines, file_path.name
            ):
                joined = "\n".join(body)
                if q_lower in joined.lower() or q_lower in heading.lower():
                    if resolution == "L2" and len(joined) > 1500:
                        excerpt_truncated = True
                    l2_excerpt = joined[:1500]
                    l2_full = joined[:8000]
                    l1_skeleton = _extract_axiom_skeleton(heading, body)
                    l3_links = _extract_l3_links(file_path, joined, ldir)
                    rel_in_layer = str(file_path.relative_to(ldir)).replace("\\", "/")
                    promoter_codon, capsule_token = self._build_section_capsule(
                        resolution=resolution,
                        layer_name=lname,
                        rel_in_layer=rel_in_layer,
                        heading=heading,
                        start_line=start_line,
                        end_line=end_line,
                        scope=scope,
                        l1_skeleton=l1_skeleton,
                        l2_excerpt=l2_excerpt,
                        l2_full=l2_full,
                        l3_links=l3_links,
                        env_scope=env_scope,
                        secret=secret,
                        key_required=key_required,
                    )
                    entry: dict[str, Any] = {
                        "file": str(file_path.relative_to(self.repo_dir)),
                        "layer": lname,
                        "section": heading,
                        "start_line": start_line,
                        "end_line": end_line,
                        "promoter_codon": promoter_codon,
                        "capsule_token": capsule_token if include_capsules else None,
                    }
                    if resolution == "L0":
                        entry["surface_preview"] = (
                            f"{promoter_codon['codon']} ({', '.join(promoter_codon['tags'])})"
                        )
                    elif resolution == "L1":
                        entry["axiom_skeleton"] = l1_skeleton
                        entry["excerpt"] = l1_skeleton
                    else:
                        entry["excerpt"] = l2_excerpt
                    matches.append(entry)

        total_matches = len(matches)
        returned_matches = matches[:15]
        returned_tokens = sum(
            int(m["promoter_codon"]["token_estimates"][resolution]) for m in returned_matches
        )
        capsule_overhead_tokens = (
            sum(len(str(m["capsule_token"])) // 4 for m in returned_matches)
            if include_capsules
            else 0
        )
        baseline_l2_tokens = sum(
            int(m["promoter_codon"]["token_estimates"]["L2"]) for m in returned_matches
        )
        tokens_saved = max(0, baseline_l2_tokens - returned_tokens)
        savings_pct = (
            round((tokens_saved / baseline_l2_tokens) * 100, 1) if baseline_l2_tokens > 0 else 0.0
        )

        query_warnings: list[dict[str, Any]] = []
        if total_matches > 15 or excerpt_truncated:
            query_warnings.append(
                self._emit_warning(
                    "WARN",
                    "RESPONSE_TRUNCATED",
                    f"Query matched {total_matches} section(s) (returning top "
                    f"{min(total_matches, 15)}). Narrow 'query', 'scope', or 'layer' "
                    "to inspect full sections without truncation.",
                    {
                        "query": query,
                        "total_matches": total_matches,
                        "excerpt_truncated": excerpt_truncated,
                    },
                )
            )

        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        {
                            "query": query,
                            "scope": scope,
                            "layer": layer_arg,
                            "resolution": resolution,
                            "include_capsules": include_capsules,
                            "token_compaction_metrics": {
                                "resolution": resolution,
                                "returned_estimated_tokens": returned_tokens,
                                "capsule_overhead_tokens": capsule_overhead_tokens,
                                "full_l2_baseline_tokens": baseline_l2_tokens,
                                "tokens_saved": tokens_saved,
                                "savings_pct": savings_pct,
                            },
                            "total_matches_found": total_matches,
                            "match_count": len(returned_matches),
                            "truncated": bool(query_warnings),
                            "warnings": query_warnings,
                            "matches": returned_matches,
                        },
                        indent=2,
                    ),
                }
            ],
            "isError": False,
        }
