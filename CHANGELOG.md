# Changelog

All notable changes to `dotfiles-ubuntu` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.3.0] - 2026-10-28

### Added
- **Zero-Dependency Contextual Layer & System MCP Server (`scripts/dotfiles_mcp_server.py` & `system/mcp-layer.json`)**:
  - Implemented `scripts/dotfiles_mcp_server.py` in pure Python >= 3.10 standard library (JSON-RPC 2.0 over `stdio`, supporting both newline-delimited and `Content-Length` framed streams, plus `--self-test`, `--layer-id`, `--layer-role`, `--version`, and `--help` CLI flags).
  - Exposed 8 MCP `Resources` (`dotfiles://layer/identity`, `dotfiles://system/manifests`, `dotfiles://governance/rules`, `dotfiles://governance/hooks`, `dotfiles://governance/skills`, `dotfiles://governance/templates`, `dotfiles://docs/index`, `dotfiles://mcp/topology`), 6 read-only `Tools` (`get_layer_overview`, `audit_node_drift`, `read_layer_document` with strict `REPO_DIR` path-traversal protection, `query_governance_rules`, `discover_federated_mcps`, `compare_layer_patterns`), and 3 `Prompts` (`orient-on-layer`, `audit-container-or-node`, `orchestrate-federated-mcps`).
  - Added `system/mcp-layer.json` declaring the layer's role, upstream repository lineage, default stack templates, and federated MCP servers with mandatory pre-call safety guardrails.
  - Extended `scripts/verify-repo.sh` (`[7/7]`) to lint `scripts/dotfiles_mcp_server.py` with `ruff check`, validate `system/mcp-layer.json`, and execute `./scripts/dotfiles_mcp_server.py --self-test` in CI.
- **Contextual Layer & System MCP Server Specification & Multi-Service Orchestration Guide (`docs/`)**:
  - Added `docs/architecture/03_contextual_mcp_and_federation.md` defining the Dual-Plane Model (GNU Stow local plane vs. MCP distributed plane), 5 non-negotiable security & zero-dependency invariants (Python >= 3.10 stdlib, strictly read-only, path containment inside `REPO_DIR`), JSON-RPC 2.0 contracts for 8 `Resources`, 6 `Tools`, and 3 `Prompts`, and the `system/mcp-layer.json` federation schema.
  - Added `docs/reference/contextual_mcp_and_multi_service_orchestration.md` detailing both **Mode A (Standalone Container/Node MCP Use Case)** and **Mode B (Enterprise Multi-Service Context Mesh)**, plus step-by-step configuration recipes for Google Antigravity 2.0 (`~/.gemini/config/mcp_config.json`), Docker containers (`docker exec -i`), remote SSH servers (`ssh -T -o BatchMode=yes`), multi-fork layers, VS Code & GitHub Copilot (`.vscode/mcp.json`), Cursor, and Claude Code.
  - Updated `docs/README.md`, `docs/reference/enterprise_pair_programming_governance.md` (§7), `docs/reference/developer_and_extension_guide.md` (§5), `docs/architecture/02_antigravity_governance_and_hooks.md`, `README.md`, `CONTRIBUTING.md`, `SECURITY.md`, and `ACCESSIBILITY.md` for full cross-document coherence.
  - Enhanced `scripts/verify-repo.sh` Check `[1/7]` to validate the new `docs/` files and enforce a deterministic relative Markdown link integrity gate across all `.md` files in the repository.

---

## [1.2.0] - 2026-10-28

### Added
- **Navigable Documentation Hub, Normative Architecture Specs & Enterprise "pAIr programming" Guide (`docs/`)**:
  - Added `docs/README.md` providing a navigable documentation index, document hierarchy map, Mermaid subsystem diagram, and quick-lookup table for both humans and AI agents.
  - Added `docs/architecture/01_system_and_stow_engine.md` specifying the Ubuntu 26.04 LTS tripartite lifecycle (`backup.sh` $\leftrightarrow$ `audit.sh` $\leftrightarrow$ `bootstrap.sh`), 3-stage APT filtering pipeline, `system/external/{apt-repo,deb-url,script}/` plugin contracts, and GNU Stow tree-unfolding invariants.
  - Added `docs/architecture/02_antigravity_governance_and_hooks.md` specifying the 3-surface `~/.gemini/config/` architecture, the 20,000-token `defaultRulesBudget` & 18 KB `AGENTS.md` cap, sequence diagram and `stdin`/`stdout` JSON contracts for all 4 Python 3.14 lifecycle hooks (`PreToolUse`, `PostToolUse`, `PostInvocation`, `Stop`), and the 11 global skills catalog.
  - Added `docs/reference/enterprise_pair_programming_governance.md` detailing the **Enterprise Use Case — Distributed Human-AI Governance ("pAIr programming") at Scale** (3-tier `Corporate → Team → Project` hierarchy, bidirectional `/learn` $\rightarrow$ `/enrich` evolution, navigable `docs/` with **Google Jules**, **Gemini Code Assist Enterprise**, **Google Developer Knowledge MCP**, **Google NotebookLM**, and **`google-genai` SDK**, plus 1:1 portability matrix to **VS Code & GitHub Copilot**, **Cursor**, and **Claude Code**).
  - Added `docs/reference/developer_and_extension_guide.md` as a maintainer playbook for evolving `dotfiles-ubuntu` (adding stow vs. non-stow root directories, creating Layer 2 stack templates, authoring external package recipes, and running CI/symlink verification).
  - Updated `bootstrap.sh` and `audit.sh` to skip the non-stow `docs/` root directory, and updated `README.md` and `scripts/verify-repo.sh` to verify the complete `docs/` hierarchy.

---

## [1.1.1] - 2026-10-27

### Added
- **Accessibility Statement (`ACCESSIBILITY.md`)**:
  - Added `ACCESSIBILITY.md` documenting terminal screen-reader compatibility, color-independent CLI status output, keyboard-only and non-interactive script execution, GNOME `a11y` dconf preservation, known limitations, and barrier reporting guidelines.
  - Updated `scripts/verify-repo.sh` and `README.md` to track and verify `ACCESSIBILITY.md`.

---

## [1.1.0] - 2026-10-27

### Added
- **GitHub Community Standards Completeness**:
  - `CODE_OF_CONDUCT.md` (Contributor Covenant v2.1).
  - `.github/ISSUE_TEMPLATE/bug_report.yml`, `.github/ISSUE_TEMPLATE/feature_request.yml`, and `.github/ISSUE_TEMPLATE/config.yml` (structured GitHub Issue Forms with `SECURITY.md` contact link).
  - `.github/PULL_REQUEST_TEMPLATE.md` with pre-merge verification checklist (`./scripts/verify-repo.sh`, secret isolation, and token budget gate).
- **Antigravity 2.0 Global Skills & Layer 2 Template Enrichment (`/enrich`)**:
  - `antigravity/.gemini/config/skills/architecture-review/SKILL.md`: Added the **5-Dimension Pre-Development Gate** (*Normative Specs → Reference Docs → Diagrams → Root Guides/Rules → Future Roadmaps*) and **4 Deterministic Verification Gates** (Zero-Residue Grep, Bilingual Structural Parity, Language Purity, and Relative Link Integrity).
  - `antigravity/.gemini/config/skills/governance/SKILL.md`: Updated `Part 2` with the **3-Stage Knowledge Extraction & Architectural Integration Pipeline** (*Reference Extraction & Gap Matrix → Normative Specs & Roadmaps → Raw Source Decommissioning*).
  - `templates/fastapi-hexagonal/rules/testing.md` and `templates/fastapi-hexagonal/skills/testing/SKILL.md`: Added the `1:1 File Mapping & Decommissioning (orphan-test-file)` rule to prevent orphaned test files when removing modules or features.
  - `scripts/verify-repo.sh`: Extended `[1/6] Open-Source Metadata & SemVer` to verify `CODE_OF_CONDUCT.md`, `.github/PULL_REQUEST_TEMPLATE.md`, and `.github/ISSUE_TEMPLATE/*.yml`.

---

## [1.0.0] - 2026-10-26

### Added
- **Declarative Ubuntu 26.04 LTS ("Resolute Raccoon") System Engine**:
  - `bootstrap.sh` with modular modes (`--all`, `--antigravity`, `--stow`, `--packages`, `--external`, `--nvm`, `--gnome`, `--version`, `--help`) and automatic collision backup (`*.backup.YYYYMMDD`).
  - `backup.sh` to snapshot manual APT packages (`system/packages-manual.txt`), application Snaps (`system/snaps.txt`), NPM globals (`system/npm-globals.txt`), NVM default version (`system/nvm-default.txt`), active external recipes (`system/external.txt`), GNOME extensions (`system/gnome-extensions.txt`), and declarative GNOME desktop settings (`system/gnome-settings.dconf`).
  - `audit.sh` (`--clean`, `--version`, `--help`) to detect bidirectional package drift, stow symlink health, inactive external APT repositories, and residual files, with per-machine hardware exclusions via `.audit-ignore`.
  - External package recipe catalog (`system/external/{apt-repo,deb-url,script}/`) for Docker Engine, Google Chrome, Google Cloud CLI, ProtonVPN, Proton Mail, Proton Pass, Discord, AutoFirma, Antigravity 2.0 (Agents), and Antigravity IDE.
- **GNU Stow Dotfile Modules (`bash/`, `git/`, `antigravity/`)**:
  - `bash/.bashrc` and `bash/.profile` with automatic sourcing of untracked `~/.bashrc.local`.
  - `git/.gitconfig` with automatic inclusion of untracked `~/.gitconfig.local` so personal identity (`user.name`, `user.email`) is never committed.
  - `antigravity/` tree-unfolded module linking `~/.gemini/config/{AGENTS.md,hooks.json,scripts/,skills/*}` and `~/.local/share/applications/antigravity-*.desktop` while preserving machine-local credentials and IDE state.
- **Google Antigravity 2.0 Global Customization Suite (`antigravity/.gemini/config/`)**:
  - `AGENTS.md` (~16.5 KB, engineered to stay strictly within Antigravity 2.0's 20,000-token `defaultRulesBudget` and 24 KB per-file cap) encoding 15 universal engineering mandates: reusability first, professional robustness, strict typing (`mypy --strict`), AAA testing with explicit 3-comment separation, documentation hierarchy, zero-backward clean cutovers, code decommissioning & mandatory obsolete-test pruning, pre-commit hygiene, exhaustive planning, `0-byte` `__init__.py` package marker purity, 4-Channel Subagent Digest (`Domain State`, `Affected Port/Contract`, `Invariants & Constraints`, `Actionable Delta`), language purity, and pre-debug diagnostic sweeps.
  - **Python 3.14 Lifecycle Hooks (`hooks.json` + `scripts/`)**:
    - `pre_tool_guard.py` (`PreToolUse`): Deterministically blocks non-empty writes to consumer `src/**/__init__.py` or `tests/**/__init__.py`, manual edits to `alembic/versions/*.py`, and automatic execution of mutating `git` (`add`, `commit`, `push`, `reset --hard`, `clean -f`) or `alembic` commands.
    - `post_edit_format.py` (`PostToolUse`): Runs `ruff format` automatically whenever the agent edits a `.py` file.
    - `post_invocation_lint.py` (`PostInvocation`): Runs `ruff check` and AST architecture/test checks (`check_project`, `check_tests`) on modified and untracked Python files with `"terminationBehavior": "force_continue"`.
    - `stop_verify_tests.py` (`Stop`): Verifies affected unit tests pass across modified and untracked Python workspaces before concluding a task.
  - **11 Reusable Global Skills (`skills/`)**:
    - 6 interactive workflow slash commands: `/sopen`, `/sclose`, `/continue`, `/priority`, `/review`, `/enrich`.
    - 5 procedural engineering skills (`kebab-case` identifiers): `architecture-review`, `governance`, `refactoring`, `testing`, `validation`.
- **Layer 2 Project Starter Template (`templates/fastapi-hexagonal/`)**:
  - Reusable `.agents/rules/` (`coding.md`, `environment.md`, `governance.md` with `trigger: model_decision`, `testing.md`), `.agents/skills/` (`fastapi-database`, `fastapi-frontend`, `fastapi-testing`, `start`), and starter governance templates (`governance/{WORKTASK,WORKROAD,WORKVALI,BACKLOG,CHANGELOG,SESSION}.md`).
- **Utility Scripts & CI Verification (`scripts/`, `.github/workflows/ci.yml`)**:
  - `scripts/antigravity-install.sh` to install or upgrade Antigravity 2.0 (Agents) and Antigravity IDE directly from `~/Downloads/` archives.
  - `scripts/audit-global-config.sh` to verify `~/.gemini/config/` tree unfolding, symlinks, and zero orphaned files.
  - `scripts/verify-repo.sh` and GitHub Actions workflow (`.github/workflows/ci.yml`) validating Bash syntax, Python hook linting, `hooks.json` schema, `AGENTS.md` token budget, and `SKILL.md` frontmatter.
