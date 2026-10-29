"""Node introspection, drift auditing, document reading, and federation tools."""

from __future__ import annotations

import json
import os
import socket
import subprocess
from typing import Any

from dotfiles_mcp.constants import (
    AGENTS_MD_MAX_BYTES,
    ANSI_ESCAPE_RE,
    VALID_ENVIRONMENTS,
)
from dotfiles_mcp.manifest_helpers import (
    _is_running_in_container,
    _merge_unique_strings,
    _parse_skill_frontmatter,
    _read_git_commit,
    _read_non_empty_lines,
    _read_os_pretty_name,
    _read_version,
)
from dotfiles_mcp.node_base import MCPNodeBase
from dotfiles_mcp.promotion_engine import compare_project_patterns_multilayer


class FederationToolsMixin(MCPNodeBase):
    """Implements overview, drift audit, document reading, and federation MCP tools."""

    def _tool_get_layer_overview(self, args: dict[str, Any]) -> dict[str, Any]:
        target_dir = self._resolve_layer_dir(args.get("layer"))
        manifest = self._load_layer_manifest(target_dir)
        sys_dir = target_dir / "system"
        apt_pkgs = _read_non_empty_lines(sys_dir / "packages-manual.txt")
        snaps = _read_non_empty_lines(sys_dir / "snaps.txt")
        npm_globals = _read_non_empty_lines(sys_dir / "npm-globals.txt")
        external = _read_non_empty_lines(sys_dir / "external.txt")
        gnome_ext = _read_non_empty_lines(sys_dir / "gnome-extensions.txt")
        skills_root = target_dir / "antigravity/.gemini/config/skills"
        skills_names = [
            _parse_skill_frontmatter(sf, target_dir)["name"]
            for sf in sorted(skills_root.glob("*/SKILL.md"))
        ]
        templates_root = target_dir / "templates"
        template_names = (
            [d.name for d in sorted(templates_root.iterdir()) if d.is_dir()]
            if templates_root.is_dir()
            else []
        )
        docs_root = target_dir / "docs"
        docs_files = (
            [str(p.relative_to(target_dir)) for p in sorted(docs_root.rglob("*.md"))]
            if docs_root.is_dir()
            else []
        )
        agents_file = target_dir / "antigravity/.gemini/config/AGENTS.md"
        agents_bytes = agents_file.stat().st_size if agents_file.is_file() else 0
        warnings = self._evaluate_layer_warnings(target_dir, agents_bytes)
        digest = {
            "channel_1_node_and_system_state": {
                "version": _read_version(target_dir),
                "layer_id": manifest.get("layer_id"),
                "layer_role": manifest.get("layer_role"),
                "hostname": socket.gethostname(),
                "in_container": _is_running_in_container(),
                "os_pretty_name": _read_os_pretty_name(),
                "git_commit": _read_git_commit(target_dir),
                "manifest_counts": {
                    "apt_manual_packages": len(apt_pkgs),
                    "snaps": len(snaps),
                    "npm_globals": len(npm_globals),
                    "enabled_external_recipes": len(external),
                    "gnome_extensions": len(gnome_ext),
                },
            },
            "channel_2_governance_and_stack_contracts": {
                "global_skills_count": len(skills_names),
                "global_skills": skills_names,
                "stack_templates": template_names,
                "baseline_guardrails": manifest.get("baseline_guardrails", []),
            },
            "channel_3_active_invariants_and_hooks": {
                "agents_md_bytes": agents_bytes,
                "agents_md_estimated_tokens": agents_bytes // 4,
                "agents_md_budget_cap_bytes": AGENTS_MD_MAX_BYTES,
                "agents_md_budget_utilization_pct": round(
                    (agents_bytes / AGENTS_MD_MAX_BYTES) * 100, 1
                ),
                "active_lifecycle_hooks": [
                    "PreToolUse (pre_tool_guard.py)",
                    "PostToolUse (post_edit_format.py)",
                    "PostInvocation (post_invocation_lint.py)",
                    "Stop (stop_verify_tests.py)",
                ],
                "mcp_security_mode": "strictly-read-only-path-contained",
                "context_compaction_protocol": "rcap1 (L0->L1->L2->L3 zlib+HMAC-SHA256)",
                "log_dir": str(self.log_dir) if self.log_dir else None,
                "warnings": warnings,
            },
            "channel_4_navigable_docs_and_federated_mcps": {
                "docs_index": "docs/README.md",
                "documents": docs_files,
                "mounted_layers": self._discover_mounted_layers(),
                "supported_environments": list(manifest.get("environments", {}).keys()),
                "federated_mcps": manifest.get("federated_mcps", []),
            },
        }
        return {
            "content": [{"type": "text", "text": json.dumps(digest, indent=2)}],
            "isError": False,
        }

    def _tool_audit_node_drift(self, args: dict[str, Any]) -> dict[str, Any]:
        mode = str(args.get("mode", "verify-repo"))
        if mode not in ("verify-repo", "system-audit", "both"):
            raise ValueError(
                f"Invalid mode {mode!r}: must be 'verify-repo', 'system-audit', or 'both'"
            )
        env = dict(os.environ)
        env["NO_COLOR"] = "1"
        env["LC_ALL"] = "C"
        results: dict[str, Any] = {"mode": mode, "healthy": True, "checks": {}}
        scripts_to_run: list[tuple[str, list[str]]] = []
        if mode in ("verify-repo", "both"):
            scripts_to_run.append(("verify_repo", [str(self.repo_dir / "scripts/verify-repo.sh")]))
        if mode in ("system-audit", "both"):
            scripts_to_run.append(("system_audit", [str(self.repo_dir / "audit.sh")]))

        for key, cmd in scripts_to_run:
            proc = subprocess.run(  # noqa: S603
                cmd,
                cwd=self.repo_dir,
                env=env,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            clean_out = ANSI_ESCAPE_RE.sub("", proc.stdout + proc.stderr).strip()
            check_ok = proc.returncode == 0
            if not check_ok:
                results["healthy"] = False
            results["checks"][key] = {
                "exit_code": proc.returncode,
                "passed": check_ok,
                "output": clean_out,
            }
        if not results["healthy"]:
            results["warnings"] = [
                self._emit_warning(
                    "WARN",
                    "NODE_DRIFT_DETECTED",
                    "Repository verification or system drift audit reported issues.",
                    {"mode": mode},
                )
            ]
        else:
            results["warnings"] = []
        return {
            "content": [{"type": "text", "text": json.dumps(results, indent=2)}],
            "isError": False,
        }

    def _tool_read_layer_document(self, args: dict[str, Any]) -> dict[str, Any]:
        rel_path = str(args.get("relative_path", ""))
        target_dir = self._resolve_layer_dir(args.get("layer"))
        target = self._resolve_safe_path(rel_path, target_dir)
        content = target.read_text(encoding="utf-8")
        return {
            "content": [{"type": "text", "text": content}],
            "isError": False,
        }

    def _tool_discover_federated_mcps(self, args: dict[str, Any]) -> dict[str, Any]:
        root_manifest = self._load_layer_manifest()
        filter_role = str(args.get("filter_role", "")).strip().lower()
        env_arg = str(args.get("environment", "")).strip().lower()
        if env_arg and env_arg not in VALID_ENVIRONMENTS:
            raise ValueError(
                f"Invalid environment {env_arg!r}: must be one of {VALID_ENVIRONMENTS}"
            )
        layer_arg = str(args.get("layer", "all")).strip() or "all"
        if layer_arg == "all":
            target_dirs = [
                self.repo_dir,
                *(self.repo_dir / str(m["relative_path"]) for m in self._discover_mounted_layers()),
            ]
        else:
            target_dirs = [self._resolve_layer_dir(layer_arg)]

        root_env_profiles = root_manifest.get("environments", {})
        active_env_profile = root_env_profiles.get(env_arg) if env_arg else None
        root_env_guardrails = (
            active_env_profile.get("default_guardrails", [])
            if isinstance(active_env_profile, dict)
            else []
        )
        root_baseline = root_manifest.get("baseline_guardrails", [])

        mcps: list[dict[str, Any]] = []
        for tdir in target_dirs:
            t_manifest = self._load_layer_manifest(tdir)
            source_layer_id = t_manifest.get("layer_id", tdir.name)
            layer_baseline = t_manifest.get("baseline_guardrails", [])
            layer_env_profile = t_manifest.get("environments", {}).get(env_arg) if env_arg else None
            if active_env_profile is None and isinstance(layer_env_profile, dict):
                active_env_profile = layer_env_profile
            layer_env_guardrails = (
                layer_env_profile.get("default_guardrails", [])
                if isinstance(layer_env_profile, dict)
                else []
            )
            for raw_mcp in t_manifest.get("federated_mcps", []):
                mcp_copy = dict(raw_mcp)
                mcp_copy.setdefault("source_layer", source_layer_id)
                mcp_copy.setdefault("activation_policy", "on-demand")
                mcp_copy.setdefault(
                    "when_to_invoke",
                    "Invoke on demand when the task requires this layer/service capability.",
                )
                mcp_copy.setdefault(
                    "avoid_when",
                    "Avoid invoking when local repository files or narrower layers suffice.",
                )
                mcp_copy["effective_guardrails"] = _merge_unique_strings(
                    root_baseline,
                    layer_baseline,
                    root_env_guardrails,
                    layer_env_guardrails,
                    mcp_copy.get("required_guardrails", []),
                )
                mcps.append(mcp_copy)

        if filter_role:
            mcps = [
                m
                for m in mcps
                if filter_role in str(m.get("role", "")).lower()
                or filter_role in str(m.get("layer", "")).lower()
                or filter_role in str(m.get("mcp_id", "")).lower()
            ]
        if env_arg:
            mcps = [m for m in mcps if env_arg in m.get("environments", list(VALID_ENVIRONMENTS))]

        mcp_warnings: list[dict[str, Any]] = []
        if len(mcps) > 3 and not filter_role and not env_arg:
            mcp_warnings.append(
                self._emit_warning(
                    "WARN",
                    "MCP_FANOUT_WARNING",
                    f"Unfiltered discovery returned {len(mcps)} MCPs across multiple layers. "
                    "Specify 'environment' (dev/tst/pre/pro), 'layer', or 'filter_role' "
                    "to prevent excessive MCP fan-out.",
                    {"returned_mcp_count": len(mcps), "layer": layer_arg},
                )
            )

        payload: dict[str, Any] = {
            "layer_id": root_manifest.get("layer_id"),
            "layer_role": root_manifest.get("layer_role"),
            "upstream_layer": root_manifest.get("upstream_layer"),
            "queried_layer": layer_arg,
            "active_environment": env_arg or "all",
            "environment_profile": active_env_profile,
            "mounted_layers": self._discover_mounted_layers(),
            "federated_mcp_count": len(mcps),
            "warnings": mcp_warnings,
            "federated_mcps": mcps,
        }
        return {
            "content": [{"type": "text", "text": json.dumps(payload, indent=2)}],
            "isError": False,
        }

    def _tool_compare_layer_patterns(self, args: dict[str, Any]) -> dict[str, Any]:
        layer_arg = str(args.get("layer", "all")).strip() or "all"
        mounted = self._discover_mounted_layers()
        if layer_arg == "all":
            target_dirs = [
                ("root", self.repo_dir, self._load_layer_manifest()),
                *(
                    (
                        str(m["name"]),
                        self.repo_dir / str(m["relative_path"]),
                        self._load_layer_manifest(self.repo_dir / str(m["relative_path"])),
                    )
                    for m in mounted
                ),
            ]
        else:
            tdir = self._resolve_layer_dir(layer_arg)
            lname = "root" if tdir == self.repo_dir else tdir.name
            target_dirs = [(lname, tdir, self._load_layer_manifest(tdir))]

        proj_rules = [str(r).strip() for r in args.get("project_rules", [])]
        proj_skills = [str(s).strip() for s in args.get("project_skills", [])]
        comparison = compare_project_patterns_multilayer(
            self.repo_dir,
            mounted,
            project_rules=proj_rules,
            project_skills=proj_skills,
            target_dirs=target_dirs,
        )
        return {
            "content": [{"type": "text", "text": json.dumps(comparison, indent=2)}],
            "isError": False,
        }
