# Changelog

All notable changes to `dotfiles-ubuntu` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-10-27

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
