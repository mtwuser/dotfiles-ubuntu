# dotfiles-ubuntu

[![Version](https://img.shields.io/badge/version-1.4.0-blue.svg)](VERSION)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Ubuntu](https://img.shields.io/badge/Ubuntu-26.04%20LTS-E95420.svg)](https://ubuntu.com/)
[![Antigravity](https://img.shields.io/badge/Google%20Antigravity-2.0-8E44AD.svg)](https://antigravity.google/)

Declarative system manager, dotfile engine, and **Distributed Human-AI Governance ("pAIr programming") Platform** for **Ubuntu 26.04 LTS ("Resolute Raccoon")** and **Google Antigravity 2.0 / Gemini** *(directly extrapolable to **VS Code & GitHub Copilot**, **Cursor**, and **Claude Code**)*.

This repository is designed to be **modular** — you can use the entire suite or pick only the pieces you need:
1. **Ubuntu System Backup, Audit & Restore (`backup.sh`, `audit.sh`, `bootstrap.sh`)** — snapshot your installed APT packages, Snaps, NPM globals, external tools, and GNOME desktop settings into plain-text manifests, audit system drift at any time, or rebuild a machine from scratch.
2. **Dotfile Symlink Management (`bash/`, `git/`)** — manage `~/.bashrc`, `~/.profile`, and `~/.gitconfig` via [GNU Stow](https://www.gnu.org/software/stow/) while keeping personal identity and secrets in untracked local overrides (`~/.bashrc.local`, `~/.gitconfig.local`).
3. **Google Antigravity 2.0 & Multi-Tier AI Governance (`antigravity/`, `templates/`, `docs/`)** — universal `AGENTS.md` behavioral rules, Python 3.14 lifecycle hooks (`PreToolUse` safety guards, auto-format, lint + AST checks, test gate), 11 reusable skills (`/sopen`, `/sclose`, `/continue`, `/enrich`, `/priority`, `/review`, etc.), and project starter templates (`templates/fastapi-hexagonal/`) shared across all three Antigravity surfaces:
   - **Antigravity 2.0 (Agents Desktop App)** — `/opt/antigravity-agents` (state in `~/.gemini/antigravity/`)
   - **Antigravity IDE** — `/opt/antigravity-ide` (state in `~/.gemini/antigravity-ide/`)
   - **Antigravity CLI (`agy`)** — `~/.local/bin/agy` (settings in `~/.gemini/antigravity-cli/`)

> **Enterprise Use Case — Distributed "pAIr programming" Governance & Contextual MCP Federation**:
> Beyond individual workstations, this fork-and-stow model allows organizations to orchestrate Human-AI collaboration across **Corporate**, **Team**, and **Project** tiers, pairing bidirectional rule evolution (`/learn` $\rightarrow$ `/enrich`) with navigable repository documentation (`docs/`). Furthermore, any instance or fork of `dotfiles-ubuntu` hosted on a system, container, or remote server can run as a **zero-dependency, read-only Model Context Protocol (MCP) Server** (`scripts/dotfiles_mcp_server.py`) to expose live environment drift, layer rules, and federated MCP topologies across multi-service architectures. See **[`docs/reference/enterprise_pair_programming_governance.md`](docs/reference/enterprise_pair_programming_governance.md)**, **[`docs/reference/contextual_mcp_and_multi_service_orchestration.md`](docs/reference/contextual_mcp_and_multi_service_orchestration.md)**, and the navigable hub at **[`docs/README.md`](docs/README.md)**.

---

## Quick Start: 3 Main Ways to Use This Repository

You can use this repository **just for Google Antigravity 2.0** (standalone), **fork it to manage and restore your own Ubuntu 26.04 workstation**, or **adopt it as an enterprise/multi-team Human-AI governance platform**.

---

### Path 1: Google Antigravity 2.0 Setup & Usage (Standalone)

Use this path if you want the **Antigravity 2.0 / IDE / CLI** global rules, lifecycle hooks, skills, and project templates without changing your `~/.bashrc`, `~/.gitconfig`, or Ubuntu packages.

#### 1. Install the Global Antigravity Configuration (`~/.gemini/config/`)

```bash
git clone https://github.com/mtwuser/dotfiles-ubuntu.git ~/dotfiles-ubuntu
cd ~/dotfiles-ubuntu
./bootstrap.sh --antigravity
```

What this configures (via GNU Stow tree-unfolding, preserving your local credentials, MCP servers, and plugins):
- **Global Rules (`~/.gemini/config/AGENTS.md`)** — Universal engineering standards (clean code, strict typing, AAA testing, hexagonal boundaries, zero-residue governance).
- **Lifecycle Hooks (`~/.gemini/config/hooks.json` + `scripts/`)** — Deterministic `PreToolUse` safety guards (`pre_tool_guard.py`), automatic `ruff format` on file edits (`PostToolUse`), lint + AST checks with `force_continue` (`PostInvocation`), and test verification (`Stop`).
- **11 Global Skills (`~/.gemini/config/skills/`)** — Available immediately in every workspace across Antigravity Agents, IDE, and CLI:
  - **Session & Workflow Slash Commands**: `/sopen` (initialize session & sync state), `/sclose` (close session, update changelog & commit), `/continue` (mid-session checkpoint), `/priority` (pick next task from governance files), `/review` (audit code, architecture & tests), `/enrich` (extract reusable patterns from a project into global skills).
  - **Procedural Skills**: `architecture-review`, `governance`, `refactoring`, `testing`, `validation`.
- **Desktop Launchers (`~/.local/share/applications/`)** — Application menu entries for Antigravity Agents and Antigravity IDE.

#### 2. Install or Update the Antigravity Binaries (Optional)

If you also want to install or update the **Antigravity 2.0 (Agents)** or **Antigravity IDE** desktop apps, download their `.zip` or `.tar.gz` archives into `~/Downloads/` and run:

```bash
cd ~/dotfiles-ubuntu
./scripts/antigravity-install.sh --all      # or --agents / --ide
```

#### 3. Bootstrap a Project with a Layer 2 Starter Template (Optional)

Global rules (`~/.gemini/config/`) apply to all projects automatically. To also scaffold project-local rules and governance (`.agents/rules/`, `.agents/skills/start/`) in a specific repository:

```bash
mkdir -p <your-project>/.agents
cp -r ~/dotfiles-ubuntu/templates/fastapi-hexagonal/{rules,skills} <your-project>/.agents/
cp ~/dotfiles-ubuntu/templates/fastapi-hexagonal/governance/SESSION.md <your-project>/.agents/SESSION.md
cp ~/dotfiles-ubuntu/templates/fastapi-hexagonal/governance/{WORKTASK,WORKROAD,WORKVALI,BACKLOG,CHANGELOG}.md <your-project>/
```

---

### Path 2: Fork & Manage YOUR Own Ubuntu 26.04 System

The `system/` folder in this repository ships with the author's workstation manifests as a reference baseline. By **forking** this repository, you can turn it into your personal Ubuntu 26.04 backup, audit, and recovery engine in minutes — **without installing any of the author's personal apps**.

#### Phase A — Initialize Your Fork on Your Current Ubuntu 26.04 PC

```bash
# 1. Fork this repository on GitHub, then clone YOUR fork locally
git clone https://github.com/<your-user>/dotfiles-ubuntu.git ~/dotfiles-ubuntu
cd ~/dotfiles-ubuntu

# 2. Overwrite system/* manifests with YOUR machine's current packages & GNOME settings
./backup.sh

# 3. Verify that your system and manifests match (0 drift)
./audit.sh

# 4. Link dotfiles (.bashrc, .profile, .gitconfig, Antigravity)
#    Your personal Git user.name / user.email are automatically preserved in ~/.gitconfig.local
./bootstrap.sh --stow

# 5. Commit and push your personal baseline to your fork
git add -A && git commit -m "chore: initialize manifests from my Ubuntu 26.04 workstation" && git push
```

> **How `./backup.sh` replaces the author's packages with yours**:
> Running `./backup.sh` scans your machine and rewrites `system/packages-manual.txt` (your manual APT packages), `system/snaps.txt` (your application Snaps), `system/npm-globals.txt` (your global NPM tools), `system/nvm-default.txt`, `system/external.txt` (only the recipes from `system/external/` that are actually installed on your PC), `system/gnome-extensions.txt`, and `system/gnome-settings.dconf`. Any software you don't use (e.g., AutoFirma, Proton, Discord) is automatically excluded.

#### Phase B — Day-to-Day Usage on Your Machine (Backup & Audit)

Whenever you install or remove packages, tweak GNOME settings, or edit your dotfiles:

```bash
cd ~/dotfiles-ubuntu

# Check what changed on your machine compared to your repo (read-only)
./audit.sh

# Capture the new state into system/* manifests and push to your fork
./backup.sh
git diff
git add -A && git commit -m "chore: sync system manifests" && git push
```

- **Want to enable an external tool from the `system/external/` catalog (e.g. Docker, Chrome, GCloud CLI)?**
  Add its recipe path (e.g. `apt-repo/docker.sh`) to `system/external.txt` and run `./bootstrap.sh --external` (or install it manually and run `./backup.sh`).
- **Have hardware-specific packages (e.g. NVIDIA drivers) you don't want in your portable manifest?**
  Add their package names to `.audit-ignore` (gitignored per machine).

#### Phase C — Restore or Provision a Second / Fresh Ubuntu 26.04 PC from Your Fork

When you set up a new laptop or reinstall Ubuntu 26.04 from scratch, clone **your fork** and run `bootstrap.sh`:

```bash
git clone https://github.com/<your-user>/dotfiles-ubuntu.git ~/dotfiles-ubuntu
cd ~/dotfiles-ubuntu

./bootstrap.sh          # Interactive mode — asks confirmation before each step
# or
./bootstrap.sh --all    # Unattended mode — installs all your packages, settings & symlinks
```

#### Individual Bootstrap Modes (Pick Only What You Need)

```bash
./bootstrap.sh --antigravity   # Only ~/.gemini/config/ + desktop launchers
./bootstrap.sh --stow          # Only symlink bash/, git/, and antigravity/ modules
./bootstrap.sh --packages      # Only APT + Snaps + NPM globals from system/*.txt
./bootstrap.sh --external      # Only external recipes enabled in system/external.txt
./bootstrap.sh --nvm           # Only NVM + default Node.js version
./bootstrap.sh --gnome         # Only GNOME extensions + dconf desktop settings
```

---

### Path 3: Enterprise & Team Human-AI Governance ("pAIr programming" at Scale)

Organizations can use this repository's hierarchical fork model to standardize AI-assisted software engineering across teams without losing project autonomy:

1. **Corporate Baseline (`Layer A`)**: Maintain an organization-wide fork defining universal security, typing, AAA testing, and commit rules (`AGENTS.md` + `hooks.json` + global `skills/`).
2. **Team / Stack Blueprints (`Layer B`)**: Maintain team forks or `templates/<stack>/` catalogs for specific architectures (e.g., Python/FastAPI Hexagonal DDD, Data/BigQuery, Web Islands).
3. **Project Context & Navigable Docs (`Layer C` + `docs/`)**: Combine project-local `.agents/` rules and `WORKTASK.md` trackers with a structured, indexed `docs/` directory (`docs/README.md`, `docs/architecture/`) maintained alongside code (or automated with **Google Jules**, **Gemini Code Assist Enterprise**, **NotebookLM**, and **Google Developer Knowledge MCP**).
4. **Organic Bidirectional Evolution**: Strategic standards flow downward (`Corporate → Team → Project` via `/sopen`), while battle-tested patterns discovered in projects (`/learn`) are promoted upward (`/enrich` `Project → Team → Corporate`) to benefit the entire organization immediately.
5. **Optional Contextual MCP Server & Multi-Service Orchestration (`scripts/dotfiles_mcp_server.py`)**: Run any fork or container instance of `dotfiles-ubuntu` as a zero-dependency, read-only MCP server over `stdio`, `docker exec -i`, or `ssh` — either as a **standalone container/node health & docs introspector** or as a **Federated Context Mesh** orchestrating multiple MCPs across complex multi-service topologies.

📖 **Full Architecture & Setup Guides**:
- **[`docs/reference/enterprise_pair_programming_governance.md`](docs/reference/enterprise_pair_programming_governance.md)** — Corporate $\rightarrow$ Team $\rightarrow$ Project governance, Google AI docs tooling, and 1:1 VS Code / GitHub Copilot mapping.
- **[`docs/reference/contextual_mcp_and_multi_service_orchestration.md`](docs/reference/contextual_mcp_and_multi_service_orchestration.md)** — Standalone & federated MCP server architecture and step-by-step configuration (`mcp_config.json`, `.vscode/mcp.json`, Docker containers, remote SSH servers).
- **[`docs/README.md`](docs/README.md)** — Navigable documentation index and subsystem map.

---

## Repository Structure

```
~/dotfiles-ubuntu/
│
├── bash/                              ← stow module: shell config
│   ├── .bashrc                        ←   → ~/.bashrc
│   └── .profile                       ←   → ~/.profile
│
├── git/                               ← stow module: git global config
│   └── .gitconfig                     ←   → ~/.gitconfig
│
├── antigravity/                       ← stow module: Antigravity IDE config
│   ├── .gemini/
│   │   └── config/
│   │       ├── AGENTS.md              ←   → ~/.gemini/config/AGENTS.md
│   │       ├── hooks.json             ←   → ~/.gemini/config/hooks.json
│   │       ├── scripts/               ←   → ~/.gemini/config/scripts/
│   │       └── skills/                ←   → ~/.gemini/config/skills/<name>/
│   │           ├── architecture-review/, governance/, refactoring/, testing/, validation/
│   │           └── sopen/, sclose/, continue/, enrich/, priority/, review/
│   └── .local/share/applications/
│       ├── antigravity-agents.desktop ←   → ~/.local/share/applications/
│       └── antigravity-ide.desktop    ←   → ~/.local/share/applications/
│
├── docs/                              ← NOT stow — navigable architecture & reference hub
│   ├── README.md                      ←   Documentation index, subsystem map & AI agent lookup
│   ├── architecture/                  ←   Normative technical specifications
│   │   ├── 01_system_and_stow_engine.md           ← Ubuntu 26.04 engine, 3-stage APT filter, Stow
│   │   ├── 02_antigravity_governance_and_hooks.md ← Token budget, 4 hook JSON contracts, 11 skills
│   │   └── 03_contextual_mcp_and_federation.md    ← Zero-dependency MCP server contract & schema
│   └── reference/                     ←   Enterprise use cases & maintainer extension guides
│       ├── enterprise_pair_programming_governance.md         ← Enterprise Human-AI governance & Copilot mapping
│       ├── contextual_mcp_and_multi_service_orchestration.md ← Node/Container MCP & multi-service orchestration
│       └── developer_and_extension_guide.md                  ← Maintainer playbook for evolving dotfiles-ubuntu
│
├── .github/
│   ├── ISSUE_TEMPLATE/                ← GitHub Issue Forms (bug report, feature request, config)
│   ├── PULL_REQUEST_TEMPLATE.md       ← Pull Request verification checklist
│   └── workflows/ci.yml               ← GitHub Actions CI verification workflow
│
├── templates/                         ← NOT stow — project starter templates
│   └── fastapi-hexagonal/             ←   FastAPI + Hexagonal DDD + HTMX (rules, skills, governance)
│
├── scripts/                           ← NOT stow — utility, MCP, subtree & CI verification scripts
│   ├── antigravity-install.sh         ←   Install/update Antigravity IDE & Agents
│   ├── audit-global-config.sh         ←   Verify ~/.gemini/config/ symlinks & orphans
│   ├── dotfiles_mcp_server.py         ←   Zero-dependency read-only Contextual MCP Server (stdio)
│   ├── layer-subtree.sh               ←   Upstream fork sync & git subtree context graph manager (layers/*)
│   └── verify-repo.sh                 ←   Deterministic CI & pre-commit verification suite
│
├── system/                            ← NOT stow — declarative system & MCP layer manifests
│   ├── packages-manual.txt            ←   APT packages (manual only, official Ubuntu 26.04 repos)
│   ├── snaps.txt                      ←   Snap application packages (excludes base/runtime snaps)
│   ├── npm-globals.txt                ←   NPM global packages
│   ├── external.txt                   ←   Active external recipes enabled on this machine
│   ├── gnome-extensions.txt           ←   GNOME Shell extensions
│   ├── gnome-settings.dconf           ←   GNOME desktop settings (declarative dconf)
│   ├── nvm-default.txt                ←   Default Node.js version
│   ├── mcp-layer.json                 ←   Contextual MCP layer identity & federated MCP topology
│   └── external/                      ←   Catalog of available external package recipes
│       ├── apt-repo/                  ←     Packages with own DEB822 APT repo (.sources)
│       │   ├── docker.sh, google-chrome.sh
│       │   ├── google-cloud-cli.sh, protonvpn.sh
│       ├── deb-url/                   ←     Direct .deb download recipes
│       │   ├── autofirma.sh, discord.sh
│       │   ├── proton-mail.sh
│       │   └── proton-pass.sh
│       └── script/                    ←     Custom install scripts
│           ├── antigravity-ide.sh
│           └── antigravity-agents.sh
│
├── tests/                             ← ❌ NOT stowed — automated test suite (100% branch coverage)
│   ├── unit/                          ←   1:1 unit tests for all 5 Python hooks & MCP server
│   │   ├── test_pre_tool_guard.py
│   │   ├── test_post_edit_format.py
│   │   ├── test_post_invocation_lint.py
│   │   ├── test_stop_verify_tests.py
│   │   └── test_dotfiles_mcp_server.py
│   └── imp/                           ←   stdio JSON-RPC 2.0 & Bash CLI contract tests
│       ├── test_mcp_and_hooks_stdio.py
│       └── test_cli_scripts.py
│
├── bootstrap.sh                       ← restore system from manifests
├── backup.sh                          ← capture current system state
├── audit.sh                           ← detect drift & residual files
├── Makefile                           ← dev/test automation (make install, install-runtime, test-cov, lint, verify)
├── pyproject.toml                     ← pytest, 100% branch coverage, ruff & mypy --strict config
├── requirements.txt                   ← base runtime dependencies (0 packages in upstream; extensible in forks)
├── requirements-dev.txt               ← dev/test dependencies (-r requirements.txt + pytest, pytest-cov, ruff, mypy)
├── VERSION                            ← semantic version (single source of truth)
├── ACCESSIBILITY.md                   ← accessibility commitment & terminal/a11y support
├── CHANGELOG.md                       ← release history (Keep a Changelog + SemVer)
├── CODE_OF_CONDUCT.md                 ← Contributor Covenant v2.1
├── CONTRIBUTING.md                    ← contribution & architecture guidelines
├── SECURITY.md                        ← secret & identity isolation policy
├── LICENSE                            ← MIT License
├── .gitignore
└── README.md
```

### Stow modules vs regular directories

| Directory | Stow module? | Stow target | Purpose |
|-----------|:---:|-------------|---------|
| `bash/` | ✅ | `~/.bashrc`, `~/.profile` | Shell configuration |
| `git/` | ✅ | `~/.gitconfig` | Git global settings |
| `antigravity/` | ✅ | `~/.gemini/config/*`, `~/.local/share/applications/*` | Antigravity config + .desktop entries |
| `docs/` | ❌ | — | Navigable documentation hub & enterprise Human-AI governance architecture |
| `templates/` | ❌ | — | Project starter templates (copied manually) |
| `scripts/` | ❌ | — | Utility, MCP, subtree & CI scripts (`antigravity-install.sh`, `audit-global-config.sh`, `dotfiles_mcp_server.py`, `layer-subtree.sh`, `verify-repo.sh`) |
| `system/` | ❌ | — | Package manifests, MCP layer topology (`mcp-layer.json`), & external recipe catalog |
| `layers/` | ❌ | — | Optional mounted `git subtree` context forks (`layers/<name>/` for departmental/service/environment orchestration) |
| `tests/` | ❌ | — | Unit (`tests/unit/`) & integration (`tests/imp/`) test suite with 100% branch coverage |

---

## Configuration Architecture

Configuration follows a 3-layer hierarchy. Each layer extends the one above it:

```
Layer 1: Shared (Global)         ← This repo: ~/dotfiles-ubuntu/antigravity/
Layer 2: Templates (Reusable)    ← This repo: ~/dotfiles-ubuntu/templates/
Layer 3: Custom (Project-local)  ← Each project: <project>/.agents/
```

### Layer 1: Shared (Global)

Managed by the `antigravity/` stow module. Applied to **all projects** automatically via symlinks into `~/.gemini/config/`.

Contains:
- **AGENTS.md** — Universal rules (reusability, robustness, strict typing, AAA testing, zero-residue governance, model delegation)
- **hooks.json + scripts/** — Automated Python 3.14 lifecycle hooks:
  - `pre_tool_guard.py` (`PreToolUse`) — Deterministically blocks non-empty writes to consumer `src/**/__init__.py` or `tests/**/__init__.py`, manual edits to `alembic/versions/*.py`, and automatic execution of mutating `git` (`add`, `commit`, `push`, `reset --hard`, `clean -f`) or `alembic` commands
  - `post_edit_format.py` (`PostToolUse`) — Runs `ruff format` automatically whenever the agent edits a `.py` file
  - `post_invocation_lint.py` (`PostInvocation`) — Runs `ruff check` and AST architecture/test checks (`check_project`, `check_tests`) on modified and untracked Python files at the end of a turn (`force_continue` on errors)
  - `stop_verify_tests.py` (`Stop`) — Verifies affected unit tests pass on modified and untracked Python workspaces before concluding a task
- **skills/** — 6 interactive slash-command skills and 5 procedural engineering skills:

#### Global Slash Commands (`~/.gemini/config/skills/<command>/SKILL.md`)

| Command | When to Run | Purpose & Actions |
|---------|-------------|-------------------|
| `/sopen` | Start of every session | Pulls latest `~/dotfiles-ubuntu`, recovers session context across 3 tiers (`brain/` → `.agents/SESSION.md` → `git status` + `WORKTASK.md`), and activates project-specific `/start` if present |
| `/continue` | Mid-session (between tasks or before `/compact`) | Checkpoints active progress into `WORKTASK.md` and `.agents/SESSION.md` so zero context is lost if the conversation is compacted or closed |
| `/sclose` | End of every session | Consolidates completed tasks (`WORKTASK.md` → `CHANGELOG.md`), updates `.agents/SESSION.md`, syncs `~/dotfiles-ubuntu` if modified, and outputs ready-to-run `git commit` blocks per repository |
| `/priority` | When picking the next task | Audits `WORKTASK.md` → `WORKROAD.md` → `roadmaps/` in strict priority order and recommends the next actionable work item |
| `/review` | After implementing a feature or before release | Audits code structure, Clean Code compliance, hexagonal architecture boundaries, and AAA test coverage against global and project rules |
| `/enrich` | Periodically / after project milestones | Scans `.agents/rules/` and `.agents/skills/` across active workspace repos and compares them with `~/dotfiles-ubuntu` to promote universal patterns upward (`Project → Framework → Global`) or fix downward drift |

> **`/learn` (built-in Antigravity command) vs `/enrich` (this repository)**:
> They are complementary steps of the knowledge lifecycle:
> - **During a task (`/learn` — native)**: When you correct the agent in chat or solve a tricky project setup, `/learn` captures that lesson immediately from the current conversation into a local rule/skill in your current project (`.agents/`).
> - **Across projects (`/enrich` — `dotfiles-ubuntu`)**: Built-in `/learn` does not know about your multi-repo layer hierarchy (`Layer A: ~/dotfiles-ubuntu` ↔ `Layer B: framework` ↔ `Layer C: product`) or GNU Stow. Running `/enrich` audits the rules accumulated across your projects, promotes mature stack-agnostic patterns upstream to `~/dotfiles-ubuntu` (while keeping framework-specific patterns in Layer B), reconciles contradictions, and runs `stow -t ~ -R antigravity`.

#### Global Procedural Skills (`~/.gemini/config/skills/<skill>/SKILL.md`)

Activated automatically by the agent when matching tasks arise (or explicitly on request):

| Skill | When Activated | Purpose |
|-------|----------------|---------|
| `architecture-review` | Designing architecture or reviewing specifications | Performs intersection audits, unifies orthogonal classifications, and enforces cross-document naming coherence |
| `governance` | Promoting work between lifecycle tiers | Enforces one-way work flow (`roadmaps/ → WORKROAD.md → WORKTASK.md → CHANGELOG.md`), cross-task analysis, and clean-room knowledge extraction |
| `refactoring` | Splitting large files (>400 lines) or "God Components" | Guides safe, incremental extraction of cohesive modules while preserving public contracts and test coverage |
| `testing` | Writing, fixing, or auditing test suites | Enforces AAA (`Arrange-Act-Assert`) structure, hexagonal mock boundaries, naming conventions, and branch coverage audits |
| `validation` | Manual UI / web QA sessions | Drives structured human-agent manual verification checklists tracked in `WORKVALI.md` |

### Layer 2: Templates (Reusable)

Stack-specific configurations that can be copied into new projects. NOT symlinked — copied once, then customized.

```bash
# Copy template rules & skills to your new project
mkdir -p <your-project>/.agents
cp -r ~/dotfiles-ubuntu/templates/fastapi-hexagonal/{rules,skills} <your-project>/.agents/

# Then customize:
# 1. Update rules/environment.md with your project paths
# 2. Adjust rules/coding.md for your stack conventions
# 3. Modify rules/testing.md for your test framework
```

### Layer 3: Custom (Project-Specific)

Once a template is copied into a project, it becomes that project's custom configuration:

```
my-project/
├── .agents/                    ← Layer 3 (custom) — committed to project repo
│   ├── rules/
│   │   ├── coding.md           ← Stack-specific coding rules
│   │   ├── environment.md      ← Project paths, commands
│   │   ├── governance.md       ← Work lifecycle adapted for this project
│   │   └── testing.md          ← Test patterns for this stack
│   ├── skills/                 ← Project-specific procedural guides
│   │   └── start/SKILL.md      ← Project startup sequence (`/start`)
│   └── SESSION.md              ← Session state (cross-machine recovery)
├── BACKLOG.md                  ← Tech debt observations
├── CHANGELOG.md                ← Completed work
├── WORKROAD.md                 ← Planned roadmap
├── WORKTASK.md                 ← Active work items
├── WORKVALI.md                 ← Manual validation tracker
└── docs/                       ← Navigable repository knowledge (architecture, reference, index)
```

Custom rules **extend** the shared layer. They live in the project's own git repo and travel with it.

### Navigable Repository Knowledge (`docs/`) & Cross-IDE Portability

When an AI agent operates inside a repository configured with this model, it draws simultaneously on **4 pillars of context**:
1. **Organization / Corporate Rules (`Layer A`)** — universal engineering rigor, security, and AAA testing (`AGENTS.md`).
2. **Team / Stack Blueprints (`Layer B`)** — architectural and tech-stack conventions (`templates/`).
3. **Project Rules, Skills & Tasks (`Layer C`)** — domain invariants (`.agents/`) and active work state (`WORKTASK.md`, `SESSION.md`).
4. **Navigable Repository Documentation (`docs/`)** — structured architecture specs (`docs/architecture/`), reference guides (`docs/reference/`), and a navigable index (`docs/README.md`) maintained in-flow or automated with **Google Jules**, **Gemini Code Assist Enterprise**, **NotebookLM**, and **Google Developer Knowledge MCP**.

> **Portability to VS Code & GitHub Copilot**: While natively implemented for **Google Antigravity 2.0 & Gemini**, this exact Markdown-driven hierarchy maps 1:1 to **VS Code & GitHub Copilot** (`AGENTS.md`, `.github/copilot-instructions.md`, `.github/instructions/*.instructions.md`, `.github/prompts/*.prompt.md`), **Cursor** (`.cursor/rules/*.mdc`), and **Claude Code**. See **[`docs/reference/enterprise_pair_programming_governance.md`](docs/reference/enterprise_pair_programming_governance.md)** for the full architecture and equivalence table.

### Dynamic Workspace Detection

All shared skills use `<PROJECT_ROOT>` as a placeholder, resolved at runtime from Antigravity's workspace metadata. Sub-repos are detected dynamically by scanning for `.git` directories — no hardcoded paths.

---

## How It Works

### Stow modules

Each stow module mirrors `$HOME`. When activated, stow creates symlinks:

```
~/dotfiles-ubuntu/bash/.bashrc                            → ~/.bashrc
~/dotfiles-ubuntu/git/.gitconfig                          → ~/.gitconfig
~/dotfiles-ubuntu/antigravity/.gemini/config/AGENTS.md    → ~/.gemini/config/AGENTS.md
~/dotfiles-ubuntu/antigravity/.gemini/config/skills/<name>/ → ~/.gemini/config/skills/<name>/
~/dotfiles-ubuntu/antigravity/.local/share/applications/  → ~/.local/share/applications/
```

**Manage modules:**

```bash
cd ~/dotfiles-ubuntu

# Activate a module
stow -t ~ bash

# Deactivate a module
stow -t ~ -D bash

# Re-stow after changes
stow -t ~ -R bash
```

> **Important**: Because the repo lives at `~/dotfiles-ubuntu` (not directly under `~` as a child named like the module), you must always pass `-t ~` to stow. The `bootstrap.sh` script handles this automatically.

#### Why `~/.gemini/config/` uses Stow Tree Unfolding (individual symlinks)

Unlike `~/.bashrc` (which is a single file symlink), `~/.gemini/config/` and `~/.gemini/config/skills/` are **real directories** that mix tracked dotfiles with machine-local files:
- **Tracked via Stow (`~/dotfiles-ubuntu/antigravity/`)**: `AGENTS.md`, `hooks.json`, `scripts/`, and the 11 core skills inside `skills/<name>/`.
- **Machine-local (untracked)**: `config.json`, `mcp_config.json`, `plugins/`, `projects/`, `sidecars/`, `.ruff_cache/`, and locally installed extension/cloud skills inside `skills/`.

Because `~/.gemini/config/` and `~/.gemini/config/skills/` already exist as real directories, GNU Stow automatically performs **tree unfolding**: it creates individual symlinks for each tracked item (`AGENTS.md`, `hooks.json`, `scripts/`, and each shared skill folder `skills/<name>`) without touching your local credentials, MCP servers, or third-party skills.

You can verify the health of `~/.gemini/config/` symlinks at any time with:

```bash
~/dotfiles-ubuntu/scripts/audit-global-config.sh
```

### Directory & Path Conventions (Stow, Scripts & Workspaces)

Several paths across the system play specific roles in GNU Stow, helper scripts, and Antigravity lifecycle hooks/skills:

| Path | Managed by Stow? | Role & Scripts / Processes that use it |
|------|:----------------:|----------------------------------------|
| `~/dotfiles-ubuntu/` | Source repo | Canonical source of truth. Referenced by `bootstrap.sh`, `backup.sh`, `audit.sh`, `scripts/audit-global-config.sh`, and global skills (`/sopen`, `/sclose`, `/continue`, `/enrich`) for automatic sync and `stow -t ~ -R antigravity`. |
| `~/.gemini/config/` | ✅ (Tree-unfolded) | Shared across **all 3 Antigravity surfaces** (Desktop Agents, IDE, CLI). Stow links `AGENTS.md`, `hooks.json`, `scripts/`, and each shared skill in `skills/<name>/` while preserving local untracked files (`config.json`, `mcp_config.json`, `plugins/`, `projects/`, `sidecars/`). |
| `~/.local/share/applications/` | ✅ (Tree-unfolded) | Desktop launchers (`antigravity-agents.desktop` and `antigravity-ide.desktop`) linked by the `antigravity` stow module and refreshed by `update-desktop-database`. |
| `~/.bashrc`, `~/.profile`, `~/.gitconfig` | ✅ | Symlinked from `bash/` and `git/` stow modules. Automatically include untracked machine-local overrides (`~/.bashrc.local` and `~/.gitconfig.local`). |
| `~/Projects/<project>/` | ❌ (Never stowed) | Standard workspace location for user repositories. **GNU Stow never creates symlinks inside `~/Projects/`**: global rules/skills in `~/.gemini/config/` apply automatically to every workspace, while project-specific rules (`<project>/.agents/`) are copied from `templates/` and committed to each project's Git repo. Lifecycle hooks (`scripts/*.py`) receive the active project path dynamically via `workspacePaths`, and `/enrich` reads the active workspace without scanning unrelated folders in `~/Projects/`. |
| `~/Downloads/` | ❌ | Staging directory used by `scripts/antigravity-install.sh`. The installer automatically detects and extracts `Antigravity.zip` / `Antigravity.tar.gz` (or `Antigravity-x64.*`) and `Antigravity IDE.zip` / `Antigravity IDE.tar.gz` from `~/Downloads/` before installing. |
| `/opt/antigravity-agents/` & `/opt/antigravity-ide/` | ❌ | Target installation directories populated by `scripts/antigravity-install.sh`, verified by `bootstrap.sh`/`audit.sh` (`system/external/script/antigravity-*.sh`), and targeted by `.desktop` launchers. |
| `~/AppImage/` | ❌ | Monitored by `audit.sh` (`--clean` mode) to detect and optionally clean up orphaned AppImage directories. |

### System manifests & external recipe catalog

The `system/` directory contains plain-text manifests of installed software, consumed by `bootstrap.sh`, verified by `audit.sh`, and updated by `backup.sh`:

| File / Directory | Purpose |
|------------------|---------|
| `system/packages-manual.txt` | Manually installed Ubuntu 26.04 APT packages (automatically excludes external & machine-local driver packages) |
| `system/snaps.txt` | Installed Snap applications (automatically excludes `core*`, `bare`, `gnome-*`, and `mesa-*` runtime snaps) |
| `system/npm-globals.txt` | Global NPM packages under the active Node.js version |
| `system/nvm-default.txt` | Default Node.js major version managed by NVM |
| `system/external.txt` | List of external recipes from `system/external/` enabled on this machine (auto-detected by `./backup.sh`) |
| `system/external/{apt-repo,deb-url,script}/` | **Recipe catalog** for third-party software (Docker, Chrome, GCloud CLI, Proton, Discord, AutoFirma, Antigravity). Only recipes listed in `system/external.txt` are required by `audit.sh` or installed by `bootstrap.sh --external`. To enable a new recipe from the catalog on a fresh machine, add its relative path (e.g. `apt-repo/docker.sh`) to `system/external.txt` and run `./bootstrap.sh --external`. |
| `system/gnome-extensions.txt` | Installed GNOME Shell extension UUIDs |
| `system/gnome-settings.dconf` | Declarative GNOME desktop settings (keybindings, interface, touchpad, dock, tiling) — excludes private/ephemeral state |
| `system/mcp-layer.json` | Declarative layer/node identity (`corporate`, `team`, `service-node`, `workstation`), upstream lineage, and federated MCP topology served by `scripts/dotfiles_mcp_server.py` |

---

## Daily Usage

### After installing/removing packages

```bash
cd ~/dotfiles-ubuntu
./backup.sh
git diff
git add -A && git commit -m "chore: update system manifests" && git push
```

### Adding a new dotfile to track

```bash
# Example: track SSH config
mkdir -p ~/dotfiles-ubuntu/ssh/.ssh
cp ~/.ssh/config ~/dotfiles-ubuntu/ssh/.ssh/config
cd ~/dotfiles-ubuntu && stow -t ~ ssh
git add -A && git commit -m "feat: add ssh config module"
```

### Installing / updating Antigravity IDE & Agents

Download the latest release archives (`.zip` or `.tar.gz`) directly into `~/Downloads/` with their standard filenames:
- **Antigravity 2.0 (Agents)**: `~/Downloads/Antigravity.zip` or `~/Downloads/Antigravity.tar.gz` *(also supports `Antigravity-x64.zip` / `.tar.gz`, or pre-extracted `~/Downloads/Antigravity/Antigravity-x64/`)*
- **Antigravity IDE**: `~/Downloads/Antigravity IDE.zip` or `~/Downloads/Antigravity IDE.tar.gz` *(or pre-extracted `~/Downloads/Antigravity IDE/`)*

Then run:

```bash
cd ~/dotfiles-ubuntu
./scripts/antigravity-install.sh            # interactive
./scripts/antigravity-install.sh --all      # install/update both
./scripts/antigravity-install.sh --agents   # Agents only
./scripts/antigravity-install.sh --ide      # IDE only
```

The script **automatically extracts the `.zip` or `.tar.gz` archives from `~/Downloads/`**, backs up the previous installation (`/opt/antigravity-*.backup`), copies the new release into `/opt/antigravity-agents` and `/opt/antigravity-ide`, and sets Electron sandbox permissions (`chrome-sandbox 4755`). Desktop entries (`antigravity-agents.desktop` and `antigravity-ide.desktop`) are managed via the `antigravity/` stow module.

> **Note (`bootstrap.sh --all` vs `scripts/antigravity-install.sh --all`)**:
> `./bootstrap.sh --all` (or `--external`) checks whether `/opt/antigravity-agents/antigravity` and `/opt/antigravity-ide/antigravity-ide` already exist and **skips** them if installed (idempotent initial provisioning). To **upgrade** an existing installation after downloading a new release, always run `./scripts/antigravity-install.sh --all`.

### Multi-machine sync

```bash
# Starting work on any machine
cd ~/dotfiles-ubuntu && git pull --ff-only

# After changes
cd ~/dotfiles-ubuntu && git add -A && git commit -m "..." && git push
```

The Antigravity skills `/sopen` and `/sclose` handle this automatically (§0 and §3.5).

### Auditing system drift

```bash
cd ~/dotfiles-ubuntu
./audit.sh              # read-only — shows discrepancies
./audit.sh --clean      # interactive — offers to remove residual files
```

The audit compares the current system state against the repo manifests bidirectionally:
- **Stow symlinks & Tree Unfolding** — verifies all module files are correctly linked and `~/.gemini/config/` is not directory-folded
- **APT / Snap / NPM / GNOME Extensions** — detects packages installed on the machine but not tracked in `system/`, and vice versa
- **External recipes & APT repos (`system/external.txt`)** — detects untracked external packages, missing enabled recipes, and disabled DEB822 `.sources` repositories
- **Residual files** — finds bootstrap backups (`*.backup.*`) and orphaned directories
- **Repo status** — uncommitted changes, unpushed commits

---

## Customization

### Adding a new shared skill

Create `antigravity/.gemini/config/skills/<name>/SKILL.md` with YAML frontmatter:

```markdown
---
name: my-skill-name
description: "When to use this skill"
---

# Skill Title
[instructions]
```

### Adding a new shared command skill

Slash commands (e.g. `/sopen`) are skills too. Create `antigravity/.gemini/config/skills/<name>/SKILL.md` — the directory name becomes the `/<name>` command:

```markdown
---
name: <name>
description: one-line description of what this command does and when to use it
---

# Command Title — `/<name>`
[steps]
```

After adding, re-stow to update symlinks:

```bash
cd ~/dotfiles-ubuntu && stow -t ~ -R antigravity
```

### Skill distribution model

Shared skills live in `dotfiles-ubuntu` and are installed in a single layer:

```
dotfiles-ubuntu/antigravity/.gemini/config/skills/sopen/SKILL.md   (source of truth)
    ↓ stow -t ~
~/.gemini/config/skills/sopen/                                     (global symlink)
```

Global skills are discovered by Antigravity in **every** workspace — no per-project symlinks are needed. Projects only commit **project-specific** skills (e.g., `.agents/skills/start/SKILL.md`) to git.

> **Why symlinks instead of copies?** Single source of truth. Update a skill in `dotfiles-ubuntu`, run `stow -R antigravity`, and every project sees the update immediately — no need to propagate copies.

---

## Bootstrap Modes

| Flag | Installs |
|------|----------|
| *(no flag)* | Interactive — asks before each step |
| `--antigravity` | Only Antigravity global rules, skills, and lifecycle hooks (`~/.gemini/config/`) |
| `--all` | Everything without prompting |
| `--packages` | APT + Snaps + NPM globals |
| `--stow` | All dotfile symlinks (bash + git + antigravity) |
| `--nvm` | NVM + Node.js |
| `--gnome` | GNOME extensions list + dconf settings |
| `--external` | External packages enabled in `system/external.txt` (APT `.sources` repos, `.deb` downloads, custom scripts) |
| `--help` / `-h` | Show usage help |

---

## Audit Modes

| Flag | Action |
|------|--------|
| *(no flag)* | Read-only audit — shows all discrepancies |
| `--clean` | Interactive cleanup — offers to delete residual files |
| `--help` / `-h` | Show usage help |

### Machine-local exclusions

Create `.audit-ignore` (gitignored) to suppress warnings for hardware-specific packages:

```bash
# .audit-ignore — packages specific to THIS machine
# GPU drivers, hardware firmware, etc.
nvidia-driver-595-open
```

---

## Multi-Machine Setup

### Setting up a new computer

```bash
# 1. Clone your fork (or the upstream repo)
git clone https://github.com/<your-user>/dotfiles-ubuntu.git ~/dotfiles-ubuntu

# 2. Install system + dotfiles
cd ~/dotfiles-ubuntu
chmod +x bootstrap.sh backup.sh audit.sh scripts/*.sh
./bootstrap.sh              # interactive — asks before each step

# 3. Install Antigravity IDE & Agents (optional)
# Download binaries to ~/Downloads/ first, then:
./scripts/antigravity-install.sh

# 4. Clone your project repos
git clone https://github.com/<your-user>/<your-project>.git ~/Projects/<your-project>
# (repeat for other projects)

# 5. Authenticate Antigravity
# Open Antigravity IDE → sign in when prompted
# Credentials are stored locally in ~/.gemini/*.json (per-machine)

# 6. Start working
# Open your project in Antigravity IDE and run /sopen
# The agent detects "new machine" and recovers context from SESSION.md + git
```

### Migrating an existing computer

If the target computer already has configuration (dotfiles, Antigravity config):

#### Before running bootstrap

```bash
# Check what exists — are these real files or symlinks?
ls -la ~/.bashrc ~/.gitconfig ~/.gemini/config/AGENTS.md 2>/dev/null
ls -la ~/.gemini/config/skills 2>/dev/null

# If real files (not symlinks) → review for unique rules you want to keep
cat ~/.gemini/config/AGENTS.md
ls ~/.gemini/config/skills/
```

#### Run bootstrap — it's safe

```bash
git clone https://github.com/<your-user>/dotfiles-ubuntu.git ~/dotfiles-ubuntu
cd ~/dotfiles-ubuntu && chmod +x bootstrap.sh backup.sh audit.sh scripts/*.sh
./bootstrap.sh --stow
```

`bootstrap.sh` handles collisions automatically:

| If it finds... | It does... |
|---|---|
| Nothing at target | Creates symlinks directly |
| Real files (`.bashrc`, `AGENTS.md`, etc.) | Renames to `*.backup.YYYYMMDD`, then creates symlinks |
| Existing symlinks (previously installed) | Stow overwrites them (idempotent) |

#### After bootstrap — rescue unique config

If the pre-check revealed unique rules on this computer:

```bash
# Compare backup against the new shared config
diff ~/.bashrc.backup.* ~/dotfiles-ubuntu/bash/.bashrc
diff ~/.gemini/config/AGENTS.md.backup.* ~/dotfiles-ubuntu/antigravity/.gemini/config/AGENTS.md

# If there are unique rules worth keeping → merge them into dotfiles-ubuntu
# Then commit and push so both machines benefit
cd ~/dotfiles-ubuntu
git add -A
git commit -m "docs: merge unique rules from secondary machine"
git push
```

#### What stays untouched

These local files are **never modified** by `bootstrap.sh`:

| File | Purpose |
|------|---------|
| `~/.gemini/config/config.json` | Antigravity IDE preferences |
| `~/.gemini/config/mcp_config.json` | MCP server configuration |
| `~/.gemini/config/plugins/` | Installed Antigravity plugins |
| `~/.gemini/config/projects/` | Workspace definitions |
| `~/.gemini/config/sidecars/` | Local sidecars |
| `~/.gemini/antigravity/brain/` | Conversation history (local per-machine) |
| `~/.gemini/*.json` (OAuth) | Authentication credentials |

### Daily sync procedures

The skills `/sopen` and `/sclose` handle sync automatically:

| Skill | Step | Action |
|---|---|---|
| `/sopen` | §0 Global Config Sync | `cd ~/dotfiles-ubuntu && git pull --ff-only` |
| `/sclose` | §3.5 Global Config Sync | Commit + push if dotfiles-ubuntu was modified |

### Portability matrix

| Data | Portable? | Mechanism | Recovery on new machine |
|------|:---------:|-----------|------------------------|
| System config (shell, git) | ✅ | `dotfiles-ubuntu` stow modules | `./bootstrap.sh --stow` |
| Global agent config (rules, skills) | ✅ | `dotfiles-ubuntu/antigravity/` stow module | `./bootstrap.sh --stow` |
| System packages (APT, snaps, npm) | ✅ | `dotfiles-ubuntu/system/` manifests | `./bootstrap.sh --packages` |
| GNOME settings | ✅ | `dotfiles-ubuntu/system/gnome-settings.dconf` | `./bootstrap.sh --gnome` |
| Templates | ✅ | `dotfiles-ubuntu/templates/` | Clone |
| Project rules (`.agents/`) | ✅ | Project git repo | `git clone` |
| Session state (`SESSION.md`) | ✅ | Project git repo | `/sopen` Tier 2 |
| Governance (WORKTASK, WORKROAD, CHANGELOG) | ✅ | Project git repo | `/sopen` Tier 3 |
| Source code | ✅ | Project git repo | `git clone` |
| Antigravity binaries (IDE, Agents) | 🔧 | `scripts/antigravity-install.sh` | Download + run script |
| Conversation history (`brain/`) | ❌ | Local `~/.gemini/antigravity/brain/` | Auto-healed by `/sopen` (Tier 2 + 3) |
| Auth credentials | ❌ | Local `~/.gemini/*.json` | Re-authenticate in IDE |
| CLI history | ❌ | Local `~/.gemini/history/` | Regenerates automatically |

> **Key insight**: Conversation artifacts (`brain/`) are local by design. When you open a session
> on a new machine, `/sopen` detects missing `brain/` data and recovers context from
> `SESSION.md` (Tier 2) and `git status`/`git log` (Tier 3). No data is truly lost —
> only the detailed conversation scratchpads are machine-specific.

---

## Uninstall

### Remove stow symlinks (keeps the repo)

```bash
cd ~/dotfiles-ubuntu
stow -t ~ -D bash git antigravity
```

### Remove everything

```bash
cd ~/dotfiles-ubuntu
stow -t ~ -D bash git antigravity
cd ~ && rm -rf ~/dotfiles-ubuntu
```

---

## Security & Local Overrides

**Never commit secrets or personal identity.**
- **Git identity**: `git/.gitconfig` includes `~/.gitconfig.local` (`[include] path = ~/.gitconfig.local`). Your `user.name` and `user.email` live in `~/.gitconfig.local` (automatically preserved by `bootstrap.sh`).
- **Shell overrides**: `bash/.bashrc` sources `~/.bashrc.local` if present for machine- or project-specific environment variables.
- **Ignored patterns**: `.gitignore` excludes SSH keys (`~/.ssh/id_*`), GPG keys (`~/.gnupg/`), credentials (`~/.netrc`), backup files (`*.backup.*`), and local overrides (`.bashrc.local`, `.gitconfig.local`, `.audit-ignore`).

If you need to track SSH **config** (not keys), create the `ssh/` module with only the `config` file. See [`SECURITY.md`](SECURITY.md) for the full secret and identity isolation policy.

---

## Development, Testing, Virtual Environment & CI

### Layered Dependency Model (`requirements.txt` $\leftarrow$ `requirements-dev.txt` & Environment Profiles)

`dotfiles-ubuntu` separates **base runtime dependencies** from **development/testing tools** using chained requirement files (`-r requirements.txt`), enabling clean extensibility across corporate, team, and multi-environment (`tst`, `pre`, `pro`) MCP forks:

| Mode / File | Python Requirement | Packages Included | Virtual Environment (`venv`) Needed? |
|-------------|--------------------|-------------------|:------------------------------------:|
| **Base Runtime** ([`requirements.txt`](requirements.txt) — `bootstrap.sh`, `backup.sh`, `audit.sh`, `~/.gemini/config/scripts/*.py` hooks, and `scripts/dotfiles_mcp_server.py`) | Ubuntu 26.04 LTS system `python3` (**Python 3.14**; MCP server is also backward-compatible with Python >= 3.10 for older containers/remote hosts) | **Zero (`0`) in upstream base** — 100% Python Standard Library *(extensible in forks that add custom runtime MCP tools)* | **No** in upstream base (or `make install-runtime` if a fork adds runtime packages to `requirements.txt`) |
| **Development, Linting & Testing** ([`requirements-dev.txt`](requirements-dev.txt) — chains `-r requirements.txt`) | Python 3.14 (or >= 3.13) | `-r requirements.txt` + `pytest`, `pytest-cov`, `ruff`, `mypy` | **Yes** (`./venv` created via `make install`) |
| **Multi-Environment MCP / Service Forks** (`requirements-tst.txt`, `requirements-pre.txt`, `requirements-pro.txt` — optional in forks) | System or container `python3` | `-r requirements.txt` + environment-specific SDKs or MCP connectors | Optional per node (`pip install -r requirements-<env>.txt`) |

> **Why keep `requirements.txt` separate from `requirements-dev.txt`?**
> 1. **Zero Runtime Pollution**: In the upstream repository, both the Contextual MCP Server and the 4 lifecycle hooks use **100% Python Standard Library** and run directly on Ubuntu 26.04 LTS's native `/usr/bin/python3` (`Python 3.14`) without a `venv`. Keeping `pytest`, `mypy`, and `ruff` in `requirements-dev.txt` ensures that production/staging containers or remote SSH nodes never install test/lint packages if they run `pip install -r requirements.txt`.
> 2. **Multi-Environment MCP Extensibility (`tst`, `pre`, `pro`)**: When a team or platform fork customizes `dotfiles-ubuntu` as a service-node MCP layer across `tst`, `pre`, or `pro` environments, it can place shared runtime libraries in `requirements.txt` (or environment-specific libraries in `requirements-<env>.txt` starting with `-r requirements.txt`), while `requirements-dev.txt` automatically inherits `-r requirements.txt` for local testing and CI.
> 3. **Automatic Hook Discovery**: When `post_edit_format.py`, `post_invocation_lint.py`, or `stop_verify_tests.py` run inside any project, they automatically discover `ruff` and `pytest` from `<workspace>/venv/bin/`. Running `make install` (`requirements-dev.txt`) creates `./venv` inside `~/dotfiles-ubuntu` so those hooks also operate on `dotfiles-ubuntu` itself.

### Setting Up the Local Development `venv` & Running Tests

```bash
cd ~/dotfiles-ubuntu

# 1. Create ./venv and install requirements-dev.txt (chains -r requirements.txt + pytest, pytest-cov, ruff, mypy)
make install

# 2. Run the full test suite (tests/unit/ + tests/imp/) with 100% branch coverage gate
make test-cov

# 3. Run Ruff linter + Mypy --strict type checker
make lint

# 4. Run the complete 8-stage repository & CI verification suite
make verify
```

### Versioning & Contributing

- **Semantic Versioning**: Tracked in [`VERSION`](VERSION) (`1.4.0`) and [`CHANGELOG.md`](CHANGELOG.md). All CLI scripts support `--version` / `-v`.
- **Repository Verification & CI**: Run `make verify` or `./scripts/verify-repo.sh` locally (also executed automatically by GitHub Actions in [`.github/workflows/ci.yml`](.github/workflows/ci.yml)) to validate:
  1. Open-source metadata, SemVer sync, and all relative Markdown links across `.md` files.
  2. Bash syntax (`bash -n`) and executable permissions across all 16 shell scripts and external recipes.
  3. Python lifecycle hooks and MCP server compilation, `ruff check`, and `mypy --strict` (0 errors).
  4. `hooks.json` schema and script target resolution.
  5. `AGENTS.md` token budget (`< 18 KB`).
  6. `SKILL.md` YAML frontmatter (`kebab-case`) and line budget (`< 500` lines).
  7. Contextual MCP Server (`./scripts/dotfiles_mcp_server.py --self-test` & `system/mcp-layer.json`).
  8. Automated test suite (`tests/unit/` + `tests/imp/`), `0-byte` `tests/**/__init__.py` purity, and **100.00% statement and branch coverage**.
- **Contributing**: See [`CONTRIBUTING.md`](CONTRIBUTING.md) and [`docs/reference/developer_and_extension_guide.md`](docs/reference/developer_and_extension_guide.md) for guidelines on adding external package recipes, skills, lifecycle hooks, or tests.
