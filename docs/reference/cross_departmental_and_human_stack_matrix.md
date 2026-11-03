# Cross-Departmental Composition & `Human-Stack` Matrix (`0..95`)

> **Parent Reference**: [`docs/reference/enterprise_pair_programming_governance.md`](enterprise_pair_programming_governance.md) | **Normative Architecture**: [`docs/architecture/02_antigravity_governance_and_hooks.md`](../architecture/02_antigravity_governance_and_hooks.md) & [`docs/architecture/06_layer_governance_and_promotion_engines.md`](../architecture/06_layer_governance_and_promotion_engines.md)

This reference defines the **7-Axis Multidimensional Taxonomy (`Entity Lineage × Topological Class × Deontic Precedence × Actor RBAC × Physical Pillars × Communication Channels × Progression Scales`)**, the **Perspective Matrix across `Root 0` (Government vs. Enterprise vs. OSS) and Child Departments (`D1..D4`)**, the **Cross-Departmental Contextual Algebra (`0..80`)**, and the **`Human-Spec` / `Human-Stack` Matrix (`85..95`)**.

---

## 0. Canonical 7-Axis Multidimensional Taxonomy & Perspective Matrix (`Root 0` $\rightarrow$ `Child Departments` $\rightarrow$ `Units & Nodes`)

Because `dotfiles-ubuntu` orchestrates organizations, codebases, containers, and human-agent pairing simultaneously, every concept belongs to one of **7 orthogonal dimensions** (with zero overloaded terms):

| Axis # | Orthogonal Dimension (Canonical Name) | Question It Answers | Canonical Values / Enums (`constants.py`) | Disambiguation Rule (What Never to Mix) |
| :--- | :--- | :--- | :--- | :--- |
| **Axis 1** | **Entity & Sovereignty Lineage (`entity_kind` $\times$ `collective_scope` $\times$ `governing_root_id`)** | *What kind of legal/organizational entity is this, who is its sovereign `Root 0`, and is another layer `internal` or `external`?* | `VALID_ENTITY_KINDS`: `public-government` (`collective`, `prec: 1..4`), `enterprise` (`collective`, `prec: 5..84`), `individual` (`individual`, `workstation` / `85..95`), `open-source` (`collective`, upstream appliance).<br/>**Relationship**: `internal` (same `governing_root_id` + `entity_kind`) vs. `external:<entity_kind>` | Never confuse **`entity_kind`** (*nature of the sovereign entity: Government vs. Enterprise vs. Individual vs. OSS*) with **`layer_role`** (*hierarchical rank inside that entity*). Both a Government and an Enterprise have a `Root 0` and child `Departments`. |
| **Axis 2** | **Topological Class: `Layer` vs. `Node` vs. `Bot` vs. `Project` (`topological_class` / `layer_role`)** | *What is this repository or runtime instance functionally within the graph?* | `TOPOLOGICAL_ROLE_CLASSES`:<br/>1. **`governance-layer` (*Normative Layer*)**: `corporate` (`Tier 1 Root 0`: Public Admin `1..2` \| Company `10`), `domain-policy` (`Tier 2A Statutory/Fiduciary Dept`), `department` (`Tier 2B Functional Dept`), `squad` (`Tier 2C Sub-Dept / Operational Unit / Squad`)<br/>2. **`runtime-node` (*Execution/Infra Node*)**: `workstation` (`10`), `service-node` (`60`), `environment-cluster` (`70`)<br/>3. **`ephemeral-sandbox` (*Time-Bounded Bot*)**: `ephemeral-bot` (`15`)<br/>4. **`consumer-workspace` (*Deliverable Repo*)**: `project` (`80`) | **Exact difference between `Layer` and `Node`**:<br/>• A **Governance Layer (`governance-layer`)** defines *deontic laws, templates, RBAC rosters, and `surface_bindings`* across **`Root 0` $\rightarrow$ `Department (1..N recursive)`**.<br/>• A **Runtime Node (`runtime-node`)** is a *physical or virtual execution target* (Ubuntu workstation, Docker container `service-node`, or staging/prod `environment-cluster`) audited via `audit_node_drift` and federating runtime MCPs (`postgres`, `redis`, `voip`). |
| **Axis 3** | **Deontic Precedence (`precedence: 0..100` *Lex Superior*)** | *When multiple layers bind to the same file surface, which rule wins?* | `1..2` Public Administration `Root 0` (`public-gov-root`) $\rightarrow$ `3..4` Public Departments (`dept-justice`, `dept-tax`, `dept-territorial`) $\rightarrow$ `5..9` Enterprise Fiduciary `domain-policy` (Legal/IP `5`, Sec `7`) $\rightarrow$ `10` Corporate `Root 0` (`acme-corp-root`) / `workstation` $\rightarrow$ `15` `ephemeral-bot` $\rightarrow$ `15..40` Functional `department` (Finance `15`, Ops `20`, IT `25`, Brand `30`, Marketing `35`) $\rightarrow$ `40..60` Sub-Department / Unit / `squad` (`50`) $\rightarrow$ `60..80` `service-node` (`60`), `environment-cluster` (`70`), `project` (`80`) $\rightarrow$ `85..95` `Human-Stack` | Lower number = higher authority (`1 < 3 < 5 < 10 < 25 < 50 < 80 < 85`). `Root 0` is always at the top of its entity (`1..2` for Public Admin, `10` for Enterprise). `Human-Stack` (`85..95`) modulates *pedagogical pairing*, never overriding `0..80` laws. |
| **Axis 4** | **Actor RBAC & Overarching Authority (`effective_role`: `5` Roles)** | *Which human or bot email (`git user.email`) is acting, and what can they approve?* | `owner`, `maintainer`, `validator`, `member` (in `layer_authority.roster`) + `consumer` (`5` effective roles).<br/>**`UPSTREAM_HIERARCHICAL_AUTHORITY`**: Parent `owner`/`maintainer` (`prec_parent < prec_child`) inherits authority **only when `relationship_scope == "internal"`**. | Never confuse **`actor_role`** (*person's permission: `owner`, `validator`...*) with **`layer_role`** (*repository rank: `corporate`, `department`...*). |
| **Axis 5** | **Physical Context Pillars on Disk (`Pillar A / B / C / D`) & Template Kinds** | *Where do files physically reside on the workstation and workspace?* | • **`Pillar A` (Global `$HOME`)**: `~/.gemini/config/` (`AGENTS.md`, `hooks.json`, `10` global skills)<br/>• **`Pillar B` (Templates & Subtrees)**: `templates/*` (`core-base`, `business-stack`, `science-stack`, `tech-stack`) + `layers/<id>/`<br/>• **`Pillar C` (Workspace Overlay)**: `<repo>/.agents/` (`rules/layer-<NN>-<id>.md`, `SESSION.md`, `LAYER_LINEAGE.md`)<br/>• **`Pillar D` (Navigable Corpus)**: `README.md` $\rightarrow$ `docs/guides/` $\rightarrow$ `docs/{architecture,reference}/` | Refer to local disk mechanisms as **Context Pillars (`Pillar A..D`)** so they never collide with **Organizational Levels (`Level 1..4`)**. |
| **Axis 6** | **Inter-Layer Communication Channels (`6` Deterministic Protocols)** | *How do layers and nodes communicate vertically, horizontally, and across entities?* | 1. **Downward Template Sync (`make sync`)**: 4 modes (`reconcile`, `accept-upstream`, `keep-local`, `merge`)<br/>2. **Downward Task Directive (`make delegate`)**: 1-hop delivery into `layers/<child>/WORKTASK.md`<br/>3. **Upward Rule Promotion (`make promote`)**: 1-hop PR (`--create-pr`) + OSS agnosticism gate<br/>4. **Bilateral 1-Hop Radar (`make horizon` / `layer_report`)**: 3 buckets (`inbound_from_upstream`, `inbound_from_downstream`, `local_workspace_changes`)<br/>5. **Ephemeral Consultation (`make consult` / `spawn-ephemeral`)**: `rcap1` (`inter-layer` read-only or `intra-layer` with `seal-return`)<br/>6. **$N$-Departmental Consensus (`make env-gate --files`)**: 4 states (`RECONCILED_FLOW`, `ITERATION_REQUIRED`, `ESCALATE_TO_ROOT`, `ESCALATE_INTER_ENTITY_ROOTS`) | Every cross-layer action uses one of these 6 channels; direct cross-layer edits are blocked by `pre_tool_guard.py`. |
| **Axis 7** | **Progression Scales (`rcap1 L0..L3` vs. `Human-Spec L1..L4` vs. `C1..C3` vs. `dev..pro`)** | *Which scale does a shorthand code refer to?* | • **`rcap1` Capsule Resolution**: `L0` (Codon) $\rightarrow$ `L1` (Exon) $\rightarrow$ `L2` (Section) $\rightarrow$ `L3` (Deep Links)<br/>• **`Human-Spec` Maturity**: `domain-<area>:L1` (Explorer) $\rightarrow$ `L2` (Practitioner) $\rightarrow$ `L3` (Architect) $\rightarrow$ `L4` (Principal)<br/>• **Command Consciousness**: `C1` (Auto-reflexive) $\rightarrow$ `C2` (Guided tactical) $\rightarrow$ `C3` (Conscious human-gated)<br/>• **Environment Gates**: `dev` $\rightarrow$ `tst` $\rightarrow$ `pre` $\rightarrow$ `pro` | Always qualify `L0..L3` as **`rcap1` Resolution** and `domain-<area>:L1..L4` as **`Human-Spec` Maturity**. |

### 0.1. Perspective Matrix by Organizational Level (`Root 0` Base Use Cases $\rightarrow$ Child Department Archetypes `D1..D4` $\rightarrow$ Units & Nodes)

| Organizational Level & Archetype | `entity_kind`, `layer_role` & `topological_class` | `precedence` | Core Use Case, Inheritance & Cross-Layer Behavior |
| :--- | :--- | :---: | :--- |
| **Tier 1 (`Root 0` — Case R0-A): Public Administration / Government Root** *(State, Regional, or Municipal Administration)* | `public-government` · `corporate` · `governance-layer` | **`1..2`**<br/>(`public-gov-root`) | • **Internal Child Public Departments (`prec: 3..4`)**: Justice (`dept-justice`), Tax (`dept-tax`), Territorial/Geo (`dept-territorial`), and Environment (`dept-environment`) inherit `entity_kind="public-government"` and `governing_root_id="public-gov-root"` (`relationship_scope: "internal"`). Public `Root 0` holds `UPSTREAM_HIERARCHICAL_AUTHORITY` over its public departments.<br/>• **External Companies / Citizens (`prec: 5..95`)**: Mounted as `external:public-government`. Statutory laws prevail (`1..4 < 10`), and no private `Root 0` can override a public regulatory block (`PUBLIC_REGULATORY_COMPLIANCE_REQUIRED`). |
| **Tier 1 (`Root 0` — Case R0-B): Enterprise / Company Root** *(Company, Law Firm, Hospital, Holding)* | `enterprise` · `corporate` · `governance-layer` | **`10`** | • **Internal Departments & Sub-Departments/Units (`prec: 5..80`)**: Propagates `governing_root_id` (e.g. `acme-corp-root`) across 1 or $N$ hops (`Root 0 -> Dept [-> Sub-Dept/Unit/Squad] -> Project`), arbitrates cross-department blocks (`ESCALATE_TO_ROOT`), and codifies learned rules upstream (`rule_learning_hint`).<br/>• **External Enterprise Partner (`partner-corp-root`)**: Classified as `external:enterprise` (`CROSS_ENTITY_ESCALATION_REQUIRED`). |
| **Tier 1 (`Root 0` — Case R0-C): Open-Source Upstream & Individual Appliance** *(`mtwuser/dotfiles-ubuntu`)* | `open-source` / `individual` · `workstation` · `runtime-node` | **`10`** | • **`oss-readonly-appliance` (`~/dotfiles-ubuntu`)**: Read-only self-syncing workstation baseline (`oss_auto_sync_covered: true`) usable standalone by any individual practitioner (`entity_kind: "individual"`).<br/>• **`oss-dev` (`DOTFILES_DEV_REPO_DIR`)**: Maintainer development repo where universal patterns are enriched and verified (`scan_open_source_agnosticism`). |
| **Tier 2 (`Child Dept` — Case D1): Public Administration Department** *(Justice, Tax, Territorial/Geo, Environment)* | `public-government` · `domain-policy` / `department` · `governance-layer` | **`3..4`** | Direct child of Public Administration `Root 0` (`1..2`). Stores modular `< 465`-line statutes, territorial registries, and administrative procedures in `docs/` using `science-stack/scientific-knowledge-branch`. Queried on demand via `make consult` (`rcap1`) by civil servants or private enterprises. |
| **Tier 2 (`Child Dept` — Case D2): Enterprise Fiduciary / Guardrail Dept** *(Legal/IP, Cybersecurity, Regulatory Compliance)* | `enterprise` · **`domain-policy`** · `governance-layer` | **`5..9`** | **Why `prec: 5..9` (`< 10`) under Enterprise `Root 0` (`10`)**: Fiduciary invariants (GDPR, Patent Novelty, Secret Isolation) must bind all functional departments (`15..40`) and sub-units (`40..80`) via *Lex Superior*, while sharing `governing_root_id="acme-corp-root"` (`internal`) so Executive `Root 0` can arbitrate internal deadlocks (`ESCALATE_TO_ROOT`). |
| **Tier 2 (`Child Dept` — Case D3): Enterprise Functional / Line Dept** *(Finance `15`, Ops `20`, IT `25`, Brand `30`, Marketing `35`)* | `enterprise` · **`department`** · `governance-layer` | **`15..40`** | Applies `business-stack`, `science-stack`, or `tech-stack` across 3 modes: (1) **Pure Domain/Ledger Governance**, (2) **In-Situ Tooling** (`make setup-dev` overlays `technical-base`), and (3) **$N$-Departmental Surface Co-Ownership** (`co_owning_layers` consensus across `Marketing + Brand + IT + Legal`). |
| **Tier 2B (`Recursive Sub-Department / Unit / Squad` — Case D4)** *(e.g. `Root 0 [10] -> Dept [20] -> Sub-Dept / Unit / Squad [40..60]`)* | `enterprise` / `public-government` · `department` or `squad` · `governance-layer` | **`30..60`**<br/>(`50` default for `squad`) | **Why `squad` is a Sub-Department / Unit role (not a separate stack)**: Any department can subdivide into specialized Sub-Departments, Operational Units, Research Labs, or Delivery Squads (`--role department` or `--role squad`) applying `business-stack`, `science-stack`, or `tech-stack` while preserving the ancestor `governing_root_id` across all hops. |
| **Tier 3 (`Project / Case Workspace` vs. `Runtime Nodes`)** | • `project` (`consumer-workspace`)<br/>• `service-node` / `environment-cluster` (`runtime-node`) | **`60..80`**<br/>(`60` node, `70` cluster, `80` project) | • **`project` (`80`, `apply-project`)**: Concrete application, legal case, administrative expediente, or research study repo.<br/>• **`service-node` (`60`) / `environment-cluster` (`70`)**: Live container/server/cluster runtime nodes exposing `audit_node_drift` and `discover_federated_mcps`. |

---

## 1. Cross-Departmental & Multi-Specialty Composition Matrix: LegalTech, Governed Marketing & Transversal Platforms (`VoIP`)

In traditional enterprises, whenever a business or functional department (Legal, Marketing, Finance, Operations) needs to build software, automate workflows, or integrate with another specialty, two structural failures emerge:
1. **The IT Bottleneck (Context Loss)**: Business writes static handoff specs for IT; engineers build technically sound code that inadvertently misses legal, brand, or financial nuances because those domain rules live in separate silos.
2. **Shadow IT (Engineering Drift)**: The business department builds its own scripts, bots, or connectors outside IT; it solves the immediate domain need, but without `1:1:1` architecture, `100%` test coverage, type safety, or corporate security guards.

`dotfiles-ubuntu` eliminates both failure modes by turning organizational departments and technical stacks into a **3-Axis Compositional Matrix ("Contextual Algebra")** where **Google Antigravity** acts as the universal execution surface:

```mermaid
flowchart LR
    subgraph Axis1["Axis 1: Deontic Precedence Order (0..100 Lex Superior)"]
        P5["Legal / IP (5)\nStatutory & Trade-Secret Gates"]
        P10["Corporate Root 0 (10)\nEnterprise Identity & SSoT Ledgers"]
        P15["Finance (15) / Ops (20)\nUnit Economics, HSE & SLAs"]
        P25["Engineering / Tech (25)\n1:1:1 Specs, 100% Tests & Strict Typing"]
        P30["Brand (30) -> Marketing (35)\nVisual Tokens, Tone & Growth"]
        P50["Squad / Project (50..80)\nBounded-Context Implementation"]
        P5 --> P10 --> P15 --> P25 --> P30 --> P50
    end

    subgraph Axis2["Axis 2: 4 Cross-Layer Weaving Mechanisms"]
        W1["A. In-Situ Dev Overlay\n(make setup-dev <-> make sync)"]
        W2["B. Parent-Governed Project\n(--parent-dir <dept> --template <stack>)"]
        W3["C. Horizontal Subtree Mount\n(layer-subtree.sh add layers/<dept>)"]
        W4["D. Ephemeral rcap1 Consult\n(make consult / spawn-ephemeral)"]
    end

    subgraph Axis3["Axis 3: Homogenized Antigravity Experience"]
        AG["Unified Workspace (.agents/)\n• Same commands (/sopen, /review, /continue, /sclose)\n• Same lifecycle (WORKTASK -> verify -> CHANGELOG)\n• Rules woven in exact 0..100 deontic order"]
    end

    Axis1 --> Axis2 --> Axis3
```

1. **Order Defines Authority (*Lex Superior* `0..100`)**:
   - Combining **Legal (`5`) + Tech (`25`)** is not an unordered bag of prompts: because `5 < 25`, `.agents/rules/layer-05-dept-legal.md` takes deontic precedence over `layer-25-dept-tech.md`. The AI agent enforces `100%` unit test coverage and hexagonal architecture (`25`) *in service of* statutory IP and confidentiality invariants (`5`), never allowing a technical shortcut to bypass a legal gate.
2. **Infinite Specialized Profiles, Zero Cognitive Overhead**:
   - Whether the resulting workspace is a *LegalTech MCP Engineer*, a *Governed Growth & Social Automation Specialist*, or a *Transversal VoIP Platform Architect*, the human operator interacts with the exact same Antigravity commands (`/sopen`, `make status`, `make verify`, `/review`, `/sclose`) while `inspect_workspace_status` (`C1 / C2 / C3` command tiers) filters out irrelevant commands.

### 1.1. The 6 Cross-Specialty Enterprise Archetypes

| Enterprise Scenario | Workspace Owner | Woven Rule Chain (`0..100` *Lex Superior*) | 1-Command Activation | Effective Antigravity Profile |
| :--- | :--- | :--- | :--- | :--- |
| **1. Pure Business Governance** *(Policies, Patents, Financial Ledgers)* | `Root 0` (`10`) or `Department` (`5..20`) | `human-core` + `business-base` (`10`) + `templates/<dept>/` (`5..20`) | `bootstrap-workspace` / `make sync` | **Normative & SSoT Ledger Auditor** (`workspace_mode: business`) |
| **2. In-Department Tooling** *(Scripts/validators inside a business repo)* | `Department` (`Legal`, `Finance`, `Ops`) | `<dept>` (`5..20`) + `business-base` (`10`) + **`technical-base` (`25`, temporary)** | `make setup-dev` *(reverts to `business` via `make sync`)* | **In-Situ Domain Automation Engineer** (`workspace_mode: hybrid`) |
| **3. Department-Owned Tech Product** *(e.g., **LegalTech Patent/Contract MCP**)* | `Legal` (`5`) or Embedded Legal Squad | **`Legal` (`5`)** $\rightarrow$ `Root 0` (`10`) $\rightarrow$ **`Tech` + `FastAPI` (`25..50`)** | `apply-project <app> --parent-dir <dept> --template <stack>` | **Software Architect Subordinated to Department Law** (`hybrid`) |
| **4. Multi-Departmental Intersection** *(e.g., **Marketing + Social Media Hub**)* | `Marketing` / `Growth` Squad (`35`) | **`Legal/GDPR` (`5`)** $\rightarrow$ `Root 0` (`10`) $\rightarrow$ **`Tech` (`25`)** $\rightarrow$ **`Brand` (`30`)** $\rightarrow$ **`Marketing` (`35`)** | `--parent-dir dept-marketing` + `layer-subtree.sh add` (`legal`, `brand`) | **Full-Stack Growth Engineer Governed by Legal, Brand & Security** |
| **5. Transversal Enterprise Platform** *(e.g., **Company-Wide `VoIP` Service**)* | Platform `service-node` / `squad` (`25`) | **Inward**: `Legal` (`5`) $\rightarrow$ `Root 0` (`10`) $\rightarrow$ `Ops` (`20`) $\rightarrow$ `Tech/VoIP` (`25`)<br/>**Outward**: Exports `templates/voip-pack` + `federated_mcps` | Consumers mount `layers/voip-platform` or apply `--template voip-pack` | **Critical Infrastructure Builder (inward) / Governed Service Provider (outward)** |
| **6. Punctual Cross-Departmental Audit** *(e.g., Design checks Patent Gate with Legal)* | Any consumer workspace | Active workspace + **Ephemeral `rcap1` Capsule (`L0..L2`, `kr: true`)** | `make consult LAYER=dept-legal QUERY="..."` | **Zero-Residue Read-Only Inter-Departmental Advisor** (`inter-layer`) |

---

### 1.2. Concrete Walkthroughs of the 3 Cross-Specialty Cases

#### Case A — When the Legal Department Builds Technology (e.g., a LegalTech Patent & Contract Auditor MCP)

Suppose the **Legal & IP Department (`dept-legal-ip`, `precedence: 5`)** needs a custom Model Context Protocol (MCP) server or microservice to audit supplier contracts and patent claims against `corporate/` ledgers. The enterprise can execute this in two ways depending on team structure:

- **Option A1 — Embedded Technical Development Under Legal (`--parent-dir` or `make setup-dev`)**:
  - A technical specialist working directly for Legal scaffolds `legal-contract-mcp/` governed by `dept-legal-ip`:
    ```bash
    ./scripts/layer-config.sh apply-project ~/Projects/legal-contract-mcp \
      --parent-dir ~/Projects/dept-legal-ip \
      --template technical-base,fastapi-hexagonal
    ```
  - *(Or, if authoring automation scripts directly inside `~/Projects/dept-legal-ip`, runs `make setup-dev` to overlay `technical-base` onto `business-base` + `dept-legal-ip`, and `make sync` when finished).*
  - **Resulting Agent Behavior**: Antigravity enforces `mypy --strict`, `ruff`, hexagonal ports/adapters, and `100.00%` isolated unit branch coverage from `technical-base` (`25`), while `dept-legal-ip` (`5`) acts as supreme law — blocking any tool output or test fixture from exposing unpatented inventions (*World Novelty Gate*) or trade secrets (`<TS-ID>`) outside sealed `rcap1` (`kr: true`) capsules.
- **Option A2 — Delegated to the Engineering Department (`dept-tech`) with Legal Mounted**:
  - Legal delegates the build to Engineering via `./scripts/layer-config.sh delegate-to-child ~/Projects/corporate-root --to-child dept-tech --task "Build Patent Audit MCP" --ticket LEG-2026-009`.
  - The engineering squad mounts `layers/dept-legal-ip/` (`./scripts/layer-subtree.sh add dept-legal-ip <url>`). Because `dept-legal-ip` carries `precedence: 5` and `dept-tech` carries `precedence: 25`, `resolve_surface_governance` enforces the exact same `Legal (5) > Corporate (10) > Tech (25)` hierarchy.

#### Case B — When Marketing Connects to Social Media (Multi-Departmental Intersection)

Suppose **Marketing (`dept-marketing`, `precedence: 35`)** wants to build an automated omnichannel campaign engine connected to LinkedIn, X, and Instagram APIs (`marketing-social-hub/`). In a governed enterprise, a social media automation tool touches **four distinct specialties simultaneously**:
1. **Legal & Compliance (`precedence: 5`)**: Enforces GDPR privacy, embargo dates (*World Novelty Gate*), and **Zero-Greenwashing** (every sustainability or unit-economics claim in a post must cite an audited `Batch #NNN` ledger in `corporate/`).
2. **Corporate Root 0 (`precedence: 10`)**: Enforces secret isolation and executive crisis SLAs (`P0 < 1h`).
3. **Engineering / Tech (`precedence: 25`)**: Enforces OAuth token security, idempotent retry queues, rate-limiting, and `100%` `AAA` unit test coverage.
4. **Brand & Design (`precedence: 30`)**: Locks corporate casing, phonetic standards, color contrast (`WCAG >= 4.5:1`), and visual tokens so Marketing (`35`) cannot alter brand identity.
5. **Marketing (`precedence: 35`)**: Defines campaign hooks, audience segmentation, UTM attribution, and posting cadences.

- **How It Is Configured**:
  ```bash
  # Inside dept-marketing (or the marketing-social-hub squad fork):
  ./scripts/layer-subtree.sh add dept-legal ~/Projects/dept-legal-ip master
  ./scripts/layer-subtree.sh add dept-brand ~/Projects/dept-brand-design master
  ./scripts/layer-config.sh apply-project ~/Projects/marketing-social-hub \
    --parent-dir ~/Projects/dept-marketing \
    --template technical-base,fastapi-hexagonal \
    --layers all
  ```
- **Resulting Agent Behavior**: A single developer or technical marketer in Antigravity operates with all five layers woven in `.agents/rules/` (`layer-05-dept-legal.md`, `layer-10-root.md`, `layer-30-dept-brand.md`, `layer-35-dept-marketing.md`, `technical-base.md`, `fastapi-hexagonal.md`). Any code or campaign template generated by the AI automatically satisfies Legal, Brand, Security, and Growth constraints in a single pass.

#### Case C — When a Service Is Transversal to the Entire Company (e.g., Enterprise `VoIP` / Unified Communications)

Suppose the organization operates a transversal **`VoIP` & Unified Communications Platform (`voip-platform`)** used across Customer Support, Sales/Marketing, Legal counsel lines, and Executive communications. A transversal platform has a **dual inward/outward architecture**:

1. **Inward Perspective (Building & Operating the `VoIP` Core)**:
   - `voip-platform` is bootstrapped as a `service-node` (or platform `squad`) at `precedence: 25` with `technical-base` + `fastapi-hexagonal`, mounting **`dept-legal` (`5`)** (telephony recording consent laws, wiretap compliance, audio retention TTLs) and **`dept-ops` (`20`)** (`< 1h` P0 incident SLA, emergency failover routing).
   - It declares its runtime MCP server (`voip-sip-controller`) under `federated_mcps` in `system/mcp-layer.json` with explicit `required_guardrails` (e.g., *"Never initiate call recording or transcript export without a verified consent token; `pro` environment restricted to read-only telemetry"*), and packages a reusable client template at `templates/voip-client-pack/`.
2. **Outward Perspective (Consuming `VoIP` Across Any Department or Squad)**:
   - Whenever **Customer Support**, **Sales/Marketing**, or **Legal** builds a workspace that integrates voice calls or AI voice agents, they mount `layers/voip-platform/` (or run `apply-project --template voip-client-pack`).
   - Their Antigravity agents immediately discover the `voip-sip-controller` MCP via `discover_federated_mcps(layer="all")` **pre-loaded with the combined `effective_guardrails` of Legal (`5`) + Corporate (`10`) + Ops (`20`) + VoIP (`25`)**, guaranteeing uniform compliance across every department that touches telephony.

### 1.3. Deterministic $N$-Departmental Consensus (`3+` Layers), Mutual Entity Identification (`Internal` vs `External`) & `Root 0` Rule-Learning Loop

When a deliverable intersects **3 or more departments** (for example, an omnichannel campaign `campaigns/q4.html` co-owned by **`Marketing` (`25`) + `Legal` (`5`) + `IT` (`30`)** under `acme-root`), or crosses **external organizational boundaries** (such as a Public Government administration `gov-es-aepd` at `precedence: 2` or an external enterprise partner `partner-dept-sec` governed by `partner-root`), `match_authoritative_surface_bindings` (`co_owning_layers`) and `evaluate_multilayer_surface_consensus` (`make env-gate`) enforce four deterministic states:

| Consensus State (`consensus_status`) | Trigger Condition Across $N$ Co-Owning Layers | Relationship Scope (`Internal` vs `External`) | Deterministic Workflow & `Root 0` Rule-Learning Loop |
| :--- | :--- | :--- | :--- |
| **`1. RECONCILED_FLOW`** *(Frictionless / Automated)* | All $N$ co-owning layers (`Marketing`, `Legal`, `IT`) are satisfied via actor role, internal `Root 0` overarching authority, or `APPROVED` decision / codified rule. | `internal` or `external` | **Proceeds directly to `pre` / `pro`** (`allowed: true`). |
| **`2. ITERATION_REQUIRED`** *(Constructive Divergence)* | Any co-owning layer records `REJECTED` or `DEFERRED` (`INTER_DEPT_ITERATION_REQUIRED`), or has not yet signed off (`PENDING` $\rightarrow$ `SURFACE_AUTHORITY_REQUIRED`). | `internal` or `external` | **Iterate on the same task branch in `dev`/`tst`**: apply the requested domain adjustments (e.g., Legal's GDPR opt-in clause) and re-validate in `pre`. |
| **`3. ESCALATE_TO_ROOT`** *(Internal Cross-Departmental Deadlock)* | An internal department (`relationship_scope: "internal"`) records `BLOCKED` (`CROSS_DEPT_ESCALATION_TO_ROOT_REQUIRED`). | **`internal`** *(shares `governing_root_id`, e.g., `acme-root`)* | **Halts `pro` and escalates 1-hop upward to `Root 0` (`governing_root_id`)** for cross-CO arbitration. Once `Root 0` resolves the dispute, it codifies the learned criterion upstream (`rule_learning_hint`: `promote-from-project --to-layer <root> --create-pr`) so future recurring cases become automatic **`RECONCILED_FLOW`**. |
| **`4. ESCALATE_INTER_ENTITY_ROOTS`** *(External Statutory or Partner Block)* | An external layer (`relationship_scope: "external"`) records `BLOCKED`. | **`external:public-government`** (`1..4`), **`external:enterprise`** (other company's `Root 0`), **`external:individual`** (`85..95`) | **Local `Root 0` cannot override an external entity (`hierarchical_authority_granted: false`)**:<br/>• `external:public-government` $\rightarrow$ `PUBLIC_REGULATORY_COMPLIANCE_REQUIRED` (must satisfy statutory law).<br/>• `external:enterprise` $\rightarrow$ `CROSS_ENTITY_ESCALATION_REQUIRED` (requires inter-entity alignment between local `Root 0` and external `Root 0`). |

---

## 2. The `Human-Spec` & `Human-Stack` Matrix: Fluid Multidisciplinary Profiles & Maturity Adaptation

While **Axis 1 (Deontic Precedence `0..80`)** defines *which organizational laws govern the repository* and **Axis 2 (Stack Templates)** defines *which technical or operational architecture applies*, modern professionals are rarely single-track specialists. To guide each human operator with zero overengineering, `dotfiles-ubuntu` distinguishes strictly between an atomic **`Human-Spec`** and a composed **`Human-Stack`** at **`precedence: 85..95`**:

$$\text{Human-Stack (Composed Person/Role Profile)} = \text{Human-Spec}_1 + \text{Human-Spec}_2 + \dots + \text{Human-Spec}_n$$

| Concept | Exact Definition & Granularity | Software Analogy | Concrete Examples | Where It Lives & Evolves |
| :--- | :--- | :--- | :--- | :--- |
| **`science-stack` / `business-stack` / `tech-stack`** *(Objective Discipline & Methodology)* | **Defines the objective methodology, verification rules, and knowledge taxonomy (`Trunk -> Branch -> Specialty`) of the field** (`precedence: 25..80`). Independent of who the user is. | A domain framework & reference library (`scientific-knowledge-branch`, `corporate-ops-ledger`, `fastapi-hexagonal`). | • `science-stack/scientific-knowledge-branch` *(Epistemic rigor, modular `< 465`-line `docs/` statutory/scientific corpus, `make consult`)*<br/>• `tech-stack/fastapi-hexagonal` | Lives in `templates/{science-stack,business-stack,tech-stack}/`. Applied to workspaces via `apply-project` or `bootstrap-workspace`. |
| **`Human-Spec`** *(Atomic Capability Facet)* | **A single modular building block** describing one domain maturity level, one cross-discipline bridge, one cognitive/soft skill, or one temporal session role (`precedence: 85..95`). | A single library or tool facet (`domain-legal:L3`, `domain-python:L1`). | • `domain-legal:L3` *(Legal Expert)*<br/>• `domain-python:L1` *(Python Explorer)*<br/>• `bridge-tech-for-business`<br/>• `soft-socratic-coach` | Lives in the **Living Catalog** (`docs/reference/` or `templates/`). Refined and shared across companies via `/enrich` + `make promote`. |
| **`Human-Stack`** *(Contextual Seniority & Pairing Profile)* | **The personalized combination of $N$ `Human-Specs`** representing a real person's contextual maturity in the active workspace (`precedence: 85..95`). Shifts when the same person changes workspace context. | A personalized IDE/pairing profile for the current workspace context. | **Same Lawyer in two workspaces**:<br/>• Civil Law Case: `domain-civil-law:L4` *(Direct peer)*<br/>• Tax/Python Tool: `domain-tax:L1 + domain-python:L1 + soft-socratic-coach` *(Didactic guide)* | Declared **optionally** in `.agents/SESSION.md` (personal), `.agents/LAYER_LINEAGE.md` / `README.md` (team), or in chat. Shifts fluidly by context and as mastery grows (`L1 -> L2`). |

- **Invariance of Quality (`0..80` *Lex Superior*)**: A `Human-Stack` (`85..95`) **never lowers statutory, security, architectural, or `100%` test-coverage gates (`0..80`)**. Whether paired with an `L1` newcomer or an `L4` Principal, the deliverable must pass the exact same verification suite (`make verify`).
- **Fluid Cognitive Adaptation (`85..95`)**: What changes is **how the AI pairs with the human** — adjusting explanation depth, cross-discipline vocabulary bridges, Socratic coaching, and review pacing to match the operator's active `Human-Stack`.

```mermaid
flowchart LR
    subgraph Laws["System Invariants (Precedence 0..80 — Non-Negotiable)"]
        O1["Organizational Laws: Legal (5) -> Root 0 (10) -> Tech (25) -> Brand (30)"]
        O2["Execution Templates: human-core / technical-base / business-base / fastapi"]
    end

    subgraph Specs["1. Living Catalog of Atomic Human-Specs (Precedence 85..95)"]
        S1["A. Domain Maturity: domain-<area>:L1..L4"]
        S2["B. Hard-Skill Bridges: bridge-tech-for-business · bridge-business-for-tech"]
        S3["C. Soft/Cognitive Style: soft-socratic-coach · soft-red-team-critic · soft-deep-flow"]
        S4["D. Temporal Session Hat: hat-onboarding-explorer · hat-feature-builder · hat-forensic-auditor"]
    end

    subgraph Stack["2. Composed Human-Stack (100% Optional — 4 Graduated Modes)"]
        HS["Case 0: Omitted (Default) | Case 1: In-Chat Spec | Case 2: Personal SESSION.md | Case 3: Team Blueprint\nEvolves organically via /learn -> /enrich -> make promote"]
    end

    Laws --> HS
    Specs --> HS
```

### 2.1. The 4 Categories of Atomic `Human-Specs` (The Building Blocks)

| `Human-Spec` Category | Atomic Catalog Identifiers (`precedence: 85..95`) | How Each `Human-Spec` Modulates Agent Pairing Behavior |
| :--- | :--- | :--- |
| **A. Asymmetric Domain Maturity (`domain-<area>:L1..L4`)** | • `domain-<area>:L1` *(Guided Explorer / Onboarding)*<br/>• `domain-<area>:L2` *(Autonomous Practitioner)*<br/>• `domain-<area>:L3` *(Systems Architect / Domain Expert)*<br/>• `domain-<area>:L4` *(Principal / Cross-Domain Strategist)* | In domains tagged **`L1`**, the agent explains the architectural *why* before edits, links to `docs/guides/`, and walks through the 5-link ripple chain step by step. In domains tagged **`L3/L4`**, it uses terse 4-channel digests, boundary trade-offs (`N vs N±1`), and zero condescension. |
| **B. Cross-Discipline Bridges (`bridge-*`)** | • `bridge-tech-for-business`<br/>• `bridge-business-for-tech`<br/>• `bridge-legal-engineering`<br/>• `bridge-growth-engineering` | Translates concepts across guilds: explains hexagonal ports, `AAA` tests, and Git gates to business specialists as *enforceable contract clauses and audit ledgers*, or translates EBITDA, CAPEX/OPEX, and IP novelty rules to engineers as *state-machine invariants*. |
| **C. Cognitive & Soft-Skill Style (`soft-*`)** | • `soft-socratic-coach` *(Active learning)*<br/>• `soft-red-team-critic` *(Assumption challenger)*<br/>• `soft-executive-storyteller` *(Board/ROI framing)*<br/>• `soft-deep-flow` *(Maximum velocity, minimal prose)* | Modulates collaboration dynamics: prompts the user to spot edge cases (`socratic-coach`), stress-tests architectural or commercial premises (`red-team-critic`), or packages technical diffs into executive impact summaries (`executive-storyteller`). |
| **D. Temporal Session Hat (`hat-*`)** | • `hat-onboarding-explorer` · `hat-feature-builder`<br/>• `hat-forensic-auditor` · `hat-cross-dept-integrator` | Allows the same person to shift modes fluidly within a single day (e.g., *Explorer* when entering an unfamiliar module in the morning, *Feature Builder* at midday, and *Forensic Auditor* during pre-release review). |

### 2.2. How & Where to Apply `Human-Specs` and `Human-Stacks` (`4` Optional Graduated Use Cases)

Adoption is **100% optional** and follows a clean specificity hierarchy (**`In-Chat Override -> Personal .agents/SESSION.md -> Team Blueprint -> Default`**):

| Use Case & Adoption Level | Mandatory? | Where It Is Declared | Who Defines It & How It Works in Practice |
| :--- | :---: | :--- | :--- |
| **Case 0 — Default Standard Operation *(Nothing Declared)*** | **No (`100% Optional`)** | Left blank (`[Optional: leave blank for default...]`). | **Nobody**: When omitted, the agent operates with standard `human-core` + active layer/stack rules (`0..80`) with zero extra prompts or ceremony. |
| **Case 1 — Punctual In-Chat Activation *(Single `Human-Spec` on the Fly)*** | Optional | **Directly in the chat prompt** for a single task. | **Any user on demand**: A Senior Engineer (`L3`) reviewing a supplier contract says in chat: *"Apply `bridge-business-for-tech` and `soft-red-team-critic` to audit this clause."* Active only for that turn/task. |
| **Case 2 — Personal Evolving `Human-Stack` *(Individual Fluidity)*** | Optional | **`.agents/SESSION.md`** *(local to the user's machine, read by `/sopen`, **zero `make diff` drift** on shared team files)*. | **Each individual practitioner**: A Marketing Director (`domain-marketing:L3`) learning Python automation (`domain-python:L1 + bridge-tech-for-business + soft-socratic-coach`) records their stack in `SESSION.md` and upgrades `domain-python:L1 -> L2` months later as mastery grows. |
| **Case 3 — Corporate / Squad Onboarding Directive *(Role Archetype)*** | Optional | **`README.md`** *(Department / Squad layer)* or **`.agents/LAYER_LINEAGE.md`** *(Project workspace)*. | **Layer Owner or Squad Lead**: Pre-fills a recommended `Human-Stack` for a role (e.g., *Squad Onboarding Engineer*: `domain-stack:L1 \| bridge-business-for-tech \| soft-socratic-coach \| hat-onboarding-explorer`) so new hires receive guided architectural mentorship automatically on `/sopen`. |

### 2.3. The Full Deontic Spectrum (`1..95`) & `$HOME` vs. `Workspace` Across Public Administration, Enterprise, Science & Individual Work

By separating **`$HOME` (`~/dotfiles-ubuntu` — Organizational Membership)** from **`Workspace` (`<repo>/.agents/` — Active Case + Crossed `layers/*` + Specialization Stack + Contextual `Human-Stack`)**, the exact same governance engine scales from a national public administration down to a single freelancer:

| Persona & Context | `$HOME` (`~/dotfiles-ubuntu`) | Active `Workspace` & Mounted `layers/*` (`1..80`) | Specialization Stack & Contextual `Human-Stack` (`85..95`) | Functional Outcome in Antigravity |
| :--- | :--- | :--- | :--- | :--- |
| **1. Public Administration Chain** *(Public `Root 0` $\rightarrow$ Public Dept $\rightarrow$ Civil Servant)* | • Public Admin: `human-core`<br/>• Dept Maintainer: `public-gov-root` (`1`)<br/>• Civil Servant: `dept-justice` (`3`) | • Public `Root 0`: `public-gov-root` (`1..2`)<br/>• Public Dept: `dept-justice` (`3`) & `dept-territorial` (`4`, statutes in `docs/` `< 465` lines)<br/>• Civil Servant: `expediente-2026-042/` (`80`) | `business-base` + `science-stack/scientific-knowledge-branch` (`domain-admin-law:L3`) | Constitutional `Root 0` (`1..2`), justice (`3`), and territorial (`4`) statutes govern every administrative resolution; laws in `docs/` are queried on demand (`make consult`) with `0` idle token bloat. |
| **2. Law Firm / Enterprise Member Crossing Public Admin** | `empresa-dept-legal` (`15`, inheriting `empresa-root` at `10`) | Client filing `recurso-fiscal-cliente-x/` crossing `layers/dept-justice` (`3`) + `layers/dept-tax` (`4`) | `science-stack/scientific-knowledge-branch` + `business-stack/corporate-ops-ledger` (`domain-civil-law:L4 + domain-tax-law:L2`) | Public statutes (`3..4`) automatically override internal company policies (`10..15`) via *Lex Superior*; agent operates as a peer in civil law (`L4`) and explains recent tax changes step-by-step (`L2`). |
| **3. Enterprise Tech Lead (`L4`) vs. Junior Developer (`L1`)** | Both stow `empresa-dept-tech` (`25`, inheriting `empresa-root` at `10`) | Both open `checkout-service/` (`50..80`) | `tech-stack/fastapi-hexagonal`; Lead sets `domain-python:L4`, Junior sets `domain-python:L1 + soft-socratic-coach` in `.agents/SESSION.md` | Identical `100%` branch coverage and hexagonal gates (`0..80`); Lead gets rapid 4-channel execution (`L4`), Junior gets Socratic architectural mentorship (`L1`). |
| **4. Specialist Shifting Contexts** *(Same Person, Different Workspace)* | `dept-bio-lab` (`20`) or `dept-legal` (`15`) | • **Workspace A**: Primary clinical/legal research repo<br/>• **Workspace B**: Cross-cutting tax grant or Python automation (`make setup-dev`) | • **Workspace A**: `science-stack` (`domain-biotech:L4`)<br/>• **Workspace B**: `tech-stack` (`domain-python:L1 + bridge-tech-for-business`) | Demonstrates why `science-stack` (objective field) and `Human-Stack` (contextual seniority) are orthogonal: the same specialist is `L4` in their core science and `L1` when crossing into Python or tax law. |
| **5. Individual Professional** | Default `human-core` (`workstation-sync.sh --setup`) | Personal or client project (`apply-project`) | Any `science-stack`, `business-stack`, or `tech-stack` + optional `Human-Stack` in `.agents/SESSION.md` | Enjoys the full `human-core` task-branch lifecycle (`make status`, `make task`, `/review`, `/sclose`) with zero corporate setup ceremony. |
