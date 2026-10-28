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

### B. Adding or Updating an Antigravity Skill (`antigravity/.gemini/config/skills/`)

1. Create `antigravity/.gemini/config/skills/<skill-name>/SKILL.md`.
2. Include valid YAML frontmatter at the top of `SKILL.md`:
   - `name:` **MUST** be `kebab-case` (lowercase letters, digits, and hyphens only, e.g., `name: architecture-review`).
   - `description:` A concise 1–2 sentence trigger description explaining *when* the agent should activate the skill.
3. Keep `SKILL.md` under **500 lines**. If a skill needs large reference tables or templates, place them in subdirectories (`references/`, `examples/`, `scripts/`) inside the skill folder.
4. Re-stow after creating a new skill directory:
   ```bash
   cd ~/dotfiles-ubuntu && stow -t ~ -R antigravity
   ```

### C. Modifying Lifecycle Hooks (`antigravity/.gemini/config/hooks.json` & `scripts/`) or the MCP Server (`scripts/dotfiles_mcp_server.py`)

All Python scripts in `antigravity/.gemini/config/scripts/*.py` and `scripts/dotfiles_mcp_server.py` must:
- Use **100% Python Standard Library** at runtime (zero external `pip` dependencies so runtime execution works out-of-the-box without a `venv`).
- Include `from __future__ import annotations` and pass `mypy --strict` and `ruff check` with 0 errors.
- Be executable (`chmod +x`).
- Maintain **100% statement and branch coverage** in `tests/unit/` with explicit `# Arrange`, `# Act`, `# Assert` comments and `0-byte` `tests/**/__init__.py` files.

---

## 3. Development Environment (`venv`), Testing & Pre-Commit Verification

`dotfiles-ubuntu` uses a two-tier dependency layout:
- **[`requirements.txt`](requirements.txt)** — Base runtime dependencies (empty in the upstream repository because `scripts/dotfiles_mcp_server.py` and the `~/.gemini/config/scripts/*.py` hooks use 100% Ubuntu 26.04 LTS `Python 3.14` standard library; extensible in corporate/service forks or via `requirements-<env>.txt`).
- **[`requirements-dev.txt`](requirements-dev.txt)** — Chains `-r requirements.txt` and installs the development, testing, and linting toolchain (`pytest`, `pytest-cov`, `ruff`, `mypy`) into `./venv`.

Contributors modifying Python scripts, hooks, or tests should initialize `./venv` via [`Makefile`](Makefile):

```bash
cd ~/dotfiles-ubuntu

# 1. Create ./venv and install dev/test tools from requirements-dev.txt (chains -r requirements.txt)
make install

# 2. Run unit + integration tests with 100% statement and branch coverage gate
make test-cov

# 3. Run Ruff linter + Mypy --strict type checking
make lint

# 4. Run full 8-stage repository verification suite (Bash, Python, hooks.json, AGENTS.md budget, SKILL.md, MCP self-test, pytest 100% cov)
make verify

# 5. Verify local ~/.gemini/config/ symlinks & tree unfolding (if stowed locally)
./scripts/audit-global-config.sh
```

---

## 4. Versioning & Commit Conventions

- **Conventional Commits**: All commit messages follow [Conventional Commits](https://www.conventionalcommits.org/):
  - `feat:` — New skill, hook, bootstrap capability, or external recipe
  - `fix:` — Bug fix in scripts, hooks, or rules
  - `enrich:` — Knowledge promotion from downstream projects into global rules/skills
  - `docs:` — Documentation or template updates
  - `chore:` — Package manifest snapshots (`system/*.txt`) or maintenance
- **Semantic Versioning (`VERSION` + `CHANGELOG.md`)**:
  - Update `VERSION` and `CHANGELOG.md` when cutting a new release, and tag with `git tag -a vX.Y.Z -m "Release vX.Y.Z"`.
