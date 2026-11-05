"""Declarative JSON-RPC catalogs for MCP resources, tools, and prompts.

Specification: docs/architecture/03_contextual_mcp_and_federation.md
"""

from __future__ import annotations

from typing import Any

from dotfiles_mcp.core.constants import (
    VALID_AGENT_TIERS,
    VALID_ARCHITECTURAL_PLANES,
    VALID_EPHEMERAL_ACCESS_MODES,
    VALID_EPHEMERAL_ACTIONS,
    VALID_EPHEMERAL_SCOPES,
    VALID_EPISTEMIC_GRADES,
    VALID_GRCC_OPERATIONS,
    VALID_ROSTER_ROLES,
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
        "name": "Pillar A Global Engineering Rules (AGENTS.md)",
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
        "name": "Pillar B Stack Starter Templates",
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

_WS_DIR_PROP: dict[str, str] = {
    "type": "string",
    "description": "Optional target workspace directory (defaults to server repo_dir).",
}
_BRANCH_REF_PROP: dict[str, str] = {
    "type": "string",
    "description": "Optional Git branch/ref for zero-checkout DMCP projection.",
}
_ENV_PROP: dict[str, Any] = {
    "type": "string",
    "enum": ["dev", "tst", "pre", "pro"],
    "description": "Optional target environment ('dev', 'tst', 'pre', or 'pro').",
}
_LAYER_ALL_PROP: dict[str, str] = {
    "type": "string",
    "default": "all",
    "description": "Target layer filter.",
}
_INCLUDE_CAPSULES_PROP: dict[str, Any] = {
    "type": "boolean",
    "default": True,
    "description": "Whether to mint and attach rcap1 capsule_token envelopes.",
}
_RES_KEY_PROP: dict[str, str] = {
    "type": "string",
    "description": "Optional rcap1 session resonance key.",
}

MCP_TOOLS_CATALOG: tuple[dict[str, Any], ...] = (
    {
        "name": "get_layer_overview",
        "description": "Return a 4-Channel Executive Digest of this node or a layers/* subtree.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace_dir": _WS_DIR_PROP,
                "layer": {"type": "string", "description": "Target layer ('root' or subtree)."},
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
                "workspace_dir": _WS_DIR_PROP,
                "mode": {
                    "type": "string",
                    "enum": ["verify-repo", "system-audit", "both"],
                    "default": "verify-repo",
                    "description": "Audit mode ('verify-repo', 'system-audit', or 'both').",
                },
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
                "workspace_dir": _WS_DIR_PROP,
                "relative_path": {"type": "string", "description": "Path relative to layer root."},
                "layer": {"type": "string", "description": "Optional layer ('root' or subtree)."},
                "branch_ref": _BRANCH_REF_PROP,
            },
            "required": ["relative_path"],
            "additionalProperties": False,
        },
    },
    {
        "name": "query_governance_rules",
        "description": "Search Pillar A rules, templates, and docs with L0/L1/L2 rcap1 compaction.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace_dir": _WS_DIR_PROP,
                "query": {"type": "string", "description": "Keyword or phrase to search."},
                "scope": {
                    "type": "string",
                    "enum": ["all", "global", "templates", "docs"],
                    "default": "all",
                    "description": "Subset of layer documentation to search.",
                },
                "layer": _LAYER_ALL_PROP,
                "resolution": {
                    "type": "string",
                    "enum": ["L0", "L1", "L2"],
                    "default": "L2",
                    "description": "Compaction depth ('L0', 'L1', or 'L2'; default 'L2').",
                },
                "environment": _ENV_PROP,
                "resonance_key": _RES_KEY_PROP,
                "target_path": {"type": "string", "description": "Optional prioritized file path."},
                "branch_ref": _BRANCH_REF_PROP,
                "min_epistemic_grade": {
                    "type": "string",
                    "enum": list(VALID_EPISTEMIC_GRADES),
                    "description": "Optional minimum epistemic grade filter (E3, E2, E1, or E0).",
                },
                "include_capsules": _INCLUDE_CAPSULES_PROP,
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
                "workspace_dir": _WS_DIR_PROP,
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
                    "description": "Calling agent tier per AGENTS.md §12 (flash, inherit, pro).",
                },
                "environment": _ENV_PROP,
                "resonance_key": _RES_KEY_PROP,
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
                "workspace_dir": _WS_DIR_PROP,
                "filter_role": {"type": "string", "description": "Optional role substring filter."},
                "environment": _ENV_PROP,
                "layer": _LAYER_ALL_PROP,
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
                "workspace_dir": _WS_DIR_PROP,
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
                "layer": _LAYER_ALL_PROP,
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
                "workspace_dir": _WS_DIR_PROP,
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
                "environment": _ENV_PROP,
                "resolution_override": {
                    "type": "string",
                    "enum": ["L0", "L1", "L2"],
                    "description": "Optional resolution override ('L0', 'L1', or 'L2').",
                },
                "resonance_key": _RES_KEY_PROP,
                "include_capsules": _INCLUDE_CAPSULES_PROP,
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
                "workspace_dir": _WS_DIR_PROP,
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
                "ephemeral_scope": {
                    "type": "string",
                    "enum": list(VALID_EPHEMERAL_SCOPES),
                    "description": "Collaboration scope ('inter-layer' or 'intra-layer').",
                },
                "actor_role": {
                    "type": "string",
                    "enum": list(VALID_ROSTER_ROLES),
                    "default": "member",
                    "description": "Participant role spawning the bot ('owner'..'member').",
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
                "branch_ref": _BRANCH_REF_PROP,
                "task_step_id": {
                    "type": "string",
                    "description": "Decision-tree step ID for DMCP/GRCC chaining.",
                },
                "context_frame_token": {
                    "type": "string",
                    "description": "Incoming rcap1 DMCP context_frame_token to verify/chain.",
                },
                "grcc_op": {
                    "type": "string",
                    "enum": list(VALID_GRCC_OPERATIONS),
                    "description": "GRCC operation ('probe', 'seal', 'unfold', or 'prune').",
                },
                "capsule_token": {
                    "type": "string",
                    "description": "Sealed rcap1 capsule token for verify-return or GRCC seal.",
                },
                "digest": {
                    "type": "object",
                    "description": "4-Channel Executive Digest for action='seal-return'.",
                },
                "environment": {
                    "type": "string",
                    "description": "Optional environment filter ('dev', 'tst', 'pre', 'pro').",
                },
                "family": {
                    "type": "string",
                    "description": "Optional bot archetype family filter for action='catalog'.",
                },
                "resonance_key": {
                    "type": "string",
                    "description": "Optional rcap1 session resonance key for DMCP/GRCC.",
                },
                "remote": {
                    "type": "string",
                    "description": "Optional Git remote name/URL for GRCC ls-remote probe.",
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
