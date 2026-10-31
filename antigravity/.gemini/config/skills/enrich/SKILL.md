---
name: enrich
description: extract and enrich shared knowledge — scan project rules/skills for universal patterns to promote upstream
---

# Knowledge Enrichment — `/enrich`

> **Purpose**: Detect rules, skills, or patterns that have matured in a project and should be promoted to a higher layer in the knowledge hierarchy.
> Run periodically, after major milestones, or when changing PCs.

---

## Rule Layer Hierarchy

Before scanning, the agent MUST understand the 4-layer rule model:

```
Layer A — Universal (dotfiles-ubuntu)
│  Rules for ANY developer, ANY project, ANY stack.
│  Examples: zero-residue, AAA testing, commit discipline, coverage gates.
│  Location: ~/dotfiles-ubuntu/antigravity/.gemini/config/
│
├── Layer B — Framework (reusable core framework)
│   │  Rules that define a reusable framework's conventions.
│   │  Examples: hexagonal port/adapter patterns, zone architecture, HTMX conventions.
│   │  Location: <framework>/.agents/
│   │
│   ├── Layer C — Product (projects built on the framework)
│   │   │  Rules specific to a business domain or team.
│   │   │  Examples: payment flow rules, healthcare compliance, API naming for X company.
│   │   │  Location: <product>/.agents/
│   │   │
│   │   └── Layer D — Multi-Dimensional Subtree Layers (Department / Team / Sibling Service)
│   │       Cross-cutting departmental or sibling-service forks mounted under
│   │       ~/dotfiles-ubuntu/layers/<layer-name>/ via ./scripts/layer-subtree.sh.
│   │       Queried on demand via MCP (compare_layer_patterns) and promoted via
│   │       ./scripts/layer-subtree.sh push <layer-name> <target-branch>.
│   │
│   └── (other products using the same framework)
│
└── (other frameworks or standalone projects)
```

**Promotion direction**: knowledge flows UPWARD (C → B → A) when patterns prove universal.
**Inheritance direction**: configuration flows DOWNWARD (A → B → C) via dotfiles + git.

---

## §1. Inventory Scan

// delegate: flash

> [!IMPORTANT]
> **Scope restriction**: ONLY scan directories from these two sources:
> 1. **Active workspace URIs** — the repos listed in the agent's `<user_information>` metadata
> 2. **Shared config** — `~/dotfiles-ubuntu/antigravity/.gemini/config/`
>
> **NEVER** scan `~/Projects/` broadly or enter directories outside the workspace.
> Unrelated directories (e.g. `OFF/`, `ALT/`, personal projects) MUST be ignored.

1. **Identify projects from workspace** — use the workspace URIs provided in the session metadata. These are the ONLY directories to scan.
2. **For each workspace project**, read:
   - `.agents/rules/*.md` — all rule files
   - `.agents/skills/**/*.md` — all skill files (including project-specific command skills such as `start`)
3. **Read shared config** — `~/dotfiles-ubuntu/antigravity/.gemini/config/`:
   - `AGENTS.md` (global rules)
   - `hooks.json` and `scripts/*.py` (global lifecycle hooks)
   - `skills/*/SKILL.md` (shared skills, including session commands like `/sopen`, `/sclose`)
4. **Generate inventory table**:

```markdown
| Layer | Source | File | Key Concepts |
|-------|--------|------|--------------|
| A     | dotfiles-ubuntu | AGENTS.md | [list] |
| B     | <framework-repo> | coding.md | [list] |
| ...   | ... | ... | ... |
```

---

## §2. Knowledge Diff

For each project rule/skill, classify against the layer model:

### §2.1 Upward Promotion Candidates (Project → Shared)

Detect patterns that have **matured** in a project and should move up:

| Signal | What it means |
|--------|---------------|
| A project rule duplicates a shared rule but with MORE detail | The project version is richer — merge upstream |
| A project skill has no equivalent in shared config | New reusable pattern — extract |
| Multiple projects have similar rules | Convergence — unify in shared |
| A project rule contradicts a shared rule | Drift — investigate and reconcile |

### §2.2 Downward Sync Gaps (Shared → Project)

| Signal | What it means |
|--------|---------------|
| Shared rule was updated but project still has old copy | Project needs update |
| New shared skill was added but project doesn't reference it | Inform — may need integration |

### §2.3 Multi-Dimensional Layer & Template Classification

For each candidate, determine the exact target layer and template pack using `.agents/LAYER_LINEAGE.md`, `make horizon` (`inspect-horizon <project>`), `make diff` (`diff-project <project>`), or the MCP tool `compare_layer_patterns` with `layer="all"`:

| If the pattern... | Target Layer & Day-to-Day Command (`make` or CLI) |
|---|---|
| Applies to ANY project regardless of domain or stack (`<= 18,000` bytes cap, promoted from `Root 0` passing `OSS_AGNOSTICISM_VIOLATION`) | **A (Universal Open Source Root)**: `~/dotfiles-ubuntu/templates/<pack>/` (`make promote SOURCE=<path> TEMPLATE=<human-core\|technical-base\|business-base> TARGET_REPO=~/dotfiles-ubuntu`) |
| Applies to a cross-cutting domain policy (`domain-policy`, e.g., Legal/Security) or department (`department`, e.g., Design/Marketing) | **D (Parent Department or Corporate Root 0)**: 1-hop parent layer (`make promote SOURCE=<path> [TEMPLATE=<pack>]`, or `./scripts/layer-subtree.sh push <layer-name> <branch>` when pushing a mounted subtree) |
| Applies to any project using a specific stack or template pack (`stack-starter`, `department-pack`, `domain-policy-pack`) | **B (Framework Repo or Polymorphic Template Pack)**: `<layer>/templates/<pack>/` (`make promote SOURCE=<path> TEMPLATE=<pack>`) |
| Materialized lineage file (`layer-<NN>-<layer>.md`) | **Already tracked by Layer D (`layers/<layer>`)** — only promote if modified in the project (`modified_in_project` in `make diff`) |
| Only applies to this specific product/application | **C (Stays in Project)**: `<product>/.agents/` |

> [!IMPORTANT]
> **Strict 1-Hop Horizon & Never Bypass `Root 0`**:
> - Never promote directly from a child layer (`team` / `squad-*`, `department` / `dept-*`, or `domain-policy`) into `dotfiles-ubuntu` (`Layer A`).
> - Always inspect `make horizon` (`immediate_upstream_id`, `is_oss_community_horizon`, `actor_is_layer_owner`):
>   - **Internal Corporate Horizon (`is_oss_community_horizon: false`)**: Promote strictly **1 hop upward** (`Squad` $\rightarrow$ `Department` $\rightarrow$ `Corporate Root 0`) via `make promote SOURCE=<path> [TEMPLATE=<pack>]` (or `./scripts/layer-subtree.sh pull <layer-name>` from `Root 0`).
>   - **Open-Source Community Horizon (`is_oss_community_horizon: true`, only from `Root 0`)**: Never edit `~/dotfiles-ubuntu` files directly from an external workspace; always propose an anonymized Pull Request via `make promote SOURCE=<path> TEMPLATE=<human-core|technical-base|business-base> TARGET_REPO=~/dotfiles-ubuntu --create-pr`.

---

## §3. Extraction Proposal

Generate a structured proposal for the user respecting the 1-hop horizon:

```markdown
## Enrichment Proposal — [date]

### Promote 1-Hop Upward (`<immediate_upstream_id>`)
- [ ] [rule/skill name]: [what changes] — [why it belongs in immediate 1-hop parent (`Root 0` / `dept-*` / `dotfiles-ubuntu`)]

### Update Current Layer from Upstream (`make sync`)
- [ ] [project]: [rule/skill] needs sync from [1-hop parent version]

### Contradictions / Drift
- ⚠️ [description of conflict]
```

**Wait for user approval before applying any changes.**

---

## §4. Apply & Distribute (Dual-Regime Push Governance)

After approval, distinguish strictly between **Internal Corporate Repositories** and the **Open-Source Root (`dotfiles-ubuntu`)**:

### Regime 1 — Internal Corporate / Departmental / Squad Repos (`is_oss_community_horizon: false`)
1. **Promote or Sync within the 1-Hop Internal Hierarchy**:
   - Run `make promote SOURCE=<rel-path> [TEMPLATE=<pack>]` (which creates a contextualized PR when `actor_is_layer_owner: false`, or updates the 1-hop parent template/subtree when authorized).
2. **Agile Internal Commit & Push**:
   - For internal corporate, departmental (`dept-*`), and squad (`squad-*`) repositories where the user is the authorized layer owner (`actor_is_layer_owner: true`), deliver standard working commit + push blocks so internal teams and `Root 0` subtrees stay continuously synchronized:
   ```bash
   ### [Internal Corporate / Department / Squad repo]
   cd <REPO_PATH>
   git add -u
   git commit -m "chore(governance): [summary of internal layer sync/enrichment]"
   git push
   ```

### Regime 2 — Open-Source Root (`dotfiles-ubuntu` / `is_oss_community_horizon: true`)
1. **From External Workspaces (`Root 0` $\rightarrow$ `dotfiles-ubuntu`)**:
   - **NEVER** mutate `~/dotfiles-ubuntu` directly from an external project; execute `make promote ... TARGET_REPO=~/dotfiles-ubuntu --create-pr` to generate an anonymized Pull Request (`OSS_AGNOSTICISM_VIOLATION` gate enforced).
2. **Inside `dotfiles-ubuntu` (Direct Maintenance)**:
   - Run `cd ~/dotfiles-ubuntu && stow -t ~ -R antigravity && make verify` to confirm all 8 verification gates pass.
   - Log changes under `## [Unreleased]` in `CHANGELOG.md` **without bumping `VERSION`**.
   - **NEVER include `git push` on working/enrichment commits in `dotfiles-ubuntu`**. Pushing to the public Open-Source remote requires an explicit, conscious version release via `/release` (`skills/release/SKILL.md`):
   ```bash
   ### dotfiles-ubuntu (local [Unreleased] commit only — publish via /release)
   cd ~/dotfiles-ubuntu
   git add -u
   git commit -m "enrich: [summary of upstream promotions]"
   ```

---

## Rules

- **Read before writing** — always scan existing content before proposing changes
- **Never auto-merge** — all promotions require explicit user approval
- **Enforce 1-hop horizon** — `Squad` $\rightarrow$ `Department` $\rightarrow$ `Corporate Root 0` $\rightarrow$ `dotfiles-ubuntu` (never skip tiers)
- **Dual-regime push discipline** — agile `git push` is allowed for authorized owners in internal corporate/departmental repos (`is_oss_community_horizon: false`), whereas `dotfiles-ubuntu` (`is_oss_community_horizon: true`) requires PR-based intake from `Root 0` and local `[Unreleased]` commits (pushing only on explicit `/release`)
- **One direction per execution** — either promote upstream OR sync downstream, not both simultaneously
- **Log the enrichment** — update `CHANGELOG.md` under `## [Unreleased]`
