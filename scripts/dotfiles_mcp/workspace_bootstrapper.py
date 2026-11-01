"""Global profile composer, subtree manifest registrar, and one-shot workspace bootstrapper.

Specification: docs/architecture/04_compaction_surface_and_promotion_engines.md
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from dotfiles_mcp.constants import (
    AGENTS_MD_MAX_BYTES,
    COMMAND_CONSCIOUSNESS_TIERS,
    DEFAULT_INITIAL_LAYER_VERSION,
    KEBAB_ID_RE,
    LAYER_MAKEFILE_RECIPES,
    LAYER_ROLE_MAKEFILE_TARGETS,
    MCP_OPERATING_MODES,
    ROLE_DEFAULT_PRECEDENCE,
    STATUS_EXCERPT_MAX_LINES,
    VALID_LAYER_ROLES,
)
from dotfiles_mcp.fork_configurator import (
    apply_fork_to_project,
    configure_fork_manifest,
    scaffold_template_pack,
)
from dotfiles_mcp.git_governance_engine import inspect_git_governance_state
from dotfiles_mcp.manifest_helpers import (
    _is_dest_template_newer,
    _iter_layer_template_dirs,
    _merge_unique_strings,
    _render_layer_onboarding_readme,
    _resolve_template_dest_dir,
    _resolve_template_dir,
    _sync_mounted_children_into_parent,
)
from dotfiles_mcp.promotion_engine import diff_project_against_layers, inspect_layer_horizon

VALID_GLOBAL_PROFILES = ("human-core", "technical", "business", "full")
_HC = ("human-core", "human-core.md")
_TB = ("technical-base", "technical-base.md")
_BB = ("business-base", "business-base.md")
PROFILE_TEMPLATE_CHAIN: dict[str, tuple[tuple[str, str], ...]] = {
    "human-core": (_HC,),
    "technical": (_HC, _TB),
    "business": (_HC, _BB),
    "full": (_HC, _TB, _BB),
}


def _strip_frontmatter(markdown_text: str) -> str:
    """Strip an optional leading YAML frontmatter block ('--- ... ---')."""
    text = markdown_text.strip()
    end_idx = text.find("\n---\n", 4) if text.startswith("---\n") else -1
    return text[end_idx + 5 :].strip() if end_idx != -1 else text


def _strip_secondary_header(markdown_text: str) -> str:
    """Strip frontmatter, top H1, and introductory blockquote for secondary profiles."""
    lines, idx = _strip_frontmatter(markdown_text).splitlines(), 0
    while idx < len(lines) and (
        lines[idx].startswith(("# ", ">")) or not lines[idx].strip() or lines[idx].strip() == "---"
    ):
        idx += 1
    return "\n".join(lines[idx:]).strip()


def set_global_agents_profile(
    repo_dir: Path,
    profile: str,
    *,
    run_stow: bool = False,
    home_dir: Path | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Compose antigravity/.gemini/config/AGENTS.md from modular base templates."""
    if profile not in VALID_GLOBAL_PROFILES:
        raise ValueError(f"Invalid global profile {profile!r}; must be in {VALID_GLOBAL_PROFILES}")
    sections, source_files = [], []
    for idx, (tpl_id, rule_filename) in enumerate(PROFILE_TEMPLATE_CHAIN[profile]):
        rule_path = repo_dir / "templates" / tpl_id / "rules" / rule_filename
        if not rule_path.is_file():
            rel_r = rule_path.relative_to(repo_dir)
            raise ValueError(f"Missing profile template rule file: {rel_r}")
        source_files.append(str(rule_path.relative_to(repo_dir)))
        raw_text = rule_path.read_text(encoding="utf-8").strip()
        sec = _strip_frontmatter(raw_text) if idx == 0 else _strip_secondary_header(raw_text)
        sections.append(sec)

    composed = "\n\n---\n\n".join(sections) + "\n"
    composed_bytes, cap = len(composed.encode("utf-8")), AGENTS_MD_MAX_BYTES
    if composed_bytes > cap:
        raise ValueError(f"Composed AGENTS.md size ({composed_bytes} bytes) exceeds {cap}-byte cap")
    target_agents, stow_executed = repo_dir / "antigravity/.gemini/config/AGENTS.md", False
    if not dry_run:
        target_agents.parent.mkdir(parents=True, exist_ok=True)
        target_agents.write_text(composed, encoding="utf-8")
        if run_stow:
            stow_bin = shutil.which("stow") or "/usr/bin/stow"
            cmd = [stow_bin, "-t", str(home_dir or Path.home()), "-R", "antigravity"]
            subprocess.run(cmd, cwd=repo_dir, check=True, capture_output=True, text=True)  # noqa: S603
            stow_executed = True

    res: dict[str, Any] = {"profile": profile, "source_files": source_files, "dry_run": dry_run}
    res.update(target_file=str(target_agents.relative_to(repo_dir)), size_bytes=composed_bytes)
    res.update(budget_max_bytes=cap, headroom_bytes=cap - composed_bytes)
    res["stow_executed"] = stow_executed
    return res


def register_mounted_subtree(
    repo_dir: Path, layer_name: str, repo_url: str, branch: str = "master", *, dry_run: bool = False
) -> dict[str, Any]:
    """Upsert a mounted subtree entry inside root system/mcp-layer.json -> mounted_layers."""
    if not KEBAB_ID_RE.match(layer_name):
        raise ValueError(f"Invalid layer_name {layer_name!r}")
    root_manifest_path = repo_dir / "system" / "mcp-layer.json"
    if not root_manifest_path.is_file():
        raise ValueError(f"Missing root manifest: {root_manifest_path}")
    root_manifest: dict[str, Any] = json.loads(root_manifest_path.read_text(encoding="utf-8"))
    sub_p = repo_dir / "layers" / layer_name / "system" / "mcp-layer.json"
    sub_m: dict[str, Any] = json.loads(sub_p.read_text(encoding="utf-8")) if sub_p.is_file() else {}
    sub_id = str(sub_m.get("layer_id") or layer_name)
    sub_role = str(sub_m.get("layer_role") or "department")
    dept_prec, svc_prec = (
        ROLE_DEFAULT_PRECEDENCE["department"],
        ROLE_DEFAULT_PRECEDENCE["service-node"],
    )
    entry: dict[str, Any] = {"name": layer_name, "layer_id": sub_id, "layer_role": sub_role}
    entry.update(
        precedence=int(sub_m.get("precedence", dept_prec)), repository=repo_url, branch=branch
    )
    raw_layers = root_manifest.get("mounted_layers", [])
    existing = [x for x in raw_layers if isinstance(x, dict) and x.get("name") != layer_name]
    existing.append(entry)
    existing.sort(
        key=lambda item: (int(item.get("precedence", svc_prec)), str(item.get("name", "")))
    )
    root_manifest["mounted_layers"] = existing
    if not dry_run:
        root_manifest_path.write_text(json.dumps(root_manifest, indent=2) + "\n", encoding="utf-8")
    return {"registered_layer": entry, "total_mounted_layers": len(existing), "dry_run": dry_run}


def _render_layer_makefile(
    layer_id: str, layer_role: str, effective_parent: Path, repo_dir: Path
) -> str:
    """Render a role-specialized Makefile for day-to-day layer horizon, sync, and promotion."""
    parent_val = (
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
        f"DOTFILES_DIR ?= $(HOME)/dotfiles-ubuntu\nPARENT_DIR ?= {parent_val}\n{contrib_cfg}"
        "PARENT_FLAG = $(if $(PARENT_DIR),--parent-dir $(PARENT_DIR),)\nPR_FLAGS ?= --create-pr\n\n"
        f".PHONY: {phony}\n"
        f'help:\n\t@echo "Layer Workspace: {layer_id} ({layer_role})"\n{help_lines}\n\n{recipes}\n'
    )


def _sync_templates_from_roots(
    target_dir: Path,
    effective_parent: Path,
    repo_dir: Path,
    tpl_names: list[str],
    *,
    skip_id: str = "",
    check_newer: bool = False,
    dry_run: bool = False,
) -> list[str]:
    """Copy or refresh template packs from effective_parent and repo_dir into target_dir."""
    same_root = effective_parent.resolve() == repo_dir.resolve()
    roots = [repo_dir] if same_root else [effective_parent, repo_dir]
    copied: list[str] = []
    for tpl_name in tpl_names:
        if tpl_name == skip_id:
            continue
        src_tpl = next((d for r in roots if (d := _resolve_template_dir(r, tpl_name))), None)
        dest_tpl = _resolve_template_dest_dir(target_dir, tpl_name, src_tpl=src_tpl)
        if (
            src_tpl is not None
            and src_tpl.resolve() != dest_tpl.resolve()
            and not (check_newer and _is_dest_template_newer(src_tpl, dest_tpl))
        ):
            copied.append(tpl_name)
            if not dry_run:
                shutil.rmtree(dest_tpl, ignore_errors=True)
                dest_tpl.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(src_tpl, dest_tpl)
    return copied


def bootstrap_layer_workspace(
    repo_dir: Path,
    target_dir: Path,
    *,
    layer_id: str,
    layer_role: str = "department",
    precedence: int | None = None,
    description: str | None = None,
    upstream_repo: str | None = None,
    upstream_branch: str = "master",
    upstream_layer_id: str | None = None,
    parent_dir: Path | None = None,
    templates: list[str] | None = None,
    own_template_name: str | None = None,
    scaffold_own_template: bool = True,
    dry_run: bool = False,
) -> dict[str, Any]:
    """One-shot initializer for a corporate, domain-policy, department, or squad workspace."""
    if not KEBAB_ID_RE.match(layer_id):
        raise ValueError(f"Invalid layer_id {layer_id!r}")
    if layer_role not in VALID_LAYER_ROLES:
        raise ValueError(f"Invalid layer_role {layer_role!r}")
    effective_prec = (
        precedence
        if precedence is not None
        else ROLE_DEFAULT_PRECEDENCE.get(layer_role, ROLE_DEFAULT_PRECEDENCE["service-node"])
    )
    effective_parent = parent_dir if parent_dir is not None else repo_dir
    parent_manifest_path = effective_parent / "system" / "mcp-layer.json"
    inherited_templates: list[str] = []
    if parent_manifest_path.is_file():
        parent_manifest = json.loads(parent_manifest_path.read_text(encoding="utf-8"))
        if parent_manifest.get("layer_role") not in (None, "workstation"):
            upstream_layer_id = upstream_layer_id or parent_manifest.get("layer_id")
            upstream_repo = upstream_repo or parent_manifest.get("repository")
            if not upstream_repo and (effective_parent / ".git").exists():
                git_bin = shutil.which("git") or "/usr/bin/git"
                cmd = [git_bin, "config", "--get", "remote.origin.url"]
                proc = subprocess.run(  # noqa: S603
                    cmd, cwd=effective_parent, check=False, capture_output=True, text=True
                )
                upstream_repo = proc.stdout.strip() or None
            def_tpls = [str(pt) for pt in parent_manifest.get("default_stack_templates", [])]
            inherited_templates = _merge_unique_strings(def_tpls)
    requested_templates = _merge_unique_strings(inherited_templates, templates or [])
    copied_templates = _sync_templates_from_roots(
        target_dir, effective_parent, repo_dir, requested_templates, dry_run=dry_run
    )
    cfg_kw: dict[str, Any] = {"layer_id": layer_id, "layer_role": layer_role, "dry_run": dry_run}
    cfg_kw.update(precedence=effective_prec, description=description, prune_default_templates=True)
    cfg_kw.update(
        upstream_url=upstream_repo, upstream_branch=upstream_branch, upstream_id=upstream_layer_id
    )
    manifest_res = configure_fork_manifest(target_dir, **cfg_kw)
    own_tpl_id, all_tpls = own_template_name or layer_id, list(requested_templates)
    if scaffold_own_template and own_tpl_id not in all_tpls:
        all_tpls.append(own_tpl_id)
    if not dry_run and all_tpls:
        m_path = target_dir / "system/mcp-layer.json"
        m_data = json.loads(m_path.read_text(encoding="utf-8"))
        m_data["default_stack_templates"] = list(all_tpls)
        m_path.write_text(json.dumps(m_data, indent=2) + "\n", encoding="utf-8")

    is_pol = layer_role in ("domain-policy", "corporate")
    own_kind = (
        "domain-policy-pack"
        if is_pol
        else ("department-pack" if layer_role == "department" else "project-overlay")
    )
    scaf_kw: dict[str, Any] = {"template_name": own_tpl_id, "kind": own_kind, "dry_run": dry_run}
    scaf_kw.update(description=description or f"{layer_id} ({layer_role}) governance pack")
    scaf_kw.update(register_binding=True, rule_filename=f"{own_tpl_id}.md")
    scaffold_res = scaffold_template_pack(target_dir, **scaf_kw) if scaffold_own_template else None
    ag_rule = (
        f"---\ntrigger: always_on\n"
        f'description: "Layer governance rules for {layer_id} ({layer_role})."\n---\n\n'
        f"# {layer_id} Layer Rules (`{layer_role}`, `precedence: {effective_prec}`)\n\n"
        f"> Governed by `system/mcp-layer.json` (`layer_id: {layer_id}`).\n\n"
        f"## Scope & Surface Target\n"
        f"- Governs `{layer_id}` (`{layer_role}`, `precedence: {effective_prec}`).\n\n"
        f"## Normative Invariants\n"
        f"- Respect *Lex Superior* (`0..100`) and `templates/{own_tpl_id}/` contracts.\n\n"
        "## Verification & Sign-Off Gates\n"
        "- [ ] Verify `.agents/LAYER_LINEAGE.md` and `diff-project` parity before commit.\n"
    )
    chg_hdr = f"# Changelog — {layer_id}\n\n## [Unreleased]\n\n---\n\n"
    init_ver = DEFAULT_INITIAL_LAYER_VERSION
    baseline_files = {
        "VERSION": f"{init_ver}\n",
        ".gitignore": "__pycache__/\n*.pyc\n.ruff_cache/\n.mypy_cache/\n.pytest_cache/\nlogs/\n",
        "layers/.gitkeep": "",
        "Makefile": _render_layer_makefile(layer_id, layer_role, effective_parent, repo_dir),
        "README.md": _render_layer_onboarding_readme(
            layer_id, layer_role, effective_prec, own_tpl_id, all_tpls, upstream_layer_id
        ),
        "CHANGELOG.md": f"{chg_hdr}## [{init_ver}]\n- Initial layer bootstrap.\n",
        "WORKTASK.md": (
            f"# Active Work Tasks — {layer_id}\n\n- [x] Initial layer bootstrap (`v{init_ver}`).\n"
            "- [ ] Complete `Layer Setup Blueprint` in `README.md` and run Kickoff Prompt.\n"
        ),
        "antigravity/.gemini/config/AGENTS.md": ag_rule,
    }
    created_baseline: list[str] = []
    for rel_path, content in baseline_files.items():
        dest_file = target_dir / rel_path
        if not dest_file.exists():
            created_baseline.append(rel_path)
            if not dry_run:
                dest_file.parent.mkdir(parents=True, exist_ok=True)
                dest_file.write_text(content, encoding="utf-8")

    tpl_ref_arg = ",".join(all_tpls) if all_tpls else None
    empty_apply: dict[str, Any] = {"applied_template": tpl_ref_arg, "files_materialized": []}
    apply_res: dict[str, Any] = (
        apply_fork_to_project(
            target_dir, target_dir, template_ref=tpl_ref_arg, layers_filter=["all"], dry_run=False
        )
        if not dry_run
        else empty_apply
    )
    scaf_id = scaffold_res["template_id"] if scaffold_res else None
    out: dict[str, Any] = {"target_dir": str(target_dir), "layer_id": layer_id, "dry_run": dry_run}
    out.update(layer_role=layer_role, precedence=effective_prec, copied_templates=copied_templates)
    out.update(scaffolded_template=scaf_id, baseline_files_created=sorted(created_baseline))
    out.update(applied_template=apply_res.get("applied_template"), manifest=manifest_res)
    out["files_materialized"] = apply_res.get("files_materialized", [])
    return out


def sync_layer_workspace(
    repo_dir: Path,
    target_dir: Path,
    *,
    parent_dir: Path | None = None,
    templates: list[str] | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Propagate upstream template updates into target_dir/templates/ and refresh .agents/."""
    manifest_path = target_dir / "system" / "mcp-layer.json"
    if not manifest_path.is_file():
        raise ValueError(f"Missing target layer manifest: {manifest_path}")
    manifest: dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))
    own_id, own_role = (
        str(manifest.get("layer_id") or ""),
        str(manifest.get("layer_role") or "department"),
    )
    def_tpls = [str(t) for t in manifest.get("default_stack_templates", [])]
    stack_templates = _merge_unique_strings(def_tpls, templates or [])
    if not dry_run and templates:
        manifest["default_stack_templates"] = list(stack_templates)
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    existing_tpls = [name for name, _p in _iter_layer_template_dirs(target_dir)]
    candidate_tpls = list(dict.fromkeys([*stack_templates, *existing_tpls]))
    eff_parent = parent_dir if parent_dir is not None else repo_dir
    sync_kw: dict[str, Any] = {"skip_id": own_id, "check_newer": True, "dry_run": dry_run}
    synced_templates = _sync_templates_from_roots(
        target_dir, eff_parent, repo_dir, candidate_tpls, **sync_kw
    )
    synced_children = _sync_mounted_children_into_parent(
        target_dir, manifest.get("mounted_layers", []), dry_run=dry_run
    )
    makefile_path = target_dir / "Makefile"
    if not dry_run and not makefile_path.exists():
        mk_txt = _render_layer_makefile(own_id, own_role, eff_parent, repo_dir)
        makefile_path.write_text(mk_txt, encoding="utf-8")
    tpl_ref = ",".join(stack_templates) if stack_templates else None
    apply_res = apply_fork_to_project(
        target_dir, target_dir, template_ref=tpl_ref, layers_filter=["all"], dry_run=dry_run
    )
    res: dict[str, Any] = {"target_dir": str(target_dir), "layer_id": own_id, "dry_run": dry_run}
    res.update(synced_templates=synced_templates, synced_mounted_layers=synced_children)
    res.update(applied_template=apply_res.get("applied_template"))
    res["files_materialized"] = apply_res.get("files_materialized", [])
    res["participating_layers"] = apply_res.get("participating_layers", [])
    return res


def inspect_workspace_status(
    repo_dir: Path, target_dir: Path, *, parent_dir: Path | None = None
) -> dict[str, Any]:
    """Return a single-call consolidated status digest for /sopen and day-to-day layer ops."""
    ws, m_path = target_dir.resolve(), target_dir.resolve() / "system" / "mcp-layer.json"
    is_layer = m_path.is_file()
    m: dict[str, Any] = json.loads(m_path.read_text(encoding="utf-8")) if is_layer else {}
    role, lid = str(m.get("layer_role", "project")), str(m.get("layer_id", ws.name))
    prec = int(m.get("precedence", ROLE_DEFAULT_PRECEDENCE["project"]))
    tpls = [str(x) for x in m.get("default_stack_templates", [])]
    rules = [p.name for p in sorted((ws / ".agents/rules").glob("*.md"))]
    has_tech = bool({"technical-base.md", "coding.md"} & set(rules) or "technical-base" in tpls)
    has_biz = bool(
        "business-base.md" in rules
        or "business-base" in tpls
        or role in ("corporate", "domain-policy")
        or (ws / "corporate").is_dir()
    )
    mode = "hybrid" if (has_tech and has_biz) else ("business" if has_biz else "technical")
    s_file = ws / ".agents/SESSION.md"
    s_txt = s_file.read_text(encoding="utf-8") if s_file.is_file() else ""
    uuid_m = re.search(r"\b[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\b", s_txt)
    trackers = ("WORKTASK.md", "WORKROAD.md", "ROADMAP.md", "BACKLOG.md", "README.md")
    active_trk = next((t for t in trackers if (ws / t).is_file()), None)
    trk_txt = (ws / active_trk).read_text(encoding="utf-8") if active_trk else ""
    git_bin, is_git = shutil.which("git") or "/usr/bin/git", (ws / ".git").exists()

    def _git_lines(*args: str) -> list[str]:
        if not is_git:
            return []
        proc = subprocess.run(  # noqa: S603
            [git_bin, *args], cwd=ws, check=False, capture_output=True, text=True
        )
        return proc.stdout.splitlines()

    g_stat = _git_lines("status", "--short", "--branch")
    g_log = _git_lines("log", "--oneline", "-5")
    lim, last_cid = STATUS_EXCERPT_MAX_LINES, uuid_m.group(0) if uuid_m else None
    s_ex, p_ex = "\n".join(s_txt.splitlines()[:lim]), "\n".join(trk_txt.splitlines()[:lim])
    mk_t = list(LAYER_ROLE_MAKEFILE_TARGETS.get(role, LAYER_ROLE_MAKEFILE_TARGETS["project"]))
    is_ro_app = role == "workstation" and (ws / ".workstation-state.json").is_file()
    op_state = (
        "oss-readonly-appliance"
        if is_ro_app
        else (
            "oss-dev"
            if role == "workstation"
            else ("corporate-root" if role == "corporate" else role)
        )
    )
    mcp_mode = MCP_OPERATING_MODES.get(op_state, "project-consumer-only")
    cmd_tiers = {k: [t for t in v if t in mk_t] for k, v in COMMAND_CONSCIOUSNESS_TIERS.items()}
    out: dict[str, Any] = {"workspace_dir": str(ws), "layer_id": lid, "layer_role": role}
    out.update(operating_state=op_state, mcp_operating_mode=mcp_mode, precedence=prec)
    out.update(workspace_mode=mode, is_oss_dev_workspace=op_state == "oss-dev")
    out.update(command_tiers=cmd_tiers, active_templates=tpls, active_rules=rules)
    out["available_makefile_targets"] = mk_t
    out.update(git_governance=inspect_git_governance_state(ws))
    out["has_project_start_skill"] = (ws / ".agents/skills/start/SKILL.md").is_file()
    out["session_state"] = {
        "exists": s_file.is_file(),
        "last_conversation_id": last_cid,
        "excerpt": s_ex,
    }
    out["priority_state"] = {"active_tracker": active_trk, "excerpt": p_ex}
    out["git_state"] = {"is_git_repo": is_git, "status_short": g_stat, "recent_commits": g_log}
    out["horizon"] = (
        inspect_layer_horizon(repo_dir, ws, parent_dir=parent_dir) if is_layer else None
    )
    out["agent_diff"] = diff_project_against_layers(ws if is_layer else repo_dir, ws)
    return out
