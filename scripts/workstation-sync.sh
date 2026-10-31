#!/usr/bin/env bash
# workstation-sync.sh — Declarative Workstation Setup & Boot-Time Runtime Synchronizer
#
# Manages local device preferences (~/.config/dotfiles-ubuntu/workstation.conf),
# enforces optional read-only push protection on the runtime clone (~/dotfiles-ubuntu),
# pulls fast-forward updates safely without AGENTS.md profile collisions, and re-stows
# bash, git, and antigravity modules into $HOME.
#
# Usage: ./scripts/workstation-sync.sh [sync | setup | status | --auto | --help | --version]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
RUNTIME_DIR="${DOTFILES_RUNTIME_DIR:-$REPO_DIR}"
RUNTIME_DIR="$(cd "$RUNTIME_DIR" && pwd)"
VERSION_STR="$({ tr -d '[:space:]' < "$RUNTIME_DIR/VERSION"; } 2>/dev/null || echo "unknown")"

CONFIG_FILE="${DOTFILES_WORKSTATION_CONF:-$HOME/.config/dotfiles-ubuntu/workstation.conf}"
STAMP_DIR="${XDG_RUNTIME_DIR:-/tmp}"
USER_UID="${UID:-$(id -u)}"
STAMP_FILE="${DOTFILES_SYNC_STAMP:-$STAMP_DIR/dotfiles-ubuntu-${USER_UID}.synced}"
READONLY_PUSH_GUARD="VALIDATION_BLOCKED_READONLY_RUNTIME"

usage() {
  cat <<EOF
Usage: ./scripts/workstation-sync.sh [COMMAND] [OPTIONS]

Commands:
  sync, --sync       Pull latest fast-forward release, apply global profile, and re-stow (default)
  setup, --setup     Configure ~/.config/dotfiles-ubuntu/workstation.conf and initialize runtime
  status, --status   Print workstation configuration and runtime status as JSON
  --auto             Boot-throttled quiet sync invoked automatically from ~/.bashrc
  -v, --version      Show version information
  -h, --help         Show this help message

Setup Options:
  --mode <readonly|mutable>                   Workstation runtime mode (default: readonly)
  --profile <human-core|technical|business|full> Global AGENTS.md profile (default: human-core)
  --auto-sync <boot|always|off>               Shell startup sync policy (default: boot)
  --dev-repo <path>                           Dedicated development clone path
  --no-sync                                   Write configuration without running sync
EOF
}

# Defaults (overridden by CONFIG_FILE if present)
DOTFILES_WORKSTATION_MODE="${DOTFILES_WORKSTATION_MODE:-readonly}"
DOTFILES_GLOBAL_PROFILE="${DOTFILES_GLOBAL_PROFILE:-human-core}"
DOTFILES_AUTO_SYNC="${DOTFILES_AUTO_SYNC:-boot}"
DOTFILES_DEV_REPO_DIR="${DOTFILES_DEV_REPO_DIR:-}"

if [ -f "$CONFIG_FILE" ]; then
  # shellcheck disable=SC1090
  . "$CONFIG_FILE"
fi

detect_dev_repo() {
  if [ -n "$DOTFILES_DEV_REPO_DIR" ] && [ -f "$DOTFILES_DEV_REPO_DIR/system/mcp-layer.json" ]; then
    echo "$DOTFILES_DEV_REPO_DIR"
    return
  fi
  local base_name
  base_name="$(basename "$RUNTIME_DIR")"
  local candidate="$HOME/Projects/dev-${base_name}"
  if [ -f "$candidate/system/mcp-layer.json" ]; then
    echo "$candidate"
    return
  fi
  echo ""
}

apply_push_guard() {
  local mode="$1"
  if [ ! -d "$RUNTIME_DIR/.git" ]; then
    return 0
  fi
  if [ "$mode" = "readonly" ]; then
    git -C "$RUNTIME_DIR" config remote.origin.pushurl "$READONLY_PUSH_GUARD" 2>/dev/null || true
  else
    local current_guard
    current_guard="$(git -C "$RUNTIME_DIR" config --get remote.origin.pushurl 2>/dev/null || true)"
    if [ "$current_guard" = "$READONLY_PUSH_GUARD" ]; then
      git -C "$RUNTIME_DIR" config --unset remote.origin.pushurl 2>/dev/null || true
    fi
  fi
}

run_sync() {
  local quiet_unchanged="${1:-0}"
  local old_ver new_ver
  old_ver="$({ tr -d '[:space:]' < "$RUNTIME_DIR/VERSION"; } 2>/dev/null || echo "unknown")"

  apply_push_guard "$DOTFILES_WORKSTATION_MODE"

  if [ -d "$RUNTIME_DIR/.git" ]; then
    if [ "$DOTFILES_WORKSTATION_MODE" = "readonly" ]; then
      git -C "$RUNTIME_DIR" checkout -- antigravity/.gemini/config/AGENTS.md 2>/dev/null || true
    fi
    if [ "${DOTFILES_SKIP_PULL:-0}" != "1" ]; then
      GIT_TERMINAL_PROMPT=0 timeout 4s git -C "$RUNTIME_DIR" pull --ff-only -q 2>/dev/null || true
    fi
  fi

  new_ver="$({ tr -d '[:space:]' < "$RUNTIME_DIR/VERSION"; } 2>/dev/null || echo "unknown")"

  if [ -x "$RUNTIME_DIR/scripts/layer-config.sh" ]; then
    "$RUNTIME_DIR/scripts/layer-config.sh" set-global-profile "$DOTFILES_GLOBAL_PROFILE" >/dev/null
  fi

  if [ "${DOTFILES_SKIP_STOW:-0}" != "1" ] && command -v stow >/dev/null 2>&1; then
    if [ -x "$RUNTIME_DIR/bootstrap.sh" ] && [ ! -L "$HOME/.gemini/config/AGENTS.md" ]; then
      "$RUNTIME_DIR/bootstrap.sh" --antigravity >/dev/null 2>&1 || true
    fi
    stow -d "$RUNTIME_DIR" -t "$HOME" -R bash git antigravity 2>/dev/null || \
      stow -d "$RUNTIME_DIR" -t "$HOME" -R antigravity 2>/dev/null || true
  fi

  mkdir -p "$(dirname "$STAMP_FILE")" 2>/dev/null || true
  printf '%s\n' "$new_ver" > "$STAMP_FILE" 2>/dev/null || true

  if [ "$quiet_unchanged" = "1" ]; then
    if [ "$old_ver" != "$new_ver" ]; then
      echo "✨ [dotfiles-ubuntu] Workstation runtime updated: v${old_ver} -> v${new_ver} (profile: ${DOTFILES_GLOBAL_PROFILE}, mode: ${DOTFILES_WORKSTATION_MODE})"
    fi
  else
    echo "✅ [dotfiles-ubuntu] Workstation synced (v${new_ver}, profile: ${DOTFILES_GLOBAL_PROFILE}, mode: ${DOTFILES_WORKSTATION_MODE})"
  fi
}

CMD="${1:-sync}"
case "$CMD" in
  -v|--version)
    echo "dotfiles-ubuntu v$VERSION_STR"
    exit 0
    ;;
  -h|--help)
    usage
    exit 0
    ;;
  sync|--sync)
    shift || true
    QUIET_FLAG=0
    while [ $# -gt 0 ]; do
      case "$1" in
        --quiet-if-unchanged|--auto)
          QUIET_FLAG=1
          shift
          ;;
        *)
          echo "❌ Unknown option: $1" >&2
          usage >&2
          exit 1
          ;;
      esac
    done
    run_sync "$QUIET_FLAG"
    exit 0
    ;;
  --auto)
    if [ "$DOTFILES_AUTO_SYNC" = "off" ]; then
      exit 0
    fi
    if [ "$DOTFILES_AUTO_SYNC" = "boot" ] && [ -f "$STAMP_FILE" ]; then
      exit 0
    fi
    run_sync 1
    exit 0
    ;;
  setup|--setup)
    shift || true
    MODE_ARG="$DOTFILES_WORKSTATION_MODE"
    PROFILE_ARG="$DOTFILES_GLOBAL_PROFILE"
    AUTO_ARG="$DOTFILES_AUTO_SYNC"
    DEV_ARG="$DOTFILES_DEV_REPO_DIR"
    NO_SYNC=0
    while [ $# -gt 0 ]; do
      case "$1" in
        --mode)
          MODE_ARG="${2:-}"
          shift 2
          ;;
        --profile)
          PROFILE_ARG="${2:-}"
          shift 2
          ;;
        --auto-sync)
          AUTO_ARG="${2:-}"
          shift 2
          ;;
        --dev-repo)
          DEV_ARG="${2:-}"
          shift 2
          ;;
        --no-sync)
          NO_SYNC=1
          shift
          ;;
        *)
          echo "❌ Unknown option: $1" >&2
          usage >&2
          exit 1
          ;;
      esac
    done
    case "$MODE_ARG" in
      readonly|mutable) ;;
      *) echo "❌ Invalid --mode '$MODE_ARG' (expected readonly or mutable)" >&2; exit 1 ;;
    esac
    case "$PROFILE_ARG" in
      human-core|technical|business|full) ;;
      *) echo "❌ Invalid --profile '$PROFILE_ARG' (expected human-core, technical, business, or full)" >&2; exit 1 ;;
    esac
    case "$AUTO_ARG" in
      boot|always|off) ;;
      *) echo "❌ Invalid --auto-sync '$AUTO_ARG' (expected boot, always, or off)" >&2; exit 1 ;;
    esac
    DOTFILES_WORKSTATION_MODE="$MODE_ARG"
    DOTFILES_GLOBAL_PROFILE="$PROFILE_ARG"
    DOTFILES_AUTO_SYNC="$AUTO_ARG"
    DOTFILES_DEV_REPO_DIR="$DEV_ARG"
    RESOLVED_DEV="$(detect_dev_repo)"

    mkdir -p "$(dirname "$CONFIG_FILE")"
    cat > "$CONFIG_FILE" <<EOF
# Declarative Workstation Configuration for dotfiles-ubuntu
export DOTFILES_WORKSTATION_MODE="$DOTFILES_WORKSTATION_MODE"
export DOTFILES_GLOBAL_PROFILE="$DOTFILES_GLOBAL_PROFILE"
export DOTFILES_AUTO_SYNC="$DOTFILES_AUTO_SYNC"
EOF
    if [ -n "$RESOLVED_DEV" ]; then
      printf 'export DOTFILES_DEV_REPO_DIR="%s"\n' "$RESOLVED_DEV" >> "$CONFIG_FILE"
    fi
    apply_push_guard "$DOTFILES_WORKSTATION_MODE"
    echo "✅ Workstation configuration written to $CONFIG_FILE"
    if [ "$NO_SYNC" = "0" ]; then
      run_sync 0
    fi
    exit 0
    ;;
  status|--status)
    RESOLVED_DEV="$(detect_dev_repo)"
    PUSH_GUARD_URL=""
    if [ -d "$RUNTIME_DIR/.git" ]; then
      PUSH_GUARD_URL="$(git -C "$RUNTIME_DIR" config --get remote.origin.pushurl 2>/dev/null || true)"
    fi
    GUARD_ACTIVE="false"
    if [ "$PUSH_GUARD_URL" = "$READONLY_PUSH_GUARD" ]; then
      GUARD_ACTIVE="true"
    fi
    BOOT_SYNCED="false"
    if [ -f "$STAMP_FILE" ]; then
      BOOT_SYNCED="true"
    fi
    cat <<EOF
{
  "version": "$VERSION_STR",
  "runtime_dir": "$RUNTIME_DIR",
  "config_file": "$CONFIG_FILE",
  "mode": "$DOTFILES_WORKSTATION_MODE",
  "profile": "$DOTFILES_GLOBAL_PROFILE",
  "auto_sync": "$DOTFILES_AUTO_SYNC",
  "push_guard_active": $GUARD_ACTIVE,
  "boot_synced": $BOOT_SYNCED,
  "dev_repo_dir": "$RESOLVED_DEV"
}
EOF
    exit 0
    ;;
  *)
    echo "❌ Unknown option: $CMD" >&2
    usage >&2
    exit 1
    ;;
esac
