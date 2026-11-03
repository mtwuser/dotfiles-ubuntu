#!/usr/bin/env bash
# Install or update Antigravity Agents (recommended), Antigravity CLI (agy), and/or optional Antigravity IDE
# Usage: ./scripts/antigravity-install.sh [--agents | --cli | --ide | --all | --version | --help]
#   Agents (Recommended): Auto-downloads latest Linux x64 release from https://antigravity.google/download
#                         (or uses manual archive in ~/Downloads/Antigravity{.tar.gz,.zip,-x64.tar.gz,-x64.zip})
#   CLI (agy):            https://antigravity.google/cli/install.sh -> ~/.local/bin/agy
#   IDE (Optional):       ~/Downloads/Antigravity IDE{.zip,.tar.gz}

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
VERSION_STR="$(tr -d '[:space:]' < "$REPO_DIR/VERSION" 2>/dev/null || echo "unknown")"
DOWNLOADS_DIR="$HOME/Downloads"
AGENTS_DEST="/opt/antigravity-agents"
IDE_DEST="/opt/antigravity-ide"
CLI_BIN="$HOME/.local/bin/agy"
CLI_INSTALL_URL="https://antigravity.google/cli/install.sh"
HUB_RELEASES_URL="https://antigravity-hub-auto-updater-974169037036.us-central1.run.app/releases"
HUB_BUCKET_BASE="https://storage.googleapis.com/antigravity-public/antigravity-hub"
DOWNLOAD_PAGE_URL="https://antigravity.google/download"

MODE="${1:-interactive}"

case "$MODE" in
  interactive|--all|--agents|--cli|--ide) ;;
  -v|--version) echo "dotfiles-ubuntu v$VERSION_STR"; exit 0 ;;
  -h|--help)
    echo "Usage: ./scripts/antigravity-install.sh [--agents | --cli | --ide | --all | --version | --help]"
    echo "  (no flag)      Interactive — asks what to install/update"
    echo "  --agents       (Recommended) Auto-download & install/update Antigravity Agents + agy CLI"
    echo "  --cli          Install/update Antigravity CLI (agy) only (~/.local/bin/agy)"
    echo "  --ide          (Optional) Install/update Antigravity IDE only"
    echo "  --all          Install/update Antigravity Agents, CLI (agy), and optional IDE"
    echo "  -v, --version  Show version information"
    exit 0
    ;;
  *)
    echo "❌ Unknown option: $MODE" >&2
    echo "Usage: ./scripts/antigravity-install.sh [--agents | --cli | --ide | --all]" >&2
    exit 1
    ;;
esac

confirm() {
  if [ "$MODE" = "--all" ]; then return 0; fi
  read -rp "$1 (y/N): " answer
  [ "$answer" = "y" ] || [ "$answer" = "Y" ]
}

ensure_unzip() {
  if ! command -v unzip &>/dev/null; then
    echo "  → Installing unzip..."
    sudo apt-get update -qq && sudo apt-get install -y -qq unzip
  fi
}

extract_archive() {
  local archive="$1" target_dir="$2"
  echo "  → Extracting archive: $(basename "$archive")..."
  rm -rf "$target_dir" && mkdir -p "$target_dir"
  case "$archive" in
    *.zip) ensure_unzip; unzip -q -o "$archive" -d "$target_dir" ;;
    *.tar.gz|*.tgz) tar -xzf "$archive" -C "$target_dir" ;;
    *) echo "⚠️  Unsupported archive format: $archive"; return 1 ;;
  esac
}

resolve_latest_agents_url() {
  local rel_json rel_id url=""
  rel_json="$(curl -fsSL --max-time 10 "$HUB_RELEASES_URL" 2>/dev/null || true)"
  if [ -n "$rel_json" ]; then
    rel_id="$(python3 -c 'import json,sys; d=json.loads(sys.stdin.read()); r=d[0]; print(f"{r[\"version\"]}-{r[\"execution_id\"]}")' <<<"$rel_json" 2>/dev/null || true)"
    [ -n "$rel_id" ] && url="$HUB_BUCKET_BASE/$rel_id/linux-x64/Antigravity.tar.gz"
  fi
  if [ -z "$url" ]; then
    url="$(curl -fsSL --max-time 10 "$DOWNLOAD_PAGE_URL" 2>/dev/null | grep -oE 'https://storage\.googleapis\.com/antigravity-public/antigravity-hub/[^"'\'' >]+/linux-x64/Antigravity\.tar\.gz' | head -n 1 || true)"
  fi
  echo "$url"
}

prepare_agents_src() {
  mkdir -p "$DOWNLOADS_DIR"
  local latest_url archive=""
  echo "  → Checking latest Antigravity Agents release from official feed..." >&2
  latest_url="$(resolve_latest_agents_url)"
  if [ -n "$latest_url" ]; then
    echo "  → Removing previous archive(s) in $DOWNLOADS_DIR and downloading: $latest_url" >&2
    rm -rf "$DOWNLOADS_DIR/Antigravity" "$DOWNLOADS_DIR/Antigravity.zip" "$DOWNLOADS_DIR/Antigravity.tar.gz" \
           "$DOWNLOADS_DIR/Antigravity-x64.zip" "$DOWNLOADS_DIR/Antigravity-x64.tar.gz"
    if curl -fL --progress-bar -o "$DOWNLOADS_DIR/Antigravity.tar.gz.part" "$latest_url" >&2; then
      mv -f "$DOWNLOADS_DIR/Antigravity.tar.gz.part" "$DOWNLOADS_DIR/Antigravity.tar.gz"
    else
      rm -f "$DOWNLOADS_DIR/Antigravity.tar.gz.part"
      echo "⚠️  Automatic download failed; checking for a manually downloaded archive in $DOWNLOADS_DIR..." >&2
    fi
  else
    echo "⚠️  Could not resolve latest release URL automatically; checking $DOWNLOADS_DIR..." >&2
  fi

  for candidate in \
    "$DOWNLOADS_DIR/Antigravity.zip" \
    "$DOWNLOADS_DIR/Antigravity.tar.gz" \
    "$DOWNLOADS_DIR/Antigravity-x64.zip" \
    "$DOWNLOADS_DIR/Antigravity-x64.tar.gz"; do
    if [ -f "$candidate" ] && { [ -z "$archive" ] || [ "$candidate" -nt "$archive" ]; }; then
      archive="$candidate"
    fi
  done

  if [ -n "$archive" ]; then
    extract_archive "$archive" "$DOWNLOADS_DIR/Antigravity" >&2
  fi

  if [ -d "$DOWNLOADS_DIR/Antigravity/Antigravity-x64" ]; then
    echo "$DOWNLOADS_DIR/Antigravity/Antigravity-x64"
  elif [ -f "$DOWNLOADS_DIR/Antigravity/antigravity" ]; then
    echo "$DOWNLOADS_DIR/Antigravity"
  else
    echo "$DOWNLOADS_DIR/Antigravity-x64"
  fi
}

prepare_ide_src() {
  local archive=""
  for candidate in "$DOWNLOADS_DIR/Antigravity IDE.zip" "$DOWNLOADS_DIR/Antigravity IDE.tar.gz"; do
    if [ -f "$candidate" ] && { [ -z "$archive" ] || [ "$candidate" -nt "$archive" ]; }; then
      archive="$candidate"
    fi
  done

  if [ -n "$archive" ]; then
    local stage_dir="$DOWNLOADS_DIR/.antigravity-ide-stage"
    extract_archive "$archive" "$stage_dir" >&2
    rm -rf "$DOWNLOADS_DIR/Antigravity IDE"
    if [ -d "$stage_dir/Antigravity IDE" ]; then
      mv "$stage_dir/Antigravity IDE" "$DOWNLOADS_DIR/Antigravity IDE" && rm -rf "$stage_dir"
    else
      mv "$stage_dir" "$DOWNLOADS_DIR/Antigravity IDE"
    fi
  fi
  echo "$DOWNLOADS_DIR/Antigravity IDE"
}

install_or_update() {
  local name="$1" src="$2" dest="$3"
  if [ ! -d "$src" ]; then
    echo "⚠️  Source not found: $src"
    echo "   Please download the latest Linux (x64) archive manually from:"
    echo "     $DOWNLOAD_PAGE_URL"
    echo "   Save it into ~/Downloads/ and re-run: ./scripts/antigravity-install.sh --agents"
    return 1
  fi

  echo "=== $name ==="
  if [ ! -d "$dest" ]; then
    echo "  → Fresh install (creating $dest)"
    sudo mkdir -p "$dest"
  else
    echo "  → Backing up current installation..."
    sudo rm -rf "${dest}.backup" && sudo cp -r "$dest" "${dest}.backup"
    echo "  → Removing old files..."
    sudo rm -rf "${dest:?}"/*
  fi

  echo "  → Copying from $src..."
  sudo cp -r "$src"/* "$dest"/

  if [ -f "$dest/chrome-sandbox" ]; then
    sudo chmod 4755 "$dest/chrome-sandbox"
    echo "  → chrome-sandbox permissions set (4755)"
  fi
  echo "  ✅ $name installed at $dest"
}

cleanup_backup() {
  local dest="$1"
  if [ -d "${dest}.backup" ]; then
    if confirm "  Remove backup (${dest}.backup)?"; then
      sudo rm -rf "${dest}.backup"
      echo "  → Backup removed"
    else
      echo "  → Backup kept at ${dest}.backup"
    fi
  fi
}

install_or_update_cli() {
  echo "=== Antigravity CLI (agy) ==="
  mkdir -p "$(dirname "$CLI_BIN")"
  if [ -f "$CLI_BIN" ]; then
    echo "  → Removing existing $CLI_BIN (backed up to ${CLI_BIN}.backup) before fresh CLI install..."
    mv -f "$CLI_BIN" "${CLI_BIN}.backup"
  fi
  if curl -fsSL "$CLI_INSTALL_URL" | bash; then
    rm -f "${CLI_BIN}.backup"
    echo "  ✅ Antigravity CLI (agy) installed/updated at $CLI_BIN"
  else
    [ -f "${CLI_BIN}.backup" ] && mv -f "${CLI_BIN}.backup" "$CLI_BIN"
    echo "⚠️  Failed to download Antigravity CLI from $CLI_INSTALL_URL (previous binary restored if present)."
    return 1
  fi
}

# --- Agents + CLI ---
if [ "$MODE" = "--all" ] || [ "$MODE" = "--agents" ] || [ "$MODE" = "interactive" ]; then
  if [ "$MODE" = "interactive" ] && ! confirm "Install/update Antigravity Agents (recommended)?"; then
    echo "Skipping Agents."
  else
    AGENTS_SRC="$(prepare_agents_src)"
    install_or_update "Antigravity Agents" "$AGENTS_SRC" "$AGENTS_DEST"
    cleanup_backup "$AGENTS_DEST"
    echo ""
    install_or_update_cli
  fi
fi

if [ "$MODE" = "--cli" ] || { [ "$MODE" = "interactive" ] && ! [ -f "$CLI_BIN" ]; }; then
  if [ "$MODE" = "--cli" ] || confirm "Install/update Antigravity CLI (agy)?"; then
    install_or_update_cli
  fi
fi

echo ""

# --- Optional IDE ---
if [ "$MODE" = "--all" ] || [ "$MODE" = "--ide" ] || [ "$MODE" = "interactive" ]; then
  if [ "$MODE" = "interactive" ] && ! confirm "Install/update Antigravity IDE (optional)?"; then
    echo "Skipping IDE."
  else
    IDE_SRC="$(prepare_ide_src)"
    install_or_update "Antigravity IDE" "$IDE_SRC" "$IDE_DEST"
    cleanup_backup "$IDE_DEST"
  fi
fi

echo ""
echo "  → Updating desktop database..."
update-desktop-database ~/.local/share/applications 2>/dev/null || true
echo ""
echo "✅ Done. Restart any running Antigravity instances to apply updates."
