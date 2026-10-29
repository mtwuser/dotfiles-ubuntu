"""Declarative JSON-RPC catalogs for MCP resources, tools, and prompts.

Specification: docs/architecture/03_contextual_mcp_and_federation.md
"""

from __future__ import annotations

from typing import Any

from dotfiles_mcp.constants import VALID_ARCHITECTURAL_PLANES

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
                    "description": "Target layer ('root' or a mounted subtree in layers/*).",
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
                        "'docs/architecture/01_system_and_stow_engine.md'."
                    ),
                },
                "layer": {
                    "type": "string",
                    "description": "Optional layer ('root' or a mounted subtree in layers/*).",
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
                    "description": "Keyword or phrase to search (e.g., 'testing', 'migrations').",
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
                    "description": "'all', 'root', or a specific mounted subtree name.",
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
                "resonance_key": {
                    "type": "string",
                    "description": "Optional secret key to seal rcap1 context capsules.",
                },
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
                        "Chained context capsule token ('rcap1.<header>.<payload>.<sig>')."
                    ),
                },
                "target_level": {
                    "type": "string",
                    "enum": ["L0", "L1", "L2", "L3"],
                    "description": "Target unfolding depth ('L0', 'L1', 'L2', or 'L3').",
                },
                "agent_tier": {
                    "type": "string",
                    "enum": ["flash", "inherit", "pro"],
                    "default": "inherit",
                    "description": (
                        "Calling agent tier per AGENTS.md §13 ('flash', 'inherit', 'pro')."
                    ),
                },
                "environment": {
                    "type": "string",
                    "enum": ["dev", "tst", "pre", "pro"],
                    "description": "Optional target environment ('dev', 'tst', 'pre', or 'pro').",
                },
                "resonance_key": {
                    "type": "string",
                    "description": "Optional secret key to unlock key-gated capsules.",
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
                    "description": "Optional role substring filter (e.g. 'database').",
                },
                "environment": {
                    "type": "string",
                    "enum": ["dev", "tst", "pre", "pro"],
                    "description": "Optional environment filter ('dev', 'tst', 'pre', or 'pro').",
                },
                "layer": {
                    "type": "string",
                    "default": "all",
                    "description": "'all', 'root', or a specific mounted subtree name/layer_id.",
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
                    "description": "Target layer ('all', 'root', or a mounted subtree).",
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
                    "description": "Optional relative file path in the target project.",
                },
                "architectural_plane": {
                    "type": "string",
                    "enum": list(VALID_ARCHITECTURAL_PLANES),
                    "description": "Optional stack-agnostic architectural plane.",
                },
                "scope": {
                    "type": "string",
                    "description": "Optional feature module, domain slice, or bounded context.",
                },
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
