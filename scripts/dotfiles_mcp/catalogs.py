"""Declarative JSON-RPC catalogs for MCP resources, tools, and prompts.

Specification: docs/architecture/03_contextual_mcp_and_federation.md
"""

from __future__ import annotations

from typing import Any

from dotfiles_mcp.constants import (
    VALID_AGENT_TIERS,
    VALID_ARCHITECTURAL_PLANES,
    VALID_EPHEMERAL_ACCESS_MODES,
    VALID_EPHEMERAL_ACTIONS,
)

MCP_RESOURCES_CATALOG: tuple[dict[str, Any], ...] = (
    {
        "uri": "dotfiles://layer/identity",
        "name": "Layer & System Node Identity",
        "description": "Repository SemVer version, layer_id, layer_role, OS release, and lineage.",
        "mimeType": "application/json",
    },
    {
        "uri": "dotfiles://system/manifests",
        "name": "Declarative Ubuntu System Manifests",
        "description": "Tracked APT packages, Snaps, NPM globals, NVM default, and GNOME state.",
        "mimeType": "application/json",
    },
    {
        "uri": "dotfiles://governance/rules",
        "name": "Layer A Global Engineering Rules (AGENTS.md)",
        "description": "Universal behavioral mandates, strict typing, AAA testing, and governance.",
        "mimeType": "text/markdown",
    },
    {
        "uri": "dotfiles://governance/hooks",
        "name": "Antigravity Lifecycle Hooks Configuration (hooks.json)",
        "description": "Deterministic PreToolUse, PostToolUse, PostInvocation, and Stop hooks.",
        "mimeType": "application/json",
    },
    {
        "uri": "dotfiles://governance/skills",
        "name": "Global Skills Catalog",
        "description": "Structured list of global slash-command and procedural engineering skills.",
        "mimeType": "application/json",
    },
    {
        "uri": "dotfiles://governance/templates",
        "name": "Layer B Stack Starter Templates",
        "description": "Inventory of reusable project starter templates available in templates/.",
        "mimeType": "application/json",
    },
    {
        "uri": "dotfiles://docs/index",
        "name": "Navigable Documentation Index (docs/README.md)",
        "description": "Structured index of architecture specs and reference guides.",
        "mimeType": "text/markdown",
    },
    {
        "uri": "dotfiles://mcp/topology",
        "name": "Federated MCP Topology & Guardrails (system/mcp-layer.json)",
        "description": "Downstream and sibling MCP servers associated with this layer.",
        "mimeType": "application/json",
    },
    {
        "uri": "dotfiles://mcp/diagnostics",
        "name": "Runtime MCP Event & Alert Diagnostics (logs/mcp_*.jsonl)",
        "description": "Live telemetry summary of recent MCP calls, sizes, and alerts from logs/.",
        "mimeType": "application/json",
    },
)

MCP_TOOLS_CATALOG: tuple[dict[str, Any], ...] = (
    {
        "name": "get_layer_overview",
        "description": "Return a 4-Channel Executive Digest of this node or a layers/* subtree.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "layer": {"type": "string", "description": "Target layer ('root' or subtree)."}
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "audit_node_drift",
        "description": "Run deterministic read-only verification and/or system drift audit.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "mode": {
                    "type": "string",
                    "enum": ["verify-repo", "system-audit", "both"],
                    "default": "verify-repo",
                    "description": "Audit mode ('verify-repo', 'system-audit', or 'both').",
                }
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "read_layer_document",
        "description": "Read a Markdown spec, template rule, skill, or manifest file in a layer.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "relative_path": {"type": "string", "description": "Path relative to layer root."},
                "layer": {"type": "string", "description": "Optional layer ('root' or subtree)."},
            },
            "required": ["relative_path"],
            "additionalProperties": False,
        },
    },
    {
        "name": "query_governance_rules",
        "description": "Search Layer A rules, templates, and docs with L0/L1/L2 rcap1 compaction.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Keyword or phrase to search."},
                "scope": {
                    "type": "string",
                    "enum": ["all", "global", "templates", "docs"],
                    "default": "all",
                    "description": "Subset of layer documentation to search.",
                },
                "layer": {
                    "type": "string",
                    "default": "all",
                    "description": "Target layer filter.",
                },
                "resolution": {
                    "type": "string",
                    "enum": ["L0", "L1", "L2"],
                    "default": "L2",
                    "description": "Compaction depth ('L0', 'L1', or 'L2'; default 'L2').",
                },
                "environment": {
                    "type": "string",
                    "enum": ["dev", "tst", "pre", "pro"],
                    "description": "Optional environment binding ('dev', 'tst', 'pre', or 'pro').",
                },
                "resonance_key": {"type": "string", "description": "Optional rcap1 secret key."},
                "include_capsules": {
                    "type": "boolean",
                    "default": True,
                    "description": "Whether to mint and attach rcap1 capsule_token envelopes.",
                },
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
    {
        "name": "unfold_context_capsule",
        "description": "Decrypt and decompress an rcap1 capsule across L0->L1->L2->L3 levels.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "capsule_token": {"type": "string", "description": "Chained rcap1 capsule token."},
                "target_level": {
                    "type": "string",
                    "enum": ["L0", "L1", "L2", "L3"],
                    "description": "Target unfolding depth ('L0', 'L1', 'L2', or 'L3').",
                },
                "agent_tier": {
                    "type": "string",
                    "enum": list(VALID_AGENT_TIERS),
                    "default": "inherit",
                    "description": "Calling agent tier per AGENTS.md §13 (flash, inherit, pro).",
                },
                "environment": {
                    "type": "string",
                    "enum": ["dev", "tst", "pre", "pro"],
                    "description": "Optional target environment ('dev', 'tst', 'pre', or 'pro').",
                },
                "resonance_key": {"type": "string", "description": "Optional secret key."},
            },
            "required": ["capsule_token"],
            "additionalProperties": False,
        },
    },
    {
        "name": "discover_federated_mcps",
        "description": "Discover downstream or sibling MCP servers and inherited guardrails.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "filter_role": {"type": "string", "description": "Optional role substring filter."},
                "environment": {
                    "type": "string",
                    "enum": ["dev", "tst", "pre", "pro"],
                    "description": "Optional environment filter ('dev', 'tst', 'pre', or 'pro').",
                },
                "layer": {
                    "type": "string",
                    "default": "all",
                    "description": "Target layer filter.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "compare_layer_patterns",
        "description": "Compare project rules/skills against layers for upward promotion or sync.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_rules": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Rule filenames in the project (e.g. ['coding.md']).",
                },
                "project_skills": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Skill names in the project (e.g. ['start']).",
                },
                "layer": {
                    "type": "string",
                    "default": "all",
                    "description": "Target layer filter.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "resolve_surface_governance",
        "description": "Project and weave governance rules across 0..N layers for a surface.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "target_path": {"type": "string", "description": "Optional relative file path."},
                "architectural_plane": {
                    "type": "string",
                    "enum": list(VALID_ARCHITECTURAL_PLANES),
                    "description": "Optional stack-agnostic architectural plane.",
                },
                "scope": {"type": "string", "description": "Optional feature or bounded context."},
                "traits": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional semantic cross-cutting tags (e.g. ['pii']).",
                },
                "environment": {
                    "type": "string",
                    "enum": ["dev", "tst", "pre", "pro"],
                    "description": "Optional target environment ('dev', 'tst', 'pre', 'pro').",
                },
                "resolution_override": {
                    "type": "string",
                    "enum": ["L0", "L1", "L2"],
                    "description": "Optional resolution override ('L0', 'L1', or 'L2').",
                },
                "resonance_key": {"type": "string", "description": "Optional rcap1 secret key."},
                "include_capsules": {
                    "type": "boolean",
                    "default": True,
                    "description": "Whether to attach rcap1 capsule_token envelopes.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "orchestrate_ephemeral_fork",
        "description": "Spawn, inspect, evaluate, or reap TTL-bounded ephemeral Department Bots.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": list(VALID_EPHEMERAL_ACTIONS),
                    "default": "evaluate",
                    "description": "Lifecycle action ('spawn', 'inspect', 'evaluate', or 'reap').",
                },
                "fork_id": {
                    "type": "string",
                    "description": "Existing fork_id (or 'all' for reap).",
                },
                "bot_role": {
                    "type": "string",
                    "default": "dept-specialist-bot",
                    "description": "Kebab-case role identity for the Department Bot.",
                },
                "target_path": {
                    "type": "string",
                    "description": "Target surface path to evaluate.",
                },
                "target_globs": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional glob boundaries for the ephemeral fork.",
                },
                "architectural_planes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional architectural planes for the ephemeral fork.",
                },
                "mount_templates": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional subset of template packs to activate.",
                },
                "mount_layers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional subset of mounted layers/* to link.",
                },
                "mount_project_rules_from": {
                    "type": "string",
                    "description": "Optional project directory to bridge .agents/rules/*.md from.",
                },
                "model_tier": {
                    "type": "string",
                    "enum": list(VALID_AGENT_TIERS),
                    "default": "flash",
                    "description": "Target subagent model tier ('flash', 'inherit', 'pro').",
                },
                "access_mode": {
                    "type": "string",
                    "enum": list(VALID_EPHEMERAL_ACCESS_MODES),
                    "default": "strictly-read-only",
                    "description": "Capability boundary for the ephemeral Department Bot.",
                },
                "resolution": {
                    "type": "string",
                    "enum": ["L0", "L1", "L2"],
                    "default": "L2",
                    "description": "Context resolution depth for the Department Bot.",
                },
                "ttl_seconds": {
                    "type": "integer",
                    "default": 300,
                    "description": "Time-to-live in seconds (10..3600).",
                },
                "one_shot": {
                    "type": "boolean",
                    "default": True,
                    "description": "Whether action='evaluate' auto-reaps its ephemeral fork.",
                },
            },
            "additionalProperties": False,
        },
    },
)

MCP_PROMPTS_CATALOG: tuple[dict[str, Any], ...] = (
    {
        "name": "orient-on-layer",
        "description": "Orient an AI agent on this layer using a 4-Channel Executive Digest.",
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
        "description": "Audit live package, symlink, and repository drift on this node.",
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
        "description": "Discover federated MCP servers and load inherited effective_guardrails.",
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
