# Ubuntu 26.04 System Management, GNU Stow & Multi-Machine Operations Guide

> **Human Operator Manual (Tier 2 Progressive Disclosure)**
>
> Complete operational guide for managing Ubuntu 26.04 LTS packages, GNU Stow dotfile symlinks, Antigravity binary upgrades, multi-machine provisioning/migration, drift audits, and uninstallation. For internal engine specifications, see **[`docs/architecture/01_system_and_stow_engine.md`](../architecture/01_system_and_stow_engine.md)**; for the executive overview, return to **[`README.md`](../../README.md)**.

---

## 1. How GNU Stow & Tree Unfolding Work

GNU Stow projects tracked configuration modules from `~/dotfiles-ubuntu` into `$HOME` while preserving untracked machine-local files.

### 1.1. Stow Modules (`bash/`, `git/`, `antigravity/`)

Each stow module mirrors `$HOME`. When activated from `~/dotfiles-ubuntu`, GNU Stow creates symlinks into `~`:

```
~/dotfiles-ubuntu/bash/.bashrc                              → ~/.bashrc
~/dotfiles-ubuntu/git/.gitconfig                            → ~/.gitconfig
~/dotfiles-ubuntu/antigravity/.gemini/config/AGENTS.md      → ~/.gemini/config/AGENTS.md
~/dotfiles-ubuntu/antigravity/.gemini/config/skills/<name>/ → ~/.gemini/config/skills/<name>/
~/dotfiles-ubuntu/antigravity/.local/share/applications/    → ~/.local/share/applications/
```

**Manage modules directly with `stow`:**

```bash
cd ~/dotfiles-ubuntu
stow -t ~ bash        # Activate a module
stow -t ~ -D bash     # Deactivate a module
stow -t ~ -R bash     # Re-stow after changes
```

> **Important**: Because the repository lives at `~/dotfiles-ubuntu`, always pass `-t ~` to `stow`. The [`bootstrap.sh`](../../bootstrap.sh) script handles this automatically.

### 1.2. Why `~/.gemini/config/` Uses Stow Tree Unfolding (Individual Symlinks)

Unlike `~/.bashrc` (a single file symlink), `~/.gemini/config/` and `~/.gemini/config/skills/` are **real directories** that mix tracked dotfiles with machine-local runtime files:
- **Tracked via Stow (`~/dotfiles-ubuntu/antigravity/`)**: `AGENTS.md`, `hooks.json`, `scripts/`, and the 10 universal global skills inside `skills/<name>/` (while the 4 software-engineering skills `testing`, `refactoring`, `validation`, and `oss-contribute` live in `templates/science-stack/software-engineering/skills/` and are projected into `.agents/skills/` on technical workspaces).
- **Machine-local (untracked)**: `config.json`, `mcp_config.json`, `plugins/`, `projects/`, `sidecars/`, `.ruff_cache/`, and locally installed extension/cloud skills inside `skills/`.

Because `~/.gemini/config/` and `~/.gemini/config/skills/` already exist as real directories, GNU Stow automatically performs **tree unfolding**: it creates individual symlinks for each tracked item (`AGENTS.md`, `hooks.json`, `scripts/`, and each shared skill folder `skills/<name>`) without touching local credentials, MCP servers, or third-party skills.

Verify `~/.gemini/config/` symlink health at any time with:

```bash
~/dotfiles-ubuntu/scripts/audit-global-config.sh
```

---

## 2. Directory & Path Conventions (Stow, Scripts & Workspaces)

The table below defines which workstation paths are managed by GNU Stow and which remain independent workspace or binary directories:

| Path | Managed by Stow? | Role & Scripts / Processes That Use It |
|------|:----------------:|----------------------------------------|
| `~/dotfiles-ubuntu/` | Source repo | Canonical source of truth. Referenced by [`bootstrap.sh`](../../bootstrap.sh), [`backup.sh`](../../backup.sh), [`audit.sh`](../../audit.sh), [`scripts/audit-global-config.sh`](../../scripts/audit-global-config.sh), and global skills (`/sopen`, `/sclose`, `/continue`, `/enrich`, `/release`) for automatic sync and `stow -t ~ -R antigravity`. |
| `~/.gemini/config/` | ✅ (Tree-unfolded) | Shared across **Antigravity 2.0 (`antigravity-agents` desktop) and Antigravity CLI (`agy`)**. Stow links `AGENTS.md`, `hooks.json`, `scripts/`, and each shared skill in `skills/<name>/` while preserving local untracked files (`config.json`, `mcp_config.json`, `plugins/`, `projects/`, `sidecars/`). |
| `~/.local/share/applications/` | ✅ (Tree-unfolded) | Desktop launchers (`antigravity-agents.desktop` and `antigravity-ide.desktop`) linked by the `antigravity` stow module and refreshed by `update-desktop-database`. |
| `~/.bashrc`, `~/.profile`, `~/.gitconfig` | ✅ | Symlinked from `bash/` and `git/` stow modules. Automatically include untracked machine-local overrides (`~/.bashrc.local` and `~/.gitconfig.local`). |
| `~/Projects/<project>/` | ❌ (Never stowed) | Standard workspace location for user repositories. **GNU Stow never creates symlinks inside `~/Projects/`**: global rules/skills in `~/.gemini/config/` apply automatically to every workspace, while project-specific rules (`<project>/.agents/`) are projected from `templates/` and committed to each project's Git repo. Lifecycle hooks (`scripts/*.py`) receive the active project path dynamically via `workspacePaths`. |
| `~/Downloads/` | ❌ | Staging directory used by [`scripts/antigravity-install.sh`](../../scripts/antigravity-install.sh). The installer automatically detects and extracts `Antigravity.zip` / `Antigravity.tar.gz` (or `Antigravity-x64.*`, recommended) and optional `Antigravity IDE.zip` / `Antigravity IDE.tar.gz` from `~/Downloads/` before installing. |
| `/opt/antigravity-agents/`, `~/.local/bin/agy` & `/opt/antigravity-ide/` | ❌ | Target installation paths populated by `scripts/antigravity-install.sh` (`antigravity-agents` + `agy` CLI recommended for daily work; `antigravity-ide` optional), verified by `bootstrap.sh`/`audit.sh`, and targeted by `.desktop` launchers. |
| `~/AppImage/` | ❌ | Monitored by `audit.sh` (`--clean` mode) to detect and optionally clean up orphaned AppImage directories. |

---

## 3. System Manifests & External Recipe Catalog (`system/`)

The `system/` directory contains plain-text manifests of installed software, consumed by [`bootstrap.sh`](../../bootstrap.sh), verified by [`audit.sh`](../../audit.sh), and updated by [`backup.sh`](../../backup.sh):

| Purpose & Tracked State | File / Directory |
|-------------------------|------------------|
| Manually installed Ubuntu 26.04 APT packages (automatically excludes external & machine-local driver packages). | [`system/packages-manual.txt`](../../system/packages-manual.txt) |
| Installed Snap applications (automatically excludes `core*`, `bare`, `gnome-*`, and `mesa-*` runtime snaps). | [`system/snaps.txt`](../../system/snaps.txt) |
| Global NPM packages under the active Node.js version. | [`system/npm-globals.txt`](../../system/npm-globals.txt) |
| Default Node.js major version managed by NVM. | [`system/nvm-default.txt`](../../system/nvm-default.txt) |
| List of external recipes from `system/external/` enabled on this machine (auto-detected by `./backup.sh`). | [`system/external.txt`](../../system/external.txt) |
| **Recipe catalog** for third-party software (Docker, Chrome, GCloud CLI, Proton, Discord, AutoFirma, Antigravity). Only recipes listed in `system/external.txt` are required by `audit.sh` or installed by `bootstrap.sh --external`. To enable a recipe on a fresh machine, add its relative path (e.g. `apt-repo/docker.sh`) to `system/external.txt` and run `./bootstrap.sh --external`. | `system/external/{apt-repo,deb-url,script}/` |
| Installed GNOME Shell extension UUIDs. | [`system/gnome-extensions.txt`](../../system/gnome-extensions.txt) |
| Declarative GNOME desktop settings (keybindings, interface, touchpad, dock, tiling) — excludes private/ephemeral state. | [`system/gnome-settings.dconf`](../../system/gnome-settings.dconf) |
| Declarative layer/node identity (`corporate`, `domain-policy`, `department`, `squad`, `service-node`, `workstation`), upstream lineage, authority policy, and federated MCP topology served by [`scripts/dotfiles_mcp_server.py`](../../scripts/dotfiles_mcp_server.py). | [`system/mcp-layer.json`](../../system/mcp-layer.json) |

---

## 4. Daily Operations & Bootstrap / Audit Modes

Routine workstation operations cover capturing package/GNOME changes, upgrading Antigravity binaries, and executing targeted `bootstrap.sh` or `audit.sh` flags.

### 4.1. Capturing System Changes & Tracking New Dotfiles

Run `./backup.sh` after package or GNOME updates, or create a new directory to track an additional dotfile module via GNU Stow:

```bash
# After installing or removing APT/Snap/NPM packages or changing GNOME settings:
cd ~/dotfiles-ubuntu
./backup.sh
git diff
git add -A && git commit -m "chore: update system manifests" && git push

# Example: track SSH config (never keys) as a new GNU Stow module:
mkdir -p ~/dotfiles-ubuntu/ssh/.ssh
cp ~/.ssh/config ~/dotfiles-ubuntu/ssh/.ssh/config
cd ~/dotfiles-ubuntu && stow -t ~ ssh
git add -A && git commit -m "feat: add ssh config module"
```

### 4.2. Installing or Upgrading Antigravity Agents (Recommended), CLI (`agy`) & Optional IDE

> **Recommended Setup**: Only **Antigravity 2.0 (`antigravity-agents`)** and **Antigravity CLI (`agy`)** are required for daily engineering and governance workflows. **Antigravity IDE (`antigravity-ide`)** remains supported as an optional legacy editor.

1. **Antigravity 2.0 (`antigravity-agents` — Recommended, Auto-Downloaded)**: `scripts/antigravity-install.sh --agents` automatically queries the official release feed (`https://antigravity.google/download`), removes any previous archive in `~/Downloads/`, downloads the latest `Antigravity.tar.gz` (`linux-x64`), and installs it to `/opt/antigravity-agents`. If offline or if automatic download fails, it falls back to any manually downloaded `~/Downloads/Antigravity{.tar.gz,.zip}` archive and instructs you to download from `https://antigravity.google/download`.
2. **Antigravity CLI (`agy` — Automatic via Official Bootstrapper)**: Installed to `~/.local/bin/agy` via `curl -fsSL https://antigravity.google/cli/install.sh | bash`. Because the official `install.sh` skips installation when `~/.local/bin/agy` already exists, `scripts/antigravity-install.sh` automatically backs up and removes `~/.local/bin/agy` before running the installer (and restores the backup if offline) whenever `--agents`, `--cli`, or `--all` is executed.
3. **Antigravity IDE (`antigravity-ide` — Optional)**: Place `~/Downloads/Antigravity IDE.zip` or `~/Downloads/Antigravity IDE.tar.gz` in `~/Downloads/` only if you also use the standalone IDE.

Then run:

```bash
cd ~/dotfiles-ubuntu
./scripts/antigravity-install.sh --agents   # (Recommended) Install/update Agents + agy CLI
./scripts/antigravity-install.sh --cli      # Install/update agy CLI only (~/.local/bin/agy)
./scripts/antigravity-install.sh --ide      # (Optional) Install/update Antigravity IDE only
./scripts/antigravity-install.sh --all      # Install/update Agents, agy CLI, and optional IDE
./scripts/antigravity-install.sh            # Interactive prompt
```

The installer extracts the archives from `~/Downloads/`, backs up the previous installation (`/opt/antigravity-*.backup`), installs the new release into `/opt/antigravity-agents` (and optionally `/opt/antigravity-ide`), sets Electron sandbox permissions (`chrome-sandbox 4755`), and refreshes `~/.local/bin/agy`.

> **Note (`bootstrap.sh --all` vs `scripts/antigravity-install.sh --agents`)**:
> `./bootstrap.sh --all` (or `--external`) checks whether `/opt/antigravity-agents/antigravity` already exists and **skips** it if installed (idempotent initial provisioning). To **upgrade** an existing installation and refresh `agy` CLI after downloading a new release, run `./scripts/antigravity-install.sh --agents`.

### 4.3. Bootstrap Modes (`./bootstrap.sh`) & Audit Modes (`./audit.sh`)

Each flag below scopes `bootstrap.sh` or `audit.sh` to a specific workstation subsystem:

| Script & Flag | Action |
|---------------|--------|
| `./bootstrap.sh` *(no flag)* | Interactive — asks confirmation before each provisioning step. |
| `./bootstrap.sh --workstation` | Configures `~/dotfiles-ubuntu` as a declarative read-only workstation runtime appliance (`~/.config/dotfiles-ubuntu/workstation.conf`), enables once-per-boot auto-sync, and exposes `dotfiles-sync`. |
| `./bootstrap.sh --antigravity` | Only Antigravity global rules, skills, and lifecycle hooks (`~/.gemini/config/`) + desktop launchers. |
| `./bootstrap.sh --all` | Unattended — installs all packages, external recipes, NVM, GNOME settings, and Stow symlinks. |
| `./bootstrap.sh --packages` | Only APT + Snaps + NPM globals from `system/*.txt`. |
| `./bootstrap.sh --stow` | Only dotfile symlinks (`bash` + `git` + `antigravity`). |
| `./bootstrap.sh --nvm` | Only NVM + default Node.js version. |
| `./bootstrap.sh --gnome` | Only GNOME extensions list + `dconf` desktop settings. |
| `./bootstrap.sh --external` | Only external packages enabled in `system/external.txt` (APT `.sources` repos, `.deb` downloads, custom scripts). |
| `./audit.sh` *(no flag)* | Read-only bidirectional drift check across Stow symlinks, APT/Snap/NPM/GNOME, external recipes, residual files, and Git status. |
| `./audit.sh --clean` | Interactive cleanup — offers to remove residual bootstrap backups (`*.backup.*`) and orphaned directories. |

To suppress drift warnings for hardware-specific packages on a specific workstation, create `.audit-ignore` (gitignored):

```bash
# .audit-ignore — packages specific to THIS machine (GPU drivers, firmware, etc.)
nvidia-driver-595-open
```

---

## 5. Multi-Machine Provisioning, Migration & Portability Matrix

Provision a fresh Ubuntu 26.04 machine, configure a private workstation appliance, or migrate existing dotfiles without losing local state.

### 5.1. Setting Up a New Computer

Clone the repository, run `bootstrap.sh`, and install the Antigravity binaries in three steps:

```bash
# 1. Clone your fork (or the upstream repo) and run bootstrap
git clone https://github.com/<your-user>/dotfiles-ubuntu.git ~/dotfiles-ubuntu
cd ~/dotfiles-ubuntu
chmod +x bootstrap.sh backup.sh audit.sh scripts/*.sh
./bootstrap.sh              # interactive — or ./bootstrap.sh --all

# 2. Install Antigravity Agents + agy CLI (after downloading Antigravity archive to ~/Downloads/)
./scripts/antigravity-install.sh --agents

# 3. Clone project repositories, sign in to Antigravity Agents, and run /sopen
git clone https://github.com/<your-user>/<your-project>.git ~/Projects/<your-project>
```

#### 5.1.1. Workstation Runtime Appliance Mode, Private Forks & Boot Auto-Sync (`workstation-sync.sh` / `dotfiles-sync`)

Whether `~/dotfiles-ubuntu` (or your personal private workstation fork `~/<your-pc-repo>`) is used as the machine's global runtime appliance while developing engine changes in an independent private clone `~/Projects/dev-<repo>`, each repository points strictly to its own `origin` (with the public Open-Source `dotfiles-ubuntu` as `upstream`):

```bash
# In your personal workstation clone (~/dotfiles-ubuntu or ~/<your-pc-repo>):
./bootstrap.sh --workstation
# Or configure private workstation mode explicitly:
./scripts/workstation-sync.sh --setup --mode private --profile human-base --auto-sync boot
```

This creates `~/.config/dotfiles-ubuntu/workstation.conf` (untracked per-device state) and activates five capabilities:
1. **Sovereign Private Workstation, Multi-Machine / Hat Branches, Personal Child Tutor Layers & Cross-Project Consultation (`mode=private` / `mode=readonly`)**: In `mode=private`, your `$HOME` repository (`~/<your-pc-repo>` or `~/dotfiles-ubuntu`, `visibility_scope: "private:individual:root-0"`, `precedence: 90`, `mcp_operating_mode: "personal-root-hub"`) keeps `origin` unlocked so you commit and push personal packages (`system/*.txt`) and personal trackers (`WORKTASK.md`, `WORKROAD.md`, `BACKLOG.md`) to your private remote while locking `upstream` (`remote.upstream.pushurl = VALIDATION_BLOCKED_READONLY_RUNTIME`). Unlike a company `Root 0` (`10`) that relates upward to public administration (`1..4`), an individual `Root 0` operates in **top-down personal enrichment mode**: it pulls Open-Source `templates/` downward from `upstream` (`dotfiles-ubuntu`), maintains parallel branches for distinct machines (`machine/<hostname>`) or contexts (`master` on `"global_profile": "human-base"` vs. `hat/<specialty>`), and can govern its own **personal child sub-layers** (`private:individual:department` / `private:individual:unit`, such as an **Academic University Tutor**, **Career Coach**, or **Research Lab** bootstrapped with `--parent-dir ~/<your-pc-repo>`) via `internal-1hop-hierarchical` (see [Cross-Departmental & Human-Stack Matrix (`§2.4` & `§3`)](../reference/cross_departmental_and_human_stack_matrix.md)). Any local workspace can also query your personal hub via `make consult LAYER=workstation QUERY="..."`. When cloned at `~/<your-pc-repo>`, `bootstrap.sh` and `workstation-sync.sh` automatically maintain a compatibility symlink `~/dotfiles-ubuntu -> ~/<your-pc-repo>` and resolve `DOTFILES_RUNTIME_DIR` dynamically in `bash/.bashrc` and `audit.sh`.
2. **Unified Automatic Workstation Sync (`dotfiles-sync` or `make workstation-sync`)**:
   - A single command (`dotfiles-sync` or `make workstation-sync`, also run automatically once per boot) executes the full synchronization cascade automatically without extra flags:
     1. **Private `origin` Sync**: Pulls fast-forward updates from your workstation repository's own `origin` (`~/<your-pc-repo>.git`).
     2. **Open-Source `upstream` Git Merge**: Fetches `upstream` (`dotfiles-ubuntu`) and merges any new official Open-Source releases while preserving your personal `system/mcp-layer.json` identity (`layer_id`, `precedence: 90`, `entity_kind: "individual"`).
     3. **Clean Committed `dev` Detection**: If a related local development clone (`~/Projects/dev-<repo>`) exists on the machine and its working tree is clean (`git status` clean, meaning changes are committed and verified, never half-edited work in progress), it automatically syncs the tracker-free engine into `~/<your-pc-repo>` (omitting `WORKTASK.md`, `WORKROAD.md`, `BACKLOG.md`, `WORKVALI.md`, `roadmaps/`, `.agents/`, `corporate/`, and `layers/` and preserving `system/mcp-layer.json`) and records the sync commit automatically.
     4. **Profile & GNU Stow**: Re-applies `DOTFILES_GLOBAL_PROFILE` and runs `stow -t ~ -R bash git antigravity`.
3. **Once-Per-Boot Terminal Auto-Sync**: On the first interactive terminal opened after booting Ubuntu, `bash/.bashrc` checks `${XDG_RUNTIME_DIR:-/tmp}/dotfiles-ubuntu-${UID}.synced` (stored in RAM `tmpfs`, cleared on reboot) and runs `workstation-sync.sh --auto` with a 4-second network timeout so offline boots never hang.
4. **Self-Cleaning Contributor Clone (`make setup-dev` / `make reset-dev`)**: Inside `~/Projects/dev-<repo>` (`visibility_scope: "private:open-source:dev"`), `WORKTASK.md`, `WORKROAD.md`, and `BACKLOG.md` are tracked in your private `origin` (`dev-<repo>.git`). Running `make setup-dev` (or `make reset-dev`) purges any temporary `.agents/` or `WORKVALI.md` fork-test residue while preserving your private `WORKTASK.md`, `WORKROAD.md`, `BACKLOG.md`, and `roadmaps/`.
5. **Tracker-Free Open-Source Release Publication (`make publish-oss`)**: Running `make publish-oss` (or `./scripts/workstation-sync.sh --publish-oss [--dry-run]`) verifies the repository and exports a clean, tracker-free snapshot (excluding `WORKTASK.md`, `WORKROAD.md`, `ROADMAP.md`, `BACKLOG.md`, `WORKVALI.md`, `roadmaps/`, `.agents/`, `corporate/`, and `layers/`) to `upstream` (`dotfiles-ubuntu`).

### 5.2. Migrating an Existing Computer & Rescuing Unique Config

If the target computer already has `.bashrc`, `.gitconfig`, or `~/.gemini/config/AGENTS.md`:

```bash
# 1. Inspect existing files before running bootstrap
ls -la ~/.bashrc ~/.gitconfig ~/.gemini/config/AGENTS.md ~/.gemini/config/skills 2>/dev/null

# 2. Run bootstrap --stow (automatically renames conflicting real files to *.backup.YYYYMMDD)
cd ~/dotfiles-ubuntu && ./bootstrap.sh --stow

# 3. Compare backups against the shared config and merge any unique rules worth keeping
diff ~/.bashrc.backup.* ~/dotfiles-ubuntu/bash/.bashrc
diff ~/.gemini/config/AGENTS.md.backup.* ~/dotfiles-ubuntu/antigravity/.gemini/config/AGENTS.md
```

**What stays untouched by `bootstrap.sh`**:
- `~/.gemini/config/config.json` (IDE preferences), `~/.gemini/config/mcp_config.json` (MCP server config), `~/.gemini/config/plugins/`, `~/.gemini/config/projects/`, `~/.gemini/config/sidecars/`.
- `~/.gemini/antigravity/brain/` (per-machine conversation history) and `~/.gemini/*.json` (OAuth credentials).

### 5.3. Cross-Machine Portability Matrix

The portability matrix below summarizes which workstation artifacts travel via Git/Stow and which remain machine-local:

| Data | Portable? | Mechanism | Recovery on New Machine |
|------|:---------:|-----------|-------------------------|
| System config (`bash`, `git`) | ✅ | `dotfiles-ubuntu` stow modules | `./bootstrap.sh --stow` |
| Global agent config (rules, hooks, skills) | ✅ | `dotfiles-ubuntu/antigravity/` stow module | `./bootstrap.sh --antigravity` or `--stow` |
| System packages (APT, Snaps, NPM) | ✅ | `dotfiles-ubuntu/system/` manifests | `./bootstrap.sh --packages` |
| GNOME settings & extensions | ✅ | `dotfiles-ubuntu/system/gnome-*` | `./bootstrap.sh --gnome` |
| Polymorphic templates (`templates/`) | ✅ | `dotfiles-ubuntu/templates/` | `git clone` |
| Project rules & session state (`.agents/`, `SESSION.md`, `WORKTASK.md`) | ✅ | Project Git repository | `git clone` + `/sopen` (Tier 2 & Tier 3 recovery) |
| Antigravity binaries (`Agents`, `agy` CLI, optional `IDE`) | 🔧 | [`scripts/antigravity-install.sh`](../../scripts/antigravity-install.sh) | `./scripts/antigravity-install.sh --agents` (or `--cli`) |
| Conversation scratchpads (`brain/`) | ❌ | Local `~/.gemini/antigravity/brain/` | Auto-healed by `/sopen` from `SESSION.md` + `git log` |
| Auth credentials & CLI history | ❌ | Local `~/.gemini/*.json`, `~/.gemini/history/` | Re-authenticate in IDE |

---

## 6. Uninstallation & Local Secret Isolation

GNU Stow symlinks can be cleanly removed at any time, and personal credentials remain strictly isolated in untracked `.local` files.

### 6.1. Uninstalling Stow Symlinks

Deactivate the stowed symlink modules with `stow -t ~ -D` before optionally deleting the clone:

```bash
# Remove stow symlinks (keeps ~/dotfiles-ubuntu intact):
cd ~/dotfiles-ubuntu && stow -t ~ -D bash git antigravity

# Remove symlinks and delete the repository:
cd ~/dotfiles-ubuntu && stow -t ~ -D bash git antigravity && cd ~ && rm -rf ~/dotfiles-ubuntu
```

### 6.2. Security & Machine-Local Overrides

**Never commit secrets or personal identity.**
- **Git identity**: [`git/.gitconfig`](../../git/.gitconfig) includes `~/.gitconfig.local` (`[include] path = ~/.gitconfig.local`). Your `user.name` and `user.email` live in `~/.gitconfig.local` (automatically preserved by `bootstrap.sh`).
- **Shell overrides**: [`bash/.bashrc`](../../bash/.bashrc) sources `~/.bashrc.local` if present for machine- or project-specific environment variables.
- **Ignored patterns**: [`.gitignore`](../../.gitignore) excludes SSH keys (`~/.ssh/id_*`), GPG keys (`~/.gnupg/`), credentials (`~/.netrc`), backup files (`*.backup.*`), and local overrides (`.bashrc.local`, `.gitconfig.local`, `.audit-ignore`). See **[`SECURITY.md`](../../SECURITY.md)** for full details.
