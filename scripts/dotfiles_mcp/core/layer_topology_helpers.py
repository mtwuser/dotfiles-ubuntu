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
from fnmatch import fnmatchcase
from pathlib import Path
from typing import Any

from dotfiles_mcp.core.constants import (
    DEFAULT_SQUAD_ONBOARDING_SPEC,
    HUMAN_STACK_BLUEPRINT_HINT,
    LAYER_MAKEFILE_RECIPES,
    LAYER_MANIFEST_CONTRACT_REV,
    LAYER_ROLE_MAKEFILE_TARGETS,
    MAKEFILE_ROLE_HEADER_PREFIX,
    PUBLIC_GOV_PREFIXES,
    REPO_DIR,
    ROLE_DEFAULT_PRECEDENCE,
    ROLE_ENVIRONMENT_PERMISSIONS,
    ROLE_ONBOARDING_SPECS,
    TEMPLATE_MANIFEST_CONTRACT_REV,
    TOPOLOGICAL_ROLE_CLASSES,
    VALID_ENTITY_KINDS,
)
from dotfiles_mcp.core.manifest_helpers import (
    _has_stale_schema,
    _is_oss_root_manifest,
    _iter_layer_template_dirs,
    _load_manifest_dict,
    _resolve_template_dir,
    _sha256_file,
    _stamp_schema_rev,
)


def _resolve_layer_entity_identity(
    target_dir: Path, manifest: dict[str, Any] | None = None, parent_dir: Path | None = None
) -> dict[str, Any]:
    """Resolve entity_kind, collective_scope, and governing_root_id (Root 0) for a layer."""
    ws = target_dir.resolve()
    m = manifest if manifest is not None else _load_manifest_dict(ws)
    lid, lrole = str(m.get("layer_id", ws.name)), str(m.get("layer_role", "project"))
    prec = int(m.get("precedence", ROLE_DEFAULT_PRECEDENCE.get(lrole, 80)))
    raw_ek = str(m.get("entity_kind", "")).strip().lower()
    if raw_ek in VALID_ENTITY_KINDS:
        ek = raw_ek
    elif (
        lrole == "workstation"
        and lid not in ("dotfiles-ubuntu-default", "dotfiles-workstation-root")
    ) or prec >= 85:
        ek = "individual"
    elif _is_oss_root_manifest(m):
        ek = "open-source"
    elif 1 <= prec <= 4 or lid.lower().startswith(PUBLIC_GOV_PREFIXES):
        ek = "public-government"
    else:
        ek = "enterprise"
    cscope = "individual" if ek == "individual" else "collective"
    exp_root = str(m.get("governing_root_id", "")).strip()
    up_raw = m.get("upstream_layer")
    raw_up_lid = str(up_raw.get("layer_id", "")).strip() if isinstance(up_raw, dict) else ""
    up_lid = "" if raw_up_lid == "dotfiles-workstation-root" else raw_up_lid
    eff_p, p_root, p_ek = _resolve_default_parent_dir(ws, parent_dir), "", ""
    if eff_p is not None and (eff_p / "system/mcp-layer.json").is_file():
        pm = _load_manifest_dict(eff_p)
        if not _is_oss_root_manifest(pm):
            p_id = _resolve_layer_entity_identity(eff_p, pm)
            p_root = str(p_id["governing_root_id"] or pm.get("layer_id", eff_p.name))
            p_ek = str(p_id["entity_kind"])
    org_pfx = re.split(r"-(?:dept|squad)-", lid)[0] if ("-dept-" in lid or "-squad-" in lid) else ""
    up_org_pfx = (
        re.split(r"-(?:dept|squad)-", up_lid)[0]
        if ("-dept-" in up_lid or "-squad-" in up_lid)
        else ""
    )
    conflict_pfx = bool(org_pfx and p_root and not p_root.startswith(org_pfx))
    if ek == "individual":
        gov_root: str | None = exp_root or None
    elif exp_root:
        gov_root = exp_root
    elif lrole == "corporate" or ek == "open-source" or (ek == "public-government" and prec <= 2):
        gov_root = lid
    elif p_root and p_ek == ek and not conflict_pfx:
        gov_root = p_root
    elif up_org_pfx:
        gov_root = f"{up_org_pfx}-root"
    elif up_lid:
        gov_root = up_lid
    elif org_pfx:
        gov_root = f"{org_pfx}-root"
    else:
        gov_root = lid
    t_cls = TOPOLOGICAL_ROLE_CLASSES.get(lrole, "consumer-workspace")
    return {"layer_id": lid, "layer_role": lrole, "topological_class": t_cls, "precedence": prec,
        "entity_kind": ek, "collective_scope": cscope, "governing_root_id": gov_root}  # fmt: skip


def _classify_inter_layer_relationship(
    source_identity: dict[str, Any], target_identity: dict[str, Any]
) -> dict[str, Any]:
    """Classify mutual relationship between layers (internal vs external collective/individual)."""
    src_ek, tgt_ek = str(source_identity["entity_kind"]), str(target_identity["entity_kind"])
    src_root, tgt_root = (
        source_identity.get("governing_root_id"),
        target_identity.get("governing_root_id"),
    )
    same_root = bool(
        src_root
        and src_root == tgt_root
        and src_ek == tgt_ek
        and source_identity["collective_scope"] == "collective"
        and target_identity["collective_scope"] == "collective"
    )
    rel_scope = "internal" if same_root else "external"
    return {"relationship_scope": rel_scope,
        "external_category": "internal" if same_root else f"external:{tgt_ek}",
        "same_governing_root": same_root, "source_governing_root_id": src_root,
        "target_governing_root_id": tgt_root, "target_entity_kind": tgt_ek,
        "target_collective_scope": target_identity["collective_scope"]}  # fmt: skip


def _match_manifest_actor_role(manifest: dict[str, Any], actor_email: str) -> tuple[str, bool]:
    """Resolve actor_email role (owner, maintainer, validator, member, consumer) in manifest."""
    raw_auth = manifest.get("layer_authority")
    auth = raw_auth if isinstance(raw_auth, dict) else {}
    raw_roster = auth.get("roster")
    roster = raw_roster if isinstance(raw_roster, dict) else {}

    def _Pool(top_key: str, roster_key: str) -> list[str]:
        top = [str(e).strip() for e in auth.get(top_key, []) if str(e).strip()]
        r_list = [
            str(m.get("email", "")).strip()
            for m in roster.get(roster_key, [])
            if isinstance(m, dict) and str(m.get("email", "")).strip()
        ]
        return list(dict.fromkeys([*top, *r_list]))

    owners = _Pool("authorized_emails", "owners")
    maintainers = _Pool("maintainer_emails", "maintainers")
    validators = _Pool("validator_emails", "validators")
    members = _Pool("member_emails", "members")
    has_roster = bool(owners or maintainers or validators or members)
    clean_em = actor_email.strip().lower()
    if not clean_em:
        return "consumer", has_roster
    for role_name, pool in (
        ("owner", owners),
        ("maintainer", maintainers),
        ("validator", validators),
        ("member", members),
    ):
        if any(fnmatchcase(clean_em, pat.lower()) for pat in pool):
            return role_name, has_roster
    return "consumer", has_roster


def _resolve_hierarchical_actor_profile(
    target_dir: Path, *, actor_email: str, parent_dir: Path | None = None
) -> dict[str, Any]:
    """Compute effective actor role, read-only upstream inheritance, and parent overarching auth."""
    ws = target_dir.resolve()
    ws_m = _load_manifest_dict(ws)
    eff_p = _resolve_default_parent_dir(ws, parent_dir)
    local_id_meta = _resolve_layer_entity_identity(ws, ws_m, eff_p)
    lid, lrole, lprec = (
        str(local_id_meta["layer_id"]),
        str(local_id_meta["layer_role"]),
        int(local_id_meta["precedence"]),
    )
    local_role, has_roster = _match_manifest_actor_role(ws_m, actor_email)
    up_role, up_id, up_prec, hier_ok = "consumer", None, None, False
    up_rel = "none"
    if eff_p is not None and (eff_p / "system/mcp-layer.json").is_file():
        up_m = _load_manifest_dict(eff_p)
        up_id_meta = _resolve_layer_entity_identity(eff_p, up_m)
        up_id = str(up_id_meta["layer_id"])
        up_prec = int(up_id_meta["precedence"])
        rel = _classify_inter_layer_relationship(local_id_meta, up_id_meta)
        up_rel = str(rel["external_category"])
        if not _is_oss_root_manifest(up_m):
            up_role, _ = _match_manifest_actor_role(up_m, actor_email)
            hier_ok = (
                up_role in ("owner", "maintainer")
                and up_prec < lprec
                and rel["relationship_scope"] == "internal"
            )
    rank = {"owner": 4, "maintainer": 3, "validator": 2, "member": 1, "consumer": 0}
    eff_role = up_role if (hier_ok and rank[up_role] > rank[local_role]) else local_role
    return {"layer_id": lid, "layer_role": lrole, "precedence": lprec,
        "entity_identity": local_id_meta, "actor_email": actor_email, "local_role": local_role,
        "has_configured_roster": has_roster, "upstream_layer_id": up_id,
        "upstream_precedence": up_prec, "upstream_role": up_role, "upstream_relationship": up_rel,
        "upstream_read_only": up_role not in ("owner", "maintainer"),
        "hierarchical_authority_granted": hier_ok, "effective_role": eff_role,
        "allowed_environments": list(ROLE_ENVIRONMENT_PERMISSIONS[eff_role])}  # fmt: skip


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
    """Resolve a 1-hop child layer directory strictly inside mounted ws/layers/<child>."""
    layers_dir = workspace_dir.resolve() / "layers"
    cand = layers_dir / child_name
    if (cand / "system" / "mcp-layer.json").is_file():
        return cand.resolve()
    for mf in sorted(layers_dir.glob("*/system/mcp-layer.json")):
        with contextlib.suppress(json.JSONDecodeError, OSError):
            data = json.loads(mf.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("layer_id") == child_name:
                return mf.parent.parent.resolve()
    return None


def _is_makefile_outdated(ws_dir: Path, role: str) -> bool:
    """Return True if ws_dir/Makefile is a generated layer Makefile missing current targets."""
    req_t = LAYER_ROLE_MAKEFILE_TARGETS.get(role, LAYER_ROLE_MAKEFILE_TARGETS["project"])
    mk_txt = (ws_dir / "Makefile").read_text("utf-8") if (ws_dir / "Makefile").is_file() else ""
    return mk_txt.startswith(MAKEFILE_ROLE_HEADER_PREFIX) and (
        any(f"\n{t}:\n" not in mk_txt for t in req_t)
        or "--upstream-dir $(TARGET_REPO)" not in mk_txt
        or "consult-layer $(CURDIR) $(PARENT_FLAG)" not in mk_txt
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
        stale_cm = _has_stale_schema(cm_f, LAYER_MANIFEST_CONTRACT_REV)
        c_files = ["system/mcp-layer.json"] if stale_cm else []
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
            push_c = f"./scripts/layer-subtree.sh push {cname} {br}"
            drifts.append({"layer_id": cname, "mounted_path": f"layers/{cname}",
                "drift_files": c_files, "subtree_push_command": push_c,
                "subtree_pull_command": f"./scripts/layer-subtree.sh pull {cname}"})  # fmt: skip
    return drifts


def _sync_mounted_children_into_parent(
    target_dir: Path, mounted_layers: list[Any], *, dry_run: bool = False
) -> list[str]:
    """Synchronize parent contracts, Makefile, and shared templates into layers/<child>/."""
    ws = target_dir.resolve()
    rem = {
        str(e.get("name") or e.get("layer_id") or "").strip()
        for e in (mounted_layers or [])
        if isinstance(e, dict) and str(e.get("repository") or "").strip()
    }
    drifts = _inspect_mounted_children_drifts(ws, mounted_layers)
    synced = [str(d["layer_id"]) for d in drifts if str(d["layer_id"]) not in rem]
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
    p_wt = ws / "WORKTASK.md"
    if not dry_run and p_wt.is_file() and (ws / "layers").is_dir():
        done_tks = {
            m.group(1).lower()
            for cwt in (ws / "layers").glob("*/WORKTASK.md")
            for ln in cwt.read_text("utf-8").splitlines()
            if re.match(r"^\s*-\s*\[[xX]\]\s+", ln)
            and (m := re.search(r"\b([A-Z]{2,12}-\d{2,6}(?:-\d{1,6})?)\b", ln))
        }
        p_txt = p_wt.read_text("utf-8")
        p_lines = [
            re.sub(r"^(\s*-\s*\[)[ /](\])", r"\1x\2", pl).replace(
                "stage: `delegated`", "stage: `completed (pro)`"
            )
            if re.match(r"^\s*-\s*\[[ /]\]\s+", pl)
            and "->" in pl
            and any(tk in pl.lower() for tk in done_tks)
            else pl
            for pl in p_txt.splitlines()
        ]
        if (new_p_txt := "\n".join(p_lines) + "\n") != p_txt:
            p_wt.write_text(new_p_txt, "utf-8")
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
