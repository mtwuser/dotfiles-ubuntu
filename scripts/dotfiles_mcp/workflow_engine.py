"""Task-branch workflow onboarding and ephemeral consultation engine.

Specification: docs/architecture/04_compaction_surface_and_promotion_engines.md
"""

import json
import re
from pathlib import Path
from typing import Any

from dotfiles_mcp.authority_engine import verify_layer_operation_authority
from dotfiles_mcp.constants import (
    KEBAB_ID_RE,
    MAX_BRANCH_SLUG_CHARS,
    MAX_BRANCH_SLUG_TOKENS,
    MAX_CONSULT_MATCHES,
    ROLE_DEFAULT_PRECEDENCE,
    VALID_AGENT_TIERS,
    VALID_DELEGATION_DIRS,
    VALID_DELEGATION_SURFACES,
    VALID_TRACKER_FILES,
)
from dotfiles_mcp.ephemeral_fork_engine import reap_ephemeral_fork, spawn_ephemeral_fork
from dotfiles_mcp.git_governance_engine import stage_non_destructive_proposal
from dotfiles_mcp.layer_topology_helpers import _resolve_mounted_child_dir
from dotfiles_mcp.manifest_helpers import (
    _ensure_rule_file_frontmatter,
    _load_manifest_dict,
    _resolve_template_dir,
)
from dotfiles_mcp.tools_surface import SurfaceToolsMixin

VALID_TASK_TRACKERS: tuple[str, ...] = VALID_TRACKER_FILES
_TASK_LINE_RE = re.compile(r"^(\s*-\s*\[)([ /xX])(\]\s+)(.+)$")
_ACTIVE_TASK_SECTION_RE = re.compile(r"\n*## Active Task\n[\s\S]*$", re.MULTILINE)
_TICKET_ID_RE = re.compile(r"\b([A-Z]{2,12}-[A-Z0-9-]{1,20})\b")


def _derive_branch_slug(task_text: str, *, strip_ticket: str = "") -> str:
    """Derive a clean kebab-case branch slug from a markdown task description."""
    plain = re.sub(r"[*_`~]", "", task_text)
    plain = re.sub(r"Delegated from\s+[a-z0-9-]+\s*\([^)]*\)", "", plain, flags=re.IGNORECASE)
    if strip_ticket:
        plain = re.sub(rf"\b{re.escape(strip_ticket)}\b", "", plain, flags=re.IGNORECASE)
        plain = re.sub(r"^\s*\[?\s*P[012]\s*·?\s*\]?\s*:?\s*", "", plain, flags=re.IGNORECASE)
    tokens = [tok for tok in re.split(r"[^a-z0-9]+", plain.lower()) if tok]
    slug = "-".join(tokens[:MAX_BRANCH_SLUG_TOKENS])[:MAX_BRANCH_SLUG_CHARS].strip("-")
    return slug or "work-item"


def _load_ws_manifest(ws: Path) -> tuple[dict[str, Any], str, str]:
    m = _load_manifest_dict(ws)
    return m, str(m.get("layer_id", ws.name)), str(m.get("layer_role", "project"))


def start_task_workflow(
    workspace_dir: Path,
    *,
    task_query: str,
    tracker: str = "WORKTASK.md",
    ticket_id: str | None = None,
    branch_prefix: str = "feature",
    dry_run: bool = False,
) -> dict[str, Any]:
    """Claim a task in <tracker>, mark it [/], update SESSION.md, and return branch metadata."""
    clean_q = task_query.strip()
    if not clean_q:
        raise ValueError("task_query must be a non-empty string")
    if tracker not in VALID_TASK_TRACKERS:
        raise ValueError(f"Invalid tracker {tracker!r}: must be one of {VALID_TASK_TRACKERS}")
    ws = workspace_dir.resolve()
    trk_file = ws / tracker
    if not trk_file.is_file():
        raise ValueError(f"Tracker file not found: {trk_file}")
    _manifest, layer_id, layer_role = _load_ws_manifest(ws)

    lines = trk_file.read_text(encoding="utf-8").splitlines()
    match_idx, matched_body = None, ""
    for idx, line in enumerate(lines):
        if (m := _TASK_LINE_RE.match(line)) and clean_q.lower() in line.lower():
            match_idx, matched_body = idx, m.group(4).strip()
            lines[idx] = f"{m.group(1)}/{m.group(3)}{matched_body}"
            break
    if match_idx is None:
        raise ValueError(f"No task matching {clean_q!r} found in {tracker}")

    subtasks: list[str] = []
    for sub_line in lines[match_idx + 1 :]:
        if sub_line.startswith(("  ", "\t")) and sub_line.strip():
            subtasks.append(sub_line.strip())
        elif sub_line.strip():
            break

    t_m = _TICKET_ID_RE.search(matched_body)
    eff_ticket = (ticket_id or "").strip().upper() or (t_m.group(1) if t_m else "")
    o_m = re.search(r"Delegated from\s+`?([a-z0-9-]+)`?", matched_body, re.IGNORECASE)
    origin_id = o_m.group(1) if o_m else ""
    slug = _derive_branch_slug(matched_body, strip_ticket=eff_ticket)
    pfx = branch_prefix.strip().strip("/") or "feature"
    branch_name = f"{pfx}/{eff_ticket}-{slug}" if eff_ticket else f"{pfx}/{slug}"
    git_cmd, session_rel = f"git checkout -b {branch_name}", ".agents/SESSION.md"
    session_file = ws / session_rel
    if not dry_run:
        trk_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        session_file.parent.mkdir(parents=True, exist_ok=True)
        def_s = "# Session State Log\n\n## Session Log\n\n- Initialized.\n"
        existing = session_file.read_text(encoding="utf-8") if session_file.is_file() else def_s
        cleaned = _ACTIVE_TASK_SECTION_RE.sub("", existing).rstrip()
        active_block = (
            f"\n\n## Active Task\n- **Tracker**: `{tracker}`\n"
            f"- **Ticket ID**: `{eff_ticket or 'unassigned'}`\n"
            f"- **Origin Layer**: `{origin_id or layer_id}`\n"
            f"- **Branch**: `{branch_name}`\n- **Task**: {matched_body}\n"
        )
        session_file.write_text(cleaned + active_block, encoding="utf-8")

    out_id = {"workspace_dir": str(ws), "layer_id": layer_id, "layer_role": layer_role}
    out_tk = {"tracker": tracker, "task_query": clean_q, "ticket_id": eff_ticket}
    out_st = {
        "origin_layer_id": origin_id,
        "matched_task": matched_body,
        "task_status": "in_progress",
    }
    out_br = {"subtasks": subtasks, "branch_name": branch_name, "git_branch_command": git_cmd}
    return {**out_id, **out_tk, **out_st, **out_br, "session_file": session_rel, "dry_run": dry_run}


def complete_task_workflow(
    workspace_dir: Path,
    *,
    task_query: str,
    deliverable: str = "",
    summary: str = "",
    tracker: str = "WORKTASK.md",
    parent_dir: Path | None = None,
    actor_email: str | None = None,
    create_pr: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Mark a task [x] in <tracker> and report reciprocal completion upward to the parent layer."""
    clean_q = task_query.strip()
    if not clean_q:
        raise ValueError("task_query must be a non-empty string")
    if tracker not in VALID_TASK_TRACKERS:
        raise ValueError(f"Invalid tracker {tracker!r}: must be one of {VALID_TASK_TRACKERS}")
    ws = workspace_dir.resolve()
    trk_file = ws / tracker
    if not trk_file.is_file():
        raise ValueError(f"Tracker file not found: {trk_file}")
    manifest, layer_id, _role = _load_ws_manifest(ws)
    up_cfg = manifest.get("upstream_layer")
    up_id_default = str(up_cfg.get("layer_id", "")) if isinstance(up_cfg, dict) else ""

    lines = trk_file.read_text(encoding="utf-8").splitlines()
    match_idx, matched_body = None, ""
    deliv_sfx = f" *(Deliverable: `{deliverable.strip()}`)*" if deliverable.strip() else ""
    for idx, line in enumerate(lines):
        if (m := _TASK_LINE_RE.match(line)) and clean_q.lower() in line.lower():
            match_idx, matched_body = idx, m.group(4).strip()
            new_b = matched_body if deliv_sfx in matched_body else f"{matched_body}{deliv_sfx}"
            lines[idx] = f"{m.group(1)}x{m.group(3)}{new_b}"
            break
    if match_idx is None:
        raise ValueError(f"No task matching {clean_q!r} found in {tracker}")
    if not dry_run:
        trk_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    t_m = _TICKET_ID_RE.search(matched_body)
    eff_ticket = t_m.group(1) if t_m else clean_q.upper()
    o_m = re.search(r"Delegated from\s+`?([a-z0-9-]+)`?", matched_body, re.IGNORECASE)
    origin_id = o_m.group(1) if o_m else up_id_default
    res_parent = (
        parent_dir.resolve()
        if parent_dir
        else (_resolve_mounted_child_dir(ws, origin_id) if origin_id else None)
    )
    parent_updated, staged_receipt = False, None
    comp_line = (
        f"- [x] **[{eff_ticket} -> `{layer_id}` (`{tracker}`, stage: `completed (pro)`)]**: "
        f"{summary.strip() or matched_body}{deliv_sfx}"
    )
    if res_parent is not None and res_parent.is_dir():
        auth_ok = verify_layer_operation_authority(
            res_parent, operation="release", actor_email=actor_email, record_blocked=False
        )["allowed"]
        if auth_ok and not create_pr:
            parent_updated, p_wt = True, res_parent / "WORKTASK.md"
            if not dry_run:
                p_txt = p_wt.read_text("utf-8") if p_wt.is_file() else f"# Tasks — {origin_id}\n"
                p_lines, replaced = p_txt.splitlines(), False
                for i, pl in enumerate(p_lines):
                    if eff_ticket.lower() in pl.lower() and "->" in pl:
                        p_lines[i], replaced = comp_line, True
                        break
                if replaced:
                    p_wt.write_text("\n".join(p_lines) + "\n", encoding="utf-8")
                else:
                    p_hdr = "## Outbound Delegations"
                    p_base = p_txt.rstrip() if p_hdr in p_txt else f"{p_txt.rstrip()}\n\n{p_hdr}"
                    p_wt.write_text(f"{p_base}\n{comp_line}\n", encoding="utf-8")
        else:
            stg_kw: dict[str, Any] = {
                "scope_tag": f"to-{origin_id or res_parent.name}",
                "file_name": f"completion-{eff_ticket.lower()}.md",
                "content": comp_line,
                "operation": "complete-task",
                "dry_run": dry_run,
                "actor_email": actor_email or "",
                "reason_code": "UPWARD_COMPLETION_RECEIPT",
            }
            staged_receipt = str(stage_non_destructive_proposal(ws, **stg_kw))

    branch_name = f"feature/{eff_ticket}-completed"
    commit_msg = f"feat(governance): complete {eff_ticket} in {layer_id} and report upward"
    t_repo = str(res_parent or ws)
    pr_cmds = [
        f"cd {t_repo} && git checkout -b {branch_name}",
        f"cd {t_repo} && git add WORKTASK.md && git commit -m {json.dumps(commit_msg)}",
        f"cd {t_repo} && git push -u origin {branch_name}",
    ]
    c_id = {"workspace_dir": str(ws), "layer_id": layer_id, "dry_run": dry_run}
    c_tk = {"ticket_id": eff_ticket, "origin_layer_id": origin_id, "task_status": "completed"}
    c_dl = {"deliverable": deliverable.strip(), "parent_tracker_updated": parent_updated}
    c_pr = {"branch_name": branch_name, "git_pr_commands": pr_cmds}
    c_rec = {"staged_completion_receipt": staged_receipt, "completion_pr_plan": c_pr}
    return {**c_id, **c_tk, **c_dl, **c_rec}


def consult_layer_ephemeral(
    repo_dir: Path,
    workspace_dir: Path,
    *,
    target_layer: str,
    query: str,
    target_path: str = "corporate/policy.md",
    model_tier: str = "flash",
    dry_run: bool = False,
) -> dict[str, Any]:
    """Run a zero-residue, one-shot strictly-read-only ephemeral consultation against a layer."""
    clean_layer, clean_q = target_layer.strip(), query.strip()
    if not KEBAB_ID_RE.match(clean_layer):
        raise ValueError(f"Invalid target_layer {target_layer!r}")
    if not clean_q:
        raise ValueError("query must be a non-empty string")
    clean_tier = model_tier.strip().lower() or "flash"
    clean_path = target_path.strip() or "corporate/policy.md"
    if clean_tier not in VALID_AGENT_TIERS:
        raise ValueError(f"Invalid model_tier {model_tier!r}: must be one of {VALID_AGENT_TIERS}")

    ws, root = workspace_dir.resolve(), repo_dir.resolve()
    layer_cands = [
        ws / "layers" / clean_layer,
        root / "layers" / clean_layer,
        _resolve_mounted_child_dir(ws, clean_layer),
        _resolve_mounted_child_dir(root, clean_layer),
        root if clean_layer == "root" else None,
    ]
    eval_root = next(
        (c.resolve() for c in layer_cands if c and (c / "system/mcp-layer.json").is_file()), None
    )
    mount_tpls: list[str] | None = None
    if eval_root is None:
        tpl_host = next(
            (
                h
                for h in (ws, root)
                if _resolve_template_dir(h, clean_layer) and (h / "system/mcp-layer.json").is_file()
            ),
            None,
        )
        if tpl_host is not None:
            eval_root, mount_tpls = tpl_host, [clean_layer]
    if eval_root is None:
        raise ValueError(f"Target layer or template not found: {clean_layer!r}")

    base_manifest = json.loads((eval_root / "system/mcp-layer.json").read_text(encoding="utf-8"))
    sp_cfg: dict[str, Any] = {"bot_role": f"consult-{clean_layer}", "mount_templates": mount_tpls}
    sp_mode: dict[str, Any] = {"model_tier": clean_tier, "access_mode": "strictly-read-only"}
    sp_sc: dict[str, Any] = {"ephemeral_scope": "inter-layer", "resolution": "L2"}
    spawned = spawn_ephemeral_fork(
        eval_root, base_manifest, dry_run=dry_run, **sp_cfg, **sp_mode, **sp_sc
    )
    res_key = str(spawned["session_resonance_key"])
    node_dir = Path(str(spawned["fork_dir"])) if not dry_run else eval_root
    node = SurfaceToolsMixin(repo_dir=node_dir, log_dir=None)
    q_resp = node._tool_query_governance_rules(
        {"query": clean_q, "resolution": "L1", "layer": "root", "resonance_key": res_key}
    )
    q_payload = json.loads(q_resp["content"][0]["text"])
    s_kw = {"target_path": clean_path, "resolution_override": "L2", "include_capsules": True}
    s_all = {**s_kw, "resonance_key": res_key}
    s_payload = json.loads(node._tool_resolve_surface_governance(s_all)["content"][0]["text"])
    if not dry_run:
        reap_ephemeral_fork(eval_root, fork_id=str(spawned["fork_id"]))

    q_matches = [
        {
            "section": str(m.get("section", "")),
            "file": str(m.get("file", "")),
            "excerpt": str(m.get("excerpt", "")),
            "capsule_token": str(m.get("capsule_token") or ""),
        }
        for m in q_payload.get("matches", [])[:MAX_CONSULT_MATCHES]
    ]
    caps = [m["capsule_token"] for m in q_matches if m["capsule_token"]]
    dept_prec = int(base_manifest.get("precedence", ROLE_DEFAULT_PRECEDENCE["department"]))
    ch1_id = {"target_layer": clean_layer, "access_mode": "strictly-read-only"}
    ch1_role = {"layer_id": str(base_manifest.get("layer_id", eval_root.name))}
    ch1_r2 = {"layer_role": str(base_manifest.get("layer_role", "department"))}
    ch1 = {**ch1_id, **ch1_role, **ch1_r2, "precedence": dept_prec}
    inf_plane = str(s_payload.get("inferred_plane", "domain"))
    ch2_p = {"target_path": clean_path, "inferred_plane": inf_plane}
    ch2 = {**ch2_p, "matched_bindings_count": len(s_payload.get("resolved_bindings", []))}
    ch4_c = {"handback_contract": "4-channel-digest+rcap1", "capsule_tokens": caps}
    ch4 = {**ch4_c, "match_count": int(q_payload.get("match_count", 0))}
    d_head = {"channel_1_domain_state": ch1, "channel_2_affected_surface": ch2}
    d_tail = {"channel_3_invariants_and_constraints": q_matches, "channel_4_actionable_delta": ch4}
    digest = {**d_head, **d_tail}
    out_head = {"workspace_dir": str(ws), "target_layer": clean_layer}
    out_fork = {"resolved_target_dir": str(eval_root), "ephemeral_fork_id": str(spawned["fork_id"])}
    out_mode = {"access_mode": "strictly-read-only", "model_tier": clean_tier, "query": clean_q}
    out_flags = {"target_path": clean_path, "auto_reaped": True, "dry_run": dry_run}
    out_res = {"capsule_matches": q_matches, "four_channel_digest": digest}
    return {**out_head, **out_fork, **out_mode, **out_flags, **out_res}


def delegate_directive_to_child(
    workspace_dir: Path, *, child_layer: str, directive: str = "",
    source_rel_path: str | None = None, ticket_id: str | None = None, priority: str = "P1",
    tracker: str = "WORKTASK.md", actor_email: str | None = None, force_overwrite: bool = False,
    create_pr: bool = False, dry_run: bool = False,
) -> dict[str, Any]:  # fmt: skip
    """Delegate a 1-hop downward directive or governance artifact into layers/<child>/<tracker>."""
    clean_child, clean_dir = child_layer.strip(), directive.strip()
    if not KEBAB_ID_RE.match(clean_child):
        raise ValueError(f"Invalid child_layer {child_layer!r}: must be kebab-case")
    if priority not in ("P0", "P1", "P2"):
        raise ValueError(f"Invalid priority {priority!r}: must be P0, P1, or P2")
    if tracker not in VALID_DELEGATION_SURFACES:
        raise ValueError(
            f"Invalid tracker/surface {tracker!r}: must be in {VALID_DELEGATION_SURFACES}"
        )
    ws, src_file, src_body = workspace_dir.resolve(), None, ""
    if source_rel_path:
        src_file = (ws / source_rel_path.strip().lstrip("/")).resolve()
        if not src_file.is_relative_to(ws) or not src_file.is_file():
            raise ValueError(f"Invalid or missing source_rel_path: {source_rel_path!r}")
        src_body = src_file.read_text(encoding="utf-8").strip()
    if not clean_dir and not src_body:
        raise ValueError("directive must be a non-empty string or source_rel_path must be provided")
    verdict = verify_layer_operation_authority(
        ws, operation="delegate-to-child", actor_email=actor_email
    )
    if not verdict["allowed"]:
        raise ValueError(f"DELEGATION_AUTHORITY_DENIED: {verdict['remediation']}")
    mnt_dir = ws / "layers" / clean_child
    cand_dir = mnt_dir if mnt_dir.is_dir() else _resolve_mounted_child_dir(ws, clean_child)
    tdir = cand_dir if cand_dir is not None and cand_dir.is_relative_to(ws) else None
    if tdir is None:
        raise ValueError(f"Target 1-hop child layer not found: {clean_child!r}")
    m = _load_manifest_dict(ws)
    pid, prole = str(m.get("layer_id", ws.name)), str(m.get("layer_role", "corporate"))
    pprec = int(m.get("precedence", ROLE_DEFAULT_PRECEDENCE["corporate"]))
    eff_text = clean_dir or f"Delivered `{src_file.name if src_file else tracker}`"
    t_match = re.search(r"\b([A-Z]{2,12}-[A-Z0-9-]{2,20})\b", eff_text)
    eff_ticket = (ticket_id or "").strip().upper() or (
        t_match.group(1) if t_match else f"{pid.upper()}-{clean_child.upper()}-01"
    )
    entry = (
        f"- [ ] **[{priority} · {eff_ticket} · Delegated from `{pid}` (`{prole}`, "
        f"`precedence: {pprec}`)]**: {eff_text}"
    )
    def_fn = f"{eff_ticket.lower()}.md" if tracker in VALID_TRACKER_FILES else "delegated-item.md"
    fname, updated, staged = src_file.name if src_file is not None else def_fn, [], []
    stg_kw: dict[str, Any] = {"scope_tag": f"from-{pid}", "file_name": fname, "dry_run": dry_run,
        "operation": "delegate-to-child", "actor_email": actor_email or ""}  # fmt: skip
    c_auth = verify_layer_operation_authority(
        tdir, operation="delegate-to-child", actor_email=actor_email, record_blocked=False
    )
    is_child_owner = bool(c_auth["allowed"]) and not create_pr
    if not is_child_owner:
        p_body = src_body or (f"# {eff_text}\n" if tracker == "rules" else entry)
        p_stg = stage_non_destructive_proposal(
            tdir, content=p_body, reason_code="CROSS_OWNER_CHILD_DELEGATION", **stg_kw
        )
        staged.append(str(p_stg))
    elif tracker == "rules":
        ctpl = str(_load_manifest_dict(tdir).get("layer_id") or clean_child)
        r_dest, r_body = tdir / "templates" / ctpl / "rules" / fname, src_body or f"# {eff_text}\n"
        if r_dest.is_file() and not force_overwrite:
            staged.append(str(stage_non_destructive_proposal(tdir, content=r_body, **stg_kw)))
        else:
            for rp in (r_dest, tdir / ".agents/rules" / fname):
                updated.append(str(rp))
                if not dry_run:
                    rp.parent.mkdir(parents=True, exist_ok=True)
                    rp.write_text(f"{r_body.rstrip()}\n", encoding="utf-8")
                    _ensure_rule_file_frontmatter(rp, sync_in_place=True)
    elif tracker in VALID_DELEGATION_DIRS:
        tfile = tdir / tracker / fname
        hdr = f"> **Delivered from**: `{pid}` (`{prole}`, `precedence: {pprec}`)"
        hdr_body = f"{hdr}\n\n{src_body or eff_text}"
        if tfile.is_file() and not force_overwrite:
            staged.append(str(stage_non_destructive_proposal(tdir, content=hdr_body, **stg_kw)))
        else:
            updated.append(str(tfile))
            if not dry_run:
                tfile.parent.mkdir(parents=True, exist_ok=True)
                tfile.write_text(f"{hdr_body}\n", encoding="utf-8")
    else:
        tfile = tdir / tracker
        updated.append(str(tfile))
        if not dry_run:
            def_h = f"# Active Work Tasks — {clean_child}\n\n"
            cur = tfile.read_text("utf-8") if tfile.is_file() else def_h
            blk = f"{entry}\n\n{src_body}" if (src_body and clean_dir) else entry
            if entry not in cur:
                tfile.write_text(f"{cur}{'' if cur.endswith('\n') else '\n'}{blk}\n", "utf-8")
    p_wt, p_hdr = ws / "WORKTASK.md", "## Outbound Delegations"
    p_entry = (
        f"- [/] **[{eff_ticket} -> `{clean_child}` (`{tracker}`, stage: `delegated`)]**: {eff_text}"
    )
    if not dry_run:
        p_cur = p_wt.read_text("utf-8") if p_wt.is_file() else f"# Active Work Tasks — {pid}\n"
        p_base = p_cur.rstrip() if p_hdr in p_cur else f"{p_cur.rstrip()}\n\n{p_hdr}"
        if p_entry not in p_base:
            p_wt.write_text(f"{p_base}\n{p_entry}\n", encoding="utf-8")
    if src_file is not None and src_file.name in VALID_TRACKER_FILES:
        note = f"- *Delivered to `{clean_child}` (`{tracker}`)*"
        if not dry_run and note not in src_body:
            src_file.write_text(f"{src_body}\n{note}\n", encoding="utf-8")
    c_br = next(
        (str(e.get("branch") or "master") for e in (m.get("mounted_layers") or [])
            if isinstance(e, dict) and e.get("name") in (clean_child, tdir.name)),
        "master",
    )  # fmt: skip
    deliv_mode = "direct_subtree" if (is_child_owner and not staged) else "proposal_pr"
    push_br = c_br if deliv_mode == "direct_subtree" else f"delegate/{eff_ticket.lower()}"
    return {"parent_layer_id": pid, "parent_layer_role": prole, "dry_run": dry_run,
        "child_layer": clean_child, "ticket_id": eff_ticket, "priority": priority,
        "tracker": tracker, "delivery_mode": deliv_mode,
        "actor_is_child_owner": bool(c_auth["allowed"]),
        "subtree_push_command": f"./scripts/layer-subtree.sh push {tdir.name} {push_br}",
        "delegated_entry": entry, "parent_ledger_entry": p_entry,
        "updated_paths": updated, "staged_proposals": staged}  # fmt: skip
