"""Task-branch workflow onboarding, upstream template diffing, and ephemeral consultation.

Specification: docs/architecture/04_compaction_surface_and_promotion_engines.md
"""

import difflib
import json
import re
import shutil
from pathlib import Path
from typing import Any

from dotfiles_mcp.constants import KEBAB_ID_RE, VALID_AGENT_TIERS
from dotfiles_mcp.ephemeral_fork_engine import reap_ephemeral_fork, spawn_ephemeral_fork
from dotfiles_mcp.manifest_helpers import (
    _iter_layer_template_dirs,
    _resolve_mounted_child_dir,
    _resolve_template_dir,
)
from dotfiles_mcp.tools_surface import SurfaceToolsMixin

VALID_TASK_TRACKERS: tuple[str, ...] = (
    "WORKTASK.md",
    "BACKLOG.md",
    "WORKROAD.md",
    "ROADMAP.md",
)
_TASK_LINE_RE = re.compile(r"^(\s*-\s*\[)([ /xX])(\]\s+)(.+)$")
_ACTIVE_TASK_SECTION_RE = re.compile(r"\n*## Active Task\n[\s\S]*$", re.MULTILINE)
_HEADING_RE = re.compile(r"^#{1,3}\s+.+$")


def _derive_branch_slug(task_text: str) -> str:
    """Derive a clean kebab-case branch slug from a markdown task description."""
    plain = re.sub(r"[*_`~]", "", task_text)
    plain = re.sub(r"Delegated from\s+[a-z0-9-]+\s*\([^)]*\)", "", plain, flags=re.IGNORECASE)
    tokens = [tok for tok in re.split(r"[^a-z0-9]+", plain.lower()) if tok]
    slug = "-".join(tokens[:7])[:48].strip("-")
    return slug or "work-item"


def start_task_workflow(
    workspace_dir: Path,
    *,
    task_query: str,
    tracker: str = "WORKTASK.md",
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

    m_path = ws / "system" / "mcp-layer.json"
    m_data = json.loads(m_path.read_text(encoding="utf-8")) if m_path.is_file() else {}
    manifest = m_data if isinstance(m_data, dict) else {}
    layer_id = str(manifest.get("layer_id", ws.name))
    layer_role = str(manifest.get("layer_role", "project"))

    lines = trk_file.read_text(encoding="utf-8").splitlines()
    match_idx: int | None = None
    matched_body = ""
    for idx, line in enumerate(lines):
        m = _TASK_LINE_RE.match(line)
        if m and clean_q.lower() in line.lower():
            match_idx = idx
            matched_body = m.group(4).strip()
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

    slug = _derive_branch_slug(matched_body)
    branch_name = f"task/{slug}"
    git_cmd = f"git checkout -b {branch_name}"
    session_rel = ".agents/SESSION.md"
    session_file = ws / session_rel

    if not dry_run:
        trk_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        session_file.parent.mkdir(parents=True, exist_ok=True)
        existing_session = (
            session_file.read_text(encoding="utf-8")
            if session_file.is_file()
            else "# Session State Log\n\n## Session Log\n\n- Initialized.\n"
        )
        cleaned_session = _ACTIVE_TASK_SECTION_RE.sub("", existing_session).rstrip()
        active_block = (
            f"\n\n## Active Task\n"
            f"- **Tracker**: `{tracker}`\n"
            f"- **Branch**: `{branch_name}`\n"
            f"- **Task**: {matched_body}\n"
        )
        session_file.write_text(cleaned_session + active_block, encoding="utf-8")

    return {
        "workspace_dir": str(ws),
        "layer_id": layer_id,
        "layer_role": layer_role,
        "tracker": tracker,
        "task_query": clean_q,
        "matched_task": matched_body,
        "task_status": "in_progress",
        "subtasks": subtasks,
        "branch_name": branch_name,
        "git_branch_command": git_cmd,
        "session_file": session_rel,
        "dry_run": dry_run,
    }


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
    cand_tpls = list(
        dict.fromkeys([*(str(x) for x in ws_m.get("default_stack_templates", [])), *ws_tpls])
    )
    if template_filter:
        clean_flt = template_filter.strip()
        cand_tpls = [t for t in cand_tpls if t == clean_flt]

    file_comparisons: list[dict[str, Any]] = []
    safe_applied: list[str] = []
    for tpl in cand_tpls:
        up_tdir = _resolve_template_dir(up, tpl)
        ws_tdir = _resolve_template_dir(ws, tpl)
        if up_tdir is None or ws_tdir is None:
            continue
        up_rules = {p.name: p for p in sorted((up_tdir / "rules").glob("*.md"))}
        ws_rules = {p.name: p for p in sorted((ws_tdir / "rules").glob("*.md"))}
        for rname in sorted(set(up_rules) | set(ws_rules)):
            up_rf, ws_rf = up_rules.get(rname), ws_rules.get(rname)
            rel_file = str((ws_rf or (ws_tdir / "rules" / rname)).relative_to(ws)).replace(
                "\\", "/"
            )
            if up_rf is not None and ws_rf is None:
                up_secs = [h for h, _b in _parse_markdown_sections_map(up_rf.read_text("utf-8"))]
                dest_rf = ws_tdir / "rules" / rname
                if apply_upstream_only:
                    safe_applied.append(rel_file)
                    if not dry_run:
                        dest_rf.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(up_rf, dest_rf)
                file_comparisons.append(
                    {
                        "template": tpl,
                        "rule_file": rel_file,
                        "status": "upstream_only_file",
                        "in_sync_sections": [],
                        "upstream_only_sections": up_secs,
                        "local_only_sections": [],
                        "diverged_sections": [],
                        "recommended_action": "adopt_upstream_file",
                    }
                )
            elif ws_rf is not None and up_rf is None:
                ws_secs = [h for h, _b in _parse_markdown_sections_map(ws_rf.read_text("utf-8"))]
                file_comparisons.append(
                    {
                        "template": tpl,
                        "rule_file": rel_file,
                        "status": "local_only_file",
                        "in_sync_sections": [],
                        "upstream_only_sections": [],
                        "local_only_sections": ws_secs,
                        "diverged_sections": [],
                        "recommended_action": "keep_local_or_promote",
                    }
                )
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
                    diff_lines = list(
                        difflib.unified_diff(
                            ws_map[h].splitlines(),
                            up_map[h].splitlines(),
                            fromfile="local",
                            tofile="upstream",
                            lineterm="",
                        )
                    )[:16]
                    diverged.append(
                        {
                            "heading": h,
                            "drift_direction": "upstream_newer" if up_newer else "local_newer",
                            "diff_preview": "\n".join(diff_lines),
                            "recommended_action": "review_and_merge_section",
                        }
                    )
                if apply_upstream_only and up_only:
                    safe_applied.append(rel_file)
                    if not dry_run:
                        cur_txt = ws_rf.read_text(encoding="utf-8").rstrip()
                        extra = "".join(f"\n\n{h}\n\n{up_map[h]}" for h in up_only)
                        ws_rf.write_text(f"{cur_txt}{extra}\n", encoding="utf-8")
                status = (
                    "in_sync"
                    if not (up_only or loc_only or diverged)
                    else ("diverged" if diverged else "section_additions")
                )
                rec = (
                    "none"
                    if status == "in_sync"
                    else (
                        "review_diverged_sections"
                        if diverged
                        else ("adopt_upstream_sections" if up_only else "keep_local_or_promote")
                    )
                )
                file_comparisons.append(
                    {
                        "template": tpl,
                        "rule_file": rel_file,
                        "status": status,
                        "in_sync_sections": in_sync,
                        "upstream_only_sections": up_only,
                        "local_only_sections": loc_only,
                        "diverged_sections": diverged,
                        "recommended_action": rec,
                    }
                )

    summary = {
        "files_compared": len(file_comparisons),
        "in_sync_files": sum(1 for f in file_comparisons if f["status"] == "in_sync"),
        "files_with_upstream_additions": sum(
            1 for f in file_comparisons if f["upstream_only_sections"]
        ),
        "files_with_local_customizations": sum(
            1 for f in file_comparisons if f["local_only_sections"]
        ),
        "files_with_diverged_sections": sum(1 for f in file_comparisons if f["diverged_sections"]),
    }
    return {
        "workspace_dir": str(ws),
        "upstream_dir": str(up),
        "layer_id": str(ws_m.get("layer_id", ws.name)),
        "upstream_layer_id": str(up_m.get("layer_id", up.name)),
        "template_filter": template_filter,
        "apply_upstream_only": apply_upstream_only,
        "dry_run": dry_run,
        "safe_applied_files": safe_applied,
        "summary": summary,
        "file_comparisons": file_comparisons,
    }


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
    clean_layer = target_layer.strip()
    if not KEBAB_ID_RE.match(clean_layer):
        raise ValueError(f"Invalid target_layer {target_layer!r}")
    clean_q = query.strip()
    if not clean_q:
        raise ValueError("query must be a non-empty string")
    clean_tier = model_tier.strip().lower() or "flash"
    if clean_tier not in VALID_AGENT_TIERS:
        raise ValueError(f"Invalid model_tier {model_tier!r}: must be one of {VALID_AGENT_TIERS}")
    clean_path = target_path.strip() or "corporate/policy.md"

    ws, root = workspace_dir.resolve(), repo_dir.resolve()
    layer_cands = [
        ws / "layers" / clean_layer,
        root / "layers" / clean_layer,
        _resolve_mounted_child_dir(ws, clean_layer),
        _resolve_mounted_child_dir(root, clean_layer),
        root if clean_layer == "root" else None,
    ]
    eval_root = next(
        (
            c.resolve()
            for c in layer_cands
            if c is not None and (c / "system/mcp-layer.json").is_file()
        ),
        None,
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
    spawned = spawn_ephemeral_fork(
        eval_root,
        base_manifest,
        bot_role=f"consult-{clean_layer}",
        mount_templates=mount_tpls,
        model_tier=clean_tier,
        access_mode="strictly-read-only",
        resolution="L2",
        dry_run=dry_run,
    )
    fork_dir = Path(str(spawned["fork_dir"]))
    node = SurfaceToolsMixin(repo_dir=fork_dir if not dry_run else eval_root, log_dir=None)
    q_resp = node._tool_query_governance_rules(
        {"query": clean_q, "resolution": "L1", "layer": "root"}
    )
    q_payload = json.loads(q_resp["content"][0]["text"])
    s_resp = node._tool_resolve_surface_governance(
        {
            "target_path": clean_path,
            "resolution_override": "L2",
            "resonance_key": str(spawned.get("session_resonance_key", "")),
            "include_capsules": True,
        }
    )
    s_payload = json.loads(s_resp["content"][0]["text"])
    if not dry_run:
        reap_ephemeral_fork(eval_root, fork_id=str(spawned["fork_id"]))

    q_matches = [
        {
            "section": str(m.get("section", "")),
            "file": str(m.get("file", "")),
            "excerpt": str(m.get("excerpt", "")),
            "capsule_token": str(m.get("capsule_token") or ""),
        }
        for m in q_payload.get("matches", [])[:5]
    ]
    caps = [m["capsule_token"] for m in q_matches if m["capsule_token"]]
    digest = {
        "channel_1_domain_state": {
            "target_layer": clean_layer,
            "layer_id": str(base_manifest.get("layer_id", eval_root.name)),
            "layer_role": str(base_manifest.get("layer_role", "department")),
            "precedence": int(base_manifest.get("precedence", 30)),
            "access_mode": "strictly-read-only",
        },
        "channel_2_affected_surface": {
            "target_path": clean_path,
            "inferred_plane": str(s_payload.get("inferred_plane", "domain")),
            "matched_bindings_count": len(s_payload.get("resolved_bindings", [])),
        },
        "channel_3_invariants_and_constraints": q_matches,
        "channel_4_actionable_delta": {
            "handback_contract": "4-channel-digest+rcap1",
            "match_count": int(q_payload.get("match_count", 0)),
            "capsule_tokens": caps,
        },
    }
    return {
        "workspace_dir": str(ws),
        "target_layer": clean_layer,
        "resolved_target_dir": str(eval_root),
        "ephemeral_fork_id": str(spawned["fork_id"]),
        "access_mode": "strictly-read-only",
        "model_tier": clean_tier,
        "query": clean_q,
        "target_path": clean_path,
        "auto_reaped": True,
        "dry_run": dry_run,
        "capsule_matches": q_matches,
        "four_channel_digest": digest,
    }
