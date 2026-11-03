"""1:1 unit tests for scripts/dotfiles_mcp/mcp_node/capability_registry.py.

Specification: docs/architecture/05_ephemeral_forks_and_department_bots.md
"""

from __future__ import annotations

import pytest
from dotfiles_mcp.capsules.capsule_engine import CapsuleError
from dotfiles_mcp.mcp_node.capability_registry import (
    orchestrate_ephemeral_return_capsule,
    resolve_bot_archetype,
    resolve_mcp_capability_profile,
)


class TestCapabilityRegistry:
    """Verify OOP MCP permission rings, bot archetype catalog, and symbiotic return capsules."""

    def test_resolve_bot_archetype_and_capability_profile_across_environments(self) -> None:
        """Resolve catalog vs custom bot archetypes and Permanent <-> Ephemeral symbiosis state."""
        # Arrange
        manifest = {
            "layer_id": "dept-security",
            "layer_role": "department",
            "precedence": 30,
            "environments": {"pre": {"access_mode": "strictly-read-only"}},
        }
        active_forks = [
            {
                "fork_id": "eph-sec-1",
                "bot_role": "security-auditor-bot",
                "remaining_ttl_seconds": 240.0,
            }
        ]

        # Act
        known_arch = resolve_bot_archetype("security-auditor-bot")
        custom_arch = resolve_bot_archetype("custom-ops-bot")
        dev_prof = resolve_mcp_capability_profile(manifest, environment="dev")
        pro_prof = resolve_mcp_capability_profile(
            manifest,
            environment="pro",
            active_ephemeral_forks=active_forks,
            family_filter="audit-and-compliance",
        )

        # Assert
        assert known_arch["catalog_registered"] is True
        assert known_arch["family"] == "audit-and-compliance"
        assert custom_arch["catalog_registered"] is False
        assert custom_arch["family"] == "custom-departmental"
        assert len(dev_prof["oop_capability_inheritance"]["granted_ring_ids"]) == 5
        assert (
            dev_prof["permanent_ephemeral_symbiosis"]["symbiotic_state"] == "basal-permanent-only"
        )
        assert pro_prof["oop_capability_inheritance"]["granted_ring_ids"] == [
            "R0_DISCOVERY",
            "R1_COMPACTION",
            "R2_CRYPTO_UNFOLD",
        ]
        assert pro_prof["permanent_ephemeral_symbiosis"]["symbiotic_state"] == "ephemeral-augmented"
        assert (
            pro_prof["permanent_ephemeral_symbiosis"]["ephemeral_to_permanent_hotplug"][
                "active_leases_count"
            ]
            == 1
        )
        assert all(b["family"] == "audit-and-compliance" for b in pro_prof["bot_archetype_catalog"])

    def test_orchestrate_ephemeral_return_capsule_seals_verifies_and_guards(self) -> None:
        """Seal and verify an Ephemeral Bot's 4-Channel Digest and enforce lease/input guards."""
        # Arrange
        active_store: dict[str, dict[str, object]] = {
            "eph-1": {
                "bot_role": "security-auditor-bot",
                "session_resonance_key": "k-sec-123",
                "target_globs": ["src/api/**"],
            }
        }
        digest = {
            "channel_1_domain_state": "API layer audited",
            "channel_2_affected_surface": ["src/api/routes.py"],
            "channel_3_invariants_and_constraints": ["RBAC enforced"],
            "channel_4_actionable_delta": ["Zero findings"],
        }

        def _resolver(fid: str, pid: str) -> dict[str, object] | None:
            return active_store.get(fid) if pid == "dept-sec" else None

        # Act
        sealed = orchestrate_ephemeral_return_capsule(
            "seal-return",
            fork_id="eph-1",
            parent_layer_id="dept-sec",
            meta_resolver=_resolver,
            arguments={"digest": digest},
        )
        verified = orchestrate_ephemeral_return_capsule(
            "verify-return",
            fork_id=None,
            parent_layer_id="dept-sec",
            meta_resolver=_resolver,
            arguments={"capsule_token": sealed["capsule_token"]},
        )

        # Assert
        assert sealed["action"] == "seal-return" and sealed["fork_id"] == "eph-1"
        assert verified["action"] == "verify-return" and verified["verified"] is True
        assert verified["digest"]["channel_1_domain_state"] == "API layer audited"
        with pytest.raises(ValueError, match="Missing required 'fork_id'"):
            orchestrate_ephemeral_return_capsule(
                "seal-return",
                fork_id=None,
                parent_layer_id="dept-sec",
                meta_resolver=_resolver,
                arguments={"digest": digest},
            )
        with pytest.raises(ValueError, match="EPHEMERAL_FORK_EXPIRED"):
            orchestrate_ephemeral_return_capsule(
                "seal-return",
                fork_id="eph-expired",
                parent_layer_id="dept-sec",
                meta_resolver=_resolver,
                arguments={"digest": digest},
            )
        with pytest.raises(ValueError, match="Missing or invalid 'digest'"):
            orchestrate_ephemeral_return_capsule(
                "seal-return",
                fork_id="eph-1",
                parent_layer_id="dept-sec",
                meta_resolver=_resolver,
                arguments={"digest": "not-a-dict"},
            )
        with pytest.raises(ValueError, match="Missing required 'capsule_token'"):
            orchestrate_ephemeral_return_capsule(
                "verify-return",
                fork_id="eph-1",
                parent_layer_id="dept-sec",
                meta_resolver=_resolver,
                arguments={},
            )
        active_store.clear()
        with pytest.raises(CapsuleError, match="EPHEMERAL_LEASE_EXPIRED_OR_SHREDDED"):
            orchestrate_ephemeral_return_capsule(
                "verify-return",
                fork_id="eph-1",
                parent_layer_id="dept-sec",
                meta_resolver=_resolver,
                arguments={"capsule_token": sealed["capsule_token"]},
            )
