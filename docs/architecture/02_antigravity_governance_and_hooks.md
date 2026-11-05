# Architecture 02: Google Antigravity 2.0 Governance, Lifecycle Hooks & Skills

> **Normative Specification — Subsystem 2 (`antigravity/.gemini/config/` & `templates/`)**
>
> This document specifies the runtime architecture, token-budget constraints, lifecycle hook JSON contracts (`PreToolUse`, `PostToolUse`, `PostInvocation`, `Stop`), skill discovery mechanics, and Layer 2 starter templates for Google Antigravity 2.0.

---

## 1. Shared Global Configuration (`~/.gemini/config/`) Across `antigravity-agents` & `agy`

Google Antigravity 2.0 operates across two local developer surfaces (`antigravity-agents` desktop and `agy` CLI) that share a single global configuration root at `~/.gemini/config/`:

| Surface | Binary / Install Location | Surface-Specific State | Shared Global Config (Stowed) |
|---------|---------------------------|------------------------|-------------------------------|
| **Antigravity 2.0 (`antigravity-agents`)** | `/opt/antigravity-agents/antigravity` | `~/.gemini/antigravity/` (`brain/`, MCP schemas) | `~/.gemini/config/{AGENTS.md,hooks.json,scripts/,skills/}` |
| **Antigravity CLI (`agy`)** | `~/.local/bin/agy` | `~/.gemini/antigravity-cli/` | `~/.gemini/config/{AGENTS.md,hooks.json,scripts/,skills/}` |

> **Cross-Container & Multi-Layer Extension**: While GNU Stow links `~/.gemini/config/` on the local host with zero latency, these same governance assets (`AGENTS.md`, `hooks.json`, `skills/`, `templates/`) can also be exposed across isolated Docker containers, remote SSH servers, and multi-squad forks via the optional Contextual MCP Server ([`03_contextual_mcp_and_federation.md`](03_contextual_mcp_and_federation.md)).

---

## 2. Token Budget Engineering & Progressive Disclosure

Antigravity 2.0 enforces two strict runtime limits when loading rules into the LLM context window:
1. **Per-File Cap**: Individual rule files exceeding **24 KB** are truncated or rejected.
2. **Global Inline Budget (`defaultRulesBudget`)**: The combined size of all `always_on` rules (`~/.gemini/config/AGENTS.md` + all active workspace `.agents/rules/*.md` with `trigger: always_on`) is capped at **20,000 tokens** (~70–75 KB across a multi-repo workspace). If the combined `always_on` payload exceeds this budget, Antigravity evicts global rules from inline injection.

### 2.1. Architectural Invariants for Rules & Skills

The following 3-tier loading hierarchy partitions inline always-on guardrails from conditional rules and on-demand skills to keep the active context window within budget:

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Tier 1: Always-On Inline Rules (Strict Budget <= 20,000 tokens total)   │
│  • ~/.gemini/config/AGENTS.md (MUST stay <= 18,000 bytes; target ~16KB) │
│  • <project>/.agents/rules/{project,coding,environment}.md (always_on)  │
├─────────────────────────────────────────────────────────────────────────┤
│ Tier 2: Conditional Rules (Loaded on demand via trigger: model_decision)│
│  • <project>/.agents/rules/{governance,testing,documentation}.md        │
├─────────────────────────────────────────────────────────────────────────┤
│ Tier 3: Procedural & Workflow Skills (Loaded only when activated)       │
│  • ~/.gemini/config/skills/<name>/SKILL.md (< 500 lines, kebab-case)    │
│  • <project>/.agents/skills/<name>/SKILL.md                             │
└─────────────────────────────────────────────────────────────────────────┘
```

- **Hard Gate**: `scripts/verify-repo.sh` (Check `[5/8]`) fails CI if `antigravity/.gemini/config/AGENTS.md` exceeds **18,000 bytes**, and `post_invocation_lint.py` (`check_rules_token_budget`) warns at runtime if `AGENTS.md` exceeds `18,000 bytes` (`[TOKEN_BUDGET_EXCEEDED]`) or if combined `always_on` rules across `AGENTS.md` + workspace `.agents/rules/*.md` exceed `80,000 bytes` (~20,000 tokens, `[WORKSPACE_RULES_BUDGET_EXCEEDED]`).
- **Rule vs. Skill Separation**: *Rules* govern **what** invariants must hold (concise mandates); *Skills* teach **how** to execute multi-step workflows (loaded on demand).

---

## 3. Lifecycle Hooks Architecture (`hooks.json` + `scripts/*.py`)

Antigravity 2.0 executes deterministic Python 3.14 hook scripts at four points in the agent execution lifecycle. All hooks receive a JSON payload on `stdin` and write a JSON response to `stdout`.

```mermaid
sequenceDiagram
    participant Agent as Antigravity Agent
    participant Pre as PreToolUse (pre_tool_guard.py)
    participant Tool as Workspace Tool (edit_file / run_command)
    participant Post as PostToolUse (post_edit_format.py)
    participant Inv as PostInvocation (post_invocation_lint.py)
    participant Stop as Stop (stop_verify_tests.py)

    Agent->>Pre: Tool call request (stdin JSON)
    alt Violates safety/architecture invariant
        Pre-->>Agent: {"decision": "deny", "reason": "..."}
    else Allowed
        Pre-->>Tool: {"decision": "allow"}
        Tool-->>Post: File modified (.py)
        Post->>Post: ruff format <file>
        Agent->>Inv: Turn completed
        alt Ruff or AST check_project/check_tests fails
            Inv-->>Agent: {"injectSteps": [...], "terminationBehavior": "force_continue"}
        end
        Agent->>Stop: Agent attempts to finish (NO_TOOL_CALL / model_stop)
        alt Unit tests fail on modified/untracked .py files
            Stop-->>Agent: {"decision": "continue", "reason": "..."}
        else All tests pass
            Stop-->>Agent: {"decision": "stop"}
        end
    end
```

### 3.1. Hook Contract & `1:1:1` Test Traceability Reference

Each of the 4 Antigravity lifecycle hooks (`PreToolUse`, `PostToolUse`, `PostInvocation`, `Stop`) maps `1:1:1` to a standalone Python 3.14 script in `antigravity/.gemini/config/scripts/` and an isolated unit test suite:

| Hook Event | Enforcement Behavior | Matcher | Input (`stdin` JSON keys) | Output (`stdout` JSON contract) | Source Script | `1:1` Unit Test |
|------------|----------------------|---------|---------------------------|---------------------------------|---------------|-----------------|
| **`PreToolUse`** | **Hard-blocks** (via POSIX `shlex` segment tokenizer + subshell unwrapping + regex fallback):<br>1. Non-empty writes or partial edits (`_init_write_leaves_non_empty`: blocks non-empty `Content`/`Replacement`/`ReplacementChunks`, `Append=True` on existing non-empty files, and partial `Target`/`ReplacementChunks` removals that leave residual bytes on disk) to consumer `src/**/__init__.py` or `tests/**/__init__.py` (across both `_FILE_WRITE_TOOLS` and `run_command` shell output redirections `>`/`>>`/`>\|`/`&>`, heredocs `<<EOF`, `tee`, `cp`/`mv`/`install`, `sed -i`/`perl -i`, `touch`/`truncate`, `dd of=`, and inline `python -c`).<br>2. Manual edits or shell writes to `alembic/versions/*.py`.<br>3. Direct edits or shell writes to materialized upstream layer rules (`.agents/rules/layer-<NN>-*.md`).<br>4. Automatic execution of mutating `git` (`add`, `commit`, `push`, `reset --hard`, `clean -f`, `subtree add\|pull\|push\|merge`) or `alembic` (`revision`, `upgrade`, `downgrade`) commands across compound commands, global flags (`-C`, `-c`, `--no-pager`), env/sudo/nice/timeout/ionice/stdbuf/chrt/taskset wrappers (with option arguments via `_WRAPPER_FLAGS_WITH_ARG` and `timeout` positional duration), `sh -c` / `bash -c` subshells, and `python -c` `subprocess`/`os.system` calls without false positives on quoted strings or input redirections (`<`). | `write_file\|edit_file\|replace_file_content\|multi_replace_file_content\|write_to_file\|run_command` | `toolCall.name`, `toolCall.args` (`Path`, `TargetFile`, `Content`, `Replacement`, `CodeContent`, `ReplacementChunks`, `Target`, `Append`, `CommandLine`) | `{"decision": "allow"}` or `{"decision": "deny", "reason": "..."}` | [`pre_tool_guard.py`](../../antigravity/.gemini/config/scripts/pre_tool_guard.py) | [`test_pre_tool_guard.py`](../../tests/unit/test_pre_tool_guard.py) (`TestPreToolGuard`) |
| **`PostToolUse`** | Resolves relative `Path` / `TargetFile` entries against `workspacePaths` and runs `ruff format` on any edited `.py` file immediately after the write completes. | `edit_file\|write_file\|...` | `toolCall.args.Path` / `TargetFile`, `workspacePaths` | `{}` or `< 465`-line pre-growth advisory | [`post_edit_format.py`](../../antigravity/.gemini/config/scripts/post_edit_format.py) | [`test_post_edit_format.py`](../../tests/unit/test_post_edit_format.py) (`TestPostEditFormat`) |
| **`PostInvocation`** | Exposes `inspect_checker_availability(workspace_paths)` for adapter introspection (`ruff_available`, `venv_python_available`, `structural_checks_available`), checks `always_on` rule token budgets (`check_rules_token_budget`: `AGENTS.md <= 18 KB` and combined workspace `always_on` rules `<= 80 KB`), detects modified **and untracked** `.py` and `docs/**/*.md` files, and runs `ruff check` + `< 465`-line modularity gate (`[max-file-lines]`, `[max-doc-lines]`) + defense-in-depth `[init-purity]` and `[zero-touch-migration]` checks + `1:1:1` `Specification:` pointer check (`[missing-spec-pointer]`) + AST-aware AAA test comment check (`[missing-aaa]`) + AST `check_project`/`check_tests`. Forces the agent to fix violations in the same turn up to `_MAX_FORCE_CONTINUE_INVOCATIONS = 5`, emitting an explicit circuit-breaker halt footer once `invocationNum >= 5`. | *(All turns)* | `workspacePaths`, `invocationNum` | `{}` or `{"injectSteps": [{"ephemeralMessage": "..."}], "terminationBehavior": "force_continue"}` | [`post_invocation_lint.py`](../../antigravity/.gemini/config/scripts/post_invocation_lint.py) | [`test_post_invocation_lint.py`](../../tests/unit/test_post_invocation_lint.py) (`TestPostInvocationLint`) |
| **`Stop`** | Runs `pytest --tb=line -q --no-header -x` across workspaces with modified/untracked `.py` files before allowing the agent to conclude its turn (`decision="continue"` blocks the stop and forces remediation if tests fail). | *(Normal stop: `NO_TOOL_CALL` / `model_stop`)* | `workspacePaths`, `terminationReason` | `{"decision": "stop"}` or `{"decision": "continue", "reason": "..."}` | [`stop_verify_tests.py`](../../antigravity/.gemini/config/scripts/stop_verify_tests.py) | [`test_stop_verify_tests.py`](../../tests/unit/test_stop_verify_tests.py) (`TestStopVerifyTests`) |

### 3.2. Deterministic Hook-to-Documentation Contract Parity (`scripts/verify-repo.sh` Check `[4/8]`)

To prevent silent drift between what the lifecycle hooks enforce in Python and what is documented in `AGENTS.md`, `SECURITY.md`, `README.md`, and `docs/architecture/`, `scripts/verify-repo.sh` (Check `[4/8]`) and `tests/imp/test_repo_parity_gates.py` import the hook modules directly and enforce four automated parity checks on every CI run:
1. **Matcher Set Parity**: `hooks.json` `PreToolUse` and `PostToolUse` `matcher` sets must equal `pre_tool_guard._FILE_WRITE_TOOLS` (`| {"run_command"}` for `PreToolUse`).
2. **Enforced Guard Token Parity**: Every git subcommand in `pre_tool_guard._DOCUMENTED_GIT_SUBCOMMANDS` (`add`, `commit`, `push`, `reset --hard`, `clean -f`, `subtree`), every alembic subcommand in `_DOCUMENTED_ALEMBIC_SUBCOMMANDS` (`revision`, `upgrade`, `downgrade`), and every file guard (`alembic/versions/`, `0 bytes` `__init__.py`) must match `_MUTATING_GIT_RE` / `_ALEMBIC_MUTATE_RE` and appear across `AGENTS.md`, `02_antigravity_governance_and_hooks.md`, `SECURITY.md`, and `README.md`.
3. **Token-Budget Threshold Parity**: `post_invocation_lint._AGENTS_MD_MAX_BYTES` (`18,000` bytes) and `_TOTAL_RULES_BUDGET_MAX_BYTES` (`80,000` bytes) plus warning codes (`TOKEN_BUDGET_EXCEEDED`, `WORKSPACE_RULES_BUDGET_EXCEEDED`) must match `dotfiles_mcp_server.AGENTS_MD_MAX_BYTES` and `docs/architecture/02..04`.
4. **Bidirectional `1:1:1` Source $\leftrightarrow$ Unit Test $\leftrightarrow$ Specification Traceability**: Every Python module in `antigravity/.gemini/config/scripts/` and `scripts/dotfiles_mcp/*/` must declare a `Specification: docs/architecture/<file>.md` header in its docstring, and that specification file must cross-reference the module and its `1:1` unit test.

---

## 4. Complete 23-Skill Matrix (`antigravity/.gemini/config/skills/` & `templates/**/skills/`)

Every skill resides in `antigravity/.gemini/config/skills/<name>/SKILL.md` (10 universal lifecycle, governance, and dual-mode audit skills), `templates/science-stack/software-engineering/skills/<name>/SKILL.md` (4 software-engineering and substrate skills), or `templates/{science-stack,business-stack,framework-stack}/*/skills/<name>/SKILL.md` (9 domain specialization-stack skills) and must declare YAML frontmatter with a `kebab-case` `name:` and `description:` (verified by `scripts/verify-repo.sh` Check `[6/8]`).

### 4.1. Interactive Slash-Command Skills (`/<name>` — 8 Global Skills)

The 8 interactive slash-command skills in `antigravity/.gemini/config/skills/` govern session lifecycle (`/sopen`, `/continue`, `/sclose`), prioritization (`/priority`), dual-mode auditing (`/review`, `/full-audit`), knowledge promotion (`/enrich`), and SemVer releases (`/release`):

| Skill / Command | Primary Responsibility | Key Artifacts Read / Updated |
|-----------------|------------------------|------------------------------|
| **[`sopen`](../../antigravity/.gemini/config/skills/sopen/SKILL.md)** (`/sopen`) | Pulls latest `~/dotfiles-ubuntu` (`--ff-only`), inspects mounted `layers/*` & `logs/mcp_alerts.jsonl`, restores session context across 3 tiers (`brain/` $\rightarrow$ `.agents/SESSION.md` $\rightarrow$ `git status`), and triggers project `/start` | `.agents/SESSION.md`, `WORKTASK.md`, `WORKROAD.md` |
| **[`continue`](../../antigravity/.gemini/config/skills/continue/SKILL.md)** (`/continue`) | Mid-session checkpoint: snapshots active task progress, promotes completed task blocks (`WORKTASK.md` $\rightarrow$ `CHANGELOG.md`), and delivers commit blocks | `.agents/SESSION.md`, `WORKTASK.md`, `WORKROAD.md`, `CHANGELOG.md` |
| **[`sclose`](../../antigravity/.gemini/config/skills/sclose/SKILL.md)** (`/sclose`) | End-of-session closure: runs governance promotion (Zero-Clutter Invariant), closes `.agents/SESSION.md`, runs `make verify` if `dotfiles-ubuntu` changed, emits knowledge signals, and delivers local per-repo commits (`[Unreleased]`) | `.agents/SESSION.md`, `WORKTASK.md`, `WORKROAD.md`, `BACKLOG.md`, `CHANGELOG.md` |
| **[`release`](../../antigravity/.gemini/config/skills/release/SKILL.md)** (`/release`) | Explicit SemVer release cut: runs zero-leak/agnosticism scans and `make verify`, promotes `## [Unreleased]` $\rightarrow$ `## [X.Y.Z] - YYYY-MM-DD`, syncs `VERSION`/`pyproject.toml`/`README.md`, and delivers the release commit + tag + push block | `VERSION`, `pyproject.toml`, `README.md`, `CHANGELOG.md` |
| **[`priority`](../../antigravity/.gemini/config/skills/priority/SKILL.md)** (`/priority`) | Enforces the deterministic priority chain (`WORKTASK.md` $\rightarrow$ `WORKROAD.md` / `BACKLOG.md` $\rightarrow$ `roadmaps/`) and Phase 0.5 deep-analysis | `WORKTASK.md`, `WORKROAD.md`, `BACKLOG.md`, `roadmaps/*.md` |
| **[`review`](../../antigravity/.gemini/config/skills/review/SKILL.md)** (`/review`) | Tactical `C1` read-only review across the active session delta (default) or a targeted path/dimension (`/review [path\|docs\|arch\|1:1:1\|layer]`): evaluates `1. docs` (3-tier, 5-link ripple & Conceptual/Semantic Isomorphism), `2. arch` (code or SSoT ledgers), `3. 1:1:1` (tests or sign-off gates), and `4. layer` (manifests & horizon) | `src/**`, `tests/unit/**`, `tests/imp/**`, `docs/**`, `system/mcp-layer.json`, `corporate/**` |
| **[`full-audit`](../../antigravity/.gemini/config/skills/full-audit/SKILL.md)** (`/full-audit`) | Convergent `C2` closed-world repository gate: executes all 5 deterministic probes (`Probe A..E`, including `Relational Cluster Mass` $M_{\text{cluster}}$) and all 4 canonical passes (including Conceptual & Semantic Documentation Isomorphism) across 100% of the repository toward `Regime 0 (0 findings)` | `docs/**`, `.agents/**`, `src/**`, `tests/**`, `WORKTASK.md`, `WORKROAD.md`, `BACKLOG.md` |
| **[`enrich`](../../antigravity/.gemini/config/skills/enrich/SKILL.md)** (`/enrich`) | Scans active workspace `.agents/` against `~/dotfiles-ubuntu` (`Pillar A`), `templates/*` (`Pillar B`), and mounted `layers/*` subtrees, proposes 1-hop upward promotions (`promote-from-project` / `layer-subtree.sh push`) and downward syncs (`sync-layer`), and runs `stow -t ~ -R antigravity` | `.agents/rules/*.md`, `.agents/skills/**`, `~/dotfiles-ubuntu/antigravity/`, `~/dotfiles-ubuntu/layers/*` |

### 4.2. Core Procedural Skills (2 Global + 4 `software-engineering` Branch Skills)

The 6 core procedural skills provide reusable workflows for architecture intersection reviews, work-lifecycle governance, zero-residue refactoring, 3-tier AAA testing, 5-layer UI validation, and empirical OSS hot-path contributions:

| Skill Name | Source Pack (`kind`) | Activation Trigger & Core Methodology |
|------------|----------------------|---------------------------------------|
| **[`architecture-review`](../../antigravity/.gemini/config/skills/architecture-review/SKILL.md)** | Global (`human-base`) | **5-Step Intersection Audit** + **5-Dimension Pre-Development Gate** (*Normative Specs $\rightarrow$ Reference Docs $\rightarrow$ Diagrams $\rightarrow$ Root Guides $\rightarrow$ Roadmaps*) + **4 Deterministic Verification Gates** |
| **[`governance`](../../antigravity/.gemini/config/skills/governance/SKILL.md)** | Global (`human-base`) | **One-Way Work Lifecycle** (`roadmaps/ → WORKROAD → WORKTASK → CHANGELOG`), 1-hop downward directive delegation (`make delegate`), and **3-Stage Conversation Extraction Pipeline** |
| **[`refactoring`](../../templates/science-stack/software-engineering/skills/refactoring/SKILL.md)** | `software-engineering` (`science-stack`) | **Zero-Residue Cutover** (no shims/aliases) + **`1:1:1` Test/Spec Alignment** + **3-Step Obsolete Test Pruning Audit** (`orphan-test-file`, dead symbol sweep, default-parameter sensitivity verification) |
| **[`testing`](../../templates/science-stack/software-engineering/skills/testing/SKILL.md)** | `software-engineering` (`science-stack`) | **Bidirectional 3-Tier Flow (`E2E <-> Imp <-> Unit`)**, **Explicit 3-Comment AAA**, **Service Constructor Mock Injection**, **Anti-Characterization Trap**, and **5-Phase Test Consolidation** |
| **[`validation`](../../templates/science-stack/software-engineering/skills/validation/SKILL.md)** | `software-engineering` (`science-stack`) | **5-Layer Validation Protocol** (Render, Interaction, Persistence, Observation, Edge Cases) tracked in `WORKVALI.md` |
| **[`oss-contribute`](../../templates/science-stack/software-engineering/skills/oss-contribute/SKILL.md)** | `software-engineering` (`science-stack`) | **Empirical Hot-Path Profiling** (`timeit`/`cProfile`) $\rightarrow$ **3-Tier Substrate Escalation** (`Stdlib C-Primitive` $\rightarrow$ `Optional PEP 7 C-Accelerator` $\rightarrow$ `Isolated ~/Projects/oss-contrib-<repo> Upstream PR`) |

### 4.3. Specialization-Stack Skills (9 Skills: `science-stack`, `business-stack`, & `framework-stack`)

The 9 specialization-stack skills extend the core baseline with domain-specific procedures for academic-to-professional Socratic tutoring (`M1..M4`), hexagonal business ledgers, FastAPI/Angular/Django stacks, and NIST CSF 2.0 security audits:

| Skill Name | Specialization Pack (`kind`) | Target Domain & Core Methodology |
|------------|------------------------------|----------------------------------|
| **[`academic-tutor`](../../templates/science-stack/scientific-knowledge-branch/skills/academic-tutor/SKILL.md)** | `scientific-knowledge-branch` (`science-stack`) | Personalizes knowledge consumption across the Academic (`M1..M2` `docs/guides/` Socratic progression) $\rightarrow$ Professional (`M3` `org-*` practice) $\rightarrow$ Scientific (`M4` `sci-*` `docs/reference/` `L3` frontier) continuum via `consumer_viewpoint` and `citation_receipt` |
| **[`ledger-surface-audit`](../../templates/business-stack/corporate-ops-ledger/skills/ledger-surface-audit/SKILL.md)** | `corporate-ops-ledger` (`business-stack`) | Audits 3-ring Hexagonal Business traceability (`corporate/ledgers/` $\rightarrow$ `corporate/{policies,sops}/` $\rightarrow$ `surfaces/{web,forms,print}/`) and `[DEPT]-[TYPE]-[YYYY]-[NNN]` citation parity |
| **[`start`](../../templates/framework-stack/fastapi-hexagonal/skills/start/SKILL.md)** | `fastapi-hexagonal` (`framework-stack`) | Bootstraps or resumes a Python FastAPI + Hexagonal DDD service workspace (`./venv`, `uvicorn`, environment readiness) |
| **[`fastapi-testing`](../../templates/framework-stack/fastapi-hexagonal/skills/fastapi-testing/SKILL.md)** | `fastapi-hexagonal` (`framework-stack`) | Enforces 4-layer hexagonal test isolation (`domain`, `application`, `adapters`, `entrypoints`) with `httpx.AsyncClient` and async DB fixtures alongside `software-engineering`'s `testing` |
| **[`database-migrations`](../../templates/framework-stack/fastapi-hexagonal/skills/database/SKILL.md)** | `fastapi-hexagonal` (`framework-stack`) | Governs user-gated Alembic async schema migrations, zero-touch `alembic/versions/*.py` invariants, and downgrade safety |
| **[`frontend-patterns`](../../templates/framework-stack/fastapi-hexagonal/skills/frontend/SKILL.md)** | `fastapi-hexagonal` (`framework-stack`) | Guides FastAPI web frontend integration, typed API client boundaries, and accessible UI state patterns |
| **[`angular-testing`](../../templates/framework-stack/angular-web/skills/angular-testing/SKILL.md)** | `angular-web` (`framework-stack`) | Enforces Standalone Angular 19+ component and Signal store unit/harness testing |
| **[`django-testing`](../../templates/framework-stack/django-backend/skills/django-testing/SKILL.md)** | `django-backend` (`framework-stack`) | Enforces Django 5.2+ `pytest-django` service-layer isolation and `django_assert_num_queries` N+1 gates |
| **[`nist-csf-audit`](../../templates/framework-stack/nist-csf-security/skills/nist-csf-audit/SKILL.md)** | `nist-csf-security` (`framework-stack`) | Audits NIST CSF 2.0 (`GV/ID/PR/DE/RS/RC`) control ledgers and evidence mappings |

---

## 5. Layer 2 Polymorphic Template Packs (`templates/`)

`templates/` provides 3 composable foundational governance pillars (`templates/base-stack/*`, `kind: "base-stack"`) and 3 active specialization stack families (`templates/science-stack/*`, `templates/business-stack/*`, and `templates/framework-stack/*`):

### 5.1. 3-Tier Base Governance Pillars (`templates/base-stack/{human-base,science-base,business-base}`)

- **`templates/base-stack/human-base/`**: Universal cognitive rigor (`§1–10`), `5-Surface Change Propagation`, forensic `[WIRE] / [CONSOLIDATE] / [PRUNE]` intent verification, `dotfiles-ubuntu` native self-guidance (`§11`), universal task-branch & inter-layer lifecycle (`make status`, `make sync`, `make task` $\rightarrow$ `feature/<TICKET-ID>-<slug>`, `make complete`, `make consult`, `make delegate` strictly inside `layers/<child>/`, `make promote`), `$HOME` vs. `Workspace` separation, scoped `antigravity-agents` workspace containment, model delegation (`§12`), single-language purity & semantic naming synthesis (`§13`), and `[Unreleased]` commit discipline. Default machine-global `AGENTS.md` baseline (with the 10 universal global skills in `antigravity/.gemini/config/skills/`).
- **`templates/base-stack/science-base/`**: Universal scientific & academic degree baseline (`kind: "base-stack"`): `Trunk -> Branch -> Specialty` epistemic hierarchy, universal `1:1:1` Theory/Specification $\leftrightarrow$ Proof/Verification $\leftrightarrow$ Corpus/Implementation traceability, `AAA` Hypothesis-Method-Proof verification, SI/ISO dimensional & `N vs N ± 1` boundary precision, and `domain-<branch>:M1..M4` academic/mastery progression (`M1` Undergraduate Foundation $\rightarrow$ `M2` Applied Practitioner $\rightarrow$ `M3` Specialist/Master $\rightarrow$ `M4` Principal/Research Chair).
- **`templates/base-stack/business-base/`**: Enterprise & normative governance, Single Source of Truth Ledger (`corporate/`), Cross-Departmental Precedence Matrix (`1..80` from Public Administration `Root 0` & Public Depts `1..4` to Enterprise `Root 0`, Departments & Sub-Departments/Units `5..80`), Mutual Entity & Lineage Identification (`entity_kind`, `governing_root_id`, `internal` vs `external`), 4-State $N$-Departmental Surface Consensus (`RECONCILED_FLOW`, `ITERATION_REQUIRED`, `ESCALATE_TO_ROOT`, `ESCALATE_INTER_ENTITY_ROOTS`), *Lex Superior* IP/confidentiality firewall & Crisis Escalation SLAs (`P0/P1/P2`), Traceable Ledger IDs (`[DEPT]-[TYPE]-[YYYY]-[NNN]`), Three-Part Functional Verification Structure, and AI Agent Capability Matrix by Organizational Role.

### 5.2. Orthogonal Specialization Stack Families (`templates/science-stack/`, `templates/business-stack/`, & `templates/framework-stack/`)

- **`templates/science-stack/`**:
  - **`software-engineering/`**: Computer Science & Software Engineering branch (`kind: "science-stack"`, `extends: "science-base"`, `rules/software-engineering.md`) enforcing strict typing (`ruff`/`mypy --strict`, `tsc --noEmit`, `cargo clippy`, `shellcheck`), C-backed floor-version stdlib primitives, `0-byte` `__init__.py` purity, 6-Stage Structural Evolution Ladder (`< 465` lines, `< 15` modules/dir, `Probe E` $M_{\text{cluster}} < 1,200$), `100%` isolated unit branch coverage, and the 4 software engineering skills (`skills/testing/`, `skills/refactoring/`, `skills/validation/`, `skills/oss-contribute/`).
  - **`scientific-knowledge-branch/`**: Scientific, legal, public-administration, and territorial knowledge specialization pack (`kind: "science-stack"`, `extends: "science-base"`, `rules/scientific-methodology.md`) enforcing `Trunk -> Branch -> Specialty` routing, primary-evidence & citation hierarchy, `< 465`-line modular `docs/` libraries queried via `make consult`, and `Human-Stack` (`M1..M4`) didactic adaptation.
- **`templates/business-stack/corporate-ops-ledger/`**: Reference Hexagonal Business Architecture pack (`kind: "business-stack"`, `extends: "business-base"`) with `rules/ops-ledger-architecture.md` (`corporate/ledgers/` $\rightarrow$ `corporate/{policies,sops}/` $\rightarrow$ `surfaces/{web,forms,print}/`) and `skills/ledger-surface-audit/SKILL.md`.
- **`templates/framework-stack/`** (`kind: "framework-stack"`, `upstream_framework` metadata):
  - **`fastapi-hexagonal/`** (`extends: "software-engineering"`, `upstream_framework: "fastapi"`): Python FastAPI + Hexagonal DDD (`rules/{coding,testing,environment,governance}.md`, `skills/{start,fastapi-testing,frontend,database}/SKILL.md`, `governance/*`).
  - **`angular-web/`** (`extends: "software-engineering"`, `upstream_framework: "angular"`): Standalone Angular 19+ Signals, OnPush & reactive forms (`rules/angular-architecture.md`, `skills/angular-testing/SKILL.md`).
  - **`django-backend/`** (`extends: "software-engineering"`, `upstream_framework: "django"`): Modular Django 5.2+ service-layer & query optimization (`rules/django-architecture.md`, `skills/django-testing/SKILL.md`).
  - **`nist-csf-security/`** (`extends: "business-base"`, `upstream_framework: "nist-csf-2.0"`): NIST CSF 2.0 & ISO/IEC 27001 controls (`rules/nist-csf-controls.md`, `skills/nist-csf-audit/SKILL.md`).
