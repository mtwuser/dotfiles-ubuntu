"""Global profile composer, subtree manifest registrar, and one-shot workspace bootstrapper.

Specification: docs/architecture/04_compaction_surface_and_promotion_engines.md
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .constants import (
    AGENTS_MD_MAX_BYTES,
    KEBAB_ID_RE,
    ROLE_DEFAULT_PRECEDENCE,
    VALID_LAYER_ROLES,
)
from .fork_configurator import (
    apply_fork_to_project,
    configure_fork_manifest,
    scaffold_template_pack,
)

VALID_GLOBAL_PROFILES = ("human-core", "technical", "business", "full")

PROFILE_TEMPLATE_CHAIN: dict[str, tuple[tuple[str, str], ...]] = {
    "human-core": (("human-core", "human-core.md"),),
    "technical": (
        ("human-core", "human-core.md"),
        ("technical-base", "technical-base.md"),
    ),
    "business": (
        ("human-core", "human-core.md"),
        ("business-base", "business-base.md"),
    ),
    "full": (
        ("human-core", "human-core.md"),
        ("technical-base", "technical-base.md"),
        ("business-base", "business-base.md"),
    ),
}


def _strip_secondary_header(markdown_text: str) -> str:
    """Strip the top H1 and introductory blockquote when appending a secondary profile."""
    lines = markdown_text.strip().splitlines()
    idx = 0
    while idx < len(lines) and (
        lines[idx].startswith("# ")
        or lines[idx].startswith(">")
        or not lines[idx].strip()
        or lines[idx].strip() == "---"
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
        raise ValueError(
            f"Invalid global profile {profile!r}; must be one of {VALID_GLOBAL_PROFILES}"
        )

    chain = PROFILE_TEMPLATE_CHAIN[profile]
    sections: list[str] = []
    source_files: list[str] = []
    for idx, (tpl_id, rule_filename) in enumerate(chain):
        rule_path = repo_dir / "templates" / tpl_id / "rules" / rule_filename
        if not rule_path.is_file():
            raise ValueError(
                f"Missing profile template rule file: {rule_path.relative_to(repo_dir)}"
            )
        source_files.append(str(rule_path.relative_to(repo_dir)))
        raw_text = rule_path.read_text(encoding="utf-8").strip()
        sections.append(raw_text if idx == 0 else _strip_secondary_header(raw_text))

    composed = "\n\n---\n\n".join(sections) + "\n"
    composed_bytes = len(composed.encode("utf-8"))
    if composed_bytes > AGENTS_MD_MAX_BYTES:
        raise ValueError(
            f"Composed AGENTS.md size ({composed_bytes} bytes) exceeds "
            f"{AGENTS_MD_MAX_BYTES}-byte cap"
        )

    target_agents = repo_dir / "antigravity" / ".gemini" / "config" / "AGENTS.md"
    stow_executed = False
    if not dry_run:
        target_agents.parent.mkdir(parents=True, exist_ok=True)
        target_agents.write_text(composed, encoding="utf-8")
        if run_stow:
            target_home = str(home_dir or Path.home())
            stow_bin = shutil.which("stow") or "/usr/bin/stow"
            subprocess.run(  # noqa: S603
                [stow_bin, "-t", target_home, "-R", "antigravity"],
                cwd=repo_dir,
                check=True,
                capture_output=True,
                text=True,
            )
            stow_executed = True

    return {
        "profile": profile,
        "source_files": source_files,
        "target_file": str(target_agents.relative_to(repo_dir)),
        "size_bytes": composed_bytes,
        "budget_max_bytes": AGENTS_MD_MAX_BYTES,
        "headroom_bytes": AGENTS_MD_MAX_BYTES - composed_bytes,
        "stow_executed": stow_executed,
        "dry_run": dry_run,
    }


def register_mounted_subtree(
    repo_dir: Path,
    layer_name: str,
    repo_url: str,
    branch: str = "master",
    *,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Upsert a mounted subtree entry inside root system/mcp-layer.json -> mounted_layers."""
    if not KEBAB_ID_RE.match(layer_name):
        raise ValueError(f"Invalid layer_name {layer_name!r}")

    root_manifest_path = repo_dir / "system" / "mcp-layer.json"
    if not root_manifest_path.is_file():
        raise ValueError(f"Missing root manifest: {root_manifest_path}")

    root_manifest: dict[str, Any] = json.loads(root_manifest_path.read_text(encoding="utf-8"))
    sub_manifest_path = repo_dir / "layers" / layer_name / "system" / "mcp-layer.json"
    sub_manifest: dict[str, Any] = (
        json.loads(sub_manifest_path.read_text(encoding="utf-8"))
        if sub_manifest_path.is_file()
        else {}
    )

    entry = {
        "name": layer_name,
        "layer_id": str(sub_manifest.get("layer_id") or layer_name),
        "layer_role": str(sub_manifest.get("layer_role") or "department"),
        "precedence": int(sub_manifest.get("precedence", 30)),
        "repository": repo_url,
        "branch": branch,
    }

    existing: list[dict[str, Any]] = [
        item
        for item in root_manifest.get("mounted_layers", [])
        if isinstance(item, dict) and item.get("name") != layer_name
    ]
    existing.append(entry)
    existing.sort(key=lambda item: (int(item.get("precedence", 50)), str(item.get("name", ""))))
    root_manifest["mounted_layers"] = existing

    if not dry_run:
        root_manifest_path.write_text(json.dumps(root_manifest, indent=2) + "\n", encoding="utf-8")

    return {
        "registered_layer": entry,
        "total_mounted_layers": len(existing),
        "dry_run": dry_run,
    }


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
    scaffold_own_template: bool = True,
    dry_run: bool = False,
) -> dict[str, Any]:
    """One-shot initializer for a corporate, domain-policy, department, or team workspace."""
    if not KEBAB_ID_RE.match(layer_id):
        raise ValueError(f"Invalid layer_id {layer_id!r}")
    if layer_role not in VALID_LAYER_ROLES:
        raise ValueError(f"Invalid layer_role {layer_role!r}")

    effective_prec = (
        precedence if precedence is not None else ROLE_DEFAULT_PRECEDENCE.get(layer_role, 50)
    )
    effective_parent = parent_dir if parent_dir is not None else repo_dir
    parent_manifest_path = effective_parent / "system" / "mcp-layer.json"
    inherited_templates: list[str] = []
    if parent_manifest_path.is_file():
        parent_manifest = json.loads(parent_manifest_path.read_text(encoding="utf-8"))
        if parent_manifest.get("layer_role") not in (None, "workstation"):
            upstream_layer_id = upstream_layer_id or parent_manifest.get("layer_id")
            upstream_repo = upstream_repo or parent_manifest.get("repository")
            inherited_templates = [
                str(pt).strip()
                for pt in parent_manifest.get("default_stack_templates", [])
                if str(pt).strip()
            ]

    requested_templates: list[str] = list(inherited_templates)
    for t in templates or []:
        t_clean = t.strip()
        if t_clean and t_clean not in requested_templates:
            requested_templates.append(t_clean)

    copied_templates: list[str] = []
    search_roots = (
        [effective_parent, repo_dir]
        if effective_parent.resolve() != repo_dir.resolve()
        else [repo_dir]
    )
    for tpl_name in requested_templates:
        src_tpl = next(
            (
                root / "templates" / tpl_name
                for root in search_roots
                if (root / "templates" / tpl_name).is_dir()
            ),
            None,
        )
        dest_tpl = target_dir / "templates" / tpl_name
        if src_tpl is not None and src_tpl.resolve() != dest_tpl.resolve():
            copied_templates.append(tpl_name)
            if not dry_run:
                if dest_tpl.exists():
                    shutil.rmtree(dest_tpl)
                shutil.copytree(src_tpl, dest_tpl)

    manifest_res = configure_fork_manifest(
        target_dir,
        layer_id=layer_id,
        layer_role=layer_role,
        precedence=effective_prec,
        description=description,
        upstream_url=upstream_repo,
        upstream_branch=upstream_branch,
        upstream_id=upstream_layer_id,
        prune_default_templates=True,
        dry_run=dry_run,
    )

    if not dry_run and requested_templates:
        m_path = target_dir / "system" / "mcp-layer.json"
        m_data = json.loads(m_path.read_text(encoding="utf-8"))
        m_data["default_stack_templates"] = list(requested_templates)
        m_path.write_text(json.dumps(m_data, indent=2) + "\n", encoding="utf-8")

    own_kind = (
        "domain-policy-pack"
        if layer_role in ("domain-policy", "corporate")
        else ("department-pack" if layer_role == "department" else "project-overlay")
    )
    scaffold_res: dict[str, Any] | None = None
    if scaffold_own_template:
        scaffold_res = scaffold_template_pack(
            target_dir,
            template_name=layer_id,
            kind=own_kind,
            description=description or f"{layer_id} ({layer_role}) governance pack",
            register_binding=True,
            rule_filename=f"{layer_id}.md",
            dry_run=dry_run,
        )

    baseline_files = {
        "VERSION": "0.1.0\n",
        ".gitignore": "__pycache__/\n*.pyc\n.ruff_cache/\n.mypy_cache/\n.pytest_cache/\nlogs/\n",
        "layers/.gitkeep": "",
        "README.md": f"# {layer_id} (`{layer_role}`, `precedence: {effective_prec}`)\n",
        "CHANGELOG.md": (
            f"# Changelog — {layer_id}\n\n"
            f"## [Unreleased]\n\n"
            f"---\n\n"
            f"## [0.1.0]\n"
            f"- Initial layer bootstrap.\n"
        ),
        "WORKTASK.md": (
            f"# Active Work Tasks — {layer_id}\n\n- [x] Initial layer bootstrap (`v0.1.0`).\n"
        ),
        "antigravity/.gemini/config/AGENTS.md": (
            f"# {layer_id} Layer Rules (`{layer_role}`, `precedence: {effective_prec}`)\n\n"
            f"> Governed by `system/mcp-layer.json` (`layer_id: {layer_id}`).\n\n"
            f"## Scope & Surface Target\n"
            f"- Governs `{layer_id}` (`{layer_role}`, `precedence: {effective_prec}`).\n\n"
            f"## Normative Invariants\n"
            f"- Respect *Lex Superior* (`0..100`) and `templates/{layer_id}/` contracts.\n\n"
            f"## Verification & Sign-Off Gates\n"
            f"- [ ] Verify `.agents/LAYER_LINEAGE.md` and `diff-project` parity before commit.\n"
        ),
    }
    created_baseline: list[str] = []
    for rel_path, content in baseline_files.items():
        dest_file = target_dir / rel_path
        if not dest_file.exists():
            created_baseline.append(rel_path)
            if not dry_run:
                dest_file.parent.mkdir(parents=True, exist_ok=True)
                dest_file.write_text(content, encoding="utf-8")

    all_tpls = list(requested_templates)
    if scaffold_own_template and layer_id not in all_tpls:
        all_tpls.append(layer_id)
    tpl_ref_arg = ",".join(all_tpls) if all_tpls else None

    apply_res: dict[str, Any] = {
        "applied_template": tpl_ref_arg,
        "files_materialized": [],
    }
    if not dry_run:
        apply_res = apply_fork_to_project(
            target_dir,
            target_dir,
            template_ref=tpl_ref_arg,
            layers_filter=["all"],
            dry_run=False,
        )

    return {
        "target_dir": str(target_dir),
        "layer_id": layer_id,
        "layer_role": layer_role,
        "precedence": effective_prec,
        "copied_templates": copied_templates,
        "scaffolded_template": scaffold_res["template_id"] if scaffold_res else None,
        "baseline_files_created": sorted(created_baseline),
        "applied_template": apply_res.get("applied_template"),
        "files_materialized": apply_res.get("files_materialized", []),
        "manifest": manifest_res,
        "dry_run": dry_run,
    }


def sync_layer_workspace(
    repo_dir: Path,
    target_dir: Path,
    *,
    parent_dir: Path | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Propagate upstream template updates into target_dir/templates/ and refresh .agents/."""
    manifest_path = target_dir / "system" / "mcp-layer.json"
    if not manifest_path.is_file():
        raise ValueError(f"Missing target layer manifest: {manifest_path}")

    manifest: dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))
    own_layer_id = str(manifest.get("layer_id") or "")
    stack_templates = [
        str(t).strip() for t in manifest.get("default_stack_templates", []) if str(t).strip()
    ]
    existing_tpls = (
        [
            d.name
            for d in sorted((target_dir / "templates").iterdir())
            if d.is_dir() and not d.name.startswith(".")
        ]
        if (target_dir / "templates").is_dir()
        else []
    )
    candidate_tpls = list(dict.fromkeys([*stack_templates, *existing_tpls]))
    effective_parent = parent_dir if parent_dir is not None else repo_dir
    search_roots = (
        [effective_parent, repo_dir]
        if effective_parent.resolve() != repo_dir.resolve()
        else [repo_dir]
    )

    synced_templates: list[str] = []
    for tpl_name in candidate_tpls:
        if tpl_name == own_layer_id:
            continue
        src_tpl = next(
            (
                root / "templates" / tpl_name
                for root in search_roots
                if (root / "templates" / tpl_name).is_dir()
            ),
            None,
        )
        dest_tpl = target_dir / "templates" / tpl_name
        if src_tpl is not None and src_tpl.resolve() != dest_tpl.resolve():
            synced_templates.append(tpl_name)
            if not dry_run:
                shutil.rmtree(dest_tpl, ignore_errors=True)
                shutil.copytree(src_tpl, dest_tpl)

    tpl_ref = ",".join(stack_templates) if stack_templates else None
    apply_res = apply_fork_to_project(
        target_dir,
        target_dir,
        template_ref=tpl_ref,
        layers_filter=["all"],
        dry_run=dry_run,
    )
    return {
        "target_dir": str(target_dir),
        "layer_id": own_layer_id,
        "synced_templates": synced_templates,
        "applied_template": apply_res.get("applied_template"),
        "files_materialized": apply_res.get("files_materialized", []),
        "participating_layers": apply_res.get("participating_layers", []),
        "dry_run": dry_run,
    }
