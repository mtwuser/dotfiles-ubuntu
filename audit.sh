#!/usr/bin/env bash
# Audits system state against dotfiles-ubuntu manifests
# Usage: ./audit.sh [--clean]
#   (no flag)  Read-only audit — shows all sections, detail only on issues
#   --clean    Interactive cleanup of residual files

set -euo pipefail
export LC_ALL=C

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SYSTEM_DIR="$SCRIPT_DIR/system"
VERSION_STR="$(tr -d '[:space:]' < "$SCRIPT_DIR/VERSION" 2>/dev/null || echo "unknown")"
MODE="${1:-audit}"

case "$MODE" in
  audit|--clean) ;;
  -v|--version)
    echo "dotfiles-ubuntu v$VERSION_STR"
    exit 0
    ;;
  -h|--help)
    echo "Usage: ./audit.sh [--clean | --version | --help]"
    echo "  (no flag)      Read-only audit — shows all sections, detail only on issues"
    echo "  --clean        Interactive cleanup of residual files"
    echo "  -v, --version  Show version information"
    exit 0
    ;;
  *)
    echo "❌ Unknown option: $MODE" >&2
    echo "Usage: ./audit.sh [--clean | --version | --help]" >&2
    exit 1
    ;;
esac

if [ -n "${NO_COLOR:-}" ]; then
  RED='' GREEN='' YELLOW='' BLUE='' CYAN='' NC='' BOLD=''
else
  RED='\033[0;31m' GREEN='\033[0;32m' YELLOW='\033[1;33m'
  BLUE='\033[0;34m' CYAN='\033[0;36m' NC='\033[0m' BOLD='\033[1m'
fi

ISSUES=0
AUDIT_IGNORE=""
if [ -f "$SCRIPT_DIR/.audit-ignore" ]; then
  AUDIT_IGNORE="$(grep -v '^#' "$SCRIPT_DIR/.audit-ignore" | grep -v '^$' | sort)"
fi

section() { echo -e "\n${BLUE}=== $1 ===${NC}"; }
ok()      { echo -e "  ${GREEN}✅${NC} $1"; }
warn()    { echo -e "  ${YELLOW}⚠️${NC}  $1"; ISSUES=$((ISSUES + 1)); }
item()    { echo -e "      $1"; }
confirm() { read -rp "  $1 (y/N): " answer; [ "$answer" = "y" ] || [ "$answer" = "Y" ]; }

echo -e "${BOLD}🔍 dotfiles-ubuntu audit — $(date +%Y-%m-%d)${NC}"

# 1. Stow Symlinks
section "Stow Symlinks"
STOW_OK=0
STOW_ISSUES=0

cd "$SCRIPT_DIR"
for module_dir in */; do
  module_name="${module_dir%/}"
  case "$module_name" in
    system|scripts|templates|docs|layers|logs|tests|venv|.venv|htmlcov|.git) continue ;;
  esac
  [ ! -d "$module_name" ] && continue

  while IFS= read -r relpath; do
    [ -z "$relpath" ] && continue
    target="$HOME/$relpath"
    source="$SCRIPT_DIR/$module_name/$relpath"
    if [ -e "$target" ] || [ -L "$target" ]; then
      resolved_target="$(readlink -f "$target" 2>/dev/null || echo "BROKEN")"
      resolved_source="$(readlink -f "$source")"
      if [ "$resolved_target" = "$resolved_source" ]; then
        STOW_OK=$((STOW_OK + 1))
      else
        warn "[$module_name] ~/$relpath → wrong target"
        item "expected: $resolved_source"
        item "actual:   $resolved_target"
        STOW_ISSUES=$((STOW_ISSUES + 1))
      fi
    else
      warn "[$module_name] ~/$relpath → missing"
      STOW_ISSUES=$((STOW_ISSUES + 1))
    fi
  done < <(find "$module_name" -type f -not -path '*/.git/*' -not -path '*/__pycache__/*' -not -name '*.pyc' -printf '%P\n')
done

if [ "$STOW_ISSUES" -eq 0 ]; then
  if [ -L "$HOME/.gemini" ] || [ -L "$HOME/.gemini/config" ] || [ -L "$HOME/.gemini/config/skills" ]; then
    warn "~/.gemini/config or ~/.gemini/config/skills is a folded symlink instead of a real directory"
  else
    ok "All $STOW_OK symlinks healthy (tree-unfolded)"
  fi
fi

# 2. APT Packages
section "APT Packages"
if [ -f "$SYSTEM_DIR/packages-manual.txt" ]; then
  CURRENT_APT="$(apt-mark showmanual 2>/dev/null | grep -v '^linux-generic-hwe-' | sort)"
  UBUNTU_REMOTE="$(grep -h '^Package: ' /var/lib/apt/lists/*ubuntu.com*Packages 2>/dev/null | awk '{print $2}' | sort -u || true)"
  if [ -n "$UBUNTU_REMOTE" ]; then
    CURRENT_APT="$(awk 'NR==FNR {ok[$1]=1; next} {base=$1; sub(/:.*/, "", base); if (ok[base]) print $1}' <(echo "$UBUNTU_REMOTE") <(echo "$CURRENT_APT"))"
  fi
  MANIFEST_APT="$(grep -v '^$' "$SYSTEM_DIR/packages-manual.txt" | sort)"
  ONLY_SYSTEM="$(comm -23 <(echo "$CURRENT_APT") <(echo "$MANIFEST_APT") || true)"
  ONLY_MANIFEST="$(comm -13 <(echo "$CURRENT_APT") <(echo "$MANIFEST_APT") || true)"

  EXTERNAL_PKGS=""
  for ext_file in "$SYSTEM_DIR"/external/deb-url/*.sh "$SYSTEM_DIR"/external/script/*.sh "$SYSTEM_DIR"/external/apt-repo/*.sh; do
    [ -f "$ext_file" ] || continue
    ext_check="$(grep '^CHECK=' "$ext_file" 2>/dev/null | head -1 | cut -d'"' -f2 || true)"
    [ -n "$ext_check" ] && EXTERNAL_PKGS="$EXTERNAL_PKGS $ext_check"
    ext_packages="$(grep '^PACKAGES=' "$ext_file" 2>/dev/null | head -1 | cut -d'"' -f2 || true)"
    [ -n "$ext_packages" ] && EXTERNAL_PKGS="$EXTERNAL_PKGS $ext_packages"
    repo_helpers="$(grep -oP '[a-z0-9][-a-z0-9]*-(?:stable-)?release[_/]' "$ext_file" 2>/dev/null | sed 's|[_/]$||' | sort -u || true)"
    [ -n "$repo_helpers" ] && EXTERNAL_PKGS="$EXTERNAL_PKGS $repo_helpers"
  done
  EXTERNAL_PKGS_SORTED="$(echo "$EXTERNAL_PKGS" | tr ' ' '\n' | grep -v '^$' | sort -u)"

  if [ -n "$EXTERNAL_PKGS_SORTED" ]; then
    ONLY_SYSTEM="$(comm -23 <(echo "$ONLY_SYSTEM") <(echo "$EXTERNAL_PKGS_SORTED") || true)"
    ONLY_MANIFEST="$(comm -23 <(echo "$ONLY_MANIFEST") <(echo "$EXTERNAL_PKGS_SORTED") || true)"
  fi
  if [ -n "$AUDIT_IGNORE" ]; then
    ONLY_SYSTEM="$(comm -23 <(echo "$ONLY_SYSTEM") <(echo "$AUDIT_IGNORE") || true)"
    ONLY_MANIFEST="$(comm -23 <(echo "$ONLY_MANIFEST") <(echo "$AUDIT_IGNORE") || true)"
  fi

  HAS_DRIFT=false
  if [ -n "$ONLY_SYSTEM" ]; then
    HAS_DRIFT=true
    COUNT=$(echo "$ONLY_SYSTEM" | wc -l)
    warn "$COUNT installed but not in manifest (run ./backup.sh to capture):"
    echo "$ONLY_SYSTEM" | head -20 | while IFS= read -r pkg; do item "${GREEN}+ $pkg${NC}"; done
    [ "$COUNT" -gt 20 ] && item "... and $((COUNT - 20)) more"
  fi
  if [ -n "$ONLY_MANIFEST" ]; then
    HAS_DRIFT=true
    COUNT=$(echo "$ONLY_MANIFEST" | wc -l)
    warn "$COUNT in manifest but not installed:"
    echo "$ONLY_MANIFEST" | while IFS= read -r pkg; do item "${RED}- $pkg${NC}"; done
  fi
  if [ "$HAS_DRIFT" = false ]; then
    TOTAL=$(grep -c . <<< "$MANIFEST_APT" || true)
    ok "In sync ($TOTAL packages)"
  fi
else
  warn "packages-manual.txt not found"
fi

# 3. Snap Packages
section "Snap Packages"
if [ -f "$SYSTEM_DIR/snaps.txt" ] && command -v snap &>/dev/null; then
  CURRENT_SNAPS="$(snap list 2>/dev/null | tail -n +2 | awk '$6 !~ /^(base|snapd)$/ && $1 !~ /^(gnome-[0-9]|gtk-common-themes|mesa-[0-9])/ {print $1}' | sort || true)"
  MANIFEST_SNAPS="$(grep -v '^$' "$SYSTEM_DIR/snaps.txt" | sort || true)"
  ONLY_SYSTEM="$(comm -23 <(echo "$CURRENT_SNAPS") <(echo "$MANIFEST_SNAPS") | grep -v '^$' || true)"
  ONLY_MANIFEST="$(comm -13 <(echo "$CURRENT_SNAPS") <(echo "$MANIFEST_SNAPS") | grep -v '^$' || true)"
  HAS_DRIFT=false
  if [ -n "$ONLY_SYSTEM" ]; then
    HAS_DRIFT=true
    COUNT=$(echo "$ONLY_SYSTEM" | wc -l)
    warn "$COUNT installed but not in manifest:"
    echo "$ONLY_SYSTEM" | while IFS= read -r snap_pkg; do item "${GREEN}+ $snap_pkg${NC}"; done
  fi
  if [ -n "$ONLY_MANIFEST" ]; then
    HAS_DRIFT=true
    COUNT=$(echo "$ONLY_MANIFEST" | wc -l)
    warn "$COUNT in manifest but not installed:"
    echo "$ONLY_MANIFEST" | while IFS= read -r snap_pkg; do item "${RED}- $snap_pkg${NC}"; done
  fi
  if [ "$HAS_DRIFT" = false ]; then
    TOTAL=$(grep -c . <<< "$MANIFEST_SNAPS" || true)
    ok "In sync ($TOTAL snaps)"
  fi
elif ! command -v snap &>/dev/null; then
  warn "snap not available on this system"
else
  warn "snaps.txt not found"
fi

# 4. NPM Globals
section "NPM Globals"
if ! command -v npm &>/dev/null && [ -s "$HOME/.nvm/nvm.sh" ]; then
  export NVM_DIR="$HOME/.nvm"
  # shellcheck source=/dev/null
  . "$NVM_DIR/nvm.sh"
fi
if [ -f "$SYSTEM_DIR/npm-globals.txt" ] && command -v npm &>/dev/null; then
  CURRENT_NPM="$(npm list -g --depth=0 2>/dev/null | tail -n +2 | sed 's/^[-├└─+` ]*//g' | grep -v '^$' | sort || true)"
  MANIFEST_NPM="$(grep -v '^$' "$SYSTEM_DIR/npm-globals.txt" | sort || true)"
  ONLY_SYSTEM="$(comm -23 <(echo "$CURRENT_NPM") <(echo "$MANIFEST_NPM") | grep -v '^$' || true)"
  ONLY_MANIFEST="$(comm -13 <(echo "$CURRENT_NPM") <(echo "$MANIFEST_NPM") | grep -v '^$' || true)"
  HAS_DRIFT=false
  if [ -n "$ONLY_SYSTEM" ]; then
    HAS_DRIFT=true
    COUNT=$(echo "$ONLY_SYSTEM" | wc -l)
    warn "$COUNT installed but not in manifest:"
    echo "$ONLY_SYSTEM" | while IFS= read -r pkg; do item "${GREEN}+ $pkg${NC}"; done
  fi
  if [ -n "$ONLY_MANIFEST" ]; then
    HAS_DRIFT=true
    COUNT=$(echo "$ONLY_MANIFEST" | wc -l)
    warn "$COUNT in manifest but not installed:"
    echo "$ONLY_MANIFEST" | while IFS= read -r pkg; do item "${RED}- $pkg${NC}"; done
  fi
  if [ "$HAS_DRIFT" = false ]; then
    TOTAL=$(grep -c . <<< "$MANIFEST_NPM" || true)
    ok "In sync ($TOTAL packages)"
  fi
elif ! command -v npm &>/dev/null; then
  warn "npm not available (install NVM+Node with ./bootstrap.sh --nvm)"
else
  warn "npm-globals.txt not found"
fi

# 5. External Packages
section "External Packages"
EXT_DIR="$SYSTEM_DIR/external"
EXT_INSTALLED=0
EXT_MISSING=0
if [ -d "$EXT_DIR" ]; then
  MISSING_NAMES=()
  UNTRACKED_NAMES=()
  INACTIVE_REPOS=()
  MANIFEST_EXT=""
  if [ -f "$SYSTEM_DIR/external.txt" ]; then
    MANIFEST_EXT="$(grep -v '^#' "$SYSTEM_DIR/external.txt" | grep -v '^$' | sort || true)"
  fi

  for pkg_file in "$EXT_DIR"/apt-repo/*.sh "$EXT_DIR"/deb-url/*.sh "$EXT_DIR"/script/*.sh; do
    [ -f "$pkg_file" ] || continue
    rel_ext="${pkg_file#"$EXT_DIR"/}"
    IN_MANIFEST=true
    if [ -f "$SYSTEM_DIR/external.txt" ] && ! grep -qxF "$rel_ext" <<< "$MANIFEST_EXT"; then
      IN_MANIFEST=false
    fi
    NAME="" DESCRIPTION="" CHECK="" CHECK_CMD="" URL="" PACKAGES="" INSTALL_CMD=""
    setup_repo() { :; }
    # shellcheck source=/dev/null
    source "$pkg_file"

    INSTALLED=false
    if [ -n "${CHECK:-}" ] && dpkg -s "$CHECK" &>/dev/null 2>&1; then
      INSTALLED=true
      if [ "$IN_MANIFEST" = true ] && [[ "$pkg_file" == *"/apt-repo/"* ]] && ! apt-cache policy "$CHECK" 2>/dev/null | grep -q 'http'; then
        INACTIVE_REPOS+=("$NAME")
      fi
    elif [ -n "${CHECK_CMD:-}" ] && eval "$CHECK_CMD" &>/dev/null 2>&1; then
      INSTALLED=true
    fi

    if [ "$IN_MANIFEST" = true ]; then
      if [ "$INSTALLED" = true ]; then
        EXT_INSTALLED=$((EXT_INSTALLED + 1))
      else
        MISSING_NAMES+=("$NAME ($rel_ext)")
        EXT_MISSING=$((EXT_MISSING + 1))
      fi
    elif [ "$INSTALLED" = true ]; then
      UNTRACKED_NAMES+=("$NAME ($rel_ext)")
    fi
  done

  if [ "${#UNTRACKED_NAMES[@]}" -gt 0 ]; then
    warn "${#UNTRACKED_NAMES[@]} external package(s) installed but not in external.txt (run ./backup.sh to capture):"
    for name in "${UNTRACKED_NAMES[@]}"; do item "${GREEN}+ $name${NC}"; done
  fi
  if [ "$EXT_MISSING" -gt 0 ]; then
    warn "$EXT_MISSING external package(s) in external.txt but not installed:"
    for name in "${MISSING_NAMES[@]}"; do item "${RED}- $name${NC}"; done
    item "💡 Run ${CYAN}./bootstrap.sh --external${NC} to install"
  fi
  if [ "${#INACTIVE_REPOS[@]}" -gt 0 ]; then
    warn "${#INACTIVE_REPOS[@]} external APT repo(s) inactive or disabled:"
    for name in "${INACTIVE_REPOS[@]}"; do item "${YELLOW}! $name (package installed, but APT repository is disabled/missing)${NC}"; done
    item "💡 Run ${CYAN}./bootstrap.sh --external${NC} to re-enable APT repositories"
  fi
  if [ "${#UNTRACKED_NAMES[@]}" -eq 0 ] && [ "$EXT_MISSING" -eq 0 ] && [ "${#INACTIVE_REPOS[@]}" -eq 0 ]; then
    TOTAL=$((EXT_INSTALLED + EXT_MISSING))
    ok "In sync ($TOTAL external packages active)"
  fi
else
  ok "No external packages defined"
fi

# 6. GNOME Extensions
section "GNOME Extensions"
if [ -f "$SYSTEM_DIR/gnome-extensions.txt" ] && command -v gnome-extensions &>/dev/null; then
  CURRENT_EXT="$(gnome-extensions list --enabled 2>/dev/null | sort || true)"
  MANIFEST_EXT_GNOME="$(grep -v '^#' "$SYSTEM_DIR/gnome-extensions.txt" | grep -v '^$' | sort || true)"
  MISSING_EXT_GNOME="$(comm -13 <(echo "$CURRENT_EXT") <(echo "$MANIFEST_EXT_GNOME") | grep -v '^$' || true)"
  if [ -n "$MISSING_EXT_GNOME" ]; then
    COUNT=$(echo "$MISSING_EXT_GNOME" | wc -l)
    warn "$COUNT GNOME extension(s) in manifest but not enabled:"
    echo "$MISSING_EXT_GNOME" | while IFS= read -r ext_uuid; do item "${RED}- $ext_uuid${NC}"; done
  else
    TOTAL=$(grep -c . <<< "$MANIFEST_EXT_GNOME" || true)
    ok "In sync ($TOTAL extensions enabled)"
  fi
else
  ok "GNOME extensions check skipped or not applicable"
fi

# 7. Residual Files
section "Residual Files"
FOUND_RESIDUALS=false
BACKUPS="$(find "$HOME" -maxdepth 4 -name '*.backup.*' \
  -not -path '*/dotfiles-ubuntu/*' -not -path '*/.git/*' 2>/dev/null || true)"

if [ -n "$BACKUPS" ]; then
  FOUND_RESIDUALS=true
  COUNT=$(echo "$BACKUPS" | wc -l)
  warn "$COUNT backup file(s) from bootstrap:"
  echo "$BACKUPS" | while IFS= read -r f; do item "${f/#$HOME/\~}"; done
  if [ "$MODE" = "--clean" ]; then
    if confirm "Delete $COUNT backup file(s)?"; then
      echo "$BACKUPS" | while IFS= read -r f; do
        rm -rf "$f"
        echo -e "      ${RED}deleted${NC} ${f/#$HOME/\~}"
      done
      ok "Backup files removed"
    fi
  else
    item "💡 Run with ${CYAN}--clean${NC} to remove interactively"
  fi
fi

if [ -d "$HOME/AppImage" ]; then
  FOUND_RESIDUALS=true
  SIZE="$(du -sh "$HOME/AppImage" 2>/dev/null | cut -f1)"
  warn "~/AppImage/ exists ($SIZE total):"
  while IFS= read -r app; do
    [ -z "$app" ] && continue
    APP_SIZE="$(du -sh "$HOME/AppImage/$app" 2>/dev/null | cut -f1)"
    item "$app ($APP_SIZE)"
  done < <(ls -1 "$HOME/AppImage" 2>/dev/null)

  if [ "$MODE" = "--clean" ]; then
    while IFS= read -r app; do
      [ -z "$app" ] && continue
      if confirm "Delete ~/AppImage/$app/?"; then
        rm -rf "${HOME:?}/AppImage/$app"
        echo -e "      ${RED}deleted${NC} ~/AppImage/$app/"
      fi
    done < <(ls -1 "$HOME/AppImage" 2>/dev/null)
    if [ -d "$HOME/AppImage" ] && [ -z "$(ls -A "$HOME/AppImage")" ]; then
      rmdir "$HOME/AppImage"
      ok "Removed empty ~/AppImage/"
    fi
  else
    item "💡 Run with ${CYAN}--clean${NC} to remove interactively"
  fi
fi

[ "$FOUND_RESIDUALS" = false ] && ok "No residual files found"

# 8. Repo Status
section "Repo Status"
cd "$SCRIPT_DIR"
if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
  warn "Uncommitted changes:"
  git status --short | while IFS= read -r line; do item "$line"; done
else
  ok "Working tree clean"
fi

UPSTREAM="$(git rev-parse --abbrev-ref '@{u}' 2>/dev/null || true)"
if [ -n "$UPSTREAM" ]; then
  UNPUSHED="$(git log --oneline '@{u}..HEAD' 2>/dev/null || true)"
  BEHIND="$(git log --oneline 'HEAD..@{u}' 2>/dev/null || true)"
  if [ -n "$UNPUSHED" ]; then
    COUNT=$(echo "$UNPUSHED" | wc -l)
    warn "$COUNT unpushed commit(s):"
    echo "$UNPUSHED" | while IFS= read -r line; do item "$line"; done
  fi
  if [ -n "$BEHIND" ]; then
    COUNT=$(echo "$BEHIND" | wc -l)
    warn "$COUNT unpulled commit(s) behind remote:"
    echo "$BEHIND" | while IFS= read -r line; do item "$line"; done
  fi
  if [ -z "$UNPUSHED" ] && [ -z "$BEHIND" ]; then
    ok "In sync with remote"
  fi
else
  warn "No upstream branch configured"
fi

echo ""
if [ "$ISSUES" -eq 0 ]; then
  echo -e "${GREEN}${BOLD}✅ System is clean and in sync.${NC}"
  exit 0
else
  echo -e "${YELLOW}${BOLD}⚠️  $ISSUES issue(s) found.${NC}"
  [ "$MODE" != "--clean" ] && echo -e "   Run ${CYAN}./audit.sh --clean${NC} to fix residual files interactively."
  exit 1
fi
