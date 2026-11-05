"""Global profile composer, subtree manifest registrar, and one-shot workspace bootstrapper.

Specification: docs/architecture/06_layer_governance_and_promotion_engines.md
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from dotfiles_mcp.core.constants import (
    AGENTS_MD_MAX_BYTES,
    BUSINESS_MODE_RULE_FILES,
    BUSINESS_MODE_TEMPLATES,
    COMMAND_CONSCIOUSNESS_TIERS,
    KEBAB_ID_RE,
    LAYER_MANIFEST_CONTRACT_REV,
    LAYER_ROLE_MAKEFILE_TARGETS,
    MAKEFILE_CUSTOM_TARGETS_MARKER,
    MAKEFILE_ROLE_HEADER_PREFIX,
    ROLE_DEFAULT_PRECEDENCE,
    SCIENCE_MODE_TEMPLATES,
    STATUS_EXCERPT_MAX_LINES,
    TECHNICAL_MODE_RULE_FILES,
    TECHNICAL_MODE_TEMPLATES,
    TEMPLATE_MANIFEST_CONTRACT_REV,
    VALID_LAYER_ROLES,
    VALID_SYNC_STRATEGIES,
)
from dotfiles_mcp.core.layer_topology_helpers import (
    _is_dest_template_newer,
    _render_layer_makefile,
    _render_layer_onboarding_readme,
    _resolve_default_parent_dir,
    _resolve_layer_entity_identity,
    _sync_mounted_children_into_parent,
)
from dotfiles_mcp.core.manifest_helpers import (
    _iter_layer_template_dirs,
    _merge_unique_strings,
    _resolve_effective_human_stack,
    _resolve_template_dest_dir,
    _resolve_template_dir,
    _stamp_schema_rev,
    classify_library_domain,
)
from dotfiles_mcp.governance.fork_configurator import (
    apply_fork_to_project,
    configure_fork_manifest,
    scaffold_template_pack,
)
from dotfiles_mcp.governance.git_governance_engine import inspect_git_governance_state
from dotfiles_mcp.governance.horizon_engine import (
    inspect_layer_horizon,
    reconcile_template_pack_sync,
)
from dotfiles_mcp.governance.promotion_engine import diff_project_against_layers

VALID_GLOBAL_PROFILES = ("human-base", "science", "technical", "business", "full")
_HB, _SB = ("human-base", "human-base.md"), ("science-base", "science-base.md")
_SE = ("software-engineering", "software-engineering.md")
_BB = ("business-base", "business-base.md")
PROFILE_TEMPLATE_CHAIN: dict[str, tuple[tuple[str, str], ...]] = {
    "human-base": (_HB,), "science": (_HB, _SB), "technical": (_HB, _SB, _SE),
    "business": (_HB, _BB), "full": (_HB, _SB, _SE, _BB),
}  # fmt: skip


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


def _ensure_fixed_mcp_registered(repo_dir: Path, target_home: Path) -> None:
    """Idempotently register dotfiles-mcp in <home>/.gemini/{config,antigravity}/mcp_config.json."""
    cfg_p = target_home / ".gemini/config/mcp_config.json"
    ag_p = target_home / ".gemini/antigravity/mcp_config.json"
    cfg_p.parent.mkdir(parents=True, exist_ok=True)
    data: dict[str, Any] = json.loads(cfg_p.read_text("utf-8")) if cfg_p.is_file() else {}
    srv_arg = str((repo_dir / "scripts/dotfiles_mcp_server.py").resolve())
    data.setdefault("mcpServers", {})["dotfiles-mcp"] = {"command": "python3", "args": [srv_arg]}
    cfg_p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    ag_p.parent.mkdir(parents=True, exist_ok=True)
    if not ag_p.exists() and not ag_p.is_symlink():
        ag_p.symlink_to(cfg_p)


def set_global_agents_profile(
    repo_dir: Path, profile: str, *, run_stow: bool = False,
    home_dir: Path | None = None, dry_run: bool = False,
) -> dict[str, Any]:  # fmt: skip
    """Compose antigravity/.gemini/config/AGENTS.md from modular base templates."""
    if profile not in VALID_GLOBAL_PROFILES:
        raise ValueError(f"Invalid global profile {profile!r}; must be in {VALID_GLOBAL_PROFILES}")
    sections, source_files = [], []
    for idx, (tpl_id, rule_filename) in enumerate(PROFILE_TEMPLATE_CHAIN[profile]):
        tdir = _resolve_template_dir(repo_dir, tpl_id) or (repo_dir / "templates" / tpl_id)
        rule_path = tdir / "rules" / rule_filename
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
    m_path = repo_dir / "system/mcp-layer.json"
    if not dry_run:
        target_agents.parent.mkdir(parents=True, exist_ok=True)
        target_agents.write_text(composed, encoding="utf-8")
        m_data = json.loads(m_path.read_text("utf-8")) if m_path.is_file() else {}
        if m_data.get("entity_kind") == "individual" or int(m_data.get("precedence", 10)) >= 85:
            m_data["global_profile"] = profile
            m_path.write_text(json.dumps(m_data, indent=2, ensure_ascii=False) + "\n", "utf-8")
        if run_stow:
            target_home, stow_bin = home_dir or Path.home(), shutil.which("stow") or "/usr/bin/stow"
            cmd = [stow_bin, "-t", str(target_home), "-R", "antigravity"]
            subprocess.run(cmd, cwd=repo_dir, check=True, capture_output=True, text=True)  # noqa: S603
            _ensure_fixed_mcp_registered(repo_dir, target_home)
            stow_executed = True

    return {"profile": profile, "source_files": source_files, "dry_run": dry_run,
        "target_file": str(target_agents.relative_to(repo_dir)), "size_bytes": composed_bytes,
        "budget_max_bytes": cap, "headroom_bytes": cap - composed_bytes,
        "stow_executed": stow_executed}  # fmt: skip


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
    dept_prec = ROLE_DEFAULT_PRECEDENCE["department"]
    svc_prec = ROLE_DEFAULT_PRECEDENCE["service-node"]
    entry: dict[str, Any] = {"name": layer_name, "layer_id": sub_id, "layer_role": sub_role,
        "precedence": int(sub_m.get("precedence", dept_prec)), "repository": repo_url,
        "branch": branch}  # fmt: skip
    raw_layers = root_manifest.get("mounted_layers", [])
    existing = [x for x in raw_layers if isinstance(x, dict) and x.get("name") != layer_name]
    existing.append(entry)
    existing.sort(key=lambda it: (int(it.get("precedence", svc_prec)), str(it.get("name", ""))))
    root_manifest["mounted_layers"] = existing
    if not dry_run:
        r_json = json.dumps(root_manifest, indent=2, ensure_ascii=False) + "\n"
        root_manifest_path.write_text(r_json, encoding="utf-8")
    return {"registered_layer": entry, "total_mounted_layers": len(existing), "dry_run": dry_run}


def _sync_templates_from_roots(
    target_dir: Path, effective_parent: Path, repo_dir: Path, tpl_names: list[str], *,
    skip_id: str = "", check_newer: bool = False, strategy: str = "accept-upstream",
    dry_run: bool = False,
) -> tuple[list[str], list[dict[str, Any]]]:  # fmt: skip
    """Copy or reconcile template packs from effective_parent and repo_dir into target_dir."""
    same_root = effective_parent.resolve() == repo_dir.resolve()
    roots = [repo_dir] if same_root else [effective_parent, repo_dir]
    expanded = list(dict.fromkeys(t for t in tpl_names if t and t != skip_id))
    for tpl_name in list(expanded):
        cur = tpl_name
        while src_d := next((d for r in roots if (d := _resolve_template_dir(r, cur))), None):
            tj = src_d / "template.json"
            ext = (
                str(json.loads(tj.read_text("utf-8")).get("extends") or "") if tj.is_file() else ""
            )
            if not ext or ext == skip_id or ext in expanded:
                break
            expanded.insert(expanded.index(tpl_name), ext)
            cur = ext
    copied, conflicts = list[str](), list[dict[str, Any]]()
    for tpl_name in expanded:
        src_tpl = next((d for r in roots if (d := _resolve_template_dir(r, tpl_name))), None)
        dest_tpl = _resolve_template_dest_dir(target_dir, tpl_name, src_tpl=src_tpl)
        local_tpl = _resolve_template_dir(target_dir, tpl_name) or dest_tpl
        if src_tpl is not None and src_tpl.resolve() != dest_tpl.resolve():
            is_newer = check_newer and _is_dest_template_newer(src_tpl, local_tpl)
            did_copy, c_list = reconcile_template_pack_sync(
                target_dir, tpl_name, src_tpl, dest_tpl,
                strategy=strategy, is_local_newer=is_newer, dry_run=dry_run,
            )  # fmt: skip
            if did_copy:
                copied.append(tpl_name)
            conflicts.extend(c_list)
    return copied, conflicts


def bootstrap_layer_workspace(
    repo_dir: Path, target_dir: Path, *, layer_id: str, layer_role: str = "department",
    precedence: int | None = None, description: str | None = None,
    upstream_repo: str | None = None, upstream_branch: str = "master",
    upstream_layer_id: str | None = None, parent_dir: Path | None = None,
    templates: list[str] | None = None, own_template_name: str | None = None,
    entity_kind: str | None = None, governing_root_id: str | None = None,
    scaffold_own_template: bool = True, dry_run: bool = False,
) -> dict[str, Any]:  # fmt: skip
    """One-shot initializer for a corporate, domain-policy, department, or squad workspace."""
    if not KEBAB_ID_RE.match(layer_id):
        raise ValueError(f"Invalid layer_id {layer_id!r}")
    if layer_role not in VALID_LAYER_ROLES:
        raise ValueError(f"Invalid layer_role {layer_role!r}")
    def_prec = ROLE_DEFAULT_PRECEDENCE.get(layer_role, ROLE_DEFAULT_PRECEDENCE["service-node"])
    effective_prec = precedence if precedence is not None else def_prec
    effective_parent = parent_dir if parent_dir is not None else repo_dir
    parent_manifest_path = effective_parent / "system" / "mcp-layer.json"
    inherited_templates: list[str] = []
    if parent_manifest_path.is_file():
        parent_manifest = json.loads(parent_manifest_path.read_text(encoding="utf-8"))
        p_ent = _resolve_layer_entity_identity(effective_parent, parent_manifest)
        if p_ent["entity_kind"] != "open-source" and (
            parent_dir is not None or parent_manifest.get("layer_role") not in (None, "workstation")
        ):
            entity_kind = entity_kind or str(p_ent["entity_kind"])
            p_fb = parent_manifest.get("layer_id", effective_parent.name)
            governing_root_id = governing_root_id or str(p_ent["governing_root_id"] or p_fb)
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
    dom_def = classify_library_domain(layer_id)["default_stack_templates"]
    requested_templates = _merge_unique_strings(inherited_templates, templates or dom_def)
    copied_templates, _ = _sync_templates_from_roots(
        target_dir, effective_parent, repo_dir, requested_templates, dry_run=dry_run
    )
    cfg_kw: dict[str, Any] = {"layer_id": layer_id, "layer_role": layer_role, "dry_run": dry_run,
        "precedence": effective_prec, "description": description, "prune_default_templates": True,
        "upstream_url": upstream_repo, "upstream_branch": upstream_branch,
        "upstream_id": upstream_layer_id, "entity_kind": entity_kind,
        "governing_root_id": governing_root_id}  # fmt: skip
    manifest_res = configure_fork_manifest(target_dir, **cfg_kw)
    own_tpl_id, all_tpls = own_template_name or layer_id, list(requested_templates)
    if scaffold_own_template and own_tpl_id not in all_tpls:
        all_tpls.append(own_tpl_id)
    if not dry_run and all_tpls:
        m_path = target_dir / "system/mcp-layer.json"
        m_data = json.loads(m_path.read_text(encoding="utf-8"))
        m_data["default_stack_templates"] = list(all_tpls)
        m_path.write_text(json.dumps(m_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    is_tech_sq = layer_role == "squad" and bool(set(requested_templates) & set(TECHNICAL_MODE_TEMPLATES))  # noqa: E501  # fmt: skip
    is_sci = bool(set(requested_templates) & set(SCIENCE_MODE_TEMPLATES))
    own_kind = "framework-stack" if is_tech_sq else ("science-stack" if is_sci else "business-stack")  # noqa: E501  # fmt: skip
    scaf_kw: dict[str, Any] = {"template_name": own_tpl_id, "kind": own_kind, "dry_run": dry_run,
        "description": description or f"{layer_id} ({layer_role}) governance pack",
        "register_binding": True, "rule_filename": f"{own_tpl_id}.md"}  # fmt: skip
    scaffold_res = scaffold_template_pack(target_dir, **scaf_kw) if scaffold_own_template else None
    ag_rule = "\n".join([
        "---", "trigger: always_on",
        f'description: "Layer governance rules for {layer_id} ({layer_role})."', "---", "",
        f"# {layer_id} Layer Rules (`{layer_role}`, `precedence: {effective_prec}`)", "",
        f"> Governed by `system/mcp-layer.json` (`layer_id: {layer_id}`).", "",
        "## Scope & Surface Target",
        f"- Governs `{layer_id}` (`{layer_role}`, `precedence: {effective_prec}`).", "",
        "## Normative Invariants",
        f"- Respect *Lex Superior* (`0..100`) and `templates/{own_tpl_id}/` contracts.", "",
        "## Verification & Sign-Off Gates",
        "- [ ] Verify `.agents/LAYER_LINEAGE.md` and `diff-project` parity before commit.", "",
    ])  # fmt: skip
    readme_md = _render_layer_onboarding_readme(
        layer_id, layer_role, effective_prec, own_tpl_id, all_tpls, upstream_layer_id
    )
    wt_md = (
        f"# Active Work Tasks — {layer_id}\n\n- [x] Initial layer bootstrap.\n"
        "- [ ] Complete `Layer Setup Blueprint` in `README.md` and run Kickoff Prompt.\n"
    )
    git_ign = "__pycache__/\n*.pyc\n.ruff_cache/\n.mypy_cache/\n.pytest_cache/\nlogs/\n"
    chg_md = f"# Changelog — {layer_id}\n\n## [Unreleased]\n- Initial bootstrap.\n"
    mk_txt = _render_layer_makefile(layer_id, layer_role, effective_parent, repo_dir)
    baseline_files = {".gitignore": git_ign, "layers/.gitkeep": "", "README.md": readme_md,
        "WORKTASK.md": wt_md, "CHANGELOG.md": chg_md, "Makefile": mk_txt,
        "antigravity/.gemini/config/AGENTS.md": ag_rule}  # fmt: skip
    created_baseline: list[str] = []
    for rel_path, content in baseline_files.items():
        dest_file = target_dir / rel_path
        if not dest_file.exists():
            created_baseline.append(rel_path)
            if not dry_run:
                dest_file.parent.mkdir(parents=True, exist_ok=True)
                dest_file.write_text(content, encoding="utf-8")
    for sub_d in ("reference", "architecture", "guides") if not dry_run else ():
        (target_dir / "docs" / sub_d).mkdir(parents=True, exist_ok=True)
        (target_dir / "docs" / sub_d / ".gitkeep").touch(exist_ok=True)

    tpl_ref_arg = ",".join(all_tpls) if all_tpls else None
    empty_apply: dict[str, Any] = {"applied_template": tpl_ref_arg, "files_materialized": []}
    ap_kw: dict[str, Any] = {"template_ref": tpl_ref_arg, "layers_filter": ["all"], "dry_run": False}  # noqa: E501  # fmt: skip
    apply_res = apply_fork_to_project(target_dir, target_dir, **ap_kw) if not dry_run else empty_apply  # noqa: E501  # fmt: skip
    scaf_id = scaffold_res["template_id"] if scaffold_res else None
    return {"target_dir": str(target_dir), "layer_id": layer_id, "dry_run": dry_run,
        "layer_role": layer_role, "precedence": effective_prec,
        "copied_templates": copied_templates, "scaffolded_template": scaf_id,
        "baseline_files_created": sorted(created_baseline),
        "applied_template": apply_res.get("applied_template"), "manifest": manifest_res,
        "files_materialized": apply_res.get("files_materialized", [])}  # fmt: skip


def sync_layer_workspace(
    repo_dir: Path, target_dir: Path, *, parent_dir: Path | None = None,
    templates: list[str] | None = None, strategy: str = "reconcile", dry_run: bool = False,
) -> dict[str, Any]:  # fmt: skip
    """Propagate upstream template updates into target_dir/templates/ and refresh .agents/."""
    if strategy not in VALID_SYNC_STRATEGIES:
        raise ValueError(f"Invalid sync strategy {strategy!r}; must be in {VALID_SYNC_STRATEGIES}")
    manifest_path = target_dir / "system" / "mcp-layer.json"
    if not manifest_path.is_file():
        raise ValueError(f"Missing target layer manifest: {manifest_path}")
    manifest: dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))
    own_id, raw_role = str(manifest.get("layer_id") or ""), str(manifest.get("layer_role") or "department")  # noqa: E501  # fmt: skip
    own_role = "squad" if raw_role == "team" else raw_role
    def_tpls = [str(t) for t in manifest.get("default_stack_templates", [])]
    stack_templates = _merge_unique_strings(def_tpls, templates or [])
    stale_rev = manifest.get("schema_version") != LAYER_MANIFEST_CONTRACT_REV
    if not dry_run and (stale_rev or raw_role == "team" or bool(templates)):
        manifest["schema_version"], manifest["layer_role"] = LAYER_MANIFEST_CONTRACT_REV, own_role
        manifest["default_stack_templates"] = list(stack_templates)
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", "utf-8")

    existing_tpls = [name for name, _p in _iter_layer_template_dirs(target_dir)]
    candidate_tpls = list(dict.fromkeys([*stack_templates, *existing_tpls]))
    eff_parent = _resolve_default_parent_dir(target_dir, parent_dir) or repo_dir
    sync_kw: dict[str, Any] = {
        "skip_id": own_id, "check_newer": True, "strategy": strategy, "dry_run": dry_run,
    }  # fmt: skip
    synced_templates, conflicts = _sync_templates_from_roots(
        target_dir, eff_parent, repo_dir, candidate_tpls, **sync_kw
    )
    for _tname, tdir in _iter_layer_template_dirs(target_dir) if not dry_run else ():
        _stamp_schema_rev(tdir / "template.json", TEMPLATE_MANIFEST_CONTRACT_REV)
    synced_children = _sync_mounted_children_into_parent(
        target_dir, manifest.get("mounted_layers", []), dry_run=dry_run
    )
    makefile_path = target_dir / "Makefile"
    cur_mk = makefile_path.read_text(encoding="utf-8") if makefile_path.is_file() else ""
    c_idx = cur_mk.find(MAKEFILE_CUSTOM_TARGETS_MARKER)
    c_tail = f"\n{cur_mk[c_idx:].strip()}\n" if c_idx != -1 else ""
    new_mk = _render_layer_makefile(own_id, own_role, eff_parent, repo_dir) + c_tail
    mk_ok = not cur_mk or cur_mk.startswith(MAKEFILE_ROLE_HEADER_PREFIX)
    mk_upgraded = mk_ok and cur_mk != new_mk
    if not dry_run:
        if not (set(stack_templates) & set(TECHNICAL_MODE_TEMPLATES)):
            for rf in ("science-base.md", "software-engineering.md"):
                (target_dir / ".agents/rules" / rf).unlink(missing_ok=True)
            for sk in ("testing", "refactoring", "validation", "oss-contribute"):
                shutil.rmtree(target_dir / ".agents/skills" / sk, ignore_errors=True)
        if mk_upgraded:
            makefile_path.write_text(new_mk, encoding="utf-8")
    app_svcs = [
        {"template": t, **rs} for t in candidate_tpls
        if (td := _resolve_template_dir(target_dir, t) or _resolve_template_dir(repo_dir, t))
        and (tj := td / "template.json").is_file()
        and isinstance(rs := json.loads(tj.read_text("utf-8")).get("runtime_service"), dict)
    ]  # fmt: skip
    tpl_ref = ",".join(stack_templates) if stack_templates else None
    apply_res = apply_fork_to_project(
        target_dir, target_dir, template_ref=tpl_ref, layers_filter=["all"], dry_run=dry_run
    )
    return {
        "target_dir": str(target_dir), "layer_id": own_id, "strategy": strategy,
        "dry_run": dry_run, "makefile_upgraded": mk_upgraded,
        "synced_templates": synced_templates, "reconciliation_conflicts": conflicts,
        "synced_mounted_layers": synced_children, "app_services_redeployed": app_svcs,
        "applied_template": apply_res.get("applied_template"),
        "files_materialized": apply_res.get("files_materialized", []),
        "participating_layers": apply_res.get("participating_layers", []),
    }  # fmt: skip


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
    has_tech = bool(
        set(TECHNICAL_MODE_RULE_FILES) & set(rules) or set(TECHNICAL_MODE_TEMPLATES) & set(tpls)
    )
    has_biz = bool(
        set(BUSINESS_MODE_RULE_FILES) & set(rules) or set(BUSINESS_MODE_TEMPLATES) & set(tpls)
        or role in ("corporate", "domain-policy") or (ws / "corporate").is_dir()
    )  # fmt: skip
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
        proc = subprocess.run([git_bin, *args], cwd=ws, check=False, capture_output=True, text=True)  # noqa: S603
        return proc.stdout.splitlines()

    g_stat = _git_lines("status", "--short", "--branch")
    g_log = _git_lines("log", "--oneline", "-5")
    lim, last_cid = STATUS_EXCERPT_MAX_LINES, uuid_m.group(0) if uuid_m else None
    s_ex, p_ex = "\n".join(s_txt.splitlines()[:lim]), "\n".join(trk_txt.splitlines()[:lim])
    mk_t = list(LAYER_ROLE_MAKEFILE_TARGETS.get(role, LAYER_ROLE_MAKEFILE_TARGETS["project"]))
    ent_id = _resolve_layer_entity_identity(ws, m, parent_dir=parent_dir)
    op_state, mcp_mode = str(ent_id["operating_state"]), str(ent_id["mcp_operating_mode"])
    hs = _resolve_effective_human_stack(ws, m)
    cmd_tiers = {k: [t for t in v if t in mk_t] for k, v in COMMAND_CONSCIOUSNESS_TIERS.items()}
    s_st = {"exists": s_file.is_file(), "last_conversation_id": last_cid, "excerpt": s_ex}
    a_root = ws if is_layer else (parent_dir or repo_dir)
    return {"workspace_dir": str(ws), "layer_id": lid, "layer_role": role,
        "entity_identity": ent_id, "visibility_scope": ent_id["visibility_scope"],
        "exposure_boundary": ent_id["exposure_boundary"],
        "can_expose_to_oss": ent_id["can_expose_to_oss"],
        "global_profile": str(m.get("global_profile", "human-base")),
        "human_stack": hs["facets"], "human_stack_scope": hs["scope"],
        "operating_state": op_state, "mcp_operating_mode": mcp_mode, "precedence": prec,
        "workspace_mode": mode, "is_oss_dev_workspace": op_state == "oss-dev",
        "command_tiers": cmd_tiers, "active_templates": tpls, "active_rules": rules,
        "available_makefile_targets": mk_t, "git_governance": inspect_git_governance_state(ws),
        "has_project_start_skill": (ws / ".agents/skills/start/SKILL.md").is_file(),
        "session_state": s_st, "priority_state": {"active_tracker": active_trk, "excerpt": p_ex},
        "git_state": {"is_git_repo": is_git, "status_short": g_stat, "recent_commits": g_log},
        "horizon": inspect_layer_horizon(repo_dir, ws, parent_dir=parent_dir) if is_layer else None,
        "agent_diff": diff_project_against_layers(a_root, ws)}  # fmt: skip
