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
import base64
import contextlib
import fnmatch
import hashlib
import hmac
import json
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import zlib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_DIR = SCRIPT_DIR.parent
PROTOCOL_VERSION = "2024-11-05"
VALID_LAYER_ROLES = (
    "corporate",
    "department",
    "domain-policy",
    "team",
    "service-node",
    "environment-cluster",
    "workstation",
)
VALID_ENVIRONMENTS = ("dev", "tst", "pre", "pro")
VALID_ARCHITECTURAL_PLANES = (
    "schema",
    "domain",
    "application",
    "presentation",
    "infrastructure",
    "testing",
)
PLANE_PATH_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("testing", ("tests/", "e2e/", "__tests__/", "test_", "_test.", ".spec.")),
    (
        "presentation",
        (
            "templates/",
            "static/",
            "ui/",
            "views/",
            "components/",
            "pages/",
            ".html",
            ".css",
            ".scss",
            ".tsx",
            ".jsx",
            ".vue",
        ),
    ),
    (
        "schema",
        (
            "models.py",
            "schema.py",
            "schemas/",
            "migrations/",
            "alembic/",
            "entities/",
            ".sql",
            ".prisma",
        ),
    ),
    ("domain", ("service.py", "domain.py", "ports.py", "domain/", "services/", "policies/")),
    (
        "application",
        (
            "router.py",
            "controller.py",
            "use_cases.py",
            "tasks.py",
            "dependencies.py",
            "application/",
            "use_cases/",
            "routers/",
            "api/",
            "handlers/",
        ),
    ),
    (
        "infrastructure",
        (
            "repository.py",
            "dockerfile",
            "repositories/",
            "adapters/",
            "infrastructure/",
            "infra/",
            "db/",
        ),
    ),
)
STRUCTURAL_PATH_SEGMENTS = frozenset(
    {
        "src",
        "app",
        "internal",
        "pkg",
        "lib",
        "templates",
        "static",
        "partials",
        "components",
        "css",
        "js",
        "tests",
        "unit",
        "imp",
        "e2e",
        "docs",
        "architecture",
        "reference",
    }
)
CAPSULE_PREFIX = "rcap1"
VALID_RESOLUTIONS = ("L0", "L1", "L2")
VALID_CAPSULE_LEVELS = ("L0", "L1", "L2", "L3")
VALID_AGENT_TIERS = ("flash", "inherit", "pro")
AGENT_TIER_RANK: dict[str, int] = {"flash": 1, "inherit": 2, "pro": 3}
LEVEL_INDEX: dict[str, int] = {"L0": 0, "L1": 1, "L2": 2, "L3": 3}
NEXT_LEVEL_MAP: dict[str, str] = {"L0": "L1", "L1": "L2", "L2": "L3"}
LEVEL_MIN_TIER: dict[str, str] = {"L0": "flash", "L1": "flash", "L2": "inherit", "L3": "inherit"}
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
MD_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
BACKTICK_PATH_RE = re.compile(r"`([a-zA-Z0-9_./-]+\.(?:md|html|j2|css))`")
BOLD_TERM_RE = re.compile(r"\*\*([^*]{3,40})\*\*")
WORD_TOKEN_RE = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_-]{2,}")
CODON_STOPWORDS = frozenset(
    {
        "the",
        "and",
        "for",
        "with",
        "that",
        "this",
        "from",
        "are",
        "must",
        "never",
        "when",
        "all",
        "any",
        "not",
        "use",
        "only",
        "into",
        "over",
    }
)

MCP_RESOURCES_CATALOG: tuple[dict[str, Any], ...] = (
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
            "Deterministic PreToolUse, PostToolUse, PostInvocation, and Stop hook definitions."
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
)

MCP_TOOLS_CATALOG: tuple[dict[str, Any], ...] = (
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
                        "Target layer ('root' or a mounted subtree name/layer_id under layers/*)."
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
                        "Optional layer ('root' or a mounted subtree name/layer_id under layers/*)."
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
            "and/or mounted git subtree layers (layers/*) by keyword or topic, "
            "with optional multi-resolution compaction (L0 Promoter Codon, "
            "L1 Axiom Skeleton, or L2 Full Section) and chained rcap1 capsules."
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
                "resolution": {
                    "type": "string",
                    "enum": ["L0", "L1", "L2"],
                    "default": "L2",
                    "description": (
                        "Compaction depth: 'L0' (Promoter Codon headers + rcap1:L0 capsules), "
                        "'L1' (Axiom Skeletons + rcap1:L1 capsules), or 'L2' (full sections + "
                        "rcap1:L2 capsules; default)."
                    ),
                },
                "environment": {
                    "type": "string",
                    "enum": ["dev", "tst", "pre", "pro"],
                    "description": (
                        "Optional environment binding ('dev', 'tst', 'pre', or 'pro') "
                        "for chained context capsules."
                    ),
                },
                "resonance_key": {
                    "type": "string",
                    "description": (
                        "Optional resonance secret key to cryptographically seal "
                        "the returned rcap1 context capsules."
                    ),
                },
                "include_capsules": {
                    "type": "boolean",
                    "default": True,
                    "description": (
                        "Whether to mint and attach rcap1 capsule_token envelopes to each match "
                        "(set to false when querying L2/L1 without needing subsequent unfolding)."
                    ),
                },
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
    {
        "name": "unfold_context_capsule",
        "description": (
            "Inspect or progressively decrypt and decompress a Resonant Context Capsule "
            "(rcap1:...) from L0 (Promoter Codon) -> L1 (Axiom Skeleton) -> L2 (Full Section) "
            "-> L3 (Deep Linked Skill/Spec), enforcing sequential hash chaining and "
            "agent capability/environment gates."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "capsule_token": {
                    "type": "string",
                    "description": (
                        "Chained context capsule token ('rcap1.<header>.<payload>.<sig>') "
                        "returned by query_governance_rules or unfold_context_capsule."
                    ),
                },
                "target_level": {
                    "type": "string",
                    "enum": ["L0", "L1", "L2", "L3"],
                    "description": (
                        "Target unfolding depth: 'L0' (promoter header inspection only), "
                        "'L1' (Axiom Skeleton), 'L2' (Full Section), or 'L3' (Deep Linked "
                        "Skills/Specs). Defaults to the next sequential level."
                    ),
                },
                "agent_tier": {
                    "type": "string",
                    "enum": ["flash", "inherit", "pro"],
                    "default": "inherit",
                    "description": (
                        "Calling agent capability tier per AGENTS.md §13 ('flash' is capped "
                        "at L1; 'inherit' and 'pro' can unfold L2 and L3)."
                    ),
                },
                "environment": {
                    "type": "string",
                    "enum": ["dev", "tst", "pre", "pro"],
                    "description": (
                        "Optional target environment context ('dev', 'tst', 'pre', or 'pro')."
                    ),
                },
                "resonance_key": {
                    "type": "string",
                    "description": (
                        "Optional capability/resonance secret key to unlock key-gated capsules."
                    ),
                },
            },
            "required": ["capsule_token"],
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
    {
        "name": "resolve_surface_governance",
        "description": (
            "Project and weave governance rules, invariants, canonical templates, "
            "and rcap1 context capsules across 0..N mounted layers (Root + layers/*) "
            "for a target application surface (target_path, architectural_plane, "
            "scope, traits), ordered by numeric deontic precedence (0..100)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "target_path": {
                    "type": "string",
                    "description": (
                        "Optional relative file path in the target project "
                        "(e.g. 'templates/checkout/summary.html', 'src/legal/router.py')."
                    ),
                },
                "architectural_plane": {
                    "type": "string",
                    "enum": list(VALID_ARCHITECTURAL_PLANES),
                    "description": (
                        "Optional stack-agnostic architectural plane ('schema', 'domain', "
                        "'application', 'presentation', 'infrastructure', or 'testing')."
                    ),
                },
                "scope": {
                    "type": "string",
                    "description": (
                        "Optional feature module, domain slice, or bounded context name "
                        "(e.g. 'checkout', 'legal', 'catalog')."
                    ),
                },
                "traits": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Optional semantic cross-cutting tags "
                        "(e.g. ['pii', 'financial', 'public-facing'])."
                    ),
                },
                "environment": {
                    "type": "string",
                    "enum": ["dev", "tst", "pre", "pro"],
                    "description": "Optional target environment ('dev', 'tst', 'pre', 'pro').",
                },
                "resolution_override": {
                    "type": "string",
                    "enum": ["L0", "L1", "L2"],
                    "description": (
                        "Optional resolution override ('L0', 'L1', or 'L2'). Defaults to "
                        "adaptive ('L2' for authoritative bindings, 'L1' for transversal)."
                    ),
                },
                "resonance_key": {
                    "type": "string",
                    "description": "Optional resonance secret key to seal rcap1 capsules.",
                },
                "include_capsules": {
                    "type": "boolean",
                    "default": True,
                    "description": "Whether to attach rcap1 capsule_token envelopes.",
                },
            },
            "additionalProperties": False,
        },
    },
)

MCP_PROMPTS_CATALOG: tuple[dict[str, Any], ...] = (
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
            "Audit live package, symlink, and repository drift on this container or server node."
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
            "their inherited effective_guardrails and activation_policy before "
            "executing cross-service operations."
        ),
        "arguments": [
            {
                "name": "workflow_goal",
                "description": "Goal of the multi-service or infrastructure operation.",
                "required": True,
            },
            {
                "name": "environment",
                "description": "Optional target environment ('dev', 'tst', 'pre', or 'pro').",
                "required": False,
            },
            {
                "name": "layer",
                "description": "Optional target layer ('all', 'root', or a mounted subtree).",
                "required": False,
            },
        ],
    },
)


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


def _is_running_in_container(marker_path: Path | None = None) -> bool:
    marker = marker_path or Path("/.dockerenv")
    return marker.is_file()


def _read_git_commit(repo_dir: Path | None = None) -> str:
    base_dir = repo_dir or REPO_DIR
    env_fallback = os.environ.get("DOTFILES_GIT_COMMIT", "").strip()
    git_bin = shutil.which("git")
    if not git_bin:
        return env_fallback or "unknown"
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
    return env_fallback or "unknown"


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


def _count_result_warnings(result: dict[str, Any]) -> int:
    content_list = result.get("content")
    if not isinstance(content_list, list) or not content_list:
        return 0
    first_text = content_list[0].get("text", "")
    if not isinstance(first_text, str) or not first_text.startswith("{"):
        return 0
    with contextlib.suppress(json.JSONDecodeError):
        parsed: dict[str, Any] = json.loads(first_text)
        top_w = parsed.get("warnings")
        if isinstance(top_w, list):
            return len(top_w)
        ch3 = parsed.get("channel_3_active_invariants_and_hooks")
        if isinstance(ch3, dict) and isinstance(ch3.get("warnings"), list):
            return len(ch3["warnings"])
    return 0


def _extract_compaction_event_fields(target: str, result: dict[str, Any]) -> dict[str, Any]:
    content_list = result.get("content")
    if not isinstance(content_list, list) or not content_list:
        return {}
    first_text = content_list[0].get("text", "")
    if not isinstance(first_text, str) or not first_text.startswith("{"):
        return {}
    with contextlib.suppress(json.JSONDecodeError):
        parsed: dict[str, Any] = json.loads(first_text)
        if target in ("query_governance_rules", "resolve_surface_governance"):
            metrics = parsed.get("token_compaction_metrics", {})
            return {
                "resolution": str(
                    parsed.get("resolution") or metrics.get("resolution", "adaptive")
                ),
                "tokens_saved": int(metrics.get("tokens_saved", 0)),
                "savings_pct": float(metrics.get("savings_pct", 0.0)),
            }
        if target == "unfold_context_capsule":
            return {
                "unfolded_level": parsed.get("unfolded_level"),
                "agent_tier": str(parsed.get("agent_tier", "inherit")),
                "decrypted_hops": int(parsed.get("decrypted_hops", 0)),
            }
    return {}


def _infer_plane_from_path(rel_path: str) -> str:
    norm = rel_path.strip().replace("\\", "/").lstrip("/").lower()
    return next(
        (plane for plane, tokens in PLANE_PATH_RULES if any(tok in norm for tok in tokens)),
        "",
    )


def _infer_scope_from_path(rel_path: str) -> str:
    parts = [
        p
        for p in rel_path.strip().replace("\\", "/").strip("/").split("/")
        if p and "." not in p and p.lower() not in STRUCTURAL_PATH_SEGMENTS
    ]
    return parts[0].lower() if parts else ""


def _glob_matches(rel_path: str, pattern: str) -> bool:
    norm_path = rel_path.strip().replace("\\", "/").lstrip("/")
    norm_pat = pattern.strip().replace("\\", "/").lstrip("/")
    return bool(
        norm_pat == "**"
        or fnmatch.fnmatchcase(norm_path, norm_pat)
        or (norm_pat.endswith("/**") and norm_path.startswith(norm_pat[:-2]))
    )


def _binding_matches_surface(
    binding: dict[str, Any],
    target_path: str,
    plane: str,
    scope: str,
    traits: set[str],
) -> bool:
    globs = [str(g) for g in binding.get("target_globs", ["**"])]
    planes = [str(p).lower() for p in binding.get("architectural_planes", ["*"])]
    scopes = [str(s).lower() for s in binding.get("scopes", ["*"])]
    req_traits = {str(t).lower() for t in binding.get("traits", [])}
    glob_ok = not target_path or any(_glob_matches(target_path, g) for g in globs)
    plane_ok = not plane or "*" in planes or plane in planes
    scope_ok = not scope or "*" in scopes or scope in scopes
    traits_ok = not req_traits or bool(req_traits & traits)
    return glob_ok and plane_ok and scope_ok and traits_ok


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64url_decode(token: str) -> bytes:
    padding = "=" * ((4 - len(token) % 4) % 4)
    return base64.urlsafe_b64decode((token + padding).encode("ascii"))


def _slugify_codon(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:36]
    return slug or "section"


def _extract_codon_tags(heading: str, body_text: str) -> list[str]:
    candidates = [heading, *BOLD_TERM_RE.findall(body_text)]
    tags: list[str] = []
    for chunk in candidates:
        for word in WORD_TOKEN_RE.findall(chunk.lower()):
            if word not in CODON_STOPWORDS and word not in tags:
                tags.append(word)
                if len(tags) == 5:
                    return tags
    return tags


def _extract_axiom_skeleton(heading: str, body_lines: list[str]) -> str:
    exons: list[str] = [f"## {heading}"]
    bullets = 0
    folded = 0
    in_code = False
    for raw in body_lines:
        stripped = raw.strip()
        if stripped.startswith("```"):
            in_code = not in_code
            folded += 1
            continue
        if in_code or not stripped or stripped.startswith(("#", "|", "---")):
            if stripped and not stripped.startswith("#"):
                folded += 1
            continue
        if stripped.startswith(">") or stripped.startswith(("**Mandate", "**Description")):
            exons.append(stripped[:160])
        elif stripped.startswith(("- ", "* ")) or re.match(r"^\d+\.\s", stripped):
            if bullets < 4:
                exons.append(stripped[:120])
                bullets += 1
            else:
                folded += 1
        elif len(exons) == 1:
            exons.append(stripped[:160])
        else:
            folded += 1
    if folded > 0:
        exons.append(f"[+{folded} detail/table/code lines folded in rcap1:L1]")
    return "\n".join(exons)


class CapsuleError(ValueError):
    """Raised when an rcap1 context capsule fails verification and has already emitted an alert."""


def _iter_markdown_sections(
    lines: list[str],
    default_heading: str,
) -> list[tuple[str, int, int, list[str]]]:
    sections: list[tuple[str, int, int, list[str]]] = []
    current_heading = default_heading
    section_start = 1
    section_lines: list[str] = []
    for idx, line in enumerate(lines, start=1):
        if line.startswith(("## ", "### ", "#### ")) and section_lines:
            sections.append((current_heading, section_start, idx - 1, section_lines))
            current_heading = line.lstrip("#").strip()
            section_start = idx
            section_lines = [line]
        else:
            if line.startswith("# ") and idx == 1:
                current_heading = line.lstrip("#").strip()
            section_lines.append(line)
    if section_lines:
        sections.append((current_heading, section_start, len(lines), section_lines))
    return sections


def _extract_l3_links(
    source_file: Path,
    section_text: str,
    layer_root: Path,
) -> list[dict[str, Any]]:
    raw_refs = [m.group(2).split("#")[0].strip() for m in MD_LINK_RE.finditer(section_text)]
    raw_refs.extend(m.group(1).strip() for m in BACKTICK_PATH_RE.finditer(section_text))
    seen: set[str] = set()
    links: list[dict[str, Any]] = []
    root_resolved = layer_root.resolve()
    for ref in raw_refs:
        if not ref or ref.startswith(("http://", "https://", "mailto:")):
            continue
        for base in (source_file.parent, root_resolved):
            cand = (base / ref).resolve()
            if cand.is_file() and cand.is_relative_to(root_resolved):
                rel_str = str(cand.relative_to(root_resolved)).replace("\\", "/")
                if rel_str not in seen and (
                    rel_str in ALLOWED_ROOT_FILES
                    or any(rel_str.startswith(p) for p in ALLOWED_READ_PREFIXES)
                ):
                    seen.add(rel_str)
                    raw_bytes = cand.read_bytes()
                    size = len(raw_bytes)
                    links.append(
                        {
                            "path": rel_str,
                            "bytes": size,
                            "estimated_tokens": max(1, size // 4),
                            "sha256": hashlib.sha256(raw_bytes).hexdigest()[:16],
                        }
                    )
                break
    return links


def _compute_digest16(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16]


def _derive_chain_key(
    secret: bytes,
    layer_name: str,
    level: str,
    parent_hash: str,
    env_scope: str,
) -> bytes:
    ctx = f"rcap1-key:{layer_name}:{level}:{parent_hash}:{env_scope}".encode()
    return hmac.new(secret, ctx, hashlib.sha256).digest()


def _xor_keystream(data: bytes, key: bytes) -> bytes:
    out = bytearray(len(data))
    offset = 0
    counter = 0
    while offset < len(data):
        block = hashlib.sha256(key + counter.to_bytes(4, "big")).digest()
        chunk_len = min(32, len(data) - offset)
        for idx in range(chunk_len):
            out[offset + idx] = data[offset + idx] ^ block[idx]
        offset += chunk_len
        counter += 1
    return bytes(out)


def _seal_single_capsule(
    header: dict[str, Any],
    inner_payload: dict[str, Any],
    chain_key: bytes,
) -> str:
    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    raw_inner = json.dumps(inner_payload, separators=(",", ":")).encode("utf-8")
    compressed = zlib.compress(raw_inner, level=9)
    encrypted = _xor_keystream(compressed, chain_key)
    cipher_b64 = _b64url_encode(encrypted)
    signing_input = f"{CAPSULE_PREFIX}.{header_b64}.{cipher_b64}".encode("ascii")
    sig_hex = hmac.new(chain_key, signing_input, hashlib.sha256).hexdigest()[:24]
    return f"{CAPSULE_PREFIX}.{header_b64}.{cipher_b64}.{sig_hex}"


def _parse_capsule_envelope(capsule_token: str) -> tuple[dict[str, Any], str, bytes, str]:
    parts = capsule_token.strip().split(".")
    if len(parts) != 4 or parts[0] != CAPSULE_PREFIX:
        raise ValueError("Malformed rcap1 context capsule envelope")
    _, header_b64, cipher_b64, sig_hex = parts
    try:
        header = json.loads(_b64url_decode(header_b64).decode("utf-8"))
        cipher_bytes = _b64url_decode(cipher_b64)
    except Exception as exc:
        raise ValueError(f"Invalid base64 or JSON in rcap1 capsule header: {exc}") from exc
    if not isinstance(header, dict) or header.get("lvl") not in NEXT_LEVEL_MAP:
        raise ValueError("Invalid or unsupported rcap1 capsule header level")
    return header, f"{CAPSULE_PREFIX}.{header_b64}.{cipher_b64}", cipher_bytes, sig_hex


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
            "schema_version": "1.2",
            "layer_id": base_dir.name if base_dir != self.repo_dir else "dotfiles-ubuntu-default",
            "layer_role": "workstation",
            "precedence": 10 if base_dir == self.repo_dir else 50,
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
            "surface_bindings": [],
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
                    "precedence": int(sub_manifest.get("precedence", 50)),
                    "surface_binding_count": len(sub_manifest.get("surface_bindings", [])),
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

    # ------------------------------------------------------------------
    # Tools
    # ------------------------------------------------------------------
    def list_tools(self) -> list[dict[str, Any]]:
        return [dict(item) for item in MCP_TOOLS_CATALOG]

    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        args = arguments or {}
        if name == "get_layer_overview":
            return self._tool_get_layer_overview(args)
        if name == "audit_node_drift":
            return self._tool_audit_node_drift(args)
        if name == "read_layer_document":
            return self._tool_read_layer_document(args)
        if name == "query_governance_rules":
            return self._tool_query_governance_rules(args)
        if name == "unfold_context_capsule":
            return self._tool_unfold_context_capsule(args)
        if name == "discover_federated_mcps":
            return self._tool_discover_federated_mcps(args)
        if name == "compare_layer_patterns":
            return self._tool_compare_layer_patterns(args)
        if name == "resolve_surface_governance":
            return self._tool_resolve_surface_governance(args)
        raise ValueError(f"Unknown tool name: {name!r}")

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

    def _resolve_resonance_secret(self, explicit_key: str | None = None) -> bytes:
        raw_key = (
            (explicit_key or "").strip()
            or os.environ.get("DOTFILES_RESONANCE_KEY", "").strip()
            or f"dotfiles-resonance-v1:{_read_version(self.repo_dir)}"
        )
        return raw_key.encode("utf-8")

    def _build_section_capsule(
        self,
        *,
        resolution: str,
        layer_name: str,
        rel_in_layer: str,
        heading: str,
        start_line: int,
        end_line: int,
        scope: str,
        l1_skeleton: str,
        l2_excerpt: str,
        l2_full: str,
        l3_links: list[dict[str, Any]],
        env_scope: str,
        secret: bytes,
        key_required: bool = False,
    ) -> tuple[dict[str, Any], str]:
        l0_summary = f"[{layer_name}] {rel_in_layer} :: {heading}"
        l3_tokens = sum(int(item["estimated_tokens"]) for item in l3_links) + 60
        cost_map = {
            "L0": max(1, len(l0_summary) // 4),
            "L1": max(1, len(l1_skeleton) // 4),
            "L2": max(1, len(l2_excerpt) // 4),
            "L3": l3_tokens,
        }
        tags = _extract_codon_tags(heading, l2_excerpt)
        promoter_codon = {
            "codon": f"AUG:{scope}:{_slugify_codon(heading)}:UAA",
            "layer": layer_name,
            "tags": tags,
            "l3_links_count": len(l3_links),
            "token_estimates": cost_map,
        }
        l3_paths = [str(item["path"]) for item in l3_links]
        h0 = _compute_digest16(layer_name, rel_in_layer, heading)
        h1 = _compute_digest16(h0, l1_skeleton)
        h2 = _compute_digest16(h1, l2_full)
        h3 = _compute_digest16(
            h2,
            *(f"{item['path']}:{item['sha256']}" for item in l3_links),
        )
        digest_by_level = {"L0": h0, "L1": h1, "L2": h2, "L3": h3}
        issuer_id = str(self._load_layer_manifest().get("layer_id", "root"))
        base_meta = {
            "lyr": layer_name,
            "sc": scope,
            "f": rel_in_layer,
            "s": start_line,
            "e": end_line,
            "env": env_scope,
            "h1": h1,
        }
        next_cap: str | None = None
        capsules_by_level: dict[str, str] = {}
        for lvl in ("L2", "L1", "L0"):
            nxt = NEXT_LEVEL_MAP[lvl]
            ph = digest_by_level[lvl]
            min_tier = "pro" if (env_scope == "pro" and nxt == "L3") else LEVEL_MIN_TIER[nxt]
            hdr = {
                "v": 1,
                "lvl": lvl,
                "next": nxt,
                "iss": issuer_id,
                "lyr": layer_name,
                "sec": heading[:80],
                "codon": promoter_codon["codon"],
                "tags": tags,
                "cost": cost_map,
                "cap": min_tier,
                "env": env_scope,
                "kr": key_required,
                "ph": ph,
            }
            inner_lvl: dict[str, Any] = {
                **base_meta,
                "ph": ph,
                "h_cur": ph,
                "h_next": digest_by_level[nxt],
            }
            if lvl == "L2":
                inner_lvl["l3"] = l3_paths
            else:
                inner_lvl["next_cap"] = next_cap
            ck = _derive_chain_key(secret, layer_name, lvl, ph, env_scope)
            next_cap = _seal_single_capsule(hdr, inner_lvl, ck)
            capsules_by_level[lvl] = next_cap
        return promoter_codon, capsules_by_level[resolution]

    def _tool_query_governance_rules(self, args: dict[str, Any]) -> dict[str, Any]:
        query = str(args.get("query", "")).strip()
        if not query:
            raise ValueError("'query' must be a non-empty string")
        scope = str(args.get("scope", "all"))
        resolution = str(args.get("resolution", "L2")).strip().upper() or "L2"
        if resolution not in VALID_RESOLUTIONS:
            raise ValueError(
                f"Invalid resolution {resolution!r}: must be one of {VALID_RESOLUTIONS}"
            )
        env_arg = str(args.get("environment", "")).strip().lower()
        if env_arg and env_arg not in VALID_ENVIRONMENTS:
            raise ValueError(
                f"Invalid environment {env_arg!r}: must be one of {VALID_ENVIRONMENTS}"
            )
        env_scope = env_arg or "all"
        include_capsules = bool(args.get("include_capsules", True))
        explicit_key = (
            str(args["resonance_key"]).strip() if args.get("resonance_key") is not None else ""
        )
        key_required = bool(explicit_key or os.environ.get("DOTFILES_RESONANCE_KEY", "").strip())
        secret = self._resolve_resonance_secret(explicit_key or None)
        layer_arg = str(args.get("layer", "all")).strip() or "all"
        if layer_arg == "all":
            layer_dirs = [
                self.repo_dir,
                *(self.repo_dir / str(m["relative_path"]) for m in self._discover_mounted_layers()),
            ]
        else:
            layer_dirs = [self._resolve_layer_dir(layer_arg)]

        candidate_files: list[tuple[str, Path, Path]] = []
        for ldir in layer_dirs:
            lname = "root" if ldir == self.repo_dir else ldir.name
            if scope in ("all", "global"):
                candidate_files.append((lname, ldir, ldir / "antigravity/.gemini/config/AGENTS.md"))
            if scope in ("all", "templates"):
                for tf in sorted((ldir / "templates").glob("*/rules/*.md")):
                    candidate_files.append((lname, ldir, tf))
            if scope in ("all", "docs"):
                for df in sorted((ldir / "docs").rglob("*.md")):
                    candidate_files.append((lname, ldir, df))

        matches: list[dict[str, Any]] = []
        excerpt_truncated = False
        q_lower = query.lower()
        for lname, ldir, file_path in candidate_files:
            if not file_path.is_file():
                continue
            lines = file_path.read_text(encoding="utf-8").splitlines()
            for heading, start_line, end_line, body in _iter_markdown_sections(
                lines, file_path.name
            ):
                joined = "\n".join(body)
                if q_lower in joined.lower() or q_lower in heading.lower():
                    if resolution == "L2" and len(joined) > 1500:
                        excerpt_truncated = True
                    l2_excerpt = joined[:1500]
                    l2_full = joined[:8000]
                    l1_skeleton = _extract_axiom_skeleton(heading, body)
                    l3_links = _extract_l3_links(file_path, joined, ldir)
                    rel_in_layer = str(file_path.relative_to(ldir)).replace("\\", "/")
                    promoter_codon, capsule_token = self._build_section_capsule(
                        resolution=resolution,
                        layer_name=lname,
                        rel_in_layer=rel_in_layer,
                        heading=heading,
                        start_line=start_line,
                        end_line=end_line,
                        scope=scope,
                        l1_skeleton=l1_skeleton,
                        l2_excerpt=l2_excerpt,
                        l2_full=l2_full,
                        l3_links=l3_links,
                        env_scope=env_scope,
                        secret=secret,
                        key_required=key_required,
                    )
                    entry: dict[str, Any] = {
                        "file": str(file_path.relative_to(self.repo_dir)),
                        "layer": lname,
                        "section": heading,
                        "start_line": start_line,
                        "end_line": end_line,
                        "promoter_codon": promoter_codon,
                        "capsule_token": capsule_token if include_capsules else None,
                    }
                    if resolution == "L0":
                        entry["surface_preview"] = (
                            f"{promoter_codon['codon']} ({', '.join(promoter_codon['tags'])})"
                        )
                    elif resolution == "L1":
                        entry["axiom_skeleton"] = l1_skeleton
                        entry["excerpt"] = l1_skeleton
                    else:
                        entry["excerpt"] = l2_excerpt
                    matches.append(entry)

        total_matches = len(matches)
        returned_matches = matches[:15]
        returned_tokens = sum(
            int(m["promoter_codon"]["token_estimates"][resolution]) for m in returned_matches
        )
        capsule_overhead_tokens = (
            sum(len(str(m["capsule_token"])) // 4 for m in returned_matches)
            if include_capsules
            else 0
        )
        baseline_l2_tokens = sum(
            int(m["promoter_codon"]["token_estimates"]["L2"]) for m in returned_matches
        )
        tokens_saved = max(0, baseline_l2_tokens - returned_tokens)
        savings_pct = (
            round((tokens_saved / baseline_l2_tokens) * 100, 1) if baseline_l2_tokens > 0 else 0.0
        )

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
                            "resolution": resolution,
                            "include_capsules": include_capsules,
                            "token_compaction_metrics": {
                                "resolution": resolution,
                                "returned_estimated_tokens": returned_tokens,
                                "capsule_overhead_tokens": capsule_overhead_tokens,
                                "full_l2_baseline_tokens": baseline_l2_tokens,
                                "tokens_saved": tokens_saved,
                                "savings_pct": savings_pct,
                            },
                            "total_matches_found": total_matches,
                            "match_count": len(returned_matches),
                            "truncated": bool(query_warnings),
                            "warnings": query_warnings,
                            "matches": returned_matches,
                        },
                        indent=2,
                    ),
                }
            ],
            "isError": False,
        }

    def _tool_unfold_context_capsule(self, args: dict[str, Any]) -> dict[str, Any]:
        raw_token = str(args.get("capsule_token", "")).strip()
        try:
            header, signing_prefix, cipher_bytes, sig_hex = _parse_capsule_envelope(raw_token)
        except ValueError as exc:
            self._emit_warning(
                "WARN",
                "CAPSULE_CHAIN_BROKEN",
                str(exc),
                {"capsule_prefix": raw_token[:32]},
            )
            raise CapsuleError(
                f"{exc} [Recovery: Re-run query_governance_rules to obtain a fresh capsule.]"
            ) from exc

        cur_lvl = str(header["lvl"])
        default_next = str(header.get("next", NEXT_LEVEL_MAP[cur_lvl]))
        target_level = str(args.get("target_level") or default_next).strip().upper()
        if target_level not in VALID_CAPSULE_LEVELS:
            raise ValueError(
                f"Invalid target_level {target_level!r}: must be one of {VALID_CAPSULE_LEVELS}"
            )

        agent_tier = str(args.get("agent_tier", "inherit")).strip().lower() or "inherit"
        if agent_tier not in VALID_AGENT_TIERS:
            raise ValueError(
                f"Invalid agent_tier {agent_tier!r}: must be one of {VALID_AGENT_TIERS}"
            )

        env_arg = str(args.get("environment", "")).strip().lower()
        if env_arg and env_arg not in VALID_ENVIRONMENTS:
            raise ValueError(
                f"Invalid environment {env_arg!r}: must be one of {VALID_ENVIRONMENTS}"
            )

        expected_issuer = str(self._load_layer_manifest().get("layer_id", "root"))
        cap_issuer = str(header.get("iss") or expected_issuer)
        if cap_issuer != expected_issuer:
            msg = (
                f"Cross-node capsule mismatch: capsule was issued by MCP node {cap_issuer!r}, "
                f"but this MCP server is {expected_issuer!r}. "
                "[Recovery: Invoke unfold_context_capsule on the issuing MCP server node.]"
            )
            self._emit_warning(
                "WARN",
                "CAPSULE_RESONANCE_DENIED",
                msg,
                {"reason": "issuer_node_mismatch", "capsule_issuer": cap_issuer},
            )
            raise CapsuleError(msg)

        cap_env = str(header.get("env", "all"))
        if cap_env != "all" and env_arg != cap_env:
            msg = (
                f"Capsule is bound to environment {cap_env!r}; "
                f"cannot unfold with environment={env_arg or 'unspecified'!r}. "
                f"[Recovery: Pass environment={cap_env!r}.]"
            )
            self._emit_warning(
                "WARN",
                "CAPSULE_RESONANCE_DENIED",
                msg,
                {"reason": "environment_mismatch", "capsule_env": cap_env},
            )
            raise CapsuleError(msg)

        explicit_key = (
            str(args["resonance_key"]).strip() if args.get("resonance_key") is not None else ""
        )
        env_key = os.environ.get("DOTFILES_RESONANCE_KEY", "").strip()
        if header.get("kr") is True and not (explicit_key or env_key):
            msg = (
                "Capsule requires an explicit resonance_key (header.kr=true), "
                "but none was provided via arguments or DOTFILES_RESONANCE_KEY. "
                "[Recovery: Provide resonance_key or re-query without key gating.]"
            )
            self._emit_warning(
                "WARN",
                "CAPSULE_RESONANCE_DENIED",
                msg,
                {"reason": "missing_resonance_key", "level": cur_lvl},
            )
            raise CapsuleError(msg)

        secret = self._resolve_resonance_secret(explicit_key or None)
        hdr_layer = str(header.get("lyr", "root"))
        step_key = _derive_chain_key(secret, hdr_layer, cur_lvl, str(header.get("ph", "")), cap_env)
        expected_sig = hmac.new(
            step_key, signing_prefix.encode("ascii"), hashlib.sha256
        ).hexdigest()[:24]
        if not hmac.compare_digest(sig_hex, expected_sig):
            msg = (
                "Capsule resonance signature verification failed "
                "(invalid resonance_key or tampered capsule). "
                "[Recovery: Verify resonance_key or re-run query_governance_rules.]"
            )
            self._emit_warning(
                "WARN",
                "CAPSULE_RESONANCE_DENIED",
                msg,
                {"reason": "hmac_mismatch", "level": cur_lvl},
            )
            raise CapsuleError(msg)

        if target_level == "L0":
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "unfolded_level": "L0",
                                "unfold_chain": [],
                                "decrypted_hops": 0,
                                "chain_verified": True,
                                "truncated": False,
                                "warnings": [],
                                "promoter_header": header,
                                "next_capsule_token": raw_token,
                            },
                            indent=2,
                        ),
                    }
                ],
                "isError": False,
            }

        if LEVEL_INDEX[target_level] <= LEVEL_INDEX[cur_lvl]:
            raise ValueError(
                f"target_level {target_level!r} must be deeper than capsule level {cur_lvl!r} "
                "(or 'L0' for promoter inspection)"
            )

        required_tier = (
            "pro" if (cap_env == "pro" and target_level == "L3") else LEVEL_MIN_TIER[target_level]
        )
        if AGENT_TIER_RANK[agent_tier] < AGENT_TIER_RANK[required_tier]:
            msg = (
                f"Agent tier {agent_tier!r} is insufficient to unfold {target_level!r} "
                f"(requires {required_tier!r} per AGENTS.md §13 Model Delegation Discipline). "
                f"[Recovery: Request target_level='L1' or delegate to a {required_tier!r} agent.]"
            )
            self._emit_warning(
                "WARN",
                "CAPSULE_CAPABILITY_INSUFFICIENT",
                msg,
                {"agent_tier": agent_tier, "target_level": target_level},
            )
            raise CapsuleError(msg)

        step_lvl = cur_lvl
        step_header = header
        step_cipher = cipher_bytes
        unfold_chain: list[str] = []
        inner: dict[str, Any] = {}
        digest_map: dict[str, str] = {}
        layer_name = hdr_layer
        layer_dir = self._resolve_layer_dir(layer_name)
        rel_file = ""
        target_file = self.repo_dir
        start_line = 1
        end_line = 1
        heading = str(header.get("sec", ""))
        joined_section = ""
        l1_skeleton = ""
        l3_links: list[dict[str, Any]] = []
        line_drift_relocated = False

        while step_lvl != target_level:
            nxt = NEXT_LEVEL_MAP[step_lvl]
            try:
                decrypted_bytes = _xor_keystream(step_cipher, step_key)
                inner = json.loads(zlib.decompress(decrypted_bytes).decode("utf-8"))
            except Exception as exc:
                msg = (
                    f"Failed to decompress chained capsule interior at {step_lvl}->{nxt}: {exc} "
                    "[Recovery: Re-run query_governance_rules to mint a fresh capsule.]"
                )
                self._emit_warning("WARN", "CAPSULE_CHAIN_BROKEN", msg, {"level": step_lvl})
                raise CapsuleError(msg) from exc

            if not isinstance(inner, dict) or inner.get("ph") != step_header.get("ph"):
                msg = (
                    f"Capsule parent hash mismatch inside decrypted payload at {step_lvl}->{nxt} "
                    "[Recovery: Re-run query_governance_rules to mint a fresh capsule.]"
                )
                self._emit_warning("WARN", "CAPSULE_CHAIN_BROKEN", msg, {"level": step_lvl})
                raise CapsuleError(msg)

            if not digest_map:
                rel_file = str(inner.get("f", ""))
                target_file = self._resolve_safe_path(rel_file, layer_dir)
                all_lines = target_file.read_text(encoding="utf-8").splitlines()
                start_line = max(1, int(inner.get("s", 1)))
                end_line = min(len(all_lines), int(inner.get("e", len(all_lines))))
                section_lines = all_lines[start_line - 1 : end_line]
                l1_skeleton = _extract_axiom_skeleton(heading, section_lines)
                live_h0 = _compute_digest16(layer_name, rel_file, heading)
                live_h1 = _compute_digest16(live_h0, l1_skeleton)
                if live_h1 != inner.get("h1"):
                    _, start_line, end_line, section_lines = next(
                        (
                            sec
                            for sec in _iter_markdown_sections(all_lines, target_file.name)
                            if sec[0] == heading
                        ),
                        (heading, start_line, end_line, section_lines),
                    )
                    l1_skeleton = _extract_axiom_skeleton(heading, section_lines)
                    live_h1 = _compute_digest16(live_h0, l1_skeleton)
                    line_drift_relocated = live_h1 == inner.get("h1")
                joined_section = "\n".join(section_lines)
                l3_links = _extract_l3_links(target_file, joined_section, layer_dir)
                live_h2 = _compute_digest16(live_h1, joined_section[:8000])
                live_h3 = _compute_digest16(
                    live_h2,
                    *(f"{item['path']}:{item['sha256']}" for item in l3_links),
                )
                digest_map = {"L0": live_h0, "L1": live_h1, "L2": live_h2, "L3": live_h3}

            if inner.get("h_cur") != digest_map[step_lvl] or inner.get("h_next") != digest_map[nxt]:
                msg = (
                    f"Capsule chain digest mismatch at {step_lvl}->{nxt}: "
                    "underlying section drifted or payload tampered. "
                    "[Recovery: Re-run query_governance_rules(resolution='L2') for fresh content.]"
                )
                self._emit_warning(
                    "WARN",
                    "CAPSULE_CHAIN_BROKEN",
                    msg,
                    {"file": rel_file, "hop": f"{step_lvl}->{nxt}"},
                )
                raise CapsuleError(msg)

            unfold_chain.append(f"{step_lvl}->{nxt}")
            step_lvl = nxt
            if step_lvl != target_level:
                step_header, _, step_cipher, _ = _parse_capsule_envelope(str(inner["next_cap"]))
                step_key = _derive_chain_key(
                    secret, layer_name, step_lvl, digest_map[step_lvl], cap_env
                )

        next_capsule_token = str(inner["next_cap"]) if "next_cap" in inner else None
        l3_paths = [str(item["path"]) for item in l3_links]
        unfold_truncated = (target_level in ("L2", "L3") and len(joined_section) > 8000) or (
            target_level == "L3"
            and (len(l3_paths) > 5 or any(int(item["bytes"]) > 4000 for item in l3_links[:5]))
        )
        unfold_warnings: list[dict[str, Any]] = []
        if unfold_truncated:
            unfold_warnings.append(
                self._emit_warning(
                    "WARN",
                    "RESPONSE_TRUNCATED",
                    f"Unfolded {target_level} context for section {heading!r} exceeded inline "
                    "excerpt bounds (8,000-char section or 5x4,000-char L3 link cap). "
                    "Use 'read_layer_document' to inspect complete files.",
                    {
                        "file": str(target_file.relative_to(self.repo_dir)),
                        "target_level": target_level,
                        "section_chars": len(joined_section),
                        "l3_links_count": len(l3_paths),
                    },
                )
            )

        if target_level == "L1":
            unfolded_body: dict[str, Any] = {
                "file": str(target_file.relative_to(self.repo_dir)),
                "layer": layer_name,
                "section": heading,
                "start_line": start_line,
                "end_line": end_line,
                "axiom_skeleton": l1_skeleton,
                "l3_links_count": len(l3_links),
            }
        elif target_level == "L2":
            unfolded_body = {
                "file": str(target_file.relative_to(self.repo_dir)),
                "layer": layer_name,
                "section": heading,
                "start_line": start_line,
                "end_line": end_line,
                "full_section": joined_section[:8000],
                "l3_links": l3_links,
            }
        else:
            linked_docs: list[dict[str, Any]] = []
            for l3_path in l3_paths[:5]:
                l3_file = self._resolve_safe_path(l3_path, layer_dir)
                l3_text = l3_file.read_text(encoding="utf-8")
                linked_docs.append(
                    {
                        "path": str(l3_file.relative_to(self.repo_dir)),
                        "line_count": len(l3_text.splitlines()),
                        "excerpt": l3_text[:4000],
                    }
                )
            root_manifest = self._load_layer_manifest()
            layer_manifest = self._load_layer_manifest(layer_dir)
            effective_env = env_arg or (cap_env if cap_env != "all" else "")
            root_env_g = (
                root_manifest.get("environments", {})
                .get(effective_env, {})
                .get("default_guardrails", [])
                if effective_env
                else []
            )
            layer_env_g = (
                layer_manifest.get("environments", {})
                .get(effective_env, {})
                .get("default_guardrails", [])
                if effective_env
                else []
            )
            unfolded_body = {
                "file": str(target_file.relative_to(self.repo_dir)),
                "layer": layer_name,
                "section": heading,
                "full_section": joined_section[:8000],
                "linked_l3_documents": linked_docs,
                "effective_guardrails": _merge_unique_strings(
                    root_manifest.get("baseline_guardrails", []),
                    layer_manifest.get("baseline_guardrails", []),
                    root_env_g,
                    layer_env_g,
                ),
                "federated_mcps": layer_manifest.get("federated_mcps", []),
            }

        payload = {
            "unfolded_level": target_level,
            "unfold_chain": unfold_chain,
            "decrypted_hops": len(unfold_chain),
            "chain_verified": True,
            "line_drift_relocated": line_drift_relocated,
            "agent_tier": agent_tier,
            "environment": cap_env,
            "parent_digest": header.get("ph"),
            "level_digest": digest_map[target_level],
            "truncated": bool(unfold_warnings),
            "warnings": unfold_warnings,
            "promoter_header": header,
            "content": unfolded_body,
            "next_capsule_token": next_capsule_token,
        }
        return {
            "content": [{"type": "text", "text": json.dumps(payload, indent=2)}],
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
                    s for s in proj_skills if s not in layer_a_skills and s not in layer_b_skills
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

    def _tool_resolve_surface_governance(self, args: dict[str, Any]) -> dict[str, Any]:
        target_path = str(args.get("target_path", "")).strip()
        explicit_plane = str(args.get("architectural_plane", "")).strip().lower()
        if explicit_plane and explicit_plane not in VALID_ARCHITECTURAL_PLANES:
            raise ValueError(
                f"Invalid architectural_plane {explicit_plane!r}: "
                f"must be one of {VALID_ARCHITECTURAL_PLANES}"
            )
        explicit_scope = str(args.get("scope", "")).strip().lower()
        raw_traits = args.get("traits") or []
        traits_list = sorted({str(t).strip().lower() for t in raw_traits if str(t).strip()})
        traits_set = set(traits_list)
        if not (target_path or explicit_plane or explicit_scope or traits_set):
            raise ValueError(
                "At least one surface selector ('target_path', 'architectural_plane', "
                "'scope', or 'traits') must be provided"
            )
        env_arg = str(args.get("environment", "")).strip().lower()
        if env_arg and env_arg not in VALID_ENVIRONMENTS:
            raise ValueError(
                f"Invalid environment {env_arg!r}: must be one of {VALID_ENVIRONMENTS}"
            )
        res_override = str(args.get("resolution_override", "")).strip().upper()
        if res_override and res_override not in VALID_RESOLUTIONS:
            raise ValueError(
                f"Invalid resolution_override {res_override!r}: must be one of {VALID_RESOLUTIONS}"
            )
        include_capsules = bool(args.get("include_capsules", True))
        explicit_key = (
            str(args["resonance_key"]).strip() if args.get("resonance_key") is not None else ""
        )
        key_required = bool(explicit_key or os.environ.get("DOTFILES_RESONANCE_KEY", "").strip())
        secret = self._resolve_resonance_secret(explicit_key or None)
        env_scope = env_arg or "all"
        effective_plane = explicit_plane or _infer_plane_from_path(target_path)
        effective_scope = explicit_scope or _infer_scope_from_path(target_path)

        layer_dirs = [
            self.repo_dir,
            *(self.repo_dir / str(m["relative_path"]) for m in self._discover_mounted_layers()),
        ]
        participating_layers: list[dict[str, Any]] = []
        pruned_layers: list[dict[str, Any]] = []
        matched_records: list[tuple[int, int, str, Path, str, str, dict[str, Any]]] = []
        layer_guardrails_in_order: list[tuple[int, list[str]]] = []

        for ldir in layer_dirs:
            lname = "root" if ldir == self.repo_dir else ldir.name
            manifest = self._load_layer_manifest(ldir)
            layer_id = str(manifest.get("layer_id", lname))
            layer_role = str(manifest.get("layer_role", "service-node"))
            default_prec = 10 if ldir == self.repo_dir else 50
            layer_prec = int(manifest.get("precedence", default_prec))
            raw_bindings = manifest.get("surface_bindings") or [
                {
                    "binding_id": f"{lname}-default-baseline",
                    "target_globs": ["**"],
                    "architectural_planes": ["*"],
                    "scopes": ["*"],
                    "traits": [],
                    "mode": "transversal",
                    "rule_files": ["antigravity/.gemini/config/AGENTS.md"],
                    "canonical_templates": [],
                    "invariants": list(manifest.get("baseline_guardrails", [])),
                }
            ]
            matched_in_layer = [
                b
                for b in raw_bindings
                if isinstance(b, dict)
                and _binding_matches_surface(
                    b, target_path, effective_plane, effective_scope, traits_set
                )
            ]
            if not matched_in_layer:
                pruned_layers.append(
                    {
                        "layer": lname,
                        "layer_id": layer_id,
                        "layer_role": layer_role,
                        "precedence": layer_prec,
                    }
                )
                continue

            participating_layers.append(
                {
                    "layer": lname,
                    "layer_id": layer_id,
                    "layer_role": layer_role,
                    "precedence": layer_prec,
                    "matched_bindings_count": len(matched_in_layer),
                }
            )
            env_g = (
                manifest.get("environments", {}).get(env_arg, {}).get("default_guardrails", [])
                if env_arg
                else []
            )
            layer_guardrails_in_order.append(
                (layer_prec, [*manifest.get("baseline_guardrails", []), *env_g])
            )
            for b in matched_in_layer:
                b_prec = int(b.get("precedence", layer_prec))
                m_rank = 0 if str(b.get("mode", "")).lower() == "authoritative" else 1
                matched_records.append((b_prec, m_rank, lname, ldir, layer_id, layer_role, b))

        participating_layers.sort(key=lambda item: (int(item["precedence"]), str(item["layer_id"])))
        matched_records.sort(
            key=lambda rec: (rec[0], rec[1], rec[4], str(rec[6].get("binding_id", "")))
        )
        layer_guardrails_in_order.sort(key=lambda item: item[0])

        resolved_bindings: list[dict[str, Any]] = []
        invariant_groups: list[list[str]] = [g for _, g in layer_guardrails_in_order]
        template_groups: list[list[str]] = []
        returned_tokens = 0
        capsule_overhead_tokens = 0
        baseline_l2_tokens = 0

        for b_prec, _, lname, ldir, layer_id, layer_role, b in matched_records:
            mode = (
                "authoritative"
                if str(b.get("mode", "")).lower() == "authoritative"
                else "transversal"
            )
            res = res_override or ("L2" if mode == "authoritative" else "L1")
            b_invariants = [str(inv) for inv in b.get("invariants", []) if str(inv).strip()]
            b_templates = [str(tpl) for tpl in b.get("canonical_templates", []) if str(tpl).strip()]
            invariant_groups.append(b_invariants)
            template_groups.append([f"{lname}:{tpl}" for tpl in b_templates])

            sections_out: list[dict[str, Any]] = []
            for rf_rel in b.get("rule_files", []):
                rf_path = (ldir / str(rf_rel).strip().lstrip("/")).resolve()
                if not rf_path.is_file():
                    continue
                lines = rf_path.read_text(encoding="utf-8").splitlines()
                rel_in_layer = str(rf_path.relative_to(ldir)).replace("\\", "/")
                for heading, start_line, end_line, body in _iter_markdown_sections(
                    lines, rf_path.name
                )[:3]:
                    joined = "\n".join(body)
                    l2_excerpt = joined[:1500]
                    l2_full = joined[:8000]
                    l1_skeleton = _extract_axiom_skeleton(heading, body)
                    l3_links = _extract_l3_links(rf_path, joined, ldir)
                    promoter_codon, capsule_token = self._build_section_capsule(
                        resolution=res,
                        layer_name=lname,
                        rel_in_layer=rel_in_layer,
                        heading=heading,
                        start_line=start_line,
                        end_line=end_line,
                        scope=effective_scope or "all",
                        l1_skeleton=l1_skeleton,
                        l2_excerpt=l2_excerpt,
                        l2_full=l2_full,
                        l3_links=l3_links,
                        env_scope=env_scope,
                        secret=secret,
                        key_required=key_required,
                    )
                    sec_entry: dict[str, Any] = {
                        "file": str(rf_path.relative_to(self.repo_dir)),
                        "layer": lname,
                        "section": heading,
                        "start_line": start_line,
                        "end_line": end_line,
                        "resolution": res,
                        "promoter_codon": promoter_codon,
                        "capsule_token": capsule_token if include_capsules else None,
                    }
                    if res == "L0":
                        sec_entry["surface_preview"] = (
                            f"{promoter_codon['codon']} ({', '.join(promoter_codon['tags'])})"
                        )
                    elif res == "L1":
                        sec_entry["axiom_skeleton"] = l1_skeleton
                        sec_entry["excerpt"] = l1_skeleton
                    else:
                        sec_entry["excerpt"] = l2_excerpt
                    sections_out.append(sec_entry)
                    returned_tokens += int(promoter_codon["token_estimates"][res])
                    baseline_l2_tokens += int(promoter_codon["token_estimates"]["L2"])
                    if include_capsules:
                        capsule_overhead_tokens += len(capsule_token) // 4

            resolved_bindings.append(
                {
                    "binding_id": str(b.get("binding_id", f"{lname}-binding")),
                    "layer": lname,
                    "layer_id": layer_id,
                    "layer_role": layer_role,
                    "precedence": b_prec,
                    "mode": mode,
                    "resolution": res,
                    "invariants": b_invariants,
                    "canonical_templates": b_templates,
                    "sections": sections_out,
                }
            )

        tokens_saved = max(0, baseline_l2_tokens - returned_tokens)
        savings_pct = (
            round((tokens_saved / baseline_l2_tokens) * 100, 1) if baseline_l2_tokens > 0 else 0.0
        )
        payload = {
            "surface_query": {
                "target_path": target_path,
                "effective_plane": effective_plane or "all",
                "effective_scope": effective_scope or "all",
                "traits": traits_list,
                "environment": env_scope,
                "resolution_mode": res_override or "adaptive",
            },
            "precedence_policy": (
                "Numeric precedence (0..100, lower value = higher authority / Lex Superior); "
                "authoritative bindings default to L2, transversal bindings default to L1."
            ),
            "participating_layers_count": len(participating_layers),
            "participating_layers": participating_layers,
            "pruned_layers_count": len(pruned_layers),
            "pruned_layers": pruned_layers,
            "resolved_bindings_count": len(resolved_bindings),
            "resolved_bindings": resolved_bindings,
            "effective_invariants": _merge_unique_strings(*invariant_groups),
            "canonical_templates": _merge_unique_strings(*template_groups),
            "token_compaction_metrics": {
                "resolution": res_override or "adaptive",
                "returned_estimated_tokens": returned_tokens,
                "capsule_overhead_tokens": capsule_overhead_tokens,
                "full_l2_baseline_tokens": baseline_l2_tokens,
                "tokens_saved": tokens_saved,
                "savings_pct": savings_pct,
            },
            "warnings": [],
        }
        return {
            "content": [{"type": "text", "text": json.dumps(payload, indent=2)}],
            "isError": False,
        }

    # ------------------------------------------------------------------
    # Prompts
    # ------------------------------------------------------------------
    def list_prompts(self) -> list[dict[str, Any]]:
        return [dict(item) for item in MCP_PROMPTS_CATALOG]

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
            env_scope = args.get("environment", "pre")
            layer_scope = args.get("layer", "all")
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
                                f"1. Call `discover_federated_mcps(layer={layer_scope!r}, "
                                f"environment={env_scope!r})` on this layer MCP.\n"
                                "2. Verify each target MCP's `activation_policy` "
                                "(`when_to_invoke` / `avoid_when`) and extract its merged "
                                "`effective_guardrails`.\n"
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

        t0 = time.perf_counter()
        raw_args = params.get("arguments")
        tool_args: dict[str, Any] = raw_args if isinstance(raw_args, dict) else {}
        logged_layer = str(tool_args.get("layer") or "root")
        logged_env = str(tool_args.get("environment") or "all")

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
                result = self.call_tool(tool_name, tool_args)
            elif method == "prompts/list":
                result = {"prompts": self.list_prompts()}
            elif method == "prompts/get":
                prompt_name = str(params.get("name", ""))
                result = self.get_prompt(prompt_name, tool_args)
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}",
                    },
                }
            duration_ms = round((time.perf_counter() - t0) * 1000, 2)
            resp: dict[str, Any] = {"jsonrpc": "2.0", "id": msg_id, "result": result}
            resp_bytes = len(json.dumps(resp).encode("utf-8"))
            warning_count = _count_result_warnings(result)
            if resp_bytes > MCP_PAYLOAD_WARN_BYTES:
                warning_count += 1
                self._emit_warning(
                    "WARN",
                    "LARGE_MCP_PAYLOAD_WARNING",
                    f"MCP response for {method!r} is {resp_bytes} bytes "
                    f"(~{resp_bytes // 4} tokens > {MCP_PAYLOAD_WARN_BYTES}-byte soft cap).",
                    {"method": method, "response_bytes": resp_bytes},
                )
            target_name = str(params.get("name") or params.get("uri") or method)
            self._write_jsonl(
                "mcp_events.jsonl",
                {
                    "ts": datetime.now(UTC).isoformat(),
                    "method": method,
                    "target": target_name,
                    "layer": logged_layer,
                    "environment": logged_env,
                    "duration_ms": duration_ms,
                    "status": "ok",
                    "response_bytes": resp_bytes,
                    "estimated_tokens": resp_bytes // 4,
                    "warning_count": warning_count,
                    **_extract_compaction_event_fields(target_name, result),
                },
            )
            return resp
        except (ValueError, FileNotFoundError, KeyError) as exc:
            duration_ms = round((time.perf_counter() - t0) * 1000, 2)
            if not isinstance(exc, CapsuleError):
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
                    "layer": logged_layer,
                    "environment": logged_env,
                    "duration_ms": duration_ms,
                    "status": "error",
                    "warning_count": 1,
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
        bool(tools_list and len(tools_list["result"]["tools"]) == 8),
        "Expected 8 tools",
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
                "arguments": {"query": "AAA", "scope": "global", "resolution": "L0"},
            },
        }
    )
    _require(
        bool(query_res and not query_res["result"]["isError"]),
        "query_governance_rules failed",
    )
    query_payload = json.loads(query_res["result"]["content"][0]["text"])  # type: ignore[index]
    first_capsule = query_payload["matches"][0]["capsule_token"]
    unfold_l1 = server.handle_request(
        {
            "jsonrpc": "2.0",
            "id": 71,
            "method": "tools/call",
            "params": {
                "name": "unfold_context_capsule",
                "arguments": {
                    "capsule_token": first_capsule,
                    "target_level": "L1",
                    "agent_tier": "flash",
                },
            },
        }
    )
    _require(
        bool(unfold_l1 and not unfold_l1["result"]["isError"]),
        "unfold_context_capsule (L0->L1) failed",
    )
    l1_payload = json.loads(unfold_l1["result"]["content"][0]["text"])  # type: ignore[index]
    unfold_l3 = server.handle_request(
        {
            "jsonrpc": "2.0",
            "id": 72,
            "method": "tools/call",
            "params": {
                "name": "unfold_context_capsule",
                "arguments": {
                    "capsule_token": l1_payload["next_capsule_token"],
                    "target_level": "L3",
                    "agent_tier": "inherit",
                },
            },
        }
    )
    _require(
        bool(unfold_l3 and not unfold_l3["result"]["isError"]),
        "unfold_context_capsule (L1->L3) failed",
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

    surf_res = server.handle_request(
        {
            "jsonrpc": "2.0",
            "id": 91,
            "method": "tools/call",
            "params": {
                "name": "resolve_surface_governance",
                "arguments": {"target_path": "src/checkout/service.py"},
            },
        }
    )
    _require(
        bool(surf_res and not surf_res["result"]["isError"]),
        "resolve_surface_governance failed",
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
    resolved_layer_id = args.layer_id or os.environ.get("DOTFILES_LAYER_ID") or None
    resolved_layer_role = args.layer_role or os.environ.get("DOTFILES_LAYER_ROLE") or None

    if args.self_test:
        if args.no_log:
            return run_self_test(
                DotfilesMCPServer(
                    repo_dir=REPO_DIR,
                    layer_id_override=resolved_layer_id,
                    layer_role_override=resolved_layer_role,
                    log_dir=None,
                )
            )
        try:
            with tempfile.TemporaryDirectory() as tmp_log:
                test_log_dir = Path(args.log_dir or tmp_log)
                server = DotfilesMCPServer(
                    repo_dir=REPO_DIR,
                    layer_id_override=resolved_layer_id,
                    layer_role_override=resolved_layer_role,
                    log_dir=test_log_dir,
                )
                rc = run_self_test(server)
                _require((test_log_dir / "mcp_events.jsonl").is_file(), "Missing mcp_events.jsonl")
                _require((test_log_dir / "mcp_alerts.jsonl").is_file(), "Missing mcp_alerts.jsonl")
                return rc
        except OSError:
            return run_self_test(
                DotfilesMCPServer(
                    repo_dir=REPO_DIR,
                    layer_id_override=resolved_layer_id,
                    layer_role_override=resolved_layer_role,
                    log_dir=None,
                )
            )

    resolved_log_dir = (
        None
        if args.no_log
        else Path(args.log_dir or os.environ.get("DOTFILES_MCP_LOG_DIR", str(REPO_DIR / "logs")))
    )
    server = DotfilesMCPServer(
        repo_dir=REPO_DIR,
        layer_id_override=resolved_layer_id,
        layer_role_override=resolved_layer_role,
        log_dir=resolved_log_dir,
    )
    run_stdio_loop(server)
    return 0


if __name__ == "__main__":
    sys.exit(main())
