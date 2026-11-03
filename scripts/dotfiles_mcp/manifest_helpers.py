"""System, manifest, and telemetry helper functions for dotfiles-ubuntu MCP.

Specification: docs/architecture/03_contextual_mcp_and_federation.md
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from dotfiles_mcp.constants import (
    MISSING_VERSION_SENTINEL,
    REPO_DIR,
    TEMPLATE_MANIFEST_CONTRACT_REV,
    TEMPLATE_STACK_GROUP_DIRS,
    VALID_TEMPLATE_KINDS,
)


def _read_version(repo_dir: Path | None = None) -> str:
    vf = (repo_dir or REPO_DIR) / "VERSION"
    return vf.read_text(encoding="utf-8").strip() if vf.is_file() else MISSING_VERSION_SENTINEL


def _read_os_pretty_name(os_release: Path | None = None) -> str:
    rf = os_release or Path("/etc/os-release")
    if rf.is_file():
        for line in rf.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.startswith("PRETTY_NAME="):
                return line.split("=", 1)[1].strip().strip('"')
    return f"{platform.system()} {platform.release()}"


def _is_running_in_container(marker_path: Path | None = None) -> bool:
    return (marker_path or Path("/.dockerenv")).is_file()


def _read_git_commit(repo_dir: Path | None = None) -> str:
    base_dir, env_fb = repo_dir or REPO_DIR, os.environ.get("DOTFILES_GIT_COMMIT", "").strip()
    git_bin = shutil.which("git")
    if not git_bin:
        return env_fb or "unknown"
    with contextlib.suppress(OSError):
        proc = subprocess.run(  # noqa: S603
            [git_bin, "rev-parse", "--short", "HEAD"], cwd=base_dir,
            capture_output=True, text=True, timeout=5, check=False,
        )  # fmt: skip
        if proc.returncode == 0:
            return proc.stdout.strip()
    return env_fb or "unknown"


def _parse_skill_frontmatter(skill_md: Path, repo_dir: Path | None = None) -> dict[str, Any]:
    base_dir, lines = repo_dir or REPO_DIR, skill_md.read_text(encoding="utf-8").splitlines()
    name, description = skill_md.parent.name, ""
    if lines and lines[0].strip() == "---":
        for idx in range(1, min(len(lines), 30)):
            if lines[idx].strip() == "---":
                fm = "\n".join(lines[1:idx])
                if name_m := re.search(r"^name:\s*(.+)$", fm, re.MULTILINE):
                    name = name_m.group(1).strip().strip("'\"")
                if desc_m := re.search(r"^description:\s*(.+)$", fm, re.MULTILINE):
                    description = desc_m.group(1).strip().strip("'\"")
                break
    return {"name": name, "description": description,
        "path": str(skill_md.relative_to(base_dir)), "line_count": len(lines)}  # fmt: skip


def _read_non_empty_lines(path: Path) -> list[str]:
    if not path.is_file():
        return []
    return [
        ln.strip()
        for ln in path.read_text(encoding="utf-8", errors="ignore").splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]


def _merge_unique_strings(*groups: list[str]) -> list[str]:
    seen, merged = set[str](), list[str]()
    for group in groups:
        for item in group:
            if (clean := str(item).strip()) and clean not in seen:
                seen.add(clean)
                merged.append(clean)
    return merged


def _count_result_warnings(result: dict[str, Any]) -> int:
    content_list = result.get("content")
    if not isinstance(content_list, list) or not content_list:
        return 0
    first_text = content_list[0].get("text", "")
    if not isinstance(first_text, str) or not first_text.startswith("{"):
        return 0
    with contextlib.suppress(json.JSONDecodeError):
        parsed: dict[str, Any] = json.loads(first_text)
        if isinstance(top_w := parsed.get("warnings"), list):
            return len(top_w)
        ch3 = parsed.get("channel_3_active_invariants_and_hooks")
        if isinstance(ch3, dict) and isinstance(ch3.get("warnings"), list):
            return len(ch3["warnings"])
    return 0


def _extract_compaction_event_fields(target: str, result: dict[str, Any]) -> dict[str, Any]:
    content_list = result.get("content")
    if not isinstance(content_list, list) or not content_list:
        return {}
    first_text = content_list[0].get("text", "")
    if not isinstance(first_text, str) or not first_text.startswith("{"):
        return {}
    with contextlib.suppress(json.JSONDecodeError):
        parsed: dict[str, Any] = json.loads(first_text)
        if target in ("query_governance_rules", "resolve_surface_governance"):
            metrics = parsed.get("token_compaction_metrics", {})
            res = str(parsed.get("resolution") or metrics.get("resolution", "adaptive"))
            return {"resolution": res, "tokens_saved": int(metrics.get("tokens_saved", 0)),
                "savings_pct": float(metrics.get("savings_pct", 0.0))}  # fmt: skip
        if target == "unfold_context_capsule":
            return {"unfolded_level": parsed.get("unfolded_level"),
                "agent_tier": str(parsed.get("agent_tier", "inherit")),
                "decrypted_hops": int(parsed.get("decrypted_hops", 0))}  # fmt: skip
    return {}


def _iter_layer_template_dirs(layer_dir: Path) -> list[tuple[str, Path]]:
    """Return sorted (template_name, template_dir) pairs across root and stack-group folders."""
    templates_root = layer_dir / "templates"
    if not templates_root.is_dir():
        return []
    found: dict[str, Path] = {}
    for d in sorted(templates_root.iterdir()):
        if not d.is_dir() or d.name.startswith("."):
            continue
        if d.name in TEMPLATE_STACK_GROUP_DIRS:
            for sub in sorted(d.iterdir()):
                if sub.is_dir() and not sub.name.startswith("."):
                    found.setdefault(sub.name, sub)
        else:
            found[d.name] = d
    return sorted(found.items(), key=lambda item: item[0])


def _resolve_template_dir(layer_dir: Path, tpl_ref: str) -> Path | None:
    """Resolve a template pack directory by short name or stack-group relative path."""
    clean = tpl_ref.strip().strip("/")
    if not clean or clean in TEMPLATE_STACK_GROUP_DIRS:
        return None
    t_root, leaf = layer_dir / "templates", clean.split("/")[-1]
    cands = (t_root / clean, t_root / leaf, *(t_root / g / leaf for g in TEMPLATE_STACK_GROUP_DIRS))
    return next((c for c in cands if c.is_dir() and c.name not in TEMPLATE_STACK_GROUP_DIRS), None)


def _resolve_template_dest_dir(
    layer_dir: Path, tpl_name: str, *, kind: str | None = None, src_tpl: Path | None = None
) -> Path:
    """Resolve the destination directory for creating, syncing, or promoting a template pack."""
    if src_tpl is not None and src_tpl.parent.name in TEMPLATE_STACK_GROUP_DIRS:
        return layer_dir / "templates" / src_tpl.parent.name / tpl_name
    if (existing := _resolve_template_dir(layer_dir, tpl_name)) is not None:
        return existing
    if kind in TEMPLATE_STACK_GROUP_DIRS:
        return layer_dir / "templates" / str(kind) / tpl_name
    return layer_dir / "templates" / tpl_name


def _sha256_file(path: Path) -> str:
    """Compute SHA-256 hex digest using C-backed hashlib.file_digest without heap-loading."""
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def _has_stale_schema(json_file: Path, expected_rev: str) -> bool:
    """Return True if json_file exists and its schema_version or template kind is stale."""
    if not json_file.is_file():
        return False
    d = json.loads(json_file.read_text(encoding="utf-8"))
    bad_k = (
        expected_rev == TEMPLATE_MANIFEST_CONTRACT_REV
        and isinstance(d, dict)
        and d.get("kind") not in VALID_TEMPLATE_KINDS
    )
    return not isinstance(d, dict) or d.get("schema_version") != expected_rev or bad_k


def _stamp_schema_rev(json_file: Path, expected_rev: str) -> None:
    """Update schema_version and normalize non-canonical template kind in json_file when stale."""
    if _has_stale_schema(json_file, expected_rev):
        raw = json.loads(json_file.read_text("utf-8"))
        base = raw if isinstance(raw, dict) else {}
        d: dict[str, Any] = {**base, "schema_version": expected_rev}
        if (
            expected_rev == TEMPLATE_MANIFEST_CONTRACT_REV
            and d.get("kind") not in VALID_TEMPLATE_KINDS
        ):
            k_str = f"{d.get('kind', '')} {d.get('description', '')} {d.get('target_role', '')}"
            is_biz = any(t in k_str for t in ("policy", "department", "corporate"))
            d["kind"] = "business-stack" if is_biz else "tech-stack"
        json_file.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n", "utf-8")


def _ensure_rule_file_frontmatter(rule_path: Path, *, sync_in_place: bool = True) -> str:
    """Ensure a markdown rule file starts with Antigravity 2.0 'trigger: always_on' frontmatter."""
    text = rule_path.read_text(encoding="utf-8")
    if text.startswith("---\n"):
        return text
    desc = f"Governance rules for {rule_path.stem}"
    for line in text.splitlines():
        if line.startswith("# "):
            desc = line[2:].strip().replace('"', "'")
            break
    updated = f'---\ntrigger: always_on\ndescription: "{desc}"\n---\n{text}'
    if sync_in_place:
        rule_path.write_text(updated, encoding="utf-8")
    return updated


def _resolve_oss_contrib_repo_dir(up: Path) -> Path:
    """Resolve the dedicated contributing repository for OSS upward promotions."""
    env_dir = os.environ.get("DOTFILES_DEV_REPO_DIR", "").strip()
    candidates = [Path(env_dir).expanduser()] if env_dir else []
    candidates.append(up.parent / "Projects" / f"dev-{up.name}")
    for cand in candidates:
        if (cand / "system" / "mcp-layer.json").is_file():
            return cand.resolve()
    return up


def _load_manifest_dict(target_dir: Path) -> dict[str, Any]:
    """Load <target_dir>/system/mcp-layer.json as a dictionary, or {} if missing/invalid."""
    mpath = target_dir / "system" / "mcp-layer.json"
    loaded = json.loads(mpath.read_text(encoding="utf-8")) if mpath.is_file() else {}
    return loaded if isinstance(loaded, dict) else {}


def _is_oss_root_manifest(manifest: dict[str, Any]) -> bool:
    """Return True when manifest represents the Open-Source community root layer."""
    role = str(manifest.get("layer_role", ""))
    return str(manifest.get("layer_id", "")) == "root" or role in ("root", "workstation")


def discover_layer_template_names(layer_dir: Path) -> list[str]:
    """Return sorted template directory names present under layer_dir/templates."""
    return [name for name, _path in _iter_layer_template_dirs(layer_dir)]


def _inspect_single_template_dir(
    tpl_dir: Path, layer_dir: Path, source_layer: str
) -> dict[str, Any]:
    """Build catalog metadata for a single template pack directory."""
    meta_file = tpl_dir / "template.json"
    loaded = json.loads(meta_file.read_text(encoding="utf-8")) if meta_file.is_file() else {}
    meta: dict[str, Any] = loaded if isinstance(loaded, dict) else {}
    rules = [str(p.relative_to(layer_dir)) for p in sorted((tpl_dir / "rules").glob("*.md"))]
    skills = [
        _parse_skill_frontmatter(p, layer_dir)
        for p in sorted((tpl_dir / "skills").glob("*/SKILL.md"))
    ]
    gov = [str(p.relative_to(layer_dir)) for p in sorted((tpl_dir / "governance").glob("*.md"))]
    assets_dir = tpl_dir / "assets"
    assets = (
        [str(p.relative_to(layer_dir)) for p in sorted(assets_dir.rglob("*")) if p.is_file()]
        if assets_dir.is_dir()
        else []
    )
    parent_grp = tpl_dir.parent.name if tpl_dir.parent.name in TEMPLATE_STACK_GROUP_DIRS else "core"
    raw_k = str(meta.get("kind", "tech-stack"))
    return {
        "template_name": tpl_dir.name,
        "source_layer": source_layer,
        "kind": raw_k if raw_k in VALID_TEMPLATE_KINDS else "tech-stack",
        "stack_group": str(meta.get("stack_group", parent_grp)),
        "target_role": str(meta.get("target_role", "squad")),
        "description": str(meta.get("description", f"Template pack {tpl_dir.name}")),
        "rules": rules,
        "skills": skills,
        "governance_files": gov,
        "assets": assets,
        "recommended_surface_bindings": list(meta.get("recommended_surface_bindings", [])),
    }


def discover_templates_catalog(
    repo_dir: Path,
    mounted_layers: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Discover all template packs across the root layer and mounted subtrees."""
    catalog: list[dict[str, Any]] = []
    search_targets: list[tuple[str, Path]] = [("root", repo_dir)]
    for entry in mounted_layers or []:
        rel = str(entry.get("relative_path", ""))
        if rel:
            search_targets.append((str(entry.get("name", rel)), repo_dir / rel))

    for source_layer, ldir in search_targets:
        for _tpl_name, tpl_dir in _iter_layer_template_dirs(ldir):
            catalog.append(_inspect_single_template_dir(tpl_dir, ldir, source_layer))
    return catalog
