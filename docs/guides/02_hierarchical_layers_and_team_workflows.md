# Hierarchical Governance Layers, Authority Gates & Team Workflows Guide

> **Human & Architect Operator Manual (Tier 2 Progressive Disclosure)**
>
> Step-by-step guide to the 3-Layer Configuration Architecture, 3-Tier Profile Composition (`human-core`, `technical-base`, `business-base`), Multi-Tier Organizational Workflows (`Open Source <-> Corporate Root 0 <-> Department <-> Squad/Team`), Git Email Authority Gates, 1-Hop Horizon Radar, and Custom Skill Authoring. For normative engine contracts, see **[`docs/architecture/02_antigravity_governance_and_hooks.md`](../architecture/02_antigravity_governance_and_hooks.md)** and **[`docs/architecture/04_compaction_surface_and_promotion_engines.md`](../architecture/04_compaction_surface_and_promotion_engines.md)**.

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

### 1.2 Global Slash Commands & Procedural Skills (`~/.gemini/config/skills/`)

| Skill / Command | Type | When to Use & Key Actions |
|-----------------|------|---------------------------|
| `/sopen` | Slash Command | Start of every session: pulls `~/dotfiles-ubuntu`, runs `inspect-horizon` (1-hop upstream/downstream check), and restores context (`brain/` $\rightarrow$ `.agents/SESSION.md` $\rightarrow$ `WORKTASK.md`). |
| `/continue` | Slash Command | Mid-session checkpoint: syncs `WORKTASK.md`, `CHANGELOG.md` (`[Unreleased]`), and `.agents/SESSION.md`. |
| `/sclose` | Slash Command | End of session: consolidates completed work under `## [Unreleased]`, runs `check-authority`, and outputs ready-to-run local `git commit` blocks. |
| `/release` | Slash Command | Explicit SemVer release (`vX.Y.Z`): verifies `check-authority --op release`, runs zero-leak/agnosticism scans and `make verify`, promotes `[Unreleased]` $\rightarrow$ `[X.Y.Z]`, and outputs commit + tag + push commands. |
| `/priority` | Slash Command | Audits `WORKTASK.md` $\rightarrow$ `ROADMAP.md` / `BACKLOG.md` $\rightarrow$ `roadmaps/` to pick the next task. |
| `/review` | Slash Command | Audits code structure, Clean Code, hexagonal boundaries, and AAA test coverage. |
| `/enrich` | Slash Command | Compares workspace `.agents/` against parent layers (`diff-project`), checks `inspect-horizon`, and promotes reusable rules upward (`promote-from-project`, including anonymized `Root 0 -> OSS` PR plans). |
| `architecture-review` | Procedural | Multi-dimensional specification reviews, orthogonal classification unification, and naming coherence. |
| `governance` | Procedural | One-way work lifecycle transitions and clean-room knowledge extraction. |
| `refactoring` | Procedural | Safe decomposition of files approaching the `< 465`-line gate (`<= 400` target) with `1:1:1` parity. |
| `testing` | Procedural | AAA (`Arrange-Act-Assert`) test structure, mock boundaries, and 100% branch coverage audits. |
| `validation` | Procedural | Structured human-agent manual UI/web QA verification tracked in `WORKVALI.md`. |

> **`/learn` (built-in Antigravity command) vs. `/enrich` (`dotfiles-ubuntu`)**:
> `/learn` captures a lesson from the current chat into the active workspace's `.agents/`. `/enrich` evaluates matured rules across workspaces and promotes them upward (`Squad/App -> Department -> Corporate Root 0 -> Open Source`) via `layer-config.sh promote-from-project`.

---

## 2. `antigravity-ide` (360° Viewer) vs. `antigravity-agents` (Scoped Workspaces)

| Surface | Role in Multi-Tier Governance | File-Access & Context Boundary |
|---------|-------------------------------|--------------------------------|
| **`antigravity-ide`** (`/opt/antigravity-ide`) | **360° Visual & Terminal Explorer**: Open the Corporate Root (`Root 0`) or a multi-repo parent folder to inspect code, diffs, and terminals across all departments and squads simultaneously without leaking unrelated agent rules into a single conversation. | Visual/terminal inspection across all folders. |
| **`antigravity-agents`** (`/opt/antigravity-agents`) | **Scoped Agent Execution Surface**: Open a specific Workspace Root (`Corporate Root 0`, a `Department` repo, or a `Squad/App` repo). Automatically loads global `~/.gemini/config/AGENTS.md` (`human-core`) + `<workspace>/.agents/rules/layer-<NN>-<name>.md` ordered by `precedence` (`0..100`). | `Non-Workspace File Access`: set to **`allow`** on Corporate Root (`Root 0` holistic orchestration) and **`deny`/`ask`** on Department or Squad workspaces to enforce strict vertical/horizontal isolation. |

---

## 3. Multi-Tier Lifecycle: `Open Source <-> Corporate Root 0 <-> Department <-> Squad`

### 3.1 Bootstrapping & Synchronizing Each Tier (`scripts/layer-config.sh`)

```bash
# 1. [Corporate Root 0 Architect] Initialize Corporate Root and configure owner authority:
./scripts/layer-config.sh bootstrap-workspace /path/to/corp-root \
  --id acme-corp-root --role corporate --precedence 10 --templates business-base
./scripts/layer-config.sh set-authority /path/to/corp-root \
  --owner-role "Principal Enterprise Architect" --emails "architect@acme.com" \
  --upstream-repo "https://github.com/mtwuser/dotfiles-ubuntu.git"

# 2. [Department Lead] Bootstrap a Department workspace, configure authority, and mount into Root 0:
./scripts/layer-config.sh bootstrap-workspace /path/to/dept-legal \
  --id dept-legal-ip --role domain-policy --precedence 5 \
  --parent-dir /path/to/corp-root --templates business-base
./scripts/layer-config.sh set-authority /path/to/dept-legal \
  --owner-role "Chief Legal Officer (CLO)" --emails "clo@acme.com"
./scripts/layer-config.sh register-subtree dept-legal https://github.com/acme/dept-legal.git master

# 3. [Squad / Team Lead] Bootstrap a Squad workspace inheriting from its parent Department:
./scripts/layer-config.sh bootstrap-workspace /path/to/squad-patents \
  --id squad-patent-ops --role team --precedence 60 \
  --parent-dir /path/to/dept-legal --templates technical-base
```

### 3.2 Authority Gate, 1-Hop Horizon Radar & Child-Contextualized Promotion

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

### 3.3 Day-to-Day Ergonomics: Slash Workflows (`/sopen`, `/enrich`) & Generated Layer `Makefile`

Nobody needs to memorize long `layer-config.sh` invocations for daily operations. Every layer workspace initialized or synced via `bootstrap-workspace` / `sync-layer` provides two built-in ergonomic channels:

1. **In Chat (`/sopen` & `/enrich` Slash Workflows)**:
   - **`/sopen`**: Automatically inspects the workspace's 1-hop horizon (`make horizon`) and rule drift (`make diff`) at session start.
   - **`/enrich`**: Classifies local `.agents/` rules against the 1-hop parent layer, runs `make promote` (upward) or `make sync` (downward) after user approval, and prepares commit/PR blocks.
2. **In Terminal (Role-Specialized `Makefile` in Every Layer Workspace)**:
   - `make horizon` — Inspects 1-hop upstream parent and 1-hop downstream `mounted_layers`.
   - `make sync` — Propagates inherited template packs from the configured parent (`PARENT_DIR`) and refreshes `.agents/` rules + `LAYER_LINEAGE.md`.
   - `make diff` — Verifies zero drift between `.agents/` projections and `templates/`.
   - `make authority` — Checks whether `git config user.email` is authorized to cut a release (`layer_authority`).
   - `make promote SOURCE=.agents/rules/<file>.md [TEMPLATE=<pack>] [TARGET_REPO=<path>]` — Promotes a generalized rule/skill 1-hop upward with `PR_FLAGS=--create-pr`.
   - `make mcp-test` — Runs the MCP layer discovery self-test across the workspace and its mounted subtrees.

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
