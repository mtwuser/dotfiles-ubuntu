"""Stack-agnostic surface selector inference, matching, and Lex Specialis scoring."""

from __future__ import annotations

import fnmatch
from typing import Any

from dotfiles_mcp.constants import PLANE_PATH_RULES, STRUCTURAL_PATH_SEGMENTS


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
    traits_ok = not req_traits or bool(req_traits & traits)
    return glob_ok and plane_ok and scope_ok and traits_ok


def _compute_binding_specificity(binding: dict[str, Any]) -> int:
    globs = [str(g).strip() for g in binding.get("target_globs", ["**"]) if str(g).strip()]
    planes = [
        str(p).strip().lower() for p in binding.get("architectural_planes", ["*"]) if str(p).strip()
    ]
    scopes = [str(s).strip().lower() for s in binding.get("scopes", ["*"]) if str(s).strip()]
    traits = [str(t).strip().lower() for t in binding.get("traits", []) if str(t).strip()]
    glob_pts = 1 if (globs and "**" not in globs) else 0
    plane_pts = 2 if (planes and "*" not in planes) else 0
    scope_pts = 3 if (scopes and "*" not in scopes) else 0
    trait_pts = 4 * len(traits)
    return glob_pts + plane_pts + scope_pts + trait_pts
