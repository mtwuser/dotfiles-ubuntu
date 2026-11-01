"""Fork parameterization, polymorphic template scaffolding, and static project projection.

Specification: docs/architecture/04_compaction_surface_and_promotion_engines.md
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from dotfiles_mcp.constants import (
    KEBAB_ID_RE,
    OWNER_WRITABLE_MODE_BIT,
    ROLE_DEFAULT_PRECEDENCE,
    TEMPLATE_STACK_GROUP_DIRS,
    VALID_LAYER_ROLES,
    VALID_TEMPLATE_KINDS,
)
from dotfiles_mcp.manifest_helpers import (
    _ensure_rule_file_frontmatter,
    _iter_layer_template_dirs,
    _merge_unique_strings,
    _parse_skill_frontmatter,
    _render_lineage_markdown,
    _resolve_template_dest_dir,
    _resolve_template_dir,
)
from dotfiles_mcp.promotion_engine import collect_layer_effective_bindings


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
    return dict(
        template_name=tpl_dir.name,
        source_layer=source_layer,
        kind=str(meta.get("kind", "stack-starter")),
        stack_group=str(meta.get("stack_group", parent_grp)),
        target_role=str(meta.get("target_role", "squad")),
        description=str(meta.get("description", f"Template pack {tpl_dir.name}")),
        rules=rules,
        skills=skills,
        governance_files=gov,
        assets=assets,
        recommended_surface_bindings=list(meta.get("recommended_surface_bindings", [])),
    )


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


def configure_fork_manifest(
    repo_dir: Path,
    *,
    layer_id: str,
    layer_role: str = "squad",
    precedence: int | None = None,
    description: str | None = None,
    upstream_url: str | None = None,
    upstream_id: str | None = None,
    upstream_branch: str | None = None,
    prune_default_templates: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Parameterize system/mcp-layer.json (v1.2) for a fork."""
    if not KEBAB_ID_RE.match(layer_id):
        raise ValueError(f"Invalid layer_id {layer_id!r}: must be kebab-case")
    if layer_role not in VALID_LAYER_ROLES:
        raise ValueError(f"Invalid layer_role {layer_role!r}: must be one of {VALID_LAYER_ROLES}")
    eff_precedence = precedence if precedence is not None else ROLE_DEFAULT_PRECEDENCE[layer_role]
    if eff_precedence < 0 or eff_precedence > 100:
        raise ValueError(f"Invalid precedence {eff_precedence}: must be between 0 and 100")

    manifest_path = repo_dir / "system" / "mcp-layer.json"
    manifest: dict[str, Any] = dict(
        schema_version="1.2",
        layer_id=layer_id,
        layer_role=layer_role,
        precedence=eff_precedence,
        description=description or f"Configured {layer_role} layer ({layer_id})",
        upstream_layer=dict(
            layer_id="mtwuser/dotfiles-ubuntu",
            repository="https://github.com/mtwuser/dotfiles-ubuntu.git",
            branch="master",
        ),
        mounted_layers_dir="layers",
        mounted_layers=[],
        default_stack_templates=discover_layer_template_names(repo_dir),
        baseline_guardrails=[],
        surface_bindings=[],
        environments={},
        federated_mcps=[],
    )
    if manifest_path.is_file():
        loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            manifest.update(loaded)

    manifest.update(
        schema_version="1.2",
        layer_id=layer_id,
        layer_role=layer_role,
        precedence=eff_precedence,
    )
    if description is not None:
        manifest["description"] = description

    upstream = dict(manifest.get("upstream_layer", {}))
    if upstream_url is not None:
        upstream["repository"] = upstream_url
    if upstream_id is not None:
        upstream["layer_id"] = upstream_id
    if upstream_branch is not None:
        upstream["branch"] = upstream_branch
    manifest["upstream_layer"] = upstream

    if prune_default_templates:
        pruned = {"agile-task-branch", "fastapi-hexagonal", "human-core", "technical-base"}
        manifest["default_stack_templates"] = [
            t for t in manifest.get("default_stack_templates", []) if t not in pruned
        ]
        kept_bindings: list[dict[str, Any]] = []
        for b in manifest.get("surface_bindings", []):
            if not isinstance(b, dict):
                continue
            refs = [*b.get("rule_files", []), *b.get("canonical_templates", [])]
            if not any("fastapi-hexagonal/" in str(r) for r in refs):
                kept_bindings.append(b)
        manifest["surface_bindings"] = kept_bindings

    if not dry_run:
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def scaffold_template_pack(
    repo_dir: Path,
    *,
    template_name: str,
    kind: str = "stack-starter",
    description: str | None = None,
    register_binding: bool = False,
    rule_filename: str | None = None,
    scopes: list[str] | None = None,
    planes: list[str] | None = None,
    traits: list[str] | None = None,
    globs: list[str] | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Scaffold a polymorphic template pack under templates/<template_name>/."""
    if not KEBAB_ID_RE.match(template_name):
        raise ValueError(f"Invalid template_name {template_name!r}: must be kebab-case")
    if kind not in VALID_TEMPLATE_KINDS:
        raise ValueError(f"Invalid template kind {kind!r}: must be one of {VALID_TEMPLATE_KINDS}")
    effective_rule = rule_filename or "policy.md"
    if not effective_rule.endswith(".md") or "/" in effective_rule or ".." in effective_rule:
        raise ValueError(f"Invalid rule_filename {effective_rule!r}: must be a simple .md filename")

    if _resolve_template_dir(repo_dir, template_name) is not None:
        raise ValueError(f"Template directory already exists: templates/{template_name}")
    tpl_dir = _resolve_template_dest_dir(repo_dir, template_name, kind=kind)
    rel_tpl = str(tpl_dir.relative_to(repo_dir)).replace("\\", "/")
    is_tech = kind in ("stack-starter", "tech-stack")

    desc = description or f"{template_name} ({kind}) governance and template pack"
    mode = "authoritative" if kind == "domain-policy-pack" else "transversal"
    default_res = "L2" if mode == "authoritative" else "L1"
    binding_entry: dict[str, Any] = {
        "binding_id": f"{template_name}-surface-binding",
        "description": desc,
        "mode": mode,
        "target_globs": globs or ["*"],
        "architectural_planes": planes or ["*"],
        "scopes": scopes or ["*"],
        "traits": traits or ["*"],
        "default_resolution": default_res,
        "invariants": [f"Enforce {template_name} ({kind}) rules and canonical assets"],
        "rule_files": [f"{rel_tpl}/rules/{effective_rule}"],
        "canonical_templates": ([f"{rel_tpl}/assets/canonical_snippet.md"] if not is_tech else []),
    }
    tpl_manifest = {
        "schema_version": "1.0",
        "template_id": template_name,
        "kind": kind,
        "target_role": "domain-policy" if kind == "domain-policy-pack" else "squad",
        "description": desc,
        "recommended_surface_bindings": [binding_entry],
    }
    files_to_write: dict[str, str] = {
        f"{rel_tpl}/template.json": json.dumps(tpl_manifest, indent=2) + "\n",
        f"{rel_tpl}/rules/{effective_rule}": (
            f"---\ntrigger: always_on\n"
            f'description: "Governance rules and invariants for {template_name} ({kind})."\n'
            f"---\n\n# {template_name} Governance Rules ({kind})\n\n## Scope & Surface Target\n"
            f"- **Template Pack**: `{rel_tpl}/` (`{kind}`).\n\n"
            f"## Normative Invariants\n"
            f'> *"Enforce {template_name} invariants consistently across matching surfaces"*\n\n'
            f"- Follow the canonical patterns defined in `{rel_tpl}/`.\n\n"
            f"## Verification & Sign-Off Gates\n"
            f"- [ ] Verify zero drift via `./scripts/layer-config.sh diff-project`.\n"
        ),
        f"{rel_tpl}/skills/{template_name}-guide/SKILL.md": (
            f"---\nname: {template_name}-guide\n"
            f'description: "Procedural guide for applying {template_name} ({kind}) rules."\n'
            f"---\n\n# {template_name} Guide\n\n"
            f"1. Review `{rel_tpl}/rules/{effective_rule}`.\n"
            f"2. Verify invariants via `./scripts/layer-config.sh diff-project` "
            f"and promote via `promote-from-project --create-pr`.\n"
        ),
    }
    if is_tech or kind == "project-overlay":
        files_to_write[f"{rel_tpl}/governance/WORKTASK.md"] = (
            f"# Active Work Tasks — {template_name}\n\n- [ ] Initial setup\n"
        )
    if is_tech:
        files_to_write[f"{rel_tpl}/governance/Makefile"] = (
            ".PHONY: install format lint test test-cov verify\n"
            "install:\n\t@echo 'Configure stack dependencies'\n"
            "verify:\n\t@echo 'Run stack verification gates'\n"
        )
    if not is_tech:
        files_to_write[f"{rel_tpl}/assets/canonical_snippet.md"] = (
            f"<!-- Canonical asset for {template_name} ({kind}) -->\n"
        )

    if not dry_run:
        for rel_path, content in files_to_write.items():
            full_path = repo_dir / rel_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding="utf-8")
        manifest_path = repo_dir / "system" / "mcp-layer.json"
        if manifest_path.is_file():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if isinstance(manifest, dict):
                manifest["default_stack_templates"] = _merge_unique_strings(
                    manifest.get("default_stack_templates", []), [template_name]
                )
                if register_binding:
                    bindings = list(manifest.get("surface_bindings", []))
                    bindings.append(binding_entry)
                    manifest["surface_bindings"] = bindings
                manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    return dict(
        template_id=template_name,
        kind=kind,
        files_created=sorted(files_to_write.keys()),
        binding_registered=register_binding,
        dry_run=dry_run,
    )


def apply_fork_to_project(
    repo_dir: Path,
    target_project_dir: Path,
    *,
    template_ref: str | None = None,
    layers_filter: list[str] | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Materialize template pack and 0..N layer rules/bindings into a target project."""
    root_manifest_path = repo_dir / "system" / "mcp-layer.json"
    root_manifest: dict[str, Any] = (
        json.loads(root_manifest_path.read_text(encoding="utf-8"))
        if root_manifest_path.is_file()
        else {"layer_id": "root", "layer_role": "corporate", "precedence": 10}
    )
    layers_dir = repo_dir / "layers"
    candidate_layers: list[tuple[str, Path, dict[str, Any]]] = [("root", repo_dir, root_manifest)]
    if layers_dir.is_dir():
        for sub in sorted(layers_dir.iterdir()):
            if not sub.is_dir() or sub.name.startswith("."):
                continue
            sub_m_path = sub / "system" / "mcp-layer.json"
            sub_m = (
                json.loads(sub_m_path.read_text(encoding="utf-8"))
                if sub_m_path.is_file()
                else {"layer_id": sub.name, "layer_role": "department", "precedence": 50}
            )
            candidate_layers.append((sub.name, sub, sub_m))

    if layers_filter and "all" not in layers_filter:
        allowed = set(layers_filter)
        candidate_layers = [
            (name, ldir, m)
            for name, ldir, m in candidate_layers
            if name in allowed or str(m.get("layer_id")) in allowed
        ]
    candidate_layers.sort(key=lambda item: (int(item[2].get("precedence", 50)), item[0]))

    resolved_templates: list[tuple[str, Path]] = []
    if template_ref:
        for raw_ref in [r.strip() for r in template_ref.split(",") if r.strip()]:
            found_dir: Path | None = None
            found_name = ""
            if ":" in raw_ref:
                layer_part, tpl_part = raw_ref.split(":", 1)
                for name, ldir, _m in candidate_layers:
                    cand_d = _resolve_template_dir(ldir, tpl_part) if name == layer_part else None
                    if cand_d is not None:
                        found_dir, found_name = cand_d, cand_d.name
                        break
            else:
                for _name, ldir, _m in sorted(candidate_layers, key=lambda item: item[0] != "root"):
                    cand_d = _resolve_template_dir(ldir, raw_ref)
                    if cand_d is not None:
                        found_dir, found_name = cand_d, cand_d.name
                        break
            if found_dir is None:
                raise ValueError(f"Template {raw_ref!r} not found in selected layers")
            resolved_templates.append((found_name, found_dir))
    else:
        for tpl_item in root_manifest.get("default_stack_templates", []):
            tpl_str = str(tpl_item)
            cand_d = _resolve_template_dir(repo_dir, tpl_str) if tpl_str != "human-core" else None
            if cand_d is not None:
                resolved_templates.append((cand_d.name, cand_d))

    resolved_tpl_name = ",".join(t[0] for t in resolved_templates)
    mat_templates = list(resolved_templates)
    seen_names = {t[0] for t in mat_templates}
    for grp, base_id in (("tech-stack", "technical-base"), ("business-stack", "business-base")):
        if (
            base_id not in seen_names
            and any(d.parent.name == grp for _n, d in resolved_templates)
            and (base_dir := _resolve_template_dir(repo_dir, base_id)) is not None
        ):
            mat_templates.insert(0, (base_id, base_dir))
            seen_names.add(base_id)

    copied_files: list[str] = []
    agents_dir = target_project_dir / ".agents"
    for tpl_name, tpl_dir in mat_templates:
        for sub_name, dest_sub in (
            ("rules", agents_dir / "rules"),
            ("skills", agents_dir / "skills"),
        ):
            src_sub = tpl_dir / sub_name
            if src_sub.is_dir():
                for src_file in sorted(src_sub.rglob("*")):
                    if not src_file.is_file():
                        continue
                    rel = src_file.relative_to(src_sub)
                    dest = dest_sub / rel
                    copied_files.append(str(dest.relative_to(target_project_dir)))
                    if not dry_run:
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        dest.unlink(missing_ok=True)
                        shutil.copy2(src_file, dest)
                        if sub_name == "rules" and dest.suffix == ".md":
                            _ensure_rule_file_frontmatter(dest)
                        dest.chmod(dest.stat().st_mode | OWNER_WRITABLE_MODE_BIT)
        gov_src = tpl_dir / "governance"
        if gov_src.is_dir():
            for gfile in [*sorted(gov_src.glob("*.md")), *sorted(gov_src.glob("Makefile"))]:
                dest_g = (
                    agents_dir / "SESSION.md"
                    if gfile.name == "SESSION.md"
                    else target_project_dir / gfile.name
                )
                if not dest_g.exists():
                    copied_files.append(str(dest_g.relative_to(target_project_dir)))
                    if not dry_run:
                        dest_g.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(gfile, dest_g)
                        dest_g.chmod(dest_g.stat().st_mode | OWNER_WRITABLE_MODE_BIT)
        assets_src = tpl_dir / "assets"
        if assets_src.is_dir():
            for afile in sorted(assets_src.rglob("*")):
                if not afile.is_file():
                    continue
                dest_a = agents_dir / "assets" / tpl_name / afile.relative_to(assets_src)
                copied_files.append(str(dest_a.relative_to(target_project_dir)))
                if not dry_run:
                    dest_a.parent.mkdir(parents=True, exist_ok=True)
                    dest_a.unlink(missing_ok=True)
                    shutil.copy2(afile, dest_a)
                    dest_a.chmod(dest_a.stat().st_mode | OWNER_WRITABLE_MODE_BIT)

    lineage_rows: list[str] = []
    for name, ldir, m in candidate_layers:
        prec, lid = int(m.get("precedence", 50)), str(m.get("layer_id", name))
        role = str(m.get("layer_role", "department"))
        bindings = collect_layer_effective_bindings(ldir, m)
        lineage_rows.append(f"| `{prec}` | `{name}` | `{lid}` | `{role}` | `{len(bindings)}` |")
        layer_agents = ldir / "antigravity/.gemini/config/AGENTS.md"
        dest_rule = agents_dir / "rules" / f"layer-{prec:02d}-{name}.md"
        if name == "root" and repo_dir.resolve() == target_project_dir.resolve():
            if not dry_run:
                dest_rule.unlink(missing_ok=True)
        elif layer_agents.is_file():
            copied_files.append(str(dest_rule.relative_to(target_project_dir)))
            if not dry_run:
                dest_rule.parent.mkdir(parents=True, exist_ok=True)
                dest_rule.unlink(missing_ok=True)
                shutil.copy2(layer_agents, dest_rule)
                _ensure_rule_file_frontmatter(dest_rule)
                dest_rule.chmod(dest_rule.stat().st_mode | OWNER_WRITABLE_MODE_BIT)

    lineage_dest, session_dest = agents_dir / "LAYER_LINEAGE.md", agents_dir / "SESSION.md"
    copied_files.extend([str(lineage_dest.relative_to(target_project_dir)), ".agents/SESSION.md"])
    if not dry_run:
        lineage_dest.parent.mkdir(parents=True, exist_ok=True)
        lineage_dest.write_text(
            _render_lineage_markdown(resolved_tpl_name, lineage_rows), encoding="utf-8"
        )
        if not session_dest.exists():
            tpl_tag = resolved_tpl_name or "default"
            session_dest.write_text(
                f"# Session State Log\n\n## Session Log\n\n- Initialized (`{tpl_tag}`).\n",
                encoding="utf-8",
            )

    return dict(
        target_project_dir=str(target_project_dir),
        applied_template=resolved_tpl_name or None,
        participating_layers=[name for name, _d, _m in candidate_layers],
        files_materialized=_merge_unique_strings(copied_files),
        dry_run=dry_run,
    )
