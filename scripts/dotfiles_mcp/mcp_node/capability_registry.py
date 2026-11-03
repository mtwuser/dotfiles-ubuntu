"""OOP MCP capability rings, bot archetype catalog, and Permanent <-> Ephemeral symbiosis.

Specification: docs/architecture/05_ephemeral_forks_and_department_bots.md
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from dotfiles_mcp.capsules.capsule_engine import (
    _parse_capsule_envelope,
    seal_ephemeral_digest_capsule,
    unseal_ephemeral_digest_capsule,
)
from dotfiles_mcp.core.constants import ROLE_DEFAULT_PRECEDENCE

MCP_PERMISSION_RINGS: tuple[dict[str, Any], ...] = (
    {
        "ring_id": "R0_DISCOVERY",
        "crud_permissions": ["read"],
        "persistence_mode": "permanent",
        "extension_class": "ResourcesMixin + FederationToolsMixin",
        "tools": [
            "get_layer_overview",
            "read_layer_document",
            "discover_federated_mcps",
            "audit_node_drift",
        ],
        "description": "Zero-mutation layer identity, topology, and drift telemetry.",
    },
    {
        "ring_id": "R1_COMPACTION",
        "crud_permissions": ["read", "filter"],
        "persistence_mode": "permanent",
        "extension_class": "CompactionToolsMixin + SurfaceToolsMixin",
        "tools": ["query_governance_rules", "resolve_surface_governance"],
        "description": "3D surface responsibility filtering and rcap1 L0/L1/L2 compaction.",
    },
    {
        "ring_id": "R2_CRYPTO_UNFOLD",
        "crud_permissions": ["read", "decrypt"],
        "persistence_mode": "hybrid-symbiotic",
        "extension_class": "UnfoldToolsMixin",
        "tools": ["unfold_context_capsule"],
        "description": "HMAC key, agent-tier, and surface-gated L1->L3 capsule decapsulation.",
    },
    {
        "ring_id": "W_EPHEMERAL_SANDBOX",
        "crud_permissions": ["create", "read", "update", "delete"],
        "persistence_mode": "ephemeral",
        "extension_class": "EphemeralToolsMixin",
        "tools": ["orchestrate_ephemeral_fork"],
        "description": "Scoped CoW ephemeral sandbox CRUD (spawn, evaluate, seal-return, reap).",
    },
    {
        "ring_id": "W_GOVERNANCE_PROPOSAL",
        "crud_permissions": ["create", "read", "update"],
        "persistence_mode": "permanent",
        "extension_class": "FederationToolsMixin",
        "tools": ["compare_layer_patterns"],
        "description": "Inter-layer pattern comparison and upward/downward proposal routing.",
    },
)

BOT_ARCHETYPE_CATALOG: tuple[dict[str, Any], ...] = (
    {
        "bot_role": "security-auditor-bot",
        "family": "audit-and-compliance",
        "recommended_tier": "inherit",
        "default_access_mode": "strictly-read-only",
        "default_encapsulation": "L2",
        "granted_rings": ["R0_DISCOVERY", "R1_COMPACTION", "R2_CRYPTO_UNFOLD"],
        "description": "Audits security boundaries, RBAC authority, and path-containment gates.",
    },
    {
        "bot_role": "doc-coherence-bot",
        "family": "audit-and-compliance",
        "recommended_tier": "flash",
        "default_access_mode": "strictly-read-only",
        "default_encapsulation": "L1",
        "granted_rings": ["R0_DISCOVERY", "R1_COMPACTION"],
        "description": "Sweeps markdown links, taxonomy parity, and 3-tier doc coherence.",
    },
    {
        "bot_role": "architecture-reviewer-bot",
        "family": "architecture-and-code",
        "recommended_tier": "pro",
        "default_access_mode": "strictly-read-only",
        "default_encapsulation": "L2",
        "granted_rings": ["R0_DISCOVERY", "R1_COMPACTION", "R2_CRYPTO_UNFOLD"],
        "description": "Evaluates relational cluster mass, DAG layering, and 1:1:1 symbiosis.",
    },
    {
        "bot_role": "refactoring-surgeon-bot",
        "family": "architecture-and-code",
        "recommended_tier": "inherit",
        "default_access_mode": "read-write-scoped",
        "default_encapsulation": "L2",
        "granted_rings": [
            "R0_DISCOVERY",
            "R1_COMPACTION",
            "R2_CRYPTO_UNFOLD",
            "W_EPHEMERAL_SANDBOX",
        ],
        "description": "Executes scoped module extractions and 1:1 unit test alignment.",
    },
    {
        "bot_role": "ops-ledger-bot",
        "family": "data-and-operations",
        "recommended_tier": "flash",
        "default_access_mode": "strictly-read-only",
        "default_encapsulation": "L1",
        "granted_rings": ["R0_DISCOVERY", "R1_COMPACTION"],
        "description": "Validates corporate-ops-ledger citations and Business AAA contracts.",
    },
    {
        "bot_role": "normative-analyst-bot",
        "family": "scientific-and-normative",
        "recommended_tier": "pro",
        "default_access_mode": "strictly-read-only",
        "default_encapsulation": "L2",
        "granted_rings": ["R0_DISCOVERY", "R1_COMPACTION", "R2_CRYPTO_UNFOLD"],
        "description": "Synthesizes territorial, legal, and scientific knowledge corpora.",
    },
)


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
