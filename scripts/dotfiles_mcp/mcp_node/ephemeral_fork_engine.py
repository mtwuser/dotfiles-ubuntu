"""Ephemeral scoped fork materialization, cross-project bridging, and TTL garbage collection.

Specification: docs/architecture/05_ephemeral_forks_and_department_bots.md
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any

from dotfiles_mcp.core.constants import (
    CAPSULE_BRIEF_PREVIEW_CHARS,
    CAPSULE_HMAC_HEX_LEN,
    DEFAULT_EPHEMERAL_TTL_SECONDS,
    EPOCH_DECIMAL_PLACES,
    FORK_ID_HASH_HEX_LEN,
    KEBAB_ID_RE,
    LAYER_MANIFEST_CONTRACT_REV,
    MAX_ACTIVE_EPHEMERAL_FORKS,
    MAX_BRIEF_INVARIANTS,
    MAX_EPHEMERAL_TTL_SECONDS,
    MIN_EPHEMERAL_TTL_SECONDS,
    OWNER_DIR_RWX_BITS,
    ROLE_DEFAULT_PRECEDENCE,
    VALID_AGENT_TIERS,
    VALID_ARCHITECTURAL_PLANES,
    VALID_EPHEMERAL_ACCESS_MODES,
    VALID_EPHEMERAL_SCOPES,
    VALID_RESOLUTIONS,
    VALID_ROSTER_ROLES,
)
from dotfiles_mcp.core.manifest_helpers import _resolve_template_dir


def _is_writable_or_creatable(target: Path) -> bool:
    curr = target
    while not curr.exists() and curr.parent != curr:
        curr = curr.parent
    return curr.exists() and os.access(curr, os.W_OK)


def default_ephemeral_root(repo_dir: Path, ephemeral_root: Path | None = None) -> Path:
    """Return the resolved directory holding active ephemeral forks (with /tmp fallback if ro)."""
    if ephemeral_root is not None:
        return ephemeral_root.resolve()
    if env_override := os.environ.get("DOTFILES_EPHEMERAL_ROOT", "").strip():
        return Path(env_override).resolve()
    candidate = (repo_dir.resolve() / "logs/ephemeral_forks").resolve()
    if candidate.is_dir() or _is_writable_or_creatable(candidate):
        return candidate
    tmp_fallback = (Path(tempfile.gettempdir()).resolve() / "dotfiles_ephemeral_forks").resolve()
    return tmp_fallback if _is_writable_or_creatable(tmp_fallback) else candidate


def extract_ephemeral_advisories(
    resolved_bindings: list[dict[str, Any]], target_path: str
) -> list[dict[str, Any]]:
    """Extract Department Bot delegation advisories from matched surface bindings."""
    advisories, seen_roles = [], set()
    for binding in resolved_bindings:
        policy = binding.get("ephemeral_fork_policy")
        bot_role = str(policy.get("bot_role", "")).strip() if isinstance(policy, dict) else ""
        if not bot_role or bot_role in seen_roles or not isinstance(policy, dict):
            continue
        seen_roles.add(bot_role)
        call_args = {"action": "evaluate", "bot_role": bot_role, "target_path": target_path or "*"}
        r_id = {"bot_role": bot_role, "source_layer": str(binding.get("layer", "root"))}
        r_bind = {"source_binding_id": str(binding.get("binding_id", ""))}
        r_pol = {
            "trigger": str(policy.get("trigger", "on_surface_match")),
            "model_tier": str(policy.get("model_tier", "flash")),
            "access_mode": str(policy.get("access_mode", "strictly-read-only")),
            "mount_templates": [str(t) for t in policy.get("mount_templates", [])],
            "resolution": str(policy.get("resolution", "L2")),
            "ttl_seconds": int(policy.get("ttl_seconds", DEFAULT_EPHEMERAL_TTL_SECONDS)),
            "handback_contract": str(policy.get("handback_contract", "4-channel-digest+rcap1")),
            "recommended_mcp_call": {"tool": "orchestrate_ephemeral_fork", "arguments": call_args},
        }
        advisories.append({**r_id, **r_bind, **r_pol})
    return advisories


def reap_expired_ephemeral_forks(
    repo_dir: Path, ephemeral_root: Path | None = None, now_epoch: float | None = None
) -> list[str]:
    """Delete expired or corrupted ephemeral forks under ephemeral_root."""
    root = default_ephemeral_root(repo_dir, ephemeral_root)
    if not root.is_dir():
        return []
    now, reaped = now_epoch if now_epoch is not None else time.time(), []
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        manifest_path = child / "system/mcp-layer.json"
        expired = not manifest_path.is_file()
        if not expired:
            try:
                data = json.loads(manifest_path.read_text(encoding="utf-8"))
                expired = now >= float(
                    data.get("ephemeral_metadata", {}).get("expires_at_epoch", 0.0)
                )
            except OSError, ValueError, TypeError, json.JSONDecodeError:
                expired = True
        if expired:
            _ensure_dirs_writable(child)
            shutil.rmtree(child, ignore_errors=True)
            reaped.append(child.name)
    return reaped


def _ensure_dirs_writable(root: Path) -> None:
    for d in (root, *(p for p in root.rglob("*") if p.is_dir(follow_symlinks=False))):
        d.chmod(d.stat().st_mode | OWNER_DIR_RWX_BITS)


def _copy_zero_copy(src: Path, dst: Path) -> None:
    """Materialize file or directory tree using hardlinks (0 extra blocks) or copy fallback."""
    if src.is_dir():
        shutil.copytree(
            src, dst, symlinks=True, dirs_exist_ok=True, copy_function=_link_or_copy_file
        )
        _ensure_dirs_writable(dst)
    else:
        _link_or_copy_file(str(src), str(dst))


def _link_or_copy_file(src_str: str, dst_str: str) -> str:
    with contextlib.suppress(OSError):
        os.link(src_str, dst_str)
        return dst_str
    return shutil.copy2(src_str, dst_str)


def _prepare_project_bridge(project_dir: Path) -> tuple[list[str], str, dict[str, Any]]:
    """Validate and extract a target project's .agents/rules/*.md as a bridge payload."""
    proj = project_dir.resolve()
    if not proj.is_dir():
        raise FileNotFoundError(f"mount_project_rules_from directory does not exist: {proj}")
    rules_dir, bridged_files = proj / ".agents" / "rules", []
    sections = [f"# Ephemeral Project Bridge ({proj.name})\n"]
    for rf in sorted(rules_dir.glob("*.md")) if rules_dir.is_dir() else []:
        if not rf.resolve().is_relative_to(proj):
            raise ValueError(
                f"Outbound symlink escape denied in mount_project_rules_from: {rf.name}"
            )
        sections.append(f"## Rule: {rf.name}\n\n{rf.read_text(encoding='utf-8').strip()}\n")
        bridged_files.append(f".agents/rules/{rf.name}")
    w, lid = ["*"], f"bridge-{proj.name.lower().replace('_', '-')}"
    b_head = {"binding_id": "ephemeral-project-bridge-rules", "mode": "authoritative"}
    b_match = {"target_globs": w, "architectural_planes": w, "scopes": w, "traits": w}
    b_desc = {
        "description": f"Bridged workspace rules from {proj.name}",
        "default_resolution": "L2",
    }
    b_inv = {"invariants": [f"Enforce bridged workspace contracts from {proj.name}"]}
    b_files = {"rule_files": ["antigravity/.gemini/config/AGENTS.md"], "canonical_templates": []}
    binding: dict[str, Any] = {**b_head, **b_desc, **b_match, **b_inv, **b_files}
    m_head = {"schema_version": LAYER_MANIFEST_CONTRACT_REV, "layer_id": lid, "layer_role": "squad"}
    m_prec = {"precedence": ROLE_DEFAULT_PRECEDENCE["bridge"], "default_stack_templates": []}
    m_desc = {"description": f"Ephemeral cross-project rule bridge from {proj.name}"}
    m_guard = {"baseline_guardrails": [f"Cross-project bridge active from {proj.name}"]}
    m_tail = {"surface_bindings": [binding], "environments": {}, "federated_mcps": []}
    bridge_manifest: dict[str, Any] = {**m_head, **m_prec, **m_desc, **m_guard, **m_tail}
    return bridged_files, "\n".join(sections), bridge_manifest


def spawn_ephemeral_fork(
    repo_dir: Path,
    base_manifest: dict[str, Any],
    *,
    bot_role: str,
    target_globs: list[str] | None = None,
    architectural_planes: list[str] | None = None,
    mount_templates: list[str] | None = None,
    mount_layers: list[str] | None = None,
    mount_project_rules_from: Path | None = None,
    model_tier: str = "flash",
    access_mode: str = "strictly-read-only",
    ephemeral_scope: str | None = None,
    actor_role: str = "member",
    resolution: str = "L2",
    ttl_seconds: int = DEFAULT_EPHEMERAL_TTL_SECONDS,
    ephemeral_root: Path | None = None,
    now_epoch: float | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Materialize a zero-copy, TTL-bounded ephemeral fork for a Department Bot."""
    role_clean = bot_role.strip()
    planes, globs = list(architectural_planes or ["*"]), list(target_globs or ["*"])
    eff_scope = (ephemeral_scope or "intra-layer").strip().lower()
    clean_actor = actor_role.strip().lower() or "member"
    if not KEBAB_ID_RE.match(role_clean):
        raise ValueError(f"Invalid bot_role {role_clean!r}: must be kebab-case")
    if model_tier not in VALID_AGENT_TIERS:
        raise ValueError(f"Invalid model_tier {model_tier!r}: must be one of {VALID_AGENT_TIERS}")
    if access_mode not in VALID_EPHEMERAL_ACCESS_MODES:
        raise ValueError(f"Invalid access_mode {access_mode!r}")
    if eff_scope not in VALID_EPHEMERAL_SCOPES:
        raise ValueError(
            f"Invalid ephemeral_scope {eff_scope!r}: must be in {VALID_EPHEMERAL_SCOPES}"
        )
    if clean_actor not in VALID_ROSTER_ROLES:
        raise ValueError(f"Invalid actor_role {clean_actor!r}: must be one of {VALID_ROSTER_ROLES}")
    if eff_scope == "inter-layer" and access_mode != "strictly-read-only":
        raise ValueError("Inter-layer ephemeral forks must use access_mode='strictly-read-only'")
    if clean_actor == "validator" and access_mode == "read-write-scoped":
        raise ValueError("Validator actor_role cannot use access_mode='read-write-scoped'")
    is_ro_ws = (
        base_manifest.get("layer_role") == "workstation"
        and (repo_dir / ".workstation-state.json").is_file()
    )
    if is_ro_ws and access_mode != "strictly-read-only":
        raise ValueError(
            "Read-only workstation appliance only permits access_mode='strictly-read-only'"
        )
    if resolution not in VALID_RESOLUTIONS:
        raise ValueError(f"Invalid resolution {resolution!r}: must be one of {VALID_RESOLUTIONS}")
    if not (MIN_EPHEMERAL_TTL_SECONDS <= ttl_seconds <= MAX_EPHEMERAL_TTL_SECONDS):
        raise ValueError(f"Invalid ttl_seconds {ttl_seconds}")
    for p in planes:
        if p != "*" and p not in VALID_ARCHITECTURAL_PLANES:
            raise ValueError(f"Invalid architectural_plane {p!r}")
    for kind, items in (("mount_template", mount_templates), ("mount_layer", mount_layers)):
        for item in items or []:
            if not KEBAB_ID_RE.match(item):
                raise ValueError(f"Invalid {kind} {item!r}: must be kebab-case")

    reaped = reap_expired_ephemeral_forks(repo_dir, ephemeral_root, now_epoch=now_epoch)
    root = default_ephemeral_root(repo_dir, ephemeral_root)
    active_dirs = [d for d in root.iterdir() if d.is_dir()] if root.is_dir() else []
    if len(active_dirs) >= MAX_ACTIVE_EPHEMERAL_FORKS:
        raise ValueError(
            f"EPHEMERAL_FORK_LIMIT_REACHED: active ephemeral forks ({len(active_dirs)}) "
            f"reached maximum capacity ({MAX_ACTIVE_EPHEMERAL_FORKS}). Reap unused forks first."
        )

    created_at = round(now_epoch if now_epoch is not None else time.time(), EPOCH_DECIMAL_PLACES)
    expires_at = round(created_at + ttl_seconds, EPOCH_DECIMAL_PLACES)
    seed = f"{role_clean}:{created_at}:{target_globs}:{mount_templates}:{mount_project_rules_from}"
    fork_hash = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:FORK_ID_HASH_HEX_LEN]
    fork_id = f"eph-{role_clean}-{fork_hash}"
    session_secret = hashlib.sha256(f"rcap1-ephemeral:{fork_id}:{created_at}".encode()).hexdigest()[
        :CAPSULE_HMAC_HEX_LEN
    ]
    default_tpls = list(base_manifest.get("default_stack_templates", []))
    effective_templates = list(mount_templates) if mount_templates is not None else default_tpls
    tpl_dirs = [d for t in effective_templates if (d := _resolve_template_dir(repo_dir, t))]
    tpl_rules = [
        str(rf.relative_to(repo_dir)).replace("\\", "/")
        for td in tpl_dirs
        for rf in sorted((td / "rules").glob("*.md"))
    ]
    tpl_assets = [
        str(af.relative_to(repo_dir)).replace("\\", "/")
        for td in tpl_dirs
        for af in sorted((td / "assets").glob("*.md"))
    ]
    canonical_tpls = tpl_assets or tpl_rules
    rule_files = ["antigravity/.gemini/config/AGENTS.md", *tpl_rules]

    parent_layers_dir = repo_dir / "layers"
    selected_layers = [
        c.name
        for c in (sorted(parent_layers_dir.iterdir()) if parent_layers_dir.is_dir() else [])
        if c.is_dir()
        and not c.name.startswith(".")
        and (mount_layers is None or c.name in mount_layers)
    ]
    parent_id = str(base_manifest.get("layer_id", "dotfiles-ubuntu-default"))
    bridged_files, bridge_md, bridge_manifest = (
        _prepare_project_bridge(mount_project_rules_from)
        if mount_project_rules_from is not None
        else ([], "", {})
    )
    bridge_extra: dict[str, Any] = {}
    if mount_project_rules_from is not None:
        selected_layers.append("ephemeral-project-bridge")
        b_id_map = {"bridge_layer_id": str(bridge_manifest.get("layer_id", ""))}
        b_doc_map = {"bridge_agents_md": bridge_md, "bridge_manifest": bridge_manifest}
        bridge_extra = {**b_id_map, **b_doc_map, "bridged_project_files": bridged_files}
    meta_id = {"fork_id": fork_id, "bot_role": role_clean, "parent_layer_id": parent_id}
    meta_mode = {"model_tier": model_tier, "access_mode": access_mode, "ephemeral_scope": eff_scope}
    meta_role = {"actor_role": clean_actor, "resolution": resolution, "target_globs": globs}
    meta_surf = {"architectural_planes": planes, "mount_layers_filter": mount_layers}
    meta_time = {"created_at_epoch": created_at, "expires_at_epoch": expires_at}
    meta_ttl = {"ttl_seconds": ttl_seconds, "session_resonance_key": session_secret}
    meta_hb = {"handback_contract": "4-channel-digest+rcap1", **bridge_extra}
    m_part1 = {**meta_id, **meta_mode, **meta_role}
    eph_meta: dict[str, Any] = {**m_part1, **meta_surf, **meta_time, **meta_ttl, **meta_hb}
    b_id = {"binding_id": f"{role_clean}-ephemeral-authority", "mode": "authoritative"}
    b_sc = {"target_globs": globs, "architectural_planes": planes, "scopes": ["*"], "traits": ["*"]}
    b_desc = {"description": f"Authoritative scoped binding for {role_clean}"}
    b_res = {"default_resolution": resolution, "rule_files": rule_files}
    b_invs = [
        f"Operate strictly within {access_mode} mode ({eff_scope}) and {globs} surface boundary",
        "Return output using the 4-Channel Executive Digest contract (AGENTS.md §12)",
    ]
    b_docs = {"invariants": b_invs, "canonical_templates": canonical_tpls}
    binding: dict[str, Any] = {**b_id, **b_desc, **b_sc, **b_res, **b_docs}
    up_meta = {
        "layer_id": parent_id,
        "repository": "local-ephemeral-overlay",
        "branch": "ephemeral",
    }
    schema_ver = str(base_manifest.get("schema_version", LAYER_MANIFEST_CONTRACT_REV))
    em_head = {"schema_version": schema_ver, "layer_id": fork_id, "layer_role": "ephemeral-bot"}
    em_prec = {"precedence": ROLE_DEFAULT_PRECEDENCE["ephemeral-bot"], "upstream_layer": up_meta}
    em_desc = {"description": f"Ephemeral Department Bot ({role_clean}) scoped to {globs}"}
    em_mount = {"mounted_layers_dir": "layers", "mounted_layers": selected_layers}
    em_tpls = {"default_stack_templates": effective_templates, "surface_bindings": [binding]}
    em_guards = [
        f"Ephemeral Bot Role: {role_clean} (tier={model_tier}, access={access_mode}, "
        f"scope={eff_scope})",
        "AGENTS.md §12 (Return compact 4-Channel Executive Digest + rcap1 capsule)",
        *list(base_manifest.get("baseline_guardrails", [])),
    ]
    base_envs = dict(base_manifest.get("environments", {}))
    em_env = {"baseline_guardrails": em_guards, "environments": base_envs}
    em_tail = {"federated_mcps": [], "ephemeral_metadata": eph_meta}
    em_part1 = {**em_head, **em_prec, **em_desc, **em_mount}
    ephemeral_manifest: dict[str, Any] = {**em_part1, **em_tpls, **em_env, **em_tail}

    fork_dir = root / fork_id
    if not dry_run:
        for subdir in ("system", "layers", "logs"):
            (fork_dir / subdir).mkdir(parents=True, exist_ok=True)
        for item in ("antigravity", "docs", "templates", "VERSION"):
            if (repo_dir / item).exists() and not (fork_dir / item).exists():
                _copy_zero_copy(repo_dir / item, fork_dir / item)
        for lname in selected_layers:
            if lname != "ephemeral-project-bridge":
                _copy_zero_copy(parent_layers_dir / lname, fork_dir / "layers" / lname)
        if bridge_manifest:
            b_layer = fork_dir / "layers" / "ephemeral-project-bridge"
            for b_sub in ("antigravity/.gemini/config", "system"):
                (b_layer / b_sub).mkdir(parents=True, exist_ok=True)
            b_agents = b_layer / "antigravity/.gemini/config/AGENTS.md"
            b_agents.write_text(bridge_md, encoding="utf-8")
            b_json = json.dumps(bridge_manifest, indent=2, ensure_ascii=False) + "\n"
            (b_layer / "system/mcp-layer.json").write_text(b_json, encoding="utf-8")
        e_json = json.dumps(ephemeral_manifest, indent=2, ensure_ascii=False) + "\n"
        (fork_dir / "system/mcp-layer.json").write_text(e_json, encoding="utf-8")
    out_rt = {"dry_run": dry_run, "fork_dir": str(fork_dir), "bridged_project_files": bridged_files}
    return {**eph_meta, **out_rt, "reaped_expired": reaped, "manifest": ephemeral_manifest}


def inspect_ephemeral_forks(
    repo_dir: Path,
    fork_id: str | None = None,
    ephemeral_root: Path | None = None,
    now_epoch: float | None = None,
) -> dict[str, Any]:
    """List active ephemeral forks or inspect a specific fork_id after TTL cleanup."""
    reaped = reap_expired_ephemeral_forks(repo_dir, ephemeral_root, now_epoch=now_epoch)
    root = default_ephemeral_root(repo_dir, ephemeral_root)
    now, forks = now_epoch if now_epoch is not None else time.time(), []
    for child in sorted(root.iterdir()) if root.is_dir() else []:
        m_path = child / "system/mcp-layer.json"
        if not m_path.is_file() or (fork_id and child.name != fork_id):
            continue
        data = json.loads(m_path.read_text(encoding="utf-8"))
        meta = data.get("ephemeral_metadata", {})
        rem = max(0.0, round(float(meta.get("expires_at_epoch", 0.0)) - now, 1))
        f_id = {"fork_id": child.name, "fork_dir": str(child),
            "bot_role": str(meta.get("bot_role", ""))}  # fmt: skip
        f_mode = {"model_tier": str(meta.get("model_tier", "flash")),
            "access_mode": str(meta.get("access_mode", "strictly-read-only"))}  # fmt: skip
        f_scope = {"ephemeral_scope": str(meta.get("ephemeral_scope", "intra-layer")),
            "actor_role": str(meta.get("actor_role", "member")), "remaining_ttl_seconds": rem,
            "default_stack_templates": list(data.get("default_stack_templates", []))}  # fmt: skip
        forks.append({**f_id, **f_mode, **f_scope})
    if fork_id and not forks:
        if fork_id in reaped:
            raise FileNotFoundError(
                f"EPHEMERAL_FORK_EXPIRED: Ephemeral fork {fork_id!r} expired and was reaped."
            )
        raise FileNotFoundError(f"Ephemeral fork {fork_id!r} not found.")
    return {"active_count": len(forks), "reaped_expired": reaped, "forks": forks}


def reap_ephemeral_fork(
    repo_dir: Path, fork_id: str, ephemeral_root: Path | None = None, dry_run: bool = False
) -> dict[str, Any]:
    """Explicitly reap one ephemeral fork by fork_id or 'all' active ephemeral forks."""
    root, reaped = default_ephemeral_root(repo_dir, ephemeral_root), []
    if fork_id == "all":
        for child in sorted(root.iterdir()) if root.is_dir() else []:
            if child.is_dir():
                reaped.append(child.name)
                if not dry_run:
                    _ensure_dirs_writable(child)
                    shutil.rmtree(child, ignore_errors=True)
    else:
        if not KEBAB_ID_RE.match(fork_id):
            raise ValueError(f"Invalid fork_id {fork_id!r}: must be kebab-case or 'all'")
        target = (root / fork_id).resolve()
        if not target.is_relative_to(root) or not target.is_dir():
            raise FileNotFoundError(f"Ephemeral fork {fork_id!r} not found under {root}")
        reaped.append(fork_id)
        if not dry_run:
            _ensure_dirs_writable(target)
            shutil.rmtree(target, ignore_errors=True)
    if not dry_run:
        with contextlib.suppress(OSError):
            root.rmdir()
            root.parent.rmdir()
    return {"dry_run": dry_run, "reaped_forks": reaped}


def build_subagent_invocation_brief(
    manifest: dict[str, Any],
    target_path: str,
    surface_projection: dict[str, Any],
    capsule_token: str | None,
) -> dict[str, Any]:
    """Build a deterministic Antigravity invoke_subagent brief with 4-Channel digest contract."""
    meta = manifest.get("ephemeral_metadata", {})
    bot_role = str(meta.get("bot_role", manifest.get("layer_id", "ephemeral-bot")))
    model_tier = str(meta.get("model_tier", "flash"))
    access_mode = str(meta.get("access_mode", "strictly-read-only"))
    invariants = list(surface_projection.get("effective_invariants", []))
    eph_scope = str(meta.get("ephemeral_scope", "intra-layer"))
    actor_role = str(meta.get("actor_role", "member"))
    channels = [
        "1. Domain State",
        "2. Affected Surface",
        "3. Invariants & Constraints",
        "4. Actionable Delta",
    ]
    prompt_lines = [
        f"You are operating as Ephemeral Department Bot '{bot_role}' "
        f"(scope={eph_scope}, actor_role={actor_role}, access_mode={access_mode}, "
        f"model_tier={model_tier}).",
        f"Target Surface: {target_path or '*'}\nEnforced Invariants:",
        *(f"- {inv}" for inv in invariants[:MAX_BRIEF_INVARIANTS]),
        "Return ONLY a compact 4-Channel Executive Digest (AGENTS.md §12):",
        *(f"  {ch}" for ch in channels),
        *(
            [f"Sealed Context Capsule (rcap1): {capsule_token[:CAPSULE_BRIEF_PREVIEW_CHARS]}..."]
            if capsule_token
            else []
        ),
    ]
    s_type = "research" if access_mode == "strictly-read-only" else "self"
    b_head = {"subagent_type": s_type, "model_tier": model_tier, "access_mode": access_mode}
    b_role = {"role": f"Department Bot ({bot_role})", "ephemeral_scope": eph_scope}
    b_surf = {"actor_role": actor_role, "target_path": target_path or "*"}
    c_tpls = list(surface_projection.get("canonical_templates", []))
    b_inv = {"effective_invariants": invariants, "canonical_templates": c_tpls}
    b_hb = {"handback_channels": channels, "capsule_token": capsule_token}
    return {**b_head, **b_role, **b_surf, **b_inv, **b_hb, "prompt": "\n".join(prompt_lines)}
