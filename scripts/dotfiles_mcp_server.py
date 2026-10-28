#!/usr/bin/env python3
"""Zero-dependency, read-only Model Context Protocol (MCP) server for dotfiles-ubuntu.

Exposes the current repository/fork's declarative Ubuntu system manifests,
Google Antigravity 2.0 governance rules, Layer 2 templates, navigable docs/,
live drift audits, and federated MCP topology over JSON-RPC 2.0 (stdio).

Specification: docs/architecture/03_contextual_mcp_and_federation.md
Configuration guide: docs/reference/contextual_mcp_and_multi_service_orchestration.md
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_DIR = SCRIPT_DIR.parent
PROTOCOL_VERSION = "2024-11-05"
VALID_LAYER_ROLES = (
    "corporate",
    "department",
    "team",
    "service-node",
    "environment-cluster",
    "workstation",
)
VALID_ENVIRONMENTS = ("dev", "tst", "pre", "pro")
AGENTS_MD_WARN_BYTES = 16000
AGENTS_MD_MAX_BYTES = 18000
MCP_PAYLOAD_WARN_BYTES = 16000
MAX_LOG_FILE_BYTES = 524288
ALLOWED_READ_PREFIXES = ("docs/", "templates/", "antigravity/", "system/")
ALLOWED_ROOT_FILES = {
    "README.md",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "ACCESSIBILITY.md",
    "CODE_OF_CONDUCT.md",
    "VERSION",
}
ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")


def _read_version(repo_dir: Path | None = None) -> str:
    base_dir = repo_dir or REPO_DIR
    version_file = base_dir / "VERSION"
    if version_file.is_file():
        return version_file.read_text(encoding="utf-8").strip()
    return "0.0.0"


def _read_os_pretty_name(os_release: Path | None = None) -> str:
    release_file = os_release or Path("/etc/os-release")
    if release_file.is_file():
        for line in release_file.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.startswith("PRETTY_NAME="):
                return line.split("=", 1)[1].strip().strip('"')
    return f"{platform.system()} {platform.release()}"


def _read_git_commit(repo_dir: Path | None = None) -> str:
    base_dir = repo_dir or REPO_DIR
    git_bin = shutil.which("git")
    if not git_bin:
        return "unknown"
    try:
        proc = subprocess.run(  # noqa: S603
            [git_bin, "rev-parse", "--short", "HEAD"],
            cwd=base_dir,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if proc.returncode == 0:
            return proc.stdout.strip()
    except OSError:
        pass
    return "unknown"


def _parse_skill_frontmatter(skill_md: Path, repo_dir: Path | None = None) -> dict[str, Any]:
    base_dir = repo_dir or REPO_DIR
    lines = skill_md.read_text(encoding="utf-8").splitlines()
    name = skill_md.parent.name
    description = ""
    if lines and lines[0].strip() == "---":
        for idx in range(1, min(len(lines), 30)):
            if lines[idx].strip() == "---":
                fm = "\n".join(lines[1:idx])
                name_m = re.search(r"^name:\s*(.+)$", fm, re.MULTILINE)
                desc_m = re.search(r"^description:\s*(.+)$", fm, re.MULTILINE)
                if name_m:
                    name = name_m.group(1).strip().strip("'\"")
                if desc_m:
                    description = desc_m.group(1).strip().strip("'\"")
                break
    return {
        "name": name,
        "description": description,
        "path": str(skill_md.relative_to(base_dir)),
        "line_count": len(lines),
    }


def _read_non_empty_lines(path: Path) -> list[str]:
    if not path.is_file():
        return []
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def _merge_unique_strings(*groups: list[str]) -> list[str]:
    seen: set[str] = set()
    merged: list[str] = []
    for group in groups:
        for item in group:
            clean = str(item).strip()
            if clean and clean not in seen:
                seen.add(clean)
                merged.append(clean)
    return merged


class DotfilesMCPServer:
    """Read-only MCP server exposing dotfiles-ubuntu system & governance context."""

    def __init__(
        self,
        repo_dir: Path = REPO_DIR,
        layer_id_override: str | None = None,
        layer_role_override: str | None = None,
        log_dir: Path | None = None,
    ) -> None:
        self.repo_dir = repo_dir.resolve()
        self.layer_id_override = layer_id_override
        self.layer_role_override = layer_role_override
        self.log_dir = log_dir.resolve() if log_dir is not None else None

    def _write_jsonl(self, filename: str, record: dict[str, Any]) -> None:
        if self.log_dir is None:
            return
        with contextlib.suppress(OSError):
            self.log_dir.mkdir(parents=True, exist_ok=True)
            target = self.log_dir / filename
            if target.is_file() and target.stat().st_size >= MAX_LOG_FILE_BYTES:
                target.replace(self.log_dir / f"{filename}.1")
            with target.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(record) + "\n")

    def _emit_warning(
        self,
        severity: str,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        alert = {
            "ts": datetime.now(UTC).isoformat(),
            "severity": severity,
            "code": code,
            "message": message,
            "details": details or {},
        }
        self._write_jsonl("mcp_alerts.jsonl", alert)
        return alert

    def _evaluate_layer_warnings(
        self,
        target_dir: Path,
        agents_bytes: int,
    ) -> list[dict[str, Any]]:
        warnings: list[dict[str, Any]] = []
        if agents_bytes > AGENTS_MD_MAX_BYTES:
            warnings.append(
                self._emit_warning(
                    "CRITICAL",
                    "TOKEN_BUDGET_EXCEEDED",
                    f"AGENTS.md is {agents_bytes} bytes (exceeds {AGENTS_MD_MAX_BYTES}-byte cap; "
                    "context truncation risk).",
                    {"agents_md_bytes": agents_bytes, "cap_bytes": AGENTS_MD_MAX_BYTES},
                )
            )
        elif agents_bytes >= AGENTS_MD_WARN_BYTES:
            warnings.append(
                self._emit_warning(
                    "WARN",
                    "TOKEN_BUDGET_NEAR_LIMIT",
                    f"AGENTS.md is {agents_bytes} bytes (>= {AGENTS_MD_WARN_BYTES}-byte warning "
                    f"threshold; {AGENTS_MD_MAX_BYTES - agents_bytes} bytes remaining).",
                    {"agents_md_bytes": agents_bytes, "cap_bytes": AGENTS_MD_MAX_BYTES},
                )
            )
        if target_dir == self.repo_dir:
            for entry in self._discover_mounted_layers():
                if not entry["has_upstream"]:
                    warnings.append(
                        self._emit_warning(
                            "WARN",
                            "SUBTREE_LINEAGE_WARNING",
                            f"Mounted subtree {entry['relative_path']!r} is missing "
                            "upstream_layer.repository in system/mcp-layer.json.",
                            {"layer": entry["name"]},
                        )
                    )
        return warnings

    def _load_layer_manifest(self, target_dir: Path | None = None) -> dict[str, Any]:
        base_dir = (target_dir or self.repo_dir).resolve()
        manifest_path = base_dir / "system" / "mcp-layer.json"
        data: dict[str, Any] = {
            "schema_version": "1.1",
            "layer_id": base_dir.name if base_dir != self.repo_dir else "dotfiles-ubuntu-default",
            "layer_role": "workstation",
            "description": "Declarative Ubuntu 26.04 LTS & Google Antigravity 2.0 Layer",
            "upstream_layer": {
                "layer_id": "mtwuser/dotfiles-ubuntu",
                "repository": "https://github.com/mtwuser/dotfiles-ubuntu.git",
                "branch": "master",
            },
            "mounted_layers_dir": "layers",
            "mounted_layers": [],
            "default_stack_templates": ["fastapi-hexagonal"],
            "baseline_guardrails": [],
            "environments": {},
            "federated_mcps": [],
        }
        if manifest_path.is_file():
            loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                data.update(loaded)
        if base_dir == self.repo_dir:
            if self.layer_id_override:
                data["layer_id"] = self.layer_id_override
            if self.layer_role_override:
                data["layer_role"] = self.layer_role_override
        return data

    def _discover_mounted_layers(self) -> list[dict[str, Any]]:
        layers_dir = self.repo_dir / "layers"
        discovered: list[dict[str, Any]] = []
        if not layers_dir.is_dir():
            return discovered
        for sub in sorted(layers_dir.iterdir()):
            if not sub.is_dir() or sub.name.startswith("."):
                continue
            raw_manifest_path = sub / "system" / "mcp-layer.json"
            has_upstream = True
            if raw_manifest_path.is_file():
                raw_data = json.loads(raw_manifest_path.read_text(encoding="utf-8"))
                if isinstance(raw_data, dict) and "upstream_layer" in raw_data:
                    up = raw_data.get("upstream_layer")
                    has_upstream = bool(isinstance(up, dict) and up.get("repository"))
            sub_manifest = self._load_layer_manifest(sub)
            discovered.append(
                {
                    "name": sub.name,
                    "relative_path": f"layers/{sub.name}",
                    "layer_id": sub_manifest.get("layer_id", sub.name),
                    "layer_role": sub_manifest.get("layer_role", "service-node"),
                    "version": _read_version(sub),
                    "has_docs": (sub / "docs").is_dir(),
                    "has_rules": (sub / "antigravity/.gemini/config/AGENTS.md").is_file(),
                    "has_templates": (sub / "templates").is_dir(),
                    "has_upstream": has_upstream,
                    "federated_mcp_count": len(sub_manifest.get("federated_mcps", [])),
                }
            )
        return discovered

    def _resolve_layer_dir(self, layer: str | None = None) -> Path:
        clean = (layer or "").strip()
        root_id = str(self._load_layer_manifest().get("layer_id", ""))
        if not clean or clean in ("root", "self", root_id):
            return self.repo_dir
        for entry in self._discover_mounted_layers():
            if clean in (entry["name"], entry["layer_id"]):
                return (self.repo_dir / str(entry["relative_path"])).resolve()
        raise ValueError(f"Unknown or unmounted layer: {layer!r}")

    def _resolve_safe_path(self, relative_path: str, base_dir: Path | None = None) -> Path:
        target_base = (base_dir or self.repo_dir).resolve()
        clean_rel = relative_path.strip().lstrip("/")
        if not clean_rel or ".." in Path(clean_rel).parts:
            raise ValueError(f"Invalid or forbidden relative path: {relative_path!r}")
        candidate = (target_base / clean_rel).resolve()
        if not candidate.is_relative_to(target_base):
            raise ValueError(f"Path escapes repository root: {relative_path!r}")
        rel_str = str(candidate.relative_to(target_base)).replace("\\", "/")
        allowed = rel_str in ALLOWED_ROOT_FILES or any(
            rel_str.startswith(prefix) for prefix in ALLOWED_READ_PREFIXES
        )
        if not allowed:
            raise ValueError(
                f"Access denied for {relative_path!r}: only docs/, templates/, "
                "antigravity/, system/, and root documentation files are readable."
            )
        if not candidate.is_file():
            raise FileNotFoundError(f"Document not found: {rel_str}")
        return candidate

    # ------------------------------------------------------------------
    # Resources
    # ------------------------------------------------------------------
    def list_resources(self) -> list[dict[str, Any]]:
        return [
            {
                "uri": "dotfiles://layer/identity",
                "name": "Layer & System Node Identity",
                "description": (
                    "Repository SemVer version, layer_id, layer_role, OS release, "
                    "hostname, Git commit, and upstream lineage."
                ),
                "mimeType": "application/json",
            },
            {
                "uri": "dotfiles://system/manifests",
                "name": "Declarative Ubuntu System Manifests",
                "description": (
                    "Tracked APT manual packages, application Snaps, NPM globals, "
                    "NVM default version, enabled external recipes, and GNOME extensions."
                ),
                "mimeType": "application/json",
            },
            {
                "uri": "dotfiles://governance/rules",
                "name": "Layer A Global Engineering Rules (AGENTS.md)",
                "description": (
                    "Universal behavioral mandates, strict typing, AAA testing, "
                    "refactoring, and commit governance rules."
                ),
                "mimeType": "text/markdown",
            },
            {
                "uri": "dotfiles://governance/hooks",
                "name": "Antigravity Lifecycle Hooks Configuration (hooks.json)",
                "description": (
                    "Deterministic PreToolUse, PostToolUse, PostInvocation, and Stop "
                    "hook definitions."
                ),
                "mimeType": "application/json",
            },
            {
                "uri": "dotfiles://governance/skills",
                "name": "Global Skills Catalog",
                "description": (
                    "Structured list of all global interactive slash-command skills "
                    "and procedural engineering skills in this layer."
                ),
                "mimeType": "application/json",
            },
            {
                "uri": "dotfiles://governance/templates",
                "name": "Layer B Stack Starter Templates",
                "description": (
                    "Inventory of reusable project starter templates (rules, skills, "
                    "and governance files) available in templates/."
                ),
                "mimeType": "application/json",
            },
            {
                "uri": "dotfiles://docs/index",
                "name": "Navigable Documentation Index (docs/README.md)",
                "description": (
                    "Structured index of architecture specifications and reference "
                    "guides for this repository layer."
                ),
                "mimeType": "text/markdown",
            },
            {
                "uri": "dotfiles://mcp/topology",
                "name": "Federated MCP Topology & Guardrails (system/mcp-layer.json)",
                "description": (
                    "Downstream and sibling MCP servers associated with this layer "
                    "or service node and their mandatory pre-call safety guardrails."
                ),
                "mimeType": "application/json",
            },
            {
                "uri": "dotfiles://mcp/diagnostics",
                "name": "Runtime MCP Event & Alert Diagnostics (logs/mcp_*.jsonl)",
                "description": (
                    "Live telemetry summary of recent MCP calls, response sizes, "
                    "and token-budget/truncation/security alerts from logs/."
                ),
                "mimeType": "application/json",
            },
        ]

    def read_resource(self, uri: str) -> dict[str, Any]:
        if uri == "dotfiles://layer/identity":
            manifest = self._load_layer_manifest()
            payload = {
                "version": _read_version(self.repo_dir),
                "layer_id": manifest.get("layer_id", "dotfiles-ubuntu-default"),
                "layer_role": manifest.get("layer_role", "workstation"),
                "description": manifest.get("description", ""),
                "hostname": socket.gethostname(),
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
            templates_root = self.repo_dir / "templates"
            catalog: list[dict[str, Any]] = []
            if templates_root.is_dir():
                for tpl_dir in sorted(templates_root.iterdir()):
                    if not tpl_dir.is_dir():
                        continue
                    rules = [
                        str(p.relative_to(self.repo_dir))
                        for p in sorted((tpl_dir / "rules").glob("*.md"))
                    ]
                    skills = [
                        _parse_skill_frontmatter(p, self.repo_dir)
                        for p in sorted((tpl_dir / "skills").glob("*/SKILL.md"))
                    ]
                    gov = [
                        str(p.relative_to(self.repo_dir))
                        for p in sorted((tpl_dir / "governance").glob("*.md"))
                    ]
                    catalog.append(
                        {
                            "template_name": tpl_dir.name,
                            "rules": rules,
                            "skills": skills,
                            "governance_files": gov,
                        }
                    )
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
            }
            return {
                "uri": uri,
                "mimeType": "application/json",
                "text": json.dumps(diag_payload, indent=2),
            }

        raise ValueError(f"Unknown resource URI: {uri!r}")

    # ------------------------------------------------------------------
    # Tools
    # ------------------------------------------------------------------
    def list_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "get_layer_overview",
                "description": (
                    "Return a compact 4-Channel Executive Digest of this dotfiles-ubuntu "
                    "node/layer or any mounted git subtree layer in layers/* "
                    "(1. Node & System State, 2. Governance & Stack Contracts, "
                    "3. Active Invariants & Hooks, 4. Docs, Mounted Subtrees & Federated MCPs)."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "layer": {
                            "type": "string",
                            "description": (
                                "Target layer ('root' or a mounted subtree name/layer_id "
                                "under layers/*)."
                            ),
                        }
                    },
                    "additionalProperties": False,
                },
            },
            {
                "name": "audit_node_drift",
                "description": (
                    "Run deterministic read-only verification and/or system drift audit "
                    "on this node or container (verify-repo.sh and/or audit.sh)."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "mode": {
                            "type": "string",
                            "enum": ["verify-repo", "system-audit", "both"],
                            "default": "verify-repo",
                            "description": (
                                "'verify-repo' runs static repository & hook checks; "
                                "'system-audit' runs live Ubuntu package/symlink drift "
                                "checks; 'both' runs both."
                            ),
                        }
                    },
                    "additionalProperties": False,
                },
            },
            {
                "name": "read_layer_document",
                "description": (
                    "Read a Markdown specification, template rule, skill, or manifest "
                    "file inside the root repository or a mounted git subtree layer in layers/* "
                    "(confined to docs/, templates/, antigravity/, system/, and root docs)."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "relative_path": {
                            "type": "string",
                            "description": (
                                "Path relative to the target layer root, e.g. "
                                "'docs/architecture/01_system_and_stow_engine.md' or "
                                "'templates/fastapi-hexagonal/rules/coding.md'."
                            ),
                        },
                        "layer": {
                            "type": "string",
                            "description": (
                                "Optional layer ('root' or a mounted subtree name/layer_id "
                                "under layers/*)."
                            ),
                        },
                    },
                    "required": ["relative_path"],
                    "additionalProperties": False,
                },
            },
            {
                "name": "query_governance_rules",
                "description": (
                    "Search across Layer A rules (AGENTS.md), Layer B stack templates "
                    "(templates/), and architecture docs (docs/) across the root layer "
                    "and/or mounted git subtree layers (layers/*) by keyword or topic."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": (
                                "Keyword or phrase to search (e.g., 'testing', "
                                "'migrations', 'decommissioning')."
                            ),
                        },
                        "scope": {
                            "type": "string",
                            "enum": ["all", "global", "templates", "docs"],
                            "default": "all",
                            "description": "Subset of layer documentation to search.",
                        },
                        "layer": {
                            "type": "string",
                            "default": "all",
                            "description": (
                                "'all' (search root + all mounted subtrees in layers/*), "
                                "'root' (only root layer), or a specific mounted subtree name."
                            ),
                        },
                    },
                    "required": ["query"],
                    "additionalProperties": False,
                },
            },
            {
                "name": "discover_federated_mcps",
                "description": (
                    "Discover downstream or sibling MCP servers registered in the root "
                    "layer and/or mounted git subtree layers (layers/*), optionally "
                    "filtered by role, layer, and target environment (dev, tst, pre, pro)."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "filter_role": {
                            "type": "string",
                            "description": (
                                "Optional role substring filter (e.g. 'database', "
                                "'documentation', 'telemetry')."
                            ),
                        },
                        "environment": {
                            "type": "string",
                            "enum": ["dev", "tst", "pre", "pro"],
                            "description": (
                                "Optional environment filter ('dev', 'tst', 'pre', or 'pro') "
                                "returning environment-specific guardrails and access mode."
                            ),
                        },
                        "layer": {
                            "type": "string",
                            "default": "all",
                            "description": (
                                "'all' (aggregate MCPs from root + mounted subtrees in layers/*), "
                                "'root', or a specific mounted subtree name/layer_id."
                            ),
                        },
                    },
                    "additionalProperties": False,
                },
            },
            {
                "name": "compare_layer_patterns",
                "description": (
                    "Compare a consumer project's .agents/rules/ and .agents/skills/ "
                    "names against the root layer or a mounted departmental/team subtree "
                    "layer (layers/*) to assist with /enrich upward promotion or downward sync."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_rules": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": (
                                "Rule filenames or identifiers in the project "
                                "(e.g. ['coding.md', 'testing.md'])."
                            ),
                        },
                        "project_skills": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": (
                                "Skill names in the project (e.g. ['start', "
                                "'fastapi-testing', 'custom-deploy'])."
                            ),
                        },
                        "layer": {
                            "type": "string",
                            "description": (
                                "Optional target layer ('root' or a mounted subtree "
                                "name/layer_id in layers/*)."
                            ),
                        },
                    },
                    "additionalProperties": False,
                },
            },
        ]

    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        args = arguments or {}

        if name == "get_layer_overview":
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

        if name == "audit_node_drift":
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
                scripts_to_run.append(
                    ("verify_repo", [str(self.repo_dir / "scripts/verify-repo.sh")])
                )
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

        if name == "read_layer_document":
            rel_path = str(args.get("relative_path", ""))
            target_dir = self._resolve_layer_dir(args.get("layer"))
            target = self._resolve_safe_path(rel_path, target_dir)
            content = target.read_text(encoding="utf-8")
            return {
                "content": [{"type": "text", "text": content}],
                "isError": False,
            }

        if name == "query_governance_rules":
            query = str(args.get("query", "")).strip()
            if not query:
                raise ValueError("'query' must be a non-empty string")
            scope = str(args.get("scope", "all"))
            layer_arg = str(args.get("layer", "all")).strip() or "all"
            if layer_arg == "all":
                layer_dirs = [
                    self.repo_dir,
                    *(
                        self.repo_dir / str(m["relative_path"])
                        for m in self._discover_mounted_layers()
                    ),
                ]
            else:
                layer_dirs = [self._resolve_layer_dir(layer_arg)]

            candidate_files: list[Path] = []
            for ldir in layer_dirs:
                if scope in ("all", "global"):
                    candidate_files.append(ldir / "antigravity/.gemini/config/AGENTS.md")
                if scope in ("all", "templates"):
                    candidate_files.extend(sorted((ldir / "templates").glob("*/rules/*.md")))
                if scope in ("all", "docs"):
                    candidate_files.extend(sorted((ldir / "docs").rglob("*.md")))

            matches: list[dict[str, Any]] = []
            excerpt_truncated = False
            q_lower = query.lower()
            for file_path in candidate_files:
                if not file_path.is_file():
                    continue
                lines = file_path.read_text(encoding="utf-8").splitlines()
                current_heading = file_path.name
                section_start = 1
                section_lines: list[str] = []

                def _flush_section(
                    heading: str,
                    start_line: int,
                    end_line: int,
                    body: list[str],
                    fp: Path = file_path,
                ) -> None:
                    nonlocal excerpt_truncated
                    joined = "\n".join(body)
                    if q_lower in joined.lower() or q_lower in heading.lower():
                        if len(joined) > 1500:
                            excerpt_truncated = True
                        matches.append(
                            {
                                "file": str(fp.relative_to(self.repo_dir)),
                                "section": heading,
                                "start_line": start_line,
                                "end_line": end_line,
                                "excerpt": joined[:1500],
                            }
                        )

                for idx, line in enumerate(lines, start=1):
                    if line.startswith(("## ", "### ", "#### ")) and section_lines:
                        _flush_section(current_heading, section_start, idx - 1, section_lines)
                        current_heading = line.lstrip("#").strip()
                        section_start = idx
                        section_lines = [line]
                    else:
                        if line.startswith("# ") and idx == 1:
                            current_heading = line.lstrip("#").strip()
                        section_lines.append(line)
                if section_lines:
                    _flush_section(current_heading, section_start, len(lines), section_lines)

            total_matches = len(matches)
            query_warnings: list[dict[str, Any]] = []
            if total_matches > 15 or excerpt_truncated:
                query_warnings.append(
                    self._emit_warning(
                        "WARN",
                        "RESPONSE_TRUNCATED",
                        f"Query matched {total_matches} section(s) (returning top "
                        f"{min(total_matches, 15)}). Narrow 'query', 'scope', or 'layer' "
                        "to inspect full sections without truncation.",
                        {
                            "query": query,
                            "total_matches": total_matches,
                            "excerpt_truncated": excerpt_truncated,
                        },
                    )
                )

            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "query": query,
                                "scope": scope,
                                "layer": layer_arg,
                                "total_matches_found": total_matches,
                                "match_count": min(total_matches, 15),
                                "truncated": bool(query_warnings),
                                "warnings": query_warnings,
                                "matches": matches[:15],
                            },
                            indent=2,
                        ),
                    }
                ],
                "isError": False,
            }

        if name == "discover_federated_mcps":
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
                    *(
                        self.repo_dir / str(m["relative_path"])
                        for m in self._discover_mounted_layers()
                    ),
                ]
            else:
                target_dirs = [self._resolve_layer_dir(layer_arg)]

            env_profiles = root_manifest.get("environments", {})
            active_env_profile = env_profiles.get(env_arg) if env_arg else None
            env_guardrails = (
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
                        env_guardrails,
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
                mcps = [
                    m for m in mcps if env_arg in m.get("environments", list(VALID_ENVIRONMENTS))
                ]

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

        if name == "compare_layer_patterns":
            target_dir = self._resolve_layer_dir(args.get("layer"))
            target_manifest = self._load_layer_manifest(target_dir)
            proj_rules = [str(r).strip() for r in args.get("project_rules", [])]
            proj_skills = [str(s).strip() for s in args.get("project_skills", [])]

            global_skills_root = target_dir / "antigravity/.gemini/config/skills"
            layer_a_skills = {
                _parse_skill_frontmatter(sf, target_dir)["name"]
                for sf in global_skills_root.glob("*/SKILL.md")
            } | {sf.parent.name for sf in global_skills_root.glob("*/SKILL.md")}

            layer_b_rules: set[str] = set()
            layer_b_skills: set[str] = set()
            templates_root = target_dir / "templates"
            if templates_root.is_dir():
                for rf in templates_root.glob("*/rules/*.md"):
                    layer_b_rules.add(rf.name)
                for sf in templates_root.glob("*/skills/*/SKILL.md"):
                    layer_b_skills.add(_parse_skill_frontmatter(sf, target_dir)["name"])
                    layer_b_skills.add(sf.parent.name)

            comparison = {
                "compared_against_layer": target_manifest.get("layer_id"),
                "already_in_layer_a_skills": sorted(s for s in proj_skills if s in layer_a_skills),
                "already_in_layer_b_templates": {
                    "rules": sorted(r for r in proj_rules if r in layer_b_rules),
                    "skills": sorted(s for s in proj_skills if s in layer_b_skills),
                },
                "candidates_for_upward_promotion": {
                    "novel_rules": sorted(r for r in proj_rules if r not in layer_b_rules),
                    "novel_skills": sorted(
                        s
                        for s in proj_skills
                        if s not in layer_a_skills and s not in layer_b_skills
                    ),
                },
                "available_in_layer_b_but_missing_in_project": {
                    "rules": sorted(r for r in layer_b_rules if r not in proj_rules),
                    "skills": sorted(s for s in layer_b_skills if s not in proj_skills),
                },
            }
            return {
                "content": [{"type": "text", "text": json.dumps(comparison, indent=2)}],
                "isError": False,
            }

        raise ValueError(f"Unknown tool name: {name!r}")

    # ------------------------------------------------------------------
    # Prompts
    # ------------------------------------------------------------------
    def list_prompts(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "orient-on-layer",
                "description": (
                    "Orient an AI agent on this dotfiles-ubuntu layer/node using a "
                    "4-Channel Executive Digest and navigable docs/ index."
                ),
                "arguments": [
                    {
                        "name": "task_description",
                        "description": "Optional summary of the task to perform.",
                        "required": False,
                    }
                ],
            },
            {
                "name": "audit-container-or-node",
                "description": (
                    "Audit live package, symlink, and repository drift on this "
                    "container or server node."
                ),
                "arguments": [
                    {
                        "name": "target_service",
                        "description": "Optional name of the container or service node.",
                        "required": False,
                    }
                ],
            },
            {
                "name": "orchestrate-federated-mcps",
                "description": (
                    "Discover federated MCP servers on this layer/node and load "
                    "their mandatory safety guardrails before executing cross-service operations."
                ),
                "arguments": [
                    {
                        "name": "workflow_goal",
                        "description": "Goal of the multi-service or infrastructure operation.",
                        "required": True,
                    }
                ],
            },
        ]

    def get_prompt(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        args = arguments or {}
        if name == "orient-on-layer":
            task = args.get("task_description", "general architectural exploration")
            return {
                "description": f"Layer orientation for: {task}",
                "messages": [
                    {
                        "role": "user",
                        "content": {
                            "type": "text",
                            "text": (
                                f"Task context: {task}\n\n"
                                "1. Call the `get_layer_overview` tool to inspect this node's "
                                "4-Channel Executive Digest.\n"
                                "2. Read the `dotfiles://docs/index` resource to locate the "
                                "relevant normative specification before proposing changes."
                            ),
                        },
                    }
                ],
            }

        if name == "audit-container-or-node":
            service = args.get("target_service", "current node")
            return {
                "description": f"Environment & governance drift audit for {service}",
                "messages": [
                    {
                        "role": "user",
                        "content": {
                            "type": "text",
                            "text": (
                                f"Perform a read-only drift audit on `{service}`:\n"
                                "1. Call `audit_node_drift` with `mode='both'`.\n"
                                "2. Read `dotfiles://system/manifests` and `dotfiles://layer/identity`.\n"
                                "3. Summarize any symlink, package, or repository discrepancies."
                            ),
                        },
                    }
                ],
            }

        if name == "orchestrate-federated-mcps":
            goal = args.get("workflow_goal", "multi-service operation")
            return {
                "description": f"Guardrailed MCP orchestration for: {goal}",
                "messages": [
                    {
                        "role": "user",
                        "content": {
                            "type": "text",
                            "text": (
                                f"Workflow goal: {goal}\n\n"
                                "Before calling any downstream database, cloud, or service MCP:\n"
                                "1. Call `discover_federated_mcps` on this `dotfiles-ubuntu` "
                                "layer MCP.\n"
                                "2. Extract the `required_guardrails` for every target MCP.\n"
                                "3. Call `query_governance_rules` for any referenced rules and "
                                "enforce them strictly throughout execution."
                            ),
                        },
                    }
                ],
            }

        raise ValueError(f"Unknown prompt name: {name!r}")

    # ------------------------------------------------------------------
    # JSON-RPC 2.0 Dispatcher
    # ------------------------------------------------------------------
    def handle_request(self, message: dict[str, Any]) -> dict[str, Any] | None:
        method = message.get("method", "")
        msg_id = message.get("id")
        params = message.get("params") or {}

        # Notifications (no id) do not return a response
        if msg_id is None:
            return None

        try:
            if method == "initialize":
                result: dict[str, Any] = {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {
                        "resources": {"subscribe": False, "listChanged": False},
                        "tools": {"listChanged": False},
                        "prompts": {"listChanged": False},
                    },
                    "serverInfo": {
                        "name": "dotfiles-ubuntu-mcp",
                        "version": _read_version(),
                    },
                }
            elif method == "ping":
                result = {}
            elif method == "resources/list":
                result = {"resources": self.list_resources()}
            elif method == "resources/templates/list":
                result = {"resourceTemplates": []}
            elif method == "resources/read":
                uri = str(params.get("uri", ""))
                result = {"contents": [self.read_resource(uri)]}
            elif method == "tools/list":
                result = {"tools": self.list_tools()}
            elif method == "tools/call":
                tool_name = str(params.get("name", ""))
                tool_args = params.get("arguments") or {}
                result = self.call_tool(tool_name, tool_args)
            elif method == "prompts/list":
                result = {"prompts": self.list_prompts()}
            elif method == "prompts/get":
                prompt_name = str(params.get("name", ""))
                prompt_args = params.get("arguments") or {}
                result = self.get_prompt(prompt_name, prompt_args)
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}",
                    },
                }
            resp: dict[str, Any] = {"jsonrpc": "2.0", "id": msg_id, "result": result}
            resp_bytes = len(json.dumps(resp).encode("utf-8"))
            if resp_bytes > MCP_PAYLOAD_WARN_BYTES:
                self._emit_warning(
                    "WARN",
                    "LARGE_MCP_PAYLOAD_WARNING",
                    f"MCP response for {method!r} is {resp_bytes} bytes "
                    f"(~{resp_bytes // 4} tokens > {MCP_PAYLOAD_WARN_BYTES}-byte soft cap).",
                    {"method": method, "response_bytes": resp_bytes},
                )
            self._write_jsonl(
                "mcp_events.jsonl",
                {
                    "ts": datetime.now(UTC).isoformat(),
                    "method": method,
                    "target": str(params.get("name") or params.get("uri") or method),
                    "status": "ok",
                    "response_bytes": resp_bytes,
                    "estimated_tokens": resp_bytes // 4,
                },
            )
            return resp
        except (ValueError, FileNotFoundError, KeyError) as exc:
            self._emit_warning(
                "WARN",
                "SECURITY_OR_VALIDATION_ERROR",
                str(exc),
                {"method": method},
            )
            self._write_jsonl(
                "mcp_events.jsonl",
                {
                    "ts": datetime.now(UTC).isoformat(),
                    "method": method,
                    "target": str(params.get("name") or params.get("uri") or method),
                    "status": "error",
                    "error": str(exc),
                },
            )
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": -32602, "message": str(exc)},
            }
        except Exception as exc:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": -32603, "message": f"Internal error: {exc}"},
            }


def run_stdio_loop(server: DotfilesMCPServer) -> None:
    """Serve JSON-RPC 2.0 over stdio (supports line-delimited and Content-Length framing)."""
    stdin_buf = sys.stdin.buffer
    stdout_buf = sys.stdout.buffer

    while True:
        first_line = stdin_buf.readline()
        if not first_line:
            break

        stripped = first_line.strip()
        if not stripped:
            continue

        use_content_length = False
        if stripped.lower().startswith(b"content-length:"):
            use_content_length = True
            length = int(stripped.split(b":", 1)[1].strip())
            while True:
                header_line = stdin_buf.readline()
                if not header_line or header_line in (b"\r\n", b"\n"):
                    break
            raw_body = stdin_buf.read(length)
        else:
            raw_body = stripped

        try:
            request = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            err_resp = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": f"Parse error: {exc}"},
            }
            payload = json.dumps(err_resp).encode("utf-8")
            stdout_buf.write(payload + b"\n")
            stdout_buf.flush()
            continue

        response = server.handle_request(request)
        if response is None:
            continue

        out_bytes = json.dumps(response).encode("utf-8")
        if use_content_length:
            header = f"Content-Length: {len(out_bytes)}\r\n\r\n".encode("ascii")
            stdout_buf.write(header + out_bytes)
        else:
            stdout_buf.write(out_bytes + b"\n")
        stdout_buf.flush()


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def run_self_test(server: DotfilesMCPServer) -> int:
    """Execute deterministic in-process verification of all MCP capabilities."""
    print(f"═══ dotfiles-ubuntu MCP Server Self-Test (v{_read_version()}) ═══")

    # 1. Initialize
    init_resp = server.handle_request(
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
    )
    _require(bool(init_resp and "result" in init_resp), "initialize failed")
    print("  ✅ initialize handshake ok")

    # 2. Resources list & read all 9 resources
    res_list = (
        server.handle_request({"jsonrpc": "2.0", "id": 2, "method": "resources/list", "params": {}})
        or {}
    )
    _require(
        bool(res_list and len(res_list["result"]["resources"]) == 9),
        "Expected 9 resources",
    )
    for res in res_list["result"]["resources"]:
        uri = res["uri"]
        read_resp = (
            server.handle_request(
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "resources/read",
                    "params": {"uri": uri},
                }
            )
            or {}
        )
        _require(bool(read_resp and "result" in read_resp), f"Failed reading {uri}")
        text = read_resp["result"]["contents"][0]["text"]
        _require(len(text) > 0, f"Empty resource payload for {uri}")
    print("  ✅ resources/list & resources/read verified across all 9 resources")

    # 3. Tools list & call
    tools_list = server.handle_request(
        {"jsonrpc": "2.0", "id": 4, "method": "tools/list", "params": {}}
    )
    _require(
        bool(tools_list and len(tools_list["result"]["tools"]) == 6),
        "Expected 6 tools",
    )

    overview = server.handle_request(
        {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {"name": "get_layer_overview", "arguments": {}},
        }
    )
    _require(
        bool(overview and not overview["result"]["isError"]),
        "get_layer_overview failed",
    )

    doc_read = server.handle_request(
        {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "tools/call",
            "params": {
                "name": "read_layer_document",
                "arguments": {"relative_path": "docs/README.md"},
            },
        }
    )
    _require(
        bool(doc_read and "Documentation Index" in doc_read["result"]["content"][0]["text"]),
        "read_layer_document failed",
    )

    query_res = server.handle_request(
        {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call",
            "params": {
                "name": "query_governance_rules",
                "arguments": {"query": "AAA", "scope": "all"},
            },
        }
    )
    _require(
        bool(query_res and not query_res["result"]["isError"]),
        "query_governance_rules failed",
    )

    fed_res = server.handle_request(
        {
            "jsonrpc": "2.0",
            "id": 8,
            "method": "tools/call",
            "params": {"name": "discover_federated_mcps", "arguments": {}},
        }
    )
    _require(
        bool(fed_res and not fed_res["result"]["isError"]),
        "discover_federated_mcps failed",
    )

    cmp_res = server.handle_request(
        {
            "jsonrpc": "2.0",
            "id": 9,
            "method": "tools/call",
            "params": {
                "name": "compare_layer_patterns",
                "arguments": {
                    "project_rules": ["coding.md", "custom-domain.md"],
                    "project_skills": ["sopen", "custom-skill"],
                },
            },
        }
    )
    _require(
        bool(cmp_res and not cmp_res["result"]["isError"]),
        "compare_layer_patterns failed",
    )

    # 4. Path-containment security gate verification
    traversal_attempt = server.handle_request(
        {
            "jsonrpc": "2.0",
            "id": 10,
            "method": "tools/call",
            "params": {
                "name": "read_layer_document",
                "arguments": {"relative_path": "../../../etc/passwd"},
            },
        }
    )
    _require(
        bool(traversal_attempt and "error" in traversal_attempt),
        "Path traversal must be rejected",
    )
    diag_after = server.handle_request(
        {
            "jsonrpc": "2.0",
            "id": 101,
            "method": "resources/read",
            "params": {"uri": "dotfiles://mcp/diagnostics"},
        }
    )
    _require(
        bool(diag_after and "result" in diag_after),
        "Failed reading dotfiles://mcp/diagnostics after tools",
    )
    print("  ✅ tools/list, tools/call & path-containment security gate verified")

    # 5. Prompts list & get
    prompts_list = (
        server.handle_request({"jsonrpc": "2.0", "id": 11, "method": "prompts/list", "params": {}})
        or {}
    )
    _require(
        bool(prompts_list and len(prompts_list["result"]["prompts"]) == 3),
        "Expected 3 prompts",
    )
    for pr in prompts_list["result"]["prompts"]:
        p_resp = server.handle_request(
            {
                "jsonrpc": "2.0",
                "id": 12,
                "method": "prompts/get",
                "params": {"name": pr["name"], "arguments": {"workflow_goal": "test"}},
            }
        )
        _require(bool(p_resp and "result" in p_resp), f"Failed prompt {pr['name']}")
    print("  ✅ prompts/list & prompts/get verified across all 3 prompts")
    print("🎉 MCP server self-test passed (0 errors)!")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="dotfiles_mcp_server.py",
        description=(
            "Zero-dependency, read-only Model Context Protocol (MCP) server "
            "for dotfiles-ubuntu layer, container, and system introspection."
        ),
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"dotfiles-ubuntu-mcp v{_read_version()}",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run deterministic in-process self-test of all MCP resources, tools, and prompts.",
    )
    parser.add_argument(
        "--layer-id",
        default=None,
        help="Override layer_id from system/mcp-layer.json.",
    )
    parser.add_argument(
        "--layer-role",
        choices=VALID_LAYER_ROLES,
        default=None,
        help="Override layer_role from system/mcp-layer.json.",
    )
    parser.add_argument(
        "--log-dir",
        default=None,
        help="Directory for structured JSONL event & alert logs (default: ./logs).",
    )
    parser.add_argument(
        "--no-log",
        action="store_true",
        help="Disable writing mcp_events.jsonl and mcp_alerts.jsonl to disk.",
    )
    args = parser.parse_args(argv)

    if args.self_test:
        with tempfile.TemporaryDirectory() as tmp_log:
            test_log_dir = None if args.no_log else Path(args.log_dir or tmp_log)
            server = DotfilesMCPServer(
                repo_dir=REPO_DIR,
                layer_id_override=args.layer_id,
                layer_role_override=args.layer_role,
                log_dir=test_log_dir,
            )
            rc = run_self_test(server)
            if test_log_dir is not None:
                _require((test_log_dir / "mcp_events.jsonl").is_file(), "Missing mcp_events.jsonl")
                _require((test_log_dir / "mcp_alerts.jsonl").is_file(), "Missing mcp_alerts.jsonl")
            return rc

    resolved_log_dir = (
        None
        if args.no_log
        else Path(args.log_dir or os.environ.get("DOTFILES_MCP_LOG_DIR", str(REPO_DIR / "logs")))
    )
    server = DotfilesMCPServer(
        repo_dir=REPO_DIR,
        layer_id_override=args.layer_id,
        layer_role_override=args.layer_role,
        log_dir=resolved_log_dir,
    )
    run_stdio_loop(server)
    return 0


if __name__ == "__main__":
    sys.exit(main())
