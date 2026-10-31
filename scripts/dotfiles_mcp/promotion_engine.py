"""Multi-layer rule comparison, project diffing, and upward governance promotion engine.

Specification: docs/architecture/04_compaction_surface_and_promotion_engines.md
"""

from __future__ import annotations

import hashlib
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
from dotfiles_mcp.constants import AGENTS_MD_MAX_BYTES, KEBAB_ID_RE, MATERIALIZED_RULE_RE
from dotfiles_mcp.manifest_helpers import _parse_skill_frontmatter


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def collect_layer_effective_bindings(
    layer_dir: Path, manifest: dict[str, Any]
) -> list[dict[str, Any]]:
    """Merge manifest surface_bindings with active template.json recommended_surface_bindings."""
    effective: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for raw_b in manifest.get("surface_bindings") or []:
        if isinstance(raw_b, dict):
            if raw_b.get("binding_id"):
                seen_ids.add(str(raw_b["binding_id"]))
            effective.append(raw_b)
    for tpl_name in manifest.get("default_stack_templates", []):
        meta_file = layer_dir / "templates" / str(tpl_name) / "template.json"
        if not meta_file.is_file():
            continue
        loaded = json.loads(meta_file.read_text(encoding="utf-8"))
        recs = loaded.get("recommended_surface_bindings", []) if isinstance(loaded, dict) else []
        for rec_b in recs:
            if isinstance(rec_b, dict):
                bid = str(rec_b.get("binding_id", ""))
                if not bid or bid not in seen_ids:
                    if bid:
                        seen_ids.add(bid)
                    effective.append(rec_b)
    return effective


def _route_novel_item(
    item_name: str, item_kind: str, layer_records: list[dict[str, Any]], root_headroom_bytes: int
) -> dict[str, Any]:
    """Recommend the optimal target layer and destination for a novel rule or skill."""
    stem = item_name.removesuffix(".md").lower()
    tokens = {t for t in re.split(r"[-_.]", stem) if len(t) >= 3}
    for rec in layer_records:
        lname = str(rec["name"])
        if lname != "root" and (lname in stem or bool(tokens & set(rec["keywords"]))):
            tpls = list(rec["templates"])
            suffix = "AGENTS.md" if item_kind == "rules" else f"skills/{stem}/SKILL.md"
            dest = (
                f"layers/{lname}/templates/{tpls[0]}/{item_kind}/{item_name}"
                if tpls
                else f"layers/{lname}/antigravity/.gemini/config/{suffix}"
            )
            cmd = f"./scripts/layer-subtree.sh push {lname} feat/promote-{stem}"
            return {
                "item": item_name,
                "kind": item_kind,
                "target_layer": lname,
                "target_role": rec["layer_role"],
                "target_destination": dest,
                "subtree_push_command": cmd,
            }
    root_rec = layer_records[0]
    root_tpls = list(root_rec["templates"])
    if item_kind == "rules" and root_tpls:
        dest = f"templates/{root_tpls[0]}/rules/{item_name}"
        scope = f"template-pack:root:{root_tpls[0]}"
    elif item_kind == "skills":
        dest, scope = f"antigravity/.gemini/config/skills/{stem}/SKILL.md", "global-skills-root"
    else:
        dest, scope = "antigravity/.gemini/config/AGENTS.md", "global-agents-root"
    return {
        "item": item_name,
        "kind": item_kind,
        "target_layer": "root",
        "target_role": root_rec["layer_role"],
        "target_scope": scope,
        "target_destination": dest,
        "root_agents_md_headroom_bytes": root_headroom_bytes,
    }


def compare_project_patterns_multilayer(
    repo_dir: Path,
    mounted_layers: list[dict[str, Any]],
    *,
    project_rules: list[str],
    project_skills: list[str],
    target_dirs: list[tuple[str, Path, dict[str, Any]]],
) -> dict[str, Any]:
    """Compare consumer project rules/skills across 1..N layers and route promotions."""
    layer_a_skills: set[str] = set()
    layer_b_rules: set[str] = set()
    layer_b_skills: set[str] = set()
    layer_records: list[dict[str, Any]] = []
    for lname, ldir, manifest in target_dirs:
        skills_root = ldir / "antigravity/.gemini/config/skills"
        if skills_root.is_dir():
            for sf in skills_root.glob("*/SKILL.md"):
                layer_a_skills.update((_parse_skill_frontmatter(sf, ldir)["name"], sf.parent.name))
        tpl_root, tpl_names = ldir / "templates", []
        if tpl_root.is_dir():
            for tdir in (d for d in sorted(tpl_root.iterdir()) if d.is_dir() and d.name[:1] != "."):
                tpl_names.append(tdir.name)
                layer_b_rules.update(rf.name for rf in (tdir / "rules").glob("*.md"))
                for sf in (tdir / "skills").glob("*/SKILL.md"):
                    layer_b_skills.update(
                        (_parse_skill_frontmatter(sf, ldir)["name"], sf.parent.name)
                    )
        raw_id = f"{lname}-{manifest.get('layer_id', '')}".lower()
        kw = {t for t in re.split(r"[-_]", raw_id) if len(t) >= 3}
        for b in collect_layer_effective_bindings(ldir, manifest):
            for k in ("scopes", "traits"):
                kw.update(str(v).lower() for v in b.get(k, []) if v != "*")
        layer_records.append(
            {
                "name": lname,
                "layer_id": manifest.get("layer_id", lname),
                "layer_role": manifest.get("layer_role", "workstation"),
                "templates": tpl_names,
                "keywords": kw,
            }
        )
    materialized_rules = [r for r in project_rules if MATERIALIZED_RULE_RE.match(r)]
    filtered_proj_rules = [r for r in project_rules if not MATERIALIZED_RULE_RE.match(r)]
    novel_rules = sorted(r for r in filtered_proj_rules if r not in layer_b_rules)
    novel_skills = sorted(
        s for s in project_skills if s not in layer_a_skills and s not in layer_b_skills
    )
    root_agents = repo_dir / "antigravity/.gemini/config/AGENTS.md"
    agents_sz = root_agents.stat().st_size if root_agents.is_file() else 0
    headroom = max(0, AGENTS_MD_MAX_BYTES - agents_sz)
    routing = [
        *(_route_novel_item(r, "rules", layer_records, headroom) for r in novel_rules),
        *(_route_novel_item(s, "skills", layer_records, headroom) for s in novel_skills),
    ]
    primary_id = target_dirs[0][2].get("layer_id") if len(target_dirs) == 1 else "all"
    return {
        "compared_against_layer": primary_id,
        "layers_scanned": [r["name"] for r in layer_records],
        "mounted_layers_count": len(mounted_layers),
        "materialized_layer_rules": sorted(materialized_rules),
        "already_in_layer_a_skills": sorted(s for s in project_skills if s in layer_a_skills),
        "already_in_layer_b_templates": {
            "rules": sorted(r for r in filtered_proj_rules if r in layer_b_rules),
            "skills": sorted(s for s in project_skills if s in layer_b_skills),
        },
        "candidates_for_upward_promotion": {
            "novel_rules": novel_rules,
            "novel_skills": novel_skills,
        },
        "promotion_routing": routing,
        "available_in_layer_b_but_missing_in_project": {
            "rules": sorted(r for r in layer_b_rules if r not in filtered_proj_rules),
            "skills": sorted(s for s in layer_b_skills if s not in project_skills),
        },
    }


def diff_project_against_layers(repo_dir: Path, project_dir: Path) -> dict[str, Any]:
    """Compare SHA-256 digests between <project_dir>/.agents/ and fork layers/templates."""
    layer_sources: dict[str, tuple[str, Path]] = {}
    search_layers: list[tuple[str, Path]] = [("root", repo_dir)]
    layers_dir = repo_dir / "layers"
    if layers_dir.is_dir():
        search_layers.extend(
            (s.name, s) for s in sorted(layers_dir.iterdir()) if s.is_dir() and s.name[:1] != "."
        )
    for lname, ldir in search_layers:
        tpl_root = ldir / "templates"
        if not tpl_root.is_dir():
            continue
        for tdir in (d for d in sorted(tpl_root.iterdir()) if d.is_dir() and d.name[:1] != "."):
            tag = f"{lname}:{tdir.name}"
            for rf in sorted((tdir / "rules").glob("*.md")):
                layer_sources.setdefault(f"rules/{rf.name}", (tag, rf))
            for sf in sorted((tdir / "skills").glob("*/SKILL.md")):
                layer_sources.setdefault(f"skills/{sf.parent.name}/SKILL.md", (tag, sf))
            assets_dir = tdir / "assets"
            for af in sorted(assets_dir.rglob("*")):
                if af.is_file():
                    rel_a = str(af.relative_to(assets_dir)).replace("\\", "/")
                    layer_sources.setdefault(f"assets/{tdir.name}/{rel_a}", (tag, af))

    in_sync: list[dict[str, str]] = []
    modified_in_project: list[dict[str, str]] = []
    novel_in_project: list[str] = []
    agents_dir = project_dir / ".agents"
    proj_files: list[tuple[str, Path]] = []
    if (agents_dir / "rules").is_dir():
        proj_files.extend(
            (f"rules/{rf.name}", rf) for rf in sorted((agents_dir / "rules").glob("*.md"))
        )
    if (agents_dir / "skills").is_dir():
        proj_files.extend(
            (f"skills/{sf.parent.name}/SKILL.md", sf)
            for sf in sorted((agents_dir / "skills").glob("*/SKILL.md"))
        )
    if (agents_dir / "assets").is_dir():
        proj_files.extend(
            (str(af.relative_to(agents_dir)).replace("\\", "/"), af)
            for af in sorted((agents_dir / "assets").rglob("*"))
            if af.is_file()
        )
    proj_resolved = project_dir.resolve()
    for rel_key, pfile in proj_files:
        if not pfile.resolve().is_relative_to(proj_resolved):
            raise ValueError(f"Outbound symlink escape denied in project_dir: {rel_key}")
        matched_origin: tuple[str, Path] | None = layer_sources.get(rel_key)
        m = MATERIALIZED_RULE_RE.match(pfile.name)
        if m:
            sub_name = m.group(2)
            rel_ag = "antigravity/.gemini/config/AGENTS.md"
            sub_ag = (
                repo_dir / rel_ag if sub_name == "root" else repo_dir / "layers" / sub_name / rel_ag
            )
            if sub_ag.is_file():
                matched_origin = (f"layer:{sub_name}", sub_ag)
        if matched_origin is not None:
            origin, src_path = matched_origin
            if _sha256_file(pfile) == _sha256_file(src_path):
                in_sync.append({"file": rel_key, "source": origin})
            else:
                t_rel = str(src_path.relative_to(repo_dir))
                modified_in_project.append(
                    {"file": rel_key, "source": origin, "target_path": t_rel}
                )
        else:
            novel_in_project.append(rel_key)
    return {
        "project_dir": str(project_dir),
        "in_sync": in_sync,
        "modified_in_project": modified_in_project,
        "novel_in_project": novel_in_project,
    }


def promote_project_asset_to_layer(
    repo_dir: Path,
    project_dir: Path,
    *,
    source_rel_path: str,
    target_layer: str = "root",
    target_template: str | None = None,
    upstream_dir: Path | None = None,
    prepare_pr: bool = False,
    actor_email: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Promote a rule, skill, or asset from <project_dir> into a fork layer or template pack."""
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

    content = src_file.read_text(encoding="utf-8")
    if _is_oss_root_manifest(_load_manifest_dict(layer_base)):
        verify_oss_promotion_agnosticism(project_dir.resolve(), content, source_rel_path)

    rel_parts = src_file.relative_to(project_dir.resolve()).parts
    is_tpl_src = (
        len(rel_parts) >= 4
        and rel_parts[0] == "templates"
        and rel_parts[2] in ("rules", "skills", "assets")
    )
    inferred_tpl = (
        rel_parts[2]
        if len(rel_parts) >= 4 and rel_parts[:2] == (".agents", "assets")
        else (rel_parts[1] if is_tpl_src else None)
    )
    eff_template = target_template or inferred_tpl
    if eff_template and not KEBAB_ID_RE.match(eff_template):
        raise ValueError(f"Invalid target_template {eff_template!r}: must be kebab-case")
    if len(rel_parts) >= 4 and (
        rel_parts[:2] == (".agents", "assets") or (is_tpl_src and rel_parts[2] == "assets")
    ):
        dest_file = layer_base / "templates" / str(eff_template) / "assets" / Path(*rel_parts[3:])
    elif src_file.name == "SKILL.md":
        lines = content.splitlines()
        if len(lines) > 500 or not lines or lines[0].strip() != "---":
            raise ValueError("Promoted SKILL.md must have YAML frontmatter and <= 500 lines")
        meta = _parse_skill_frontmatter(src_file, project_dir)
        if not KEBAB_ID_RE.match(meta["name"]) or not meta["description"]:
            raise ValueError("Promoted SKILL.md must have kebab-case name and description")
        dest_file = (
            layer_base / "templates" / eff_template / "skills" / src_file.parent.name / "SKILL.md"
            if eff_template
            else layer_base
            / "antigravity/.gemini/config/skills"
            / src_file.parent.name
            / "SKILL.md"
        )
    elif eff_template:
        dest_file = layer_base / "templates" / eff_template / "rules" / src_file.name
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

    if not dry_run:
        dest_file.parent.mkdir(parents=True, exist_ok=True)
        dest_file.unlink(missing_ok=True)
        shutil.copy2(src_file, dest_file)
        dest_file.chmod(0o644)

    eff_layer = "root" if layer_base == repo_resolved and upstream_dir is None else target_layer
    src_rel_str = str(src_file.relative_to(project_dir.resolve()))
    dest_rel_str = str(dest_file.relative_to(repo_resolved))
    sha256_str = _sha256_file(src_file)
    result: dict[str, Any] = {
        "source": src_rel_str,
        "target_layer": eff_layer,
        "target_template": eff_template,
        "destination": dest_rel_str,
        "sha256": sha256_str,
        "subtree_push_command": (
            f"./scripts/layer-subtree.sh push {eff_layer} feat/promote-{src_file.stem}"
            if eff_layer != "root"
            else None
        ),
        "dry_run": dry_run,
    }
    if prepare_pr or upstream_dir is not None:
        result["promotion_pr_plan"] = build_upward_promotion_pr_plan(
            project_dir,
            layer_base,
            source_rel=src_rel_str,
            dest_rel=str(dest_file.relative_to(layer_base)),
            target_layer=eff_layer,
            target_template=eff_template,
            sha256=sha256_str,
            actor_email=actor_email,
        )
    return result


def inspect_layer_horizon(
    repo_dir: Path,
    workspace_dir: Path,
    *,
    parent_dir: Path | None = None,
    actor_email: str | None = None,
) -> dict[str, Any]:
    """Inspect 1-hop downward propagation & quiet upward promotion candidates for a workspace."""
    ws, up, oss = workspace_dir.resolve(), (parent_dir or repo_dir).resolve(), repo_dir.resolve()
    ws_m, up_m = _load_manifest_dict(ws), _load_manifest_dict(up)
    oss_vf, up_vf, ws_vf = oss / "VERSION", up / "VERSION", ws / "VERSION"
    oss_ver = oss_vf.read_text(encoding="utf-8").strip() if oss_vf.is_file() else None
    up_ver = up_vf.read_text(encoding="utf-8").strip() if up_vf.is_file() else None
    ws_ver = ws_vf.read_text(encoding="utf-8").strip() if ws_vf.is_file() else None
    is_oss = _is_oss_root_manifest(up_m)
    auth_v = verify_layer_operation_authority(ws, operation="release", actor_email=actor_email)
    up_auth_v = verify_layer_operation_authority(up, operation="release", actor_email=actor_email)
    ws_tpls = [d.name for d in sorted((ws / "templates").glob("*")) if d.is_dir()]
    cand_tpls = [*(str(x) for x in ws_m.get("default_stack_templates", [])), *ws_tpls]
    shared = [
        t
        for t in dict.fromkeys(cand_tpls)
        if (up / "templates" / t).is_dir() and (ws / "templates" / t).is_dir()
    ]
    drifts: list[dict[str, Any]] = []
    for tpl in shared:
        for ws_rf in sorted((ws / "templates" / tpl / "rules").glob("*.md")):
            up_rf = up / "templates" / tpl / "rules" / ws_rf.name
            if not up_rf.is_file() or _sha256_file(ws_rf) != _sha256_file(up_rf):
                rel_src = f"templates/{tpl}/rules/{ws_rf.name}"
                up_newer = up_rf.is_file() and up_rf.stat().st_mtime_ns > ws_rf.stat().st_mtime_ns
                oss_ok = True
                try:
                    verify_oss_promotion_agnosticism(ws, ws_rf.read_text(encoding="utf-8"), rel_src)
                except ValueError:
                    oss_ok = False
                cmd = (
                    f"./scripts/layer-config.sh promote-from-project {ws} "
                    f"--source {rel_src} --to-template {tpl} --upstream-dir {up} --prepare-pr"
                )
                drifts.append(
                    {
                        "template": tpl,
                        "rule_file": rel_src,
                        "drift_direction": "upstream_newer" if up_newer else "workspace_newer",
                        "oss_agnostic": oss_ok,
                        "promote_command": cmd,
                    }
                )
    local_diff = diff_project_against_layers(ws, ws)
    sync_sfx = f" --parent-dir {up}" if parent_dir is not None else ""
    up_drifts = [d for d in drifts if d["drift_direction"] == "workspace_newer"]
    return {
        "workspace_dir": str(ws),
        "layer_id": str(ws_m.get("layer_id", ws.name)),
        "layer_role": str(ws_m.get("layer_role", "project")),
        "actor_is_layer_owner": bool(auth_v["allowed"]),
        "actor_is_upstream_owner": bool(up_auth_v["allowed"]),
        "immediate_upstream_dir": str(up),
        "immediate_upstream_id": str(up_m.get("layer_id", up.name)),
        "immediate_upstream_role": str(up_m.get("layer_role", "unknown")),
        "is_oss_community_horizon": is_oss,
        "oss_root_version": oss_ver,
        "upstream_version": up_ver,
        "workspace_version": ws_ver,
        "downward_sync_needed": any(d["drift_direction"] == "upstream_newer" for d in drifts),
        "downward_sync_command": f"./scripts/layer-config.sh sync-layer {ws}{sync_sfx}",
        "shared_template_drifts": drifts,
        "upward_promotion_suggestions": (
            [d for d in up_drifts if d["oss_agnostic"]]
            if is_oss
            else [
                *(d["promote_command"] for d in up_drifts),
                *(
                    f"./scripts/layer-config.sh promote-from-project {ws} "
                    f"--source .agents/{rel} --upstream-dir {up} --prepare-pr"
                    for rel in local_diff["novel_in_project"]
                ),
            ]
        ),
    }
