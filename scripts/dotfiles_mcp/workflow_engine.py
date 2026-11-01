"""Task-branch workflow onboarding, upstream template diffing, and ephemeral consultation.

Specification: docs/architecture/04_compaction_surface_and_promotion_engines.md
"""

import difflib
import json
import re
import shutil
from pathlib import Path
from typing import Any

from dotfiles_mcp.authority_engine import verify_layer_operation_authority
from dotfiles_mcp.constants import (
    KEBAB_ID_RE,
    MAX_BRANCH_SLUG_CHARS,
    MAX_BRANCH_SLUG_TOKENS,
    MAX_CONSULT_MATCHES,
    MAX_DIFF_PREVIEW_LINES,
    VALID_AGENT_TIERS,
    VALID_TRACKER_FILES,
)
from dotfiles_mcp.ephemeral_fork_engine import reap_ephemeral_fork, spawn_ephemeral_fork
from dotfiles_mcp.git_governance_engine import stage_non_destructive_proposal
from dotfiles_mcp.manifest_helpers import (
    _iter_layer_template_dirs,
    _resolve_mounted_child_dir,
    _resolve_template_dir,
)
from dotfiles_mcp.tools_surface import SurfaceToolsMixin

VALID_TASK_TRACKERS: tuple[str, ...] = VALID_TRACKER_FILES
_TASK_LINE_RE = re.compile(r"^(\s*-\s*\[)([ /xX])(\]\s+)(.+)$")
_ACTIVE_TASK_SECTION_RE = re.compile(r"\n*## Active Task\n[\s\S]*$", re.MULTILINE)
_HEADING_RE = re.compile(r"^#{1,3}\s+.+$")
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
    m_path = ws / "system" / "mcp-layer.json"
    m_raw = json.loads(m_path.read_text(encoding="utf-8")) if m_path.is_file() else {}
    m = m_raw if isinstance(m_raw, dict) else {}
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

    out: dict[str, Any] = {"workspace_dir": str(ws), "layer_id": layer_id, "layer_role": layer_role}
    out.update(tracker=tracker, task_query=clean_q, ticket_id=eff_ticket, origin_layer_id=origin_id)
    out.update(matched_task=matched_body, task_status="in_progress", subtasks=subtasks)
    out.update(branch_name=branch_name, git_branch_command=git_cmd, session_file=session_rel)
    out["dry_run"] = dry_run
    return out


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
            res_parent, operation="release", actor_email=actor_email
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
            }
            stg_kw.update(content=comp_line, operation="complete-task", dry_run=dry_run)
            stg_kw.update(actor_email=actor_email or "", reason_code="UPWARD_COMPLETION_RECEIPT")
            staged_receipt = str(stage_non_destructive_proposal(ws, **stg_kw))

    branch_name = f"feature/{eff_ticket}-completed"
    commit_msg = f"feat(governance): complete {eff_ticket} in {layer_id} and report upward"
    t_repo = str(res_parent or ws)
    pr_cmds = [
        f"cd {t_repo} && git checkout -b {branch_name}",
        f"cd {t_repo} && git add WORKTASK.md && git commit -m {json.dumps(commit_msg)}",
        f"cd {t_repo} && git push -u origin {branch_name}",
    ]
    out_c: dict[str, Any] = {"workspace_dir": str(ws), "layer_id": layer_id, "dry_run": dry_run}
    out_c.update(ticket_id=eff_ticket, origin_layer_id=origin_id, task_status="completed")
    out_c.update(deliverable=deliverable.strip(), parent_tracker_updated=parent_updated)
    out_c["staged_completion_receipt"] = staged_receipt
    out_c["completion_pr_plan"] = {"branch_name": branch_name, "git_pr_commands": pr_cmds}
    return out_c


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
                c_item: dict[str, Any] = {"template": tpl, "rule_file": rel_file}
                c_item.update(status="upstream_only_file", in_sync_sections=[])
                c_item.update(upstream_only_sections=up_secs, local_only_sections=[])
                c_item.update(diverged_sections=[], recommended_action="adopt_upstream_file")
                file_comparisons.append(c_item)
            elif ws_rf is not None and up_rf is None:
                ws_secs = [h for h, _b in _parse_markdown_sections_map(ws_rf.read_text("utf-8"))]
                c_item = {"template": tpl, "rule_file": rel_file, "status": "local_only_file"}
                c_item.update(in_sync_sections=[], upstream_only_sections=[])
                c_item.update(local_only_sections=ws_secs, diverged_sections=[])
                c_item["recommended_action"] = "keep_local_or_promote"
                file_comparisons.append(c_item)
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
                    d_rec: dict[str, Any] = {"heading": h, "drift_direction": d_dir}
                    d_rec.update(diff_preview="\n".join(list(u_diff)[:MAX_DIFF_PREVIEW_LINES]))
                    d_rec["recommended_action"] = "review_and_merge_section"
                    diverged.append(d_rec)
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
                c_item = {"template": tpl, "rule_file": rel_file, "status": status}
                c_item.update(in_sync_sections=in_sync, upstream_only_sections=up_only)
                c_item.update(local_only_sections=loc_only, diverged_sections=diverged)
                c_item["recommended_action"] = rec
                file_comparisons.append(c_item)

    n_up = sum(1 for f in file_comparisons if f["upstream_only_sections"])
    n_loc = sum(1 for f in file_comparisons if f["local_only_sections"])
    summary: dict[str, Any] = {"files_compared": len(file_comparisons)}
    summary["in_sync_files"] = sum(1 for f in file_comparisons if f["status"] == "in_sync")
    summary.update(files_with_upstream_additions=n_up, files_with_local_customizations=n_loc)
    summary["files_with_diverged_sections"] = sum(
        1 for f in file_comparisons if f["diverged_sections"]
    )
    out_u: dict[str, Any] = {"workspace_dir": str(ws), "upstream_dir": str(up), "dry_run": dry_run}
    out_u.update(layer_id=str(ws_m.get("layer_id", ws.name)), template_filter=template_filter)
    out_u.update(upstream_layer_id=str(up_m.get("layer_id", up.name)), summary=summary)
    out_u.update(apply_upstream_only=apply_upstream_only, safe_applied_files=safe_applied)
    out_u["file_comparisons"] = file_comparisons
    return out_u


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
    sp_kw: dict[str, Any] = {"bot_role": f"consult-{clean_layer}", "mount_templates": mount_tpls}
    sp_kw.update(model_tier=clean_tier, access_mode="strictly-read-only", resolution="L2")
    spawned = spawn_ephemeral_fork(eval_root, base_manifest, dry_run=dry_run, **sp_kw)
    node_dir = Path(str(spawned["fork_dir"])) if not dry_run else eval_root
    node = SurfaceToolsMixin(repo_dir=node_dir, log_dir=None)
    q_resp = node._tool_query_governance_rules(
        {"query": clean_q, "resolution": "L1", "layer": "root"}
    )
    q_payload = json.loads(q_resp["content"][0]["text"])
    s_kw = {"target_path": clean_path, "resolution_override": "L2", "include_capsules": True}
    s_kw["resonance_key"] = str(spawned.get("session_resonance_key", ""))
    s_payload = json.loads(node._tool_resolve_surface_governance(s_kw)["content"][0]["text"])
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
    ch1: dict[str, Any] = {"target_layer": clean_layer, "access_mode": "strictly-read-only"}
    ch1.update(layer_id=str(base_manifest.get("layer_id", eval_root.name)))
    ch1.update(layer_role=str(base_manifest.get("layer_role", "department")))
    ch1["precedence"] = int(base_manifest.get("precedence", 30))
    ch2: dict[str, Any] = {"target_path": clean_path}
    ch2["inferred_plane"] = str(s_payload.get("inferred_plane", "domain"))
    ch2["matched_bindings_count"] = len(s_payload.get("resolved_bindings", []))
    ch4: dict[str, Any] = {"handback_contract": "4-channel-digest+rcap1", "capsule_tokens": caps}
    ch4["match_count"] = int(q_payload.get("match_count", 0))
    digest: dict[str, Any] = {"channel_1_domain_state": ch1, "channel_2_affected_surface": ch2}
    digest.update(channel_3_invariants_and_constraints=q_matches, channel_4_actionable_delta=ch4)
    out_e: dict[str, Any] = {"workspace_dir": str(ws), "target_layer": clean_layer}
    out_e.update(resolved_target_dir=str(eval_root), ephemeral_fork_id=str(spawned["fork_id"]))
    out_e.update(access_mode="strictly-read-only", model_tier=clean_tier, query=clean_q)
    out_e.update(target_path=clean_path, auto_reaped=True, dry_run=dry_run)
    out_e.update(capsule_matches=q_matches, four_channel_digest=digest)
    return out_e
