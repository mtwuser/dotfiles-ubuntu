"""Role & identity authority enforcement, 1-hop delegation, and upward PR promotion planner.

Specification: docs/architecture/04_compaction_surface_and_promotion_engines.md
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from fnmatch import fnmatchcase
from pathlib import Path
from typing import Any

from dotfiles_mcp.constants import (
    AGENTS_RULES_PREFIX,
    AGENTS_SKILLS_PREFIX,
    CONSUMER_ALLOWED_OPS,
    GENERIC_EMAIL_DOMAINS,
    GENERIC_LAYER_TOKENS,
    GIT_CMD_TIMEOUT_SECONDS,
    KEBAB_ID_RE,
    MAINTAINER_ALLOWED_OPS,
    MATERIALIZED_RULE_RE,
    MIN_PRIVATE_TOKEN_LEN,
    OWNER_RESTRICTED_OPS,
    ROLE_DEFAULT_PRECEDENCE,
    VALID_DELEGATION_DIRS,
    VALID_DELEGATION_SURFACES,
    VALID_TRACKER_FILES,
    VALIDATOR_ALLOWED_OPS,
)
from dotfiles_mcp.git_governance_engine import (
    record_governance_event,
    stage_non_destructive_proposal,
)
from dotfiles_mcp.manifest_helpers import _ensure_rule_file_frontmatter, _resolve_mounted_child_dir


def resolve_git_user_email(target_dir: Path) -> str:
    """Resolve the active Git user.email for <target_dir> (or DOTFILES_GIT_USER_EMAIL)."""
    env_email = os.environ.get("DOTFILES_GIT_USER_EMAIL", "").strip()
    if env_email:
        return env_email
    try:
        cmd = ["git", "-C", str(target_dir), "config", "user.email"]
        res = subprocess.run(  # noqa: S603
            cmd, capture_output=True, text=True, timeout=GIT_CMD_TIMEOUT_SECONDS, check=False
        )
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip()
    except OSError:
        return ""
    return ""


def _load_manifest_dict(target_dir: Path) -> dict[str, Any]:
    mpath = target_dir / "system" / "mcp-layer.json"
    loaded = json.loads(mpath.read_text(encoding="utf-8")) if mpath.is_file() else {}
    return loaded if isinstance(loaded, dict) else {}


def configure_layer_authority(
    target_dir: Path,
    *,
    owner_role: str,
    authorized_emails: list[str],
    escalation_contact: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Configure or update layer_authority in <target_dir>/system/mcp-layer.json."""
    mpath = target_dir / "system" / "mcp-layer.json"
    if not mpath.is_file():
        raise ValueError(f"Missing layer manifest: {mpath}")
    cleaned_role = owner_role.strip()
    if not cleaned_role:
        raise ValueError("owner_role must be a non-empty string")
    cleaned_emails = [e.strip() for e in authorized_emails if e.strip()]
    manifest = _load_manifest_dict(target_dir)
    layer_id = str(manifest.get("layer_id", target_dir.name))
    contact = (escalation_contact or "").strip() or (
        f"{cleaned_role} ({layer_id})" + (f" <{cleaned_emails[0]}>" if cleaned_emails else "")
    )
    auth_blk: dict[str, Any] = {"owner_role": cleaned_role, "authorized_emails": cleaned_emails,
        "escalation_contact": contact, "consumer_allowed_ops": list(CONSUMER_ALLOWED_OPS),
        "owner_restricted_ops": list(OWNER_RESTRICTED_OPS)}  # fmt: skip
    manifest["layer_authority"] = auth_blk
    if not dry_run:
        mpath.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return {"target_dir": str(target_dir), "layer_id": layer_id, "dry_run": dry_run,
        "layer_authority": auth_blk}  # fmt: skip


def _detect_inherited_upstream_asset(
    target_dir: Path, manifest: dict[str, Any], target_rel_path: str
) -> tuple[bool, str]:
    """Return (is_inherited, owning_template_or_layer) if target_rel_path is upstream-owned."""
    rel = target_rel_path.replace("\\", "/").strip().lstrip("/")
    while rel.startswith("./"):
        rel = rel.removeprefix("./")
    own_id, parts = str(manifest.get("layer_id", target_dir.name)), Path(rel).parts
    r_len, s_len = len(AGENTS_RULES_PREFIX), len(AGENTS_SKILLS_PREFIX)
    is_ag_rule = len(parts) == r_len + 1 and parts[:r_len] == AGENTS_RULES_PREFIX
    if is_ag_rule and (m_rule := MATERIALIZED_RULE_RE.match(parts[-1])):
        return True, f"layer:{m_rule.group(2)}"
    inh_tpls = [str(t) for t in manifest.get("default_stack_templates", []) if str(t) != own_id]
    if len(parts) > 1 and parts[0] == "templates" and parts[1] in inh_tpls:
        return True, parts[1]
    is_ag_skill = (
        len(parts) == s_len + 2
        and parts[:s_len] == AGENTS_SKILLS_PREFIX
        and parts[-1] == "SKILL.md"
    )
    for tpl_name in inh_tpls:
        tdir = target_dir / "templates" / tpl_name
        if (is_ag_rule and (tdir / "rules" / parts[-1]).is_file()) or (
            is_ag_skill and (tdir / "skills" / parts[s_len] / "SKILL.md").is_file()
        ):
            return True, tpl_name
    return False, ""


def verify_layer_operation_authority(
    target_dir: Path,
    *,
    operation: str,
    actor_email: str | None = None,
    target_rel_path: str | None = None,
) -> dict[str, Any]:
    """Verify whether actor_email may execute <operation> on <target_dir> / <target_rel_path>."""
    manifest = _load_manifest_dict(target_dir)
    layer_id = str(manifest.get("layer_id", target_dir.name))
    upstream = manifest.get("upstream_layer", {})
    upstream_id = str(upstream.get("layer_id", "root")) if isinstance(upstream, dict) else "root"
    raw_auth = manifest.get("layer_authority")
    auth = raw_auth if isinstance(raw_auth, dict) else {}
    owner_role = str(auth.get("owner_role", f"Layer Owner ({layer_id})"))
    auth_emails = [str(e).strip() for e in auth.get("authorized_emails", []) if str(e).strip()]
    maint_emails = [str(e).strip() for e in auth.get("maintainer_emails", []) if str(e).strip()]
    val_emails = [str(e).strip() for e in auth.get("validator_emails", []) if str(e).strip()]
    ext_ops = (*MAINTAINER_ALLOWED_OPS, *VALIDATOR_ALLOWED_OPS)
    pool_raw = [
        *auth_emails,
        *maint_emails,
        *(val_emails if operation in VALIDATOR_ALLOWED_OPS else ()),
    ]
    allowed_pool = list(dict.fromkeys(pool_raw if operation in ext_ops else auth_emails))
    escalation_contact = str(auth.get("escalation_contact", f"{owner_role} ({layer_id})"))
    eff_email = resolve_git_user_email(target_dir) if actor_email is None else actor_email.strip()
    if target_rel_path:
        is_inh, origin_ref = _detect_inherited_upstream_asset(target_dir, manifest, target_rel_path)
        if is_inh:
            rem = (
                f"Blocked: '{target_rel_path}' is an inherited upstream asset (origin: "
                f"'{origin_ref}', upstream layer: '{upstream_id}'). Downstream workspaces must "
                f"not mutate or publish upstream rules directly. Process: (1) Adapt in "
                f"'templates/{layer_id}/' or local '.agents/rules/'; (2) Run './scripts/"
                f"layer-config.sh promote-from-project {target_dir} --source {target_rel_path} "
                f"--to-layer {upstream_id} --create-pr'; (3) Coordinate with "
                f"{escalation_contact} for review."
            )
            rc = "INHERITED_UPSTREAM_ASSET_IMMUTABLE"
            ev_kw: dict[str, Any] = {"operation": operation, "status": "blocked", "message": rem,
                "actor_email": eff_email, "source_rel_path": target_rel_path, "remediation": rem,
                "reason_code": rc}  # fmt: skip
            record_governance_event(target_dir, **ev_kw)
            return {"allowed": False, "operation": operation, "layer_id": layer_id,
                "reason_code": rc, "actor_email": eff_email, "target_rel_path": target_rel_path,
                "origin_source": origin_ref, "remediation": rem}  # fmt: skip
    if operation in CONSUMER_ALLOWED_OPS:
        return {"allowed": True, "reason_code": "CONSUMER_OPERATION_ALLOWED", "remediation": None,
            "operation": operation, "layer_id": layer_id, "actor_email": eff_email,
            "owner_role": owner_role}  # fmt: skip
    if allowed_pool and not (
        eff_email and any(fnmatchcase(eff_email.lower(), pat.lower()) for pat in allowed_pool)
    ):
        rem = (
            f"Blocked: Git user.email '{eff_email or '<unset>'}' is not authorized "
            f"to run '{operation}' on layer '{layer_id}' (owner: {owner_role}; "
            f"authorized: {', '.join(allowed_pool)}). "
            f"Process: (1) Keep changes in your workspace; "
            f"(2) Run './scripts/layer-config.sh promote-from-project <your-workspace> "
            f"--source .agents/rules/<file>.md --to-layer {layer_id} --create-pr'; "
            f"(3) Contact {escalation_contact} to review and sync via 'sync-layer'."
        )
        ev_kw = {"operation": operation, "status": "blocked", "actor_email": eff_email,
            "reason_code": "UNAUTHORIZED_ACTOR_EMAIL", "message": rem,
            "remediation": rem}  # fmt: skip
        record_governance_event(target_dir, **ev_kw)
        return {"allowed": False, "reason_code": "UNAUTHORIZED_ACTOR_EMAIL", "operation": operation,
            "layer_id": layer_id, "actor_email": eff_email, "owner_role": owner_role,
            "authorized_emails": allowed_pool, "escalation_contact": escalation_contact,
            "remediation": rem}  # fmt: skip
    return {"allowed": True, "reason_code": "OWNER_AUTHORIZED", "operation": operation,
        "layer_id": layer_id, "actor_email": eff_email, "owner_role": owner_role,
        "remediation": None}  # fmt: skip


def _is_oss_root_manifest(manifest: dict[str, Any]) -> bool:
    """Return True when manifest represents the Open-Source community root layer."""
    role = str(manifest.get("layer_role", ""))
    return str(manifest.get("layer_id", "")) == "root" or role in ("root", "workstation")


def verify_oss_promotion_agnosticism(project_dir: Path, content: str, source_rel: str) -> None:
    """Block promotion to an Open-Source root if content leaks private corporate identifiers."""
    proj_m = _load_manifest_dict(project_dir)
    private_tokens: set[str] = set()
    raw_ids: list[str] = [str(proj_m.get("layer_id", ""))]
    for m_entry in proj_m.get("mounted_layers") or []:
        if isinstance(m_entry, dict):
            raw_ids.extend((str(m_entry.get("name", "")), str(m_entry.get("layer_id", ""))))
    auth = proj_m.get("layer_authority")
    for pat in (auth.get("authorized_emails") or []) if isinstance(auth, dict) else []:
        if isinstance(pat, str) and "@" in pat:
            dom = pat.split("@", 1)[1].lstrip("*.").lower()
            if dom and dom not in GENERIC_EMAIL_DOMAINS:
                private_tokens.add(dom)
                raw_ids.append(dom)
    tok_pat = rf"[a-z0-9]{{{MIN_PRIVATE_TOKEN_LEN},}}"
    for rid in raw_ids:
        private_tokens.update(
            t for t in re.findall(tok_pat, rid.lower()) if t not in GENERIC_LAYER_TOKENS
        )
    leaked = sorted(
        tok for tok in private_tokens if re.search(rf"\b{re.escape(tok)}\b", content, re.IGNORECASE)
    )
    if leaked:
        raise ValueError(
            f"OSS_AGNOSTICISM_VIOLATION: Refusing to promote '{source_rel}' to Open-Source "
            f"root because it contains private layer identifiers ({', '.join(leaked)}). "
            "Generalize these terms before promoting to Open Source."
        )


def verify_single_hop_upstream(
    project_dir: Path, upstream_dir: Path, *, actor_email: str | None = None
) -> None:
    """Enforce the 1-hop upstream boundary and Root 0 owner gate for Open-Source promotions."""
    proj_m, up_m = _load_manifest_dict(project_dir), _load_manifest_dict(upstream_dir)
    up_cfg = proj_m.get("upstream_layer")
    expected_up_id = str(up_cfg.get("layer_id", "")).strip() if isinstance(up_cfg, dict) else ""
    actual_up_id = str(up_m.get("layer_id", "")).strip()
    is_corp = str(proj_m.get("layer_role", "")) == "corporate"
    both_oss = (
        is_corp or expected_up_id == "root" or "dotfiles-ubuntu" in expected_up_id
    ) and _is_oss_root_manifest(up_m)
    if expected_up_id and actual_up_id and expected_up_id != actual_up_id and not both_oss:
        src_id = str(proj_m.get("layer_id", project_dir.name))
        raise ValueError(
            f"CROSS_TIER_PROMOTION_BYPASS: Layer '{src_id}' can only promote to "
            f"immediate upstream_layer '{expected_up_id}' (1-hop), not '{actual_up_id}'."
        )
    if (
        _is_oss_root_manifest(up_m)
        and not (
            v := verify_layer_operation_authority(
                project_dir, operation="release", actor_email=actor_email
            )
        )["allowed"]
    ):
        raise ValueError(f"UNAUTHORIZED_OSS_PROMOTION: Root 0 owner required ({v['remediation']}).")


def build_upward_promotion_pr_plan(
    project_dir: Path, target_repo_dir: Path, *, source_rel: str, dest_rel: str,
    target_layer: str, target_template: str | None, sha256: str,
    actor_email: str | None = None, contributing_org: str | None = None,
    contributors: str | None = None, validation_context: str | None = None,
) -> dict[str, Any]:  # fmt: skip
    """Build a Pull Request plan anchored in the originating child layer's context."""
    proj_m, target_m = _load_manifest_dict(project_dir), _load_manifest_dict(target_repo_dir)
    oss_anonymized = _is_oss_root_manifest(target_m)
    src_lid = str(proj_m.get("layer_id", project_dir.name))
    src_role = str(proj_m.get("layer_role", "project"))
    src_prec = int(proj_m.get("precedence", ROLE_DEFAULT_PRECEDENCE["squad"]))
    source_layer_id = "enterprise-root-0" if oss_anonymized else src_lid
    source_layer_role = "corporate" if oss_anonymized else src_role
    t_fallback = target_layer if target_layer != "root" else target_repo_dir.name
    target_layer_id = str(target_m.get("layer_id", t_fallback))
    raw_t_auth = target_m.get("layer_authority")
    target_auth = raw_t_auth if isinstance(raw_t_auth, dict) else {}
    owner_role = str(target_auth.get("owner_role", f"Layer Owner ({target_layer_id})"))
    esc = str(target_auth.get("escalation_contact", f"{owner_role} ({target_layer_id})"))
    raw_email = resolve_git_user_email(project_dir) if actor_email is None else actor_email.strip()
    proposer_email = "oss-contributor" if oss_anonymized else raw_email
    def_org = "Anonymous Organization (default)" if oss_anonymized else source_layer_id
    eff_org = (contributing_org or "").strip() or def_org
    def_ctb = (
        "Principal Enterprise Architect / Domain Leads"
        if oss_anonymized
        else (proposer_email or "unspecified")
    )
    eff_contrib = (contributors or "").strip() or def_ctb
    def_ctx = f"Multi-layer governance hierarchy ({source_layer_role}, precedence {src_prec})"
    eff_ctx = (validation_context or "").strip() or def_ctx
    asset_slug = re.sub(r"[^a-z0-9]+", "-", Path(source_rel).stem.lower()).strip("-") or "asset"
    sname = Path(source_rel).name
    if oss_anonymized:
        branch_name = f"promote/oss/{asset_slug}"
        pr_title = f"[OSS Promotion -> {target_layer_id}] Promote {sname}"
        commit_msg = f"feat(governance): promote {sname} from enterprise root-0"
    else:
        safe_id = (
            source_layer_id
            if KEBAB_ID_RE.match(source_layer_id)
            else re.sub(r"[^a-z0-9]+", "-", source_layer_id.lower()).strip("-") or "project"
        )
        branch_name = f"promote/{safe_id}/{asset_slug}"
        commit_msg = (
            f"feat(governance): promote {sname} from {source_layer_id} ({source_layer_role})"
        )
        pr_title = f"[Promotion: {source_layer_id} -> {target_layer_id}] Promote {sname}"
    pr_body = (
        f"## Upward Governance Promotion (`{source_layer_id}` -> `{target_layer_id}`)\n\n"
        f"- **Origin Layer**: `{source_layer_id}` (`{source_layer_role}`, `{src_prec}`)\n"
        f"- **Proposer**: `{proposer_email or 'unspecified'}` · **Authority**: `{esc}`\n"
        f"- **Template**: `{target_template or 'layer-root'}` · **SHA-256**: `{sha256}`\n"
        f"- **Path**: `{source_rel}` -> `{dest_rel}`\n\n"
        f"### Community Attribution & Real-World Validation (Optional)\n"
        f"| Field | Value |\n| :--- | :--- |\n"
        f"| **Contributing Organization** | `{eff_org}` |\n"
        f"| **Contributors / Roles** | `{eff_contrib}` |\n"
        f"| **Validation Topology** | `{eff_ctx}` |\n\n"
        f"### Open-Source Governance & Agnosticism Checklist\n"
        f"- [x] Passed `OSS_AGNOSTICISM_VIOLATION` gate (`Root 0 <-> Department <-> Squad`).\n"
        f"- [x] Preserves `< 465` line file gate and `18,000`-byte `AGENTS.md` token budget.\n\n"
        f"### Post-Merge Downstream Inheritance\n```bash\n"
        f"./scripts/layer-config.sh sync-layer <workspace> --parent-dir {target_repo_dir}\n```\n"
    )
    gh_cmd = (
        f"cd {target_repo_dir} && gh pr create --title {json.dumps(pr_title)} "
        f"--body {json.dumps(pr_body)}"
    )
    cmds = [
        f"cd {target_repo_dir} && git checkout -b {branch_name}",
        f"cd {target_repo_dir} && git add {dest_rel} && git commit -m {json.dumps(commit_msg)}",
        f"cd {target_repo_dir} && git push -u origin {branch_name}",
        gh_cmd,
    ]
    return {"origin_layer_id": source_layer_id, "proposer_email": proposer_email,
        "origin_layer_role": source_layer_role, "contributing_org": eff_org,
        "contributors": eff_contrib, "validation_context": eff_ctx, "reviewer_contact": esc,
        "target_layer_id": target_layer_id, "target_owner_role": owner_role,
        "oss_anonymized": oss_anonymized, "branch_name": branch_name,
        "commit_message": commit_msg, "pr_title": pr_title, "pr_body": pr_body,
        "git_pr_commands": cmds}  # fmt: skip


def delegate_directive_to_child(
    workspace_dir: Path,
    *,
    child_layer: str,
    directive: str = "",
    source_rel_path: str | None = None,
    ticket_id: str | None = None,
    priority: str = "P1",
    tracker: str = "WORKTASK.md",
    actor_email: str | None = None,
    force_overwrite: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Delegate a 1-hop downward directive or governance artifact into <child_layer>/<tracker>."""
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
    sib_dir, mnt_dir = _resolve_mounted_child_dir(ws, clean_child), ws / "layers" / clean_child
    targets = [d for d in (sib_dir, mnt_dir if mnt_dir.is_dir() else None) if d is not None]
    if not targets:
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
    fname, updated, staged = src_file.name if src_file is not None else "delegated-item.md", [], []
    stg_kw: dict[str, Any] = {"scope_tag": f"from-{pid}", "file_name": fname, "dry_run": dry_run,
        "operation": "delegate-to-child", "actor_email": actor_email or ""}  # fmt: skip
    for tdir in targets:
        if tracker == "rules":
            ctpl = str(_load_manifest_dict(tdir).get("layer_id") or clean_child)
            r_dest, r_body = (
                tdir / "templates" / ctpl / "rules" / fname,
                src_body or f"# {eff_text}\n",
            )
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
                    sep = "" if cur.endswith("\n") else "\n"
                    tfile.write_text(f"{cur}{sep}{blk}\n", encoding="utf-8")
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
    return {"parent_layer_id": pid, "parent_layer_role": prole, "dry_run": dry_run,
        "child_layer": clean_child, "ticket_id": eff_ticket, "priority": priority,
        "tracker": tracker, "delegated_entry": entry, "parent_ledger_entry": p_entry,
        "updated_paths": updated, "staged_proposals": staged}  # fmt: skip
