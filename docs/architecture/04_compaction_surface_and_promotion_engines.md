# Architecture 04: Resonant Compaction (`rcap1`) & Surface Projection (`0..N`) Engines (`capsules/`)

> **Normative Specification — Subsystem 3B (`scripts/dotfiles_mcp/capsules/{capsule_engine,surface_weaver,tools_compaction,tools_unfold,tools_surface}.py`)**
>
> This document specifies the **`capsules/`** bounded-domain subpackage (Subpackage 2 of `scripts/dotfiles_mcp/`):
> 1. **Resonant Chained Context Compaction & Unfolding (`rcap1`: `L0 → L1 → L2 → L3`)**
> 2. **Stack-Agnostic Multi-Layer Surface Projection & Governance Weaver (`0..N` Layers)**
>
> For the core JSON-RPC 2.0 protocol contract (`core/` & `mcp_node/`), see **[`03_contextual_mcp_and_federation.md`](03_contextual_mcp_and_federation.md)**; for OOP capability rings and ephemeral bots (`mcp_node/`), see **[`05_ephemeral_forks_and_department_bots.md`](05_ephemeral_forks_and_department_bots.md)**; for fork parameterization, 1-hop horizon, RBAC authority, task-branch workflows, and upward promotion (`governance/` & `scripts/layer-config.sh`), see **[`06_layer_governance_and_promotion_engines.md`](06_layer_governance_and_promotion_engines.md)**.

---

## 1. `1:1:1` Source $\leftrightarrow$ Unit Test $\leftrightarrow$ Specification Traceability Matrix (`capsules/`)

Every engine module in `scripts/dotfiles_mcp/capsules/` maintains a strict `1:1:1` alignment between its subpackage-mirrored `1:1` unit test suite (`100.00%` isolated single-file branch coverage, `< 465` lines) and its bidirectional docstring pointer (`Specification: docs/architecture/04_compaction_surface_and_promotion_engines.md`):

| Subpackage & Domain | Source Module (`scripts/dotfiles_mcp/capsules/`) | `1:1` Unit Test (`tests/unit/dotfiles_mcp/capsules/`) | Normative Section & Primary Symbols |
|---|---|---|---|
| **`capsules/` — Resonant Capsule Crypto & Compression** | [`capsules/capsule_engine.py`](../../scripts/dotfiles_mcp/capsules/capsule_engine.py) | [`capsules/test_capsule_engine.py`](../../tests/unit/dotfiles_mcp/capsules/test_capsule_engine.py) (`TestCapsuleEngine`) | **§2 & Arch 05 §5.3**: `CapsuleError`, `_seal_single_capsule`, `_parse_capsule_envelope`, `_derive_chain_key`, `_xor_keystream`, `_extract_axiom_skeleton`, `_extract_l3_links`, `seal_ephemeral_digest_capsule`, `unseal_ephemeral_digest_capsule` |
| **`capsules/` — Multi-Resolution Rule Search & Minting** | [`capsules/tools_compaction.py`](../../scripts/dotfiles_mcp/capsules/tools_compaction.py) | [`capsules/test_tools_compaction.py`](../../tests/unit/dotfiles_mcp/capsules/test_tools_compaction.py) (`TestCompactionToolsMixin`) | **§2**: `CompactionToolsMixin`, `_build_section_capsule`, `_tool_query_governance_rules` |
| **`capsules/` — Hop-by-Hop Capsule Unfolding (`L0->L3`)** | [`capsules/tools_unfold.py`](../../scripts/dotfiles_mcp/capsules/tools_unfold.py) | [`capsules/test_tools_unfold.py`](../../tests/unit/dotfiles_mcp/capsules/test_tools_unfold.py) (`TestUnfoldToolsMixin`) | **§2**: `UnfoldToolsMixin`, `_resolve_ephemeral_issuer_meta`, `_tool_unfold_context_capsule` |
| **`capsules/` — Surface Selector Inference, Co-Ownership & $N$-Layer Consensus** | [`capsules/surface_weaver.py`](../../scripts/dotfiles_mcp/capsules/surface_weaver.py) | [`capsules/test_surface_weaver.py`](../../tests/unit/dotfiles_mcp/capsules/test_surface_weaver.py) (`TestSurfaceWeaver`) | **§3 & Arch 06 §4**: `collect_layer_effective_bindings`, `match_authoritative_surface_bindings`, `evaluate_multilayer_surface_consensus`, `_resolve_co_owner_ledger_decision`, `_infer_plane_from_path`, `_infer_scope_from_path`, `_binding_matches_surface`, `_compute_binding_specificity` |
| **`capsules/` — `0..N` Layer Surface Governance Weaver** | [`capsules/tools_surface.py`](../../scripts/dotfiles_mcp/capsules/tools_surface.py) | [`capsules/test_tools_surface.py`](../../tests/unit/dotfiles_mcp/capsules/test_tools_surface.py) (`TestSurfaceToolsMixin`) | **§3**: `SurfaceToolsMixin`, `_resolve_binding_asset`, `_tool_resolve_surface_governance` |

---

## 2. Resonant Chained Context Compaction & Unfolding (`rcap1`: `L0 → L1 → L2 → L3`)

When an AI agent searches across a multi-dimensional context graph (`Root` + mounted `layers/*` subtrees + `dev/tst/pre/pro` environments), returning full Markdown sections (`L2`) for every match wastes context tokens on non-resonating sections. At the same time, passing raw encrypted/Base64 blobs directly into an LLM prompt would *increase* BPE token usage due to high Shannon entropy.

To solve both problems using **100% Python Standard Library (`zlib`, `hashlib`, `hmac`, `base64`)**, `scripts/dotfiles_mcp/capsules/` implements **Resonant Chained Context Compaction (`rcap1`)**, inspired by biological DNA/RNA chromatin transcription (`Promoter Codon → Exon Skeleton → Full Transcript → Epigenetic L3 Complex`):

1. **Four Progressive Resolution Levels (`L0 → L1 → L2 → L3`) & Unified `sections` / `promoter_codon` Contract**:
   - Every Markdown rule or specification file is parsed via `_iter_markdown_sections` into discrete **`sections`** (`section`, `start_line`, `end_line`, `promoter_codon`, `capsule_token`): `query_governance_rules` returns `matches[].{section, promoter_codon, capsule_token}`, `resolve_surface_governance` returns `resolved_bindings[].sections[].{section, promoter_codon, capsule_token}`, and `unfold_context_capsule` returns `promoter_codon` alongside `content.section`.
   - **`L0` — Promoter Codon (`resolution="L0"`, ~15–25 tokens/match)**: Exposes a readable start/stop codon (`AUG:<scope>:<slug>:UAA`), 5 semantic tags, token cost estimates (`L0`, `L1`, `L2`, `L3`), and a sealed `rcap1` Matryoshka capsule token. Allows an agent to scan 15 matches across layers for `< 300` tokens, reject non-resonating sections at `0` extra cost, or resonate and unfold `L1`.
   - **`L1` — Exon Axiom Skeleton (`resolution="L1"`, ~40–65 tokens/match)**: Extracts the section heading, core mandate quote (`> *"..."*`), and up to 4 bullet titles while folding tables and fenced code blocks inside the `rcap1` capsule (`[+N detail/table/code lines folded in rcap1:L1]`). Sufficient for ~80% of coding turns (~85% token savings).
   - **`L2` — Full Section Specification (`resolution="L2"`, default)**: Returns the verbatim Markdown section (tables, code blocks, invariants) plus `l3_links` metadata (including `sha256` content digests) and an `rcap1` capsule pointing to `L3`.
   - **`L3` — Deep Linked Procedural Source (`target_level="L3"`)**: Unfolds the full content of referenced `SKILL.md` or architecture specs (`linked_l3_documents`), merged `effective_guardrails`, and `federated_mcps` for the target layer and environment.
2. **Matryoshka Chained Cryptographic Envelope (`rcap1.<header_b64>.<cipher_b64>.<hmac_sig_hex24>`)**:
   - **Shallow Prefix Inspection (`target_level="L0"`)**: The outer `<header_b64>` is decodable via `_parse_capsule_envelope` and HMAC-verified in $O(1)$ time (`decrypted_hops: 0`) without decompressing `<cipher_b64>`.
   - **3-Layer Matryoshka/Onion Nesting ($C_0(K_0) \supset C_1(K_1) \supset C_2(K_2)$)**: Each level's key is derived via $K_k = \text{HMAC-SHA256}(M_{\text{secret}}, \texttt{"rcap1-key:"} \parallel \texttt{layer} \parallel \texttt{":"} \parallel L_k \parallel \texttt{":"} \parallel H_k \parallel \texttt{":"} \parallel \texttt{env})$, where the interior payload (including `next_cap` for deeper hops) is compressed with `zlib.compress(level=9)` and encrypted with a SHA-256 counter-mode keystream (`_xor_keystream`). Unfolding unwinds the onion hop-by-hop (`L0->L1`, `L1->L2`, `L2->L3`) and verifies level-scoped digests (`h0->h1` at `L1`, `h1->h2` over the 8,000-char section at `L2`, and `h2->h3` over linked `L3` file paths + SHA-256 content digests at `L3`). Thus, drift in a linked `L3` document is caught at `L2->L3` (`CAPSULE_CHAIN_BROKEN`) while preserving valid `L1`/`L2` unfolding.
3. **Capability, Key Requirement, Ephemeral Issuer Verification & Environment Depth Gating (`AGENTS.md §12`)**:
   - `agent_tier="flash"` is restricted to `L0` and `L1` Axiom Skeletons; attempting to unfold `L2` or `L3` is deterministically blocked (`CAPSULE_CAPABILITY_INSUFFICIENT`).
   - `agent_tier="inherit"` can unfold `L1`, `L2`, and standard `L3`; unfolding `L3` in a `"pro"` environment requires `agent_tier="pro"`.
   - Capsules sealed with an explicit `resonance_key` (or `DOTFILES_RESONANCE_KEY`) set `"kr": true` in the capsule envelope (`promoter_codon`) and reject unauthenticated, wrong-key, cross-node (`"iss"` mismatch), or cross-environment unfolding attempts (`CAPSULE_RESONANCE_DENIED`). Capsules minted by an active ephemeral fork (`iss="eph-..."`) are resolved by the parent server via `_resolve_ephemeral_issuer_meta` while unexpired, and automatically rejected once the fork is reaped or expires.
4. **Dual Virtue of `rcap1` Compaction (`Token Economy` + `Business Confidentiality & Context Firewall`)**:
   - **Virtue 1 — Token Economy & Context Window Limiting (`technical` & `business` modes)**: `L0` Promoter Codons (`15–25` tokens) and `L1` Exon Skeletons (`40–65` tokens, `~85%` compaction) prevent context-window saturation when weaving rules across `0..N` layers, folding verbose Markdown tables and code blocks inside `<cipher_b64>` until explicitly unfolded.
   - **Virtue 2 — Cryptographic Business Confidentiality, *Lex Superior* & SSoT Integrity Firewall (`business` mode)**: When crossing organizational tiers (`Root 0 -> Department -> Squad -> Project`) or running `make consult` (`consult_layer_ephemeral`), every capsule is sealed with `session_resonance_key` (`kr: true`) and bound to its issuer (`iss`), environment (`env`), and level-scoped SHA-256 digests (`h0..h3`). Downstream `flash` bots or unauthenticated nodes can read `L0`/`L1` normative boundaries without exposing proprietary `L2`/`L3` annexes (`CAPSULE_CAPABILITY_INSUFFICIENT` / `CAPSULE_RESONANCE_DENIED`), while any out-of-band tampering with a `corporate/*.md` SSoT policy immediately breaks the HMAC/digest chain (`CAPSULE_CHAIN_BROKEN`).
5. **Cross-Architecture Safeguards (`include_capsules=false`, TOCTOU Line-Drift Relocation & Alert Deduplication)**:
   - **Content-Negotiation Opt-Out (`include_capsules=false`)**: Callers querying `L2` or `L1` without needing subsequent capsule unfolding can pass `include_capsules=false` on `query_governance_rules` or `resolve_surface_governance` to omit `capsule_token` (`capsule_overhead_tokens: 0`).
   - **TOCTOU Line-Drift Relocation (`line_drift_relocated`)**: If lines are inserted or deleted earlier in a Markdown file after a capsule is minted, `_tool_unfold_context_capsule` automatically relocates the section by its heading (`_iter_markdown_sections`) and verifies `live_h1..h3`, succeeding without false-positive failures when the section itself is intact.
   - **Actionable Recovery Hints & Non-Duplicate Alerts (`CapsuleError`)**: Capsule failures append an explicit `[Recovery: ...]` hint for AI agents and suppress duplicate `SECURITY_OR_VALIDATION_ERROR` alerts in `logs/mcp_alerts.jsonl`.

---

## 3. Stack-Agnostic Multi-Layer Surface Projection & Governance Weaver (`0..N` Layers via `resolve_surface_governance`)

When an organization scales from a single repository (`0` mounted subtrees) to `1` or `N` arbitrary governance layers (`layers/<any-slug>/` — such as statutory compliance, financial controls, design systems, or growth/SEO), `resolve_surface_governance` determines **which exact rules, invariants, and canonical templates from which layers govern the target file or module**, and **which layer wins when multiple layers intersect**:

1. **Zero Hardcoded Departments (`0 → 1 → N` Arbitrary Layers)**:
   - The **Root repository** (`self.repo_dir`, default `precedence: 10`) provides the universal engineering baseline (`AGENTS.md` + `templates/*`) via GNU Stow and MCP without requiring a separate `"dept-it"` subtree.
   - Any `0`, `1`, or `N` additional governance layers can be mounted under `layers/<any-slug>/` with any `layer_id`, `layer_role` (`department`, `domain-policy`, `squad`, `corporate`, `service-node`), and numeric `precedence` (`0..100`).
2. **Four Universal Surface Selectors (`surface_bindings`)**:
   - **`target_globs`**: Relative file glob patterns (`["templates/**", "static/css/**", "*.html"]`, `["*"]`, or `["**"]`).
   - **`architectural_planes`**: Universal software engineering planes (`"schema"`, `"domain"`, `"application"`, `"presentation"`, `"infrastructure"`, `"testing"`, or `"*"`). Automatically inferred from `target_path` via `_infer_plane_from_path` when omitted.
   - **`scopes`**: Feature module, bounded context, or domain service names (`["checkout", "legal", "catalog"]` or `["*"]`). Automatically inferred from `target_path` via `_infer_scope_from_path` when omitted.
   - **`traits`**: Semantic cross-cutting tags (`["pii", "financial", "public-facing"]` or wildcard `["*"]`).
3. **Numeric Deontic Precedence (`0..100`, *Lex Superior*), Selector Specificity (*Lex Specialis*) & Adaptive `rcap1` Resolution**:
   - Non-intersecting layers are pruned at `0` token cost (`pruned_layers`).
   - Intersecting bindings are sorted deterministically by `(precedence ASC, mode=="transversal" ASC, -specificity_score ASC, layer_id ASC, binding_id ASC)`:
     1. ***Lex Superior* (`precedence` `0..100` ascending)**: Lower numeric value holds higher deontic authority (`5` statutory/legal compliance > `10` root engineering baseline > `20` domain/financial > `30` design system > `60` growth/marketing).
     2. **Binding Mode (`"authoritative"` before `"transversal"`)**: Authoritative domain owners precede cross-cutting advisors at the same priority level.
     3. ***Lex Specialis* (`specificity_score` descending)**: Computed from explicit non-wildcard `traits` (`+4` each), non-wildcard `scopes` (`+3`), non-wildcard `architectural_planes` (`+2`), and non-wildcard `target_globs` (`+1`). Equal `(precedence, mode)` ties across distinct layers emit a **`SURFACE_PRECEDENCE_COLLISION`** warning.
   - **Verified Governance Assets (`SURFACE_ASSET_MISSING`), Template Binding Sync (`collect_layer_effective_bindings`) & Adaptive Resolution**: Active template packs declared in `default_stack_templates` (`templates/<name>/template.json`) automatically contribute their `recommended_surface_bindings` (deduplicated by `binding_id`). Every declared `rule_file` and `canonical_template` is verified via `_resolve_safe_path`. Bindings with `mode: "authoritative"` default to `resolution="L2"`, whereas `mode: "transversal"` bindings default to `resolution="L1"` (*Exon Axiom Skeleton*, ~85% token compaction).

---

## 4. Subpackage 4 (`governance/`): Polymorphic Fork Configurator, Authority, Horizon & Promotion Engines

To maintain strict `1:1:1` subpackage-to-specification symmetry across the 4 bounded-domain subpackages of `scripts/dotfiles_mcp/`, the normative specification for Subpackage 4 (`governance/` — `fork_configurator.py`, `workspace_bootstrapper.py`, `promotion_engine.py`, `horizon_engine.py`, `authority_engine.py`, `workflow_engine.py`, `git_governance_engine.py`, `cli_dispatcher.py`, and all 26 CLI subcommands of `scripts/layer-config.sh`) lives in **[`docs/architecture/06_layer_governance_and_promotion_engines.md`](06_layer_governance_and_promotion_engines.md)**.
