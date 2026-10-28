#!/usr/bin/env bash
# layer-subtree.sh — Orchestrate vertical upstream fork sync and horizontal
# git subtree context layers (layers/<layer-name>/) for dotfiles-ubuntu.
#
# Subcommands:
#   list                                          List mounted subtree layers in layers/
#   add <layer-name> <repo-url> [branch]          Mount a secondary dotfiles fork under layers/<layer-name>
#   pull <layer-name> [repo-url] [branch]         Pull latest changes into layers/<layer-name> (--squash)
#   pull-all                                      Pull latest changes across all mounted layers/* subtrees
#   push <layer-name> [repo-url] <target-branch>  Push local layer improvements upstream to <target-branch>
#   sync-upstream [remote-or-url] [branch]        Sync root repository vertically from its parent upstream fork
#
# Flags:
#   -n, --dry-run   Print git commands without executing them
#   -h, --help      Show usage information
#   -v, --version   Show version string

set -euo pipefail
export LC_ALL=C

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="${DOTFILES_REPO_DIR:-$(cd "$SCRIPT_DIR/.." && pwd)}"
VERSION_STR="$(tr -d '[:space:]' < "$REPO_DIR/VERSION" 2>/dev/null || echo "unknown")"

DRY_RUN=false

usage() {
  cat <<EOF
Usage: ./scripts/layer-subtree.sh [--dry-run] <command> [args...]

Orchestrate vertical upstream fork synchronization and horizontal git subtree
context layers (layers/<layer-name>/) across corporate, departmental, team,
and service-node repositories.

Commands:
  list
      List all mounted subtree layers discovered under layers/*/.

  add <layer-name> <repo-url> [branch]
      Mount a dotfiles-ubuntu fork into layers/<layer-name> via 'git subtree add --squash'.
      Default branch: master.

  pull <layer-name> [repo-url] [branch]
      Update an existing layers/<layer-name> subtree via 'git subtree pull --squash'.
      If [repo-url] or [branch] are omitted, resolves them from layers/<layer-name>/system/mcp-layer.json.

  pull-all
      Update all mounted subtrees under layers/*/ using each layer's upstream_layer metadata.

  push <layer-name> [repo-url] <target-branch>
      Promote improvements from layers/<layer-name> back to its upstream repository
      branch via 'git subtree push'. If [repo-url] is omitted, resolves it from
      layers/<layer-name>/system/mcp-layer.json.

  sync-upstream [remote-or-url] [branch]
      Synchronize the root repository vertically from its parent fork (defaults to
      upstream_layer.repository in system/mcp-layer.json and branch 'master').

Options:
  -n, --dry-run   Print the resolved git command without mutating the repository
  -h, --help      Show this help message and exit
  -v, --version   Show version information and exit
EOF
}

validate_layer_name() {
  local name="$1"
  if [[ ! "$name" =~ ^[a-z0-9]+(-[a-z0-9]+)*$ ]]; then
    echo "❌ Invalid layer name '$name': must be kebab-case (e.g., 'dept-security', 'svc-payments')." >&2
    exit 1
  fi
}

run_cmd() {
  if [ "$DRY_RUN" = true ]; then
    echo "[dry-run] $*"
  else
    "$@"
  fi
}

resolve_layer_upstream_url() {
  local name="$1"
  python3 - "$REPO_DIR/layers/$name/system/mcp-layer.json" <<'PYEOF'
import json
import sys
from pathlib import Path

p = Path(sys.argv[1])
if p.is_file():
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        print(d.get("upstream_layer", {}).get("repository", ""))
    except Exception:
        print("")
else:
    print("")
PYEOF
}

resolve_layer_upstream_branch() {
  local name="$1"
  python3 - "$REPO_DIR/layers/$name/system/mcp-layer.json" <<'PYEOF'
import json
import sys
from pathlib import Path

p = Path(sys.argv[1])
if p.is_file():
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        print(d.get("upstream_layer", {}).get("branch", "master") or "master")
    except Exception:
        print("master")
else:
    print("master")
PYEOF
}

while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    -v|--version)
      echo "dotfiles-ubuntu layer-subtree v$VERSION_STR"
      exit 0
      ;;
    -n|--dry-run)
      DRY_RUN=true
      shift
      ;;
    -*)
      echo "❌ Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
    *)
      break
      ;;
  esac
done

SUBCOMMAND="${1:-}"
if [ -z "$SUBCOMMAND" ]; then
  echo "❌ Missing subcommand (expected: list, add, pull, push, or sync-upstream)." >&2
  usage >&2
  exit 1
fi
shift

cd "$REPO_DIR"

case "$SUBCOMMAND" in
  list)
    echo "═══ Mounted Context Subtree Layers (layers/*) ═══"
    python3 - <<'PYEOF'
import json
from pathlib import Path

repo = Path(".")
layers_dir = repo / "layers"
found = []
if layers_dir.is_dir():
    for sub in sorted(layers_dir.iterdir()):
        if not sub.is_dir() or sub.name.startswith("."):
            continue
        manifest_path = sub / "system" / "mcp-layer.json"
        layer_id = sub.name
        layer_role = "unknown"
        mcps = 0
        if manifest_path.is_file():
            try:
                data = json.loads(manifest_path.read_text(encoding="utf-8"))
                layer_id = data.get("layer_id", layer_id)
                layer_role = data.get("layer_role", layer_role)
                mcps = len(data.get("federated_mcps", []))
            except Exception:
                pass
        ver_file = sub / "VERSION"
        ver = ver_file.read_text(encoding="utf-8").strip() if ver_file.is_file() else "unknown"
        found.append((sub.name, layer_id, layer_role, ver, mcps))

if not found:
    print("  (no subtree layers currently mounted in layers/)")
else:
    for name, lid, role, ver, mcps in found:
        print(f"  • layers/{name}  [id={lid}, role={role}, v{ver}, federated_mcps={mcps}]")
PYEOF
    ;;

  add)
    if [ $# -lt 2 ]; then
      echo "❌ Usage: ./scripts/layer-subtree.sh add <layer-name> <repo-url> [branch]" >&2
      exit 1
    fi
    LAYER_NAME="$1"
    REPO_URL="$2"
    BRANCH="${3:-master}"
    validate_layer_name "$LAYER_NAME"
    TARGET_PREFIX="layers/$LAYER_NAME"
    if [ -e "$REPO_DIR/$TARGET_PREFIX" ]; then
      echo "❌ Layer '$TARGET_PREFIX' already exists. Use 'pull' to update it." >&2
      exit 1
    fi
    echo "➕ Mounting subtree layer '$LAYER_NAME' into $TARGET_PREFIX from $REPO_URL ($BRANCH)..."
    run_cmd git subtree add --prefix="$TARGET_PREFIX" "$REPO_URL" "$BRANCH" --squash
    ;;

  pull)
    if [ $# -lt 1 ]; then
      echo "❌ Usage: ./scripts/layer-subtree.sh pull <layer-name> [repo-url] [branch]" >&2
      exit 1
    fi
    LAYER_NAME="$1"
    validate_layer_name "$LAYER_NAME"
    TARGET_PREFIX="layers/$LAYER_NAME"
    if [ ! -d "$REPO_DIR/$TARGET_PREFIX" ] && [ "$DRY_RUN" = false ]; then
      echo "❌ Mounted layer '$TARGET_PREFIX' does not exist. Use 'add' first." >&2
      exit 1
    fi
    DEFAULT_LAYER_URL="$(resolve_layer_upstream_url "$LAYER_NAME")"
    DEFAULT_LAYER_BRANCH="$(resolve_layer_upstream_branch "$LAYER_NAME")"
    REPO_URL="${2:-$DEFAULT_LAYER_URL}"
    BRANCH="${3:-$DEFAULT_LAYER_BRANCH}"
    if [ -z "$REPO_URL" ]; then
      echo "❌ No repository URL provided and none found in $TARGET_PREFIX/system/mcp-layer.json." >&2
      exit 1
    fi
    echo "🔄 Pulling latest subtree changes for '$TARGET_PREFIX' from $REPO_URL ($BRANCH)..."
    run_cmd git subtree pull --prefix="$TARGET_PREFIX" "$REPO_URL" "$BRANCH" --squash
    ;;

  pull-all)
    echo "═══ Pulling All Mounted Subtree Layers (layers/*) ═══"
    PULLED_COUNT=0
    if [ -d "$REPO_DIR/layers" ]; then
      for sub_dir in "$REPO_DIR/layers"/*/; do
        [ -d "$sub_dir" ] || continue
        LAYER_NAME="$(basename "$sub_dir")"
        [[ "$LAYER_NAME" == .* ]] && continue
        LAYER_URL="$(resolve_layer_upstream_url "$LAYER_NAME")"
        LAYER_BRANCH="$(resolve_layer_upstream_branch "$LAYER_NAME")"
        if [ -z "$LAYER_URL" ]; then
          echo "❌ Layer 'layers/$LAYER_NAME' is missing upstream_layer.repository in system/mcp-layer.json." >&2
          exit 1
        fi
        echo "🔄 Pulling 'layers/$LAYER_NAME' from $LAYER_URL ($LAYER_BRANCH)..."
        run_cmd git subtree pull --prefix="layers/$LAYER_NAME" "$LAYER_URL" "$LAYER_BRANCH" --squash
        PULLED_COUNT=$((PULLED_COUNT + 1))
      done
    fi
    if [ "$PULLED_COUNT" -eq 0 ]; then
      echo "  (no subtree layers currently mounted in layers/ — nothing to pull)"
    fi
    ;;

  push)
    if [ $# -lt 2 ]; then
      echo "❌ Usage: ./scripts/layer-subtree.sh push <layer-name> [repo-url] <target-branch>" >&2
      exit 1
    fi
    LAYER_NAME="$1"
    validate_layer_name "$LAYER_NAME"
    TARGET_PREFIX="layers/$LAYER_NAME"
    if [ ! -d "$REPO_DIR/$TARGET_PREFIX" ] && [ "$DRY_RUN" = false ]; then
      echo "❌ Mounted layer '$TARGET_PREFIX' does not exist." >&2
      exit 1
    fi
    if [ $# -eq 2 ]; then
      REPO_URL="$(resolve_layer_upstream_url "$LAYER_NAME")"
      TARGET_BRANCH="$2"
    else
      REPO_URL="$2"
      TARGET_BRANCH="$3"
    fi
    if [ -z "$REPO_URL" ]; then
      echo "❌ No repository URL provided and none found in $TARGET_PREFIX/system/mcp-layer.json." >&2
      exit 1
    fi
    echo "⬆️  Pushing subtree '$TARGET_PREFIX' upstream to $REPO_URL ($TARGET_BRANCH)..."
    run_cmd git subtree push --prefix="$TARGET_PREFIX" "$REPO_URL" "$TARGET_BRANCH"
    ;;

  sync-upstream)
    DEFAULT_URL="$(python3 -c 'import json, pathlib; p = pathlib.Path("system/mcp-layer.json"); d = json.loads(p.read_text()) if p.is_file() else {}; print(d.get("upstream_layer", {}).get("repository", ""))')"
    DEFAULT_BRANCH="$(python3 -c 'import json, pathlib; p = pathlib.Path("system/mcp-layer.json"); d = json.loads(p.read_text()) if p.is_file() else {}; print(d.get("upstream_layer", {}).get("branch", "master"))')"
    UPSTREAM_SOURCE="${1:-$DEFAULT_URL}"
    UPSTREAM_BRANCH="${2:-$DEFAULT_BRANCH}"
    if [ -z "$UPSTREAM_SOURCE" ]; then
      echo "❌ No upstream repository specified and none found in system/mcp-layer.json." >&2
      exit 1
    fi
    echo "⬇️  Synchronizing root repository from upstream $UPSTREAM_SOURCE ($UPSTREAM_BRANCH)..."
    run_cmd git pull --ff-only "$UPSTREAM_SOURCE" "$UPSTREAM_BRANCH"
    ;;

  *)
    echo "❌ Unknown subcommand: $SUBCOMMAND" >&2
    usage >&2
    exit 1
    ;;
esac
