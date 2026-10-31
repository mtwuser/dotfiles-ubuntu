# Ubuntu 26.04 System Management, GNU Stow & Multi-Machine Operations Guide

> **Human Operator Manual (Tier 2 Progressive Disclosure)**
>
> Complete operational guide for managing Ubuntu 26.04 LTS packages, GNU Stow dotfile symlinks, Antigravity binary upgrades, multi-machine provisioning/migration, drift audits, and uninstallation. For internal engine specifications, see **[`docs/architecture/01_system_and_stow_engine.md`](../architecture/01_system_and_stow_engine.md)**; for the executive overview, return to **[`README.md`](../../README.md)**.

---

## 1. How GNU Stow & Tree Unfolding Work

### 1.1 Stow Modules (`bash/`, `git/`, `antigravity/`)

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

### 1.2 Why `~/.gemini/config/` Uses Stow Tree Unfolding (Individual Symlinks)

Unlike `~/.bashrc` (a single file symlink), `~/.gemini/config/` and `~/.gemini/config/skills/` are **real directories** that mix tracked dotfiles with machine-local runtime files:
- **Tracked via Stow (`~/dotfiles-ubuntu/antigravity/`)**: `AGENTS.md`, `hooks.json`, `scripts/`, and the 12 core skills inside `skills/<name>/`.
- **Machine-local (untracked)**: `config.json`, `mcp_config.json`, `plugins/`, `projects/`, `sidecars/`, `.ruff_cache/`, and locally installed extension/cloud skills inside `skills/`.

Because `~/.gemini/config/` and `~/.gemini/config/skills/` already exist as real directories, GNU Stow automatically performs **tree unfolding**: it creates individual symlinks for each tracked item (`AGENTS.md`, `hooks.json`, `scripts/`, and each shared skill folder `skills/<name>`) without touching local credentials, MCP servers, or third-party skills.

Verify `~/.gemini/config/` symlink health at any time with:

```bash
~/dotfiles-ubuntu/scripts/audit-global-config.sh
```

---

## 2. Directory & Path Conventions (Stow, Scripts & Workspaces)

| Path | Managed by Stow? | Role & Scripts / Processes That Use It |
|------|:----------------:|----------------------------------------|
| `~/dotfiles-ubuntu/` | Source repo | Canonical source of truth. Referenced by [`bootstrap.sh`](../../bootstrap.sh), [`backup.sh`](../../backup.sh), [`audit.sh`](../../audit.sh), [`scripts/audit-global-config.sh`](../../scripts/audit-global-config.sh), and global skills (`/sopen`, `/sclose`, `/continue`, `/enrich`, `/release`) for automatic sync and `stow -t ~ -R antigravity`. |
| `~/.gemini/config/` | ✅ (Tree-unfolded) | Shared across **all 3 Antigravity surfaces** (Desktop Agents, IDE, CLI). Stow links `AGENTS.md`, `hooks.json`, `scripts/`, and each shared skill in `skills/<name>/` while preserving local untracked files (`config.json`, `mcp_config.json`, `plugins/`, `projects/`, `sidecars/`). |
| `~/.local/share/applications/` | ✅ (Tree-unfolded) | Desktop launchers (`antigravity-agents.desktop` and `antigravity-ide.desktop`) linked by the `antigravity` stow module and refreshed by `update-desktop-database`. |
| `~/.bashrc`, `~/.profile`, `~/.gitconfig` | ✅ | Symlinked from `bash/` and `git/` stow modules. Automatically include untracked machine-local overrides (`~/.bashrc.local` and `~/.gitconfig.local`). |
| `~/Projects/<project>/` | ❌ (Never stowed) | Standard workspace location for user repositories. **GNU Stow never creates symlinks inside `~/Projects/`**: global rules/skills in `~/.gemini/config/` apply automatically to every workspace, while project-specific rules (`<project>/.agents/`) are projected from `templates/` and committed to each project's Git repo. Lifecycle hooks (`scripts/*.py`) receive the active project path dynamically via `workspacePaths`. |
| `~/Downloads/` | ❌ | Staging directory used by [`scripts/antigravity-install.sh`](../../scripts/antigravity-install.sh). The installer automatically detects and extracts `Antigravity.zip` / `Antigravity.tar.gz` (or `Antigravity-x64.*`) and `Antigravity IDE.zip` / `Antigravity IDE.tar.gz` from `~/Downloads/` before installing. |
| `/opt/antigravity-agents/` & `/opt/antigravity-ide/` | ❌ | Target installation directories populated by `scripts/antigravity-install.sh`, verified by `bootstrap.sh`/`audit.sh` (`system/external/script/antigravity-*.sh`), and targeted by `.desktop` launchers. |
| `~/AppImage/` | ❌ | Monitored by `audit.sh` (`--clean` mode) to detect and optionally clean up orphaned AppImage directories. |

---

## 3. System Manifests & External Recipe Catalog (`system/`)

The `system/` directory contains plain-text manifests of installed software, consumed by [`bootstrap.sh`](../../bootstrap.sh), verified by [`audit.sh`](../../audit.sh), and updated by [`backup.sh`](../../backup.sh):

| File / Directory | Purpose |
|------------------|---------|
| [`system/packages-manual.txt`](../../system/packages-manual.txt) | Manually installed Ubuntu 26.04 APT packages (automatically excludes external & machine-local driver packages). |
| [`system/snaps.txt`](../../system/snaps.txt) | Installed Snap applications (automatically excludes `core*`, `bare`, `gnome-*`, and `mesa-*` runtime snaps). |
| [`system/npm-globals.txt`](../../system/npm-globals.txt) | Global NPM packages under the active Node.js version. |
| [`system/nvm-default.txt`](../../system/nvm-default.txt) | Default Node.js major version managed by NVM. |
| [`system/external.txt`](../../system/external.txt) | List of external recipes from `system/external/` enabled on this machine (auto-detected by `./backup.sh`). |
| `system/external/{apt-repo,deb-url,script}/` | **Recipe catalog** for third-party software (Docker, Chrome, GCloud CLI, Proton, Discord, AutoFirma, Antigravity). Only recipes listed in `system/external.txt` are required by `audit.sh` or installed by `bootstrap.sh --external`. To enable a recipe on a fresh machine, add its relative path (e.g. `apt-repo/docker.sh`) to `system/external.txt` and run `./bootstrap.sh --external`. |
| [`system/gnome-extensions.txt`](../../system/gnome-extensions.txt) | Installed GNOME Shell extension UUIDs. |
| [`system/gnome-settings.dconf`](../../system/gnome-settings.dconf) | Declarative GNOME desktop settings (keybindings, interface, touchpad, dock, tiling) — excludes private/ephemeral state. |
| [`system/mcp-layer.json`](../../system/mcp-layer.json) | Declarative layer/node identity (`corporate`, `domain-policy`, `department`, `team`, `service-node`, `workstation`), upstream lineage, authority policy, and federated MCP topology served by [`scripts/dotfiles_mcp_server.py`](../../scripts/dotfiles_mcp_server.py). |

---

## 4. Daily Operations & Bootstrap / Audit Modes

### 4.1 Capturing System Changes & Tracking New Dotfiles

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

### 4.2 Installing or Upgrading Antigravity IDE & Agents

Download the latest release archives (`.zip` or `.tar.gz`) directly into `~/Downloads/`:
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

The installer extracts the archives from `~/Downloads/`, backs up the previous installation (`/opt/antigravity-*.backup`), installs the new release into `/opt/antigravity-agents` and `/opt/antigravity-ide`, and sets Electron sandbox permissions (`chrome-sandbox 4755`).

> **Note (`bootstrap.sh --all` vs `scripts/antigravity-install.sh --all`)**:
> `./bootstrap.sh --all` (or `--external`) checks whether `/opt/antigravity-agents/antigravity` and `/opt/antigravity-ide/antigravity-ide` already exist and **skips** them if installed (idempotent initial provisioning). To **upgrade** an existing installation after downloading a new release, always run `./scripts/antigravity-install.sh --all`.

### 4.3 Bootstrap Modes (`./bootstrap.sh`) & Audit Modes (`./audit.sh`)

| Script & Flag | Action |
|---------------|--------|
| `./bootstrap.sh` *(no flag)* | Interactive — asks confirmation before each provisioning step. |
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

### 5.1 Setting Up a New Computer

```bash
# 1. Clone your fork (or the upstream repo) and run bootstrap
git clone https://github.com/<your-user>/dotfiles-ubuntu.git ~/dotfiles-ubuntu
cd ~/dotfiles-ubuntu
chmod +x bootstrap.sh backup.sh audit.sh scripts/*.sh
./bootstrap.sh              # interactive — or ./bootstrap.sh --all

# 2. Install Antigravity IDE & Agents (after downloading archives to ~/Downloads/)
./scripts/antigravity-install.sh --all

# 3. Clone project repositories, sign in to Antigravity IDE, and run /sopen
git clone https://github.com/<your-user>/<your-project>.git ~/Projects/<your-project>
```

### 5.2 Migrating an Existing Computer & Rescuing Unique Config

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

### 5.3 Cross-Machine Portability Matrix

| Data | Portable? | Mechanism | Recovery on New Machine |
|------|:---------:|-----------|-------------------------|
| System config (`bash`, `git`) | ✅ | `dotfiles-ubuntu` stow modules | `./bootstrap.sh --stow` |
| Global agent config (rules, hooks, skills) | ✅ | `dotfiles-ubuntu/antigravity/` stow module | `./bootstrap.sh --antigravity` or `--stow` |
| System packages (APT, Snaps, NPM) | ✅ | `dotfiles-ubuntu/system/` manifests | `./bootstrap.sh --packages` |
| GNOME settings & extensions | ✅ | `dotfiles-ubuntu/system/gnome-*` | `./bootstrap.sh --gnome` |
| Polymorphic templates (`templates/`) | ✅ | `dotfiles-ubuntu/templates/` | `git clone` |
| Project rules & session state (`.agents/`, `SESSION.md`, `WORKTASK.md`) | ✅ | Project Git repository | `git clone` + `/sopen` (Tier 2 & Tier 3 recovery) |
| Antigravity binaries (`IDE`, `Agents`) | 🔧 | [`scripts/antigravity-install.sh`](../../scripts/antigravity-install.sh) | Download archives + run installer |
| Conversation scratchpads (`brain/`) | ❌ | Local `~/.gemini/antigravity/brain/` | Auto-healed by `/sopen` from `SESSION.md` + `git log` |
| Auth credentials & CLI history | ❌ | Local `~/.gemini/*.json`, `~/.gemini/history/` | Re-authenticate in IDE |

---

## 6. Uninstallation & Local Secret Isolation

### 6.1 Uninstalling Stow Symlinks

```bash
# Remove stow symlinks (keeps ~/dotfiles-ubuntu intact):
cd ~/dotfiles-ubuntu && stow -t ~ -D bash git antigravity

# Remove symlinks and delete the repository:
cd ~/dotfiles-ubuntu && stow -t ~ -D bash git antigravity && cd ~ && rm -rf ~/dotfiles-ubuntu
```

### 6.2 Security & Machine-Local Overrides

**Never commit secrets or personal identity.**
- **Git identity**: [`git/.gitconfig`](../../git/.gitconfig) includes `~/.gitconfig.local` (`[include] path = ~/.gitconfig.local`). Your `user.name` and `user.email` live in `~/.gitconfig.local` (automatically preserved by `bootstrap.sh`).
- **Shell overrides**: [`bash/.bashrc`](../../bash/.bashrc) sources `~/.bashrc.local` if present for machine- or project-specific environment variables.
- **Ignored patterns**: [`.gitignore`](../../.gitignore) excludes SSH keys (`~/.ssh/id_*`), GPG keys (`~/.gnupg/`), credentials (`~/.netrc`), backup files (`*.backup.*`), and local overrides (`.bashrc.local`, `.gitconfig.local`, `.audit-ignore`). See **[`SECURITY.md`](../../SECURITY.md)** for full details.
