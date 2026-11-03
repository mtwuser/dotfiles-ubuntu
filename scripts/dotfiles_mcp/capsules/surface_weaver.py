"""Stack-agnostic surface selector inference, matching, and Lex Specialis scoring.

Specification: docs/architecture/04_compaction_surface_and_promotion_engines.md
"""

from __future__ import annotations

import fnmatch
import json
from pathlib import Path
from typing import Any

from dotfiles_mcp.core.constants import (
    PLANE_PATH_RULES,
    SPECIFICITY_WEIGHT_GLOB,
    SPECIFICITY_WEIGHT_PLANE,
    SPECIFICITY_WEIGHT_SCOPE,
    SPECIFICITY_WEIGHT_TRAIT,
    STRUCTURAL_PATH_SEGMENTS,
)
from dotfiles_mcp.core.manifest_helpers import _resolve_template_dir


def collect_layer_effective_bindings(
    layer_dir: Path, manifest: dict[str, Any]
) -> list[dict[str, Any]]:
    """Merge manifest surface_bindings with active template.json recommended_surface_bindings."""
    effective, seen_ids = [], set[str]()
    candidates = list(manifest.get("surface_bindings") or [])
    for tpl_name in manifest.get("default_stack_templates", []):
        tpl_dir = _resolve_template_dir(Path(layer_dir), str(tpl_name))
        meta_file = tpl_dir / "template.json" if tpl_dir is not None else None
        if meta_file is not None and meta_file.is_file():
            loaded = json.loads(meta_file.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                candidates.extend(loaded.get("recommended_surface_bindings", []))
    for raw_b in candidates:
        if isinstance(raw_b, dict):
            bid = str(raw_b.get("binding_id", ""))
            if not bid or bid not in seen_ids:
                if bid:
                    seen_ids.add(bid)
                effective.append(raw_b)
    return effective


def _infer_plane_from_path(rel_path: str) -> str:
    norm = rel_path.strip().replace("\\", "/").lstrip("/").lower()
    return next(
        (plane for plane, tokens in PLANE_PATH_RULES if any(tok in norm for tok in tokens)),
        "",
    )


def _infer_scope_from_path(rel_path: str) -> str:
    parts = [
        p
        for p in rel_path.strip().replace("\\", "/").strip("/").split("/")
        if p and "." not in p and p.lower() not in STRUCTURAL_PATH_SEGMENTS
    ]
    return parts[0].lower() if parts else ""


def _glob_matches(rel_path: str, pattern: str) -> bool:
    norm_path = rel_path.strip().replace("\\", "/").lstrip("/")
    norm_pat = pattern.strip().replace("\\", "/").lstrip("/")
    collapsed = norm_pat.replace("/**/", "/").removeprefix("**/")
    return bool(
        norm_pat == "**"
        or fnmatch.fnmatchcase(norm_path, norm_pat)
        or fnmatch.fnmatchcase(norm_path, collapsed)
        or (norm_pat.endswith("/**") and norm_path.startswith(norm_pat[:-2]))
    )


def _binding_matches_surface(
    binding: dict[str, Any],
    target_path: str,
    plane: str,
    scope: str,
    traits: set[str],
) -> bool:
    globs = [str(g) for g in binding.get("target_globs", ["**"])]
    planes = [str(p).lower() for p in binding.get("architectural_planes", ["*"])]
    scopes = [str(s).lower() for s in binding.get("scopes", ["*"])]
    req_traits = {str(t).lower() for t in binding.get("traits", [])}
    glob_ok = not target_path or any(_glob_matches(target_path, g) for g in globs)
    plane_ok = not plane or "*" in planes or plane in planes
    scope_ok = not scope or "*" in scopes or scope in scopes
    traits_ok = not req_traits or "*" in req_traits or bool(req_traits & traits)
    return glob_ok and plane_ok and scope_ok and traits_ok


def _compute_binding_specificity(binding: dict[str, Any]) -> int:
    globs = [str(g).strip() for g in binding.get("target_globs", ["**"]) if str(g).strip()]
    planes = [
        str(p).strip().lower() for p in binding.get("architectural_planes", ["*"]) if str(p).strip()
    ]
    scopes = [str(s).strip().lower() for s in binding.get("scopes", ["*"]) if str(s).strip()]
    traits = [
        str(t).strip().lower()
        for t in binding.get("traits", [])
        if str(t).strip() and str(t).strip() != "*"
    ]
    glob_pts = SPECIFICITY_WEIGHT_GLOB if (globs and "**" not in globs and "*" not in globs) else 0
    plane_pts = SPECIFICITY_WEIGHT_PLANE if (planes and "*" not in planes) else 0
    scope_pts = SPECIFICITY_WEIGHT_SCOPE if (scopes and "*" not in scopes) else 0
    trait_pts = SPECIFICITY_WEIGHT_TRAIT * len(traits)
    return glob_pts + plane_pts + scope_pts + trait_pts


def match_authoritative_surface_bindings(
    layer_nodes: list[tuple[str, Path, dict[str, Any]]], target_paths: list[str]
) -> list[dict[str, Any]]:
    """Resolve authoritative layer bindings governing each path in target_paths."""
    matches: list[dict[str, Any]] = []
    for raw_path in target_paths:
        norm_path = raw_path.strip().replace("\\", "/").lstrip("/")
        if not norm_path:
            continue
        plane, scope = _infer_plane_from_path(norm_path), _infer_scope_from_path(norm_path)
        path_hits: list[tuple[int, int, str, dict[str, Any]]] = []
        for lid, ldir, manifest in layer_nodes:
            prec = int(manifest.get("precedence", 50))
            for b in collect_layer_effective_bindings(ldir, manifest):
                mode = str(b.get("mode", "authoritative")).strip().lower()
                globs = [str(g).strip() for g in b.get("target_globs", []) if str(g).strip()]
                has_specific_glob = bool(globs and "**" not in globs and "*" not in globs)
                if (
                    mode == "authoritative"
                    and has_specific_glob
                    and _binding_matches_surface(b, norm_path, plane, scope, set())
                ):
                    spec = _compute_binding_specificity(b)
                    bid = str(b.get("binding_id", f"{lid}-binding"))
                    item = {
                        "target_path": norm_path,
                        "owning_layer_id": lid,
                        "owning_layer_dir": str(ldir),
                        "precedence": prec,
                        "binding_id": bid,
                        "specificity_score": spec,
                    }
                    path_hits.append((prec, -spec, lid, item))
        if path_hits:
            path_hits.sort(key=lambda x: (x[0], x[1], x[2]))
            matches.append(path_hits[0][3])
    return matches
