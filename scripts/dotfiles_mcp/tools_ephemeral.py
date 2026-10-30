"""MCP Tool #9 (orchestrate_ephemeral_fork) for Department Bots and scoped ephemeral forks.

Specification: docs/architecture/05_ephemeral_forks_and_department_bots.md
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dotfiles_mcp.constants import (
    DEFAULT_EPHEMERAL_TTL_SECONDS,
    VALID_EPHEMERAL_ACTIONS,
)
from dotfiles_mcp.ephemeral_fork_engine import (
    build_subagent_invocation_brief,
    default_ephemeral_root,
    inspect_ephemeral_forks,
    reap_ephemeral_fork,
    spawn_ephemeral_fork,
)
from dotfiles_mcp.tools_surface import SurfaceToolsMixin


class EphemeralToolsMixin(SurfaceToolsMixin):
    """Mixin providing MCP tool orchestrate_ephemeral_fork (spawn, inspect, evaluate, reap)."""

    def _tool_orchestrate_ephemeral_fork(self, arguments: dict[str, Any]) -> dict[str, Any]:
        action = str(arguments.get("action") or "evaluate").strip().lower()
        if action not in VALID_EPHEMERAL_ACTIONS:
            raise ValueError(f"Invalid action {action!r}: must be one of {VALID_EPHEMERAL_ACTIONS}")
        fork_id = str(arguments.get("fork_id") or "").strip() or None
        bot_role = str(arguments.get("bot_role") or "dept-specialist-bot").strip()
        target_path = str(arguments.get("target_path") or "").strip()
        model_tier = str(arguments.get("model_tier") or "flash").strip().lower()
        access_mode = str(arguments.get("access_mode") or "strictly-read-only").strip().lower()
        resolution = str(arguments.get("resolution") or "L2").strip().upper()
        ttl_seconds = int(arguments.get("ttl_seconds") or DEFAULT_EPHEMERAL_TTL_SECONDS)
        one_shot = bool(arguments.get("one_shot", True))
        target_globs = [str(g) for g in arguments.get("target_globs", []) if str(g).strip()] or None
        planes = [
            str(p) for p in arguments.get("architectural_planes", []) if str(p).strip()
        ] or None
        mount_templates = (
            [str(t) for t in arguments.get("mount_templates", []) if str(t).strip()]
            if "mount_templates" in arguments
            else None
        )
        mount_layers = (
            [str(l_id) for l_id in arguments.get("mount_layers", []) if str(l_id).strip()]
            if "mount_layers" in arguments
            else None
        )
        project_bridge_arg = str(arguments.get("mount_project_rules_from") or "").strip()
        project_bridge_path = Path(project_bridge_arg) if project_bridge_arg else None

        if action == "inspect":
            try:
                inspected = inspect_ephemeral_forks(self.repo_dir, fork_id=fork_id)
            except FileNotFoundError as exc:
                if "EPHEMERAL_FORK_EXPIRED" in str(exc):
                    self._emit_warning(
                        "WARN",
                        "EPHEMERAL_FORK_EXPIRED",
                        str(exc),
                        {"fork_id": fork_id or ""},
                    )
                raise ValueError(str(exc)) from exc
            return {
                "content": [{"type": "text", "text": json.dumps(inspected, indent=2)}],
                "isError": False,
            }

        if action == "reap":
            if not fork_id:
                raise ValueError("Missing required 'fork_id' (or 'all') for action='reap'")
            reaped_res = reap_ephemeral_fork(self.repo_dir, fork_id=fork_id)
            return {
                "content": [{"type": "text", "text": json.dumps(reaped_res, indent=2)}],
                "isError": False,
            }

        try:
            if action == "spawn" or not fork_id:
                try:
                    spawned = spawn_ephemeral_fork(
                        self.repo_dir,
                        self._load_layer_manifest(),
                        bot_role=bot_role,
                        target_globs=target_globs,
                        architectural_planes=planes,
                        mount_templates=mount_templates,
                        mount_layers=mount_layers,
                        mount_project_rules_from=project_bridge_path,
                        model_tier=model_tier,
                        access_mode=access_mode,
                        resolution=resolution,
                        ttl_seconds=ttl_seconds,
                    )
                except OSError:
                    if action != "evaluate" or not one_shot:
                        raise
                    spawned = spawn_ephemeral_fork(
                        self.repo_dir,
                        self._load_layer_manifest(),
                        bot_role=bot_role,
                        target_globs=target_globs,
                        architectural_planes=planes,
                        mount_templates=mount_templates,
                        mount_layers=mount_layers,
                        mount_project_rules_from=project_bridge_path,
                        model_tier=model_tier,
                        access_mode=access_mode,
                        resolution=resolution,
                        ttl_seconds=ttl_seconds,
                        dry_run=True,
                    )
            else:
                inspect_ephemeral_forks(self.repo_dir, fork_id=fork_id)
                fork_dir_existing = default_ephemeral_root(self.repo_dir) / fork_id
                manifest_existing = json.loads(
                    (fork_dir_existing / "system" / "mcp-layer.json").read_text(encoding="utf-8")
                )
                meta_existing = manifest_existing.get("ephemeral_metadata", {})
                spawned = {
                    "fork_id": fork_id,
                    "fork_dir": str(fork_dir_existing),
                    "bot_role": str(meta_existing.get("bot_role", bot_role)),
                    "model_tier": str(meta_existing.get("model_tier", model_tier)),
                    "access_mode": str(meta_existing.get("access_mode", access_mode)),
                    "ttl_seconds": int(meta_existing.get("ttl_seconds", ttl_seconds)),
                    "expires_at_epoch": float(meta_existing.get("expires_at_epoch", 0.0)),
                    "session_resonance_key": str(meta_existing.get("session_resonance_key", "")),
                    "bridged_project_files": [],
                    "reaped_expired": [],
                    "manifest": manifest_existing,
                }
        except (ValueError, FileNotFoundError) as exc:
            msg = str(exc)
            if "EPHEMERAL_FORK_LIMIT_REACHED" in msg:
                self._emit_warning(
                    "WARN", "EPHEMERAL_FORK_LIMIT_REACHED", msg, {"bot_role": bot_role}
                )
            elif "EPHEMERAL_FORK_EXPIRED" in msg:
                self._emit_warning(
                    "WARN", "EPHEMERAL_FORK_EXPIRED", msg, {"fork_id": fork_id or ""}
                )
            raise ValueError(msg) from exc

        if action == "spawn":
            return {
                "content": [{"type": "text", "text": json.dumps(spawned, indent=2)}],
                "isError": False,
            }

        ephemeral_dir = Path(str(spawned["fork_dir"]))
        is_materialized = ephemeral_dir.is_dir()
        ephemeral_node = SurfaceToolsMixin(
            repo_dir=ephemeral_dir if is_materialized else self.repo_dir,
            log_dir=None,
        )
        if not is_materialized:
            ephemeral_node._load_layer_manifest = (  # type: ignore[method-assign]
                lambda target_dir=None: (
                    spawned["manifest"]
                    if (target_dir is None or Path(target_dir).resolve() == self.repo_dir)
                    else SurfaceToolsMixin._load_layer_manifest(ephemeral_node, target_dir)
                )
            )
        proj_resp = ephemeral_node._tool_resolve_surface_governance(
            {
                "target_path": target_path,
                "resolution_override": resolution,
                "resonance_key": str(spawned.get("session_resonance_key", "")),
                "include_capsules": True,
            }
        )
        surface_projection = json.loads(proj_resp["content"][0]["text"])
        first_capsule = next(
            (
                str(sec["capsule_token"])
                for b_item in surface_projection.get("resolved_bindings", [])
                for sec in b_item.get("sections", [])
                if sec.get("capsule_token")
            ),
            None,
        )

        brief = build_subagent_invocation_brief(
            spawned["manifest"], target_path, surface_projection, first_capsule
        )
        auto_reaped = False
        if one_shot and fork_id is None:
            if is_materialized:
                reap_ephemeral_fork(self.repo_dir, fork_id=str(spawned["fork_id"]))
            auto_reaped = True

        eval_payload = {
            "action": "evaluate",
            "fork_id": spawned["fork_id"],
            "bot_role": spawned["bot_role"],
            "auto_reaped": auto_reaped,
            "session_resonance_key": spawned["session_resonance_key"],
            "bridged_project_files": spawned["bridged_project_files"],
            "subagent_invocation_brief": brief,
            "ephemeral_capsule": first_capsule,
            "surface_projection": surface_projection,
        }
        return {
            "content": [{"type": "text", "text": json.dumps(eval_payload, indent=2)}],
            "isError": False,
        }
