"""System, manifest, and telemetry helper functions for dotfiles-ubuntu MCP."""

from __future__ import annotations

import contextlib
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
