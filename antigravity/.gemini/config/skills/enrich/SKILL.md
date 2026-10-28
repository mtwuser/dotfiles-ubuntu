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

### §2.3 Layer Classification

For each candidate, determine the correct target layer:

| If the pattern... | Target Layer |
|---|---|
| Applies to ANY project regardless of stack | **A (dotfiles-ubuntu root)** |
| Applies to a cross-cutting department, team, or mounted service layer | **D (`~/dotfiles-ubuntu/layers/<layer-name>/` via `layer-subtree.sh push`)** |
| Applies to any project using THIS framework | **B (framework repo or `templates/<stack>/`)** |
| Only applies to this specific product/domain | **C (stays in project)** |

> [!IMPORTANT]
> **Never promote stack-specific rules to Layer A.** FastAPI patterns stay in Layer B (framework repo).
> Django patterns stay in Layer B (Django framework/project repo). Only universal principles (zero-residue, AAA,
> coverage gates) belong in Layer A.

---

## §3. Extraction Proposal

Generate a structured proposal for the user:

```markdown
## Enrichment Proposal — [date]

### Promote to Layer A (dotfiles-ubuntu)
- [ ] [rule/skill name]: [what changes] — [why it's universal]

### Promote to Layer B (framework)
- [ ] [rule/skill name]: [what changes] — [why it's framework-wide]

### Update Layer C from upstream
- [ ] [project]: [rule/skill] needs sync from [shared version]

### Contradictions / Drift
- ⚠️ [description of conflict]
```

**Wait for user approval before applying any changes.**

---

## §4. Apply & Distribute

After approval:

1. **Apply changes** to the target layer files
2. **Re-stow** if dotfiles-ubuntu was modified (also links any new shared skill): `cd ~/dotfiles-ubuntu && stow -t ~ -R antigravity`
3. **Deliver commit blocks** for each modified repo:

```bash
### dotfiles-ubuntu
cd ~/dotfiles-ubuntu
git add -A
git commit -m "enrich: [summary of upstream promotions]"
git push

### [Framework/Project repo]
cd ~/Projects/[repo]
git add -A
git commit -m "chore: sync rules from shared config"
git push
```

---

## Rules

- **Read before writing** — always scan existing content before proposing changes
- **Never auto-merge** — all promotions require explicit user approval
- **Preserve project-specific context** — do not strip domain examples when promoting; replace them with universal equivalents
- **One direction per execution** — either promote upstream OR sync downstream, not both simultaneously
- **Log the enrichment** — update the project's CHANGELOG with `enrich:` prefix entries
