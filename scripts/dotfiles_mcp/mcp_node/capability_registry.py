"""OOP MCP capability rings, bot archetype catalog, and Permanent <-> Ephemeral symbiosis.

Specification: docs/architecture/05_ephemeral_forks_and_department_bots.md
"""

from __future__ import annotations

import hashlib
import hmac
import os
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

from dotfiles_mcp.capsules.capsule_engine import (
    _parse_capsule_envelope,
    seal_dmcp_context_frame,
    seal_ephemeral_digest_capsule,
    unseal_ephemeral_digest_capsule,
    verify_dmcp_context_frame,
)
from dotfiles_mcp.core.constants import (
    CAPSULE_DIGEST_HEX_LEN,
    CAPSULE_REF_NAMESPACE,
    DEFAULT_EPHEMERAL_TTL_SECONDS,
    GIT_CMD_TIMEOUT_SECONDS,
    GRCC_CAPSULE_BLOB_PATH,
    ROLE_DEFAULT_PRECEDENCE,
    SAFE_GIT_REF_RE,
    VALID_GRCC_OPERATIONS,
)

MCP_PERMISSION_RINGS: tuple[dict[str, Any], ...] = (
    {
        "ring_id": "R0_DISCOVERY", "crud_permissions": ["read"], "persistence_mode": "permanent",
        "extension_class": "ResourcesMixin + FederationToolsMixin",
        "tools": [
            "get_layer_overview", "read_layer_document",
            "discover_federated_mcps", "audit_node_drift",
        ],
        "description": "Zero-mutation layer identity, topology, and drift telemetry.",
    },
    {
        "ring_id": "R1_COMPACTION", "crud_permissions": ["read", "filter"],
        "persistence_mode": "permanent",
        "extension_class": "CompactionToolsMixin + SurfaceToolsMixin",
        "tools": ["query_governance_rules", "resolve_surface_governance"],
        "description": "3D surface responsibility filtering and rcap1 L0/L1/L2 compaction.",
    },
    {
        "ring_id": "R2_CRYPTO_UNFOLD", "crud_permissions": ["read", "decrypt"],
        "persistence_mode": "hybrid-symbiotic", "extension_class": "UnfoldToolsMixin",
        "tools": ["unfold_context_capsule"],
        "description": "HMAC key, agent-tier, and surface-gated L1->L3 capsule decapsulation.",
    },
    {
        "ring_id": "W_EPHEMERAL_SANDBOX",
        "crud_permissions": ["create", "read", "update", "delete"],
        "persistence_mode": "ephemeral", "extension_class": "EphemeralToolsMixin",
        "tools": ["orchestrate_ephemeral_fork"],
        "description": "Scoped CoW ephemeral sandbox CRUD (spawn, evaluate, seal-return, reap).",
    },
    {
        "ring_id": "W_GOVERNANCE_PROPOSAL", "crud_permissions": ["create", "read", "update"],
        "persistence_mode": "permanent", "extension_class": "FederationToolsMixin",
        "tools": ["compare_layer_patterns"],
        "description": "Inter-layer pattern comparison and upward/downward proposal routing.",
    },
)  # fmt: skip

BOT_ARCHETYPE_CATALOG: tuple[dict[str, Any], ...] = (
    {
        "bot_role": "security-auditor-bot", "family": "audit-and-compliance",
        "recommended_tier": "inherit", "default_access_mode": "strictly-read-only",
        "default_encapsulation": "L2",
        "granted_rings": ["R0_DISCOVERY", "R1_COMPACTION", "R2_CRYPTO_UNFOLD"],
        "description": "Audits security boundaries, RBAC authority, and path-containment gates.",
    },
    {
        "bot_role": "doc-coherence-bot", "family": "audit-and-compliance",
        "recommended_tier": "flash", "default_access_mode": "strictly-read-only",
        "default_encapsulation": "L1", "granted_rings": ["R0_DISCOVERY", "R1_COMPACTION"],
        "description": "Sweeps markdown links, taxonomy parity, and 3-tier doc coherence.",
    },
    {
        "bot_role": "architecture-reviewer-bot", "family": "architecture-and-code",
        "recommended_tier": "pro", "default_access_mode": "strictly-read-only",
        "default_encapsulation": "L2",
        "granted_rings": ["R0_DISCOVERY", "R1_COMPACTION", "R2_CRYPTO_UNFOLD"],
        "description": "Evaluates relational cluster mass, DAG layering, and 1:1:1 symbiosis.",
    },
    {
        "bot_role": "refactoring-surgeon-bot", "family": "architecture-and-code",
        "recommended_tier": "inherit", "default_access_mode": "read-write-scoped",
        "default_encapsulation": "L2",
        "granted_rings": [
            "R0_DISCOVERY", "R1_COMPACTION", "R2_CRYPTO_UNFOLD", "W_EPHEMERAL_SANDBOX",
        ],
        "description": "Executes scoped module extractions and 1:1 unit test alignment.",
    },
    {
        "bot_role": "ops-ledger-bot", "family": "data-and-operations",
        "recommended_tier": "flash", "default_access_mode": "strictly-read-only",
        "default_encapsulation": "L1", "granted_rings": ["R0_DISCOVERY", "R1_COMPACTION"],
        "description": "Validates corporate-ops-ledger citations and Business AAA contracts.",
    },
    {
        "bot_role": "normative-analyst-bot", "family": "scientific-and-normative",
        "recommended_tier": "pro", "default_access_mode": "strictly-read-only",
        "default_encapsulation": "L2",
        "granted_rings": ["R0_DISCOVERY", "R1_COMPACTION", "R2_CRYPTO_UNFOLD"],
        "description": "Synthesizes territorial, legal, and scientific knowledge corpora.",
    },
)  # fmt: skip


def resolve_bot_archetype(bot_role: str) -> dict[str, Any]:
    """Resolve a canonical bot archetype from catalog or synthesize a custom role profile."""
    clean = bot_role.strip().lower() or "dept-specialist-bot"
    for entry in BOT_ARCHETYPE_CATALOG:
        if entry["bot_role"] == clean:
            return {**entry, "catalog_registered": True}
    return {
        "bot_role": clean,
        "family": "custom-departmental",
        "recommended_tier": "flash",
        "default_access_mode": "strictly-read-only",
        "default_encapsulation": "L2",
        "granted_rings": ["R0_DISCOVERY", "R1_COMPACTION", "R2_CRYPTO_UNFOLD"],
        "description": f"Custom departmental specialist bot ({clean}).",
        "catalog_registered": False,
    }


def resolve_mcp_capability_profile(
    manifest: dict[str, Any],
    *,
    environment: str = "all",
    active_ephemeral_forks: list[dict[str, Any]] | None = None,
    family_filter: str | None = None,
) -> dict[str, Any]:
    """Compute OOP capability rings, bot catalog, and Permanent <-> Ephemeral symbiosis state."""
    layer_id = str(manifest.get("layer_id", "root"))
    layer_role = str(manifest.get("layer_role", "workstation"))
    prec = int(manifest.get("precedence", ROLE_DEFAULT_PRECEDENCE.get(layer_role, 10)))
    env_clean = environment.strip().lower() or "all"
    env_cfg = manifest.get("environments", {}).get(env_clean, {})
    is_read_only_env = env_clean == "pro" or env_cfg.get("access_mode") == "strictly-read-only"
    granted_ring_ids = (
        ["R0_DISCOVERY", "R1_COMPACTION", "R2_CRYPTO_UNFOLD"]
        if is_read_only_env
        else [r["ring_id"] for r in MCP_PERMISSION_RINGS]
    )
    granted_rings = [dict(r) for r in MCP_PERMISSION_RINGS if r["ring_id"] in granted_ring_ids]

    forks = list(active_ephemeral_forks or [])
    hot_leases: list[dict[str, Any]] = []
    for fk in forks:
        arch = resolve_bot_archetype(str(fk.get("bot_role", "")))
        hot_leases.append(
            {
                "fork_id": str(fk.get("fork_id", "")),
                "bot_role": arch["bot_role"],
                "family": arch["family"],
                "granted_rings": arch["granted_rings"],
                "remaining_ttl_seconds": float(fk.get("remaining_ttl_seconds", 0.0)),
            }
        )
    symbiotic_state = "ephemeral-augmented" if hot_leases else "basal-permanent-only"
    fam_clean = (family_filter or "").strip().lower()
    catalog = [dict(b) for b in BOT_ARCHETYPE_CATALOG if not fam_clean or b["family"] == fam_clean]
    families = sorted({b["family"] for b in BOT_ARCHETYPE_CATALOG})
    return {
        "layer_id": layer_id,
        "layer_role": layer_role,
        "precedence": prec,
        "environment": env_clean,
        "oop_capability_inheritance": {
            "kernel_base": "MCPNodeBase",
            "granted_ring_ids": granted_ring_ids,
            "permission_rings": granted_rings,
        },
        "permanent_ephemeral_symbiosis": {
            "symbiotic_state": symbiotic_state,
            "zero_standing_privileges": True,
            "permanent_to_ephemeral_grants": [
                "lineage_0_to_80_inheritance",
                "surface_filtered_rcap1_capsules",
                "centralized_audit_telemetry",
            ],
            "ephemeral_to_permanent_hotplug": {
                "active_leases_count": len(hot_leases),
                "hot_plugged_leases": hot_leases,
                "ephemeral_crypto_keys_mounted": len(hot_leases),
            },
        },
        "bot_families": families,
        "bot_archetype_catalog": catalog,
    }


def orchestrate_ephemeral_return_capsule(
    action: str,
    *,
    fork_id: str | None,
    parent_layer_id: str,
    meta_resolver: Callable[[str, str], dict[str, Any] | None],
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Execute seal-return or verify-return for an Ephemeral Bot's 4-Channel Executive Digest."""
    if action == "seal-return":
        if not fork_id:
            raise ValueError("Missing required 'fork_id' for action='seal-return'")
        active_meta = meta_resolver(fork_id, parent_layer_id)
        if active_meta is None:
            raise ValueError(
                f"EPHEMERAL_FORK_EXPIRED: Cannot seal return digest for inactive fork {fork_id!r}"
            )
        digest_raw = arguments.get("digest")
        if not isinstance(digest_raw, dict):
            raise ValueError("Missing or invalid 'digest' dict for action='seal-return'")
        globs = list(active_meta.get("target_globs") or arguments.get("target_globs") or ["**"])
        sealed = seal_ephemeral_digest_capsule(
            fork_id=fork_id,
            bot_role=str(active_meta.get("bot_role", "dept-specialist-bot")),
            parent_layer_id=parent_layer_id,
            surface_globs=globs,
            digest_channels=digest_raw,
            session_key=str(active_meta.get("session_resonance_key", "")),
        )
        return {"action": "seal-return", **sealed}

    token = str(arguments.get("capsule_token") or "").strip()
    if not token:
        raise ValueError("Missing required 'capsule_token' for action='verify-return'")
    header, _, _, _ = _parse_capsule_envelope(token)
    target_fid = fork_id or str(header.get("iss", ""))
    active_meta = meta_resolver(target_fid, parent_layer_id)
    unsealed = unseal_ephemeral_digest_capsule(
        token,
        expected_parent_layer_id=parent_layer_id,
        active_fork_meta=active_meta,
    )
    return {"action": "verify-return", **unsealed}


def compute_grcc_scope_fingerprint(
    layer_id: str,
    branch_ref: str,
    task_scope: str,
) -> tuple[str, str]:
    """Compute a deterministic HMAC-SHA256 GRCC scope fingerprint and refs/capsules/<fp> ref."""
    lid = layer_id.strip() or "root"
    bref = branch_ref.strip() or "master"
    tscope = task_scope.strip() or "default"
    fp = hmac.new(b"grcc-scope-v1", f"{lid}:{bref}:{tscope}".encode(), hashlib.sha256).hexdigest()[
        :CAPSULE_DIGEST_HEX_LEN
    ]
    return fp, f"{CAPSULE_REF_NAMESPACE}{fp}"


def _run_git_plumbing(
    repo_dir: Path,
    args: list[str],
    *,
    stdin_text: str | None = None,
    check: bool = False,
) -> subprocess.CompletedProcess[str]:
    """Execute a stateless Git plumbing subcommand against repo_dir without mutating HEAD."""
    git_bin = shutil.which("git") or "git"
    git_env = {
        "GIT_AUTHOR_NAME": "dotfiles-mcp-grcc",
        "GIT_AUTHOR_EMAIL": "grcc@dotfiles-mcp.local",
        "GIT_COMMITTER_NAME": "dotfiles-mcp-grcc",
        "GIT_COMMITTER_EMAIL": "grcc@dotfiles-mcp.local",
        **os.environ,
    }
    return subprocess.run(  # noqa: S603
        [git_bin, "-C", str(repo_dir), *args],
        input=stdin_text,
        capture_output=True,
        text=True,
        env=git_env,
        timeout=GIT_CMD_TIMEOUT_SECONDS,
        check=check,
    )


def orchestrate_dmcp_branch_projection(
    repo_dir: Path,
    parent_layer_id: str,
    arguments: dict[str, Any],
    *,
    default_secret: str,
) -> dict[str, Any]:
    """Project a zero-checkout DMCP branch context frame with fail-closed master fallback."""
    branch_ref = str(arguments.get("branch_ref") or "master").strip()
    task_step_id = str(arguments.get("task_step_id") or "step-1").strip()
    target_path = str(arguments.get("target_path") or "").strip()
    surface_globs = [str(g) for g in arguments.get("target_globs", []) if str(g).strip()] or ["**"]
    ttl_seconds = int(arguments.get("ttl_seconds") or DEFAULT_EPHEMERAL_TTL_SECONDS)
    session_key = str(arguments.get("resonance_key") or default_secret).strip()
    incoming_token = str(arguments.get("context_frame_token") or "").strip()
    parent_frame_hash = "genesis"
    if incoming_token:
        verified_in = verify_dmcp_context_frame(
            incoming_token,
            expected_repo_id=parent_layer_id,
            session_key=session_key,
            target_path=target_path,
        )
        if not verified_in["verified"]:
            return {"action": "project-branch", "zero_checkout": True, **verified_in}
        parent_frame_hash = str(verified_in["frame_hash"])
    valid_ref = (
        bool(branch_ref)
        and ".." not in branch_ref
        and not branch_ref.startswith("-")
        and bool(SAFE_GIT_REF_RE.match(branch_ref))
    )
    sha_proc = (
        _run_git_plumbing(repo_dir, ["rev-parse", "--verify", f"{branch_ref}^{{commit}}"])
        if valid_ref
        else None
    )
    if sha_proc is None or sha_proc.returncode != 0:
        return {
            "action": "project-branch", "verified": False,
            "error_code": "DMCP_CONTEXT_FRAME_INVALID",
            "reason": f"Branch ref {branch_ref!r} not found or invalid",
            "effective_branch_ref": "master", "fallback_activated": True, "zero_checkout": True,
        }  # fmt: skip
    sealed = seal_dmcp_context_frame(
        repo_id=parent_layer_id,
        branch_ref=branch_ref,
        commit_sha=sha_proc.stdout.strip(),
        task_step_id=task_step_id,
        surface_globs=surface_globs,
        parent_frame_hash=parent_frame_hash,
        ttl_seconds=ttl_seconds,
        session_key=session_key,
    )
    return {
        "action": "project-branch", "verified": True, "error_code": None,
        "fallback_activated": False, "effective_branch_ref": branch_ref,
        "zero_checkout": True, **sealed,
    }  # fmt: skip


def orchestrate_grcc_capsule_ref(
    repo_dir: Path,
    parent_layer_id: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Execute GRCC O(1) probe, pre-sealed .rcap1 commit chaining, unfold, or ref pruning."""
    grcc_op = str(arguments.get("grcc_op") or "probe").strip().lower()
    if grcc_op not in VALID_GRCC_OPERATIONS:
        raise ValueError(f"Invalid grcc_op {grcc_op!r}: must be one of {VALID_GRCC_OPERATIONS}")
    branch_ref = str(arguments.get("branch_ref") or "master").strip()
    task_scope = str(
        arguments.get("task_step_id") or arguments.get("target_path") or "default"
    ).strip()
    scope_fp, capsule_ref = compute_grcc_scope_fingerprint(parent_layer_id, branch_ref, task_scope)

    def _read_lineage() -> tuple[str | None, str | None]:
        proc = _run_git_plumbing(repo_dir, ["log", "-n", "1", "--format=%H:%P", capsule_ref])
        if proc.returncode != 0 or not proc.stdout.strip():
            return None, None
        c_sha, _, p_raw = proc.stdout.strip().partition(":")
        return c_sha, (p_raw.split()[0] if p_raw.strip() else None)

    if grcc_op == "probe":
        remote = str(arguments.get("remote") or "").strip()
        if remote:
            r_proc = _run_git_plumbing(repo_dir, ["ls-remote", "--exit-code", remote, capsule_ref])
            exists = r_proc.returncode == 0 and bool(r_proc.stdout.strip())
            c_sha, p_sha = (r_proc.stdout.split()[0] if exists else None), None
        else:
            c_sha, p_sha = _read_lineage()
            exists = c_sha is not None
        return {
            "action": "chain-capsule-ref", "grcc_op": "probe", "exists": exists,
            "capsule_ref": capsule_ref, "scope_fingerprint": scope_fp,
            "commit_sha": c_sha, "parent_commit_sha": p_sha, "zero_checkout": True,
        }  # fmt: skip

    if grcc_op == "seal":
        capsule_token = str(arguments.get("capsule_token") or "").strip()
        if not capsule_token:
            raise ValueError("Missing required 'capsule_token' for grcc_op='seal'")
        header, _, _, _ = _parse_capsule_envelope(capsule_token)
        parent_sha, _ = _read_lineage()
        blob_sha = _run_git_plumbing(
            repo_dir, ["hash-object", "-w", "--stdin"], stdin_text=capsule_token, check=True
        ).stdout.strip()
        agents_tree = _run_git_plumbing(
            repo_dir,
            ["mktree"],
            stdin_text=f"100644 blob {blob_sha}\tcapsule.rcap1\n",
            check=True,
        ).stdout.strip()
        root_tree = _run_git_plumbing(
            repo_dir, ["mktree"], stdin_text=f"040000 tree {agents_tree}\t.agents\n", check=True
        ).stdout.strip()
        commit_args = [
            "commit-tree", root_tree, *(["-p", parent_sha] if parent_sha else []),
            "-m", f"grcc({task_scope}): pre-sealed rcap1 capsule",
        ]  # fmt: skip
        commit_sha = _run_git_plumbing(repo_dir, commit_args, check=True).stdout.strip()
        _run_git_plumbing(repo_dir, ["update-ref", capsule_ref, commit_sha], check=True)
        return {
            "action": "chain-capsule-ref", "grcc_op": "seal", "sealed": True,
            "capsule_ref": capsule_ref, "scope_fingerprint": scope_fp,
            "blob_path": GRCC_CAPSULE_BLOB_PATH, "commit_sha": commit_sha,
            "parent_commit_sha": parent_sha, "capsule_header": header, "zero_checkout": True,
        }  # fmt: skip

    if grcc_op == "unfold":
        show_proc = _run_git_plumbing(repo_dir, ["show", f"{capsule_ref}:{GRCC_CAPSULE_BLOB_PATH}"])
        if show_proc.returncode != 0:
            raise ValueError(f"GRCC_CAPSULE_REF_NOT_FOUND: No pre-sealed capsule at {capsule_ref}")
        capsule_token = show_proc.stdout.strip()
        header, _, _, _ = _parse_capsule_envelope(capsule_token)
        c_sha, parent_sha = _read_lineage()
        return {
            "action": "chain-capsule-ref", "grcc_op": "unfold",
            "capsule_ref": capsule_ref, "scope_fingerprint": scope_fp,
            "blob_path": GRCC_CAPSULE_BLOB_PATH, "commit_sha": c_sha,
            "parent_commit_sha": parent_sha, "capsule_token": capsule_token,
            "capsule_header": header, "zero_checkout": True,
        }  # fmt: skip

    _run_git_plumbing(repo_dir, ["update-ref", "-d", capsule_ref])
    return {
        "action": "chain-capsule-ref", "grcc_op": "prune", "pruned": True,
        "capsule_ref": capsule_ref, "scope_fingerprint": scope_fp, "zero_checkout": True,
    }  # fmt: skip
