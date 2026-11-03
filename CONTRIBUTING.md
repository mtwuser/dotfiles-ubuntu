# Contributing to dotfiles-ubuntu

Thank you for your interest in contributing to **dotfiles-ubuntu** — the declarative Ubuntu 26.04 LTS system manager and Google Antigravity 2.0 customization suite.

> **Navigable Architecture & Maintainer Documentation**: Before modifying scripts, stow modules, templates, or the MCP server, consult **[`docs/README.md`](docs/README.md)** and the step-by-step maintainer playbook at **[`docs/reference/developer_and_extension_guide.md`](docs/reference/developer_and_extension_guide.md)**.

---

## 1. Repository Architecture & Design Invariants

Every contribution must preserve the three foundational invariants of this repository:

1. **Zero Secret / Identity Leakage**:
   - Personal identity (`user.name`, `user.email`), SSH/GPG keys, OAuth tokens (`~/.gemini/*.json`), and machine-specific overrides (`~/.bashrc.local`, `~/.gitconfig.local`, `.audit-ignore`) must **never** be committed.
2. **GNU Stow Tree Unfolding (`~/.gemini/config/`)**:
   - `~/.gemini/`, `~/.gemini/config/`, and `~/.gemini/config/skills/` must remain **real directories** on disk so GNU Stow creates individual symlinks for `AGENTS.md`, `hooks.json`, `scripts/`, and each shared skill folder without touching local credentials or MCP configs.
3. **Antigravity 2.0 Token Budget & Progressive Disclosure**:
   - Antigravity 2.0 enforces a **20,000-token `defaultRulesBudget`** across all active `always_on` rules (`AGENTS.md` + workspace `.agents/rules/*.md`) and a **24 KB per-file cap**.
   - `antigravity/.gemini/config/AGENTS.md` must remain **under 18,000 bytes** (~15–16 KB target) so it is always 100% inline-injected even in multi-repo workspaces.
   - Detailed step-by-step procedures belong in on-demand skills (`antigravity/.gemini/config/skills/<name>/SKILL.md`), not in `AGENTS.md`.

---

## 2. Adding or Modifying Components

### A. Adding an External Package Recipe (`system/external/`)

Third-party software outside the standard Ubuntu 26.04 APT repositories lives in the `system/external/` catalog under one of three categories:

| Directory | Use Case | Required Variables / Functions |
|-----------|----------|-------------------------------|
| `system/external/apt-repo/<name>.sh` | Packages with their own DEB822 `.sources` APT repository | `NAME`, `DESCRIPTION`, `CHECK`, `PACKAGES`, and `setup_repo()` |
| `system/external/deb-url/<name>.sh` | Standalone `.deb` packages downloaded via HTTPS | `NAME`, `DESCRIPTION`, `CHECK`, and `URL` |
| `system/external/script/<name>.sh` | Custom binary/installer recipes | `NAME`, `DESCRIPTION`, `CHECK_CMD`, and `INSTALL_CMD` |

> **Important**: Adding a recipe to `system/external/*/*.sh` makes it available in the catalog without forcing it onto other users' machines. A machine only installs or audits recipes listed in `system/external.txt` (which `./backup.sh` populates automatically based on what is installed locally).

### B. Adding or Updating an Antigravity Skill (`antigravity/.gemini/config/skills/` or `templates/technical-base/skills/`)

1. Universal lifecycle, governance, and dual-mode audit skills (`10` global skills: `sopen`, `sclose`, `continue`, `release`, `enrich`, `priority`, `review`, `full-audit`, `architecture-review`, `governance`) live in `antigravity/.gemini/config/skills/<skill-name>/SKILL.md`, software-engineering-specific skills (`4` `technical-base` skills: `testing`, `refactoring`, `validation`, `oss-contribute`) live in `templates/technical-base/skills/<skill-name>/SKILL.md`, and specialization-stack skills (`5` skills across `business-stack` and `tech-stack`) live in `templates/{business-stack,tech-stack}/*/skills/<skill-name>/SKILL.md` (`19` total skills).
2. Include valid YAML frontmatter at the top of `SKILL.md`:
   - `name:` **MUST** be `kebab-case` (lowercase letters, digits, and hyphens only, e.g., `name: architecture-review`).
   - `description:` A concise 1–2 sentence trigger description explaining *when* the agent should activate the skill.
3. Keep `SKILL.md` under **500 lines**. If a skill needs large reference tables or templates, place them in subdirectories (`references/`, `examples/`, `scripts/`) inside the skill folder.
4. Re-stow after creating or modifying a global skill directory:
   ```bash
   cd ~/dotfiles-ubuntu && stow -t ~ -R antigravity
   ```

### C. Modifying Lifecycle Hooks (`antigravity/.gemini/config/hooks.json` & `scripts/`), the Contextual MCP Package (`scripts/dotfiles_mcp/` & `scripts/dotfiles_mcp_server.py`), or Layer/Subtree/Docker Tooling (`scripts/layer-config.sh`, `scripts/layer-subtree.sh`, `Dockerfile`)

All Python modules in `antigravity/.gemini/config/scripts/*.py`, `scripts/dotfiles_mcp_server.py`, and `scripts/dotfiles_mcp/{core,capsules,mcp_node,governance}/*.py` (`24` modules across `4` bounded-domain subpackages) must:
- Use **100% Python Standard Library** at runtime (zero external `pip` dependencies so runtime execution works out-of-the-box without a `venv`) and prefer C-backed floor-version stdlib primitives (`hashlib.file_digest`, `stat.S_IWUSR`, `Path.is_relative_to`).
- Include `from __future__ import annotations`, declare a `Specification: docs/architecture/<spec>.md` pointer in the module docstring (`1:1:1` Source $\leftrightarrow$ Unit Test $\leftrightarrow$ Spec traceability), follow the self-indexing file-prefix taxonomy (`tools_*`, `*_engine`, `NN_*`, `test_*`), stay strictly **`< 465` lines** (`<= 400` target via the 6-Stage Structural Evolution Ladder, keeping `.sh` CLI wrappers `< 250` lines via `cli_dispatcher.py`), and pass `mypy --strict` and `ruff check` with 0 errors.
- Centralize contract identifiers (`LAYER_MANIFEST_CONTRACT_REV`, `TEMPLATE_MANIFEST_CONTRACT_REV`), slice bounds, and domain cut-points in [`scripts/dotfiles_mcp/core/constants.py`](scripts/dotfiles_mcp/core/constants.py) with explicit absolute imports (zero magic numbers/raw slices, zero `import ... as c` aliases, `.get()` at external boundaries vs. `d["k"]` on guaranteed internal dicts, and `{...}` literals instead of `.update()` packing).
- Keep `scripts/dotfiles_mcp/**/__init__.py` and all `tests/**/__init__.py` files at **`0 bytes`** (package marker purity).
- Maintain **100% isolated unit test coverage** (`tests/unit/dotfiles_mcp/`) and **100% total statement and branch coverage** across `tests/unit/`, `tests/imp/`, and `tests/e2e/` (`1` `Test<Module>` class per file, 1-line invariant docstring on every `test_*` method, explicit `# Arrange`, `# Act`, `# Assert` comments, exact boundary cut-points `N` vs `N ± 1`, bipolar guard assertions, and zero `# pragma: no cover` or blind `subprocess.run` lambdas).

---

## 3. Development Environment (`venv`), Testing & Pre-Commit Verification

`dotfiles-ubuntu` uses a two-tier dependency layout:
- **[`requirements.txt`](requirements.txt)** — Base runtime dependencies (empty in the upstream repository because `scripts/dotfiles_mcp_server.py` and the `~/.gemini/config/scripts/*.py` hooks use 100% Ubuntu 26.04 LTS `Python 3.14` standard library; extensible in corporate/service forks or via `requirements-<env>.txt`).
- **[`requirements-dev.txt`](requirements-dev.txt)** — Chains `-r requirements.txt` and installs the development, testing, and linting toolchain (`pytest`, `pytest-cov`, `ruff`, `mypy`, `shellcheck-py`) into `./venv`.

Contributors modifying Python scripts, hooks, MCP/Docker tooling, or tests should initialize `./venv` (and local `.agents/` overlay) via [`Makefile`](Makefile):

```bash
cd ~/dotfiles-ubuntu   # or cd "$DOTFILES_DEV_REPO_DIR"

# 1. Create ./venv, install requirements-dev.txt, and materialize .agents/ (technical-base + Priority-1 skills)
make setup-dev         # (or 'make install' for ./venv only)

# 2. Check consolidated workspace status (operating_state, mcp_operating_mode, command_tiers, horizon & diff)
make status

# 3. Run unit + implementation + end-to-end tests with 100% statement and branch coverage gate
make test-cov

# 4. Run Ruff linter + Mypy --strict type checking
make lint

# 5. Run full 8-stage repository verification suite (Bash, ShellCheck, Python, hooks.json, AGENTS.md budget, SKILL.md, MCP/Subtree/Docker contract, pytest 100% isolated + total cov)
make verify

# 6. (Optional) Build and verify the hardened Ubuntu 26.04 MCP Docker image
make docker-build && make docker-self-test

# 7. Verify local ~/.gemini/config/ symlinks & tree unfolding (if stowed locally)
./scripts/audit-global-config.sh
```

### Dual-Clone Contributing Setup (`~/dotfiles-ubuntu` Runtime vs. Dedicated Dev Clone)

When contributing upward from an Enterprise `Root 0` workspace while keeping `~/dotfiles-ubuntu` as your clean workstation runtime (`human-core` stowed into `~/.gemini/config/`):
- Maintain a dedicated development clone at `~/Projects/dev-<repo>` (or set `DOTFILES_DEV_REPO_DIR`) with `technical-base` projected into `.agents/rules/`.
- `inspect-horizon` and `Root 0` generated `Makefile` (`CONTRIB_REPO`) automatically detect `DOTFILES_DEV_REPO_DIR` or `~/Projects/dev-<repo>` and route upward Open-Source promotions (`promote-from-project --create-pr`) to the contributing clone while keeping `~/dotfiles-ubuntu` as the runtime `sync-layer` parent.
- Use optional `--org "<Organization>"`, `--contributors "<Roles/Handles>"`, and `--context "<Validation Topology>"` flags when generating upward PR plans (defaults remain 100% anonymous when omitted).

---

## 4. Versioning & Commit Conventions

- **Conventional Commits**: All commit messages follow [Conventional Commits](https://www.conventionalcommits.org/):
  - `feat:` — New skill, hook, bootstrap/governance capability, or external recipe
  - `fix:` — Bug fix in scripts, hooks, MCP engines, or rules
  - `refactor:` — Structural code decomposition (`< 465` lines), constant extraction, or symmetry alignment
  - `test:` — Unit (`tests/unit/`), implementation (`tests/imp/`), or end-to-end (`tests/e2e/`) test additions
  - `enrich:` — Knowledge promotion from downstream projects into global rules/skills
  - `docs:` — Documentation or template updates
  - `chore:` — Package manifest snapshots (`system/*.txt`) or maintenance
- **Semantic Versioning (`VERSION` + `CHANGELOG.md`)**:
  - Record iterative changes under `## [Unreleased]` in `CHANGELOG.md` without bumping `VERSION` during working commits; cut explicit SemVer releases (`VERSION`, `pyproject.toml`, `README.md`, `CHANGELOG.md`, and `git tag -a vX.Y.Z`) via `/release`.
