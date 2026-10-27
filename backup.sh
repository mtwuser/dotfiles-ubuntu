#!/usr/bin/env bash
# Captures current system state into system/ manifests
# Usage: ./backup.sh [--help]
# Safe to run multiple times (overwrites manifests with current machine's state)

set -euo pipefail
export LC_ALL=C

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SYSTEM_DIR="$SCRIPT_DIR/system"
VERSION_STR="$(tr -d '[:space:]' < "$SCRIPT_DIR/VERSION" 2>/dev/null || echo "unknown")"

case "${1:-}" in
  -h|--help)
    echo "Usage: ./backup.sh [--help | --version]"
    echo "  Captures the current machine's APT packages, Snaps, NPM globals,"
    echo "  NVM default version, enabled external packages, GNOME extensions,"
    echo "  and declarative GNOME settings into system/ manifests."
    exit 0
    ;;
  -v|--version)
    echo "dotfiles-ubuntu v$VERSION_STR"
    exit 0
    ;;
  "") ;;
  *)
    echo "❌ Unknown option: $1" >&2
    echo "Usage: ./backup.sh [--help | --version]" >&2
    exit 1
    ;;
esac

mkdir -p "$SYSTEM_DIR"

echo "📦 Capturing package manifests..."

echo "  → APT packages (manual only, excluding external, obsolete & machine-local)..."
RAW_APT="$(apt-mark showmanual 2>/dev/null | grep -v '^linux-generic-hwe-' | sort || true)"

# Exclude local/obsolete packages not present in official Ubuntu APT lists
UBUNTU_REMOTE="$(grep -h '^Package: ' /var/lib/apt/lists/*ubuntu.com*Packages 2>/dev/null | awk '{print $2}' | sort -u || true)"
if [ -n "$UBUNTU_REMOTE" ] && [ -n "$RAW_APT" ]; then
  RAW_APT="$(awk 'NR==FNR {ok[$1]=1; next} {base=$1; sub(/:.*/, "", base); if (ok[base]) print $1}' <(echo "$UBUNTU_REMOTE") <(echo "$RAW_APT"))"
fi

# Exclude packages managed by system/external/ catalog
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
EXTERNAL_PKGS_SORTED="$(echo "$EXTERNAL_PKGS" | tr ' ' '\n' | grep -v '^$' | sort -u || true)"

if [ -n "$EXTERNAL_PKGS_SORTED" ] && [ -n "$RAW_APT" ]; then
  RAW_APT="$(comm -23 <(echo "$RAW_APT") <(echo "$EXTERNAL_PKGS_SORTED") || true)"
fi

# Exclude machine-local ignored packages (.audit-ignore)
if [ -f "$SCRIPT_DIR/.audit-ignore" ] && [ -n "$RAW_APT" ]; then
  AUDIT_IGNORE="$(grep -v '^#' "$SCRIPT_DIR/.audit-ignore" | grep -v '^$' | sort || true)"
  if [ -n "$AUDIT_IGNORE" ]; then
    RAW_APT="$(comm -23 <(echo "$RAW_APT") <(echo "$AUDIT_IGNORE") || true)"
  fi
fi

if [ -n "$RAW_APT" ]; then
  echo "$RAW_APT" > "$SYSTEM_DIR/packages-manual.txt"
else
  : > "$SYSTEM_DIR/packages-manual.txt"
fi
echo "    $(wc -l < "$SYSTEM_DIR/packages-manual.txt") packages"

echo "  → Snap packages (applications only, excluding base/content runtimes)..."
if command -v snap &>/dev/null; then
  { snap list 2>/dev/null | tail -n +2 | awk '$6 !~ /^(base|snapd)$/ && $1 !~ /^(gnome-[0-9]|gtk-common-themes|mesa-[0-9])/ {print $1}' | sort || true; } > "$SYSTEM_DIR/snaps.txt"
else
  : > "$SYSTEM_DIR/snaps.txt"
fi
echo "    $(wc -l < "$SYSTEM_DIR/snaps.txt") snaps"

echo "  → NPM globals..."
if ! command -v npm &>/dev/null && [ -s "$HOME/.nvm/nvm.sh" ]; then
  export NVM_DIR="$HOME/.nvm"
  # shellcheck source=/dev/null
  . "$NVM_DIR/nvm.sh"
fi
if command -v npm &>/dev/null; then
  { npm list -g --depth=0 2>/dev/null | tail -n +2 | sed 's/^[-├└─+` ]*//g' | grep -v '^$' | sort || true; } > "$SYSTEM_DIR/npm-globals.txt"
else
  : > "$SYSTEM_DIR/npm-globals.txt"
fi
echo "    $(wc -l < "$SYSTEM_DIR/npm-globals.txt") packages"

echo "  → NVM default version..."
cat "$HOME/.nvm/alias/default" 2>/dev/null > "$SYSTEM_DIR/nvm-default.txt" || echo "none" > "$SYSTEM_DIR/nvm-default.txt"
echo "    $(cat "$SYSTEM_DIR/nvm-default.txt")"

echo "  → External packages (installed from system/external/ catalog)..."
EXT_DIR="$SYSTEM_DIR/external"
ENABLED_EXT=""
if [ -d "$EXT_DIR" ]; then
  for pkg_file in "$EXT_DIR"/apt-repo/*.sh "$EXT_DIR"/deb-url/*.sh "$EXT_DIR"/script/*.sh; do
    [ -f "$pkg_file" ] || continue
    NAME="" DESCRIPTION="" CHECK="" CHECK_CMD="" URL="" PACKAGES="" INSTALL_CMD=""
    setup_repo() { :; }
    # shellcheck source=/dev/null
    source "$pkg_file"
    rel_ext="${pkg_file#"$EXT_DIR"/}"
    if [ -n "${CHECK:-}" ] && dpkg -s "$CHECK" &>/dev/null 2>&1; then
      ENABLED_EXT="${ENABLED_EXT}${rel_ext}"$'\n'
    elif [ -n "${CHECK_CMD:-}" ] && eval "$CHECK_CMD" &>/dev/null 2>&1; then
      ENABLED_EXT="${ENABLED_EXT}${rel_ext}"$'\n'
    fi
  done
fi
if [ -n "$ENABLED_EXT" ]; then
  echo "$ENABLED_EXT" | grep -v '^$' | sort > "$SYSTEM_DIR/external.txt"
else
  : > "$SYSTEM_DIR/external.txt"
fi
echo "    $(wc -l < "$SYSTEM_DIR/external.txt") external packages"

echo "  → GNOME extensions..."
if command -v gnome-extensions &>/dev/null; then
  { gnome-extensions list 2>/dev/null | sort || true; } > "$SYSTEM_DIR/gnome-extensions.txt"
else
  : > "$SYSTEM_DIR/gnome-extensions.txt"
fi
echo "    $(wc -l < "$SYSTEM_DIR/gnome-extensions.txt") extensions"

echo "  → GNOME settings (declarative dconf paths only — excludes private/ephemeral state)..."
dconf dump / 2>/dev/null | awk '
  /^\[/ {
    keep = ($0 ~ /^\[(org\/gnome\/TextEditor|org\/gnome\/desktop\/(input-sources|interface|peripherals\/(keyboard|mouse|touchpad)|privacy|search-providers|session|sound|wm\/preferences)|org\/gnome\/mutter(\/keybindings)?|org\/gnome\/nautilus\/preferences|org\/gnome\/settings-daemon\/plugins\/power|org\/gnome\/shell\/extensions\/(dash-to-dock|ding|tiling-assistant))\]$/)
  }
  keep { print }
' > "$SYSTEM_DIR/gnome-settings.dconf" || true
echo "    $(wc -l < "$SYSTEM_DIR/gnome-settings.dconf") lines"

echo ""
echo "✅ Manifests updated in $SYSTEM_DIR/"
echo "   Review changes with: cd $(basename "$SCRIPT_DIR") && git diff"
