# Developer & Extension Guide for `dotfiles-ubuntu`

> **Reference Guide — Evolving `dotfiles-ubuntu` Safely & Coherently**
>
> This guide provides step-by-step instructions for extending `dotfiles-ubuntu` itself — whether adding a new root directory, creating a new Layer 2 project starter template, adding an external package recipe, or modifying Antigravity 2.0 lifecycle hooks. AI agents and maintainers should consult this guide before modifying repository structure.

---

## 1. Adding a New Top-Level Directory (Stow vs. Non-Stow Checklist)

Because `bootstrap.sh` (Step 3) and `audit.sh` (Section 1) iterate over `*/` at the repository root to discover GNU Stow modules dynamically, every new root directory must be explicitly classified:

### Case A — Adding a New GNU Stow Module (e.g., `tmux/` or `ssh/`)
1. Mirror the target `$HOME` structure inside the module directory (e.g., `tmux/.tmux.conf` $\rightarrow$ `~/.tmux.conf`).
2. If the target directory in `$HOME` contains untracked machine-local files (like `~/.ssh/`), pre-create the real directory in `bootstrap.sh` before stowing so GNU Stow performs **tree unfolding** and never symlinks the parent folder.
3. Update the `Repository Structure` tree and `Stow modules vs regular directories` table in [`README.md`](../../README.md) and [`docs/architecture/01_system_and_stow_engine.md`](../architecture/01_system_and_stow_engine.md).

### Case B — Adding a Non-Stow Root Directory (e.g., `docs/`, `templates/`, `scripts/`, `system/`)
1. Add the directory exclusion to **both** [`bootstrap.sh`](../../bootstrap.sh) (Step 3) and [`audit.sh`](../../audit.sh) (Section 1):
   ```bash
   [ "$module" = "<new-dir>" ] && continue
   ```
2. Document the directory in [`README.md`](../../README.md) and [`docs/architecture/01_system_and_stow_engine.md`](../architecture/01_system_and_stow_engine.md).

---

## 2. Parameterizing a Fork & Adding Polymorphic Template Packs (`scripts/layer-config.sh` & `templates/<name>/`)

Whether a fork represents a **Corporate Baseline (`corporate`)**, a **Statutory/Legal Domain Policy (`domain-policy`)**, a **Department (`department`)**, or a **Tech-Stack Team (`team`)**, use `./scripts/layer-config.sh` rather than editing manifests manually:

1. **Parameterize Fork Identity (`init-fork`)**:
   ```bash
   ./scripts/layer-config.sh init-fork \
     --id acme-dept-legal \
     --role domain-policy \
     --precedence 5 \
     --upstream-url https://github.com/acme/dotfiles-corp.git \
     --prune-default-templates
   ```
   - `--prune-default-templates` removes the upstream `fastapi-hexagonal` template reference and its `surface_bindings` when a fork does not target Python/FastAPI.
2. **Scaffold a Polymorphic Template Pack (`scaffold-template`)**:
   ```bash
   ./scripts/layer-config.sh scaffold-template gdpr-eu \
     --kind domain-policy-pack \
     --register-binding
   ```
   This generates `templates/<name>/template.json` (`kind`: `stack-starter` | `domain-policy-pack` | `department-pack` | `project-overlay`), `rules/`, `skills/<name>-guide/SKILL.md`, and `governance/` or `assets/`.
3. **Inspect & Materialize a Fork into a Target Application Repository (`list-templates` & `apply-project` — Without MCP / Static Mode)**:
   ```bash
   ./scripts/layer-config.sh list-templates [--json]
   ./scripts/layer-config.sh apply-project /path/to/project \
     --template fastapi-hexagonal \
     --layers all
   ```
   Copies the chosen template pack (`rules/`, `skills/`, `governance/`, `assets/`) plus all participating mounted layers (`layers/*` ordered by numeric `precedence` `0..100` into `.agents/rules/layer-<precedence>-<name>.md`) and writes `.agents/LAYER_LINEAGE.md` (with merged effective `surface_bindings` counts).
4. **Diff & Promote Matured Project Patterns Upstream (`diff-project` & `promote-from-project`)**:
   ```bash
   ./scripts/layer-config.sh diff-project /path/to/project [--json]
   ./scripts/layer-config.sh promote-from-project /path/to/project \
     --asset .agents/rules/security-audit.md \
     --to-layer dept-security
   ```
   Compares SHA-256 digests across `.agents/{rules,skills,assets}/` (`in_sync`, `modified_in_project`, `novel_in_project`) and promotes rules, skills, or canonical assets back into `Root`, `layers/<name>`, or `templates/<pack>` while enforcing `AGENTS.md` ($\le 18{,}000$ bytes) and `SKILL.md` frontmatter gates.
5. **Verify `SKILL.md` Frontmatter & Token Budget**: Every `SKILL.md` file inside `templates/` is automatically scanned by `scripts/verify-repo.sh` (Check `[6/8]`). Ensure `name:` is strictly `kebab-case`, `description:` is non-empty, and the file is `< 500` lines.

---

## 3. Adding or Updating an External Ubuntu Package Recipe (`system/external/`)

1. Choose the appropriate recipe mechanism (`apt-repo/`, `deb-url/`, or `script/`) per [`docs/architecture/01_system_and_stow_engine.md`](../architecture/01_system_and_stow_engine.md) §3.3:
   - **Prefer `apt-repo/`** whenever the vendor publishes an official signed APT repository (automatic security updates via `apt upgrade`).
   - Use **`deb-url/`** for standalone `.deb` packages without an APT repo.
   - Use **`script/`** for `/opt/` binary tarballs or custom installers.
2. Ensure the script passes `bash -n` (verified automatically by `./scripts/verify-repo.sh` Check `[2/8]`).
3. Do **not** add the recipe to `system/external.txt` unless it is installed on the reference machine — `./backup.sh` populates `system/external.txt` automatically by evaluating each recipe's `CHECK` / `CHECK_CMD`.

---

## 4. Modifying `AGENTS.md`, Global Skills, or Lifecycle Hooks

1. **Always Edit Source of Truth First**:
   - Edit files inside `~/dotfiles-ubuntu/antigravity/.gemini/config/`, never directly via `~/.gemini/config/` when creating new skill directories.
2. **Re-Stow After Structural Changes**:
   ```bash
   cd ~/dotfiles-ubuntu && stow -t ~ -R antigravity
   ```
3. **Run the Full Verification & Symlink Audit Suite**:
   ```bash
   cd ~/dotfiles-ubuntu
   ./scripts/verify-repo.sh
   ./scripts/audit-global-config.sh
   ./audit.sh
   ```
4. **Release Versioning (`VERSION` + `CHANGELOG.md`)**:
   - Bump [`VERSION`](../../VERSION) following Semantic Versioning (`MAJOR.MINOR.PATCH`), add the matching `## [X.Y.Z] - YYYY-MM-DD` section in [`CHANGELOG.md`](../../CHANGELOG.md), and update the version badge in [`README.md`](../../README.md).

---

## 5. Extending or Customizing the Contextual MCP Server (`scripts/dotfiles_mcp_server.py`)

When extending the optional Contextual Layer & System MCP Server ([`docs/architecture/03_contextual_mcp_and_federation.md`](../architecture/03_contextual_mcp_and_federation.md)):

1. **Preserve the Zero-Dependency & Read-Only Invariants**:
   - Use **only** the Python 3 standard library (`json`, `sys`, `os`, `pathlib`, `subprocess`, `re`, `platform`). Never import third-party packages that would require `pip install`.
   - Every MCP resource and tool must remain **strictly read-only**. Never add tools that mutate files, execute arbitrary shell commands, or read files outside `REPO_DIR`.
2. **Customizing Layer Identity, Mounted Subtrees & Federated MCPs (`system/mcp-layer.json` & `scripts/layer-subtree.sh`)**:
   - Fork maintainers can edit `system/mcp-layer.json` (`schema_version: "1.2"`) to set `layer_id`, `layer_role` (`corporate`, `department`, `domain-policy`, `team`, `service-node`, `environment-cluster`, or `workstation`), `precedence` (`0..100`), `surface_bindings`, `upstream_layer`, `baseline_guardrails`, `environments` (`dev`, `tst`, `pre`, `pro`), and `federated_mcps` (along with their `required_guardrails`, `activation_policy`, `when_to_invoke`, and `avoid_when`).
   - Secondary forks (departmental rules, sibling service MCPs, or environment clusters) can be mounted into `layers/<name>/` via `./scripts/layer-subtree.sh add <name> <repo-url> [branch]`, updated individually (`./scripts/layer-subtree.sh pull <name>`) or globally (`./scripts/layer-subtree.sh pull-all`), and promoted upstream via `./scripts/layer-subtree.sh push <name> <target-branch>`.
3. **Run the Deterministic MCP, Subtree & Container Self-Tests**:
   ```bash
   ./scripts/layer-subtree.sh list
   ./scripts/layer-subtree.sh pull-all
   ./scripts/dotfiles_mcp_server.py --self-test
   make docker-build && make docker-self-test
   ./scripts/verify-repo.sh
   ```

---

## 6. Python Virtual Environment (`venv`), Automated Testing (`tests/{unit,imp,e2e}`) & 100% Coverage Gate

`dotfiles-ubuntu` practices what its own `AGENTS.md` and `templates/fastapi-hexagonal/` prescribe:

### 6.1. Layered Dependency Separation (`requirements.txt` $\leftarrow$ `requirements-dev.txt` & Environment Profiles)
- **Base Runtime ([`requirements.txt`](../../requirements.txt) — Zero External Dependencies in Upstream)**: Every script executed during normal workstation, container, or remote server operation (`bootstrap.sh`, `backup.sh`, `audit.sh`, `antigravity/.gemini/config/scripts/*.py`, and `scripts/dotfiles_mcp_server.py`) uses **only the Python 3 standard library** and runs directly on Ubuntu 26.04 LTS's native `/usr/bin/python3` (`Python 3.14`; `dotfiles_mcp_server.py` also maintains `Python >= 3.10` compatibility for older containers or remote hosts). Consequently, `requirements.txt` contains zero packages in the upstream base repository, so users cloning `dotfiles-ubuntu` do **not** need a `venv` at runtime.
- **Multi-Environment Fork Extensibility (`tst`, `pre`, `pro`)**: If a corporate, team, or service-node fork extends `dotfiles-ubuntu` with custom MCP tools or scripts that require third-party runtime libraries, shared runtime packages can be added to `requirements.txt` (`make install-runtime`), and environment-specific MCP dependencies (`tst`, `pre`, `pro`) can be declared in `requirements-<env>.txt` files starting with `-r requirements.txt`.
- **Development & Testing (`./venv` + [`requirements-dev.txt`](../../requirements-dev.txt))**: `requirements-dev.txt` chains `-r requirements.txt` and adds the development/verification toolchain (`pytest`, `pytest-cov`, `ruff`, `mypy`) managed via [`Makefile`](../../Makefile) (`make install`) and [`pyproject.toml`](../../pyproject.toml).

### 6.2. Test Suite Architecture (`tests/unit/`, `tests/imp/` & `tests/e2e/`)
- **`tests/unit/` (1:1 Module Mapping & 100% Branch Coverage)**:
  - `test_pre_tool_guard.py` $\rightarrow$ `antigravity/.gemini/config/scripts/pre_tool_guard.py`
  - `test_post_edit_format.py` $\rightarrow$ `antigravity/.gemini/config/scripts/post_edit_format.py`
  - `test_post_invocation_lint.py` $\rightarrow$ `antigravity/.gemini/config/scripts/post_invocation_lint.py`
  - `test_stop_verify_tests.py` $\rightarrow$ `antigravity/.gemini/config/scripts/stop_verify_tests.py`
  - `test_dotfiles_mcp_server.py` $\rightarrow$ `scripts/dotfiles_mcp_server.py`
  - `tests/unit/dotfiles_mcp/test_<module>.py` $\rightarrow$ `1:1` unit test suites for all executable modules in `scripts/dotfiles_mcp/` (`capsule_engine`, `fork_configurator`, `manifest_helpers`, `node_base`, `promotion_engine`, `resources`, `server`, `surface_weaver`, `tools_compaction`, `tools_federation`, `tools_surface`, `tools_unfold`).
- **`tests/imp/` (Subprocess, `stdio` JSON-RPC 2.0 & Bash CLI Contracts)**:
  - `test_mcp_and_hooks_stdio.py`: Tests real subprocess `stdin`/`stdout` framing (newline-delimited and `Content-Length` LSP-style headers) for `dotfiles_mcp_server.py` and all 4 lifecycle hooks.
  - `test_cli_scripts.py`: Verifies `--help`, `--version`, invalid flag rejection, `layer-subtree.sh` (`list`, `pull`, `push`, `pull-all`), and `bash -n` syntax across all 17 `.sh` scripts and external package recipes.
- **`tests/e2e/` (End-to-End Chained Multi-Node MCP Federation, `git subtree` & Full Agent Turn Simulation)**:
  - `test_chained_mcp_federation_e2e.py`: Spawns chained `stdio` MCP server instances (`Corporate/Team Hub MCP` with mounted `layers/*` $\rightarrow$ `Downstream Service Node MCP` in `pre` environment) to validate end-to-end discovery, `effective_guardrails` inheritance, cross-node package manifest comparison, JSONL diagnostics (`dotfiles://mcp/diagnostics`), and real `git subtree add` + `pull-all` + live MCP rule discovery across local Git repositories.
  - `test_agent_turn_lifecycle_hooks_e2e.py`: Executes a full 4-hook agent turn (`PreToolUse` $\rightarrow$ `PostToolUse` $\rightarrow$ `PostInvocation` $\rightarrow$ `Stop`) against a real temporary Git workspace.
- **Mandatory Quality Gates**:
  - Every test function must contain explicit `# Arrange`, `# Act`, and `# Assert` comments.
  - All `tests/**/__init__.py` files must be **0 bytes** (package marker purity).
  - `make test-cov` enforces **100.00% statement and branch coverage** (`--cov-branch --cov-fail-under=100`).
  - `make lint` enforces `ruff check` and `mypy --strict` with 0 errors across all source and test files.
