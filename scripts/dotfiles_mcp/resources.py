"""MCP resource readers and runtime diagnostics telemetry aggregation.

Specification: docs/architecture/03_contextual_mcp_and_federation.md
"""

from __future__ import annotations

import json
import platform
import socket
from typing import Any

from dotfiles_mcp.catalogs import MCP_RESOURCES_CATALOG
from dotfiles_mcp.fork_configurator import discover_templates_catalog
from dotfiles_mcp.manifest_helpers import (
    _is_running_in_container,
    _parse_skill_frontmatter,
    _read_git_commit,
    _read_non_empty_lines,
    _read_os_pretty_name,
    _read_version,
)
from dotfiles_mcp.node_base import MCPNodeBase


class ResourcesMixin(MCPNodeBase):
    """Implements list_resources, read_resource, and dotfiles://mcp/diagnostics."""

    def list_resources(self) -> list[dict[str, Any]]:
        return [dict(item) for item in MCP_RESOURCES_CATALOG]

    def read_resource(self, uri: str) -> dict[str, Any]:
        if uri == "dotfiles://layer/identity":
            manifest = self._load_layer_manifest()
            payload = {
                "version": _read_version(self.repo_dir),
                "layer_id": manifest.get("layer_id", "dotfiles-ubuntu-default"),
                "layer_role": manifest.get("layer_role", "workstation"),
                "description": manifest.get("description", ""),
                "hostname": socket.gethostname(),
                "in_container": _is_running_in_container(),
                "os_pretty_name": _read_os_pretty_name(),
                "python_version": platform.python_version(),
                "git_commit": _read_git_commit(self.repo_dir),
                "repo_path": str(self.repo_dir),
                "upstream_layer": manifest.get("upstream_layer", {}),
            }
            return {
                "uri": uri,
                "mimeType": "application/json",
                "text": json.dumps(payload, indent=2),
            }

        if uri == "dotfiles://system/manifests":
            sys_dir = self.repo_dir / "system"
            apt_pkgs = _read_non_empty_lines(sys_dir / "packages-manual.txt")
            snaps = _read_non_empty_lines(sys_dir / "snaps.txt")
            npm_globals = _read_non_empty_lines(sys_dir / "npm-globals.txt")
            nvm_default = _read_non_empty_lines(sys_dir / "nvm-default.txt")
            external = _read_non_empty_lines(sys_dir / "external.txt")
            gnome_ext = _read_non_empty_lines(sys_dir / "gnome-extensions.txt")
            payload = {
                "counts": {
                    "apt_manual_packages": len(apt_pkgs),
                    "snaps": len(snaps),
                    "npm_globals": len(npm_globals),
                    "enabled_external_recipes": len(external),
                    "gnome_extensions": len(gnome_ext),
                },
                "nvm_default": nvm_default[0] if nvm_default else "none",
                "apt_manual_packages": apt_pkgs,
                "snaps": snaps,
                "npm_globals": npm_globals,
                "enabled_external_recipes": external,
                "gnome_extensions": gnome_ext,
            }
            return {
                "uri": uri,
                "mimeType": "application/json",
                "text": json.dumps(payload, indent=2),
            }

        if uri == "dotfiles://governance/rules":
            agents_md = self.repo_dir / "antigravity/.gemini/config/AGENTS.md"
            return {
                "uri": uri,
                "mimeType": "text/markdown",
                "text": agents_md.read_text(encoding="utf-8"),
            }

        if uri == "dotfiles://governance/hooks":
            hooks_json = self.repo_dir / "antigravity/.gemini/config/hooks.json"
            return {
                "uri": uri,
                "mimeType": "application/json",
                "text": hooks_json.read_text(encoding="utf-8"),
            }

        if uri == "dotfiles://governance/skills":
            skills_root = self.repo_dir / "antigravity/.gemini/config/skills"
            skills = [
                _parse_skill_frontmatter(sf, self.repo_dir)
                for sf in sorted(skills_root.glob("*/SKILL.md"))
            ]
            return {
                "uri": uri,
                "mimeType": "application/json",
                "text": json.dumps({"count": len(skills), "skills": skills}, indent=2),
            }

        if uri == "dotfiles://governance/templates":
            catalog = discover_templates_catalog(self.repo_dir, self._discover_mounted_layers())
            return {
                "uri": uri,
                "mimeType": "application/json",
                "text": json.dumps({"count": len(catalog), "templates": catalog}, indent=2),
            }

        if uri == "dotfiles://docs/index":
            docs_index = self.repo_dir / "docs/README.md"
            return {
                "uri": uri,
                "mimeType": "text/markdown",
                "text": docs_index.read_text(encoding="utf-8"),
            }

        if uri == "dotfiles://mcp/topology":
            manifest = self._load_layer_manifest()
            manifest["discovered_mounted_layers"] = self._discover_mounted_layers()
            return {
                "uri": uri,
                "mimeType": "application/json",
                "text": json.dumps(manifest, indent=2),
            }

        if uri == "dotfiles://mcp/diagnostics":
            return self._read_diagnostics_resource(uri)

        raise ValueError(f"Unknown resource URI: {uri!r}")

    def _read_diagnostics_resource(self, uri: str) -> dict[str, Any]:
        active_log_dir = self.log_dir or (self.repo_dir / "logs")
        events_path = active_log_dir / "mcp_events.jsonl"
        alerts_path = active_log_dir / "mcp_alerts.jsonl"
        events = (
            [json.loads(line) for line in _read_non_empty_lines(events_path)]
            if events_path.is_file()
            else []
        )
        alerts = (
            [json.loads(line) for line in _read_non_empty_lines(alerts_path)]
            if alerts_path.is_file()
            else []
        )
        by_code: dict[str, int] = {}
        for al in alerts:
            code = str(al.get("code", "UNKNOWN"))
            by_code[code] = by_code.get(code, 0) + 1
        max_bytes = max((int(ev.get("response_bytes", 0)) for ev in events), default=0)
        queries_by_res: dict[str, int] = {}
        unfolds_by_lvl: dict[str, int] = {}
        unfolds_by_tier: dict[str, int] = {}
        total_hops = 0
        total_tokens_saved = 0
        for ev in events:
            res_lvl = ev.get("resolution")
            if isinstance(res_lvl, str):
                queries_by_res[res_lvl] = queries_by_res.get(res_lvl, 0) + 1
                total_tokens_saved += int(ev.get("tokens_saved", 0))
            unf_lvl = ev.get("unfolded_level")
            if isinstance(unf_lvl, str):
                unfolds_by_lvl[unf_lvl] = unfolds_by_lvl.get(unf_lvl, 0) + 1
                tier = str(ev.get("agent_tier", "inherit"))
                unfolds_by_tier[tier] = unfolds_by_tier.get(tier, 0) + 1
                total_hops += int(ev.get("decrypted_hops", 0))
        capsule_alerts = {
            code: count for code, count in by_code.items() if code.startswith("CAPSULE_")
        }
        diag_payload: dict[str, Any] = {
            "logging_enabled": self.log_dir is not None,
            "log_dir": str(self.log_dir) if self.log_dir else None,
            "events_summary": {
                "total_events": len(events),
                "error_events": sum(1 for ev in events if ev.get("status") == "error"),
                "max_response_bytes": max_bytes,
                "recent_events": events[-5:],
            },
            "alerts_summary": {
                "total_alerts": len(alerts),
                "by_code": by_code,
                "recent_alerts": alerts[-10:],
            },
            "resonance_compaction_summary": {
                "queries_by_resolution": queries_by_res,
                "unfolds_by_target_level": unfolds_by_lvl,
                "unfolds_by_agent_tier": unfolds_by_tier,
                "total_decrypted_hops": total_hops,
                "cumulative_tokens_saved": total_tokens_saved,
                "capsule_alerts_by_code": capsule_alerts,
            },
        }
        return {
            "uri": uri,
            "mimeType": "application/json",
            "text": json.dumps(diag_payload, indent=2),
        }
