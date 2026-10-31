# dotfiles-ubuntu

[![CI](https://github.com/mtwuser/dotfiles-ubuntu/actions/workflows/ci.yml/badge.svg)](https://github.com/mtwuser/dotfiles-ubuntu/actions/workflows/ci.yml)
[![Version](https://img.shields.io/badge/version-1.8.2-blue.svg)](VERSION)
[![Coverage](https://img.shields.io/badge/coverage-100%25%20(unit%20%2B%20branch)-brightgreen.svg)](scripts/verify-repo.sh)
[![Python](https://img.shields.io/badge/python-3.14%20(zero--deps)-3776AB.svg)](pyproject.toml)
[![Ubuntu](https://img.shields.io/badge/Ubuntu-26.04%20LTS-E95420.svg)](https://ubuntu.com/)
[![Antigravity](https://img.shields.io/badge/Google%20Antigravity-2.0-8E44AD.svg)](https://antigravity.google/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

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
- **12 Global Skills (`~/.gemini/config/skills/`)** — Available immediately in every workspace across Antigravity Agents, IDE, and CLI:
  - **Session & Workflow Slash Commands**: `/sopen` (initialize session & sync state), `/sclose` (close session, update `[Unreleased]` changelog & commit), `/continue` (mid-session checkpoint), `/release` (cut & publish explicit SemVer release `vX.Y.Z`), `/priority` (pick next task from governance files), `/review` (audit code, architecture & tests), `/enrich` (extract reusable patterns from a project into global skills).
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

### Path 3: Enterprise & Team Human-AI Governance ("pAIr programming" at Scale — With or Without MCP)

Organizations can use this repository as the foundation for company-wide AI-assisted software engineering — starting from a **Corporate Reference Fork** of this open-source repository, branching into **Departmental** and **Team** layers, and applying those standards during daily **Application Development** (**either without MCP** using pure Git + GNU Stow + Templates, **or with MCP** using the built-in Contextual MCP Server and `git subtree` graph):

```
Tier 0: Public Open-Source Upstream (mtwuser/dotfiles-ubuntu)
   │  git fork + ./scripts/layer-subtree.sh sync-upstream
   ▼
Tier 1: Corporate Reference Layer (e.g., acme-corp/dotfiles-ubuntu)
   │  • Company-wide AGENTS.md, hooks.json (PreToolUse/Stop guards), 11 global skills
   ├──► Tier 2A: Departmental Forks (e.g., acme-dept-security, acme-dept-data, acme-dept-sre)
   │       • Cross-cutting security/data/cloud compliance rules, docs/, departmental MCPs
   └──► Tier 2B: Team / Stack Forks (e.g., acme-team-backend, acme-team-frontend)
           • Stack starter templates (templates/fastapi-hexagonal/, etc.)
           • Optionally mounts Tier 2A Departmental forks in layers/<dept>/ via git subtree
           │
           ▼
Tier 3: Application Development Repositories (e.g., checkout-service, billing-api)
   • Scaffolds <app>/.agents/{rules,skills} + WORKTASK.md from Tier 2B templates/<stack>/
   • Developers work with Corporate + Team + Project context (With or Without MCP)
```

#### Two Complementary Operating Perspectives (Choose One or Combine Both)

| Perspective | How It Works | When a Company Should Use It |
|-------------|--------------|------------------------------|
| **Mode A — Without MCP**<br>*(Pure Git + GNU Stow + Templates)* | 1. Company forks `dotfiles-ubuntu` $\rightarrow$ Teams fork the Corporate repo.<br>2. Developers clone their Team fork (`~/dotfiles-ubuntu`) and run `./bootstrap.sh --antigravity`.<br>3. GNU Stow links `~/.gemini/config/{AGENTS.md,hooks.json,scripts/,skills/}` locally.<br>4. Application repos copy `templates/<stack>/` into `<app>/.agents/`.<br>5. Sync runs via `/sopen` (`git pull`) and `/enrich` (upward PRs). | Ideal for organizations wanting **zero MCP server configuration** and 100% local file-based rules, deterministic lifecycle hooks, and stack templates. |
| **Mode B — With MCP**<br>*(Contextual MCP Server + `git subtree` `layers/*` + `dev/tst/pre/pro` + Docker)* | Everything in Mode A **plus**:<br>1. Team/Workstation forks mount Departmental & Sibling-Service forks into `layers/<name>/` via `./scripts/layer-subtree.sh add` (`0 bytes` added to `always_on` `AGENTS.md`).<br>2. `scripts/dotfiles_mcp_server.py` runs over `stdio` (locally, as a standalone hermetic Hub container via `docker run -i --rm`, inside microservice containers via `COPY --from` + `docker exec -i` or `-v :ro`, or via `ssh`).<br>3. Agents query cross-layer rules (`layer="all"`), audit container drift, and discover `dev/tst/pre/pro` MCPs with inherited `effective_guardrails` and JSONL audit logs (`logs/mcp_*.jsonl`). | Ideal when applications cross **multiple departments** (Security, Data, SRE), **multiple microservices/containers**, or **multiple environments (`dev/tst/pre/pro`)** and need on-demand context without exceeding the 20,000-token rule budget. |

#### Quick Integration Sequence for a Company

```bash
# 1. [Corporate Architect] Fork mtwuser/dotfiles-ubuntu -> acme-corp/dotfiles-ubuntu
#    Customize antigravity/.gemini/config/AGENTS.md and system/mcp-layer.json (layer_role: "corporate")

# 2. [Team / Department Lead] Fork acme-corp/dotfiles-ubuntu -> acme-team-backend
#    Keep synced vertically with Corporate upstream:
./scripts/layer-subtree.sh sync-upstream git@github.com:acme-corp/dotfiles-ubuntu.git main

# 3. [Optional — Multi-Dimensional Context] Mount Departmental forks into layers/* (--squash):
./scripts/layer-subtree.sh add dept-security git@github.com:acme-corp/dotfiles-dept-security.git main
./scripts/layer-subtree.sh add dept-data     git@github.com:acme-corp/dotfiles-dept-data.git main

# 4. [Developer] Clone the Team fork, activate GNU Stow hooks, and scaffold an application repo:
git clone git@github.com:acme-corp/dotfiles-team-backend.git ~/dotfiles-ubuntu
cd ~/dotfiles-ubuntu && ./bootstrap.sh --antigravity
cp -r ~/dotfiles-ubuntu/templates/fastapi-hexagonal/{rules,skills} /path/to/my-app/.agents/
cp ~/dotfiles-ubuntu/templates/fastapi-hexagonal/governance/*.md /path/to/my-app/
```

📖 **Full Architecture & Enterprise Integration Guides**:
- **[`docs/reference/enterprise_pair_programming_governance.md`](docs/reference/enterprise_pair_programming_governance.md)** — Complete step-by-step Company Integration Playbook (`Corporate → Department/Team → Application`, with or without MCP), Google AI docs tooling, and 1:1 VS Code / GitHub Copilot mapping.
- **[`docs/reference/contextual_mcp_and_multi_service_orchestration.md`](docs/reference/contextual_mcp_and_multi_service_orchestration.md)** — Standalone & federated MCP server architecture, `git subtree` (`layers/*`) workflows, `dev/tst/pre/pro` environment profiles, and IDE/Docker/SSH recipes.
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
│   │           └── sopen/, sclose/, continue/, release/, enrich/, priority/, review/
│   └── .local/share/applications/
│       ├── antigravity-agents.desktop ←   → ~/.local/share/applications/
│       └── antigravity-ide.desktop    ←   → ~/.local/share/applications/
│
├── docs/                              ← NOT stow — navigable architecture & reference hub (< 465 lines per file)
│   ├── README.md                      ←   Documentation index, subsystem map & AI agent lookup
│   ├── architecture/                  ←   Normative technical specifications (1:1:1 with code & unit tests)
│   │   ├── 01_system_and_stow_engine.md                    ← Ubuntu 26.04 engine, 3-stage APT filter, Stow
│   │   ├── 02_antigravity_governance_and_hooks.md          ← Token budget, 4 hook 1:1 contracts, 11 skills
│   │   ├── 03_contextual_mcp_and_federation.md             ← Zero-dependency MCP server protocol & schema (v1.2)
│   │   ├── 04_compaction_surface_and_promotion_engines.md  ← rcap1 compaction, 0..N surface weaver & promotion engines
│   │   └── 05_ephemeral_forks_and_department_bots.md       ← Ephemeral Department Bot forks, project bridges & TTL GC
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
├── templates/                         ← NOT stow — polymorphic template packs (stack-starter, domain-policy-pack, department-pack)
│   ├── human-core/                    ←   Default global machine baseline (cognitive rigor, dotfiles-ubuntu self-guidance, commit/priority rules)
│   ├── technical-base/                ←   Software engineering, 1:1:1 traceability, refactoring & 100% AAA testing baseline
│   ├── business-base/                 ←   Enterprise corporate ledger, Lex Superior IP/compliance & cross-surface cascade baseline
│   └── fastapi-hexagonal/             ←   FastAPI + Hexagonal DDD + HTMX (template.json, rules, skills, governance)
│
├── scripts/                           ← NOT stow — utility, MCP, subtree, fork-config & CI verification scripts
│   ├── antigravity-install.sh         ←   Install/update Antigravity IDE & Agents
│   ├── audit-global-config.sh         ←   Verify ~/.gemini/config/ symlinks & orphans
│   ├── dotfiles_mcp/                  ←   Modular Contextual MCP Server & Fork/Promotion package (17 modules, < 465 lines each)
│   │   ├── constants.py, catalogs.py  ←     Declarative constants, regexes & MCP resource/tool/prompt catalogs
│   │   ├── manifest_helpers.py        ←     System manifest, skill frontmatter & telemetry helpers
│   │   ├── fork_configurator.py       ←     Fork parameterization (init-fork), template scaffolding & apply-project
│   │   ├── workspace_bootstrapper.py  ←     Global profile composer (set-global-profile), subtree registrar & bootstrap-workspace
│   │   ├── promotion_engine.py        ←     Multi-layer pattern comparison, diff-project & promote-from-project
│   │   ├── ephemeral_fork_engine.py   ←     Zero-copy ephemeral Department Bot forks, project bridges & TTL GC
│   │   ├── surface_weaver.py          ←     Stack-agnostic surface selector inference & Lex Specialis scoring
│   │   ├── capsule_engine.py          ←     Resonant rcap1 Matryoshka L0->L3 encryption & compression engine
│   │   ├── node_base.py, resources.py ←     Base node path-containment, warnings & 9 MCP resource readers
│   │   ├── tools_federation.py        ←     Overview, drift audit, doc reader & federated MCP discovery tools
│   │   ├── tools_compaction.py        ←     Multi-resolution query_governance_rules & capsule minting
│   │   ├── tools_unfold.py            ←     Hop-by-hop unfold_context_capsule & TOCTOU line-drift relocation
│   │   ├── tools_surface.py           ←     0..N resolve_surface_governance weaver & delegation advisories
│   │   └── tools_ephemeral.py, server.py←   orchestrate_ephemeral_fork tool & JSON-RPC 2.0 dispatcher
│   ├── dotfiles_mcp_server.py         ←   Zero-dependency read-only Contextual MCP Server CLI entrypoint (stdio)
│   ├── layer-config.sh                ←   Fork parameterization (init-fork), template scaffolding, project projection & promotion
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
│   ├── unit/                          ←   1:1 unit tests for lifecycle hooks & MCP server modules
│   │   ├── dotfiles_mcp/              ←     1:1 unit tests for all 15 executable MCP package modules
│   │   │   ├── test_manifest_helpers.py
│   │   │   ├── test_fork_configurator.py
│   │   │   ├── test_workspace_bootstrapper.py
│   │   │   ├── test_promotion_engine.py
│   │   │   ├── test_ephemeral_fork_engine.py
│   │   │   ├── test_surface_weaver.py
│   │   │   ├── test_capsule_engine.py
│   │   │   ├── test_node_base.py
│   │   │   ├── test_resources.py
│   │   │   ├── test_tools_federation.py
│   │   │   ├── test_tools_compaction.py
│   │   │   ├── test_tools_unfold.py
│   │   │   ├── test_tools_surface.py
│   │   │   ├── test_tools_ephemeral.py
│   │   │   └── test_server.py
│   │   ├── test_pre_tool_guard.py
│   │   ├── test_post_edit_format.py
│   │   ├── test_post_invocation_lint.py
│   │   ├── test_stop_verify_tests.py
│   │   └── test_dotfiles_mcp_server.py
│   ├── imp/                           ←   stdio JSON-RPC 2.0, Bash CLI & repo parity gate tests
│   │   ├── test_mcp_and_hooks_stdio.py
│   │   ├── test_cli_scripts.py
│   │   └── test_repo_parity_gates.py
│   └── e2e/                           ←   chained multi-node MCP federation, surface weaving, ephemeral bots & hook tests
│       ├── test_chained_mcp_federation_e2e.py
│       ├── test_layer_config_and_promotion_e2e.py
│       ├── test_surface_and_compaction_e2e.py
│       ├── test_ephemeral_forks_e2e.py
│       └── test_agent_turn_lifecycle_hooks_e2e.py
│
├── bootstrap.sh                       ← restore system from manifests
├── backup.sh                          ← capture current system state
├── audit.sh                           ← detect drift & residual files
├── Dockerfile                         ← Ubuntu 26.04 MCP container (docker run -i --rm & multi-stage COPY --from)
├── .dockerignore                      ← clean container build context filter
├── Makefile                           ← dev/test/docker automation (make install, test-cov, lint, verify, docker-build)
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
| `scripts/` | ❌ | — | Utility, MCP, subtree & CI scripts (`antigravity-install.sh`, `audit-global-config.sh`, `dotfiles_mcp_server.py`, `dotfiles_mcp/`, `layer-subtree.sh`, `verify-repo.sh`) |
| `system/` | ❌ | — | Package manifests, MCP layer topology (`mcp-layer.json`), & external recipe catalog |
| `layers/` | ❌ | — | Optional mounted `git subtree` context forks (`layers/<name>/` for departmental/service/environment orchestration) |
| `logs/` | ❌ | — | Gitignored runtime MCP audit & alert logs (`logs/mcp_events.jsonl`, `logs/mcp_alerts.jsonl`) |
| `tests/` | ❌ | — | Unit (`tests/unit/`), integration (`tests/imp/`), and end-to-end (`tests/e2e/`) test suite with 100% branch coverage |

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
  - `pre_tool_guard.py` (`PreToolUse`) — Deterministically blocks non-empty writes to consumer `src/**/__init__.py` or `tests/**/__init__.py` and manual edits to `alembic/versions/*.py` (across both file tools and `run_command` shell redirections, heredocs, `tee`, `cp`/`mv`, `dd`, or inline `python -c`), plus automatic execution of mutating `git` (`add`, `commit`, `push`, `reset --hard`, `clean -f`, `subtree add|pull|push|merge`) or `alembic` commands
  - `post_edit_format.py` (`PostToolUse`) — Runs `ruff format` automatically whenever the agent edits a `.py` file
  - `post_invocation_lint.py` (`PostInvocation`) — Runs `ruff check`, AST architecture/test checks (`check_project`, `check_tests`), and `always_on` rule token-budget checks (`AGENTS.md` 18 KB cap & 80 KB / ~20k-token combined workspace budget) on modified and untracked Python files at the end of a turn (`force_continue` on errors)
  - `stop_verify_tests.py` (`Stop`) — Verifies affected unit tests pass on modified and untracked Python workspaces before concluding a task
- **skills/** — 7 interactive slash-command skills and 5 procedural engineering skills:

#### Global Slash Commands (`~/.gemini/config/skills/<command>/SKILL.md`)

| Command | When to Run | Purpose & Actions |
|---------|-------------|-------------------|
| `/sopen` | Start of every session | Pulls latest `~/dotfiles-ubuntu`, recovers session context across 3 tiers (`brain/` → `.agents/SESSION.md` → `git status` + `WORKTASK.md`), and activates project-specific `/start` if present |
| `/continue` | Mid-session (between tasks or before `/compact`) | Checkpoints active progress into `WORKTASK.md`, `CHANGELOG.md` (`[Unreleased]`), and `.agents/SESSION.md` so zero context is lost |
| `/sclose` | End of every session | Consolidates completed tasks (`WORKTASK.md` → `CHANGELOG.md` `[Unreleased]`), updates `.agents/SESSION.md`, verifies `~/dotfiles-ubuntu` if modified, and outputs ready-to-run local `git commit` blocks |
| `/release` | When explicitly cutting & publishing a versioned release | Runs zero-leak/agnosticism scans and `make verify`, promotes `## [Unreleased]` → `## [X.Y.Z] - YYYY-MM-DD`, syncs `VERSION`/`pyproject.toml`/`README.md`, and outputs the release commit + tag + push block |
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
| `refactoring` | Splitting large files (`< 465` lines cap, `<= 400` target) or "God Components" | Guides safe, incremental extraction of cohesive modules while preserving public contracts and `1:1:1` test/spec parity |
| `testing` | Writing, fixing, or auditing test suites | Enforces AAA (`Arrange-Act-Assert`) structure, hexagonal mock boundaries, naming conventions, and branch coverage audits |
| `validation` | Manual UI / web QA sessions | Drives structured human-agent manual verification checklists tracked in `WORKVALI.md` |

### Layer 2: Polymorphic Templates & Fork Parameterization (`templates/<name>/` & `scripts/layer-config.sh`)

Templates under `templates/<name>/` are polymorphic (discovered dynamically across both `Root` and mounted `layers/*/templates/*`, with zero hardcoded coupling to `fastapi-hexagonal`) and support 4 archetypes via `template.json`:
- **`stack-starter`**: Full tech-stack starter (`rules/`, `skills/`, `governance/`, e.g., `fastapi-hexagonal`, `nextjs-web`, `rust-axum`).
- **`domain-policy-pack`**: Authoritative legal, security, or financial domain rules and canonical assets (`rules/`, `skills/`, `assets/`, `mode: "authoritative"`).
- **`department-pack`**: Transversal departmental guidelines, design tokens, or UX/SEO checklists (`rules/`, `skills/`, `assets/`, `mode: "transversal"`).
- **`project-overlay`**: Project- or service-specific rules and assets (`rules/`, `assets/`, `governance/`).

```bash
# 1. Inspect available template packs across Root and mounted layers/*:
./scripts/layer-config.sh list-templates

# 2. Parameterize a new fork (Corporate, Domain-Policy, Department, or Team):
./scripts/layer-config.sh init-fork \
  --id acme-dept-design \
  --role department \
  --precedence 30 \
  --prune-default-templates

# 3. Scaffold a new template pack in this fork (and optionally register its surface_binding):
./scripts/layer-config.sh scaffold-template brand-design-system \
  --kind department-pack \
  --register-binding

# 4. Project template + 0..N mounted layers into a target project (Without MCP static materialization):
./scripts/layer-config.sh apply-project <your-project> \
  --template fastapi-hexagonal \
  --layers all

# 5. Diff & promote matured project rules, skills, or assets back into Root, layers/*, or templates/*:
./scripts/layer-config.sh diff-project <your-project>
./scripts/layer-config.sh promote-from-project <your-project> \
  --source .agents/rules/security-audit.md \
  --to-layer dept-security

# 6. Spawn, inspect, or reap TTL-bounded ephemeral Department Bot forks:
./scripts/layer-config.sh spawn-ephemeral --role dept-qa-bot --templates fastapi-hexagonal --tier flash --ttl 300
./scripts/layer-config.sh inspect-ephemeral
./scripts/layer-config.sh reap-ephemeral --id all

# 7. Compose machine-global AGENTS.md profile, register a mounted subtree, bootstrap or sync a multi-tier workspace (Corporate -> Department -> Squad/Team):
./scripts/layer-config.sh set-global-profile human-core --stow
./scripts/layer-config.sh register-subtree dept-legal https://github.com/acme/dept-legal.git master
./scripts/layer-config.sh bootstrap-workspace /path/to/dept-legal --id dept-legal-ip --role domain-policy --precedence 5 --templates business-base
./scripts/layer-config.sh bootstrap-workspace /path/to/squad-patents --id squad-patent-ops --role team --parent-dir /path/to/dept-legal
./scripts/layer-config.sh sync-layer /path/to/dept-legal --parent-dir /path/to/corporate-root
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

# 2. Run the full test suite (tests/unit/ + tests/imp/ + tests/e2e/) with 100% branch coverage gate
make test-cov

# 3. Run Ruff linter + Mypy --strict type checker
make lint

# 4. Run the complete 8-stage repository & CI verification suite
make verify

# 5. (Optional) Build and verify the hermetic Ubuntu 26.04 MCP Docker image
make docker-build && make docker-self-test
```

### Versioning & Contributing

- **Semantic Versioning**: Tracked in [`VERSION`](VERSION) (`1.8.2`) and [`CHANGELOG.md`](CHANGELOG.md) (ongoing changes accumulate under `## [Unreleased]` and are promoted via `/release`). All CLI scripts support `--version` / `-v`.
- **Repository Verification & CI**: Run `make verify` or `./scripts/verify-repo.sh` locally (also executed automatically by GitHub Actions in [`.github/workflows/ci.yml`](.github/workflows/ci.yml)) to validate:
  1. Open-source metadata, SemVer sync, `Dockerfile` / `.dockerignore`, and all relative Markdown links across `.md` files.
  2. Bash syntax (`bash -n`) and executable permissions across all 17 shell scripts and external recipes.
  3. Python lifecycle hooks and MCP server compilation, `ruff check`, and `mypy --strict` (0 errors).
  4. `hooks.json` schema, script target resolution, and deterministic **hook-to-documentation contract parity** (`pre_tool_guard.py` & `post_invocation_lint.py` vs. `AGENTS.md`, `SECURITY.md`, and `docs/architecture/02..03`).
  5. `AGENTS.md` token budget (`< 18 KB`).
  6. `SKILL.md` YAML frontmatter (`kebab-case`) and line budget (`< 500` lines).
  7. Contextual MCP Server, Subtree Orchestrator & Docker Contract (`./scripts/dotfiles_mcp_server.py --self-test` across 9 resources, 9 tools, 3 prompts, `resolve_surface_governance` `0..N` layer surface projection, `orchestrate_ephemeral_fork` Department Bot orchestration, and `rcap1` `L0 → L1 → L2 → L3` resonant compaction; `./scripts/layer-subtree.sh list` & `pull-all`; `system/mcp-layer.json` v1.2; Ubuntu 26.04 non-root `Dockerfile`).
  8. Automated test suite (`tests/unit/` + `tests/imp/` + `tests/e2e/`), `0-byte` `tests/**/__init__.py` purity, and **100.00% statement and branch coverage**.
- **Contributing**: See [`CONTRIBUTING.md`](CONTRIBUTING.md) and [`docs/reference/developer_and_extension_guide.md`](docs/reference/developer_and_extension_guide.md) for guidelines on adding external package recipes, skills, lifecycle hooks, or tests.
