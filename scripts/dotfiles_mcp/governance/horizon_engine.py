"""1-hop inter-layer horizon radar, section-level template diffing, and sync reconciliation engine.

Specification: docs/architecture/06_layer_governance_and_promotion_engines.md
"""

from __future__ import annotations

import contextlib
import difflib
import json
import re
import shutil
from pathlib import Path
from typing import Any

from dotfiles_mcp.core.constants import MAX_DIFF_PREVIEW_LINES
from dotfiles_mcp.core.layer_topology_helpers import (
    _inspect_mounted_children_drifts,
    _resolve_default_parent_dir,
    _resolve_hierarchical_actor_profile,
)
from dotfiles_mcp.core.manifest_helpers import (
    _is_oss_root_manifest,
    _iter_layer_template_dirs,
    _load_manifest_dict,
    _resolve_oss_contrib_repo_dir,
    _resolve_template_dir,
    _sha256_file,
)
from dotfiles_mcp.governance.authority_engine import (
    resolve_git_user_email,
    verify_layer_operation_authority,
    verify_oss_promotion_agnosticism,
)
from dotfiles_mcp.governance.git_governance_engine import stage_non_destructive_proposal
from dotfiles_mcp.governance.promotion_engine import diff_project_against_layers

_HEADING_RE = re.compile(r"^(#{1,4})\s+(.+)$")


def _clear_upstream_proposal_residue(
    target_dir: Path, prop_dir: Path, tpl_name: str, src_tpl: Path, local_tpl: Path
) -> None:
    """Remove resolved upstream proposal files, alerts, and stamp reconciled upstream hashes."""
    for pf in prop_dir.glob(f"{tpl_name}-*.md"):
        pf.unlink(missing_ok=True)
    with contextlib.suppress(OSError):
        prop_dir.rmdir()
        prop_dir.parent.rmdir()
    token = f".agents/proposals/from-upstream/{tpl_name}-"
    for rel_f in ("WORKTASK.md", ".agents/SESSION.md"):
        fp = target_dir / rel_f
        if fp.is_file() and token in (raw := fp.read_text(encoding="utf-8")):
            kept = [ln for ln in raw.splitlines() if token not in ln]
            cleaned = "\n".join(kept).removesuffix("\n\n## Governance Alerts & Pending Decisions")
            fp.write_text(f"{cleaned.rstrip()}\n", encoding="utf-8")
    local_tpl.mkdir(parents=True, exist_ok=True)
    tj = local_tpl / "template.json"
    td: dict[str, Any] = json.loads(tj.read_text("utf-8")) if tj.is_file() else {}
    rdir = src_tpl / "rules"
    td["reconciled_upstream_sha256"] = {
        rf.name: _sha256_file(rf) for rf in (sorted(rdir.glob("*.md")) if rdir.is_dir() else ())
    }
    tj.write_text(json.dumps(td, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def reconcile_template_pack_sync(
    target_dir: Path, tpl_name: str, src_tpl: Path, dest_tpl: Path, *,
    strategy: str = "reconcile", is_local_newer: bool = False, dry_run: bool = False,
) -> tuple[bool, list[dict[str, Any]]]:  # fmt: skip
    """Reconcile an upstream template pack into dest_tpl using the requested sync strategy."""
    prop_dir = target_dir / ".agents" / "proposals" / "from-upstream"
    local_tpl = _resolve_template_dir(target_dir, tpl_name) or dest_tpl
    if strategy == "keep-local" and local_tpl.is_dir():
        if not dry_run:
            _clear_upstream_proposal_residue(target_dir, prop_dir, tpl_name, src_tpl, local_tpl)
        return False, []
    if strategy == "reconcile" and is_local_newer:
        tj = local_tpl / "template.json"
        t_dict: dict[str, Any] = json.loads(tj.read_text("utf-8")) if tj.is_file() else {}
        raw_rec = t_dict.get("reconciled_upstream_sha256")
        rec_map: dict[str, Any] = raw_rec if isinstance(raw_rec, dict) else {}
        conflicts: list[dict[str, Any]] = []
        for src_rf in sorted((src_tpl / "rules").glob("*.md")):
            src_sha, loc_rf = _sha256_file(src_rf), local_tpl / "rules" / src_rf.name
            if (loc_rf.is_file() and _sha256_file(loc_rf) == src_sha) or rec_map.get(
                src_rf.name
            ) == src_sha:
                continue
            staged = stage_non_destructive_proposal(
                target_dir, scope_tag="from-upstream", file_name=f"{tpl_name}-{src_rf.name}",
                content=src_rf.read_text(encoding="utf-8"), operation="sync-layer",
                reason_code="UPSTREAM_TEMPLATE_CONFLICT", dry_run=dry_run,
            )  # fmt: skip
            rel_stg = str(staged.relative_to(target_dir.resolve())).replace("\\", "/")
            conflicts.append({"template": tpl_name, "staged_proposal": rel_stg,
                "rule_file": f"templates/{tpl_name}/rules/{src_rf.name}",
                "resolution_commands": ["make sync STRATEGY=accept-upstream",
                    "make sync STRATEGY=merge", "make sync STRATEGY=keep-local"]})  # fmt: skip
        return False, conflicts
    preserved: dict[str, list[str]] = {}
    if strategy == "merge" and (local_tpl / "rules").is_dir():
        for dest_rf in sorted((local_tpl / "rules").glob("*.md")):
            src_rf = src_tpl / "rules" / dest_rf.name
            src_txt = src_rf.read_text(encoding="utf-8") if src_rf.is_file() else ""
            blocks = [
                b.strip()
                for b in re.split(r"(?m)^(?=#+\s)", dest_rf.read_text(encoding="utf-8"))
                if b.strip().startswith("#") and b.strip().splitlines()[0].strip() not in src_txt
            ]
            if blocks:
                preserved[dest_rf.name] = blocks
    if not dry_run:
        shutil.rmtree(local_tpl, ignore_errors=True)
        shutil.rmtree(dest_tpl, ignore_errors=True)
        dest_tpl.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src_tpl, dest_tpl)
        for rname, blocks in preserved.items():
            rf, joined = dest_tpl / "rules" / rname, "\n\n".join(blocks)
            rf.write_text(f"{rf.read_text('utf-8').rstrip()}\n\n{joined}\n", encoding="utf-8")
        _clear_upstream_proposal_residue(target_dir, prop_dir, tpl_name, src_tpl, dest_tpl)
    return True, []


def _parse_markdown_sections_map(markdown_text: str) -> list[tuple[str, str]]:
    """Parse Markdown text (excluding YAML frontmatter) into ordered (heading, body) pairs."""
    text = markdown_text.strip()
    end_idx = text.find("\n---\n", 4) if text.startswith("---\n") else -1
    content = text[end_idx + 5 :].strip() if end_idx != -1 else text
    sections: list[tuple[str, str]] = []
    cur_heading = "# Preamble"
    cur_lines: list[str] = []
    for line in content.splitlines():
        if _HEADING_RE.match(line.strip()):
            body_str = "\n".join(cur_lines).strip()
            if cur_heading != "# Preamble" or body_str:
                sections.append((cur_heading, body_str))
            cur_heading = line.strip()
            cur_lines = []
        else:
            cur_lines.append(line)
    tail_str = "\n".join(cur_lines).strip()
    if cur_heading != "# Preamble" or tail_str:
        sections.append((cur_heading, tail_str))
    return sections


def compare_upstream_templates(
    repo_dir: Path,
    target_dir: Path,
    *,
    parent_dir: Path | None = None,
    template_filter: str | None = None,
    apply_upstream_only: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Compare rule sections between upstream (parent/OSS) and local workspace templates."""
    ws, up = target_dir.resolve(), (parent_dir or repo_dir).resolve()
    ws_mp, up_mp = ws / "system/mcp-layer.json", up / "system/mcp-layer.json"
    ws_raw = json.loads(ws_mp.read_text(encoding="utf-8")) if ws_mp.is_file() else {}
    up_raw = json.loads(up_mp.read_text(encoding="utf-8")) if up_mp.is_file() else {}
    ws_m = ws_raw if isinstance(ws_raw, dict) else {}
    up_m = up_raw if isinstance(up_raw, dict) else {}
    ws_tpls = [name for name, _p in _iter_layer_template_dirs(ws)]
    def_tpls = [str(x) for x in ws_m.get("default_stack_templates", [])]
    cand_tpls = list(dict.fromkeys([*def_tpls, *ws_tpls]))
    if template_filter:
        cand_tpls = [t for t in cand_tpls if t == template_filter.strip()]

    file_comparisons: list[dict[str, Any]] = []
    safe_applied: list[str] = []
    for tpl in cand_tpls:
        up_tdir, ws_tdir = _resolve_template_dir(up, tpl), _resolve_template_dir(ws, tpl)
        if up_tdir is None or ws_tdir is None:
            continue
        up_rules = {p.name: p for p in sorted((up_tdir / "rules").glob("*.md"))}
        ws_rules = {p.name: p for p in sorted((ws_tdir / "rules").glob("*.md"))}
        for rname in sorted(set(up_rules) | set(ws_rules)):
            up_rf, ws_rf = up_rules.get(rname), ws_rules.get(rname)
            rel_f = (ws_rf or (ws_tdir / "rules" / rname)).relative_to(ws)
            rel_file = str(rel_f).replace("\\", "/")
            if up_rf is not None and ws_rf is None:
                up_secs = [h for h, _b in _parse_markdown_sections_map(up_rf.read_text("utf-8"))]
                dest_rf = ws_tdir / "rules" / rname
                if apply_upstream_only:
                    safe_applied.append(rel_file)
                    if not dry_run:
                        dest_rf.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(up_rf, dest_rf)
                c_head = {"template": tpl, "rule_file": rel_file, "status": "upstream_only_file"}
                c_secs = {"in_sync_sections": [], "upstream_only_sections": up_secs}
                c_tail: dict[str, Any] = {"local_only_sections": [], "diverged_sections": []}
                c_act = {"recommended_action": "adopt_upstream_file"}
                file_comparisons.append({**c_head, **c_secs, **c_tail, **c_act})
            elif ws_rf is not None and up_rf is None:
                ws_secs = [h for h, _b in _parse_markdown_sections_map(ws_rf.read_text("utf-8"))]
                c_head = {"template": tpl, "rule_file": rel_file, "status": "local_only_file"}
                c_secs = {"in_sync_sections": [], "upstream_only_sections": []}
                c_tail = {"local_only_sections": ws_secs, "diverged_sections": []}
                c_act = {"recommended_action": "keep_local_or_promote"}
                file_comparisons.append({**c_head, **c_secs, **c_tail, **c_act})
            else:
                up_rf, ws_rf = up_rules[rname], ws_rules[rname]
                up_map = dict(_parse_markdown_sections_map(up_rf.read_text("utf-8")))
                ws_map = dict(_parse_markdown_sections_map(ws_rf.read_text("utf-8")))
                in_sync = [h for h in up_map if h in ws_map and up_map[h] == ws_map[h]]
                up_only = [h for h in up_map if h not in ws_map]
                loc_only = [h for h in ws_map if h not in up_map]
                up_newer = up_rf.stat().st_mtime_ns > ws_rf.stat().st_mtime_ns
                diverged: list[dict[str, Any]] = []
                for h in [k for k in up_map if k in ws_map and up_map[k] != ws_map[k]]:
                    u_diff = difflib.unified_diff(
                        ws_map[h].splitlines(),
                        up_map[h].splitlines(),
                        fromfile="local",
                        tofile="upstream",
                        lineterm="",
                    )
                    d_dir = "upstream_newer" if up_newer else "local_newer"
                    d_prev = "\n".join(list(u_diff)[:MAX_DIFF_PREVIEW_LINES])
                    d_head = {"heading": h, "drift_direction": d_dir, "diff_preview": d_prev}
                    diverged.append({**d_head, "recommended_action": "review_and_merge_section"})
                if apply_upstream_only and up_only:
                    safe_applied.append(rel_file)
                    if not dry_run:
                        cur_txt = ws_rf.read_text(encoding="utf-8").rstrip()
                        extra = "".join(f"\n\n{h}\n\n{up_map[h]}" for h in up_only)
                        ws_rf.write_text(f"{cur_txt}{extra}\n", encoding="utf-8")
                has_diff = bool(up_only or loc_only or diverged)
                status = (
                    "in_sync" if not has_diff else ("diverged" if diverged else "section_additions")
                )
                act_alt = "adopt_upstream_sections" if up_only else "keep_local_or_promote"
                rec = (
                    "none"
                    if status == "in_sync"
                    else ("review_diverged_sections" if diverged else act_alt)
                )
                c_head = {"template": tpl, "rule_file": rel_file, "status": status}
                c_secs = {"in_sync_sections": in_sync, "upstream_only_sections": up_only}
                c_tail = {"local_only_sections": loc_only, "diverged_sections": diverged}
                file_comparisons.append({**c_head, **c_secs, **c_tail, "recommended_action": rec})

    n_up = sum(1 for f in file_comparisons if f["upstream_only_sections"])
    n_loc = sum(1 for f in file_comparisons if f["local_only_sections"])
    n_sync = sum(1 for f in file_comparisons if f["status"] == "in_sync")
    n_div = sum(1 for f in file_comparisons if f["diverged_sections"])
    s_head = {"files_compared": len(file_comparisons), "in_sync_files": n_sync}
    s_adds = {"files_with_upstream_additions": n_up, "files_with_local_customizations": n_loc}
    summary = {**s_head, **s_adds, "files_with_diverged_sections": n_div}
    u_dirs = {"workspace_dir": str(ws), "upstream_dir": str(up), "dry_run": dry_run}
    u_ids = {"layer_id": str(ws_m.get("layer_id", ws.name)), "template_filter": template_filter}
    u_up = {"upstream_layer_id": str(up_m.get("layer_id", up.name)), "summary": summary}
    u_ap = {"apply_upstream_only": apply_upstream_only, "safe_applied_files": safe_applied}
    return {**u_dirs, **u_ids, **u_up, **u_ap, "file_comparisons": file_comparisons}


def _build_bilateral_layer_report(
    ws: Path, ws_role: str, is_oss: bool, drifts: list[dict[str, Any]],
    child_drifts: list[dict[str, Any]], local_diff: dict[str, Any],
) -> dict[str, Any]:  # fmt: skip
    """Build 3-bucket level report (inbound_from_upstream, inbound_from_downstream, local)."""
    wt_txt = (ws / "WORKTASK.md").read_text("utf-8") if (ws / "WORKTASK.md").is_file() else ""
    main_wt, _sep, out_wt = wt_txt.partition("## Outbound Delegations")
    main_lines = [ln.strip() for ln in main_wt.splitlines() if ln.strip().startswith("- [")]
    out_lines = [ln.strip() for ln in out_wt.splitlines() if ln.strip().startswith("- [")]
    in_tasks = [ln for ln in main_lines if "Delegated from" in ln and not ln.startswith("- [x]")]
    loc_prog = [ln for ln in main_lines if ln.startswith("- [/]") and "Delegated from" not in ln]
    loc_pend = [ln for ln in main_lines if ln.startswith("- [ ]") and "Delegated from" not in ln]
    p_dir = ws / ".agents" / "proposals"
    all_from = sorted(p_dir.glob("from-*/*.md")) if p_dir.is_dir() else ()
    from_up = [
        str(p.relative_to(ws)).replace("\\", "/")
        for p in all_from
        if not (ws / "layers" / p.parent.name.removeprefix("from-")).is_dir()
    ]
    oss_auto = bool(is_oss and not _is_oss_root_manifest(_load_manifest_dict(ws)))
    up_rules = (
        []
        if oss_auto
        else [d["rule_file"] for d in drifts if d["drift_direction"] == "upstream_newer"]
    )
    in_up = {
        "oss_auto_sync_covered": oss_auto,
        "delegated_tasks": in_tasks,
        "staged_proposals": from_up,
        "upstream_rule_updates": up_rules,
        "action_needed": bool(in_tasks or from_up or up_rules),
    }
    to_here = [
        str(p.relative_to(ws)).replace("\\", "/")
        for p in (sorted(p_dir.glob("to-*/*.md")) if p_dir.is_dir() else ())
    ]
    comp_child = [ln for ln in out_lines if ln.startswith("- [x]")] + [
        p for p in to_here if "/completion-" in p
    ]
    for c_wt in sorted((ws / "layers").glob("*/WORKTASK.md")) if (ws / "layers").is_dir() else ():
        comp_child.extend(
            f"{c_wt.parent.name}: {ln.strip()}"
            for ln in c_wt.read_text("utf-8").splitlines()
            if ln.strip().startswith("- [x]") and "Delegated from" in ln
        )
    from_child = [
        str(p.relative_to(ws)).replace("\\", "/")
        for p in all_from
        if (ws / "layers" / p.parent.name.removeprefix("from-")).is_dir()
    ]
    in_layers_props = [
        str(cp.relative_to(ws)).replace("\\", "/")
        for cp in (
            sorted((ws / "layers").glob("*/.agents/proposals/**/*.md"))
            if (ws / "layers").is_dir()
            else ()
        )
        if not cp.parent.name.startswith("from-")
    ]
    child_props = list(
        dict.fromkeys(
            [*(p for p in to_here if "/completion-" not in p), *from_child, *in_layers_props]
        )
    )
    c_drift_ids = [str(d["layer_id"]) for d in child_drifts]
    in_down = {
        "completed_child_delegations": comp_child,
        "staged_child_proposals": child_props,
        "child_layer_drifts": c_drift_ids,
        "action_needed": bool(comp_child or child_props or c_drift_ids),
    }
    up_r = [d["rule_file"] for d in drifts if d["drift_direction"] == "workspace_newer"]
    mod_proj = [str(m["file"]) for m in local_diff["modified_in_project"]]
    mod_assets = list(dict.fromkeys([*up_r, *mod_proj, *local_diff["novel_in_project"]]))
    pend_cons = [ln for ln in main_lines if ln.startswith("- [ ]") and "GOVERNANCE DECISION:" in ln]
    loc_chg = {
        "tasks_in_progress": loc_prog,
        "tasks_pending": loc_pend,
        "pending_consensus_items": pend_cons,
        "outbound_delegations": out_lines,
        "modified_or_novel_assets": mod_assets,
        "has_local_changes": bool(loc_prog or out_lines or mod_assets or pend_cons),
    }
    return {
        "inbound_from_upstream": in_up,
        "inbound_from_downstream": in_down,
        "local_workspace_changes": loc_chg,
    }


def inspect_layer_horizon(
    repo_dir: Path, workspace_dir: Path, *, parent_dir: Path | None = None,
    actor_email: str | None = None,
) -> dict[str, Any]:  # fmt: skip
    """Inspect 1-hop downward propagation & quiet upward promotion candidates for a workspace."""
    ws, eff_p = workspace_dir.resolve(), _resolve_default_parent_dir(workspace_dir, parent_dir)
    up, oss = (eff_p or repo_dir).resolve(), repo_dir.resolve()
    ws_m, up_m = _load_manifest_dict(ws), _load_manifest_dict(up)
    oss_vf, up_vf, ws_vf = oss / "VERSION", up / "VERSION", ws / "VERSION"
    oss_ver = oss_vf.read_text(encoding="utf-8").strip() if oss_vf.is_file() else None
    up_ver = up_vf.read_text(encoding="utf-8").strip() if up_vf.is_file() else None
    ws_ver = ws_vf.read_text(encoding="utf-8").strip() if ws_vf.is_file() else None
    is_oss = _is_oss_root_manifest(up_m)
    contrib_dir = _resolve_oss_contrib_repo_dir(up) if is_oss else up
    eff_em = resolve_git_user_email(ws) if actor_email is None else actor_email.strip()
    role_prof = _resolve_hierarchical_actor_profile(ws, actor_email=eff_em, parent_dir=eff_p)
    a_kw: dict[str, Any] = {"operation": "release", "actor_email": actor_email,
        "parent_dir": eff_p, "record_blocked": False}  # fmt: skip
    auth_v = verify_layer_operation_authority(ws, **a_kw)
    up_auth_v = verify_layer_operation_authority(
        up, operation="release", actor_email=actor_email, record_blocked=False
    )
    ws_tpls = [name for name, _p in _iter_layer_template_dirs(ws)]
    cand_tpls = [*(str(x) for x in ws_m.get("default_stack_templates", [])), *ws_tpls]
    tpl_pairs = [
        (tpl, u_d, w_d)
        for tpl in dict.fromkeys(cand_tpls)
        if (u_d := _resolve_template_dir(up, tpl)) and (w_d := _resolve_template_dir(ws, tpl))
    ]
    drifts: list[dict[str, Any]] = []
    for tpl, up_tdir, ws_tdir in tpl_pairs:
        tj = ws_tdir / "template.json"
        raw_rec = (json.loads(tj.read_text("utf-8")) if tj.is_file() else {}).get(
            "reconciled_upstream_sha256"
        )
        rec_map: dict[str, Any] = raw_rec if isinstance(raw_rec, dict) else {}
        for ws_rf in sorted((ws_tdir / "rules").glob("*.md")):
            up_rf = up_tdir / "rules" / ws_rf.name
            if not up_rf.is_file() or _sha256_file(ws_rf) != _sha256_file(up_rf):
                rel_src = str(ws_rf.relative_to(ws)).replace("\\", "/")
                rec_sha = rec_map.get(ws_rf.name)
                up_newer = up_rf.is_file() and (
                    _sha256_file(up_rf) != rec_sha
                    if isinstance(rec_sha, str)
                    else up_rf.stat().st_mtime_ns > ws_rf.stat().st_mtime_ns
                )
                oss_ok = True
                try:
                    verify_oss_promotion_agnosticism(ws, ws_rf.read_text(encoding="utf-8"), rel_src)
                except ValueError:
                    oss_ok = False
                cmd = (
                    f"./scripts/layer-config.sh promote-from-project {ws} --source {rel_src} "
                    f"--to-template {tpl} --upstream-dir {contrib_dir} --create-pr"
                )
                d_dir = "upstream_newer" if up_newer else "workspace_newer"
                drifts.append({"template": tpl, "rule_file": rel_src, "oss_agnostic": oss_ok,
                    "promote_command": cmd, "drift_direction": d_dir})  # fmt: skip
    local_diff = diff_project_against_layers(ws, ws)
    child_drifts = _inspect_mounted_children_drifts(ws, ws_m.get("mounted_layers", []))
    sync_sfx = f" --parent-dir {up}" if eff_p is not None else ""
    up_drifts = [d for d in drifts if d["drift_direction"] == "workspace_newer"]
    miss_sk = any(
        not (w_d / sf.relative_to(u_d)).is_file()
        for _t, u_d, w_d in tpl_pairs
        for sf in (u_d / "skills").rglob("SKILL.md")
    )
    need_sync = (
        any(d["drift_direction"] == "upstream_newer" for d in drifts)
        or miss_sk
        or bool(child_drifts)
    )
    novel_cmds = [
        f"./scripts/layer-config.sh promote-from-project {ws} "
        f"--source .agents/{rel} --upstream-dir {contrib_dir} --create-pr"
        for rel in local_diff["novel_in_project"]
    ]
    ws_lid, up_lid = str(ws_m.get("layer_id", ws.name)), str(up_m.get("layer_id", up.name))
    ws_role = str(ws_m.get("layer_role", "project"))
    up_sugg: list[Any] = (
        [d for d in up_drifts if d["oss_agnostic"]]
        if is_oss
        else [*(d["promote_command"] for d in up_drifts), *novel_cmds]
    )
    l_rep = _build_bilateral_layer_report(ws, ws_role, is_oss, drifts, child_drifts, local_diff)
    return {"workspace_dir": str(ws), "layer_id": ws_lid, "layer_role": ws_role,
        "is_oss_community_horizon": is_oss, "actor_is_layer_owner": bool(auth_v["allowed"]),
        "actor_role_profile": role_prof, "immediate_upstream_dir": str(up),
        "actor_is_upstream_owner": bool(up_auth_v["allowed"]), "immediate_upstream_id": up_lid,
        "immediate_upstream_role": str(up_m.get("layer_role", "unknown")),
        "oss_contrib_dir": str(contrib_dir) if is_oss else None, "oss_root_version": oss_ver,
        "upstream_version": up_ver, "workspace_version": ws_ver,
        "downward_sync_needed": need_sync, "child_sync_needed": bool(child_drifts),
        "shared_template_drifts": drifts,
        "downward_sync_command": f"./scripts/layer-config.sh sync-layer {ws}{sync_sfx}",
        "downstream_layer_drifts": child_drifts, "upward_promotion_suggestions": up_sugg,
        "layer_report": l_rep}  # fmt: skip
