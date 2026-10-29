# Changelog

All notable changes to `dotfiles-ubuntu` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.6.4] - 2026-10-29

### Changed
- **POSIX `shlex` Command-Segment Tokenizer, Subshell Unwrapping & `.venv` Discovery Parity (`antigravity/.gemini/config/scripts/*.py`, `tests/unit/test_pre_tool_guard.py`)**:
  - Upgraded `_check_command` in [`pre_tool_guard.py`](antigravity/.gemini/config/scripts/pre_tool_guard.py) from regex-only matching to a hybrid **POSIX `shlex` command-segment tokenizer** (`shlex.shlex(..., posix=True, punctuation_chars=";&|()\\n")`) with regex fallback for command substitutions (`$(...)` / backticks) and unbalanced quotes:
    1. Splits compound shell pipelines (`;`, `&&`, `||`, `|`, subshells, newlines) into discrete segments while respecting quoted strings (eliminating false positives on commands like `echo "git add && git commit"` or `python3 -c 'print("git push")'`).
    2. Strips leading `KEY=VALUE` environment assignments and command wrappers (`env`, `sudo`, `command`, `nohup`, `nice`, `time`, `python -m`, `uv run`, `poetry run`) and recursively unwraps nested `sh -c` / `bash -lc` invocations.
    3. Advances past arbitrary global `git` (`-C <dir>`, `-c <k=v>`, `--no-pager`, `--git-dir`, `--work-tree`, `--bare`) and `alembic` (`-c <cfg>`, `-n <name>`, `-x <arg>`) flags to inspect the true subcommand, and inspects `ReplacementChunks` `ReplacementContent` values in `_check_file_write` so emptying an `__init__.py` to `0 bytes` is permitted (`92 passed`, **100.00% statement and branch coverage**).
  - Updated [`post_edit_format.py`](antigravity/.gemini/config/scripts/post_edit_format.py), [`post_invocation_lint.py`](antigravity/.gemini/config/scripts/post_invocation_lint.py), and [`stop_verify_tests.py`](antigravity/.gemini/config/scripts/stop_verify_tests.py) to discover both `venv/bin/` and `.venv/bin/` across workspaces, matching `scripts/verify-repo.sh`.

---

## [1.6.3] - 2026-10-29

### Added
- **Deterministic Hook-to-Documentation Contract Parity Gate (`scripts/verify-repo.sh` Check `[4/8]`, `pre_tool_guard.py`, `tests/imp/test_cli_scripts.py`)**:
  - Extended Check `[4/8]` in [`scripts/verify-repo.sh`](scripts/verify-repo.sh) and added `test_hooks_json_and_hook_scripts_maintain_doc_contract_parity` in [`tests/imp/test_cli_scripts.py`](tests/imp/test_cli_scripts.py) to prevent drift between enforced Python lifecycle hook rules and documentation:
    1. Verifies exact matcher-set parity between `antigravity/.gemini/config/hooks.json` (`PreToolUse` / `PostToolUse`) and `pre_tool_guard._FILE_WRITE_TOOLS`.
    2. Verifies that every blocked git subcommand (`_DOCUMENTED_GIT_SUBCOMMANDS`: `add`, `commit`, `push`, `reset --hard`, `clean -f`, `subtree`), alembic subcommand (`_DOCUMENTED_ALEMBIC_SUBCOMMANDS`), and file guard (`alembic/versions/`, `0 bytes` `__init__.py`) is both matched by `_MUTATING_GIT_RE` / `_ALEMBIC_MUTATE_RE` and documented across `AGENTS.md`, `SECURITY.md`, `README.md`, and `docs/architecture/02_antigravity_governance_and_hooks.md`.
    3. Verifies that `post_invocation_lint.py` token-budget constants (`18,000` and `80,000` bytes) and warning codes match `dotfiles_mcp_server.py` and `docs/architecture/02..03`.

---

## [1.6.2] - 2026-10-28

### Changed
- **GitHub Issue Templates & Discussions Integration (`.github/ISSUE_TEMPLATE/*.yml`)**:
  - Updated [`.github/ISSUE_TEMPLATE/config.yml`](.github/ISSUE_TEMPLATE/config.yml) (`blank_issues_enabled: false`) to add a direct link to **GitHub Discussions** (`Community Q&A & Architecture Discussions`) alongside [`SECURITY.md`](SECURITY.md).
  - Updated [`.github/ISSUE_TEMPLATE/bug_report.yml`](.github/ISSUE_TEMPLATE/bug_report.yml) and [`.github/ISSUE_TEMPLATE/feature_request.yml`](.github/ISSUE_TEMPLATE/feature_request.yml) component/category dropdowns to include the **Contextual MCP Server, Subtree Graph & Docker (`scripts/dotfiles_mcp_server.py`, `layer-subtree.sh`, `Dockerfile`)** and the **Automated Test Suite (`tests/{unit,imp,e2e}/`)**.

---

## [1.6.1] - 2026-10-28

### Changed
- **Community & Security Documentation Alignment (`SECURITY.md`, `CONTRIBUTING.md`, `.github/PULL_REQUEST_TEMPLATE.md`) & Docker Layer Cache Optimization (`Dockerfile`)**:
  - Updated [`SECURITY.md`](SECURITY.md) with a dedicated isolation row for **Hardened Docker Container Isolation (`Dockerfile` & `.dockerignore`)** covering non-root `USER ubuntu` (`1000:1000`) execution, air-gapped read-only sandbox flags (`--read-only --network=none --cap-drop=ALL`), and build-context secret exclusion.
  - Updated [`CONTRIBUTING.md`](CONTRIBUTING.md) and [`.github/PULL_REQUEST_TEMPLATE.md`](.github/PULL_REQUEST_TEMPLATE.md) to reflect the complete `tests/{unit,imp,e2e}/` 100% branch-coverage test tiers, `scripts/layer-subtree.sh`, and `make docker-build && make docker-self-test` verification commands.
  - Optimized [`Dockerfile`](Dockerfile) build-arg ordering (`GIT_COMMIT`, `LAYER_ID`, `LAYER_ROLE`, `MCP_ENV` placed after the `apt-get` layer) so new Git commits never invalidate the base OS package layer cache.

---

## [1.6.0] - 2026-10-28

### Added
- **Docker Containerization for Contextual MCP Hub & Multi-Stage Sidecar Injection (`Dockerfile`, `.dockerignore`, `Makefile`)**:
  - Added an official, hardened `ubuntu:26.04` `Dockerfile` (non-root `USER ubuntu`, build-time `dotfiles_mcp_server.py --self-test` & `layer-subtree.sh list` verification gates, optional `INSTALL_RUNTIME_DEPS` and `MCP_ENV` build args) and `.dockerignore` supporting three complementary Docker MCP deployment architectures:
    1. **Pattern A — Standalone Hermetic MCP Hub (`docker run -i --rm`)**: Zero-install distribution of Corporate, Departmental, and Team context layers (including pre-mounted `layers/*` subtrees) in a kernel-isolated sandbox (`--read-only --network=none --cap-drop=ALL`).
    2. **Pattern B — Multi-Stage Sidecar Injection (`COPY --from=dotfiles-ubuntu-mcp /opt/dotfiles-ubuntu /opt/dotfiles-ubuntu` + `docker exec -i`)**: Injects governance layers into `tst`/`pre`/`pro` microservice images in a single `Dockerfile` line without requiring Git SSH keys or tokens during `docker build`, enabling live `audit_node_drift` inside the running service container.
    3. **Pattern C — Local Compose / Devcontainer Bind-Mount (`-v ~/dotfiles-ubuntu:/opt/dotfiles-ubuntu:ro` + `docker exec -i`)**: Zero-rebuild live introspection of local `dev` containers.
  - Added `make docker-build`, `make docker-self-test`, and `make docker-mcp` targets in `Makefile`.
  - Extended `scripts/dotfiles_mcp_server.py` with container runtime detection (`in_container` in `dotfiles://layer/identity` and `get_layer_overview`), `DOTFILES_GIT_COMMIT` fallback when `.git/` is excluded by `.dockerignore`, and `DOTFILES_LAYER_ID` / `DOTFILES_LAYER_ROLE` environment variable overrides.
  - Extended `scripts/verify-repo.sh`, `tests/unit/test_dotfiles_mcp_server.py`, and `tests/imp/test_cli_scripts.py` to validate the `Dockerfile` and container runtime contracts at **100.00% statement and branch coverage** (`88 passed`).

---

## [1.5.0] - 2026-10-28

### Added
- **Multi-Dimensional Context Graph Orchestration via `git subtree` (`scripts/layer-subtree.sh` & `layers/`)**:
  - Added `scripts/layer-subtree.sh` (`list`, `add`, `pull`, `pull-all`, `push`, `sync-upstream`, `--dry-run`, `--help`, `--version`) and `make layer-list` / `make layer-pull-all` to automate vertical upstream fork synchronization (`Public → Corporate → Team`) and horizontal `git subtree --squash` composition of Departmental, Team, and Sibling-Service forks under `layers/<layer-name>/` (with automatic `upstream_layer` repository/branch resolution in `pull` and `push`).
  - Updated `bootstrap.sh` and `audit.sh` to exclude `layers/` from GNU Stow symlinking, keeping `always_on` prompt rules under the 18 KB `AGENTS.md` token budget while exposing mounted subtrees on demand via the MCP server.
  - Updated `antigravity/.gemini/config/scripts/pre_tool_guard.py` to block automatic `git subtree add|pull|push|merge` execution and aligned `/sopen`, `/enrich`, and `/sclose` skills with mounted `layers/*` subtrees and `make verify`.
- **Multi-Layer & Multi-Environment (`dev`, `tst`, `pre`, `pro`) Support in `scripts/dotfiles_mcp_server.py` & `system/mcp-layer.json` (`v1.1`)**:
  - Upgraded `system/mcp-layer.json` to schema `1.1` with `environments` (`dev`, `tst`, `pre`, `pro` access modes, `requirements-<env>.txt` pointers, and default guardrails) and `mounted_layers_dir`.
  - Extended `DotfilesMCPServer` to auto-discover mounted subtrees in `layers/*/` and added `layer` (`"root"`, `<subtree>`, or `"all"`) and `environment` (`"dev"`, `"tst"`, `"pre"`, `"pro"`) filtering across `get_layer_overview`, `read_layer_document`, `query_governance_rules`, `discover_federated_mcps`, and `compare_layer_patterns`.
- **Runtime Token-Budget Warnings, Controlled Multi-Dimensional MCP Orchestration & Structured JSONL Logging (`logs/` & `dotfiles://mcp/diagnostics`)**:
  - Added `check_rules_token_budget` in `antigravity/.gemini/config/scripts/post_invocation_lint.py` to warn when `AGENTS.md` exceeds `18,000 bytes` (`TOKEN_BUDGET_EXCEEDED`) or when combined `always_on` rules across `AGENTS.md` and workspace `.agents/rules/*.md` exceed `80,000 bytes` (~20,000 tokens, `WORKSPACE_RULES_BUDGET_EXCEEDED`).
  - Added 5-level hierarchical guardrail inheritance (`effective_guardrails` = Root `baseline_guardrails` $\cup$ Subtree `baseline_guardrails` $\cup$ Root Environment `default_guardrails` $\cup$ Subtree Environment `default_guardrails` $\cup$ MCP `required_guardrails`), explicit `activation_policy` (`"on-demand"`), `when_to_invoke`, `avoid_when`, and an unfiltered fan-out guard (`MCP_FANOUT_WARNING` when $>3$ MCPs are returned without `environment` or `filter_role`) to `discover_federated_mcps`.
  - Added structured JSONL audit and alert logging (`logs/mcp_events.jsonl` recording `ts`, `method`, `target`, `layer`, `environment`, `duration_ms`, `response_bytes`, `estimated_tokens`, `warning_count`, and `status`, plus `logs/mcp_alerts.jsonl` with 512 KB size rotation, `--log-dir`, `--no-log`, and `DOTFILES_MCP_LOG_DIR` support), exposed a 9th MCP Resource (`dotfiles://mcp/diagnostics`) for remote container/SSH log inspection, and added in-band/out-of-band warnings for `TOKEN_BUDGET_NEAR_LIMIT` ($\ge 16,000$ bytes), `TOKEN_BUDGET_EXCEEDED` ($> 18,000$ bytes), `RESPONSE_TRUNCATED`, `LARGE_MCP_PAYLOAD_WARNING` ($> 16,000$ bytes), `SUBTREE_LINEAGE_WARNING`, `NODE_DRIFT_DETECTED`, and `SECURITY_OR_VALIDATION_ERROR`.
  - Removed duplicate `.ruff.toml` in favor of `pyproject.toml` as the single source of truth for `pytest`, `coverage`, `ruff`, and `mypy`.
- **Enterprise Integration Playbook (With or Without MCP) & Cross-Document Unification (`docs/` & `README.md`)**:
  - Expanded `README.md` (`Path 3`) and `docs/reference/enterprise_pair_programming_governance.md` (`§2`) with the 4-tier organizational integration flow (`Public Open-Source Upstream → Tier 1: Corporate Reference Fork → Tier 2A: Departmental Forks & Tier 2B: Team/Stack Forks → Tier 3: Application Development Repositories`) and a side-by-side comparison of **Perspective A (Without MCP: Pure Git + GNU Stow + Templates)** versus **Perspective B (With MCP: Contextual MCP Server + `layers/*` Subtree Graph + `dev/tst/pre/pro` Environments)**.
  - Unified all resource/script/check counts, lifecycle hook `stdin`/`stdout` JSON contracts, and `schema_version: "1.1"` examples across `docs/README.md`, `docs/architecture/02_antigravity_governance_and_hooks.md`, `docs/architecture/03_contextual_mcp_and_federation.md`, `docs/reference/contextual_mcp_and_multi_service_orchestration.md`, `docs/reference/developer_and_extension_guide.md`, and `SECURITY.md`.
- **End-to-End Test Suite (`tests/e2e/` & `make test-e2e`)**:
  - Completed the 3-tier testing pyramid (`tests/{unit,imp,e2e}`) with `tests/e2e/test_chained_mcp_federation_e2e.py` (validating chained multi-node `stdio` MCP communication from a Corporate/Team Hub MCP with mounted `layers/*` to a downstream Service Node MCP in `pre` environment, plus real `git subtree add` $\rightarrow$ `pull-all` $\rightarrow$ live MCP rule discovery across local Git repositories) and `tests/e2e/test_agent_turn_lifecycle_hooks_e2e.py` (simulating a complete 4-hook Antigravity agent turn `PreToolUse → PostToolUse → PostInvocation → Stop`), achieving `87 passed` at **100.00% statement and branch coverage**.

### Changed
- **Modularized `DotfilesMCPServer` (`scripts/dotfiles_mcp_server.py`)**:
  - Extracted static schema definitions to module-level constants (`MCP_RESOURCES_CATALOG`, `MCP_TOOLS_CATALOG`, `MCP_PROMPTS_CATALOG`) and decomposed `call_tool` and `read_resource` into dedicated single-responsibility methods (`_tool_get_layer_overview`, `_tool_audit_node_drift`, `_tool_read_layer_document`, `_tool_query_governance_rules`, `_tool_discover_federated_mcps`, `_tool_compare_layer_patterns`, `_read_diagnostics_resource`).

---

## [1.4.0] - 2026-10-28

### Added
- **Automated Test Suite (`tests/unit/` & `tests/imp/`) with 100% Statement & Branch Coverage**:
  - Added 1:1 unit tests in `tests/unit/` covering all 5 Python modules in the repository (`test_pre_tool_guard.py`, `test_post_edit_format.py`, `test_post_invocation_lint.py`, `test_stop_verify_tests.py`, and `test_dotfiles_mcp_server.py`) following strict 3-comment AAA (`# Arrange`, `# Act`, `# Assert`) and `0-byte` `__init__.py` package marker purity (`77 passed`, `599 statements`, `254 branches`, **100.00% branch coverage**).
  - Added integration/subprocess tests in `tests/imp/`:
    - `tests/imp/test_mcp_and_hooks_stdio.py`: End-to-end `stdio` JSON-RPC 2.0 tests for `scripts/dotfiles_mcp_server.py` (both newline-delimited and `Content-Length` framed streams, `--self-test`, `--version`) and subprocess tests for all 4 Antigravity lifecycle hooks (`pre_tool_guard.py`, `post_edit_format.py`, `post_invocation_lint.py`, `stop_verify_tests.py`).
    - `tests/imp/test_cli_scripts.py`: Deterministic CLI contract tests (`--help`, `--version`, invalid flag rejection with non-zero exit code) across `bootstrap.sh`, `backup.sh`, `audit.sh`, `scripts/verify-repo.sh`, and `scripts/antigravity-install.sh`, plus `bash -n` syntax verification across all 16 shell scripts and `system/external/*/*.sh` recipes.
- **Layered Python Dependency Architecture & Self-Contained Development `venv` (`requirements.txt`, `requirements-dev.txt`, `pyproject.toml`, `Makefile`)**:
  - Added `requirements.txt` (base runtime contract — zero external packages in upstream since runtime hooks and `dotfiles_mcp_server.py` execute directly on Ubuntu 26.04 LTS's system `Python 3.14` standard library, while serving as the base anchor for forks or `requirements-{tst,pre,pro}.txt` environment profiles) and `requirements-dev.txt` (chaining `-r requirements.txt` + `pytest`, `pytest-cov`, `ruff`, `mypy`).
  - Added `pyproject.toml` (centralized `pytest`, `coverage` 100% branch gate, `ruff` `py314`, and `mypy --strict` configuration) and `Makefile` (`make install`, `make install-runtime`, `make test`, `make test-unit`, `make test-imp`, `make test-cov`, `make lint`, `make typecheck`, `make format`, `make verify`, `make audit`, `make clean`).
  - Updated `bootstrap.sh`, `audit.sh`, and `.gitignore` to exclude non-stow development directories (`tests/`, `venv/`, `.venv/`, `htmlcov/`, `.pytest_cache/`, `.mypy_cache/`, `.coverage`).
  - Extended `scripts/verify-repo.sh` (`[1/8]` through `[8/8]`) and `.github/workflows/ci.yml` to run `ruff check`, `mypy --strict` (0 errors across 15 source and test files), `0-byte` `tests/**/__init__.py` checks, and `pytest --cov --cov-branch --cov-fail-under=100` in CI.

### Fixed
- **`scripts/dotfiles_mcp_server.py` Repository Path & OS Release Parameterization**:
  - Updated `_read_version`, `_read_git_commit`, `_parse_skill_frontmatter`, and `DotfilesMCPServer` to resolve paths against the instance's `repo_dir` parameter rather than the import-time module constant `REPO_DIR`, and parameterized `_read_os_pretty_name(os_release)` for deterministic unit testing and strict `mypy --strict` compliance.

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
