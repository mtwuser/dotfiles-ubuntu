#!/usr/bin/env bash
# audit-global-config.sh — Detect orphaned or broken links in ~/.gemini/config/
#
# Compares the active global config directory against the dotfiles source of truth.
# Reports files/directories that exist locally but are NOT symlinked from dotfiles,
# and verifies that all shared skills in dotfiles are linked in ~/.gemini/config/skills/.
#
# Machine-local exceptions (expected to NOT be symlinked at top level):
#   config.json, mcp_config.json, .migrated, .ruff_cache, node_modules,
#   plugins/, sidecars/, projects/, skills/
#
# Usage: ./scripts/audit-global-config.sh [--help]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
VERSION_STR="$(tr -d '[:space:]' < "$REPO_DIR/VERSION" 2>/dev/null || echo "unknown")"
GLOBAL_DIR="$HOME/.gemini/config"
DOTFILES_DIR="$REPO_DIR/antigravity/.gemini/config"

case "${1:-}" in
    -h|--help)
        echo "Usage: ./scripts/audit-global-config.sh [--help | --version]"
        echo "  Verifies that ~/.gemini/config/ is tree-unfolded and all shared"
        echo "  Antigravity rules, hooks, scripts, and skills are properly linked."
        exit 0
        ;;
    -v|--version)
        echo "dotfiles-ubuntu v$VERSION_STR"
        exit 0
        ;;
    "") ;;
    *)
        echo "❌ Unknown option: $1" >&2
        exit 1
        ;;
esac

# Top-level files/dirs expected to be machine-local or container dirs
EXCEPTIONS=(
    "config.json"
    "mcp_config.json"
    ".migrated"
    ".ruff_cache"
    "node_modules"
    "plugins"
    "sidecars"
    "projects"
    "skills"
)

is_exception() {
    local name="$1"
    for exc in "${EXCEPTIONS[@]}"; do
        [[ "$name" == "$exc" ]] && return 0
    done
    return 1
}

echo "═══ Antigravity Global Config Audit ═══"
echo ""
echo "Global:   $GLOBAL_DIR"
echo "Dotfiles: $DOTFILES_DIR"
echo ""

orphans=0
broken=0
ok=0

# 0. Verify tree unfolding (parent directories must be real dirs, never folded symlinks)
for dir_check in "$HOME/.gemini" "$GLOBAL_DIR" "$GLOBAL_DIR/skills"; do
    if [ -L "$dir_check" ]; then
        echo "❌ FOLDED SYMLINK: $dir_check is a symlink instead of a real directory (run: ./bootstrap.sh --antigravity)"
        broken=$((broken + 1))
    elif [ ! -d "$dir_check" ]; then
        echo "❌ MISSING DIR: $dir_check does not exist (run: ./bootstrap.sh --antigravity)"
        broken=$((broken + 1))
    fi
done

# 1. Check top-level entries (shopt dotglob to include dotfiles like .migrated)
shopt -s nullglob dotglob
for entry in "$GLOBAL_DIR"/*; do
    name=$(basename "$entry")

    if is_exception "$name" || [[ "$name" == *.backup.* ]]; then
        continue
    fi

    if [ -L "$entry" ]; then
        target=$(readlink "$entry")
        if [ -e "$entry" ]; then
            echo "✅ LINKED: $name → $target"
            ok=$((ok + 1))
        else
            echo "❌ BROKEN: $name → $target (target does not exist)"
            broken=$((broken + 1))
        fi
    else
        echo "⚠️  ORPHAN: $name (not symlinked — should be in dotfiles)"
        orphans=$((orphans + 1))
    fi
done
shopt -u dotglob

# 2. Verify all shared skills from dotfiles are linked in ~/.gemini/config/skills/
if [ -d "$DOTFILES_DIR/skills" ]; then
    for skill_dir in "$DOTFILES_DIR/skills"/*/; do
        [ -d "$skill_dir" ] || continue
        skill_name=$(basename "$skill_dir")
        global_skill="$GLOBAL_DIR/skills/$skill_name"
        if [ -L "$global_skill" ] && [ -e "$global_skill" ]; then
            target=$(readlink "$global_skill")
            echo "✅ LINKED: skills/$skill_name → $target"
            ok=$((ok + 1))
        elif [ -L "$global_skill" ]; then
            target=$(readlink "$global_skill")
            echo "❌ BROKEN: skills/$skill_name → $target"
            broken=$((broken + 1))
        else
            echo "⚠️  MISSING LINK: skills/$skill_name (run: cd ~/dotfiles-ubuntu && stow -t ~ -R antigravity)"
            orphans=$((orphans + 1))
        fi
    done
fi

echo ""
echo "─── Summary ───"
echo "  Linked:  $ok"
echo "  Orphans: $orphans"
echo "  Broken:  $broken"

if [ "$orphans" -gt 0 ] || [ "$broken" -gt 0 ]; then
    echo ""
    echo "Action: Move orphans to $DOTFILES_DIR and run 'cd ~/dotfiles-ubuntu && stow -t ~ -R antigravity'."
    exit 1
fi

echo "  Status:  All global config is properly persisted ✅"
exit 0
