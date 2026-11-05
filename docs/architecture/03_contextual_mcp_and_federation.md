# Architecture 03: Contextual Layer & System MCP Server (`dotfiles-mcp`)

> **Normative Specification — Subsystem 3 ([`scripts/dotfiles_mcp_server.py`](../../scripts/dotfiles_mcp_server.py), `scripts/dotfiles_mcp/`, & [`system/mcp-layer.json`](../../system/mcp-layer.json))**
>
> This document defines the technical specification, protocol contracts (`Resources`, `Tools`, `Prompts`), security invariants, and federation schema for operating any `dotfiles-ubuntu` instance or fork as a **Model Context Protocol (MCP) Server** representing a specific governance layer, container, server, or application node.

---

## 1. Architectural Purpose: Bridging the Physical Boundary of GNU Stow

In `dotfiles-ubuntu`, Subsystem 1 ([`01_system_and_stow_engine.md`](01_system_and_stow_engine.md)) and Subsystem 2 ([`02_antigravity_governance_and_hooks.md`](02_antigravity_governance_and_hooks.md)) solve configuration and AI governance within a **single local filesystem (`$HOME`)** via GNU Stow symlinks and lifecycle hooks.

However, modern software systems frequently span boundaries that POSIX filesystem symlinks cannot cross:
- **Containerized Runtime Topologies**: Docker containers, Devcontainers, Kubernetes pods, or sidecar services where each container has its own isolated packages and runtime state.
- **Distributed Server & Node Architectures**: Multi-server staging/production nodes, data processing workers, or specialized GPU/ML hosts.
- **Multi-Level Organizational Forks**: Separate Git forks for Corporate Governance (`Level 1 Root 0` / `Pillar A`), Department & Squad Architecture (`Level 2..3` / `Pillar B`), and Service Nodes (`Axis 2 runtime-node` / `Pillar C`) that are not simultaneously symlinked to `$HOME`.

By embedding an **optional, zero-dependency, read-only MCP server** (`scripts/dotfiles_mcp_server.py`) inside `dotfiles-ubuntu`, every fork, container, or server hosting the repository can expose its **system manifests, drift status, active governance rules, navigable `docs/`, and downstream MCP topology** over standard JSON-RPC 2.0.

### 1.1. The Dual-Plane Architecture (Stow Local Plane vs. MCP Distributed Plane)

Plane 1 (`GNU Stow + Lifecycle Hooks`) enforces zero-latency local guards in `$HOME`, while Plane 2 (`dotfiles-mcp` over JSON-RPC 2.0) provides on-demand multi-layer and cross-container introspection:

```mermaid
flowchart TD
    subgraph LocalPlane["Plane 1: Intra-Node Local Plane (GNU Stow + Hooks)"]
        direction TB
        STOW["GNU Stow Symlinks\n(~/.gemini/config/)"]
        AGENTS["Inline AGENTS.md\n(0ms Latency Push)"]
        HOOKS["PreToolUse / PostToolUse / Stop\n(Deterministic Execution Guards)"]
        STOW --> AGENTS
        STOW --> HOOKS
    end

    subgraph DistributedPlane["Plane 2: Inter-Node & Multi-Layer Plane (MCP Protocol)"]
        direction TB
        MCP_CORP["Corporate / Squad Fork MCP\n(Governance & Stack Blueprints)"]
        MCP_CONT["Container / Service Node MCP\n(docker exec -i stdio)"]
        MCP_SSH["Remote Server Node MCP\n(ssh stdio)"]
    end

    IDE["🤖 AI Agent / IDE Host\n(Antigravity · VS Code Copilot · Cursor · Claude)"]

    LocalPlane ==>|"Governs Local Host Loop\n(Always Active)"| IDE
    IDE <-->|"Introspects & Orchestrates Across Boundaries\n(JSON-RPC 2.0 over stdio / docker / ssh)"| DistributedPlane
```

| Architectural Dimension | Plane 1: Local Host (GNU Stow + Lifecycle Hooks) | Plane 2: Distributed / Multi-Layer (`dotfiles-mcp`) |
|-------------------------|--------------------------------------------------|-----------------------------------------------------|
| **Transport Mechanism** | Local POSIX symlinks (`stow -t ~`) + `stdin`/`stdout` hooks | Model Context Protocol (JSON-RPC 2.0 over `stdio`, `docker run -i --rm`, `docker exec -i`, or `ssh`) |
| **Control Flow** | **Deterministic Push / Intercept** (mandatory on every turn/tool call) | **Contextual Pull / Introspection** (queried on demand by the agent) |
| **Primary Responsibility** | Enforce coding rules, block dangerous commands (`pre_tool_guard.py`), auto-format, and run unit tests locally | Expose container/server drift, resolve cross-layer rules & `docs/`, and federate downstream MCP servers across services |
| **Dependency Footprint** | GNU Stow + Bash + Python 3.14 stdlib | Python 3.14 stdlib only (**zero external pip packages** across workstations, containers, CI, and Ubuntu 26.04 LTS) |

---

## 2. Non-Negotiable Design Boundaries & Security Invariants

To preserve the simplicity, security, and reliability of `dotfiles-ubuntu`, the MCP server implementation MUST obey five strict architectural constraints:

1. **100% Optional & Zero-Impact on Traditional Dotfiles Usage**:
   - Users who only use `bootstrap.sh`, `backup.sh`, and `audit.sh` never need to configure or run the MCP server. Nothing runs as a background daemon unless explicitly invoked by an MCP client over `stdio`.
2. **Zero External Dependencies & 4-Subpackage Bounded-Domain Architecture (Pure Python 3.14 Standard Library)**:
   - `scripts/dotfiles_mcp_server.py` (thin CLI entrypoint) and the 24-module package `scripts/dotfiles_mcp/` organized into **4 Bounded-Domain Subpackages** (`core/`: `constants.py`, `catalogs.py`, `manifest_helpers.py`, `layer_topology_helpers.py`; `capsules/`: `capsule_engine.py`, `surface_weaver.py`, `tools_compaction.py`, `tools_unfold.py`, `tools_surface.py`; `mcp_node/`: `node_base.py`, `capability_registry.py`, `resources.py`, `tools_federation.py`, `ephemeral_fork_engine.py`, `tools_ephemeral.py`, `server.py`; `governance/`: `fork_configurator.py`, `workspace_bootstrapper.py`, `promotion_engine.py`, `horizon_engine.py`, `authority_engine.py`, `workflow_engine.py`, `git_governance_engine.py`, `cli_dispatcher.py` — every file `< 465` lines with `0-byte` `__init__.py` markers and a strict **4-Subpackage Dependency DAG** `core <- capsules <- mcp_node <- governance`) MUST use only the Python 3.14 standard library (`json`, `sys`, `os`, `pathlib`, `subprocess`, `re`, `platform`, `argparse`, `zlib`, `hashlib`, `hmac`, `base64`, `shutil`, `time`, `secrets`, `stat`, `difflib`) with `from __future__ import annotations`. It must never require `pip install mcp`, `fastapi`, or a virtual environment, ensuring it runs out of the box on any Ubuntu 26.04 LTS workstation, container, CI runner, or server.
3. **Strictly Read-Only & Deterministic Execution (No Arbitrary Shell)**:
   - In accordance with [`SECURITY.md`](../../SECURITY.md), the MCP server MUST NEVER expose a generic `run_command` or `exec_shell` tool, nor any tool that modifies files, installs packages, or alters Git state.
   - The only subprocesses it may spawn are deterministic, read-only repository scripts (`./audit.sh` without `--clean`, and `./scripts/verify-repo.sh`) with fixed argument lists (`shell=False`) and strict timeouts.
4. **Strict Path Containment & Secret Exclusion**:
   - File-reading tools and resources MUST resolve paths via `Path.resolve()` and verify they reside strictly inside the `dotfiles-ubuntu` repository root (`REPO_DIR`).
   - Machine-local secret overrides (`~/.bashrc.local`, `~/.gitconfig.local`, `.env`, `~/.gemini/*.json`) and directories outside `REPO_DIR` are structurally unreachable.
5. **Complementary to Local `AGENTS.md` (Never a Replacement)**:
   - On the developer's local workstation, `AGENTS.md` and `hooks.json` remain symlinked via GNU Stow so `PreToolUse` guards cannot be bypassed. The MCP server is used for programmatic introspection, multi-fork layer resolution, and cross-container / cross-server diagnostics.

### 2.1. `1:1:1` Source $\leftrightarrow$ Unit Test $\leftrightarrow$ Specification Traceability Matrix (Core Protocol & Federation)

Every module in the `dotfiles-mcp` CLI entrypoint, `core/`, and `mcp_node/` subpackages maintains a strict `1:1:1` alignment with its isolated unit test suite (`100.00%` branch coverage, `< 465` lines) and its bidirectional specification pointer:

| Subpackage & Subsystem | Normative Spec & Primary Responsibility | Source Module (`scripts/dotfiles_mcp/`) | `1:1` Unit Test (`tests/unit/dotfiles_mcp/`) |
|---|---|---|---|
| **CLI Entrypoint & Self-Test** | **Arch 03 §7**: CLI flags (`--self-test`, `--layer-id`, `--layer-role`, `--log-dir`, `--no-log`), `run_self_test`, `main` | [`scripts/dotfiles_mcp_server.py`](../../scripts/dotfiles_mcp_server.py) | [`tests/unit/test_dotfiles_mcp_server.py`](../../tests/unit/test_dotfiles_mcp_server.py) (`TestDotfilesMCPServerCLI`) |
| **`core/` — Declarative Constants & Catalogs** | **Arch 03 §3–§4, Arch 04 §§2.7–2.8 & Arch 05 §5**: `MCP_JSONRPC_PROTOCOL_REV`, `LAYER_MANIFEST_CONTRACT_REV`, `VALID_LAYER_ROLES`, `VALID_TEMPLATE_KINDS`, `VALID_EPISTEMIC_GRADES`, `CAPSULE_ABSTRACTION_LAYERS`, `VALID_LIBRARY_PREFIXES`, `LIBRARY_DOMAIN_TAXONOMY`, `CANONICAL_SCIENCE_TRUNKS`, `CITATION_LIFECYCLE_QUADRANTS`, `MCP_PERMISSION_RINGS`, `BOT_ARCHETYPE_CATALOG`, `MCP_RESOURCES_CATALOG`, `MCP_TOOLS_CATALOG`, `MCP_PROMPTS_CATALOG` | [`core/constants.py`](../../scripts/dotfiles_mcp/core/constants.py), [`core/catalogs.py`](../../scripts/dotfiles_mcp/core/catalogs.py) | *(Declarative constants verified via `1:1` consumer tests & `verify-repo.sh`)* |
| **`core/` — Manifest & System Helpers** | **Arch 03 §3.1, Arch 04 §2.8 & Arch 06 §2**: `_read_version`, `_read_os_pretty_name`, `_is_running_in_container`, `_parse_skill_frontmatter`, `_sha256_file`, `_load_manifest_dict`, `_is_oss_root_manifest`, `discover_layer_template_names`, `discover_templates_catalog`, `_resolve_science_trunk`, `classify_library_domain`, `resolve_library_mount_endpoints`, `_resolve_template_dest_dir`, `_has_stale_schema`, `_stamp_schema_rev` | [`core/manifest_helpers.py`](../../scripts/dotfiles_mcp/core/manifest_helpers.py) | [`core/test_manifest_helpers.py`](../../tests/unit/dotfiles_mcp/core/test_manifest_helpers.py) (`TestManifestHelpers`) |
| **`core/` — Layer Topology, Subtree Sync & Onboarding Renderers** | **Arch 03 §4 & Arch 06 §§2–3**: `_resolve_layer_entity_identity`, `_classify_inter_layer_relationship`, `_match_manifest_actor_role`, `_resolve_hierarchical_actor_profile`, `_is_git_historical_blob`, `_is_dest_template_newer`, `_resolve_default_parent_dir`, `_resolve_mounted_child_dir`, `_is_makefile_outdated`, `_render_layer_makefile`, `_inspect_mounted_children_drifts`, `_sync_mounted_children_into_parent`, `_render_layer_onboarding_readme`, `_render_lineage_markdown` | [`core/layer_topology_helpers.py`](../../scripts/dotfiles_mcp/core/layer_topology_helpers.py) | [`core/test_layer_topology_helpers.py`](../../tests/unit/dotfiles_mcp/core/test_layer_topology_helpers.py) (`TestLayerTopologyHelpers`) |
| **`mcp_node/` — Node Security, Manifests & Warnings** | **Arch 03 §2, §4, §6**: `MCPNodeBase`, `_load_layer_manifest`, `_discover_mounted_layers`, `_resolve_workspace_override`, `_resolve_safe_path`, `_read_git_branch_document`, `_list_git_branch_markdown_files`, `_emit_warning` | [`mcp_node/node_base.py`](../../scripts/dotfiles_mcp/mcp_node/node_base.py) | [`mcp_node/test_node_base.py`](../../tests/unit/dotfiles_mcp/mcp_node/test_node_base.py) (`TestMCPNodeBase`) |
| **`mcp_node/` — MCP Resources & Telemetry** | **Arch 03 §3.1, §6.3**: `ResourcesMixin`, `list_resources`, `read_resource` (`9` URIs including live `capability_profile` in `dotfiles://mcp/topology`), `_read_diagnostics_resource` | [`mcp_node/resources.py`](../../scripts/dotfiles_mcp/mcp_node/resources.py) | [`mcp_node/test_resources.py`](../../tests/unit/dotfiles_mcp/mcp_node/test_resources.py) (`TestResourcesMixin`) |
| **`mcp_node/` — Node Audit & Federation Tools** | **Arch 03 §3.2, §5, §6.1**: `FederationToolsMixin` (`get_layer_overview` with OOP rings, symbiosis state & `deep_context_index`, `_discover_deep_context_index`, `audit_node_drift`, `read_layer_document`, `discover_federated_mcps`, `compare_layer_patterns`) | [`mcp_node/tools_federation.py`](../../scripts/dotfiles_mcp/mcp_node/tools_federation.py) | [`mcp_node/test_tools_federation.py`](../../tests/unit/dotfiles_mcp/mcp_node/test_tools_federation.py) (`TestFederationToolsMixin`) |
| **`mcp_node/` — JSON-RPC 2.0 Dispatcher & `stdio` Loop** | **Arch 03 §3, §6.3**: `DotfilesMCPServer`, `handle_request`, `run_stdio_loop` (`Content-Length` & newline framing) | [`mcp_node/server.py`](../../scripts/dotfiles_mcp/mcp_node/server.py) | [`mcp_node/test_server.py`](../../tests/unit/dotfiles_mcp/mcp_node/test_server.py) (`TestDotfilesMCPServer`) |
| **`capsules/` — Compaction (`rcap1`) & Surface (`0..N`) Weaver** | **See [`04_compaction_surface_and_promotion_engines.md`](04_compaction_surface_and_promotion_engines.md) §§1–4** | `capsules/{capsule_engine,surface_weaver,tools_compaction,tools_unfold,tools_surface}.py` | `capsules/test_*.py` (`5` `1:1` isolated test modules) |
| **`mcp_node/` — OOP Capability Rings, Ephemeral Scoped Forks & Symbiotic Bots** | **See [`05_ephemeral_forks_and_department_bots.md`](05_ephemeral_forks_and_department_bots.md) §§1–5** | `mcp_node/{capability_registry,ephemeral_fork_engine,tools_ephemeral}.py` | `mcp_node/test_{capability_registry,ephemeral_fork_engine,tools_ephemeral}.py` |
| **`governance/` — Inter-Layer Lifecycle, 1-Hop Horizon, RBAC Authority & Promotion** | **See [`06_layer_governance_and_promotion_engines.md`](06_layer_governance_and_promotion_engines.md) §§1–5** | `governance/{fork_configurator,workspace_bootstrapper,promotion_engine,horizon_engine,authority_engine,workflow_engine,git_governance_engine,cli_dispatcher}.py` | `governance/test_*.py` (`8` `1:1` isolated test modules) |

---

## 3. MCP Protocol Contract (`scripts/dotfiles_mcp_server.py`)

The server implements the Model Context Protocol (`protocolVersion: "2024-11-05"` / backward-compatible JSON-RPC 2.0 over newline-delimited `stdio` or `Content-Length` framed streams) and declares three capability groups: `resources`, `tools`, and `prompts`.

### 3.1. MCP Resources (`resources/list` & `resources/read`)

Each `dotfiles-ubuntu` instance exposes nine canonical URI resources representing its identity, system manifests, governance rules, documentation graph, federated MCP topology, and live runtime diagnostics:

| Resource URI | Returned Payload Description | MIME Type | Source Files in Repository |
|--------------|------------------------------|-----------|----------------------------|
| `dotfiles://layer/identity` | Node & layer identity: SemVer `version`, `layer_id`, `layer_role` (`corporate`, `domain-policy`, `department`, `squad`, `service-node`, `environment-cluster`, `workstation`, `ephemeral-bot`), `entity_kind`, `governing_root_id`, `topological_class`, `hostname`, `in_container` (boolean), `os_pretty_name`, `git_commit`, and `upstream_layer`. | `application/json` | `VERSION`, `system/mcp-layer.json`, `/etc/os-release`, `/.dockerenv`, `git rev-parse` / `DOTFILES_GIT_COMMIT` |
| `dotfiles://system/manifests` | Structured JSON dictionary containing counts and package lists for every declarative manifest tracked by this node/container. | `application/json` | `system/*.txt` (`packages-manual`, `snaps`, `npm-globals`, `nvm-default`, `external`, `gnome-extensions`) |
| `dotfiles://governance/rules` | The complete `Pillar A` universal behavioral and engineering rules active in this repository fork. | `text/markdown` | `antigravity/.gemini/config/AGENTS.md` |
| `dotfiles://governance/hooks` | Lifecycle hook configuration (`PreToolUse`, `PostToolUse`, `PostInvocation`, `Stop`) active in this layer. | `application/json` | `antigravity/.gemini/config/hooks.json` |
| `dotfiles://governance/skills` | Catalog of all global skills in this layer, extracted from YAML frontmatter (`name`, `description`, `path`, `line_count`). | `application/json` | `antigravity/.gemini/config/skills/*/SKILL.md` |
| `dotfiles://governance/templates` | Inventory of `Pillar B` base and specialization-stack starter templates available in this fork, including their `rules/`, `skills/`, and `governance/` files. | `application/json` | `templates/*/` |
| `dotfiles://docs/index` | The navigable documentation index and subsystem map for this repository or layer. | `text/markdown` | `docs/README.md` |
| `dotfiles://mcp/topology` | Declarative federation manifest listing downstream or sibling MCP servers, governance guardrails, and live `capability_profile` (`resolve_mcp_capability_profile` — `granted_rings`, `symbiotic_state`, `active_ephemeral_leases`, `bot_archetype_families`). | `application/json` | `system/mcp-layer.json`, `logs/ephemeral_forks/*` |
| `dotfiles://mcp/diagnostics` | Live telemetry summary of recent MCP JSON-RPC calls (`total_events`, `error_events`, `max_response_bytes`, `recent_events`) and structured runtime warnings/alerts (`total_alerts`, `by_code`, `recent_alerts`). | `application/json` | `logs/mcp_events.jsonl`, `logs/mcp_alerts.jsonl` |

### 3.2. MCP Tools (`tools/list` & `tools/call`)

The server exposes nine read-only, deterministic tools for live node auditing, multi-resolution resonant rule compaction/unfolding, stack-agnostic multi-layer surface projection (`0..N` layers), ephemeral Department Bot orchestration, targeted documentation retrieval, and multi-MCP orchestration. Every tool accepts an optional `workspace_dir` string parameter (validated via `_resolve_workspace_override` in `node_base.py`) so a single fixed `dotfiles-mcp` instance registered in `~/.gemini/config/mcp_config.json` can dynamically inspect any layer or project repository on the workstation:

| Tool Name | Input Arguments (`inputSchema`) | Execution Logic & Security Gate | Output Summary |
|---|---|---|---|
| **`get_layer_overview`** | `workspace_dir`: optional string, `layer`: optional string (`"root"` or a mounted subtree name/`layer_id` in `layers/*`) | Returns a compact **4-Channel Executive Digest** of the target layer: (1) Node & System State, (2) Governance & Stack Contracts, (3) Active Invariants, Token-Budget Utilization, Context Compaction Protocol (`rcap1`), & Warnings, and (4) Navigable Docs, Mounted `layers/*` Subtrees, Supported Environments (`dev`, `tst`, `pre`, `pro`), Federated MCPs, OOP Capability Inheritance (`granted_rings`), Permanent $\leftrightarrow$ Ephemeral Symbiosis (`symbiotic_state`, `active_ephemeral_leases`), & **`deep_context_index`** (`specialty_branches`, `grcc_capsule_refs`, `mounted_subtrees_count`, `epistemic_grades`, `abstraction_gradient`). | JSON digest (`< 2 KB`) giving an agent immediate situational awareness and $O(1)$ deep-context discovery. |
| **`audit_node_drift`** | `workspace_dir`: optional string, `mode`: `"verify-repo"` \| `"system-audit"` \| `"both"` (default `"verify-repo"`) | Executes `./scripts/verify-repo.sh` (or `layer-config.sh diff-project <workspace_dir>` when inspecting a child layer/project without `verify-repo.sh`) and/or `./audit.sh` in read-only mode via `subprocess.run(..., shell=False, timeout=30)` with `NO_COLOR=1`. Never runs `--clean`. | JSON report with `healthy` (boolean), `exit_code`, and clean text output showing any symlink, package, or metadata drift on that container/server. |
| **`read_layer_document`** | `workspace_dir`: optional string, `relative_path`: string, `layer`: optional string (`"root"` or a mounted subtree in `layers/*`), `branch_ref`: optional string | Resolves `(target_layer_dir / relative_path).resolve()` (or reads `<branch_ref>:<relative_path>` via stateless `git show` with zero `HEAD` checkout when `branch_ref` is provided), verifies `target.is_relative_to(target_layer_dir)`, and enforces an allowlist of readable directories (`docs/`, `templates/`, `antigravity/`, `system/`, `corporate/`, `surfaces/`, `roadmaps/`, and root documentation/tracker `.md` files). | Full Markdown or text content of the requested specification. |
| **`query_governance_rules`** | `workspace_dir`: optional string, `query`: string, `scope`: `"all"` \| `"global"` \| `"templates"` \| `"docs"`, `layer`: `"all"` \| `"root"` \| `<subtree>` (default `"all"`), `resolution`: `"L0"` \| `"L1"` \| `"L2"` (default `"L2"`), `min_epistemic_grade`: optional `"E3"` \| `"E2"` \| `"E1"` \| `"E0"`, `environment`: optional `"dev"` \| `"tst"` \| `"pre"` \| `"pro"`, `branch_ref`: optional string, `resonance_key`: optional string, `include_capsules`: optional boolean | Case-insensitive section-aware search across `AGENTS.md`, `templates/*/rules/*.md`, and `docs/**/*.md` across the root layer and/or all mounted `git subtree` layers (`layers/*/`), supporting zero-checkout `branch_ref` projection (`dmcp_projection`), multi-resolution compaction (`L0` Promoter Codons, `L1` Axiom Skeletons, `L2` Full Sections), automatic epistemic credibility inference (`E3..E0`), priority sorting (`E3 -> E0`), `min_epistemic_grade` filtering, `l3_targets` deep-wiki substrate beacons in `promoter_codon`, and chained `rcap1` context capsules. | Matching rule sections ordered by epistemic grade (`E3..E0`) with `promoter_codon` (`epistemic_grade`, `l3_targets`), `capsule_token` (`rcap1...`), `dmcp_projection`, and `token_compaction_metrics`. |
| **`unfold_context_capsule`** | `workspace_dir`: optional string, `capsule_token`: string (`"rcap1.<header>.<payload>.<sig>"`), `target_level`: optional `"L0"` \| `"L1"` \| `"L2"` \| `"L3"`, `agent_tier`: `"flash"` \| `"inherit"` \| `"pro"` (default `"inherit"`), `environment`: optional `"dev"` \| `"tst"` \| `"pre"` \| `"pro"`, `resonance_key`: optional string | Verifies the surface `promoter_codon` capsule envelope & HMAC-SHA256 chain link (including parent unfolding of active ephemeral fork capsules `iss="eph-..."`), enforces agent capability (`flash` capped at `L1`) and environment clearance, and progressively decrypts (`SHA-256 CTR`) and decompresses (`zlib`) the capsule interior (`L0 → L1 → L2 → L3`). | Unfolded level content (`L1` skeleton, `L2` full section, or `L3` linked skills/specs + guardrails), `promoter_codon`, and `next_capsule_token`. |
| **`discover_federated_mcps`** | `workspace_dir`: optional string, `filter_role`: optional string, `environment`: optional `"dev"` \| `"tst"` \| `"pre"` \| `"pro"`, `layer`: `"all"` \| `"root"` \| `<subtree>` (default `"all"`) | Aggregates registered downstream/sibling MCP servers from `system/mcp-layer.json` across the root layer and mounted `layers/*/` subtrees, filtered by `role`, `layer`, and target `environment`, attaching the active environment's `access_mode`, `requirements_file`, and `default_guardrails`. | JSON list of federated MCP descriptors, mounted subtrees, and environment safety rules. |
| **`compare_layer_patterns`** | `workspace_dir`: optional string, `project_rules`: array of strings, `project_skills`: array of strings, `layer`: optional string (`"all"` \| `"root"` \| `<subtree>`, default `"all"`) | Compares a consumer project's rule/skill inventory across `1..N` layers (`Root` + mounted `layers/*` + `templates/*`), filters out materialized `layer-<NN>-<name>.md` files into `materialized_layer_rules`, and generates deterministic `promotion_routing` recommendations (`target_layer`, `target_role`, `target_destination`, `subtree_push_command`, `root_agents_md_headroom_bytes`). | JSON classification (`compared_against_layer`, `layers_scanned`, `materialized_layer_rules`, `already_in_layer_a_skills`, `already_in_layer_b_templates`, `candidates_for_upward_promotion`, `promotion_routing`). |
| **`resolve_surface_governance`** | `workspace_dir`: optional string, `target_path`: optional string, `architectural_plane`: optional `"schema"` \| `"domain"` \| `"application"` \| `"presentation"` \| `"infrastructure"` \| `"testing"`, `scope`: optional string, `traits`: optional array of strings, `environment`: optional `"dev"` \| `"tst"` \| `"pre"` \| `"pro"`, `resolution_override`: optional `"L0"` \| `"L1"` \| `"L2"`, `resonance_key`: optional string, `include_capsules`: optional boolean | Projects and weaves effective governance bindings (`manifest["surface_bindings"]` merged and deduplicated by `binding_id` with `recommended_surface_bindings` from active `templates/<name>/template.json` packs via `collect_layer_effective_bindings`) across `0..N` layers (`Root` + arbitrary mounted `layers/*` subtrees) for a target application surface. Automatically infers `effective_plane` and `effective_scope` from `target_path`, prunes non-intersecting layers (`0` token cost), orders matching bindings by numeric `precedence` (`0..100`, *Lex Superior*), and applies adaptive `rcap1` compaction (`L2` for `authoritative` bindings, `L1` for `transversal` bindings). | Ordered `participating_layers`, `pruned_layers`, `resolved_bindings` (with `rcap1` capsules), merged `effective_invariants`, `canonical_templates`, `ephemeral_delegation_advisories`, and `token_compaction_metrics`. |
| **`orchestrate_ephemeral_fork`** | `workspace_dir`: optional string, `action`: `"spawn"` \| `"inspect"` \| `"evaluate"` \| `"reap"` \| `"catalog"` \| `"seal-return"` \| `"verify-return"` \| `"project-branch"` \| `"chain-capsule-ref"`, `fork_id`: optional string, `bot_role`: optional string, `family`: optional string, `digest`: optional object, `capsule_token`: optional string, `branch_ref`: optional string, `task_step_id`: optional string, `context_frame_token`: optional string, `grcc_op`: optional `"probe"` \| `"seal"` \| `"unfold"` \| `"prune"`, `remote`: optional string, `target_path`: optional string, `target_globs`: optional list, `architectural_planes`: optional list, `mount_templates`: optional list, `mount_layers`: optional list, `mount_project_rules_from`: optional string, `model_tier`: `"flash"` \| `"inherit"` \| `"pro"`, `access_mode`: `"strictly-read-only"` \| `"read-and-test-trigger"` \| `"read-write-scoped"`, `resolution`: `"L0"` \| `"L1"` \| `"L2"`, `ttl_seconds`: integer (`10..3600`), `one_shot`: boolean | Materializes, inspects, evaluates, or reaps hardlink/copy-isolated, TTL-bounded ephemeral Department Bot forks (`layer_role: "ephemeral-bot"`), queries OOP capability rings & 4-family bot archetypes (`action="catalog"`), seals/verifies 4-Channel Executive Digests (`action="seal-return" \| "verify-return"`), projects zero-checkout `DMCP` branch context frames with fail-closed `master` fallback (`action="project-branch"`), and executes `GRCC` $O(1)$ capsule ref chaining under `refs/capsules/<scope-fingerprint>` (`action="chain-capsule-ref"`, see [`05_ephemeral_forks_and_department_bots.md`](05_ephemeral_forks_and_department_bots.md)). | JSON lifecycle result, `capability_profile` + `bot_archetypes`, `return_capsule` (`rcap1`), `context_frame_token` (`DMCP`), `refs/capsules/<fp>` (`GRCC`), or `subagent_invocation_brief` + `ephemeral_capsule` + `ephemeral_capsules` + `surface_projection`. |

### 3.3. MCP Prompts (`prompts/list` & `prompts/get`)

The server exposes three guided prompt templates (`orient-on-layer`, `audit-container-or-node`, `orchestrate-federated-mcps`) to standardize agent orientation and federated MCP invocation:

| Prompt Name | Arguments | Purpose |
|-------------|-----------|---------|
| **`orient-on-layer`** | `task_description` (optional) | Instructs the agent to call `get_layer_overview` and `dotfiles://docs/index` first, returning a 4-Channel Executive Digest of the target node/layer before proposing changes. |
| **`audit-container-or-node`** | `target_service` (optional) | Guides the agent through executing `audit_node_drift(mode="both")` and cross-checking `dotfiles://system/manifests` to diagnose environment discrepancies across containers or servers. |
| **`orchestrate-federated-mcps`** | `workflow_goal` (required), `environment` (optional), `layer` (optional) | Instructs the agent to call `discover_federated_mcps` (scoped by `environment` and `layer`) and `query_governance_rules` on the layer MCP **before** invoking any downstream infrastructure/database MCP server, enforcing `effective_guardrails` and `activation_policy`. |

---

## 4. Declarative Layer & MCP Federation Schema (`system/mcp-layer.json`)

To enable multi-layer and multi-service orchestration without hardcoding machine-specific topologies or organizational department names into scripts, `dotfiles-ubuntu` supports an optional, declarative manifest at **`system/mcp-layer.json`** (`schema_version: "mcp-layer-v1"`).

When a squad, department, or engineer forks `dotfiles-ubuntu` for a specific corporate layer, domain-policy module, squad archetype, or service container, they customize `system/mcp-layer.json` to describe **what this node is**, **its numeric deontic `precedence` (`0..100`)**, **its stack-agnostic `surface_bindings`**, **its environment safety profiles (`dev/tst/pre/pro`)**, and **which MCP servers belong to its context**:

```json
{
  "schema_version": "mcp-layer-v1",
  "layer_id": "dotfiles-ubuntu-default",
  "layer_role": "workstation",
  "precedence": 10,
  "description": "Declarative Ubuntu 26.04 LTS & Google Antigravity 2.0 Reference Layer (Corporate / Workstation Baseline)",
  "upstream_layer": {
    "layer_id": "mtwuser/dotfiles-ubuntu",
    "repository": "https://github.com/mtwuser/dotfiles-ubuntu.git",
    "branch": "master"
  },
  "mounted_layers_dir": "layers",
  "mounted_layers": [],
  "default_stack_templates": [
    "fastapi-hexagonal"
  ],
  "baseline_guardrails": [
    "AGENTS.md §1 (Reusability First — scan workspace before creating duplicates)",
    "AGENTS.md §4 (Atomic Deliverable & Verification Inclusion) & software-engineering.md (100% branch coverage & AAA pattern)",
    "AGENTS.md §7 (Zero-Backward Law — no legacy shims or aliases)"
  ],
  "surface_bindings": [
    {
      "binding_id": "universal-engineering-baseline",
      "target_globs": ["**"],
      "architectural_planes": ["*"],
      "scopes": ["*"],
      "traits": [],
      "mode": "transversal",
      "rule_files": [
        "antigravity/.gemini/config/AGENTS.md",
        "templates/base-stack/science-base/rules/science-base.md",
        "templates/science-stack/software-engineering/rules/software-engineering.md"
      ],
      "canonical_templates": [],
      "invariants": [
        "AGENTS.md §1 (Reusability First — scan workspace before creating duplicates)",
        "AGENTS.md §2 (Professional Robustness — strongly typed, scalable implementations, < 465 lines)",
        "AGENTS.md §7 (Zero-Backward Law — no legacy shims, aliases, or @deprecated branches)"
      ]
    }
  ],
  "environments": {
    "dev": {
      "description": "Local workstation or devcontainer development environment",
      "access_mode": "read-write-local",
      "requirements_file": "requirements-dev.txt",
      "default_guardrails": [
        "AGENTS.md §4 (Atomic Deliverable & Verification Inclusion)",
        "AGENTS.md §8 (Mandatory Pre-Commit Hygiene & Zero-Literal Exclusion Gate)"
      ]
    },
    "pre": {
      "description": "Pre-production staging and release validation environment",
      "access_mode": "strictly-read-only",
      "requirements_file": "requirements-pre.txt",
      "default_guardrails": [
        "Strictly read-only observability, schema drift, and contract inspection",
        "No manual schema mutations; all migrations must flow through CI/CD"
      ]
    }
  },
  "federated_mcps": [
    {
      "mcp_id": "google-developer-knowledge",
      "role": "documentation-grounding",
      "layer": "corporate",
      "activation_policy": "on-demand",
      "environments": ["dev", "tst", "pre", "pro"],
      "description": "Official Google Cloud, Gemini, Android, Firebase, and Web documentation retrieval.",
      "when_to_invoke": "Invoke on demand when verifying official Google Cloud, Gemini, Android, Firebase, or Web API specifications.",
      "avoid_when": "Do not invoke when inspecting local repository code, internal domain models, or offline unit tests.",
      "required_guardrails": [
        "AGENTS.md §5 (Specification Hierarchy & Discrepancy Scans)",
        "software-engineering.md §3 (1:1:1 Symbiosis & Package-Marker Purity)"
      ]
    }
  ]
}
```

### 4.1. Valid `layer_role` Values (`VALID_LAYER_ROLES` — 8 Canonical Roles Across 3 Topological Classes)

Every `system/mcp-layer.json` manifest declares one of the 8 canonical `layer_role` values (`VALID_LAYER_ROLES` in `constants.py`), grouped across 3 topological classes (`governance-layer`, `runtime-node`, `ephemeral-sandbox`):

| `layer_role` | Topological Class (`Axis 2`) | Typical Deployment Target | Primary Purpose in the Context Mesh |
|--------------|------------------------------|---------------------------|-------------------------------------|
| **`corporate`** | `governance-layer` (`Level 1 / root-0`) | Organization-wide or public-administration `Root 0` fork (`acme-corp-root`, `public-gov-root`) | Exposes transverse `Pillar A` security, SSoT ledger, and engineering mandates (`AGENTS.md`) plus enterprise-approved MCP catalog (`precedence: 1..2` for Public Admin, `10` for Enterprise). |
| **`domain-policy`** | `governance-layer` (`Level 2 / department`) | Statutory, legal/IP, or regulatory department fork (`dept-justice`, `dept-tax`, `dept-territorial`, `dept-legal`) | Exposes high-precedence (`3..9`) `surface_bindings`, canonical templates, and statutory/regulatory invariants projected onto matching surfaces via `resolve_surface_governance`. |
| **`department`** | `governance-layer` (`Level 2 / department`) | Functional department or sub-department fork (`dept-finance`, `dept-tech`, `dept-marketing`) | Exposes department-specific compliance rules, specialization-stack templates (`science-stack`, `business-stack`, `framework-stack`), domain docs, `surface_bindings`, and departmental MCP servers (`15..40`); mounted into child repos via `git subtree` (`layers/<slug>`). |
| **`squad`** | `governance-layer` (`Level 3 / unit`) | Sub-department, operational unit, research lab, personal tutor, or delivery squad fork (`acme-unit-patents`, `acme-squad-payments`) | Optional sub-department/unit role (`precedence: 50`) inheriting parent department rules and applying `science-stack`, `business-stack`, or `framework-stack` templates and shared unit MCP servers. |
| **`service-node`** | `runtime-node` | Application container, Devcontainer, or transversal platform node (`layers/voip-platform` or `/opt/dotfiles-ubuntu`) | Exposes the service's package manifest (`system/*`), drift status (`audit_node_drift`), service `docs/`, and service-local MCPs across `dev`, `tst`, `pre`, `pro`. |
| **`environment-cluster`** | `runtime-node` | Shared environment topology fork (`layers/env-pre-cluster`) | Exposes cluster-wide observability and deployment guardrails for a specific environment tier (`tst`, `pre`, `pro`). |
| **`workstation`** | `runtime-node` | Developer PC (`~/dotfiles-ubuntu` / `<user>-pc`) | Default role combining local GNU Stow management with local MCP introspection, mounted `layers/*` subtrees, and composite visibility scope (`private:individual:root-0` when forked vs. `public-oss`). |
| **`ephemeral-bot`** | `ephemeral-sandbox` | TTL-bounded zero-copy sandbox (`logs/ephemeral_forks/<fork_id>`) | Materialized on demand via `orchestrate_ephemeral_fork` / `make consult` (`precedence: 15`) with scoped `MCP_PERMISSION_RINGS` (`readonly` passive MCP capability) and `rcap1` return digest membrane. |

### 4.2. Composite `visibility_scope` (`private:<entity_kind>:<tier_scope>`) vs. Passive `readonly` MCP Capability

`dotfiles-ubuntu` separates **passive MCP execution capability** (`access_mode: "strictly-read-only"` / `MCP_PERMISSION_RINGS`) from **Git orchestration privacy, context sanitization, and inter-entity exposure governance** (`visibility_scope`, `exposure_boundary`, `can_expose_to_oss`, and `inter_root_collaboration_authorized` in [`_resolve_layer_entity_identity`](../../scripts/dotfiles_mcp/core/layer_topology_helpers.py) and [`_classify_inter_layer_relationship`](../../scripts/dotfiles_mcp/core/layer_topology_helpers.py)):
- **`public-oss`**: Canonical Open-Source upstream (`layer_id: "dotfiles-ubuntu"`, `exposure_boundary: "public-oss"`, `can_expose_to_oss: True`).
- **`private:<entity_kind>:<tier_scope>`** (`entity_kind` in `{open-source, enterprise, public-government, individual}` and `tier_scope` in `{dev, root-0, department, unit, project}`):
  - **Vertical Open-Source Gateway & Sanitization Membrane (`tier_scope` in `{dev, root-0}` $\rightarrow$ `can_expose_to_oss: True`, `exposure_boundary: "oss-and-inter-root-gateway"`)**: Only `Root 0` repositories (`private:enterprise:root-0`, `private:public-government:root-0`, `private:individual:root-0`) and the private engine dev clone (`private:open-source:dev`) are authorized to collaborate or publish outward to Open Source. When exposing upward to Open Source, the `Root 0` / `dev` boundary omits all local work-orchestration trackers (`WORKTASK.md`, `WORKROAD.md`, `ROADMAP.md`, `BACKLOG.md`, `WORKVALI.md`, `roadmaps/`), `.agents/`, mounted `layers/*` subtrees, and private `corporate/*` ledgers, exporting only generic, stack-reusable architectural learnings (`templates/*`, `skills/*`, `scripts/*`, `docs/*`).
  - **Horizontal Inter-`Root 0` Collaboration (`inter_root_collaboration_authorized: True` when both peers have `can_expose_to_oss: True`)**: Two sovereign `Root 0` nodes from distinct entities (`external:<entity_kind>`) can collaborate horizontally via Pull Requests and file-based proposals (`.agents/proposals/from-peer-root/<source-root-id>/...`) while keeping their internal hierarchies (`layers/*`) and internal work trackers strictly private.
  - **Strict 1-Hop Parent Containment (`tier_scope` in `{department, unit, project}` $\rightarrow$ `can_expose_to_oss: False`, `exposure_boundary: "1-hop-parent-only"`)**: Child departments, units, and projects keep their work trackers in their private `origin` and must promote reusable patterns vertically to their corporate `Root 0` first.

---

## 5. Multi-Dimensional Context Graph: `git fork` + `git subtree` (`layers/`) + Environment Profiles (`dev/tst/pre/pro`)

A single linear chain of Git forks (`Public → Corporate → Squad`) can only represent **vertical inheritance** from a single parent. Real enterprise architectures, however, are **multi-dimensional Directed Acyclic Graphs (DAGs)** where a project simultaneously intersects:
1. **Corporate governance** (vertical parent fork),
2. **Multiple cross-cutting Departments** (e.g., Security, Data Platform, Cloud/SRE),
3. **Sibling Microservices** with coupled APIs/events, and
4. **Multiple Deployment Environments** (`dev`, `tst`, `pre`, `pro`).

`dotfiles-ubuntu` resolves this multi-dimensional orchestration without blowing past the IDE's 20,000-token `defaultRulesBudget` by combining **three orthogonal mechanisms**:

```mermaid
flowchart TD
    Public["Public Upstream\n(mtwuser/dotfiles-ubuntu)"] -->|"1. Vertical Fork\n(layer-subtree.sh sync-upstream)"| Corp["Corporate Root Fork\n(acme-corp/dotfiles-ubuntu)"]
    Corp -->|"Vertical Fork"| Squad["Squad / Workspace Hub\n(acme-squad-payments)"]
    Corp -->|"Vertical Fork"| DeptSec["Department Fork\n(acme-dept-security)"]
    Corp -->|"Vertical Fork"| DeptData["Department Fork\n(acme-dept-data)"]
    Squad -->|"Vertical Fork"| SvcFraud["Sibling Service Fork\n(acme-svc-fraud)"]

    DeptSec -->|"2. Horizontal Subtree (--squash)\nlayers/dept-security/"| Squad
    DeptData -->|"2. Horizontal Subtree (--squash)\nlayers/dept-data/"| Squad
    SvcFraud -->|"2. Horizontal Subtree (--squash)\nlayers/svc-fraud/"| Squad

    Squad -->|"GNU Stow (always_on < 18 KB)"| Stow["~/.gemini/config/\n(Primary Layer Rules Only)"]
    Squad -->|"3. On-Demand MCP Graph\n(0 idle token cost)"| MCP["scripts/dotfiles_mcp_server.py\n(Auto-discovers root + layers/* + dev/tst/pre/pro)"]
```

### 5.1. Vertical Inheritance via `git fork` (`./scripts/layer-subtree.sh sync-upstream`)

- Keeps the repository's primary root synchronized with its upstream parent (`Public → Corporate → Squad` or `Public → Personal Workstation Fork`), automatically snapshotting and restoring the downstream fork's `system/mcp-layer.json` whenever `layer_id != "dotfiles-ubuntu-default"` so merging Open-Source engine updates never overwrites fork identity.

### 5.2. Horizontal / Cross-Departmental Composition via `git subtree` (`./scripts/layer-subtree.sh add | pull | push | pull-all | list`)

- Secondary forks (Departmental governance repos, sibling service MCP repos, or cluster topologies) are mounted under the non-stow **`layers/<layer-name>/`** directory using `git subtree --squash`. When invoked inside any workspace containing `system/mcp-layer.json`, `scripts/layer-subtree.sh` automatically resolves `REPO_DIR="$PWD"`, and `run_subtree_pull()` automatically reconciles subtree merge conflicts strictly scoped inside `layers/<layer-name>/` in favor of the authoritative child repository (`--theirs`).
- Because `bootstrap.sh` and `audit.sh` skip `layers/`, mounted subtrees add **0 bytes** to the `always_on` `~/.gemini/config/AGENTS.md` token budget.
- Instead, `scripts/dotfiles_mcp_server.py` automatically discovers every subtree under `layers/*/` and exposes its `docs/`, `AGENTS.md`, `templates/`, and `federated_mcps` on demand (`layer="all"` or `layer="<layer-name>"`).

### 5.3. Transversal Environment Profiles (`environments: {dev, tst, pre, pro}` + `requirements-<env>.txt`)

- Rather than duplicating Git repositories for every environment of the same service, `system/mcp-layer.json` defines environment-specific access modes (`read-write-local` in `dev`, `read-and-test-trigger` in `tst`, `strictly-read-only` in `pre`, `strictly-read-only-audited` in `pro`), default guardrails, and `requirements-<env>.txt` pointers.

### 5.4. 3-Tier Token Optimization & Fixed vs. Ephemeral MCP Architecture (`Static .agents/rules/` + Fixed `dotfiles-mcp` + Ephemeral `make consult`)

- **Why Only ONE Fixed `dotfiles-mcp` Server Is Needed Globally**: Rather than registering a separate persistent MCP server per parent layer, `set-global-profile --stow` registers a single fixed `"dotfiles-mcp"` entry in `~/.gemini/{config,antigravity}/mcp_config.json`. Because every MCP tool (`get_layer_overview`, `query_governance_rules`, `resolve_surface_governance`, `discover_federated_mcps`) accepts `workspace_dir="<active-workspace-path>"`, that single server dynamically evaluates the active workspace's `system/mcp-layer.json`, its 1-hop parent (`PARENT_DIR`), and its mounted `layers/*` subtrees with **zero process duplication**.
- **3-Tier Context & Token Budget Allocation**:
  1. **Tier A — Static Projected Rules (`<repo>/.agents/rules/layer-<NN>-<id>.md`, Always-On, `0` RPC Latency)**: Immediate mandatory invariants from the governing layer chain (`apply-project --layers all`) stay within the `< 18 KB` per-layer budget for zero-latency enforcement.
  2. **Tier B — Fixed `dotfiles-mcp` (`workspace_dir` + Progressive `rcap1` Unfolding `L0 -> L1 -> L2 -> L3`)**: Used by any consumer of an immediate parent layer (`Root 0` $\leftarrow$ `Department` $\leftarrow$ `Unit` $\leftarrow$ `Project`). Queries start at `L0` (`~12–18` tokens/match) or `L1` (`~60–90` tokens) and unfold to `L2`/`L3` only on resonant sections, saving `85–90%` of context tokens.
  3. **Tier C — Ephemeral `strictly-read-only` MCP Forks (`make consult` / `orchestrate_ephemeral_fork`)**: Used for cross-departmental audits (`layers/<dept>/`), specialist bots (`precedence: 15`), or horizontal peer `Root 0` inspections. Returns a 4-Channel Executive Digest + `rcap1` capsule and auto-reaps (`Crypto-Shredding`) so foreign layer context never pollutes the permanent session.

### 5.5. The 4 Inter-Layer Communication Modes (`mcp_communication_mode` in `_classify_inter_layer_relationship`)

- **`internal-1hop-hierarchical`**: Vertical 1-hop communication inside the same `governing_root_id` (`make delegate` downward into `layers/<child>/`; `make promote` upward via `.agents/proposals/from-child/<child-id>/`).
- **`external-root0-to-oss-sanitized`**: Exclusive gateway from `Root 0` (`can_expose_to_oss: true`, `exposure_boundary: "oss-and-inter-root-gateway"`) or `private:open-source:dev` to `public-oss`. Automatically strips internal orchestration trackers (`WORKTASK.md`, `WORKROAD.md`, `BACKLOG.md`, `WORKVALI.md`, `roadmaps/`, `.agents/`, `corporate/`, `layers/`) and personal layers (`precedence >= 85` / `entity_kind: "individual"`), exposing only generic learnings via anonymized PR (`make publish-oss` or `make promote --create-pr`).
- **`external-peer-root0-pr-and-readonly-mcp`**: Horizontal collaboration between two distinct `Root 0` entities (`inter_root_collaboration_authorized: true`, e.g., `Root 0 A` $\leftrightarrow$ `Root 0 B`) via non-destructive file proposals (`.agents/proposals/from-peer-root/<source-root-id>/` + Pull Request) and `strictly-read-only` MCP consultation (`make consult`).
- **`blocked-must-route-via-governing-root0`**: Blocks direct external or Open-Source exposure from internal `department`, `unit`, or `project` layers (`can_expose_to_oss: false`, `exposure_boundary: "1-hop-parent-only"`), requiring promotion 1-hop at a time up to their `governing_root_id` (`Root 0`).

---

## 6. Controlled On-Demand MCP Orchestration, Runtime Warnings & Structured Logging (`logs/`)

To prevent **two opposite failure modes** in multi-dimensional context graphs — **(1) silent context/token truncation** and **(2) uncontrolled MCP fan-out or missing corporate guardrails** — `dotfiles-ubuntu` enforces deterministic runtime controls across both planes:

### 6.1. Hierarchical Guardrail Inheritance (`effective_guardrails`) & On-Demand Activation Policy

When `discover_federated_mcps` resolves MCP servers across the root repository, mounted `layers/*` subtrees, and target `dev/tst/pre/pro` environments, a downstream subtree can **never** strip or bypass parent corporate or environment safety rules. For every discovered MCP entry, `scripts/dotfiles_mcp_server.py` computes **`effective_guardrails`** as the deduplicated union of five hierarchical levels:

> `effective_guardrails` $=$ Root `baseline_guardrails` $\cup$ Subtree `baseline_guardrails` $\cup$ Root Environment `default_guardrails` $\cup$ Subtree Environment `default_guardrails` $\cup$ MCP `required_guardrails`

Additionally, every federated MCP entry carries explicit **on-demand routing metadata** so the AI agent neither under-uses nor over-uses underlying MCP servers:
- `activation_policy`: `"on-demand"` (never poll or invoke speculatively).
- `when_to_invoke`: Explicit task trigger condition for invoking the MCP.
- `avoid_when`: Explicit condition under which the agent must skip the MCP and use local context instead.

### 6.2. Runtime Warning & Alert Catalog (In-Band + Out-of-Band)

Both `post_invocation_lint.py` (local `PostInvocation` hook) and `scripts/dotfiles_mcp_server.py` actively monitor token budgets, truncation boundaries, subtree lineage, and MCP fan-out:

| Warning Code | Severity | Trigger Condition | Purpose |
|--------------|:--------:|-------------------|---------|
| `TOKEN_BUDGET_NEAR_LIMIT` | `WARN` | `AGENTS.md` $\ge 16,000$ bytes ($88\%$ of 18 KB cap) | Early warning before `AGENTS.md` reaches the 18,000-byte ceiling (`channel_3_active_invariants_and_hooks.agents_md_budget_utilization_pct`). |
| `TOKEN_BUDGET_EXCEEDED` | `CRITICAL` | `AGENTS.md` $> 18,000$ bytes | Alerts that `AGENTS.md` exceeds the hard cap and risks silent rule truncation in the IDE. |
| `WORKSPACE_RULES_BUDGET_EXCEEDED` | `WARN` | Combined `always_on` rules (`AGENTS.md` + workspace `.agents/rules/*.md`) $> 80,000$ bytes (~20k tokens) | Emitted by `post_invocation_lint.py` (`check_rules_token_budget`) when combined active rules exceed the 20,000-token budget. |
| `RESPONSE_TRUNCATED` | `WARN` | `query_governance_rules` matches $> 15$ sections / $> 1,500$ chars, or `unfold_context_capsule` (`L2`/`L3`) exceeds $8,000$-char section / $5 \times 4,000$-char `L3` link caps | Alerts the AI agent in-band (`truncated: true`) that results were capped and recommends narrowing `query`/`scope`/`layer` or calling `read_layer_document`. |
| `LARGE_MCP_PAYLOAD_WARNING` | `WARN` | Any MCP JSON-RPC response exceeds $16,000$ bytes (~4,000 tokens) | Alerts when a single MCP call consumes significant context window capacity. |
| `MCP_FANOUT_WARNING` | `WARN` | Unfiltered `discover_federated_mcps` returns $> 3$ MCPs without `environment` or `filter_role` | Prevents indiscriminate multi-MCP fan-out across layers and environments. |
| `SUBTREE_LINEAGE_WARNING` | `WARN` | A mounted `layers/<name>/` subtree is missing `upstream_layer.repository` | Detects orphan subtrees lacking upstream Git lineage. |
| `TEMPLATE_PACK_MISSING` | `WARN` | An entry in `default_stack_templates` does not exist under `templates/<name>/` | Detects stale or unmounted template pack references in `system/mcp-layer.json` (`init-fork --prune-default-templates` or `scaffold-template`). |
| `NODE_DRIFT_DETECTED` | `WARN` | `audit_node_drift` detects non-zero exit from `verify-repo.sh` or `audit.sh` | Records repository or OS/Stow drift in `logs/mcp_alerts.jsonl`. |
| `CAPSULE_CAPABILITY_INSUFFICIENT` | `WARN` | `unfold_context_capsule` called with insufficient `agent_tier` (e.g., `"flash"` requesting `L2`/`L3` or `"inherit"` requesting `L3` in `pro`) | Enforces `AGENTS.md §12` model delegation discipline at the cryptographic MCP boundary. |
| `CAPSULE_RESONANCE_DENIED` | `WARN` | Missing `resonance_key` when `header.kr=true`, invalid `resonance_key`, tampered HMAC signature, or mismatched `environment` on `rcap1` capsule | Detects unauthorized, unauthenticated, or cross-environment capsule unfolding attempts. |
| `CAPSULE_CHAIN_BROKEN` | `WARN` | Malformed `rcap1` envelope, corrupted `zlib` stream, or level-scoped `parent_hash`/section/`L3` SHA-256 content drift mismatch | Guarantees cryptographic chain integrity and level-scoped live drift detection across multi-hop Matryoshka unfolding (`L0->L1`, `L1->L2`, `L2->L3`). |
| `SURFACE_PRECEDENCE_COLLISION` | `WARN` | Two or more distinct layers match a surface with identical `(precedence, mode)` during `resolve_surface_governance` | Alerts that equal-precedence layers collided on the same surface and were tie-broken via *Lex Specialis* (`specificity_score`), recommending distinct `precedence` (`0..100`) values in `system/mcp-layer.json`. |
| `SURFACE_ASSET_MISSING` | `WARN` | A matched `surface_binding` references a `rule_file` or `canonical_template` that does not exist on disk in its layer | Detects governance metadata drift (`rule_files` or `canonical_templates` pointing to missing files) while preventing ghost templates from entering the response. |
| `EPHEMERAL_FORK_LIMIT_REACHED` | `WARN` | Active ephemeral forks reach `MAX_ACTIVE_EPHEMERAL_FORKS` (`16`) during `spawn` / `evaluate` | Prevents unbounded ephemeral fork proliferation across concurrent subagents. |
| `EPHEMERAL_FORK_EXPIRED` | `WARN` | Targeted `fork_id` has exceeded its `ttl_seconds` lease and was reaped | Alerts that the ephemeral lease expired and requires respawning if still needed. |
| `EPHEMERAL_LEASE_EXPIRED_OR_SHREDDED` | `WARN` | `action="verify-return"` attempted after an ephemeral fork lease expired or was reaped (*Crypto-Shredding*) | Guarantees zero standing privileges: return capsules cannot be decrypted once the ephemeral lease is reaped. |
| `SURFACE_BOUNDARY_VIOLATION` | `WARN` | Return digest `channel_2_affected_surface` reports file paths outside the bot's leased `surface_globs` | Enforces cryptographic scope containment on ephemeral bot handbacks (`action="verify-return"`). |
| `SECURITY_OR_VALIDATION_ERROR` | `ERROR` | Path traversal attempt (`../`), invalid `layer`/`environment`/`precedence`/`mode`, unsupported `schema_version`, or missing file | Records security containment or parameter validation rejections in `logs/mcp_alerts.jsonl`. |

### 6.3. Structured JSONL Audit & Alert Logs (`logs/mcp_events.jsonl` & `logs/mcp_alerts.jsonl`)

When running in MCP mode, `scripts/dotfiles_mcp_server.py` automatically writes structured JSON Lines to `<repo>/logs/` (configurable via `--log-dir <path>`, `DOTFILES_MCP_LOG_DIR`, or disabled via `--no-log`):
- **`logs/mcp_events.jsonl`**: Records every JSON-RPC request (`ts`, `method`, `target`, `layer`, `environment`, `duration_ms`, `response_bytes`, `estimated_tokens`, `warning_count`, `status`, plus compaction telemetry `resolution`, `tokens_saved`, `savings_pct`, `unfolded_level`, `agent_tier`, `decrypted_hops`).
- **`logs/mcp_alerts.jsonl`**: Dedicated stream of `WARN`, `ERROR`, and `CRITICAL` alerts for instant operator inspection (`tail -f ~/dotfiles-ubuntu/logs/mcp_alerts.jsonl`).
- **`dotfiles://mcp/diagnostics` (`resonance_compaction_summary`)**: Aggregates live behavioral compaction metrics (`queries_by_resolution`, `unfolds_by_target_level`, `unfolds_by_agent_tier`, `total_decrypted_hops`, `cumulative_tokens_saved`, and `capsule_alerts_by_code`).
- **Automatic Size Rotation & Container Safety**: Each log file automatically rotates to `.jsonl.1` at `512 KB`, is ignored by Git and GNU Stow (`[ "$module" = "logs" ] && continue`), and gracefully suppresses `OSError` when mounted on a read-only container filesystem (`:ro`).

### 6.4. Specialized Engines (`rcap1` Compaction, `0..N` Surface Projection, Promotion & Ephemeral Forks)

To keep each architecture specification modular (`< 465` lines) and aligned `1:1:1` with its implementation and test subpackages (`capsules/`, `governance/`, `mcp_node/`), the normative specifications for the specialized engines are maintained in **[`docs/architecture/04_compaction_surface_and_promotion_engines.md`](04_compaction_surface_and_promotion_engines.md)**, **[`docs/architecture/05_ephemeral_forks_and_department_bots.md`](05_ephemeral_forks_and_department_bots.md)**, and **[`docs/architecture/06_layer_governance_and_promotion_engines.md`](06_layer_governance_and_promotion_engines.md)**:
- **Arch 04 §2 — Resonant Chained Context Compaction & Unfolding (`rcap1`: `L0 → L1 → L2 → L3` in `capsules/`)**: `Promoter Codon → Exon Axiom Skeleton → Full Section → Deep L3 Links`, Matryoshka HMAC-SHA256 + `zlib` + SHA-256 CTR onion encryption (`capsule_engine.py`, `tools_compaction.py`, `tools_unfold.py`), `agent_tier` capability gating (`CAPSULE_CAPABILITY_INSUFFICIENT`, `CAPSULE_RESONANCE_DENIED`, `CAPSULE_CHAIN_BROKEN`), and TOCTOU line-drift relocation.
- **Arch 04 §3 — Stack-Agnostic Multi-Layer Surface Projection & Governance Weaver (`0..N` Layers via `resolve_surface_governance` in `capsules/`)**: 4 universal selectors (`target_globs`, `architectural_planes`, `scopes`, `traits`), numeric deontic `precedence` (`0..100`, *Lex Superior*), *Lex Specialis* specificity tie-breaking (`SURFACE_PRECEDENCE_COLLISION`), `SURFACE_ASSET_MISSING`, and automatic `template.json` binding merging (`collect_layer_effective_bindings` in `surface_weaver.py` & `tools_surface.py`).
- **Arch 05 §§1–5 — Ephemeral Scoped Forks, OOP Capability Rings & Symbiotic Bots (`orchestrate_ephemeral_fork` in `mcp_node/`)**: OOP CRUD permission rings (`MCP_PERMISSION_RINGS`), 4-family bot taxonomy (`BOT_ARCHETYPE_CATALOG`, `action="catalog"`), Permanent $\leftrightarrow$ Ephemeral symbiosis (`resolve_mcp_capability_profile` / `"ephemeral-augmented"`), `rcap1` Return Digest Membrane (`action="seal-return" | "verify-return"`, `EPHEMERAL_LEASE_EXPIRED_OR_SHREDDED`, `SURFACE_BOUNDARY_VIOLATION`), zero-copy hardlinked ephemeral forks (`layer_role: "ephemeral-bot"`, `precedence: 15`), cross-project `.agents/rules/*.md` bridges, 4-channel `subagent_invocation_brief`, and automatic TTL garbage collection (`EPHEMERAL_FORK_LIMIT_REACHED`, `EPHEMERAL_FORK_EXPIRED` in `capability_registry.py`, `ephemeral_fork_engine.py`, & `tools_ephemeral.py`).
- **Arch 06 §§1–5 — Polymorphic Fork Configurator (`template.json`), Static Materialization & Multi-Layer Promotion Engine (`governance/`)**: `init-fork`, `list-templates`, `scaffold-template`, `apply-project`, `compare_layer_patterns(layer="all")` (`promotion_routing`), `diff-project`, `promote-from-project`, `inspect-horizon`, `set-authority`, `start-task`, `complete-task`, `delegate-to-child`, `consult-layer`, `configure-git-policy`, `manage-roster`, `check-env-promotion`, and `record-decision` (`fork_configurator.py`, `workspace_bootstrapper.py`, `promotion_engine.py`, `horizon_engine.py`, `authority_engine.py`, `workflow_engine.py`, `git_governance_engine.py`, `cli_dispatcher.py`).

---

## 7. Verification & Self-Test Contract

To guarantee that `scripts/dotfiles_mcp_server.py` and `scripts/layer-subtree.sh` remain deterministic and pass CI on every commit:

### 7.1. CLI Flags (`--help`, `--version`, `--self-test`, `--log-dir`, `--no-log`, `list`)

- Running `./scripts/dotfiles_mcp_server.py --self-test` executes an in-process JSON-RPC 2.0 round-trip test verifying `initialize`, `resources/list`, `resources/read`, `tools/list`, `tools/call` (`get_layer_overview`, `discover_federated_mcps`, `query_governance_rules`, `unfold_context_capsule`, `resolve_surface_governance`, `orchestrate_ephemeral_fork`), `prompts/list`, and JSONL event/alert log generation without requiring an external MCP client.
- Running `./scripts/layer-subtree.sh list` inspects `layers/*/` and reports all mounted context subtrees.

### 7.2. CI & Container Gate Integration (`scripts/verify-repo.sh` & `Dockerfile`)

- `scripts/verify-repo.sh` compiles `scripts/dotfiles_mcp_server.py` (`py_compile`), lints it with `ruff check` and `mypy --strict`, validates `system/mcp-layer.json` schema (`mcp-layer-v1`) and `Dockerfile` contract (`FROM ubuntu:26.04`, non-root `USER ubuntu`, `/opt/dotfiles-ubuntu`), runs `./scripts/layer-subtree.sh list` and `./scripts/dotfiles_mcp_server.py --self-test`, and enforces **100.00% statement and branch coverage** via `pytest`.
- `Dockerfile` executes `python3 /opt/dotfiles-ubuntu/scripts/dotfiles_mcp_server.py --self-test --no-log` and `/opt/dotfiles-ubuntu/scripts/layer-subtree.sh list` during `docker build` (`make docker-build` / `make docker-self-test`), guaranteeing that every built image is self-verified and ready for both standalone `docker run -i --rm` execution and multi-stage `COPY --from` sidecar injection.
