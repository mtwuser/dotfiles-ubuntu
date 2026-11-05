"""1:1 unit tests for scripts/dotfiles_mcp/mcp_node/capability_registry.py.

Specification: docs/architecture/05_ephemeral_forks_and_department_bots.md
"""

from __future__ import annotations

import subprocess

import pytest
from dotfiles_mcp.capsules.capsule_engine import CapsuleError
from dotfiles_mcp.core.constants import REPO_DIR
from dotfiles_mcp.mcp_node.capability_registry import (
    compute_grcc_scope_fingerprint,
    orchestrate_dmcp_branch_projection,
    orchestrate_ephemeral_return_capsule,
    orchestrate_grcc_capsule_ref,
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

    def test_orchestrate_dmcp_branch_projection_and_grcc_capsule_ref_lifecycle(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Execute DMCP context frame chaining and GRCC probe, seal, unfold, and prune."""
        # Arrange
        fp, ref = compute_grcc_scope_fingerprint("dept-sec", "HEAD", "unit-grcc-scope")
        step1 = orchestrate_dmcp_branch_projection(
            REPO_DIR,
            "dept-sec",
            {"branch_ref": "HEAD", "task_step_id": "step-1", "target_globs": ["src/**"]},
            default_secret=fp,
        )
        step2 = orchestrate_dmcp_branch_projection(
            REPO_DIR,
            "dept-sec",
            {
                "branch_ref": "HEAD",
                "task_step_id": "step-2",
                "context_frame_token": step1["context_frame_token"],
                "target_path": "src/a.py",
            },
            default_secret=fp,
        )
        bad_in = orchestrate_dmcp_branch_projection(
            REPO_DIR,
            "dept-sec",
            {"branch_ref": "HEAD", "context_frame_token": "invalid-token"},
            default_secret=fp,
        )
        bad_ref = orchestrate_dmcp_branch_projection(
            REPO_DIR,
            "dept-sec",
            {"branch_ref": "--bad-ref"},
            default_secret=fp,
        )

        # Act
        probe_miss = orchestrate_grcc_capsule_ref(
            REPO_DIR, "dept-sec", {"grcc_op": "probe", "branch_ref": "HEAD", "task_step_id": fp}
        )
        sealed_1 = orchestrate_grcc_capsule_ref(
            REPO_DIR,
            "dept-sec",
            {
                "grcc_op": "seal",
                "branch_ref": "HEAD",
                "task_step_id": fp,
                "capsule_token": step1["context_frame_token"],
            },
        )
        sealed_2 = orchestrate_grcc_capsule_ref(
            REPO_DIR,
            "dept-sec",
            {
                "grcc_op": "seal",
                "branch_ref": "HEAD",
                "task_step_id": fp,
                "capsule_token": step2["context_frame_token"],
            },
        )
        probe_hit = orchestrate_grcc_capsule_ref(
            REPO_DIR, "dept-sec", {"grcc_op": "probe", "branch_ref": "HEAD", "task_step_id": fp}
        )
        unfolded = orchestrate_grcc_capsule_ref(
            REPO_DIR, "dept-sec", {"grcc_op": "unfold", "branch_ref": "HEAD", "task_step_id": fp}
        )
        pruned = orchestrate_grcc_capsule_ref(
            REPO_DIR, "dept-sec", {"grcc_op": "prune", "branch_ref": "HEAD", "task_step_id": fp}
        )
        monkeypatch.setattr(
            "dotfiles_mcp.mcp_node.capability_registry._run_git_plumbing",
            lambda _r, _a, **_k: subprocess.CompletedProcess(
                args=[], returncode=0, stdout=f"deadbeef\t{ref}\n", stderr=""
            ),
        )
        remote_probe = orchestrate_grcc_capsule_ref(
            REPO_DIR,
            "dept-sec",
            {"grcc_op": "probe", "branch_ref": "HEAD", "task_step_id": fp, "remote": "origin"},
        )

        # Assert
        assert step1["verified"] is True and step2["parent_frame_hash"] == step1["frame_hash"]
        assert bad_in["fallback_activated"] is True and bad_ref["fallback_activated"] is True
        assert probe_miss["exists"] is False and probe_hit["exists"] is True
        assert sealed_1["parent_commit_sha"] is None
        assert sealed_2["parent_commit_sha"] == sealed_1["commit_sha"]
        assert unfolded["capsule_token"] == step2["context_frame_token"]
        assert pruned["pruned"] is True and remote_probe["commit_sha"] == "deadbeef"
        with pytest.raises(ValueError, match="Invalid grcc_op"):
            orchestrate_grcc_capsule_ref(REPO_DIR, "dept-sec", {"grcc_op": "bad"})
        with pytest.raises(ValueError, match="Missing required 'capsule_token'"):
            orchestrate_grcc_capsule_ref(REPO_DIR, "dept-sec", {"grcc_op": "seal"})
        monkeypatch.setattr(
            "dotfiles_mcp.mcp_node.capability_registry._run_git_plumbing",
            lambda _r, _a, **_k: subprocess.CompletedProcess(
                args=[], returncode=1, stdout="", stderr=""
            ),
        )
        with pytest.raises(ValueError, match="GRCC_CAPSULE_REF_NOT_FOUND"):
            orchestrate_grcc_capsule_ref(REPO_DIR, "dept-sec", {"grcc_op": "unfold"})
