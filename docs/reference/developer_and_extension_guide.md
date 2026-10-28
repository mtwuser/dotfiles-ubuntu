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

## 2. Adding a New Layer 2 Stack Starter Template (`templates/<stack>/`)

To support a new technology stack or team archetype (for example, `templates/gcp-data-platform/`, `templates/nextjs-typescript/`, or `templates/rust-axum/`):

1. Create the directory structure under `templates/<stack-name>/`:
   ```
   templates/<stack-name>/
   ├── rules/
   │   ├── coding.md           # trigger: always_on (stack architecture & coding rules)
   │   ├── environment.md      # trigger: always_on (runtime, commands, safety)
   │   ├── governance.md       # trigger: model_decision (work lifecycle)
   │   └── testing.md          # trigger: model_decision (test tiers & coverage gates)
   ├── skills/
   │   ├── start/SKILL.md      # name: start (session startup checklist)
   │   └── <domain>/SKILL.md   # name: <kebab-case> (< 500 lines)
   └── governance/
       ├── WORKTASK.md
       ├── WORKROAD.md
       ├── WORKVALI.md
       ├── BACKLOG.md
       ├── CHANGELOG.md
       └── SESSION.md
   ```
2. **Verify `SKILL.md` Frontmatter**: Every `SKILL.md` file inside `templates/` is automatically scanned by `scripts/verify-repo.sh` (Check `[6/6]`). Ensure `name:` is strictly `kebab-case`, `description:` is non-empty, and the file is `< 500` lines.
3. **Keep `always_on` Rules Compact**: Remember that a project's `always_on` rules share the 20,000-token `defaultRulesBudget` with `~/.gemini/config/AGENTS.md`. Use `trigger: model_decision` for testing, governance, and documentation rules.

---

## 3. Adding or Updating an External Ubuntu Package Recipe (`system/external/`)

1. Choose the appropriate recipe mechanism (`apt-repo/`, `deb-url/`, or `script/`) per [`docs/architecture/01_system_and_stow_engine.md`](../architecture/01_system_and_stow_engine.md) §3.3:
   - **Prefer `apt-repo/`** whenever the vendor publishes an official signed APT repository (automatic security updates via `apt upgrade`).
   - Use **`deb-url/`** for standalone `.deb` packages without an APT repo.
   - Use **`script/`** for `/opt/` binary tarballs or custom installers.
2. Ensure the script passes `bash -n` (verified automatically by `./scripts/verify-repo.sh` Check `[2/6]`).
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
