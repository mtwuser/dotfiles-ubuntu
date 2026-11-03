#!/usr/bin/env bash
# layer-subtree.sh — Orchestrate vertical upstream fork sync and horizontal
# git subtree context layers (layers/<layer-name>/) for dotfiles-ubuntu.

set -euo pipefail
export LC_ALL=C

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEFAULT_REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
if [ -z "${DOTFILES_REPO_DIR:-}" ] && [ -f "$PWD/system/mcp-layer.json" ]; then REPO_DIR="$PWD"; else REPO_DIR="${DOTFILES_REPO_DIR:-$DEFAULT_REPO_DIR}"; fi
VERSION_STR="$({ tr -d '[:space:]' < "$REPO_DIR/VERSION"; } 2>/dev/null || echo "unknown")"
DRY_RUN=false

usage() {
  cat <<EOF
Usage: ./scripts/layer-subtree.sh [--dry-run] <command> [args...]

Orchestrate vertical upstream fork synchronization and horizontal git subtree
context layers (layers/<layer-name>/) across corporate, departmental, squad,
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
      branch via 'git subtree push'.
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
  if [ "$DRY_RUN" = true ]; then echo "[dry-run] $*"; else "$@"; fi
}

run_subtree_pull() {
  local prefix="$1" repo_url="$2" branch="$3" unmerged
  if [ "$DRY_RUN" = true ]; then echo "[dry-run] git subtree pull --prefix=$prefix $repo_url $branch --squash"; return 0; fi
  if ! git subtree pull --prefix="$prefix" "$repo_url" "$branch" --squash; then
    unmerged="$(git diff --name-only --diff-filter=U)"
    if [ -n "$unmerged" ] && ! echo "$unmerged" | grep -qv "^${prefix}/"; then
      echo "⚠️  Reconciling subtree conflict in '$prefix/' using authoritative child state..."
      git checkout --theirs "$prefix/" && git add "$prefix/" && git commit --no-edit
    else
      return 1
    fi
  fi
}

subtree_manifest_helper() {
  python3 - "$REPO_DIR" "$@" <<'PYEOF'
import json, subprocess, sys
from pathlib import Path

repo_dir, mode = Path(sys.argv[1]), sys.argv[2]
name = sys.argv[3] if len(sys.argv) > 3 else ""

def load_json(p: Path) -> dict:
    try:
        return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}
    except Exception:
        return {}

if mode == "url":
    rm = load_json(repo_dir / "system/mcp-layer.json")
    for entry in rm.get("mounted_layers", []):
        if isinstance(entry, dict) and entry.get("name") in (name, f"layers/{name}") and entry.get("repository"):
            print(entry["repository"])
            sys.exit(0)
    proc = subprocess.run(["git", "-C", str(repo_dir), "remote", "get-url", name], capture_output=True, text=True, check=False)
    if proc.returncode == 0 and proc.stdout.strip():
        print(proc.stdout.strip())
        sys.exit(0)
    d = load_json(repo_dir / "layers" / name / "system/mcp-layer.json")
    print(d.get("repository") or d.get("upstream_layer", {}).get("repository", ""))
elif mode == "branch":
    d = load_json(repo_dir / "layers" / name / "system/mcp-layer.json")
    print(d.get("upstream_layer", {}).get("branch", "master") or "master")
elif mode == "root-url":
    print(load_json(repo_dir / "system/mcp-layer.json").get("upstream_layer", {}).get("repository", ""))
elif mode == "root-branch":
    print(load_json(repo_dir / "system/mcp-layer.json").get("upstream_layer", {}).get("branch", "master"))
elif mode == "list":
    layers_dir, found = repo_dir / "layers", []
    if layers_dir.is_dir():
        for sub in sorted(layers_dir.iterdir()):
            if not sub.is_dir() or sub.name.startswith("."):
                continue
            d = load_json(sub / "system/mcp-layer.json")
            lid, role = d.get("layer_id", sub.name), d.get("layer_role", "unknown")
            mcps = len(d.get("federated_mcps", []))
            vf = sub / "VERSION"
            ver = vf.read_text(encoding="utf-8").strip() if vf.is_file() else "unknown"
            found.append((sub.name, lid, role, ver, mcps))
    if not found:
        print("  (no subtree layers currently mounted in layers/)")
    for sname, lid, role, ver, mcps in found:
        print(f"  • layers/{sname}  [id={lid}, role={role}, v{ver}, federated_mcps={mcps}]")
PYEOF
}

while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    -v|--version) echo "dotfiles-ubuntu layer-subtree v$VERSION_STR"; exit 0 ;;
    -n|--dry-run) DRY_RUN=true; shift ;;
    -*) echo "❌ Unknown option: $1" >&2; usage >&2; exit 1 ;;
    *) break ;;
  esac
done

SUBCOMMAND="${1:-}"
if [ -z "$SUBCOMMAND" ]; then
  echo "❌ Missing subcommand (expected: list, add, pull, pull-all, push, or sync-upstream)." >&2
  usage >&2
  exit 1
fi
shift

cd "$REPO_DIR"
git update-index -q --ignore-submodules --refresh 2>/dev/null || true

case "$SUBCOMMAND" in
  list)
    echo "═══ Mounted Context Subtree Layers (layers/*) ═══"
    subtree_manifest_helper list
    ;;
  add)
    if [ $# -lt 2 ]; then
      echo "❌ Usage: ./scripts/layer-subtree.sh add <layer-name> <repo-url> [branch]" >&2
      exit 1
    fi
    LAYER_NAME="$1"; REPO_URL="$2"; BRANCH="${3:-master}"
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
    REPO_URL="${2:-$(subtree_manifest_helper url "$LAYER_NAME")}"
    BRANCH="${3:-$(subtree_manifest_helper branch "$LAYER_NAME")}"
    if [ -z "$REPO_URL" ]; then
      echo "❌ No repository URL provided and none found in $TARGET_PREFIX/system/mcp-layer.json." >&2
      exit 1
    fi
    echo "🔄 Pulling latest subtree changes for '$TARGET_PREFIX' from $REPO_URL ($BRANCH)..."
    run_subtree_pull "$TARGET_PREFIX" "$REPO_URL" "$BRANCH"
    ;;
  pull-all)
    echo "═══ Pulling All Mounted Subtree Layers (layers/*) ═══"
    PULLED_COUNT=0
    if [ -d "$REPO_DIR/layers" ]; then
      for sub_dir in "$REPO_DIR/layers"/*/; do
        [ -d "$sub_dir" ] || continue
        LAYER_NAME="$(basename "$sub_dir")"
        [[ "$LAYER_NAME" == .* ]] && continue
        LAYER_URL="$(subtree_manifest_helper url "$LAYER_NAME")"
        LAYER_BRANCH="$(subtree_manifest_helper branch "$LAYER_NAME")"
        if [ -z "$LAYER_URL" ]; then
          echo "❌ Layer 'layers/$LAYER_NAME' is missing upstream_layer.repository in system/mcp-layer.json." >&2
          exit 1
        fi
        echo "🔄 Pulling 'layers/$LAYER_NAME' from $LAYER_URL ($LAYER_BRANCH)..."
        run_subtree_pull "layers/$LAYER_NAME" "$LAYER_URL" "$LAYER_BRANCH"
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
      REPO_URL="$(subtree_manifest_helper url "$LAYER_NAME")"; TARGET_BRANCH="$2"
    else
      REPO_URL="$2"; TARGET_BRANCH="$3"
    fi
    if [ -z "$REPO_URL" ]; then
      echo "❌ No repository URL provided and none found in $TARGET_PREFIX/system/mcp-layer.json." >&2
      exit 1
    fi
    echo "⬆️  Pushing subtree '$TARGET_PREFIX' upstream to $REPO_URL ($TARGET_BRANCH)..."
    run_cmd git subtree push --prefix="$TARGET_PREFIX" "$REPO_URL" "$TARGET_BRANCH"
    ;;
  sync-upstream)
    UPSTREAM_SOURCE="${1:-$(subtree_manifest_helper root-url)}"
    UPSTREAM_BRANCH="${2:-$(subtree_manifest_helper root-branch)}"
    if [ -z "$UPSTREAM_SOURCE" ]; then
      echo "❌ No upstream repository specified and none found in system/mcp-layer.json." >&2
      exit 1
    fi
    echo "⬇️  Synchronizing root repository from upstream $UPSTREAM_SOURCE ($UPSTREAM_BRANCH)..."
    run_cmd git pull --ff-only "$UPSTREAM_SOURCE" "$UPSTREAM_BRANCH"
    ;;
  *)
    echo "❌ Unknown subcommand: $SUBCOMMAND" >&2; usage >&2; exit 1 ;;
esac
