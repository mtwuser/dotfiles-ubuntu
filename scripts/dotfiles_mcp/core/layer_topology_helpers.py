"""Layer parent/child topology discovery, Makefile rendering, and mounted subtree sync helpers.

Specification: docs/architecture/03_contextual_mcp_and_federation.md
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from dotfiles_mcp.core.constants import (
    DEFAULT_SQUAD_ONBOARDING_SPEC,
    HUMAN_STACK_BLUEPRINT_HINT,
    LAYER_MAKEFILE_RECIPES,
    LAYER_MANIFEST_CONTRACT_REV,
    LAYER_ROLE_MAKEFILE_TARGETS,
    MAKEFILE_ROLE_HEADER_PREFIX,
    REPO_DIR,
    ROLE_ONBOARDING_SPECS,
    TEMPLATE_MANIFEST_CONTRACT_REV,
)
from dotfiles_mcp.core.manifest_helpers import (
    _has_stale_schema,
    _iter_layer_template_dirs,
    _resolve_template_dir,
    _sha256_file,
    _stamp_schema_rev,
)


def _is_git_historical_blob(src_tpl: Path, dest_rf: Path) -> bool:
    """Return True if dest_rf matches any historical git blob in src_tpl's repository."""
    src_repo = next((p for p in src_tpl.parents if (p / ".git").exists()), None)
    if src_repo is None:
        return True
    raw = dest_rf.read_bytes()
    oid = hashlib.sha1(f"blob {len(raw)}\0".encode() + raw, usedforsecurity=False).hexdigest()
    cmd = [shutil.which("git") or "/usr/bin/git", "-C", str(src_repo), "cat-file", "-e", oid]
    return subprocess.run(cmd, check=False, capture_output=True).returncode == 0  # noqa: S603


def _is_dest_template_newer(src_tpl: Path, dest_tpl: Path) -> bool:
    """Return True if dest_tpl has a modified rule file with newer mtime, sha, or local blob."""
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
                else (
                    dest_rf.stat().st_mtime_ns > src_rf.stat().st_mtime_ns
                    or not _is_git_historical_blob(src_tpl, dest_rf)
                )
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


def _is_makefile_outdated(ws_dir: Path, role: str) -> bool:
    """Return True if ws_dir/Makefile is a generated layer Makefile missing current targets."""
    req_t = LAYER_ROLE_MAKEFILE_TARGETS.get(role, LAYER_ROLE_MAKEFILE_TARGETS["project"])
    mk_txt = (ws_dir / "Makefile").read_text("utf-8") if (ws_dir / "Makefile").is_file() else ""
    return mk_txt.startswith(MAKEFILE_ROLE_HEADER_PREFIX) and (
        any(f"\n{t}:\n" not in mk_txt for t in req_t)
        or "--upstream-dir $(TARGET_REPO)" not in mk_txt
    )


def _render_layer_makefile(
    layer_id: str, layer_role: str, effective_parent: Path, repo_dir: Path
) -> str:
    """Render a role-specialized Makefile for day-to-day layer horizon, sync, and promotion."""
    p_val = (
        str(effective_parent.resolve()) if effective_parent.resolve() != repo_dir.resolve() else ""
    )
    dev_repo = "$(HOME)/Projects/dev-$(notdir $(DOTFILES_DIR))"
    contrib_cfg = (
        f"CONTRIB_REPO ?= $(if $(wildcard {dev_repo}/system/mcp-layer.json),"
        f"{dev_repo},$(DOTFILES_DIR))\nTARGET_REPO ?= $(CONTRIB_REPO)\n"
        if layer_role == "corporate"
        else "TARGET_REPO ?= $(PARENT_DIR)\n"
    )
    active = LAYER_ROLE_MAKEFILE_TARGETS.get(layer_role, LAYER_ROLE_MAKEFILE_TARGETS["department"])
    sel = [t for t in active if t in LAYER_MAKEFILE_RECIPES]
    phony, help_lines = " ".join(["help", *sel]), "\n".join(f'\t@echo "  make {t}"' for t in sel)
    recipes = "\n".join(f"{t}:\n{LAYER_MAKEFILE_RECIPES[t]}" for t in sel)
    return (
        f"# Role-Specialized Layer Makefile — {layer_id} ({layer_role})\n"
        f"DOTFILES_DIR ?= $(HOME)/dotfiles-ubuntu\nPARENT_DIR ?= {p_val}\n{contrib_cfg}"
        "PARENT_FLAG = $(if $(PARENT_DIR),--parent-dir $(PARENT_DIR),)\nPR_FLAGS ?= --create-pr\n\n"
        f".PHONY: {phony}\n"
        f'help:\n\t@echo "Layer Workspace: {layer_id} ({layer_role})"\n{help_lines}\n\n{recipes}\n'
    )


def _inspect_mounted_children_drifts(
    workspace_dir: Path, mounted_layers: list[Any]
) -> list[dict[str, Any]]:
    """Detect contract, Makefile, or shared-template drift inside mounted layers/<child>/."""
    ws, drifts = workspace_dir.resolve(), []
    for entry in (e for e in (mounted_layers or []) if isinstance(e, dict)):
        cname = str(entry.get("name") or entry.get("layer_id") or "").strip()
        mdir = ws / "layers" / cname
        if not cname or not mdir.is_dir():
            continue
        cm_f = mdir / "system/mcp-layer.json"
        cm = json.loads(cm_f.read_text("utf-8")) if cm_f.is_file() else {}
        crole = str(cm.get("layer_role") or entry.get("layer_role") or "department")
        c_files = (
            ["system/mcp-layer.json"]
            if _has_stale_schema(cm_f, LAYER_MANIFEST_CONTRACT_REV)
            else []
        )
        if _is_makefile_outdated(mdir, crole):
            c_files.append("Makefile")
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
    """Synchronize parent contracts, Makefile, and shared templates into layers/<child>/."""
    ws = target_dir.resolve()
    synced = [str(d["layer_id"]) for d in _inspect_mounted_children_drifts(ws, mounted_layers)]
    for cname in () if dry_run else synced:
        mdir, cm_f = ws / "layers" / cname, ws / "layers" / cname / "system/mcp-layer.json"
        _stamp_schema_rev(cm_f, LAYER_MANIFEST_CONTRACT_REV)
        cm = json.loads(cm_f.read_text("utf-8")) if cm_f.is_file() else {}
        cid, crole = str(cm.get("layer_id") or cname), str(cm.get("layer_role") or "department")
        if _is_makefile_outdated(mdir, crole):
            (mdir / "Makefile").write_text(
                _render_layer_makefile(cid, crole, ws, REPO_DIR), "utf-8"
            )
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


def _render_layer_onboarding_readme(
    layer_id: str, layer_role: str, effective_prec: int, own_tpl_id: str,
    active_templates: list[str], parent_id: str | None = None,
) -> str:  # fmt: skip
    """Render a role-specific Layer Setup Blueprint and Initial Chat Kickoff Prompt."""
    tier_title, scope_hint, children_hint, next_cmd_goal = ROLE_ONBOARDING_SPECS.get(
        layer_role, DEFAULT_SQUAD_ONBOARDING_SPEC
    )
    tpl_csv = ", ".join(f"`{t}`" for t in active_templates) or "`none`"
    parent_label = f"`{parent_id}`" if parent_id else "`open-source-root`"
    return (
        f"# {layer_id} (`{layer_role}`, `precedence: {effective_prec}`)\n\n"
        f"## Layer Setup Blueprint ({tier_title})\n\n"
        f"- **Layer ID & Role**: `{layer_id}` (`{layer_role}`, `precedence: {effective_prec}`)\n"
        f"- **1-Hop Upstream Parent**: {parent_label}\n"
        f"- **Active Template Packs**: {tpl_csv}\n"
        f"- **Human-Stack Profile (Optional)**: {HUMAN_STACK_BLUEPRINT_HINT}\n"
        f"- **Mission, Scope & Core Invariants**: {scope_hint}\n"
        f"- **Downstream Topology (Next Tier)**: {children_hint}\n"
        f"- **Authorized Layer Owner (`set-authority`)**: [Fill: Role title & owner email]\n\n"
        f"## Initial Chat Kickoff Prompt\n\n```text\n"
        f"Read the filled Layer Setup Blueprint in README.md, system/mcp-layer.json, and "
        f".agents/LAYER_LINEAGE.md. Tailor antigravity/.gemini/config/AGENTS.md and "
        f"templates/{own_tpl_id}/rules/{own_tpl_id}.md with our mission and invariants without "
        f"duplicating upstream rules. Run make sync && make diff, update WORKROAD.md and "
        f"WORKTASK.md, and output the exact ./scripts/layer-config.sh {next_cmd_goal}.\n```\n"
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
        f"- **Human-Stack Profile (Optional)**: {HUMAN_STACK_BLUEPRINT_HINT}",
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
