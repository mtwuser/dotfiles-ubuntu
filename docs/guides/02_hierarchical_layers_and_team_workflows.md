# Hierarchical Governance Layers, Authority Gates & Squad Workflows Guide

> **Human & Architect Operator Manual (Tier 2 Progressive Disclosure)**
>
> Step-by-step guide to the 3-Layer Configuration Architecture, 3-Tier Profile Composition (`human-core`, `technical-base`, `business-base`), 4-Level Organizational Hierarchy (`Corporate Root 0 <-> Department <-> Squad <-> Project`), Fill-in-the-Blanks Setup Blueprints & Initial Chat Kickoff Prompts, Git Email Authority Gates, 1-Hop Horizon Radar, and Custom Skill Authoring. For normative engine contracts, see **[`docs/architecture/02_antigravity_governance_and_hooks.md`](../architecture/02_antigravity_governance_and_hooks.md)** and **[`docs/architecture/04_compaction_surface_and_promotion_engines.md`](../architecture/04_compaction_surface_and_promotion_engines.md)**.

---

## 1. Configuration Architecture & 3-Tier Profile Composition

Configuration follows a 3-layer hierarchy where each layer extends the one above it:

```
Layer 1: Shared (Global)         ← ~/dotfiles-ubuntu/antigravity/  (symlinked to ~/.gemini/config/)
Layer 2: Templates (Reusable)    ← ~/dotfiles-ubuntu/templates/    (human-core, technical-base, business-base, stack packs)
Layer 3: Custom (Project-local)  ← <workspace>/.agents/            (projected rules, skills, SESSION.md & governance ledgers)
```

### 1.1 Layer 1: Shared Global Baseline (`~/.gemini/config/`)

Managed by the `antigravity/` stow module and applied to **all workspaces** automatically:
- **`AGENTS.md`** — Default `human-core` global baseline (`< 18 KB` token budget cap), switchable via:
  ```bash
  ./scripts/layer-config.sh set-global-profile <human-core|technical|business|full> --stow
  ```
- **`hooks.json` + `scripts/`** — 4 deterministic Python 3.14 lifecycle hooks:
  - `pre_tool_guard.py` (`PreToolUse`) — Blocks non-empty writes (`> 0 bytes`) to consumer `src/**/__init__.py` or `tests/**/__init__.py`, manual edits to `alembic/versions/*.py`, and direct mutations of inherited `.agents/rules/layer-*.md` across both file tools and shell commands (`heredoc`, `tee`, `sed -i`, redirections), plus automated mutating `git` (`add`, `commit`, `push`, `reset`, `rebase`, `checkout`, `merge`, `clean`, `subtree`) or `alembic` commands.
  - `post_edit_format.py` (`PostToolUse`) — Runs `ruff format` automatically whenever a `.py` file is edited.
  - `post_invocation_lint.py` (`PostInvocation`) — Enforces `< 465` lines on modified `.py`, `README.md`, and `docs/**/*.md` files, AAA test comments, `1:1:1` `Specification:` headers, `ruff check`, and `always_on` rule token budgets (`18 KB` `AGENTS.md` / `80 KB` workspace cap).
  - `stop_verify_tests.py` (`Stop`) — Runs affected unit tests before concluding a task.

### 1.2 Global Slash Commands (`~/.gemini/config/skills/`) vs. Technical-Pack Skills (`templates/technical-base/skills/`)

The 10 universal lifecycle, governance, and audit skills live in `$HOME/.gemini/config/skills/` and adapt automatically to `workspace_mode` (`"business"` vs. `"technical"` vs. `"hybrid"`), while the 3 software-engineering-specific skills (`testing`, `refactoring`, `validation`) live in `templates/technical-base/skills/` and are projected into `.agents/skills/` only on technical workspaces:

| Skill / Command | Scope | When to Use & Key Actions |
|-----------------|------|---------------------------|
| `/sopen` | Global (`human-core`) | Start of every session: runs `make status` (`./scripts/layer-config.sh status`) in a single `< 0.2s` call (`session_state`, `priority_state`, `git_state`, `horizon`, `agent_diff`) and skips `brain/` scanning when `last_conversation_id` is `null`. |
| `/continue` | Global (`human-core`) | Mid-session checkpoint: syncs `WORKTASK.md`, `CHANGELOG.md` (`[Unreleased]`), and `.agents/SESSION.md`. |
| `/sclose` | Global (`human-core`) | End of session: consolidates completed work under `## [Unreleased]`, runs `check-authority`, and outputs ready-to-run local `git commit` blocks. |
| `/release` | Global (`human-core`) | Explicit SemVer release (`vX.Y.Z`): verifies `check-authority --op release`, runs zero-leak/agnosticism scans and `make verify`, promotes `[Unreleased]` $\rightarrow$ `[X.Y.Z]`, and outputs commit + tag + push commands. |
| `/priority` | Global (Dual Mode) | Audits `WORKTASK.md` $\rightarrow$ `WORKROAD.md` / `BACKLOG.md` $\rightarrow$ `roadmaps/` using `1:1:1` specs/tests in `technical` mode or *Lex Superior* / SSoT ledgers (`corporate/`) in `business` mode. |
| `/review` | Global (Dual Mode) | Audits code/services/tests (§1–§5) in `technical` mode or corporate ledgers, *Lex Superior*, Traceable IDs (`[DEPT]-[TYPE]-[YYYY]-[NNN]`), and 3-part functional verification (§6) in `business` mode. |
| `/full-audit` | Global (Dual Mode) | Executes a multi-pass, 4-perspective + 5-persona audit adapting Pass 2 and Pass 3 to `workspace_mode` (`Spec <-> Source <-> Test` vs. `Policy <-> Ledger <-> Sign-Off Gate`). |
| `/enrich` | Global (`human-core`) | Compares workspace `.agents/` against parent layers (`diff-project`), checks `inspect-horizon`, and promotes reusable rules upward (`promote-from-project`). |
| `architecture-review` | Global (Dual Mode) | Multi-dimensional specification reviews (`docs/architecture/*.md` in `technical` mode; `corporate/**/*.md` & policy packs in `business` mode). |
| `governance` | Global (Dual Mode) | One-way work lifecycle transitions, 1-hop downward directive delegation (`make delegate` / `delegate-to-child`), and clean-room knowledge extraction. |
| `refactoring` | `technical-base` | Safe decomposition of code files approaching the `< 465`-line gate (`<= 400` target) with `1:1:1` parity. |
| `testing` | `technical-base` | AAA (`Arrange-Act-Assert`) test structure, mock boundaries, and 100% branch coverage audits. |
| `validation` | `technical-base` | Structured human-agent manual UI/web QA verification tracked in `WORKVALI.md`. |

> **`/learn` (built-in Antigravity command) vs. `/enrich` (`dotfiles-ubuntu`)**:
> `/learn` captures a lesson from the current chat into the active workspace's `.agents/`. `/enrich` evaluates matured rules across workspaces and promotes them upward (`Squad/App -> Department -> Corporate Root 0 -> Open Source`) via `layer-config.sh promote-from-project`.

---

## 2. `antigravity-ide` (360° Viewer) vs. `antigravity-agents` (Scoped Workspaces)

| Surface | Role in Multi-Tier Governance | File-Access & Context Boundary |
|---------|-------------------------------|--------------------------------|
| **`antigravity-ide`** (`/opt/antigravity-ide`) | **360° Visual & Terminal Explorer**: Open the Corporate Root (`Root 0`) or a multi-repo parent folder to inspect code, diffs, and terminals across all departments and squads simultaneously without leaking unrelated agent rules into a single conversation. | Visual/terminal inspection across all folders. |
| **`antigravity-agents`** (`/opt/antigravity-agents`) | **Scoped Agent Execution Surface**: Open a specific Workspace Root (`Corporate Root 0`, a `Department` repo, or a `Squad/App` repo). Automatically loads global `~/.gemini/config/AGENTS.md` (`human-core`) + `<workspace>/.agents/rules/layer-<NN>-<name>.md` ordered by `precedence` (`0..100`). | `Non-Workspace File Access`: set to **`allow`** on Corporate Root (`Root 0` holistic orchestration) and **`deny`/`ask`** on Department or Squad workspaces to enforce strict vertical/horizontal isolation. |

---

## 3. 4-Level Hierarchy Lifecycle: `Root 0 -> Department -> Squad -> Project`

When you initialize a layer via `bootstrap-workspace` (or a project via `apply-project`), the CLI automatically generates a **fill-in-the-blanks Setup Blueprint** and a **ready-to-paste Initial Chat Kickoff Prompt** inside the new workspace's `README.md` (or `.agents/LAYER_LINEAGE.md` for projects). Complete the 5 bullet fields and paste the kickoff prompt into your first `antigravity-agents` chat to materialize your layer rules, roadmap, and child tier commands automatically.

### 3.1 Level 1 — `Root 0` (`--role corporate`, `precedence: 10`)

1. **CLI Setup (Standalone Layer Workspace or Direct Platform Fork)**:
   ```bash
   # Option A: Standalone Corporate Root 0 workspace
   ./scripts/layer-config.sh bootstrap-workspace /path/to/corp-root \
     --id acme-corp-root --role corporate --precedence 10 --templates business-base \
     --upstream-url "https://github.com/mtwuser/dotfiles-ubuntu.git"
   ./scripts/layer-config.sh set-authority /path/to/corp-root \
     --owner-role "Principal Enterprise Architect" --emails "architect@acme.com"

   # Option B: Parameterize a cloned fork of dotfiles-ubuntu in place as Root 0
   ./scripts/layer-config.sh init-fork \
     --id acme-corp-root --role corporate --precedence 10 --prune-default-templates
   ./scripts/layer-config.sh set-authority \
     --owner-role "Principal Enterprise Architect" --emails "architect@acme.com"
   ```
2. **Fill-in-the-Blanks Blueprint (`README.md` in `Root 0`)**:
   ```markdown
   ## Layer Setup Blueprint (Level 1 — Root 0 Business & Corporate Governance)
   - **Layer ID & Role**: `acme-corp-root` (`corporate`, `precedence: 10`)
   - **1-Hop Upstream Parent**: `open-source-root`
   - **Active Template Packs**: `business-base`, `acme-corp-root`
   - **Mission, Scope & Core Invariants**: [Fill: Organization mission, core business domain, and compliance/IP/SLA non-negotiables]
   - **Downstream Topology (Next Tier)**: [Fill: Planned child Departments (--role department / --role domain-policy)]
   - **Authorized Layer Owner (`set-authority`)**: [Fill: Role title & owner email]
   ```
3. **Initial Chat Kickoff Prompt (`Root 0`)**:
   ```text
   Read the filled Layer Setup Blueprint in README.md, system/mcp-layer.json, and .agents/LAYER_LINEAGE.md. Tailor antigravity/.gemini/config/AGENTS.md and templates/acme-corp-root/rules/acme-corp-root.md with our mission and invariants without duplicating upstream rules. Run make sync && make diff, update WORKROAD.md and WORKTASK.md, and output the exact ./scripts/layer-config.sh bootstrap-workspace commands to initialize our planned child Departments.
   ```

### 3.2 Level 2 — `Department` (`--role department`, `precedence: 30` / `--role domain-policy`, `precedence: 5`)

1. **CLI Setup**:
   ```bash
   ./scripts/layer-config.sh bootstrap-workspace /path/to/dept-legal \
     --id dept-legal-ip --role domain-policy --precedence 5 \
     --parent-dir /path/to/corp-root --templates business-base
   ./scripts/layer-config.sh set-authority /path/to/dept-legal \
     --owner-role "Chief Legal Officer (CLO)" --emails "clo@acme.com"
   ./scripts/layer-config.sh register-subtree dept-legal https://github.com/acme/dept-legal.git master
   ```
2. **Fill-in-the-Blanks Blueprint (`README.md` in `Department`)**:
   ```markdown
   ## Layer Setup Blueprint (Level 2 — Department & Cross-Cutting Domain Governance)
   - **Layer ID & Role**: `dept-legal-ip` (`domain-policy`, `precedence: 5`)
   - **1-Hop Upstream Parent**: `acme-corp-root`
   - **Active Template Packs**: `business-base`, `acme-corp-root`, `dept-legal-ip`
   - **Mission, Scope & Core Invariants**: [Fill: Department mission, domain invariants, and target file surface globs]
   - **Downstream Topology (Next Tier)**: [Fill: Planned child Squads (--role squad, e.g. squad-patent-ops)]
   - **Authorized Layer Owner (`set-authority`)**: [Fill: Role title & owner email]
   ```
3. **Initial Chat Kickoff Prompt (`Department`)**:
   ```text
   Read the filled Layer Setup Blueprint in README.md, system/mcp-layer.json, and .agents/LAYER_LINEAGE.md. Tailor antigravity/.gemini/config/AGENTS.md and templates/dept-legal-ip/rules/dept-legal-ip.md with our mission and invariants without duplicating upstream rules. Run make sync && make diff, update WORKROAD.md and WORKTASK.md, and output the exact ./scripts/layer-config.sh bootstrap-workspace commands to initialize our child Squads.
   ```

### 3.3 Level 3 — `Squad` (`--role squad`, `precedence: 50`)

1. **CLI Setup**:
   ```bash
   ./scripts/layer-config.sh bootstrap-workspace /path/to/squad-patents \
     --id squad-patent-ops --role squad --precedence 50 \
     --parent-dir /path/to/dept-legal --templates technical-base,fastapi-hexagonal
   ./scripts/layer-config.sh set-authority /path/to/squad-patents \
     --owner-role "Squad Lead" --emails "lead@squad.acme.com"
   ```
2. **Fill-in-the-Blanks Blueprint (`README.md` in `Squad`)**:
   ```markdown
   ## Layer Setup Blueprint (Level 3 — Squad Execution & Tech Stack Governance)
   - **Layer ID & Role**: `squad-patent-ops` (`squad`, `precedence: 50`)
   - **1-Hop Upstream Parent**: `dept-legal-ip`
   - **Active Template Packs**: `business-base`, `acme-corp-root`, `dept-legal-ip`, `technical-base`, `fastapi-hexagonal`, `squad-patent-ops`
   - **Mission, Scope & Core Invariants**: [Fill: Squad mission, bounded contexts, tech stack conventions, and testing gates]
   - **Downstream Topology (Next Tier)**: [Fill: Target application repositories for apply-project, e.g. /path/to/patent-api]
   - **Authorized Layer Owner (`set-authority`)**: [Fill: Role title & owner email]
   ```
3. **Initial Chat Kickoff Prompt (`Squad`)**:
   ```text
   Read the filled Layer Setup Blueprint in README.md, system/mcp-layer.json, and .agents/LAYER_LINEAGE.md. Tailor antigravity/.gemini/config/AGENTS.md and templates/squad-patent-ops/rules/squad-patent-ops.md with our mission and invariants without duplicating upstream rules. Run make sync && make diff, update WORKROAD.md and WORKTASK.md, and output the exact ./scripts/layer-config.sh apply-project commands for our target application repositories.
   ```

### 3.4 Level 4 — `Project` (`apply-project`, Application / Service Workspace & In-Layer `make setup-dev`)

1. **CLI Setup (Project Under a `Department` or `Squad`, or In-Layer Technical Mode via `make setup-dev`)**:
   ```bash
   # Option A: Project workspace under a parent Department or Squad (inherits parent domain rules + tech stack)
   ./scripts/layer-config.sh apply-project /path/to/patent-api \
     --parent-dir /path/to/squad-patent-ops --template fastapi-hexagonal,agile-task-branch

   # Option B: In-layer technical dev mode inside Root 0, a Department, or a Squad (local .agents/ hybrid overlay)
   cd /path/to/dept-legal && make setup-dev   # Overlays technical-base onto business rules (make sync restores business mode)
   ```
2. **Fill-in-the-Blanks Blueprint (`.agents/LAYER_LINEAGE.md` in `Project`)**:
   ```markdown
   ## Project Setup Blueprint (Level 4 — Application Workspace)
   - **Applied Template Packs**: `technical-base,fastapi-hexagonal,squad-patent-ops`
   - **Project / Service Purpose**: [Fill: Core product/service mission and bounded context]
   - **Architecture & Integrations**: [Fill: Domain modules, DB/APIs, and UI/CLI surface]
   - **Phase 1 Milestone Goal**: [Fill: Initial vertical slice or MVP deliverable]
   ```
3. **Initial Chat Kickoff Prompt (`Project`)**:
   ```text
   /sopen — Read .agents/LAYER_LINEAGE.md, all inherited .agents/rules/*.md, and our Project Setup Blueprint.
   Initialize README.md, docs/architecture/ (1:1:1 specs), WORKROAD.md, and WORKTASK.md for Phase 1,
   then propose the Pre-Edit Scope Blueprint for Task 1.
   ```

### 3.5 Authority Gate, 1-Hop Horizon Radar & Child-Contextualized Promotion

Every layer operates with a **strict 1-hop horizon** (`inspect-horizon`): a node only inspects its immediate `1-hop upstream` parent and its immediate `1-hop downstream` children (`layers/*`). Skipping intermediate layers (`Squad -> Corporate Root` or `Department -> Open Source`) is deterministically blocked (`CROSS_TIER_PROMOTION_BYPASS`).

| Operation | Authorized Layer Owner (`git config user.email` matches `layer_authority`) | Downstream Consumer (Squad or Developer inheriting rules) |
|-----------|----------------------------------------------------------------------------|-----------------------------------------------------------|
| **Edit `templates/<pack>/` or cut `/release` on the Layer Repo** | ✅ Allowed (`check-authority --op release` passes). | ❌ Blocked (`AUTHORITY_DENIED`); returns structured remediation to propose an upward PR from the consumer's own workspace. |
| **Modify projected `.agents/rules/layer-<NN>-*.md` directly** | ❌ Blocked (`pre_tool_guard.py`); edit canonical source in `templates/<pack>/` and run `sync-layer`. | ❌ Blocked (`pre_tool_guard.py`); create a workspace-local rule in `.agents/rules/<local>.md` and promote upward. |
| **Promote a matured rule upward (`promote-from-project`)** | ✅ Can apply directly or generate a child-contextualized PR (`--create-pr`). | ✅ Generates a child-contextualized branch (`promote/<child-layer>/<role>/<artifact>`) and `gh pr create` plan targeting its immediate 1-hop parent. |
| **Promote from Corporate `Root 0` to Open Source (`dotfiles-ubuntu`)** | ✅ Supported with `--create-pr --target-repo ~/dotfiles-ubuntu`: enforces `OSS_AGNOSTICISM_VIOLATION` zero-leak gate, auto-routes to `templates/<pack>/...`, and anonymizes corporate/email metadata (`oss_anonymized: true`). | ❌ Blocked (`CROSS_TIER_PROMOTION_BYPASS` — only `Root 0` can promote to Open Source). |

```bash
# Inspect 1-hop upstream/downstream horizon from any workspace:
./scripts/layer-config.sh inspect-horizon /path/to/workspace

# Promote a squad rule upward to its parent Department as a contextualized PR plan:
./scripts/layer-config.sh promote-from-project /path/to/squad-patents \
  --source .agents/rules/patent-claim-check.md --create-pr

# Promote a generic rule from Corporate Root 0 to Open Source (anonymized + zero-leak verified):
# Note: inspect-horizon and Root 0's Makefile automatically route to DOTFILES_DEV_REPO_DIR
# (or ~/Projects/dev-<repo>) when present, keeping ~/dotfiles-ubuntu as the clean runtime clone.
./scripts/layer-config.sh promote-from-project /path/to/corp-root \
  --source templates/business-base/rules/business-base.md \
  --target-repo ~/dotfiles-ubuntu --to-template business-base --create-pr \
  --org "Anonymous Organization (default)" \
  --contributors "Principal Enterprise Architect, CLO, CTO" \
  --context "Validated across Corporate Root 0 + 5 Department subtrees + Squad workspaces"
```

### 3.6 Day-to-Day Ergonomics: Slash Workflows (`/sopen`, `/enrich`) & Generated Layer `Makefile`

Nobody needs to memorize long `layer-config.sh` invocations for daily operations. Every layer workspace initialized or synced via `bootstrap-workspace` / `sync-layer` provides two built-in ergonomic channels:

1. **In Chat (`/sopen`, `/governance`, & `/enrich` Slash Workflows)**:
   - **`/sopen`**: Runs `make status` (`./scripts/layer-config.sh status`) to obtain the workspace's session state, git state, 1-hop horizon, and rule drift in a single `< 0.2s` JSON call.
   - **`/governance` (1-Hop Downward Delegation)**: Delegates an executive or departmental directive 1-hop downward (`Root 0 -> Department` or `Department -> Squad`) via `make delegate CHILD=<layer-id> TASK="<directive>" [PRIORITY=P0|P1|P2]`.
   - **`/enrich`**: Classifies local `.agents/` rules against the 1-hop parent layer, runs `make promote` (upward) or `make sync` (downward) after user approval, and prepares commit/PR blocks.
2. **In Terminal (Role-Specialized `Makefile` & 3 Command Consciousness Tiers in Every Layer Workspace)**:
   - **`make status`** — Returns the consolidated `< 0.2s` JSON digest (`operating_state`: `"oss-readonly-appliance"` | `"oss-dev"` | `"corporate-root"` | `"domain-policy"` | `"department"` | `"squad"` | `"project"`, `workspace_mode`: `"business"` | `"technical"` | `"hybrid"`, `command_tiers`, `session_state`, `priority_state`, `git_state`, `git_governance`, `horizon`, `agent_diff`).
   - **Tier `C1: auto_reflexive` (High-Frequency / Consolidated & Auto-Runnable — `0` cross-layer mutation)**:
     - `make consult LAYER=<id> QUERY="<question>"` — Spawns a one-shot `strictly-read-only` ephemeral consultation against `<id>`, returns a 4-Channel Executive Digest + `rcap1` capsules, and auto-reaps with zero residue.
     - `make horizon` — Inspects 1-hop upstream parent and 1-hop downstream `mounted_layers`.
     - `make upstream-diff` — Compares rule sections (`#`/`##`) between the upstream parent/Open Source and local templates (`in_sync_sections`, `upstream_only_sections`, `local_only_sections`, `diverged_sections`).
     - `make diff` — Verifies zero drift between `.agents/` projections and `templates/`.
     - `make authority` — Checks whether `git config user.email` is authorized to cut a release (`layer_authority`).
     - `make mcp-test` — Runs the MCP layer discovery self-test across the workspace and its mounted subtrees.
   - **Tier `C2: guided_tactical` (Per-Task / Intra-Layer Transitions — local workspace state)**:
     - `make setup-dev` — Overlays `technical-base` (`rules/technical-base.md` + `skills/{testing,refactoring,validation}`) onto the layer's active domain/business rules in `.agents/` (`workspace_mode: "hybrid"`), enabling full software-engineering rigor inside any `Root 0`, `Department`, or `Squad` checkout without mutating `system/mcp-layer.json` (`make sync` restores `business` mode).
     - `make task TASK=<id>` — Claims a task item in `WORKTASK.md` (marking it `[/]`), updates `.agents/SESSION.md` (`## Active Task` with `Ticket ID` and `Origin Layer`), and outputs `git checkout -b feature/<TICKET-ID>-<slug>`.
     - `make sync` — Propagates inherited template packs from the configured parent (`PARENT_DIR`) and refreshes `.agents/` rules + `LAYER_LINEAGE.md`.
   - **Tier `C3: conscious_human_gated` (Low-Frequency / High-Consciousness Inter-Layer & Authority Gates)**:
     - `make complete TASK=<id> [DELIVERABLE=<path>]` — Marks a task `[x]` in `WORKTASK.md` and updates the parent layer's `WORKTASK.md` (`## Outbound Delegations` $\rightarrow$ `stage: completed (pro)`) or stages a non-destructive completion receipt + PR plan (`feature/<TICKET-ID>-completed`).
     - `make roster [ADD=<email>] [REMOVE=<email>] [ROLE=owner|maintainer|validator|member]` — Inspects or updates the layer's `owners` / `maintainers` / `validators` / `members` roster in `system/mcp-layer.json` and synchronizes `.github/CODEOWNERS`.
     - `make decision ITEM=<ref> DEC=<approve|reject|defer|blocked> [REASON=<text>]` — Records a human governance review decision in `WORKTASK.md` and `logs/governance_audit.jsonl`.
     - `make env-gate ENV=<tst|pre|pro>` — Evaluates isomorphic Business & Technical `dev -> tst -> pre -> pro` promotion invariants (`0` open `P0` in `WORKTASK.md` for `tst`, `0` unchecked items in `WORKVALI.md` + `validator_emails` gate for `pre`, `CHANGELOG.md` + `layer_authority` for `pro`).
     - `make promote SOURCE=.agents/rules/<file>.md [TEMPLATE=<pack>] [TARGET_REPO=<path>]` — Promotes a generalized rule/skill 1-hop upward with `PR_FLAGS=--create-pr` (staging non-destructively at `.agents/proposals/to-<layer>/` when target files already exist or caller lacks direct release authority, unless `--force` is passed).
     - `make delegate CHILD=<layer-id> TASK="<directive>" [TICKET=<id>] [PRIORITY=P0|P1|P2]` — Delivers a 1-hop downward directive or file into the child layer's surface, records `- [/] **[<TICKET-ID> -> <child> (stage: delegated)]**` under `## Outbound Delegations` in the parent layer's `WORKTASK.md`, and stages existing files non-destructively at `.agents/proposals/from-<parent>/` unless `--force` is passed.

---

## 4. Authoring Custom Skills & Slash Commands

Shared skills live in `antigravity/.gemini/config/skills/<name>/SKILL.md` (single source of truth symlinked to `~/.gemini/config/skills/<name>/` via `stow -t ~ -R antigravity`), while project-specific skills live in `<project>/.agents/skills/<name>/SKILL.md`.

```markdown
---
name: my-skill-name
description: "One-line description of what this skill/command does and when to activate it"
---

# Skill or `/<name>` Command Title
[Step-by-step instructions (< 500 lines, kebab-case name)]
```

After adding or updating a global skill in `~/dotfiles-ubuntu/antigravity/.gemini/config/skills/`, re-stow so every workspace sees it immediately:

```bash
cd ~/dotfiles-ubuntu && stow -t ~ -R antigravity
```
