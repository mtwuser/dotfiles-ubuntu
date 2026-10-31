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

from dotfiles_mcp.constants import REPO_DIR


def _read_version(repo_dir: Path | None = None) -> str:
    base_dir = repo_dir or REPO_DIR
    version_file = base_dir / "VERSION"
    if version_file.is_file():
        return version_file.read_text(encoding="utf-8").strip()
    return "0.0.0"


def _read_os_pretty_name(os_release: Path | None = None) -> str:
    release_file = os_release or Path("/etc/os-release")
    if release_file.is_file():
        for line in release_file.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.startswith("PRETTY_NAME="):
                return line.split("=", 1)[1].strip().strip('"')
    return f"{platform.system()} {platform.release()}"


def _is_running_in_container(marker_path: Path | None = None) -> bool:
    marker = marker_path or Path("/.dockerenv")
    return marker.is_file()


def _read_git_commit(repo_dir: Path | None = None) -> str:
    base_dir = repo_dir or REPO_DIR
    env_fallback = os.environ.get("DOTFILES_GIT_COMMIT", "").strip()
    git_bin = shutil.which("git")
    if not git_bin:
        return env_fallback or "unknown"
    try:
        proc = subprocess.run(  # noqa: S603
            [git_bin, "rev-parse", "--short", "HEAD"],
            cwd=base_dir,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if proc.returncode == 0:
            return proc.stdout.strip()
    except OSError:
        pass
    return env_fallback or "unknown"


def _parse_skill_frontmatter(skill_md: Path, repo_dir: Path | None = None) -> dict[str, Any]:
    base_dir = repo_dir or REPO_DIR
    lines = skill_md.read_text(encoding="utf-8").splitlines()
    name = skill_md.parent.name
    description = ""
    if lines and lines[0].strip() == "---":
        for idx in range(1, min(len(lines), 30)):
            if lines[idx].strip() == "---":
                fm = "\n".join(lines[1:idx])
                name_m = re.search(r"^name:\s*(.+)$", fm, re.MULTILINE)
                desc_m = re.search(r"^description:\s*(.+)$", fm, re.MULTILINE)
                if name_m:
                    name = name_m.group(1).strip().strip("'\"")
                if desc_m:
                    description = desc_m.group(1).strip().strip("'\"")
                break
    return {
        "name": name,
        "description": description,
        "path": str(skill_md.relative_to(base_dir)),
        "line_count": len(lines),
    }


def _read_non_empty_lines(path: Path) -> list[str]:
    if not path.is_file():
        return []
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def _merge_unique_strings(*groups: list[str]) -> list[str]:
    seen: set[str] = set()
    merged: list[str] = []
    for group in groups:
        for item in group:
            clean = str(item).strip()
            if clean and clean not in seen:
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
        top_w = parsed.get("warnings")
        if isinstance(top_w, list):
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
            return {
                "resolution": str(
                    parsed.get("resolution") or metrics.get("resolution", "adaptive")
                ),
                "tokens_saved": int(metrics.get("tokens_saved", 0)),
                "savings_pct": float(metrics.get("savings_pct", 0.0)),
            }
        if target == "unfold_context_capsule":
            return {
                "unfolded_level": parsed.get("unfolded_level"),
                "agent_tier": str(parsed.get("agent_tier", "inherit")),
                "decrypted_hops": int(parsed.get("decrypted_hops", 0)),
            }
    return {}


def _is_dest_template_newer(src_tpl: Path, dest_tpl: Path) -> bool:
    """Return True if dest_tpl has a modified rule file with a newer timestamp than src_tpl."""
    if not (dest_tpl / "rules").is_dir() or not (src_tpl / "rules").is_dir():
        return False
    for dest_rf in sorted((dest_tpl / "rules").glob("*.md")):
        src_rf = src_tpl / "rules" / dest_rf.name
        if src_rf.is_file():
            dest_sha = hashlib.sha256(dest_rf.read_bytes()).hexdigest()
            src_sha = hashlib.sha256(src_rf.read_bytes()).hexdigest()
            if dest_sha != src_sha and dest_rf.stat().st_mtime_ns > src_rf.stat().st_mtime_ns:
                return True
    return False


def _resolve_mounted_child_dir(workspace_dir: Path, child_name: str) -> Path | None:
    """Resolve the live sibling checkout for a mounted child layer."""
    ws = workspace_dir.resolve()
    candidates = (ws.parent / f"{ws.name}-org" / child_name, ws.parent / child_name)
    for cand in candidates:
        if cand.resolve() != ws and (cand / "system" / "mcp-layer.json").is_file():
            return cand.resolve()
    return None


_CHILD_TRACKED_REL_PATHS: tuple[str, ...] = (
    "antigravity/.gemini/config/AGENTS.md",
    "system/mcp-layer.json",
    "README.md",
    "CHANGELOG.md",
    "WORKTASK.md",
    "BACKLOG.md",
    "Makefile",
    "VERSION",
)


def _inspect_mounted_children_drifts(
    workspace_dir: Path, mounted_layers: list[Any]
) -> list[dict[str, Any]]:
    """Detect 1-hop downstream mounted layers with newer/changed sibling files."""
    ws = workspace_dir.resolve()
    drifts: list[dict[str, Any]] = []
    for entry in mounted_layers or []:
        if not isinstance(entry, dict):
            continue
        child_name = str(entry.get("name") or entry.get("layer_id") or "").strip()
        mounted_dir = ws / "layers" / child_name
        child_ws = _resolve_mounted_child_dir(ws, child_name) if child_name else None
        if not child_name or not mounted_dir.is_dir() or child_ws is None:
            continue
        changed_files: list[str] = []
        for rel in _CHILD_TRACKED_REL_PATHS:
            src_f, dst_f = child_ws / rel, mounted_dir / rel
            if src_f.is_file() and (
                not dst_f.is_file()
                or hashlib.sha256(src_f.read_bytes()).hexdigest()
                != hashlib.sha256(dst_f.read_bytes()).hexdigest()
            ):
                changed_files.append(rel)
        for sub_name in ("docs", "templates"):
            sub_dir = child_ws / sub_name
            for src_f in sorted(sub_dir.rglob("*")) if sub_dir.is_dir() else []:
                if not src_f.is_file():
                    continue
                rel_d = str(src_f.relative_to(child_ws)).replace("\\", "/")
                dst_f = mounted_dir / rel_d
                if not dst_f.is_file() or (
                    hashlib.sha256(src_f.read_bytes()).hexdigest()
                    != hashlib.sha256(dst_f.read_bytes()).hexdigest()
                ):
                    changed_files.append(rel_d)
        if changed_files:
            drifts.append(
                {
                    "layer_id": child_name,
                    "child_workspace_dir": str(child_ws),
                    "mounted_path": f"layers/{child_name}",
                    "drift_files": changed_files,
                }
            )
    return drifts


def _sync_mounted_children_into_parent(
    target_dir: Path, mounted_layers: list[Any], *, dry_run: bool = False
) -> list[str]:
    """Synchronize mounted layers/<child>/ and child template packs from live sibling checkouts."""
    ws = target_dir.resolve()
    drifts = _inspect_mounted_children_drifts(ws, mounted_layers)
    synced: list[str] = []
    for d_info in drifts:
        child_name = str(d_info["layer_id"])
        child_ws = Path(d_info["child_workspace_dir"])
        mounted_dir = ws / "layers" / child_name
        synced.append(child_name)
        if dry_run:
            continue
        for rel in _CHILD_TRACKED_REL_PATHS:
            src_f, dst_f = child_ws / rel, mounted_dir / rel
            if src_f.is_file():
                dst_f.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_f, dst_f)
        for sub_name in ("docs", ".agents", "templates"):
            src_sub, dst_sub = child_ws / sub_name, mounted_dir / sub_name
            if src_sub.is_dir():
                shutil.rmtree(dst_sub, ignore_errors=True)
                shutil.copytree(src_sub, dst_sub)
    return synced
