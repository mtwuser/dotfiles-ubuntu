---
name: full-audit
description: "Execute a deep, structured, multi-pass and multi-perspective repository audit (Conceptual 4-Perspective Matrix -> Pragmatic Technical & Stack Currency -> 1:1:1 Human-Agent Test Symbiosis -> Governance Spillover Gate into roadmaps/WORKROAD/WORKTASK/BACKLOG)."
---

# Full Repository Audit — `/full-audit`

> **Purpose**: Execute an exhaustive, zero-myopia, multi-perspective audit of the active repository without hallucinations, half-finished findings, or context loss.
> Combines a **Conceptual & Normative Pass (4-Perspective Lifecycle Matrix)** with a **Pragmatic Technical & `1:1:1` Human-Agent Test Comprehension Pass**, and automatically routes large finding sets into the repository's governance pipeline (`roadmaps/` $\rightarrow$ `WORKROAD.md` $\rightarrow$ `WORKTASK.md` / `BACKLOG.md`).

---

## Core Audit Principles

1. **Repository & Stack Agnosticism**: Never assume rules or counts from another repository. Always discover the active repository's stack, manifests, and rule hierarchy first.
2. **4-Scope Rule Separation**:
   - **Scope 1 (`$HOME` Read-Only Workstation Base)**: Universal cognitive, session, and commit governance (`human-core`).
   - **Scope 2 (General Technical Baseline — `technical-base`)**: Stack-general software engineering, `1:1:1` traceability, refactoring, and testing invariants applicable to any language or framework.
   - **Scope 3 (Stack-Specific Template Pack)**: Language- and framework-specific conventions (e.g., Python 3.14 PEP 695, FastAPI/HTMX, TypeScript/React, Rust, Go).
   - **Scope 4 (Repository-Local Specifications & Gates)**: Architecture specs (`docs/architecture/`), domain invariants, and verification gates specific to the active repository.
3. **Modern Stack Currency & Zero-Backward Law**: Always target the latest stable language/framework idioms declared by the project; flag and eliminate legacy shims, aliases, and deprecated fallbacks.
4. **4-Stage Responsibility Pipeline (`Review -> Full-Audit -> Architecture-Review -> Refactoring` & `OSS-Contribute`)**:
   - **Stage 1 — `/review` (`C1` Tactical Delta Gate)**: Fast incremental audit of the active session/git delta + 1-hop coupled neighbors.
   - **Stage 2 — `/full-audit` (This Skill — `C2` Closed-World Gap & Cluster Detection)**: Audits 100% of the repository across **5 Deterministic Probes (`Probe A..E`)**, separating **Sub-pass 1A (Pure Conceptual & Taxonomic Doc Isomorphism)** from **Sub-pass 1B (Persona Journeys)** and **Pass 2 (`Relational Cluster Mass` $M_{\text{cluster}}$ + Technical Architecture)** toward `Regime 0 (0 findings)`.
   - **Stage 3 — `architecture-review` (Domain Taxonomy & Cluster Boundary Design)**: Activated when `/full-audit` flags taxonomic drift or a `[CLUSTER_CONSOLIDATION_CANDIDATE]` ($M_{\text{cluster}} \ge 1{,}200$ across $\ge 2$ modules $\ge 385$ lines or cross-engine `_private` imports) to design the target `1:1:1` module boundaries and spec tables before moving code.
   - **Stage 4 — `refactoring` (`1:1:1` Execution & Pruning) & `oss-contribute` (`C3` Substrate)**: `refactoring` executes the physical module extraction/consolidation with `100%` isolated unit coverage; `oss-contribute` runs post-`Regime 0` for empirical hot-path profiling, `PEP 7` C-accelerators, and external `OSS-to-OSS` PRs.
5. **Execution Block Until Approval**: Present structured findings and the Pre-Edit Scope Blueprint first; never mutate repository files before explicit user confirmation.

---

## Audit Cadence Strategy (`C0 -> C3`): 1 Matrix of 4 Dimensions $\times$ 2 Radii of Action

Both `/review` and `/full-audit` evaluate the exact same **4 Canonical Dimensions (`1. docs`, `2. arch`, `3. 1:1:1`, `4. layer`)**, eliminating redundant sub-commands by separating strictly along **Radius of Action**:

| Tier & Cadence | Trigger / Moment | Command / Mechanism | Radius of Action & Analytical Focus |
| :--- | :--- | :--- | :--- |
| **`C0` — Reflexive (Per-Edit)** | Every file edit / turn end (`PostToolUse`, `PostInvocation`, `Stop`) | Lifecycle Hooks (`post_edit_format.py`, `post_invocation_lint.py`, `stop_verify_tests.py`) | **Single-File Radius (`< 1s`, `0` LLM tokens)**: Enforces `< 465` lines, `Specification:` header, AAA test markers, token budgets ($\le 18\text{ KB}$ / $80\text{ KB}$), and affected unit tests on modified files. |
| **`C1` — Tactical (Incremental / Target)** | Mid-session after completing a task, or when inspecting one path/dimension | **`/review [path \| docs \| arch \| 1:1:1 \| layer]`** | **Delta or Single-Dimension Radius (`~5–15s`)**: `/review` (no args) audits only the active session/git delta; `/review <target>` audits one module, layer, or dimension (`docs`, `arch`, `1:1:1`, `layer`). |
| **`C2` — Convergent (Closed-World Gate)** | Milestone closure or pre-release certification before `/release` | **`/full-audit`** | **100% Repository Universe Radius**: Runs all **5 Closed-World Deterministic Probes (`Probe A..E`)** and walks **Pass 1 (`docs`: `1A` Conceptual/Taxonomic + `1B` Persona), Pass 2 (`arch` + `Cluster Mass`), Pass 3 (`1:1:1`), and Pass 4 (`Spillover/Convergence`)** across 100% of the repo toward **`Regime 0 (0 findings)`**. |
| **`C3` — Evolutionary (Post-`Regime 0`)** | Strictly **after** `Regime 0` is certified (`0` compliance gaps) | **`/enrich`** (`C -> B -> A`), **`/architecture-review` + `refactoring`**, **`oss-contribute`** (`Tier -1`) | **Cross-Layer & External Radius**: Upward rule promotion (`/enrich`), orthogonal architectural redesign (`/architecture-review`), or conscious C-substrate profiling & external `OSS-to-OSS` upstream PRs (`oss-contribute`). |

---

## Phase 0 — Closed-World Context, Stack & Deterministic Probe Discovery

// delegate: flash

To provide **human-grade certainty through closed-world elimination** (never heuristic attention-window sampling), Phase 0 MUST enumerate and probe the entire repository universe upfront:

1. **Discover Stack, Operating State, Workspace Mode & Toolchain**:
   - Run `make status` (or `./scripts/layer-config.sh status`) and inspect project manifests (`system/mcp-layer.json`, `pyproject.toml`, `package.json`, `Cargo.toml`, `go.mod`, `Makefile`, `Dockerfile`, CI workflows) to determine `operating_state` (`"oss-readonly-appliance"`, `"oss-dev"`, `"corporate-root"`, `"domain-policy"`, `"department"`, `"squad"`, or `"project"`), `workspace_mode` (`"business"`, `"technical"`, or `"hybrid"`), `command_tiers`, target language versions, linters, type-checkers, and test runners.
2. **Classify Active Rules by Scope & Enumerate 100% of the File Universe**:
   - Read `.agents/rules/*.md`, `.agents/LAYER_LINEAGE.md`, and `docs/architecture/*.md` (or `corporate/**/*.md`).
   - Enumerate all root community/governance files (`README.md`, `CONTRIBUTING.md`, `SECURITY.md`, `ACCESSIBILITY.md`, `CODE_OF_CONDUCT.md`, `CHANGELOG.md`), `docs/**`, `templates/**`, `scripts/**`, and `tests/**` so zero files are omitted from terminology, link, or parity scans.
   - Separate **generic inherited rules** (`technical-base`, `business-base`) from **stack-specific rules** (`business-stack/*`, `science-stack/*`, `tech-stack/*`) and **repository-local specs**; flag any leak where repository-local counts or single-stack literals contaminate a generic rule or skill.
3. **Execute the 5 Closed-World Deterministic Probes (`Probe A..E`)**:
   - **Probe A — Live Verification & Host Audit Suite**: Run `make verify` (or `make doctor` / `make diff`) **AND** live workstation/environment audit scripts (`NO_COLOR=1 ./audit.sh`, `./scripts/audit-global-config.sh` when applicable) from the active workspace to catch cross-clone or environment-boundary false positives immediately.
   - **Probe B — Bidirectional AST Symbol, Constant & Docstring Graph**: Parse all production and test modules via AST to verify: (i) 100% explicit return annotations and 100% docstrings on public functions/methods (`not name.startswith("_") or name == "__init__"`), (ii) zero `.update(k=v)` keyword packing or raw integer slices (`> 2`), and (iii) **bidirectional constant wiring** (every constant in `constants.py` / `catalogs.py` is referenced by a consumer module or test, and every policy tuple is disjoint/consistent).
   - **Probe C — 5-Link Change-Ripple & Flag-Signature Matrix**: For every CLI subcommand, Makefile target, or engine capability, verify parity across all **5 ripple links** (`1. Engine Function <-> 2. CLI Parser <-> 3. Makefile Recipe / Hook <-> 4. Normative Spec Table (docs/architecture/01..NN) <-> 5. Root/Guide Docs & Parity Tests`), including **Parameter & Optional Flag Signature Parity between Link 2 (`CLI Parser`) and Link 3 (`Makefile Recipe`)** so Makefile wrappers never silently drop optional CLI flags.
   - **Probe D — `1:1:1` Spec Table Completeness**: Verify that every specification in `docs/architecture/01..NN` (`< 465` lines) contains an explicit `1:1:1` traceability table and that every referenced source and test file exists on disk.
   - **Probe E — Relational Cluster Mass ($M_{\text{cluster}}$) & Cross-Module Coupling Graph**: Parse the intra-package AST import graph (excluding declarative `constants.py` / `catalogs.py`) to compute each module's individual load $L(f)$, its coupled neighbor set $G$, its **Relational Cluster Mass $M_{\text{cluster}}(G) = L(f) + \sum_{g \in G} L(g)$**, and its cross-module `_private` symbol imports. Flag a **`[CLUSTER_CONSOLIDATION_CANDIDATE]`** whenever: (i) a peer `*_engine.py` module imports `_private` helpers from another `*_engine.py` module (instead of `*_helpers.py`), or (ii) $\ge 2$ coupled modules in $G$ both exceed the **Soft Compression Threshold ($L(f) \ge 385$ lines)** with $M_{\text{cluster}}(G) \ge 1{,}200$ lines, signaling a latent sub-domain that should be consolidated into a dedicated `1:1:1` module.

---

## Phase 1 — Pass 1: Conceptual Coherence, Human Persona Journeys & 4-Perspective Lifecycle Matrix

Evaluate the repository along **two orthogonal axes**:
1. **Horizontal Technical Lifecycle Matrix (4 Perspectives)** — how every rule or component behaves across setup, runtime, testing, and federation.
2. **Vertical Human Persona Journeys (`Human <-> AI <-> Technology` Unity)** — how real human archetypes experience the repository from entry point (`README.md` / CLI) to day-2 operations.

### 1.1 Horizontal 4-Perspective Lifecycle Matrix

| Perspective | Question to Verify Across Every Flow |
| :--- | :--- |
| **1. Setup / Bootstrap / Scaffolding** | Do initializers, templates, manifests, and environment setup scripts materialize files and paths in the exact locations expected at runtime? |
| **2. Runtime / Execution / Skills / Hooks** | Do runtime modules, CLI entrypoints, lifecycle hooks, and agent skills invoke the current commands, flags, and paths without legacy fallbacks? |
| **3. Verification / Testing / Gates** | Do automated linters, parity gates, and tests actually exercise the real runtime structure (e.g., class-indented methods, multi-channel guards, isolated unit coverage)? |
| **4. Federation / Integration / Extrapolation** | Do cross-layer interactions, MCP contracts, and shared templates remain 100% extrapolable without leaking local repository assumptions? |

### 1.2 Vertical Human Persona & Use-Case Journey Matrix (`Human <-> AI <-> Technology`)

Identify the concrete human archetypes served by the repository and simulate each persona's end-to-end journey from first contact to completion:

| Human Archetype (`Persona`) | End-to-End Journey to Simulate & Validate |
| :--- | :--- |
| **P1. Individual / First-Time User** | Clones the repository, reads `README.md` Quick-Start, runs initial setup/bootstrap, and executes the health/audit command. Verify zero surprise overwrites, zero false-positive drift warnings across supported profiles, and clear next steps. |
| **P2. Organizational / Root-0 Adopter** | Forks or bootstraps the top-level organizational/domain workspace (`Root 0`), configures authority and upstream lineage, and follows the step-by-step guide in `docs/guides/`. Verify that every documented CLI command and flag in the guide executes verbatim without error. |
| **P3. Department / Operational Unit Integrator** | Inherits from `Root 0` (`--parent-dir` or subtree), scaffolds specialization packs (`business-stack`, `science-stack`, `tech-stack`), and uses generated `Makefile` / CLI ergonomics (`make sync`, `make diff`, `make promote`) for 1-hop upward/downward flows. |
| **P4. Consumer Project Developer & Agent** | Applies templates to an application repository, works under active guardrails/hooks, runs tests, and receives actionable remediation whenever a guardrail blocks an operation. |
| **P5. Upstream Maintainer / Operator** | Runs full verification (`make verify`), inspects diagnostics, and prepares releases (`/release`) with zero cross-tier or private identifier leaks. |

### Pass 1 Checklist
- [ ] **3-Tier Documentation Coherence (`README.md` $\rightarrow$ `docs/guides/` $\rightarrow$ `docs/architecture/` & `docs/reference/`)**: Verify directory trees against disk (`find`/`ls`), relative links (`test -f`), CLI flag tables, and `< 465`-line modularity.
- [ ] **Conceptual & Semantic Documentation Reading Pass (`Concept-to-Code & Taxonomy Isomorphism`)**: Read prose tables and conceptual explanations word-for-word against the live codebase (`constants.py`, `templates/**/template.json`, `.agents/skills/*/SKILL.md`) to verify: (1) zero retired taxonomy terms (`VALID_TEMPLATE_KINDS`: strictly `core-base`, `business-stack`, `science-stack`, `tech-stack`), (2) complete **19-Skill Matrix** across the 3 Core Bases + 3 Specialization Stacks, (3) domain-neutral Level 3 descriptions (**Squad, Case, Research Study, or Operational Unit**), and (4) single-surface **Antigravity 2.0 (`antigravity-agents`)** workspace execution (zero legacy IDE vs. Agents comparison).
- [ ] **Verbatim Human Walkthrough Parity**: Verify that every CLI command and flag sequence shown in `README.md` and `docs/guides/` matches the actual parser options and succeeds end-to-end.
- [ ] **Modern Stack Currency**: Verify that docs, rules, templates, and code use the target modern stack version consistently (zero outdated version ranges or legacy typing syntax).
- [ ] **Zero-Backward Law Scan**: Confirm zero `@deprecated` markers, compatibility aliases (`OldName = NewName`), dual CLI flags, or dead transition branches.
- [ ] **Generic vs. Local Rule Purity**: Confirm that reusable base rules (`technical-base`) and shared skills contain zero hardcoded counts, paths, or assumptions tied to a single repository.
- [ ] **Outbound / Cross-Perspective Non-Restriction Check**: Confirm that tightening a rule, default, or guard in Perspective A does not restrict or pollute a valid outbound workflow in Perspective B (e.g., non-technical forks, read-only mounts, or downstream consumer repositories).

Record all findings in a structured table (`[P1-01]`, `[P1-02]`, ...) with severity, conflicting perspectives, exact `file:line` evidence, and clean-cutover remediation.

---

## Phase 2 — Pass 2: Pragmatic Technical Architecture (`technical`) OR Ledger & Topology Consolidation (`business`)

Once conceptual and normative requirements from Pass 1 are aligned, audit their implementation according to `workspace_mode`:
- **In `business` mode (`Root 0` / `Department` / `business-base` / `business-stack/*` / `science-stack/*`)**: Audit (1) **Single Source of Truth (SSoT) Ledger & Corpus Consolidation** (`corporate/` tables and modular `docs/` vs. prose duplication), (2) **Full Deontic Precedence (`1..95`: Territorial/Public-Admin `1..4` $\rightarrow$ Corporate/Dept/Squad `5..80` $\rightarrow$ Contextual `Human-Stack` `85..95`) & Surface Binding Coverage**, (3) **Cross-Surface Cascade (`surfaces/{web,forms,print}/`) & `< 465`-Line Modularity**, and (4) **IP Firewall & Crisis Escalation SLAs (`P0/P1/P2`)**.
- **In `technical` or `hybrid` mode (`technical-base` / `tech-stack/*`)**, audit the **code representation** following the **Pre-Edit Reading Priority (`1. Guides/Specs -> 2. Tests [E2E -> Imp -> Unit] -> 3. Source Code`)**:

1. **Floor-Version Security & Stdlib Compliance Gate**:
   - Verify the code uses modern, secure-by-default idioms of the declared language floor version (`requires-python`) and standard library primitives (`hashlib.file_digest`, `stat.S_IWUSR`, `Path.is_relative_to`) over deprecated or legacy patterns. (Keep deep hot-path profiling, optional `PEP 7` C-accelerators, and external `OSS-to-OSS` upstream PRs strictly separated in the conscious `oss-contribute` workflow.)
2. **Functional vs. Object-Oriented, Polymorphic & Subpackage Evolution Ladder (`Inline -> Function -> Class -> Protocol/Catalog -> 1:1:1 Module -> Bounded-Domain Subpackage`)**:
   - Prefer pure functions for stateless transformations, but escalate deterministically when code or shell scripts exhibit defensive syntactic compression (cryptic short identifiers, chained `.update()` packing, multi-statement `; then` Bash lines, or inline `python3 -c` blocks in `.sh` scripts $> 250$ lines) or structural data asymmetry (mixing `.get()` and `d["k"]` on the same internal dict, inline schema versions like `"1.2"`, or raw numeric slices like `[:24]`): extract a **Function** when an inline block repeats $\ge 2$ times; extract a **Class / `@dataclass`** when $\ge 3$ functions share $\ge 4$ context parameters (*Data Clump*); use a **Declarative Catalog (`dict`) or `Protocol` Polymorphism** when `if/elif` chains branch across $\ge 3$–$4$ variants; extract a **`1:1:1` Sub-Module** (or `cli_dispatcher.py` for `.sh` entrypoints $> 250$ lines / $> 5$ subcommands) when a file crosses `400` lines; and group into **`1:1:1` Bounded-Domain Subpackages (`3–8` modules/subpackage)** when a directory reaches $\ge 15$ modules.
3. **Modularity, Relational Cluster Mass ($M_{\text{cluster}}$), Directory Fan-Out (`< 15` Modules/Dir), File Size (`< 465` Lines) & Bifurcated Age Radar (`14d / 90d / 180d`)**:
   - Evaluate individual file size ($< 465$ lines, target $\le 400$), **Directory Fan-Out ($< 15$ `.py` modules per directory $\rightarrow$ group into $3\text{--}8$-module domain subpackages mirrored `1:1:1` across `tests/unit/` and `docs/architecture/`)**, and **Probe E's Relational Cluster Mass ($M_{\text{cluster}}(G) = \sum_{f \in G} L(f)$)**: when $\ge 2$ coupled modules in a functional cluster exceed `385` lines with $M_{\text{cluster}} \ge 1{,}200$ or share `_private` helpers across peer engines (`*_engine.py`), propose consolidating the shared responsibility into a dedicated `1:1:1` module (via `architecture-review` $\rightarrow$ `refactoring`). Evaluate context-dependent age (`> 14d` for staged `.agents/proposals/**` via `stale_proposals` in `make status`, `> 90d` for code/tests/`docs/architecture/`, and `> 180d` for `corporate/` and `templates/`): if **aligned in active use (`0` drift)**, propose **consolidation, `C1` automation, or upward `/enrich`**; if **drifted** (diverges from newer idioms or `Source > Spec`), propose **refactoring, adjustment, or decommissioning**.
4. **Strict Typing, Public Docstrings & Forensic Intent Resolution (`[WIRE]` vs. `[CONSOLIDATE]` vs. `[PRUNE]`)**:
   - Verify explicit parameter and return types on 100% of functions/methods, 1-line docstrings on 100% of public functions/methods, specific domain exceptions/error codes, and zero linter or type-checker warnings.
   - **Never prune an unreferenced constant, helper, or test by reflex**: inspect `git log -S <symbol> -p` and `docs/architecture/` first and classify it explicitly as **`[WIRE]`** (*unconnected design intent* $\rightarrow$ wire into its consumer engine and add bipolar tests), **`[CONSOLIDATE]`** (*duplicate SSoT* $\rightarrow$ merge into the canonical dict/catalog without losing values), or **`[PRUNE]`** (*proven obsolete residue* $\rightarrow$ remove cleanly).

Record all technical improvements in a structured table (`[P2-01]`, `[P2-02]`, ...) with `file:line` references and concrete refactoring actions.

---

## Phase 3 — Pass 3: `1:1:1` Symbiosis (`Spec <-> Source <-> Test` in `technical` mode; `Policy <-> Ledger <-> Sign-Off Gate` in `business` mode)

- **In `business` mode (`Root 0` / `Department`)**: Verify that every normative policy and corporate ledger (`corporate/**/*.md`, `templates/**/rules/*.md`, `docs/**/*.md`) maintains `1:1:1` alignment between (1) **Traceable Artifact & Ledger IDs (`[DEPT]-[TYPE]-[YYYY]-[NNN]`)**, (2) **Three-Part Functional Verification Structure** (`# Scope & Surface Target`, `# Normative Invariants`, `# Verification & Sign-Off Gates`), and (3) **Zero-Drift Layer Sync (`make diff` & `make horizon`)**.
- **In `technical` or `hybrid` mode**, audit the alignment between **Normative Specifications**, **Executable Source Modules**, and **Unit Test Suites** so tests serve as self-documenting executable specifications for both **Agent** and **Human**:

1. **Level 1 — Bidirectional `1:1:1` Specification Table (`docs/architecture/<spec>.md`)**:
   - Every executable source module declares `Specification: docs/architecture/<spec>.md`.
   - Every architecture spec (`< 465` lines) maintains a `1:1:1` table mapping `Source Module <-> 1:1 Unit Test Suite (Test<Module>) <-> Functional Responsibility & Key Verified Invariants`.
2. **Level 2 — Single Canonical Test Container per File (`Test<Module>`)**:
   - Every `1:1` test file (`tests/unit/**/test_<module>.*` or `<module>.test.*`) encapsulates its tests inside **one** canonical class/suite (`class Test<Module>` / `describe('<Module>')`) whose docstring/header links back to the source module and specification.
3. **Level 3 — Self-Documenting Behavioral Test Names + 1-Line Invariant Docstrings**:
   - **Test Method Name (`test_<subject>_<scenario_or_condition>_<expected_outcome>`)**: Reads as a natural-language functional proposition for human scanning.
   - **1-Line Invariant Docstring**: States *why* the test exists — the normative invariant, security pole, or boundary cut-point (`N` vs `N ± 1`) proven — eliminating the need for noisy inline narrative comments.
   - **Explicit AAA, Single-File `1:1:1` Isolated Coverage & Anti-Deception Gates**: Separate `# Arrange`, `# Act`, and `# Assert` comments, `100.00%` statement and branch coverage of each `<mod>.py` when running its `1:1:1` `test_<mod>.py` in strict single-file isolation (`0` *Cross-Unit Coverage Masking*), exact `N` vs `N ± 1` boundary cut-points, bipolar guard verification (negative pole first, positive pole second), explicit error matching (`match=`), and zero blind boundary/subprocess mocks.
4. **Level 4 — Bidirectional 3-Tier Test Flow (`E2E <-> Imp <-> Unit`), `imp` Terminology & Zero-Dependency Mutation Probes**:
   - **Bidirectional Asymmetry**: Read, deduce cases, and validate **Top-Down (`E2E -> Imp -> Unit`)**; author, isolate coverage, and execute **Bottom-Up (`Unit -> Imp -> E2E`)** so `tests/unit/` achieves 100% isolated branch coverage first without higher-tier masking.
   - **`tests/e2e/`**: Human persona journeys and multi-step vertical workflows catching cross-perspective/outbound regressions.
   - **`tests/imp/` (Implementation Tests — never `int`)**: Real internal boundary implementation (CLI/stdio/IPC/DB/FS) and `Spec <-> Code <-> Doc` parity gates (named `imp` to avoid `int` keyword collisions and to distinguish internal component *implementation* from production *integration*).
   - **`tests/unit/`**: `1:1` algorithmic exhaustiveness across all 4 quadrants (*Nominal*, *Exact `N` vs `N ± 1` Numeric, Input-Cardinality (`1-token` vs. `multi-token` natural queries) & Lifecycle (`greenfield t=0` vs. `brownfield N-1 -> N` upgrade with non-ASCII UTF-8 payloads, explicit `os.utime` offsets, and post-reap/reconcile disk & tracker sterility assertions) Boundaries*, *Bipolar Guard Poles*, and *Outbound/Hostile Environment Failures*).
   - **Zero-Dependency Mutation Probe Loop (`Mutant Probe -> Outbound Survivor Check -> Test Materialization`)**: Probe critical conditions, filter sets, and default parameters with adversarial mutations (`<` $\leftrightarrow$ `<=`, omitted filter items, non-default role/flag values); whenever a mutant survives across `Unit` / `Imp` / `E2E`, materialize the missing case in its respective `Test<Module>` suite.

---

## Phase 4 — Scale & Governance Spillover Gate (`WORKROAD` / `WORKTASK` / `BACKLOG`)

Before executing fixes, evaluate the total approved scope to prevent rushed execution or mid-audit context loss:

| Regime | Threshold | Mandatory Orchestration Flow |
| :--- | :--- | :--- |
| **Regime 0 — Closed-World Convergence (`0` Findings)** | All 4 Phase-0 probes and Pass 1–3 matrices return **`0` discrepancies** | 1. **Anti-Searcher-Bias Rule**: Never invent cosmetic churn, artificial refactors, or unnecessary deletions when all closed-world invariants pass.<br>2. Present the **Step-by-Step Closed-World Elimination Table (`Surface Checked -> Invariant Verified -> Status: ✅ 0 Discrepancies`)**.<br>3. Declare **`CONVERGENCE REACHED (0 findings)`** so the human operator has complete, auditable certainty that the repository is ready for commit or `/release`. |
| **Regime A — Atomic In-Session Execution** | $1\text{–}15$ cohesive findings completable within the current session with 100% verification | 1. Present the **Master Audit Plan** with a Pre-Edit Scope Blueprint (and `[WIRE]` / `[CONSOLIDATE]` / `[PRUNE]` classification for any unreferenced symbols).<br>2. Upon user approval, execute in ordered batches (`P0 Runtime/Hooks` $\rightarrow$ `P1 Rules/Skills` $\rightarrow$ `P2 Docs/Templates` $\rightarrow$ `P3 1:1:1 Tests & Gates`), walking all **5 ripple links** on every change.<br>3. Run full verification (`make verify` + Phase-0 probes) after execution to confirm **`0` residual findings** in the same turn, then close via `/continue`. |
| **Regime B — Multi-Phase Governance Spillover** | $> 15$ findings, cross-cutting architectural refactors, or multi-session scope | 1. Crystallize the full audit blueprint into `roadmaps/audit_<YYYY_MM_DD>.md`.<br>2. Register the ordered audit phases (`RA.1`, `RA.2`, ...) in `WORKROAD.md` and capture independent backlog items in `BACKLOG.md`.<br>3. Promote **only the first phase (`RA.1` $\rightarrow$ `T1`)** into `WORKTASK.md` per `/priority` and `/governance`.<br>4. Execute and verify `T1` atomically, then checkpoint via `/continue` so zero findings are ever left half-done across sessions. |
