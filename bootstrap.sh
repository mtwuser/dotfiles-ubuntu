#!/usr/bin/env bash
# Restores system configuration from dotfiles repo
# Usage: ./bootstrap.sh [--all | --antigravity | --packages | --stow | --nvm | --gnome | --external]
# Without arguments, runs interactive mode (asks before each step)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SYSTEM_DIR="$SCRIPT_DIR/system"
VERSION_STR="$(tr -d '[:space:]' < "$SCRIPT_DIR/VERSION" 2>/dev/null || echo "unknown")"
MODE="${1:-interactive}"

usage() {
  cat <<EOF
Usage: ./bootstrap.sh [--all | --antigravity | --packages | --stow | --nvm | --gnome | --external | --version | --help]

Modes:
  (no flag)      Interactive mode — asks before each step
  --antigravity  Install only Antigravity global rules, skills, and hooks (~/.gemini/config/)
  --all          Install everything without prompting
  --packages     APT + Snaps + NPM globals
  --stow         All dotfile symlinks (bash + git + antigravity)
  --nvm          NVM + Node.js
  --gnome        GNOME extensions list + dconf settings
  --external     External packages (APT repos, .deb downloads, custom scripts)
  -v, --version  Show version information
  -h, --help     Show this help message
EOF
}

case "$MODE" in
  interactive|--all|--antigravity|--packages|--stow|--nvm|--gnome|--external) ;;
  -v|--version)
    echo "dotfiles-ubuntu v$VERSION_STR"
    exit 0
    ;;
  -h|--help)
    usage
    exit 0
    ;;
  *)
    echo "❌ Unknown option: $MODE" >&2
    usage >&2
    exit 1
    ;;
esac

prepare_antigravity_dirs() {
  mkdir -p "$HOME/.gemini/config/skills" "$HOME/.local/share/applications"
  for d in "$HOME/.gemini/config/scripts" "$HOME/.gemini/config/skills"/*; do
    [ -e "$d" ] || continue
    if [ -d "$d" ] && [ ! -L "$d" ] && [ -d "$SCRIPT_DIR/antigravity/${d#"$HOME"/}" ]; then
      echo "  backup dir: ~/${d#"$HOME"/} → ~/${d#"$HOME"/}.backup.$(date +%Y%m%d)"
      mv "$d" "${d}.backup.$(date +%Y%m%d)"
    fi
  done
}

confirm() {
  if [ "$MODE" = "--all" ]; then return 0; fi
  read -rp "$1 (y/N): " answer
  [ "$answer" = "y" ] || [ "$answer" = "Y" ]
}

# --- Step 0: Antigravity-only shortcut ---
if [ "$MODE" = "--antigravity" ]; then
  echo "=== Installing Antigravity Global Configuration ==="
  if ! command -v stow &>/dev/null; then
    sudo apt update && sudo apt install -y stow
  fi
  cd "$SCRIPT_DIR"
  prepare_antigravity_dirs
  while IFS= read -r f; do
    [ -z "$f" ] && continue
    if [ -f "$HOME/$f" ] && [ ! -L "$HOME/$f" ]; then
      echo "  backup: ~/$f → ~/${f}.backup.$(date +%Y%m%d)"
      mv "$HOME/$f" "$HOME/${f}.backup.$(date +%Y%m%d)"
    fi
  done < <(find antigravity -type f -printf '%P\n')
  stow -t "$HOME" antigravity
  echo "✅ Antigravity rules, skills, and hooks linked to ~/.gemini/config/"
  exit 0
fi

# --- Step 1: APT packages ---
if [ "$MODE" = "--all" ] || [ "$MODE" = "--packages" ] || [ "$MODE" = "interactive" ]; then
  if [ -f "$SYSTEM_DIR/packages-manual.txt" ] && confirm "Install APT packages?"; then
    echo "=== Step 1: APT packages ==="
    if grep -q ':i386$' "$SYSTEM_DIR/packages-manual.txt" && ! dpkg --print-foreign-architectures | grep -qx 'i386'; then
      echo "  → Enabling i386 multiarch support..."
      sudo dpkg --add-architecture i386
    fi
    sudo apt update
    AVAILABLE_PKGS="$(grep -h '^Package: ' /var/lib/apt/lists/*Packages 2>/dev/null | awk '{print $2}' | sort -u || apt-cache pkgnames 2>/dev/null | sort -u)"
    mapfile -t INSTALL_LIST < <(
      awk 'NR==FNR {ok[$1]=1; next} NF {base=$1; sub(/:.*/, "", base); if (ok[base]) print $1; else print "SKIP:" $1 > "/dev/stderr"}' \
        <(echo "$AVAILABLE_PKGS") "$SYSTEM_DIR/packages-manual.txt" 2> >(sed 's/^SKIP:/  ⚠️  Skip (not in APT): /' >&2)
    )
    if [ "${#INSTALL_LIST[@]}" -gt 0 ]; then
      sudo apt install -y "${INSTALL_LIST[@]}"
    fi
  fi
fi

# --- Step 2: Snaps ---
if [ "$MODE" = "--all" ] || [ "$MODE" = "--packages" ] || [ "$MODE" = "interactive" ]; then
  if [ -f "$SYSTEM_DIR/snaps.txt" ] && confirm "Install Snap packages?"; then
    echo "=== Step 2: Snaps ==="
    while read -r snap; do
      [ -z "$snap" ] && continue
      sudo snap install "$snap" 2>/dev/null || \
      sudo snap install "$snap" --classic 2>/dev/null || \
      echo "⚠️  Skip: $snap (may require manual install)"
    done < "$SYSTEM_DIR/snaps.txt"
  fi
fi

# --- Step 3: GNU Stow ---
if [ "$MODE" = "--all" ] || [ "$MODE" = "--stow" ] || [ "$MODE" = "interactive" ]; then
  if confirm "Install dotfiles via GNU Stow?"; then
    echo "=== Step 3: GNU Stow ==="
    if ! command -v stow &>/dev/null; then
      sudo apt install -y stow
    fi
    cd "$SCRIPT_DIR"
    # Stow each module directory (skip system/, scripts, and non-module files)
    for module in */; do
      module="${module%/}"
      [ "$module" = "system" ] && continue
      [ "$module" = "scripts" ] && continue
      [ "$module" = "templates" ] && continue
      [ "$module" = "docs" ] && continue
      [ "$module" = "layers" ] && continue
      [ "$module" = "logs" ] && continue
      [ "$module" = "tests" ] && continue
      [ "$module" = "venv" ] && continue
      [ "$module" = ".venv" ] && continue
      [ "$module" = "htmlcov" ] && continue
      echo "  → stow $module"
      if [ "$module" = "antigravity" ]; then
        prepare_antigravity_dirs
      fi
      # Preserve existing git user identity into ~/.gitconfig.local before stowing git/
      if [ "$module" = "git" ] && [ ! -f "$HOME/.gitconfig.local" ] && [ -f "$HOME/.gitconfig" ] && [ ! -L "$HOME/.gitconfig" ]; then
        existing_name="$(git config --file "$HOME/.gitconfig" user.name 2>/dev/null || true)"
        existing_email="$(git config --file "$HOME/.gitconfig" user.email 2>/dev/null || true)"
        if [ -n "$existing_name" ] || [ -n "$existing_email" ]; then
          printf "[user]\n\tname = %s\n\temail = %s\n" "$existing_name" "$existing_email" > "$HOME/.gitconfig.local"
          echo "    preserved git identity in ~/.gitconfig.local"
        fi
      fi
      # If real files exist at target, back them up first
      while IFS= read -r f; do
        [ -z "$f" ] && continue
        if [ -f "$HOME/$f" ] && [ ! -L "$HOME/$f" ]; then
          echo "    backup: ~/$f → ~/${f}.backup.$(date +%Y%m%d)"
          mv "$HOME/$f" "$HOME/${f}.backup.$(date +%Y%m%d)"
        fi
      done < <(find "$module" -type f -printf '%P\n')
      stow -t "$HOME" "$module"
    done
  fi
fi

# --- Step 4: NVM + Node ---
if [ "$MODE" = "--all" ] || [ "$MODE" = "--nvm" ] || [ "$MODE" = "interactive" ]; then
  if [ -f "$SYSTEM_DIR/nvm-default.txt" ] && confirm "Install NVM and Node.js?"; then
    echo "=== Step 4: NVM + Node ==="
    NODE_VERSION="$(cat "$SYSTEM_DIR/nvm-default.txt")"
    if [ ! -d "$HOME/.nvm" ]; then
      echo "  → Installing NVM..."
      curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.0/install.sh | bash
    fi
    export NVM_DIR="$HOME/.nvm"
    # shellcheck source=/dev/null
    [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
    if [ -z "$NODE_VERSION" ] || [ "$NODE_VERSION" = "none" ]; then
      echo "  → Installing latest LTS Node.js..."
      nvm install --lts
      nvm alias default 'lts/*'
    else
      echo "  → Installing Node $NODE_VERSION..."
      nvm install "$NODE_VERSION"
      nvm alias default "$NODE_VERSION"
    fi
  fi
fi

# --- Step 5: NPM globals ---
if [ "$MODE" = "--all" ] || [ "$MODE" = "--packages" ] || [ "$MODE" = "interactive" ]; then
  if [ -f "$SYSTEM_DIR/npm-globals.txt" ] && confirm "Install NPM global packages?"; then
    echo "=== Step 5: NPM globals ==="
    # Ensure correct Node version is active
    export NVM_DIR="$HOME/.nvm"
    # shellcheck source=/dev/null
    [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
    if [ -f "$SYSTEM_DIR/nvm-default.txt" ]; then
      nvm use "$(cat "$SYSTEM_DIR/nvm-default.txt")" 2>/dev/null || true
    fi
    if ! command -v npm &>/dev/null; then
      echo "  ⚠️  npm not found (run './bootstrap.sh --nvm' first)"
    else
      while read -r pkg; do
        [ -z "$pkg" ] && continue
        echo "  → npm install -g $pkg"
        npm install -g "$pkg" 2>/dev/null || echo "⚠️  Skip: $pkg"
      done < "$SYSTEM_DIR/npm-globals.txt"
    fi
  fi
fi

# --- Step 6: GNOME extensions ---
if [ "$MODE" = "--all" ] || [ "$MODE" = "--gnome" ] || [ "$MODE" = "interactive" ]; then
  if [ -f "$SYSTEM_DIR/gnome-extensions.txt" ] && confirm "Show GNOME extensions to install?"; then
    echo "=== Step 6: GNOME extensions ==="
    echo "⚠️  Install manually from https://extensions.gnome.org/:"
    while read -r ext; do
      echo "  • $ext"
    done < "$SYSTEM_DIR/gnome-extensions.txt"
  fi
fi

# --- Step 7: GNOME settings ---
if [ "$MODE" = "--all" ] || [ "$MODE" = "--gnome" ] || [ "$MODE" = "interactive" ]; then
  if [ -f "$SYSTEM_DIR/gnome-settings.dconf" ] && confirm "Restore GNOME settings (dconf)?"; then
    echo "=== Step 7: GNOME settings ==="
    dconf load / < "$SYSTEM_DIR/gnome-settings.dconf"
    echo "  ✅ GNOME settings restored"
  fi
fi

# --- Step 8: External packages ---
if [ "$MODE" = "--all" ] || [ "$MODE" = "--external" ] || [ "$MODE" = "interactive" ]; then
  EXT_DIR="$SYSTEM_DIR/external"
  if [ -d "$EXT_DIR" ] && confirm "Install external packages?"; then
    echo "=== Step 8: External packages ==="

    is_external_enabled() {
      local rel_ext="${1#"$EXT_DIR"/}"
      if [ ! -f "$SYSTEM_DIR/external.txt" ]; then
        return 0
      fi
      grep -qxF "$rel_ext" "$SYSTEM_DIR/external.txt" 2>/dev/null
    }

    # 8a. APT repo packages — set up repos first, then install
    if [ -d "$EXT_DIR/apt-repo" ]; then
      NEED_UPDATE=false
      for pkg_file in "$EXT_DIR/apt-repo"/*.sh; do
        [ -f "$pkg_file" ] || continue
        is_external_enabled "$pkg_file" || continue
        # Reset variables before sourcing
        NAME="" DESCRIPTION="" PACKAGES="" CHECK=""
        setup_repo() { :; }
        # shellcheck source=/dev/null
        source "$pkg_file"

        if dpkg -s "$CHECK" &>/dev/null && apt-cache policy "$CHECK" 2>/dev/null | grep -q 'http'; then
          echo "  ✅ $NAME (already installed & repo active)"
        else
          echo "  → Setting up repo: $NAME"
          setup_repo
          NEED_UPDATE=true
        fi
      done

      # Single apt update after all repos are set up
      if [ "$NEED_UPDATE" = true ]; then
        sudo apt update -qq
      fi

      # Install packages from newly added repos
      for pkg_file in "$EXT_DIR/apt-repo"/*.sh; do
        [ -f "$pkg_file" ] || continue
        is_external_enabled "$pkg_file" || continue
        NAME="" PACKAGES="" CHECK=""
        setup_repo() { :; }
        # shellcheck source=/dev/null
        source "$pkg_file"

        if ! dpkg -s "$CHECK" &>/dev/null; then
          echo "  → Installing: $NAME ($PACKAGES)"
          # shellcheck disable=SC2086
          sudo apt install -y $PACKAGES
        fi
      done
    fi

    # 8b. Direct .deb downloads
    if [ -d "$EXT_DIR/deb-url" ]; then
      for pkg_file in "$EXT_DIR/deb-url"/*.sh; do
        [ -f "$pkg_file" ] || continue
        is_external_enabled "$pkg_file" || continue
        NAME="" DESCRIPTION="" URL="" CHECK=""
        # shellcheck source=/dev/null
        source "$pkg_file"

        if dpkg -s "$CHECK" &>/dev/null; then
          echo "  ✅ $NAME (already installed)"
        else
          echo "  → Downloading: $NAME"
          TMP_DIR="$(mktemp -d)"
          TMP_FILE="$TMP_DIR/download"
          if curl -fsSL -o "$TMP_FILE" "$URL"; then
            # Handle .zip containing .deb
            if echo "$URL" | grep -qi '\.zip$'; then
              unzip -q "$TMP_FILE" -d "$TMP_DIR"
              DEB_FILE="$(find "$TMP_DIR" -name '*.deb' | head -1)"
            else
              DEB_FILE="$TMP_FILE"
            fi
            if [ -n "$DEB_FILE" ] && [ -f "$DEB_FILE" ]; then
              echo "  → Installing: $NAME"
              sudo dpkg -i "$DEB_FILE" || sudo apt install -f -y
            else
              echo "  ⚠️  No .deb found in download: $NAME"
            fi
          else
            echo "  ⚠️  Download failed: $NAME ($URL)"
          fi
          rm -rf "$TMP_DIR"
        fi
      done
    fi

    # 8c. Custom install scripts
    if [ -d "$EXT_DIR/script" ]; then
      for pkg_file in "$EXT_DIR/script"/*.sh; do
        [ -f "$pkg_file" ] || continue
        is_external_enabled "$pkg_file" || continue
        NAME="" DESCRIPTION="" INSTALL_CMD="" CHECK_CMD=""
        # shellcheck source=/dev/null
        source "$pkg_file"

        if [ -n "$CHECK_CMD" ] && eval "$CHECK_CMD" &>/dev/null; then
          echo "  ✅ $NAME (already installed)"
        else
          echo "  → Running installer: $NAME"
          eval "$INSTALL_CMD" || echo "  ⚠️  Install failed: $NAME"
        fi
      done
    fi
  fi
fi

echo ""
echo "✅ Bootstrap complete."
echo "   Restart your terminal to apply shell changes."
echo "   Run 'source ~/.bashrc' for immediate effect."

