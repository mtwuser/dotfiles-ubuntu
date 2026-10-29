"""Multi-layer rule comparison, project diffing, and upward governance promotion engine."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Any

from dotfiles_mcp.constants import AGENTS_MD_MAX_BYTES
from dotfiles_mcp.fork_configurator import KEBAB_ID_RE
from dotfiles_mcp.manifest_helpers import _parse_skill_frontmatter

MATERIALIZED_RULE_RE = re.compile(r"^layer-(\d{2})-([a-z0-9-]+)\.md$")


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def collect_layer_effective_bindings(
    layer_dir: Path,
    manifest: dict[str, Any],
) -> list[dict[str, Any]]:
    """Merge manifest surface_bindings with active template.json recommended_surface_bindings."""
    effective: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for raw_b in manifest.get("surface_bindings") or []:
        if isinstance(raw_b, dict):
            bid = str(raw_b.get("binding_id", ""))
            if bid:
                seen_ids.add(bid)
            effective.append(raw_b)

    for tpl_name in manifest.get("default_stack_templates", []):
        meta_file = layer_dir / "templates" / str(tpl_name) / "template.json"
        if not meta_file.is_file():
            continue
        loaded = json.loads(meta_file.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            continue
        for rec_b in loaded.get("recommended_surface_bindings", []):
            if isinstance(rec_b, dict):
                bid = str(rec_b.get("binding_id", ""))
                if not bid or bid not in seen_ids:
                    if bid:
                        seen_ids.add(bid)
                    effective.append(rec_b)
    return effective


def _route_novel_item(
    item_name: str,
    item_kind: str,
    layer_records: list[dict[str, Any]],
    root_headroom_bytes: int,
) -> dict[str, Any]:
    """Recommend the optimal target layer and destination for a novel rule or skill."""
    stem = item_name.removesuffix(".md").lower()
    tokens = {t for t in re.split(r"[-_.]", stem) if len(t) >= 3}

    for rec in layer_records:
        lname = str(rec["name"])
        if lname == "root":
            continue
        keywords: set[str] = set(rec["keywords"])
        if lname in stem or bool(tokens & keywords):
            tpls = list(rec["templates"])
            dest = (
                f"layers/{lname}/templates/{tpls[0]}/{item_kind}/{item_name}"
                if tpls
                else f"layers/{lname}/antigravity/.gemini/config/"
                + ("AGENTS.md" if item_kind == "rules" else f"skills/{stem}/SKILL.md")
            )
            return {
                "item": item_name,
                "kind": item_kind,
                "target_layer": lname,
                "target_role": rec["layer_role"],
                "target_destination": dest,
                "subtree_push_command": (
                    f"./scripts/layer-subtree.sh push {lname} feat/promote-{stem}"
                ),
            }

    root_rec = layer_records[0]
    root_tpls = list(root_rec["templates"])
    if item_kind == "rules" and root_tpls:
        dest = f"templates/{root_tpls[0]}/rules/{item_name}"
        target_scope = f"template-pack:root:{root_tpls[0]}"
    elif item_kind == "skills":
        dest = f"antigravity/.gemini/config/skills/{stem}/SKILL.md"
        target_scope = "global-skills-root"
    else:
        dest = "antigravity/.gemini/config/AGENTS.md"
        target_scope = "global-agents-root"
    return {
        "item": item_name,
        "kind": item_kind,
        "target_layer": "root",
        "target_role": root_rec["layer_role"],
        "target_scope": target_scope,
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
                layer_a_skills.add(_parse_skill_frontmatter(sf, ldir)["name"])
                layer_a_skills.add(sf.parent.name)
        tpl_root = ldir / "templates"
        tpl_names: list[str] = []
        if tpl_root.is_dir():
            for tdir in sorted(tpl_root.iterdir()):
                if not tdir.is_dir() or tdir.name.startswith("."):
                    continue
                tpl_names.append(tdir.name)
                for rf in (tdir / "rules").glob("*.md"):
                    layer_b_rules.add(rf.name)
                for sf in (tdir / "skills").glob("*/SKILL.md"):
                    layer_b_skills.add(_parse_skill_frontmatter(sf, ldir)["name"])
                    layer_b_skills.add(sf.parent.name)

        kw: set[str] = {
            t
            for t in re.split(r"[-_]", f"{lname}-{manifest.get('layer_id', '')}".lower())
            if len(t) >= 3
        }
        for b in collect_layer_effective_bindings(ldir, manifest):
            for sc in b.get("scopes", []):
                if sc != "*":
                    kw.add(str(sc).lower())
            for tr in b.get("traits", []):
                if tr != "*":
                    kw.add(str(tr).lower())
        layer_records.append(
            {
                "name": lname,
                "layer_id": manifest.get("layer_id", lname),
                "layer_role": manifest.get("layer_role", "workstation"),
                "templates": tpl_names,
                "keywords": kw,
            }
        )

    materialized_rules: list[str] = []
    filtered_proj_rules: list[str] = []
    for r in project_rules:
        if MATERIALIZED_RULE_RE.match(r):
            materialized_rules.append(r)
        else:
            filtered_proj_rules.append(r)

    novel_rules = sorted(r for r in filtered_proj_rules if r not in layer_b_rules)
    novel_skills = sorted(
        s for s in project_skills if s not in layer_a_skills and s not in layer_b_skills
    )
    root_agents = repo_dir / "antigravity/.gemini/config/AGENTS.md"
    agents_bytes = root_agents.stat().st_size if root_agents.is_file() else 0
    headroom = max(0, AGENTS_MD_MAX_BYTES - agents_bytes)

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


def diff_project_against_layers(
    repo_dir: Path,
    project_dir: Path,
) -> dict[str, Any]:
    """Compare SHA-256 digests between <project_dir>/.agents/ and fork layers/templates."""
    layer_sources: dict[str, tuple[str, Path]] = {}
    search_layers: list[tuple[str, Path]] = [("root", repo_dir)]
    layers_dir = repo_dir / "layers"
    if layers_dir.is_dir():
        for sub in sorted(layers_dir.iterdir()):
            if sub.is_dir() and not sub.name.startswith("."):
                search_layers.append((sub.name, sub))

    for lname, ldir in search_layers:
        tpl_root = ldir / "templates"
        if tpl_root.is_dir():
            for tdir in sorted(tpl_root.iterdir()):
                if not tdir.is_dir() or tdir.name.startswith("."):
                    continue
                for rf in sorted((tdir / "rules").glob("*.md")):
                    layer_sources.setdefault(f"rules/{rf.name}", (f"{lname}:{tdir.name}", rf))
                for sf in sorted((tdir / "skills").glob("*/SKILL.md")):
                    layer_sources.setdefault(
                        f"skills/{sf.parent.name}/SKILL.md", (f"{lname}:{tdir.name}", sf)
                    )

    in_sync: list[dict[str, str]] = []
    modified_in_project: list[dict[str, str]] = []
    novel_in_project: list[str] = []

    agents_dir = project_dir / ".agents"
    proj_files: list[tuple[str, Path]] = []
    if (agents_dir / "rules").is_dir():
        for rf in sorted((agents_dir / "rules").glob("*.md")):
            proj_files.append((f"rules/{rf.name}", rf))
    if (agents_dir / "skills").is_dir():
        for sf in sorted((agents_dir / "skills").glob("*/SKILL.md")):
            proj_files.append((f"skills/{sf.parent.name}/SKILL.md", sf))

    for rel_key, pfile in proj_files:
        m = MATERIALIZED_RULE_RE.match(pfile.name)
        if m:
            sub_name = m.group(2)
            sub_agents = repo_dir / "layers" / sub_name / "antigravity/.gemini/config/AGENTS.md"
            if sub_agents.is_file():
                if _sha256_file(pfile) == _sha256_file(sub_agents):
                    in_sync.append({"file": rel_key, "source": f"layer:{sub_name}"})
                else:
                    modified_in_project.append(
                        {
                            "file": rel_key,
                            "source": f"layer:{sub_name}",
                            "target_path": str(sub_agents.relative_to(repo_dir)),
                        }
                    )
                continue
        if rel_key in layer_sources:
            origin, src_path = layer_sources[rel_key]
            if _sha256_file(pfile) == _sha256_file(src_path):
                in_sync.append({"file": rel_key, "source": origin})
            else:
                modified_in_project.append(
                    {
                        "file": rel_key,
                        "source": origin,
                        "target_path": str(src_path.relative_to(repo_dir)),
                    }
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
    dry_run: bool = False,
) -> dict[str, Any]:
    """Promote a rule, skill, or asset from <project_dir> into a fork layer or template pack."""
    src_file = (project_dir / source_rel_path.strip().lstrip("/")).resolve()
    if not src_file.is_relative_to(project_dir.resolve()) or not src_file.is_file():
        raise ValueError(f"Invalid or missing project source file: {source_rel_path!r}")

    layer_base = (
        repo_dir if target_layer in ("", "root") else (repo_dir / "layers" / target_layer).resolve()
    )
    if not layer_base.is_relative_to(repo_dir.resolve()) or not layer_base.is_dir():
        raise ValueError(f"Target layer directory not found: {target_layer!r}")

    content = src_file.read_text(encoding="utf-8")
    if src_file.name == "SKILL.md":
        lines = content.splitlines()
        if len(lines) > 500 or not lines or lines[0].strip() != "---":
            raise ValueError("Promoted SKILL.md must have YAML frontmatter and <= 500 lines")
        meta = _parse_skill_frontmatter(src_file, project_dir)
        if not KEBAB_ID_RE.match(meta["name"]) or not meta["description"]:
            raise ValueError("Promoted SKILL.md must have kebab-case name and description")
        dest_file = (
            layer_base
            / "templates"
            / target_template
            / "skills"
            / src_file.parent.name
            / "SKILL.md"
            if target_template
            else layer_base
            / "antigravity/.gemini/config/skills"
            / src_file.parent.name
            / "SKILL.md"
        )
    elif target_template:
        dest_file = layer_base / "templates" / target_template / "rules" / src_file.name
    else:
        dest_file = layer_base / "antigravity/.gemini/config/AGENTS.md"
        if len(content.encode("utf-8")) > AGENTS_MD_MAX_BYTES:
            raise ValueError(
                f"Promoted AGENTS.md size ({len(content.encode('utf-8'))} bytes) "
                f"exceeds {AGENTS_MD_MAX_BYTES}-byte token budget cap"
            )

    if not dry_run:
        dest_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_file, dest_file)

    eff_layer = "root" if layer_base == repo_dir else target_layer
    return {
        "source": str(src_file.relative_to(project_dir.resolve())),
        "target_layer": eff_layer,
        "target_template": target_template,
        "destination": str(dest_file.relative_to(repo_dir.resolve())),
        "sha256": _sha256_file(src_file),
        "subtree_push_command": (
            f"./scripts/layer-subtree.sh push {eff_layer} feat/promote-{src_file.stem}"
            if eff_layer != "root"
            else None
        ),
        "dry_run": dry_run,
    }
