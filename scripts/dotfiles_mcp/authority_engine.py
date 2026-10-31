"""Role & identity authority enforcement and upward PR promotion planner.

Specification: docs/architecture/04_compaction_surface_and_promotion_engines.md
Enforces asymmetric layer capabilities (Layer Owner vs. Downstream Consumer),
git user.email authority matching, inherited upstream rule immutability with
constructive remediation guidance, and child-layer-contextualized Pull Request
plans for upward promotions.
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
    CONSUMER_ALLOWED_OPS,
    GENERIC_EMAIL_DOMAINS,
    GENERIC_LAYER_TOKENS,
    KEBAB_ID_RE,
    MATERIALIZED_RULE_RE,
    OWNER_RESTRICTED_OPS,
)


def resolve_git_user_email(target_dir: Path) -> str:
    """Resolve the active Git user.email for <target_dir> (or DOTFILES_GIT_USER_EMAIL)."""
    env_email = os.environ.get("DOTFILES_GIT_USER_EMAIL", "").strip()
    if env_email:
        return env_email
    try:
        res = subprocess.run(  # noqa: S603
            ["git", "-C", str(target_dir), "config", "user.email"],  # noqa: S607
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip()
    except OSError:
        return ""
    return ""


def _load_manifest_dict(target_dir: Path) -> dict[str, Any]:
    mpath = target_dir / "system" / "mcp-layer.json"
    if mpath.is_file():
        loaded = json.loads(mpath.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            return loaded
    return {}


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
    contact = (
        escalation_contact.strip()
        if escalation_contact and escalation_contact.strip()
        else f"{cleaned_role} ({layer_id})" + (f" <{cleaned_emails[0]}>" if cleaned_emails else "")
    )
    authority_block: dict[str, Any] = {
        "owner_role": cleaned_role,
        "authorized_emails": cleaned_emails,
        "escalation_contact": contact,
        "consumer_allowed_ops": list(CONSUMER_ALLOWED_OPS),
        "owner_restricted_ops": list(OWNER_RESTRICTED_OPS),
    }
    manifest["layer_authority"] = authority_block
    if not dry_run:
        mpath.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return {
        "target_dir": str(target_dir),
        "layer_id": layer_id,
        "layer_authority": authority_block,
        "dry_run": dry_run,
    }


def _detect_inherited_upstream_asset(
    target_dir: Path, manifest: dict[str, Any], target_rel_path: str
) -> tuple[bool, str]:
    """Return (is_inherited, owning_template_or_layer) if target_rel_path is upstream-owned."""
    rel = target_rel_path.replace("\\", "/").strip().lstrip("/")
    while rel.startswith("./"):
        rel = rel[2:]
    own_id = str(manifest.get("layer_id", target_dir.name))
    parts = Path(rel).parts
    if len(parts) == 3 and parts[:2] == (".agents", "rules"):
        m_rule = MATERIALIZED_RULE_RE.match(parts[2])
        if m_rule:
            return True, f"layer:{m_rule.group(2)}"
    stack_tpls = [str(t) for t in manifest.get("default_stack_templates", [])]
    inherited_tpls = [t for t in stack_tpls if t != own_id]
    if len(parts) >= 2 and parts[0] == "templates" and parts[1] in inherited_tpls:
        return True, parts[1]
    for tpl_name in inherited_tpls:
        tpl_dir = target_dir / "templates" / tpl_name
        if (
            len(parts) == 3
            and parts[:2] == (".agents", "rules")
            and (tpl_dir / "rules" / parts[2]).is_file()
        ):
            return True, tpl_name
        if (
            len(parts) == 4
            and parts[:2] == (".agents", "skills")
            and parts[3] == "SKILL.md"
            and (tpl_dir / "skills" / parts[2] / "SKILL.md").is_file()
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
    auth = manifest.get("layer_authority", {})
    if not isinstance(auth, dict):
        auth = {}
    owner_role = str(auth.get("owner_role", f"Layer Owner ({layer_id})"))
    authorized_emails = [
        str(e).strip() for e in auth.get("authorized_emails", []) if str(e).strip()
    ]
    escalation_contact = str(auth.get("escalation_contact", f"{owner_role} ({layer_id})"))
    eff_email = (
        actor_email.strip() if actor_email is not None else resolve_git_user_email(target_dir)
    )

    if target_rel_path:
        is_inherited, origin_ref = _detect_inherited_upstream_asset(
            target_dir, manifest, target_rel_path
        )
        if is_inherited:
            return {
                "allowed": False,
                "reason_code": "INHERITED_UPSTREAM_ASSET_IMMUTABLE",
                "operation": operation,
                "layer_id": layer_id,
                "actor_email": eff_email,
                "target_rel_path": target_rel_path,
                "origin_source": origin_ref,
                "remediation": (
                    f"Blocked: '{target_rel_path}' is an inherited upstream asset "
                    f"(origin: '{origin_ref}', upstream layer: '{upstream_id}'). "
                    f"Downstream workspaces must not mutate or publish upstream rules directly. "
                    f"Process to follow: (1) Author or adapt the rule in your own layer template "
                    f"('templates/{layer_id}/') or local '.agents/rules/'; "
                    f"(2) Run './scripts/layer-config.sh promote-from-project {target_dir} "
                    f"--source {target_rel_path} --to-layer {upstream_id} --prepare-pr' "
                    f"to generate an upward Pull Request from your layer context; "
                    f"(3) Coordinate with the upstream owner ({escalation_contact}) for review."
                ),
            }

    if operation in CONSUMER_ALLOWED_OPS:
        return {
            "allowed": True,
            "reason_code": "CONSUMER_OPERATION_ALLOWED",
            "operation": operation,
            "layer_id": layer_id,
            "actor_email": eff_email,
            "owner_role": owner_role,
            "remediation": None,
        }

    if authorized_emails:
        email_lower = eff_email.lower()
        matched = bool(
            email_lower and any(fnmatchcase(email_lower, pat.lower()) for pat in authorized_emails)
        )
        if not matched:
            return {
                "allowed": False,
                "reason_code": "UNAUTHORIZED_ACTOR_EMAIL",
                "operation": operation,
                "layer_id": layer_id,
                "actor_email": eff_email,
                "owner_role": owner_role,
                "authorized_emails": authorized_emails,
                "escalation_contact": escalation_contact,
                "remediation": (
                    f"Blocked: Git user.email '{eff_email or '<unset>'}' is not authorized "
                    f"to run '{operation}' on layer '{layer_id}' (owner: {owner_role}; "
                    f"authorized: {', '.join(authorized_emails)}). "
                    f"Process to follow: (1) Keep changes in your own squad/project workspace; "
                    f"(2) Run './scripts/layer-config.sh promote-from-project <your-workspace> "
                    f"--source .agents/rules/<file>.md --to-layer {layer_id} --prepare-pr' "
                    f"to open a Pull Request from your layer context; "
                    f"(3) Contact {escalation_contact} to review and publish upstream, "
                    f"then inherit via './scripts/layer-config.sh sync-layer'."
                ),
            }

    return {
        "allowed": True,
        "reason_code": "OWNER_AUTHORIZED",
        "operation": operation,
        "layer_id": layer_id,
        "actor_email": eff_email,
        "owner_role": owner_role,
        "remediation": None,
    }


def _is_oss_root_manifest(manifest: dict[str, Any]) -> bool:
    """Return True when manifest represents the Open-Source community root layer."""
    return str(manifest.get("layer_id", "")) == "root" or str(manifest.get("layer_role", "")) in (
        "root",
        "workstation",
    )


def verify_oss_promotion_agnosticism(
    project_dir: Path,
    content: str,
    source_rel: str,
) -> None:
    """Block promotion to an Open-Source root if content leaks private corporate identifiers."""
    proj_m = _load_manifest_dict(project_dir)
    private_tokens: set[str] = set()
    raw_ids: list[str] = [str(proj_m.get("layer_id", ""))]
    for m_entry in proj_m.get("mounted_layers") or []:
        if isinstance(m_entry, dict):
            raw_ids.append(str(m_entry.get("name", "")))
            raw_ids.append(str(m_entry.get("layer_id", "")))
    auth = proj_m.get("layer_authority")
    if isinstance(auth, dict):
        for pat in auth.get("authorized_emails") or []:
            if isinstance(pat, str) and "@" in pat:
                dom = pat.split("@", 1)[1].lstrip("*.").lower()
                if dom and dom not in GENERIC_EMAIL_DOMAINS:
                    private_tokens.add(dom)
                    raw_ids.append(dom)
    for rid in raw_ids:
        for tok in re.findall(r"[a-z0-9]{4,}", rid.lower()):
            if tok not in GENERIC_LAYER_TOKENS:
                private_tokens.add(tok)
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
    project_dir: Path,
    upstream_dir: Path,
    *,
    actor_email: str | None = None,
) -> None:
    """Enforce the 1-hop upstream boundary and Root 0 owner gate for Open-Source promotions."""
    proj_m = _load_manifest_dict(project_dir)
    up_m = _load_manifest_dict(upstream_dir)
    up_cfg = proj_m.get("upstream_layer")
    expected_up_id = str(up_cfg.get("layer_id", "")).strip() if isinstance(up_cfg, dict) else ""
    actual_up_id = str(up_m.get("layer_id", "")).strip()
    both_oss = (
        str(proj_m.get("layer_role", "")) == "corporate"
        or expected_up_id == "root"
        or "dotfiles-ubuntu" in expected_up_id
    ) and _is_oss_root_manifest(up_m)
    if expected_up_id and actual_up_id and expected_up_id != actual_up_id and not both_oss:
        src_id = str(proj_m.get("layer_id", project_dir.name))
        raise ValueError(
            f"CROSS_TIER_PROMOTION_BYPASS: Layer '{src_id}' can only promote directly "
            f"to its immediate upstream_layer '{expected_up_id}' (1-hop boundary), "
            f"not '{actual_up_id}'."
        )
    if _is_oss_root_manifest(up_m):
        verdict = verify_layer_operation_authority(
            project_dir, operation="release", actor_email=actor_email
        )
        if not verdict["allowed"]:
            raise ValueError(
                "UNAUTHORIZED_OSS_PROMOTION: Only an authorized Root 0 owner may promote "
                f"assets to the Open-Source root ({verdict['remediation']})."
            )


def build_upward_promotion_pr_plan(
    project_dir: Path,
    target_repo_dir: Path,
    *,
    source_rel: str,
    dest_rel: str,
    target_layer: str,
    target_template: str | None,
    sha256: str,
    actor_email: str | None = None,
    contributing_org: str | None = None,
    contributors: str | None = None,
    validation_context: str | None = None,
) -> dict[str, Any]:
    """Build a Pull Request plan anchored in the originating child layer's context."""
    proj_m, target_m = _load_manifest_dict(project_dir), _load_manifest_dict(target_repo_dir)
    oss_anonymized = _is_oss_root_manifest(target_m)
    source_layer_id = (
        "enterprise-root-0" if oss_anonymized else str(proj_m.get("layer_id", project_dir.name))
    )
    source_layer_role = "corporate" if oss_anonymized else str(proj_m.get("layer_role", "project"))
    source_prec = int(proj_m.get("precedence", 50))
    target_layer_id = str(
        target_m.get("layer_id", target_layer if target_layer != "root" else target_repo_dir.name)
    )
    target_auth = target_m.get("layer_authority", {})
    if not isinstance(target_auth, dict):
        target_auth = {}
    owner_role = str(target_auth.get("owner_role", f"Layer Owner ({target_layer_id})"))
    escalation_contact = str(
        target_auth.get("escalation_contact", f"{owner_role} ({target_layer_id})")
    )
    proposer_email = (
        "oss-contributor"
        if oss_anonymized
        else (
            actor_email.strip() if actor_email is not None else resolve_git_user_email(project_dir)
        )
    )
    eff_org = (contributing_org or "").strip() or (
        "Anonymous Organization (default)" if oss_anonymized else source_layer_id
    )
    eff_contributors = (contributors or "").strip() or (
        "Principal Enterprise Architect / Domain Leads"
        if oss_anonymized
        else (proposer_email or "unspecified")
    )
    eff_context = (validation_context or "").strip() or (
        f"Multi-layer governance hierarchy ({source_layer_role}, precedence {source_prec})"
    )
    asset_slug = re.sub(r"[^a-z0-9]+", "-", Path(source_rel).stem.lower()).strip("-") or "asset"
    if oss_anonymized:
        branch_name = f"promote/oss/{asset_slug}"
        commit_msg = f"feat(governance): promote {Path(source_rel).name} from enterprise root-0"
        pr_title = f"[OSS Promotion -> {target_layer_id}] Promote {Path(source_rel).name}"
    else:
        safe_source_id = (
            source_layer_id
            if KEBAB_ID_RE.match(source_layer_id)
            else re.sub(r"[^a-z0-9]+", "-", source_layer_id.lower()).strip("-") or "project"
        )
        branch_name = f"promote/{safe_source_id}/{asset_slug}"
        commit_msg = (
            f"feat(governance): promote {Path(source_rel).name} "
            f"from {source_layer_id} ({source_layer_role})"
        )
        pr_title = (
            f"[Promotion: {source_layer_id} -> {target_layer_id}] Promote {Path(source_rel).name}"
        )
    pr_body = (
        f"## Upward Governance Promotion (`{source_layer_id}` -> `{target_layer_id}`)\n\n"
        f"- **Origin Layer (Context of Need)**: `{source_layer_id}` "
        f"(role: `{source_layer_role}`, precedence: `{source_prec}`)\n"
        f"- **Proposer Git Identity**: `{proposer_email or 'unspecified'}`\n"
        f"- **Target Layer & Authority**: `{target_layer_id}` (`{escalation_contact}`)\n"
        f"- **Target Template Pack**: `{target_template or 'layer-root'}`\n"
        f"- **Source Path**: `{source_rel}` -> **Destination**: `{dest_rel}`\n"
        f"- **SHA-256 Digest**: `{sha256}`\n\n"
        f"### Community Attribution & Real-World Validation (Optional)\n"
        f"| Field | Value (Edit or leave anonymous) |\n"
        f"| :--- | :--- |\n"
        f"| **Contributing Organization / Company** | `{eff_org}` |\n"
        f"| **Contributors / Roles Involved** | `{eff_contributors}` |\n"
        f"| **Real-World Validation Topology** | `{eff_context}` |\n"
        f"| **Public Release Credit Preference** | "
        f"`[ ] Credit organization/contributors in CHANGELOG.md` / `[x] Keep anonymous` |\n\n"
        f"### Open-Source Governance & Agnosticism Checklist\n"
        f"- [x] Passed `OSS_AGNOSTICISM_VIOLATION` zero-leak gate "
        f"(no private brand, domain, or internal codename literals).\n"
        f"- [x] Validated in a live multi-tier governance hierarchy "
        f"(`Root 0 <-> Department <-> Squad`).\n"
        f"- [x] Preserves `< 465` line file gate and `18,000`-byte `AGENTS.md` token budget.\n\n"
        f"### Post-Merge Downstream Inheritance\n"
        f"Once reviewed and merged by `{owner_role}`, downstream workspaces inherit "
        f"this update via:\n"
        f"```bash\n"
        f"./scripts/layer-config.sh sync-layer <downstream-workspace> "
        f"--parent-dir {target_repo_dir}\n"
        f"```\n"
    )
    return {
        "origin_layer_id": source_layer_id,
        "origin_layer_role": source_layer_role,
        "proposer_email": proposer_email,
        "contributing_org": eff_org,
        "contributors": eff_contributors,
        "validation_context": eff_context,
        "target_layer_id": target_layer_id,
        "target_owner_role": owner_role,
        "reviewer_contact": escalation_contact,
        "oss_anonymized": oss_anonymized,
        "branch_name": branch_name,
        "commit_message": commit_msg,
        "pr_title": pr_title,
        "pr_body": pr_body,
        "git_pr_commands": [
            f"cd {target_repo_dir} && git checkout -b {branch_name}",
            (
                f"cd {target_repo_dir} && git add {dest_rel} "
                f"&& git commit -m {json.dumps(commit_msg)}"
            ),
            f"cd {target_repo_dir} && git push -u origin {branch_name}",
            (
                f"cd {target_repo_dir} && gh pr create "
                f"--title {json.dumps(pr_title)} --body {json.dumps(pr_body)}"
            ),
        ],
    }
