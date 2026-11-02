"""Git branch governance, environment promotion gates, non-destructive staging, and audit ledger.

Specification: docs/architecture/04_compaction_surface_and_promotion_engines.md
"""

import contextlib
import json
import re
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from dotfiles_mcp.constants import (
    AUDIT_LOG_TAIL_LINES,
    BUSINESS_MODE_TEMPLATES,
    BUSINESS_PHASE_SEMANTICS,
    DEFAULT_ENV_BRANCH_MAP,
    DEFAULT_PROCESS_BRANCH_PREFIXES,
    DEFAULT_PROTECTED_BRANCHES,
    MAX_RECENT_GOVERNANCE_ALERTS,
    SECONDS_PER_DAY,
    STALE_MODULE_REVIEW_DAYS,
    STALE_POLICY_REVIEW_DAYS,
    STALE_PROPOSAL_MAX_DAYS,
    TECHNICAL_PHASE_SEMANTICS,
    VALID_ENVIRONMENTS,
    VALID_GOVERNANCE_DECISIONS,
    VALID_ROSTER_ROLES,
)


def _load_manifest(target_dir: Path) -> dict[str, Any]:
    mpath = target_dir / "system" / "mcp-layer.json"
    loaded = json.loads(mpath.read_text(encoding="utf-8")) if mpath.is_file() else {}
    return loaded if isinstance(loaded, dict) else {}


def _append_tracker_line(ws: Path, tracker: str, line: str, title_id: str) -> None:
    trk_file = ws / tracker
    cur = (
        trk_file.read_text(encoding="utf-8")
        if trk_file.is_file()
        else f"# Active Work Tasks — {title_id}\n\n"
    )
    if line not in cur:
        trk_file.write_text(f"{cur}{'' if cur.endswith('\n') else '\n'}{line}\n", encoding="utf-8")


def record_governance_event(
    workspace_dir: Path,
    *,
    operation: str,
    status: str,
    actor_email: str = "",
    target_layer: str = "",
    source_rel_path: str = "",
    reason_code: str = "",
    message: str = "",
    remediation: str = "",
    dry_run: bool = False,
) -> dict[str, Any]:
    """Persist a governance/permission event to logs/governance_audit.jsonl and SESSION.md."""
    ws = workspace_dir.resolve()
    manifest = _load_manifest(ws)
    layer_id = str(manifest.get("layer_id", ws.name))
    event: dict[str, Any] = {
        "ts": datetime.now(UTC).isoformat(), "workspace_dir": str(ws), "layer_id": layer_id,
        "operation": operation, "status": status, "actor_email": actor_email or "unspecified",
        "target_layer": target_layer or layer_id, "source_rel_path": source_rel_path,
        "reason_code": reason_code, "message": message, "remediation": remediation,
    }  # fmt: skip
    if not dry_run:
        with contextlib.suppress(OSError):
            log_file = ws / "logs" / "governance_audit.jsonl"
            log_file.parent.mkdir(parents=True, exist_ok=True)
            with log_file.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(event) + "\n")
            if status in ("blocked", "rejected", "deferred", "staged_proposal"):
                s_file = ws / ".agents" / "SESSION.md"
                s_file.parent.mkdir(parents=True, exist_ok=True)
                cur = (
                    s_file.read_text(encoding="utf-8")
                    if s_file.is_file()
                    else "# Session State Log\n"
                )
                hdr = "## Governance Alerts & Pending Decisions"
                bullet = (
                    f"- **[{status.upper()} · `{operation}`]** "
                    f"(`{reason_code or 'GOVERNANCE_NOTICE'}`): {message}"
                )
                base = cur.rstrip() if hdr in cur else f"{cur.rstrip()}\n\n{hdr}"
                if bullet not in base:
                    s_file.write_text(f"{base}\n{bullet}\n", encoding="utf-8")
    return event


def stage_non_destructive_proposal(
    target_dir: Path,
    *,
    scope_tag: str,
    file_name: str,
    content: str,
    operation: str,
    actor_email: str = "",
    reason_code: str = "EXISTING_FILE_PROTECTED",
    dry_run: bool = False,
) -> Path:
    """Stage a candidate governance file in .agents/proposals/<scope_tag>/ without overwriting."""
    ws = target_dir.resolve()
    staged_rel = Path(".agents") / "proposals" / scope_tag / file_name
    staged_file = ws / staged_rel
    msg = (
        f"Target file '{file_name}' is protected or already exists in '{ws.name}'; "
        f"staged non-destructively at '{staged_rel.as_posix()}' for human review (or pass --force)."
    )
    if not dry_run:
        staged_file.parent.mkdir(parents=True, exist_ok=True)
        staged_file.write_text(f"{content.rstrip()}\n", encoding="utf-8")
        entry = (
            f"- [ ] **[P0 · Staged Governance Proposal (`{scope_tag}`)]**: "
            f"Review `{staged_rel.as_posix()}` ({reason_code})"
        )
        _append_tracker_line(ws, "WORKTASK.md", entry, ws.name)
    record_governance_event(
        ws,
        operation=operation,
        status="staged_proposal",
        actor_email=actor_email,
        source_rel_path=staged_rel.as_posix(),
        reason_code=reason_code,
        message=msg,
        dry_run=dry_run,
    )
    return staged_file


def configure_git_governance_policy(
    target_dir: Path,
    *,
    protected_branches: list[str] | None = None,
    require_pr_on_protected: bool = True,
    sync_codeowners: bool = True,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Configure persistent Git branch/environment rules and optional .github/CODEOWNERS."""
    ws = target_dir.resolve()
    mpath = ws / "system" / "mcp-layer.json"
    if not mpath.is_file():
        raise ValueError(f"Missing layer manifest: {mpath}")
    manifest = _load_manifest(ws)
    layer_id = str(manifest.get("layer_id", ws.name))
    prot = [b.strip() for b in (protected_branches or DEFAULT_PROTECTED_BRANCHES) if b.strip()]
    git_gov: dict[str, Any] = {
        "protected_branches": prot,
        "require_pr_on_protected": require_pr_on_protected,
        "process_branch_prefixes": dict(DEFAULT_PROCESS_BRANCH_PREFIXES),
        "environment_branches": dict(DEFAULT_ENV_BRANCH_MAP),
        "environment_promotion_order": list(VALID_ENVIRONMENTS),
    }
    manifest["git_governance"] = git_gov
    raw_auth = manifest.get("layer_authority")
    auth = raw_auth if isinstance(raw_auth, dict) else {}
    emails = [str(e).strip() for e in auth.get("authorized_emails", []) if str(e).strip()]
    maint_ems = [str(e).strip() for e in auth.get("maintainer_emails", []) if str(e).strip()]
    val_ems = [str(e).strip() for e in auth.get("validator_emails", []) if str(e).strip()]
    owners_str = " ".join(e for e in emails if "@" in e and "*" not in e) or "@layer-owners"
    maint_str = (
        " ".join(dict.fromkeys(e for e in (*emails, *maint_ems) if "@" in e and "*" not in e))
        or owners_str
    )
    val_str = (
        " ".join(
            dict.fromkeys(e for e in (*emails, *maint_ems, *val_ems) if "@" in e and "*" not in e)
        )
        or maint_str
    )
    codeowners_rel = ".github/CODEOWNERS"
    codeowners_content = (
        f"# Auto-generated by dotfiles-ubuntu layer-config.sh configure-git-policy ({layer_id})\n"
        f"/system/mcp-layer.json {owners_str}\n/templates/ {maint_str}\n"
        f"/.agents/rules/layer-* {owners_str}\n/corporate/ {owners_str}\n"
        f"/WORKROAD.md {maint_str}\n/ROADMAP.md {maint_str}\n/WORKVALI.md {val_str}\n"
    )
    if not dry_run:
        mpath.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        if sync_codeowners:
            co_file = ws / codeowners_rel
            co_file.parent.mkdir(parents=True, exist_ok=True)
            co_file.write_text(codeowners_content, encoding="utf-8")
    return {"target_dir": str(ws), "layer_id": layer_id, "dry_run": dry_run,
        "git_governance": git_gov, "codeowners_owners": owners_str,
        "codeowners_file": codeowners_rel if sync_codeowners else None}  # fmt: skip


def inspect_git_governance_state(
    workspace_dir: Path,
    *,
    current_branch: str | None = None,
) -> dict[str, Any]:
    """Inspect active Git branch, inferred process stage, environment, and governance alerts."""
    ws = workspace_dir.resolve()
    manifest = _load_manifest(ws)
    raw_gg = manifest.get("git_governance")
    gg = raw_gg if isinstance(raw_gg, dict) else {}
    prot = [str(b) for b in gg.get("protected_branches", DEFAULT_PROTECTED_BRANCHES)]
    prefixes = {**DEFAULT_PROCESS_BRANCH_PREFIXES, **(gg.get("process_branch_prefixes") or {})}

    branch = (current_branch or "").strip()
    if not branch and (ws / ".git").exists():
        git_bin = shutil.which("git") or "/usr/bin/git"
        proc = subprocess.run(  # noqa: S603
            [git_bin, "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=ws,
            check=False,
            capture_output=True,
            text=True,
        )
        branch = proc.stdout.strip()
    eff_branch = branch or "main"
    is_protected = eff_branch in prot
    stage = next(
        (str(st) for st, pfx in prefixes.items() if eff_branch.startswith(str(pfx))),
        "protected-main" if eff_branch in ("main", "master") else "environment-branch",
    )
    if eff_branch in ("main", "master", "env/pro") or eff_branch.startswith("release/v"):
        active_env = "pro"
    elif eff_branch == "env/pre" or eff_branch.startswith("pre/"):
        active_env = "pre"
    elif eff_branch == "env/tst" or eff_branch.startswith("tst/"):
        active_env = "tst"
    else:
        active_env = "dev"

    audit_file = ws / "logs" / "governance_audit.jsonl"
    raw_lines = (
        audit_file.read_text("utf-8").splitlines()[-AUDIT_LOG_TAIL_LINES:]
        if audit_file.is_file()
        else []
    )
    alerts = [item for line in raw_lines if (item := json.loads(line)).get("status") != "allowed"]
    proposals_dir = ws / ".agents" / "proposals"
    p_paths = sorted(proposals_dir.rglob("*.md")) if proposals_dir.is_dir() else []
    staged_files = [str(p.relative_to(ws)).replace("\\", "/") for p in p_paths]
    now_ts = datetime.now(UTC).timestamp()
    stale_props = [
        str(p.relative_to(ws)).replace("\\", "/")
        for p in p_paths
        if (now_ts - p.stat().st_mtime) / SECONDS_PER_DAY > STALE_PROPOSAL_MAX_DAYS
    ]
    thresholds = {"proposals": STALE_PROPOSAL_MAX_DAYS,
        "modules_and_specs": STALE_MODULE_REVIEW_DAYS,
        "policies": STALE_POLICY_REVIEW_DAYS}  # fmt: skip
    return {"current_branch": eff_branch, "is_protected_branch": is_protected,
        "active_process_stage": stage, "active_environment": active_env,
        "protected_branches": prot, "codeowners_synced": (ws / ".github" / "CODEOWNERS").is_file(),
        "staged_proposals": staged_files, "stale_proposals": stale_props,
        "staleness_thresholds_days": thresholds,
        "recent_governance_alerts": alerts[-MAX_RECENT_GOVERNANCE_ALERTS:]}  # fmt: skip


def evaluate_environment_promotion(
    workspace_dir: Path,
    *,
    target_env: str,
    actor_email: str | None = None,
    current_branch: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Verify intrinsic promotion gates for transitioning to dev, tst, pre, or pro."""
    clean_env = target_env.strip().lower()
    if clean_env not in VALID_ENVIRONMENTS:
        raise ValueError(f"Invalid target_env {target_env!r}: must be one of {VALID_ENVIRONMENTS}")
    ws = workspace_dir.resolve()
    manifest = _load_manifest(ws)
    raw_auth = manifest.get("layer_authority")
    auth = raw_auth if isinstance(raw_auth, dict) else {}
    auth_emails = [str(e).lower() for e in auth.get("authorized_emails", []) if str(e).strip()]
    val_emails = [str(e).lower() for e in auth.get("validator_emails", []) if str(e).strip()]
    eff_actor = (actor_email or "").strip().lower()
    is_biz = str(manifest.get("layer_role", "")) in (
        "corporate",
        "department",
        "domain-policy",
    ) or bool(set(BUSINESS_MODE_TEMPLATES) & set(manifest.get("default_stack_templates", [])))
    sem_map = BUSINESS_PHASE_SEMANTICS if is_biz else TECHNICAL_PHASE_SEMANTICS
    failed_gates: list[str] = []
    wt_file, wv_file = ws / "WORKTASK.md", ws / "WORKVALI.md"
    wt_txt = wt_file.read_text(encoding="utf-8") if wt_file.is_file() else ""
    wv_txt = wv_file.read_text(encoding="utf-8") if wv_file.is_file() else ""

    if clean_env in ("tst", "pre", "pro") and re.search(r"^\s*-\s*\[ \]\s*.*P0", wt_txt, re.M):
        failed_gates.append("OPEN_P0_WORKTASKS: Resolve all unchecked P0 items in WORKTASK.md.")
    if clean_env in ("pre", "pro") and re.search(r"^\s*-\s*\[ \]", wv_txt, re.M):
        failed_gates.append("UNVERIFIED_WORKVALI_ITEMS: Complete open checks in WORKVALI.md.")
    if clean_env == "pre" and val_emails and eff_actor not in (*auth_emails, *val_emails):
        failed_gates.append(
            f"UNAUTHORIZED_PRE_VALIDATION: Actor '{actor_email or '<unset>'}' is not in "
            f"validators/owners ({', '.join((*auth_emails, *val_emails))})."
        )
    if clean_env == "pro":
        if not (ws / "CHANGELOG.md").is_file():
            failed_gates.append("MISSING_CHANGELOG: CHANGELOG.md is required for 'pro' release.")
        if auth_emails and eff_actor not in auth_emails:
            failed_gates.append(
                f"UNAUTHORIZED_PRO_RELEASE: Actor '{actor_email or '<unset>'}' is not in "
                f"layer_authority.authorized_emails ({', '.join(auth_emails)})."
            )

    allowed, req_branch = len(failed_gates) == 0, DEFAULT_ENV_BRANCH_MAP[clean_env]
    git_state = inspect_git_governance_state(ws, current_branch=current_branch)
    if not allowed:
        record_governance_event(
            ws,
            operation=f"check-env-promotion:{clean_env}",
            status="blocked",
            actor_email=actor_email or "",
            reason_code="ENV_PROMOTION_GATE_FAILED",
            message="; ".join(failed_gates),
            dry_run=dry_run,
        )
    promo_cmd = f"git checkout -B {req_branch}" if req_branch not in ("task/*", "feature/*") else ""
    return {"workspace_dir": str(ws), "current_environment": git_state["active_environment"],
        "target_environment": clean_env, "phase_semantics": sem_map[clean_env],
        "required_branch": req_branch, "allowed": allowed, "failed_gates": failed_gates,
        "git_promotion_command": promo_cmd}  # fmt: skip


def record_governance_decision(
    workspace_dir: Path,
    *,
    item_ref: str,
    decision: str,
    reason: str,
    actor_email: str = "",
    tracker: str = "WORKTASK.md",
    dry_run: bool = False,
) -> dict[str, Any]:
    """Record a human governance review decision (approve, reject, defer, blocked) in tracker."""
    clean_dec = decision.strip().lower()
    if clean_dec not in VALID_GOVERNANCE_DECISIONS:
        raise ValueError(
            f"Invalid decision {decision!r}: must be one of {VALID_GOVERNANCE_DECISIONS}"
        )
    clean_ref, clean_reason = item_ref.strip(), reason.strip()
    if not clean_ref or not clean_reason:
        raise ValueError("Both item_ref and reason must be non-empty strings")
    ws, manifest = workspace_dir.resolve(), _load_manifest(workspace_dir.resolve())
    lid = str(manifest.get("layer_id", ws.name))
    status_map = {"approve": "approved", "reject": "rejected",
        "defer": "deferred", "blocked": "blocked"}  # fmt: skip
    mapped_status, chk = status_map[clean_dec], "x" if clean_dec == "approve" else " "
    line = (
        f"- [{chk}] **[GOVERNANCE DECISION: {mapped_status.upper()} by "
        f"`{actor_email or lid}` (`{lid}`)]** (`{clean_ref}`): {clean_reason}"
    )
    if not dry_run:
        _append_tracker_line(ws, tracker, line, lid)
    ev_kw: dict[str, Any] = {"operation": "record-decision", "status": mapped_status,
        "actor_email": actor_email, "source_rel_path": clean_ref, "dry_run": dry_run,
        "reason_code": f"HUMAN_DECISION_{mapped_status.upper()}",
        "message": f"{clean_ref}: {clean_reason}"}  # fmt: skip
    ev = record_governance_event(ws, **ev_kw)
    return {"workspace_dir": str(ws), "layer_id": lid, "item_ref": clean_ref,
        "decision": clean_dec, "status": mapped_status, "tracker": tracker, "dry_run": dry_run,
        "recorded_entry": line, "audit_event": ev}  # fmt: skip


def manage_layer_roster(
    target_dir: Path,
    *,
    add_email: str | None = None,
    member_role: str = "member",
    title: str = "",
    squad: str = "",
    remove_email: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Maintain CO/Department/Squad roster (owners, validators, members) and sync CODEOWNERS."""
    ws = target_dir.resolve()
    mpath = ws / "system" / "mcp-layer.json"
    if not mpath.is_file():
        raise ValueError(f"Missing layer manifest: {mpath}")
    clean_role = member_role.strip().lower()
    if clean_role not in VALID_ROSTER_ROLES:
        raise ValueError(
            f"Invalid member_role {member_role!r}: must be one of {VALID_ROSTER_ROLES}"
        )
    manifest = _load_manifest(ws)
    layer_id = str(manifest.get("layer_id", ws.name))
    raw_auth = manifest.get("layer_authority")
    auth: dict[str, Any] = dict(raw_auth) if isinstance(raw_auth, dict) else {}
    r_raw = auth.get("roster")
    raw_roster: dict[str, Any] = r_raw if isinstance(r_raw, dict) else {}
    r_keys = ("owners", "maintainers", "validators", "members")
    roster: dict[str, list[dict[str, str]]] = {
        k: [dict(x) for x in raw_roster.get(k, []) if isinstance(x, dict)] for k in r_keys
    }
    if remove_email and remove_email.strip():
        rem_low = remove_email.strip().lower()
        for k in r_keys:
            roster[k] = [m for m in roster[k] if m.get("email", "").lower() != rem_low]
        for ek in ("authorized_emails", "maintainer_emails", "validator_emails"):
            auth[ek] = [e for e in auth.get(ek, []) if str(e).lower() != rem_low]
    if add_email and add_email.strip():
        clean_em = add_email.strip()
        em_low = clean_em.lower()
        for k in r_keys:
            roster[k] = [m for m in roster[k] if m.get("email", "").lower() != em_low]
        roster[f"{clean_role}s"].append(
            {"email": clean_em, "title": title.strip() or clean_role, "squad": squad.strip()}
        )
    owner_ems = [m["email"] for m in roster["owners"] if m.get("email")]
    maint_ems = [m["email"] for m in roster["maintainers"] if m.get("email")]
    val_ems = [m["email"] for m in roster["validators"] if m.get("email")]
    cur_auth = [str(e).strip() for e in auth.get("authorized_emails", []) if str(e).strip()]
    auth["roster"] = roster
    auth["authorized_emails"] = list(dict.fromkeys([*cur_auth, *owner_ems]))
    auth["maintainer_emails"] = list(dict.fromkeys(maint_ems))
    auth["validator_emails"] = list(dict.fromkeys(val_ems))
    manifest["layer_authority"] = auth
    if not dry_run:
        mpath.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        if (ws / ".github/CODEOWNERS").is_file() or add_email or remove_email:
            configure_git_governance_policy(ws, sync_codeowners=True, dry_run=False)
    return {
        "target_dir": str(ws),
        "layer_id": layer_id,
        "roster": roster,
        "authorized_emails": auth["authorized_emails"],
        "maintainer_emails": auth["maintainer_emails"],
        "validator_emails": auth["validator_emails"],
        "dry_run": dry_run,
    }
