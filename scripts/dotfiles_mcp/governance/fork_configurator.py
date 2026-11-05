"""Fork parameterization, polymorphic template scaffolding, and static project projection.

Specification: docs/architecture/06_layer_governance_and_promotion_engines.md
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from dotfiles_mcp.capsules.surface_weaver import collect_layer_effective_bindings
from dotfiles_mcp.core.constants import (
    KEBAB_ID_RE,
    LAYER_MANIFEST_CONTRACT_REV,
    OWNER_WRITABLE_MODE_BIT,
    PRUNABLE_STARTER_TEMPLATES,
    REPO_DIR,
    ROLE_DEFAULT_PRECEDENCE,
    TEMPLATE_MANIFEST_CONTRACT_REV,
    VALID_ENTITY_KINDS,
    VALID_LAYER_ROLES,
    VALID_TEMPLATE_KINDS,
)
from dotfiles_mcp.core.layer_topology_helpers import _render_lineage_markdown
from dotfiles_mcp.core.manifest_helpers import (
    _ensure_rule_file_frontmatter,
    _merge_unique_strings,
    _resolve_template_dest_dir,
    _resolve_template_dir,
    discover_layer_template_names,
)


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
    entity_kind: str | None = None,
    governing_root_id: str | None = None,
    prune_default_templates: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Parameterize system/mcp-layer.json (mcp-layer-v1) for a fork."""
    if not KEBAB_ID_RE.match(layer_id):
        raise ValueError(f"Invalid layer_id {layer_id!r}: must be kebab-case")
    if layer_role not in VALID_LAYER_ROLES:
        raise ValueError(f"Invalid layer_role {layer_role!r}: must be one of {VALID_LAYER_ROLES}")
    if entity_kind is not None and entity_kind not in VALID_ENTITY_KINDS:
        raise ValueError(
            f"Invalid entity_kind {entity_kind!r}: must be one of {VALID_ENTITY_KINDS}"
        )
    eff_precedence = precedence if precedence is not None else ROLE_DEFAULT_PRECEDENCE[layer_role]
    if eff_precedence < 0 or eff_precedence > 100:
        raise ValueError(f"Invalid precedence {eff_precedence}: must be between 0 and 100")

    manifest_path = repo_dir / "system" / "mcp-layer.json"
    loaded_m = (
        json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else {}
    )
    base_m = loaded_m if isinstance(loaded_m, dict) else {}
    up_default = {
        "layer_id": "mtwuser/dotfiles-ubuntu",
        "repository": "https://github.com/mtwuser/dotfiles-ubuntu.git",
        "branch": "master",
    }
    manifest: dict[str, Any] = {
        "mounted_layers_dir": "layers",
        "mounted_layers": [],
        "default_stack_templates": discover_layer_template_names(repo_dir),
        "baseline_guardrails": [],
        "surface_bindings": [],
        "environments": {},
        "federated_mcps": [],
        **base_m,
        "schema_version": LAYER_MANIFEST_CONTRACT_REV,
        "layer_id": layer_id,
        "layer_role": layer_role,
        "precedence": eff_precedence,
        "description": description
        or base_m.get("description")
        or f"Configured {layer_role} layer ({layer_id})",
    }
    if entity_kind is not None:
        manifest["entity_kind"] = entity_kind
    if governing_root_id is not None:
        manifest["governing_root_id"] = governing_root_id
    upstream = {**up_default, **dict(manifest.get("upstream_layer", {}))}
    if upstream_url is not None:
        upstream["repository"] = upstream_url
    if upstream_id is not None:
        upstream["layer_id"] = upstream_id
    if upstream_branch is not None:
        upstream["branch"] = upstream_branch
    manifest["upstream_layer"] = upstream

    if prune_default_templates:
        manifest["default_stack_templates"] = [
            t
            for t in manifest.get("default_stack_templates", [])
            if t not in PRUNABLE_STARTER_TEMPLATES
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
        manifest_path.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    return manifest


def scaffold_template_pack(
    repo_dir: Path, *, template_name: str, kind: str = "framework-stack",
    description: str | None = None, register_binding: bool = False,
    rule_filename: str | None = None, scopes: list[str] | None = None,
    planes: list[str] | None = None, traits: list[str] | None = None,
    globs: list[str] | None = None, dry_run: bool = False,
) -> dict[str, Any]:  # fmt: skip
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
    tpl_dir = _resolve_template_dest_dir(repo_dir, template_name)
    rel_tpl = str(tpl_dir.relative_to(repo_dir)).replace("\\", "/")
    is_tech = kind == "framework-stack"

    desc = description or f"{template_name} ({kind}) governance and template pack"
    mode = "transversal" if is_tech else "authoritative"
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
        "ephemeral_fork_policy": {
            "bot_role": f"{template_name}-guardian",
            "trigger": "on_surface_match",
            "model_tier": "flash" if is_tech else "inherit",
            "access_mode": "strictly-read-only",
            "mount_templates": [template_name],
            "resolution": default_res,
            "ttl_seconds": 300,
            "handback_contract": "4-channel-digest+rcap1",
        },
    }
    tpl_manifest = {
        "schema_version": TEMPLATE_MANIFEST_CONTRACT_REV,
        "template_id": template_name,
        "kind": kind,
        "target_role": "domain-policy" if kind in ("business-stack", "science-stack") else "squad",
        "description": desc,
        "recommended_surface_bindings": [binding_entry],
    }
    files_to_write: dict[str, str] = {
        f"{rel_tpl}/template.json": json.dumps(tpl_manifest, indent=2, ensure_ascii=False) + "\n",
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
    if is_tech:
        files_to_write[f"{rel_tpl}/governance/WORKTASK.md"] = (
            f"# Active Work Tasks — {template_name}\n\n- [ ] Initial setup\n"
        )
        files_to_write[f"{rel_tpl}/governance/Makefile"] = (
            ".PHONY: install format lint test test-cov verify\n"
            "install:\n\t@echo 'Configure stack dependencies'\n"
            "verify:\n\t@echo 'Run stack verification gates'\n"
        )
    else:
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
                manifest_path.write_text(
                    json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
                )

    return {"template_id": template_name, "kind": kind, "dry_run": dry_run,
        "files_created": sorted(files_to_write.keys()),
        "binding_registered": register_binding}  # fmt: skip


def apply_fork_to_project(
    repo_dir: Path,
    target_project_dir: Path,
    *,
    template_ref: str | None = None,
    layers_filter: list[str] | None = None,
    include_layer_defaults: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Materialize template pack and 0..N layer rules/bindings into a target project."""
    root_manifest_path = repo_dir / "system" / "mcp-layer.json"
    corp_prec, svc_prec = (
        ROLE_DEFAULT_PRECEDENCE["corporate"],
        ROLE_DEFAULT_PRECEDENCE["service-node"],
    )
    root_manifest: dict[str, Any] = (
        json.loads(root_manifest_path.read_text(encoding="utf-8"))
        if root_manifest_path.is_file()
        else {"layer_id": "root", "layer_role": "corporate", "precedence": corp_prec}
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
                else {"layer_id": sub.name, "layer_role": "department", "precedence": svc_prec}
            )
            candidate_layers.append((sub.name, sub, sub_m))

    if layers_filter and "all" not in layers_filter:
        allowed = set(layers_filter)
        candidate_layers = [
            (n, ld, m)
            for n, ld, m in candidate_layers
            if n in allowed or str(m.get("layer_id")) in allowed
        ]
    candidate_layers.sort(key=lambda item: (int(item[2].get("precedence", svc_prec)), item[0]))

    resolved_templates: list[tuple[str, Path]] = []
    def_tpls = [
        str(t) for t in root_manifest.get("default_stack_templates", []) if str(t) != "human-base"
    ]
    if template_ref:
        raw_list = [r.strip() for r in template_ref.split(",") if r.strip()]
        req_refs = _merge_unique_strings(def_tpls, raw_list) if include_layer_defaults else raw_list
        for raw_ref in req_refs:
            found_dir: Path | None = None
            found_name = ""
            if ":" in raw_ref:
                layer_part, tpl_part = raw_ref.split(":", 1)
                for name, ldir, _m in candidate_layers:
                    if name == layer_part and (cand_d := _resolve_template_dir(ldir, tpl_part)):
                        found_dir, found_name = cand_d, cand_d.name
                        break
            else:
                for _name, ldir, _m in sorted(candidate_layers, key=lambda item: item[0] != "root"):
                    if cand_d := _resolve_template_dir(ldir, raw_ref):
                        found_dir, found_name = cand_d, cand_d.name
                        break
                if found_dir is None and (eng_d := _resolve_template_dir(REPO_DIR, raw_ref)):
                    found_dir, found_name = eng_d, eng_d.name
            if found_dir is None:
                raise ValueError(f"Template {raw_ref!r} not found in selected layers")
            resolved_templates.append((found_name, found_dir))
    else:
        for tpl_str in def_tpls:
            if cand_d := _resolve_template_dir(repo_dir, tpl_str):
                resolved_templates.append((cand_d.name, cand_d))

    resolved_tpl_name = ",".join(t[0] for t in resolved_templates)
    mat_templates = list(resolved_templates)
    seen_names = {t[0] for t in mat_templates}
    for p_names, tpl_names, base_id in (
        (("framework-stack",), ("nist-csf-security",), "software-engineering"),
        (("framework-stack", "science-stack"), ("nist-csf-security",), "science-base"),
        (("business-stack",), ("nist-csf-security",), "business-base"),
    ):
        if (
            base_id not in seen_names
            and any(d.parent.name in p_names or n in tpl_names for n, d in resolved_templates)
            and (
                base_dir := _resolve_template_dir(repo_dir, base_id)
                or _resolve_template_dir(REPO_DIR, base_id)
            )
        ):
            mat_templates.insert(0, (base_id, base_dir))
            seen_names.add(base_id)

    copied_files: list[str] = []
    agents_dir = target_project_dir / ".agents"

    def _copy_file(src: Path, dest: Path, *, overwrite: bool = True, fm: bool = False) -> None:
        if not dry_run:
            dest.parent.mkdir(parents=True, exist_ok=True)
            if overwrite:
                dest.unlink(missing_ok=True)
            shutil.copy2(src, dest)
            if fm:
                _ensure_rule_file_frontmatter(dest)
            dest.chmod(dest.stat().st_mode | OWNER_WRITABLE_MODE_BIT)

    for tpl_name, tpl_dir in mat_templates:
        for sub_name, dest_sub in (
            ("rules", agents_dir / "rules"),
            ("skills", agents_dir / "skills"),
        ):
            src_sub = tpl_dir / sub_name
            if src_sub.is_dir():
                for src_file in sorted(src_sub.rglob("*")):
                    if src_file.is_file():
                        dest = dest_sub / src_file.relative_to(src_sub)
                        copied_files.append(str(dest.relative_to(target_project_dir)))
                        _copy_file(
                            src_file, dest, fm=(sub_name == "rules" and dest.suffix == ".md")
                        )
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
                    _copy_file(gfile, dest_g, overwrite=False)
        assets_src = tpl_dir / "assets"
        if assets_src.is_dir():
            for afile in sorted(assets_src.rglob("*")):
                if afile.is_file():
                    dest_a = agents_dir / "assets" / tpl_name / afile.relative_to(assets_src)
                    copied_files.append(str(dest_a.relative_to(target_project_dir)))
                    _copy_file(afile, dest_a)

    lineage_rows: list[str] = []
    for name, ldir, m in candidate_layers:
        prec, lid = int(m.get("precedence", svc_prec)), str(m.get("layer_id", name))
        role = str(m.get("layer_role", "department"))
        bindings = collect_layer_effective_bindings(ldir, m)
        lineage_rows.append(f"| `{prec}` | `{name}` | `{lid}` | `{role}` | `{len(bindings)}` |")
        layer_agents = ldir / "antigravity/.gemini/config/AGENTS.md"
        dest_rule = agents_dir / "rules" / f"layer-{prec:02d}-{name}.md"
        if name == "root" and repo_dir.resolve() == target_project_dir.resolve():
            if not dry_run:
                dest_rule.unlink(missing_ok=True)
            root_skills = ldir / "antigravity/.gemini/config/skills"
            for sf in sorted(root_skills.glob("*/SKILL.md")):
                dest_sk = agents_dir / "skills" / sf.parent.name / "SKILL.md"
                copied_files.append(str(dest_sk.relative_to(target_project_dir)))
                _copy_file(sf, dest_sk)
        elif layer_agents.is_file():
            copied_files.append(str(dest_rule.relative_to(target_project_dir)))
            _copy_file(layer_agents, dest_rule, fm=True)

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

    return {
        "target_project_dir": str(target_project_dir),
        "applied_template": resolved_tpl_name or None,
        "participating_layers": [name for name, _d, _m in candidate_layers],
        "files_materialized": _merge_unique_strings(copied_files),
        "dry_run": dry_run,
    }
