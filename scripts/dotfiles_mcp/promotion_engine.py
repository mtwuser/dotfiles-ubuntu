"""Multi-layer rule comparison, project diffing, and upward governance promotion engine.

Specification: docs/architecture/04_compaction_surface_and_promotion_engines.md
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any

from dotfiles_mcp.authority_engine import (
    _is_oss_root_manifest,
    _load_manifest_dict,
    build_upward_promotion_pr_plan,
    verify_layer_operation_authority,
    verify_oss_promotion_agnosticism,
    verify_single_hop_upstream,
)
from dotfiles_mcp.constants import (
    AGENTS_ASSETS_PREFIX,
    AGENTS_MD_MAX_BYTES,
    AGENTS_RULES_PREFIX,
    KEBAB_ID_RE,
    MATERIALIZED_RULE_RE,
    MIN_ROUTING_KEYWORD_LEN,
    OWNER_WRITABLE_MODE_BIT,
    REPO_DIR,
    ROLE_DEFAULT_PRECEDENCE,
    SKILL_MD_MAX_LINES,
    TEMPLATE_STACK_GROUP_DIRS,
    VALID_DELEGATION_DIRS,
    VALID_TRACKER_FILES,
)
from dotfiles_mcp.git_governance_engine import stage_non_destructive_proposal
from dotfiles_mcp.manifest_helpers import (
    _ensure_rule_file_frontmatter,
    _iter_layer_template_dirs,
    _parse_skill_frontmatter,
    _resolve_template_dest_dir,
    _resolve_template_dir,
    _sha256_file,
)


def collect_layer_effective_bindings(
    layer_dir: Path, manifest: dict[str, Any]
) -> list[dict[str, Any]]:
    """Merge manifest surface_bindings with active template.json recommended_surface_bindings."""
    effective, seen_ids = [], set[str]()
    candidates = list(manifest.get("surface_bindings") or [])
    for tpl_name in manifest.get("default_stack_templates", []):
        tpl_dir = _resolve_template_dir(layer_dir, str(tpl_name))
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


def _route_novel_item(
    item_name: str, item_kind: str, layer_records: list[dict[str, Any]], root_headroom_bytes: int
) -> dict[str, Any]:
    """Recommend the optimal target layer and destination for a novel rule or skill."""
    stem = item_name.removesuffix(".md").lower()
    tokens = {t for t in re.split(r"[-_.]", stem) if len(t) >= MIN_ROUTING_KEYWORD_LEN}
    for rec in layer_records:
        lname = str(rec["name"])
        if lname != "root" and (lname in stem or bool(tokens & set(rec["keywords"]))):
            tpls = list(rec["templates"])
            sfx = "AGENTS.md" if item_kind == "rules" else f"skills/{stem}/SKILL.md"
            dest = (
                f"layers/{lname}/templates/{tpls[0]}/{item_kind}/{item_name}"
                if tpls
                else f"layers/{lname}/antigravity/.gemini/config/{sfx}"
            )
            push_cmd = f"./scripts/layer-subtree.sh push {lname} feat/promote-{stem}"
            return {"item": item_name, "kind": item_kind, "target_layer": lname,
                "target_role": rec["layer_role"], "target_destination": dest,
                "subtree_push_command": push_cmd}  # fmt: skip
    root_rec, root_tpls = layer_records[0], list(layer_records[0]["templates"])
    if item_kind == "rules" and root_tpls:
        dest, scope = (
            f"templates/{root_tpls[0]}/rules/{item_name}",
            f"template-pack:root:{root_tpls[0]}",
        )
    elif item_kind == "skills":
        dest, scope = f"antigravity/.gemini/config/skills/{stem}/SKILL.md", "global-skills-root"
    else:
        dest, scope = "antigravity/.gemini/config/AGENTS.md", "global-agents-root"
    return {"item": item_name, "kind": item_kind, "target_layer": "root", "target_scope": scope,
        "target_role": root_rec["layer_role"], "target_destination": dest,
        "root_agents_md_headroom_bytes": root_headroom_bytes}  # fmt: skip


def compare_project_patterns_multilayer(
    repo_dir: Path, mounted_layers: list[dict[str, Any]], *,
    project_rules: list[str], project_skills: list[str],
    target_dirs: list[tuple[str, Path, dict[str, Any]]],
) -> dict[str, Any]:  # fmt: skip
    """Compare consumer project rules/skills across 1..N layers and route promotions."""
    layer_a_skills, layer_b_rules, layer_b_skills = set[str](), set[str](), set[str]()
    layer_records: list[dict[str, Any]] = []
    for lname, ldir, manifest in target_dirs:
        for sf in (ldir / "antigravity/.gemini/config/skills").glob("*/SKILL.md"):
            layer_a_skills.update((_parse_skill_frontmatter(sf, ldir)["name"], sf.parent.name))
        tpl_names: list[str] = []
        for tname, tdir in _iter_layer_template_dirs(ldir):
            tpl_names.append(tname)
            layer_b_rules.update(rf.name for rf in (tdir / "rules").glob("*.md"))
            for sf in (tdir / "skills").glob("*/SKILL.md"):
                layer_b_skills.update((_parse_skill_frontmatter(sf, ldir)["name"], sf.parent.name))
        raw_id = f"{lname}-{manifest.get('layer_id', '')}".lower()
        kw = {t for t in re.split(r"[-_]", raw_id) if len(t) >= MIN_ROUTING_KEYWORD_LEN}
        for b in collect_layer_effective_bindings(ldir, manifest):
            for k in ("scopes", "traits"):
                kw.update(str(v).lower() for v in b.get(k, []) if v != "*")
        layer_records.append({"name": lname, "layer_id": manifest.get("layer_id", lname),
            "layer_role": manifest.get("layer_role", "workstation"),
            "templates": tpl_names, "keywords": kw})  # fmt: skip
    materialized_rules = [r for r in project_rules if MATERIALIZED_RULE_RE.match(r)]
    filtered_rules = [r for r in project_rules if not MATERIALIZED_RULE_RE.match(r)]
    novel_rules = sorted(r for r in filtered_rules if r not in layer_b_rules)
    novel_skills = sorted(s for s in project_skills if s not in (layer_a_skills | layer_b_skills))
    root_ag = repo_dir / "antigravity/.gemini/config/AGENTS.md"
    headroom = max(0, AGENTS_MD_MAX_BYTES - (root_ag.stat().st_size if root_ag.is_file() else 0))
    routing = [
        *(_route_novel_item(r, "rules", layer_records, headroom) for r in novel_rules),
        *(_route_novel_item(s, "skills", layer_records, headroom) for s in novel_skills),
    ]
    primary_id = target_dirs[0][2].get("layer_id") if len(target_dirs) == 1 else "all"
    in_b_rules = sorted(r for r in filtered_rules if r in layer_b_rules)
    in_b_skills = sorted(s for s in project_skills if s in layer_b_skills)
    miss_rules = sorted(r for r in layer_b_rules if r not in filtered_rules)
    miss_skills = sorted(s for s in layer_b_skills if s not in project_skills)
    cand_up = {"novel_rules": novel_rules, "novel_skills": novel_skills}
    miss_b = {"rules": miss_rules, "skills": miss_skills}
    return {"compared_against_layer": primary_id, "promotion_routing": routing,
        "layers_scanned": [r["name"] for r in layer_records],
        "mounted_layers_count": len(mounted_layers),
        "materialized_layer_rules": sorted(materialized_rules),
        "already_in_layer_a_skills": sorted(s for s in project_skills if s in layer_a_skills),
        "already_in_layer_b_templates": {"rules": in_b_rules, "skills": in_b_skills},
        "candidates_for_upward_promotion": cand_up,
        "available_in_layer_b_but_missing_in_project": miss_b}  # fmt: skip


def diff_project_against_layers(repo_dir: Path, project_dir: Path) -> dict[str, Any]:
    """Compare SHA-256 digests between <project_dir>/.agents/ and fork layers/templates."""
    layer_sources: dict[str, list[tuple[str, Path]]] = {}
    agents_dir, proj_resolved = project_dir / ".agents", project_dir.resolve()
    subs = [
        (s.name, s) for s in sorted((repo_dir / "layers").glob("*"))
        if s.is_dir() and not s.name.startswith(".")
    ]  # fmt: skip
    eng_dirs = [("engine", REPO_DIR)] if repo_dir.resolve() != REPO_DIR.resolve() else []
    for lname, ldir in [("root", repo_dir), *subs, *eng_dirs]:
        for tname, tdir in _iter_layer_template_dirs(ldir):
            tag = f"{lname}:{tname}"
            for rf in sorted((tdir / "rules").glob("*.md")):
                layer_sources.setdefault(f"rules/{rf.name}", []).append((tag, rf))
            for sf in sorted((tdir / "skills").glob("*/SKILL.md")):
                layer_sources.setdefault(f"skills/{sf.parent.name}/SKILL.md", []).append((tag, sf))
            for af in (p for p in sorted((tdir / "assets").rglob("*")) if p.is_file()):
                rel_a = str(af.relative_to(tdir / "assets")).replace("\\", "/")
                layer_sources.setdefault(f"assets/{tname}/{rel_a}", []).append((tag, af))
        ag_sk = ldir / "antigravity/.gemini/config/skills"
        for sf in sorted(ag_sk.glob("*/SKILL.md")) if lname != "engine" else ():
            k, v = f"skills/{sf.parent.name}/SKILL.md", (f"layer:{lname}", sf)
            cur = layer_sources.get(k, [])
            layer_sources[k] = [v, *cur] if proj_resolved == repo_dir.resolve() else [*cur, v]

    in_sync, modified_in_project, novel_in_project = [], [], []
    r_files = [(f"rules/{rf.name}", rf) for rf in sorted((agents_dir / "rules").glob("*.md"))]
    s_files = [
        (f"skills/{sf.parent.name}/SKILL.md", sf)
        for sf in sorted((agents_dir / "skills").glob("*/SKILL.md"))
    ]
    a_files = [
        (str(af.relative_to(agents_dir)).replace("\\", "/"), af)
        for af in sorted((agents_dir / "assets").rglob("*")) if af.is_file()
    ]  # fmt: skip
    for rel_key, pfile in [*r_files, *s_files, *a_files]:
        if not pfile.resolve().is_relative_to(proj_resolved):
            raise ValueError(f"Outbound symlink escape denied in project_dir: {rel_key}")
        candidates: list[tuple[str, Path]] = list(layer_sources.get(rel_key, []))
        if m := MATERIALIZED_RULE_RE.match(pfile.name):
            sub_name, rel_ag = m.group(2), "antigravity/.gemini/config/AGENTS.md"
            sub_ag = (repo_dir if sub_name == "root" else repo_dir / "layers" / sub_name) / rel_ag
            if sub_ag.is_file():
                candidates = [(f"layer:{sub_name}", sub_ag)]
        if candidates:
            p_bytes, sync_origin = pfile.read_bytes(), None
            for orig, sp in candidates:
                fm_bytes = _ensure_rule_file_frontmatter(sp, sync_in_place=False).encode("utf-8")
                if p_bytes in (sp.read_bytes(), fm_bytes):
                    sync_origin = orig
                    break
            if sync_origin is not None:
                in_sync.append({"file": rel_key, "source": sync_origin})
            else:
                origin, src_path = candidates[0]
                base_r = REPO_DIR if origin.startswith("engine:") else repo_dir
                rel_t = str(src_path.relative_to(base_r))
                mod_item = {"file": rel_key, "source": origin, "target_path": rel_t}
                modified_in_project.append(mod_item)
        else:
            novel_in_project.append(rel_key)
    return {"project_dir": str(project_dir), "in_sync": in_sync,
        "modified_in_project": modified_in_project,
        "novel_in_project": novel_in_project}  # fmt: skip


def promote_project_asset_to_layer(
    repo_dir: Path, project_dir: Path, *, source_rel_path: str, target_layer: str = "root",
    target_template: str | None = None, upstream_dir: Path | None = None,
    prepare_pr: bool = False, actor_email: str | None = None,
    contributing_org: str | None = None, contributors: str | None = None,
    validation_context: str | None = None, force_overwrite: bool = False, dry_run: bool = False,
) -> dict[str, Any]:  # fmt: skip
    """Promote a rule, skill, doc, or tracker from <project_dir> into a parent layer or template."""
    src_file = (project_dir / source_rel_path.strip().lstrip("/")).resolve()
    if not src_file.is_relative_to(project_dir.resolve()) or not src_file.is_file():
        raise ValueError(f"Invalid or missing project source file: {source_rel_path!r}")
    repo_resolved = upstream_dir.resolve() if upstream_dir is not None else repo_dir.resolve()
    if upstream_dir is not None:
        verify_single_hop_upstream(project_dir.resolve(), repo_resolved, actor_email=actor_email)
    layer_base = (
        repo_resolved
        if target_layer in ("", "root") or upstream_dir is not None
        else (repo_resolved / "layers" / target_layer).resolve()
    )
    if not layer_base.is_relative_to(repo_resolved) or not layer_base.is_dir():
        raise ValueError(f"Target layer directory not found: {target_layer!r}")
    content, target_m = src_file.read_text(encoding="utf-8"), _load_manifest_dict(layer_base)
    if _is_oss_root_manifest(target_m):
        verify_oss_promotion_agnosticism(project_dir.resolve(), content, source_rel_path)

    rel_parts = src_file.relative_to(project_dir.resolve()).parts
    tpl_idx = 2 if len(rel_parts) >= 5 and rel_parts[1] in TEMPLATE_STACK_GROUP_DIRS else 1
    is_tpl_src = (
        len(rel_parts) >= tpl_idx + 3
        and rel_parts[0] == "templates"
        and rel_parts[tpl_idx + 1] in ("rules", "skills", "assets")
    )
    ag_pfx_len = len(AGENTS_ASSETS_PREFIX)
    is_ag_asset = (
        len(rel_parts) >= ag_pfx_len + 2 and rel_parts[:ag_pfx_len] == AGENTS_ASSETS_PREFIX
    )
    is_tracker = len(rel_parts) == 1 and rel_parts[0] in VALID_TRACKER_FILES
    is_gov_dir = len(rel_parts) >= 2 and rel_parts[0] in VALID_DELEGATION_DIRS
    inferred_tpl = rel_parts[2] if is_ag_asset else (rel_parts[tpl_idx] if is_tpl_src else None)
    eff_template, parent_lid = target_template or inferred_tpl, str(target_m.get("layer_id", ""))
    if (
        not eff_template
        and rel_parts[: len(AGENTS_RULES_PREFIX)] == AGENTS_RULES_PREFIX
        and src_file.name != "AGENTS.md"
        and not MATERIALIZED_RULE_RE.match(src_file.name)
        and parent_lid
        and _resolve_template_dir(layer_base, parent_lid) is not None
    ):
        eff_template = parent_lid
    if eff_template and not KEBAB_ID_RE.match(eff_template):
        raise ValueError(f"Invalid target_template {eff_template!r}: must be kebab-case")
    tpl_dest = _resolve_template_dest_dir(layer_base, str(eff_template)) if eff_template else None
    if is_tracker or is_gov_dir:
        dest_file = layer_base / Path(*rel_parts)
    elif is_ag_asset or (is_tpl_src and rel_parts[tpl_idx + 1] == "assets"):
        tail = rel_parts[ag_pfx_len + 1 :] if is_ag_asset else rel_parts[tpl_idx + 2 :]
        base_d = tpl_dest or (layer_base / "templates" / str(eff_template))
        dest_file = base_d / "assets" / Path(*tail)
    elif src_file.name == "SKILL.md":
        lines = content.splitlines()
        if len(lines) > SKILL_MD_MAX_LINES or not lines or lines[0].strip() != "---":
            raise ValueError("Promoted SKILL.md must have YAML frontmatter and <= 500 lines")
        meta = _parse_skill_frontmatter(src_file, project_dir)
        if not KEBAB_ID_RE.match(meta["name"]) or not meta["description"]:
            raise ValueError("Promoted SKILL.md must have kebab-case name and description")
        sub_p = f"skills/{src_file.parent.name}/SKILL.md"
        dest_file = (
            tpl_dest / sub_p if tpl_dest else layer_base / "antigravity/.gemini/config" / sub_p
        )
    elif tpl_dest is not None:
        dest_file = tpl_dest / "rules" / src_file.name
    else:
        dest_file = layer_base / "antigravity/.gemini/config/AGENTS.md"
        if (
            dest_file.is_file()
            and src_file.name != "AGENTS.md"
            and not MATERIALIZED_RULE_RE.match(src_file.name)
        ):
            raise ValueError(
                f"Refusing to overwrite existing AGENTS.md with rule {src_file.name!r}; "
                "specify target_template or promote AGENTS.md / layer-NN-<name>.md"
            )
        if len(content.encode("utf-8")) > AGENTS_MD_MAX_BYTES:
            raise ValueError(
                f"Promoted AGENTS.md size ({len(content.encode('utf-8'))} bytes) "
                f"exceeds {AGENTS_MD_MAX_BYTES}-byte token budget cap"
            )

    eff_layer = "root" if layer_base == repo_resolved and upstream_dir is None else target_layer
    auth_v = verify_layer_operation_authority(
        layer_base, operation="release", actor_email=actor_email, record_blocked=False
    )
    auth_ok, staged_path = bool(auth_v["allowed"]), None
    if (
        not is_tracker
        and not force_overwrite
        and (not auth_ok or (prepare_pr and dest_file.is_file()))
    ):
        stg_kw: dict[str, Any] = {"scope_tag": f"to-{eff_layer}", "file_name": dest_file.name,
            "content": content, "operation": "promote-from-project",
            "actor_email": actor_email or "", "reason_code": "TARGET_PROTECTED_OR_PR_MODE",
            "dry_run": dry_run}  # fmt: skip
        staged_path = str(stage_non_destructive_proposal(project_dir.resolve(), **stg_kw))
        prepare_pr = True
    elif not dry_run:
        dest_file.parent.mkdir(parents=True, exist_ok=True)
        if is_tracker:
            om = _load_manifest_dict(project_dir)
            oid, orole = (
                str(om.get("layer_id", project_dir.name)),
                str(om.get("layer_role", "project")),
            )
            oprec = int(om.get("precedence", ROLE_DEFAULT_PRECEDENCE["service-node"]))
            hdr = f"## Proposed from `{oid}` (`{orole}`, `precedence: {oprec}`)"
            def_hdr = f"# {rel_parts[0].removesuffix('.md')} — {layer_base.name}"
            cur = dest_file.read_text(encoding="utf-8").rstrip() if dest_file.is_file() else def_hdr
            dest_file.write_text(f"{cur}\n\n{hdr}\n\n{content.strip()}\n", encoding="utf-8")
        else:
            dest_file.unlink(missing_ok=True)
            shutil.copy2(src_file, dest_file)
            dest_file.chmod(dest_file.stat().st_mode | OWNER_WRITABLE_MODE_BIT)

    src_rel_str = str(src_file.relative_to(project_dir.resolve()))
    dest_rel_str, sha256_str = str(dest_file.relative_to(repo_resolved)), _sha256_file(src_file)
    push_cmd = (
        f"./scripts/layer-subtree.sh push {eff_layer} feat/promote-{src_file.stem}"
        if eff_layer != "root"
        else None
    )
    result: dict[str, Any] = {"source": src_rel_str, "target_layer": eff_layer,
        "target_template": eff_template, "destination": dest_rel_str, "sha256": sha256_str,
        "subtree_push_command": push_cmd, "staged_proposal": staged_path,
        "dry_run": dry_run}  # fmt: skip
    if prepare_pr or upstream_dir is not None:
        dest_rel_lb = str(dest_file.relative_to(layer_base))
        pr_kw: dict[str, Any] = {"source_rel": src_rel_str, "dest_rel": dest_rel_lb,
            "target_layer": eff_layer, "target_template": eff_template, "sha256": sha256_str,
            "actor_email": actor_email, "contributing_org": contributing_org,
            "contributors": contributors, "validation_context": validation_context}  # fmt: skip
        result["promotion_pr_plan"] = build_upward_promotion_pr_plan(
            project_dir, layer_base, **pr_kw
        )
    return result
