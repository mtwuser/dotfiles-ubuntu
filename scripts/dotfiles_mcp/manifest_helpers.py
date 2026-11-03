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
    LAYER_MANIFEST_CONTRACT_REV,
    MISSING_VERSION_SENTINEL,
    REPO_DIR,
    TEMPLATE_MANIFEST_CONTRACT_REV,
    TEMPLATE_STACK_GROUP_DIRS,
)


def _read_version(repo_dir: Path | None = None) -> str:
    base_dir = repo_dir or REPO_DIR
    version_file = base_dir / "VERSION"
    if version_file.is_file():
        return version_file.read_text(encoding="utf-8").strip()
    return MISSING_VERSION_SENTINEL


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
            [git_bin, "rev-parse", "--short", "HEAD"], cwd=base_dir,
            capture_output=True, text=True, timeout=5, check=False,
        )  # fmt: skip
        if proc.returncode == 0:
            return proc.stdout.strip()
    except OSError:
        pass
    return env_fallback or "unknown"


def _parse_skill_frontmatter(skill_md: Path, repo_dir: Path | None = None) -> dict[str, Any]:
    base_dir = repo_dir or REPO_DIR
    lines = skill_md.read_text(encoding="utf-8").splitlines()
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
    templates_root = layer_dir / "templates"
    leaf = clean.split("/")[-1]
    for cand in (
        templates_root / clean,
        templates_root / leaf,
        *(templates_root / grp / leaf for grp in TEMPLATE_STACK_GROUP_DIRS),
    ):
        if cand.is_dir() and cand.name not in TEMPLATE_STACK_GROUP_DIRS:
            return cand
    return None


def _resolve_template_dest_dir(
    layer_dir: Path,
    tpl_name: str,
    *,
    kind: str | None = None,
    src_tpl: Path | None = None,
) -> Path:
    """Resolve the destination directory for creating, syncing, or promoting a template pack."""
    if src_tpl is not None and src_tpl.parent.name in TEMPLATE_STACK_GROUP_DIRS:
        return layer_dir / "templates" / src_tpl.parent.name / tpl_name
    existing = _resolve_template_dir(layer_dir, tpl_name)
    if existing is not None:
        return existing
    if kind in TEMPLATE_STACK_GROUP_DIRS:
        return layer_dir / "templates" / str(kind) / tpl_name
    return layer_dir / "templates" / tpl_name


def _is_dest_template_newer(src_tpl: Path, dest_tpl: Path) -> bool:
    """Return True if dest_tpl has a modified rule file with newer mtime or reconciled sha."""
    if not (dest_tpl / "rules").is_dir() or not (src_tpl / "rules").is_dir():
        return False
    tj = dest_tpl / "template.json"
    t_dict: dict[str, Any] = json.loads(tj.read_text("utf-8")) if tj.is_file() else {}
    raw_rec = t_dict.get("reconciled_upstream_sha256")
    rec_map: dict[str, Any] = raw_rec if isinstance(raw_rec, dict) else {}
    for dest_rf in sorted((dest_tpl / "rules").glob("*.md")):
        src_rf = src_tpl / "rules" / dest_rf.name
        if src_rf.is_file():
            dest_sha, src_sha = _sha256_file(dest_rf), _sha256_file(src_rf)
            rec_sha = rec_map.get(dest_rf.name)
            if dest_sha != src_sha and (
                dest_sha != rec_sha
                if isinstance(rec_sha, str)
                else dest_rf.stat().st_mtime_ns > src_rf.stat().st_mtime_ns
            ):
                return True
    return False


def _resolve_default_parent_dir(workspace_dir: Path, parent_dir: Path | None) -> Path | None:
    """Resolve an explicit or Makefile/mounted-parent default parent_dir for a layer workspace."""
    if parent_dir is not None:
        return parent_dir
    ws, mk = workspace_dir.resolve(), workspace_dir.resolve() / "Makefile"
    if mk.is_file() and (
        m := re.search(r"^PARENT_DIR\s*\?=\s*(.+)$", mk.read_text(encoding="utf-8"), re.MULTILINE)
    ):
        cand = Path(m.group(1).strip())
        if cand.is_dir() and cand.resolve() != ws and (cand / "system/mcp-layer.json").is_file():
            return cand.resolve()
    if ws.parent.name == "layers" and (ws.parent.parent / "system/mcp-layer.json").is_file():
        return ws.parent.parent.resolve()
    return None


def _resolve_mounted_child_dir(workspace_dir: Path, child_name: str) -> Path | None:
    """Resolve a 1-hop child layer directory, prioritizing mounted layers/<child> inside ws."""
    ws = workspace_dir.resolve()
    roots = [ws / "layers", ws.parent / f"{ws.name}-org", ws.parent]
    for r in roots:
        cand = r / child_name
        if cand.resolve() != ws and (cand / "system" / "mcp-layer.json").is_file():
            return cand.resolve()
    for r in roots:
        if not r.is_dir():
            continue
        for sub in sorted(r.iterdir()):
            mf = sub / "system" / "mcp-layer.json"
            if sub.is_dir() and sub.resolve() != ws and mf.is_file():
                with contextlib.suppress(json.JSONDecodeError, OSError):
                    data = json.loads(mf.read_text(encoding="utf-8"))
                    if isinstance(data, dict) and data.get("layer_id") == child_name:
                        return sub.resolve()
    return None


def _sha256_file(path: Path) -> str:
    """Compute SHA-256 hex digest using C-backed hashlib.file_digest without heap-loading."""
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def _has_stale_schema(json_file: Path, expected_rev: str) -> bool:
    """Return True if json_file exists and its schema_version differs from expected_rev."""
    return (
        json_file.is_file()
        and json.loads(json_file.read_text(encoding="utf-8")).get("schema_version") != expected_rev
    )


def _stamp_schema_rev(json_file: Path, expected_rev: str) -> None:
    """Update schema_version in json_file in place when stale."""
    if _has_stale_schema(json_file, expected_rev):
        data = {**json.loads(json_file.read_text("utf-8")), "schema_version": expected_rev}
        json_file.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", "utf-8")


def _inspect_mounted_children_drifts(
    workspace_dir: Path, mounted_layers: list[Any]
) -> list[dict[str, Any]]:
    """Detect contract or shared-template drift inside mounted layers/<child>/ subtrees."""
    ws, drifts = workspace_dir.resolve(), []
    for entry in (e for e in (mounted_layers or []) if isinstance(e, dict)):
        cname = str(entry.get("name") or entry.get("layer_id") or "").strip()
        mdir = ws / "layers" / cname
        if not cname or not mdir.is_dir():
            continue
        c_files = (
            ["system/mcp-layer.json"]
            if _has_stale_schema(mdir / "system/mcp-layer.json", LAYER_MANIFEST_CONTRACT_REV)
            else []
        )
        for tname, ctdir in _iter_layer_template_dirs(mdir):
            if _has_stale_schema(tj := ctdir / "template.json", TEMPLATE_MANIFEST_CONTRACT_REV):
                c_files.append(str(tj.relative_to(mdir)).replace("\\", "/"))
            ptdir = _resolve_template_dir(ws, tname)
            for src_rf in sorted((ptdir / "rules").glob("*.md")) if ptdir else ():
                dst_rf = ctdir / "rules" / src_rf.name
                if not dst_rf.is_file() or _sha256_file(src_rf) != _sha256_file(dst_rf):
                    c_files.append(str(dst_rf.relative_to(mdir)).replace("\\", "/"))
        if c_files:
            br = str(entry.get("branch") or "master").strip()
            push_cmd = f"./scripts/layer-subtree.sh push {cname} {br}"
            pull_cmd = f"./scripts/layer-subtree.sh pull {cname}"
            drifts.append({"layer_id": cname, "mounted_path": f"layers/{cname}",
                "drift_files": c_files, "subtree_push_command": push_cmd,
                "subtree_pull_command": pull_cmd})  # fmt: skip
    return drifts


def _sync_mounted_children_into_parent(
    target_dir: Path, mounted_layers: list[Any], *, dry_run: bool = False
) -> list[str]:
    """Synchronize parent contracts and shared templates into mounted layers/<child>/ subtrees."""
    ws = target_dir.resolve()
    synced = [str(d["layer_id"]) for d in _inspect_mounted_children_drifts(ws, mounted_layers)]
    for cname in () if dry_run else synced:
        mdir = ws / "layers" / cname
        _stamp_schema_rev(mdir / "system/mcp-layer.json", LAYER_MANIFEST_CONTRACT_REV)
        for tname, ctdir in _iter_layer_template_dirs(mdir):
            _stamp_schema_rev(ctdir / "template.json", TEMPLATE_MANIFEST_CONTRACT_REV)
            ptdir = _resolve_template_dir(ws, tname)
            for src_rf in sorted((ptdir / "rules").glob("*.md")) if ptdir else ():
                dst_rf = ctdir / "rules" / src_rf.name
                dst_rf.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_rf, dst_rf)
                if (ag_rf := mdir / ".agents/rules" / src_rf.name).is_file():
                    shutil.copy2(src_rf, ag_rf)
    return synced


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


_DEFAULT_SQUAD_SPEC: tuple[str, str, str, str] = (
    "Level 3 — Squad Execution & Tech Stack Governance",
    "[Fill: Squad mission, bounded contexts, tech stack conventions, and testing gates]",
    "[Fill: Target application repositories for apply-project, e.g. /path/to/app-service]",
    "apply-project commands for our target application repositories",
)
_ROLE_ONBOARDING_SPECS: dict[str, tuple[str, str, str, str]] = {
    "corporate": (
        "Level 1 — Root 0 (Business & Corporate Governance)",
        "[Fill: Organization mission, core business domain, and compliance/IP/SLA non-negotiables]",
        "[Fill: Planned child Departments (--role department / --role domain-policy)]",
        "bootstrap-workspace commands to initialize our planned child Departments",
    ),
    "department": (
        "Level 2 — Department & Cross-Cutting Domain Governance",
        "[Fill: Department mission, domain invariants, and target file surface globs]",
        "[Fill: Planned child Squads (--role squad, e.g. squad-core-api)]",
        "bootstrap-workspace commands to initialize our child Squads",
    ),
    "domain-policy": (
        "Level 2 — Department & Cross-Cutting Domain Policy Governance",
        "[Fill: Cross-cutting policy domain (Legal/IP/Security), invariants, and surface globs]",
        "[Fill: Consumer Departments or Squads mounting this policy layer]",
        "register-subtree and bootstrap-workspace commands for consumer layers",
    ),
    "squad": _DEFAULT_SQUAD_SPEC,
}


_HUMAN_STACK_BLUEPRINT_HINT = (
    "[Optional: leave blank for default, or compose Human-Specs: "
    "domain-<area>:L1..L4 | bridge-* | soft-* | hat-*]"
)


def _render_layer_onboarding_readme(
    layer_id: str,
    layer_role: str,
    effective_prec: int,
    own_tpl_id: str,
    active_templates: list[str],
    parent_id: str | None = None,
) -> str:
    """Render a role-specific Layer Setup Blueprint and Initial Chat Kickoff Prompt."""
    tier_title, scope_hint, children_hint, next_cmd_goal = _ROLE_ONBOARDING_SPECS.get(
        layer_role, _DEFAULT_SQUAD_SPEC
    )
    tpl_csv = ", ".join(f"`{t}`" for t in active_templates) or "`none`"
    parent_label = f"`{parent_id}`" if parent_id else "`open-source-root`"
    return (
        f"# {layer_id} (`{layer_role}`, `precedence: {effective_prec}`)\n\n"
        f"## Layer Setup Blueprint ({tier_title})\n\n"
        f"- **Layer ID & Role**: `{layer_id}` (`{layer_role}`, `precedence: {effective_prec}`)\n"
        f"- **1-Hop Upstream Parent**: {parent_label}\n"
        f"- **Active Template Packs**: {tpl_csv}\n"
        f"- **Human-Stack Profile (Optional)**: {_HUMAN_STACK_BLUEPRINT_HINT}\n"
        f"- **Mission, Scope & Core Invariants**: {scope_hint}\n"
        f"- **Downstream Topology (Next Tier)**: {children_hint}\n"
        f"- **Authorized Layer Owner (`set-authority`)**: [Fill: Role title & owner email]\n\n"
        f"## Initial Chat Kickoff Prompt\n\n"
        f"```text\n"
        f"Read the filled Layer Setup Blueprint in README.md, system/mcp-layer.json, and "
        f".agents/LAYER_LINEAGE.md. Tailor antigravity/.gemini/config/AGENTS.md and "
        f"templates/{own_tpl_id}/rules/{own_tpl_id}.md with our mission and invariants without "
        f"duplicating upstream rules. Run make sync && make diff, update WORKROAD.md and "
        f"WORKTASK.md, and output the exact ./scripts/layer-config.sh {next_cmd_goal}.\n"
        f"```\n"
    )


def _render_lineage_markdown(resolved_tpl_name: str, rows: list[str]) -> str:
    """Render .agents/LAYER_LINEAGE.md with participating layers and Level 4 Project Blueprint."""
    tpl_label = resolved_tpl_name or "none"
    lines = [
        "# Multi-Layer Governance Lineage (`dotfiles-ubuntu`)\n",
        f"- **Applied Template Pack**: `{tpl_label}`\n",
        "## Participating Layers (Ordered by Precedence `0..100`)\n",
        "| Precedence | Layer | Layer ID | Role | Surface Bindings |",
        "|---:|---|---|---|---:|",
        *rows,
        "",
        "## Project Setup Blueprint (Level 4 — Application Workspace)",
        f"- **Applied Template Packs**: `{tpl_label}`",
        f"- **Human-Stack Profile (Optional)**: {_HUMAN_STACK_BLUEPRINT_HINT}",
        "- **Project / Service Purpose**: [Fill: Core product/service mission and bounded context]",
        "- **Architecture & Integrations**: [Fill: Domain modules, DB/APIs, and UI/CLI surface]",
        "- **Phase 1 Milestone Goal**: [Fill: Initial vertical slice or MVP deliverable]",
        "",
        "## Initial Chat Kickoff Prompt",
        "```text",
        "/sopen — Read .agents/LAYER_LINEAGE.md, all inherited .agents/rules/*.md, and our "
        "Project Setup Blueprint.",
        "Initialize README.md, docs/architecture/ (1:1:1 specs), WORKROAD.md, and WORKTASK.md "
        "for Phase 1, then propose the Pre-Edit Scope Blueprint for Task 1.",
        "```",
    ]
    return "\n".join(lines) + "\n"
