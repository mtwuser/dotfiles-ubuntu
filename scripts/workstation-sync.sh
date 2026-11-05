#!/usr/bin/env bash
# workstation-sync.sh — Declarative Workstation Setup, Runtime Sync & Open-Source Release Publisher
#
# Manages local device preferences (~/.config/dotfiles-ubuntu/workstation.conf),
# supports private personal workstation forks (mode=private) and passive read-only
# clones (mode=readonly), enforces upstream read-only push guards, and exports
# tracker-free Open-Source releases (--publish-oss).
#
# Usage: ./scripts/workstation-sync.sh [sync | setup | status | publish-oss | --auto | --help | --version]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
VERSION_STR="$({ tr -d '[:space:]' < "$REPO_DIR/VERSION"; } 2>/dev/null || echo "unknown")"

CONFIG_FILE="${DOTFILES_WORKSTATION_CONF:-$HOME/.config/dotfiles-ubuntu/workstation.conf}"
STAMP_DIR="${XDG_RUNTIME_DIR:-/tmp}"
USER_UID="${UID:-$(id -u)}"
STAMP_FILE="${DOTFILES_SYNC_STAMP:-$STAMP_DIR/dotfiles-ubuntu-${USER_UID}.synced}"
READONLY_PUSH_GUARD="VALIDATION_BLOCKED_READONLY_RUNTIME"
DEFAULT_OSS_UPSTREAM="https://github.com/mtwuser/dotfiles-ubuntu.git"

usage() {
  cat <<EOF
Usage: ./scripts/workstation-sync.sh [COMMAND] [OPTIONS]

Commands:
  sync, --sync               Pull latest fast-forward updates, apply global profile, and re-stow (default)
  setup, --setup             Configure ~/.config/dotfiles-ubuntu/workstation.conf and initialize runtime
  status, --status           Print workstation configuration and runtime status as JSON
  publish-oss, --publish-oss Export tracker-free release snapshot from dev repo to Open-Source upstream
  --auto                     Boot-throttled quiet sync invoked automatically from ~/.bashrc
  -v, --version              Show version information
  -h, --help                 Show this help message

Setup Options:
  --mode <private|readonly|mutable>                     Workstation runtime mode (default: readonly)
  --profile <human-base|science|technical|business|full> Global AGENTS.md profile (default: human-base)
  --auto-sync <boot|always|off>                  Shell startup sync policy (default: boot)
  --dev-repo <path>                              Dedicated development clone path
  --no-sync                                      Write configuration without running sync

Publish-OSS Options:
  --dry-run                                      Verify and stage tracker-free Open-Source release without pushing
  --create-pr                                    Push sanitized proposal branch (contrib/*) for Pull Request review
  --release-version <X.Y.Z>                      Explicit new SemVer required for owner release to master
  --remote <name-or-url>                         Target Open-Source remote (default: upstream)
EOF
}

DOTFILES_WORKSTATION_MODE="${DOTFILES_WORKSTATION_MODE:-readonly}"
DOTFILES_GLOBAL_PROFILE="${DOTFILES_GLOBAL_PROFILE:-human-base}"
DOTFILES_AUTO_SYNC="${DOTFILES_AUTO_SYNC:-boot}"
DOTFILES_DEV_REPO_DIR="${DOTFILES_DEV_REPO_DIR:-}"

if [ -f "$CONFIG_FILE" ]; then
  # shellcheck disable=SC1090
  . "$CONFIG_FILE"
fi
if [ -n "${DOTFILES_RUNTIME_DIR:-}" ] && [ -d "$DOTFILES_RUNTIME_DIR" ]; then
  RUNTIME_DIR="$(cd "$DOTFILES_RUNTIME_DIR" && pwd)"
else
  REPO_BASE="$(basename "$REPO_DIR")"
  if [[ "$REPO_BASE" == dev-* ]] && [ -d "$HOME/${REPO_BASE#dev-}" ]; then
    RUNTIME_DIR="$(cd "$HOME/${REPO_BASE#dev-}" && pwd)"
  else
    RUNTIME_DIR="$REPO_DIR"
  fi
fi

detect_dev_repo() {
  if [ -n "$DOTFILES_DEV_REPO_DIR" ] && [ -f "$DOTFILES_DEV_REPO_DIR/system/mcp-layer.json" ]; then
    echo "$DOTFILES_DEV_REPO_DIR"; return
  fi
  local candidate oss_base="${DEFAULT_OSS_UPSTREAM##*/}"
  oss_base="${oss_base%.git}"
  for candidate in "$HOME/Projects/dev-$(basename "$RUNTIME_DIR")" "$HOME/Projects/dev-${oss_base}"; do
    if [ -f "$candidate/system/mcp-layer.json" ]; then
      echo "$candidate"; return
    fi
  done
  echo ""
}

copy_sanitized_engine_tree() {
  python3 - "$1" "$2" "${3:-0}" <<'PY'
import json, pathlib, shutil, subprocess, sys
src, dst, preserve_id = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), sys.argv[3] == "1"
EXCLUDED = {"WORKTASK.md", "WORKROAD.md", "ROADMAP.md", "BACKLOG.md", "WORKVALI.md"}
PRESERVED_KEYS = ("layer_id", "layer_role", "entity_kind", "precedence", "description", "upstream_layer", "governing_root_id", "mounted_layers", "default_stack_templates", "surface_bindings", "layer_authority", "global_profile", "human_stack")
dst_manifest = dst / "system" / "mcp-layer.json"
saved_id = {k: v for k, v in json.loads(dst_manifest.read_text(encoding="utf-8")).items() if k in PRESERVED_KEYS} if (preserve_id and dst_manifest.is_file()) else {}
tracked = [r for r in subprocess.check_output(["git", "-C", str(src), "ls-files", "-z"]).decode("utf-8").split("\0") if r]
if (dst / ".git").exists():
    dst_tracked = set(subprocess.check_output(["git", "-C", str(dst), "ls-files", "-z"]).decode("utf-8").split("\0")) - {""}
    for stale in (dst_tracked - set(tracked)):
        if stale in EXCLUDED or stale.startswith(("roadmaps/", ".agents/", "corporate/", "layers/")): continue
        sf = dst / stale
        if sf.exists() or sf.is_symlink(): sf.unlink()
        p = sf.parent
        while p != dst and p.exists() and not any(p.iterdir()): p.rmdir(); p = p.parent
for rel in tracked:
    if rel in EXCLUDED or rel.startswith(("roadmaps/", ".agents/", "corporate/", "layers/")): continue
    s_file, d_file = src / rel, dst / rel
    if s_file.exists() or s_file.is_symlink():
        d_file.parent.mkdir(parents=True, exist_ok=True)
        if d_file.exists() or d_file.is_symlink(): d_file.unlink()
        shutil.copy2(s_file, d_file, follow_symlinks=False)
if dst_manifest.is_file():
    data = json.loads(dst_manifest.read_text(encoding="utf-8"))
    src_base = {b.get("binding_id"): b for b in data.get("surface_bindings", []) if isinstance(b, dict) and b.get("binding_id") == "universal-engineering-baseline"}
    if preserve_id and saved_id:
        data.update(saved_id)
        if src_base and isinstance(data.get("surface_bindings"), list):
            data["surface_bindings"] = [src_base.get(b.get("binding_id"), b) if isinstance(b, dict) else b for b in data["surface_bindings"]]
        if (data.get("entity_kind") == "individual" or int(data.get("precedence", 10)) >= 85) and data.get("global_profile", "human-base") == "human-base" and "Corporate / Workstation Baseline" in str(data.get("description", "")):
            data["description"] = f"Personal Sovereign Root 0 Workstation Hub ({data.get('layer_id', dst.name)})"
            data["default_stack_templates"] = []
            data["surface_bindings"] = [b for b in data.get("surface_bindings", []) if isinstance(b, dict) and not any("fastapi-hexagonal/" in str(r) for r in [*b.get("rule_files", []), *b.get("canonical_templates", [])])]
    elif not preserve_id:
        data.update({"layer_id": "dotfiles-ubuntu-default", "layer_role": "workstation", "entity_kind": "open-source", "precedence": 10})
    dst_manifest.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
PY
}

apply_push_guard() {
  local mode="$1" dev_dir
  dev_dir="$(detect_dev_repo)"
  for candidate_dev in "$dev_dir" "$REPO_DIR"; do
    if [ -n "$candidate_dev" ] && [ -d "$candidate_dev/.git" ]; then
      if [ "$candidate_dev" = "$dev_dir" ] || [[ "$(basename "$candidate_dev")" == dev-* ]]; then
        local dev_guard
        dev_guard="$(git -C "$candidate_dev" config --get remote.origin.pushurl 2>/dev/null || true)"
        if [ "$dev_guard" = "$READONLY_PUSH_GUARD" ]; then
          git -C "$candidate_dev" config --unset remote.origin.pushurl 2>/dev/null || true
        fi
        if git -C "$candidate_dev" config --get remote.upstream.url >/dev/null 2>&1; then
          git -C "$candidate_dev" config remote.upstream.pushurl "$READONLY_PUSH_GUARD" 2>/dev/null || true
        fi
      fi
    fi
  done
  if [ ! -d "$RUNTIME_DIR/.git" ] || [ "$RUNTIME_DIR" = "$dev_dir" ] || [[ "$(basename "$RUNTIME_DIR")" == dev-* ]]; then
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
    if git -C "$RUNTIME_DIR" config --get remote.upstream.url >/dev/null 2>&1; then
      git -C "$RUNTIME_DIR" config remote.upstream.pushurl "$READONLY_PUSH_GUARD" 2>/dev/null || true
    fi
  fi
}

reset_engine_overlay() {
  local target_dir="$1"
  [ -d "$target_dir/.git" ] || return 0
  git -C "$target_dir" checkout -- scripts antigravity bash git templates docs tests bootstrap.sh audit.sh Makefile VERSION pyproject.toml README.md CHANGELOG.md 2>/dev/null || true
}

merge_upstream_git_preserving_identity() {
  local target_dir="$1" oss_url="$2" saved_id
  [ -d "$target_dir/.git" ] || return 0
  reset_engine_overlay "$target_dir"
  saved_id="$(python3 - "$target_dir/system/mcp-layer.json" <<'PY'
import json, pathlib, sys
p = pathlib.Path(sys.argv[1])
KEYS = ("layer_id", "layer_role", "entity_kind", "precedence", "description", "upstream_layer", "governing_root_id", "mounted_layers", "default_stack_templates", "surface_bindings", "layer_authority", "global_profile", "human_stack")
d = json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}
print(json.dumps({k: d[k] for k in KEYS if k in d}))
PY
)"
  GIT_TERMINAL_PROMPT=0 git -C "$target_dir" fetch "$oss_url" --tags -q 2>/dev/null || return 0
  if ! git -C "$target_dir" merge --ff-only FETCH_HEAD -q 2>/dev/null; then
    git -C "$target_dir" merge -X theirs --no-commit --no-ff FETCH_HEAD -q 2>/dev/null || true
    python3 - "$target_dir/system/mcp-layer.json" "$saved_id" <<'PY'
import json, pathlib, sys
p, saved = pathlib.Path(sys.argv[1]), json.loads(sys.argv[2])
if p.is_file() and saved:
    d = json.loads(p.read_text(encoding="utf-8"))
    d.update(saved)
    p.write_text(json.dumps(d, indent=2) + "\n", encoding="utf-8")
PY
    git -C "$target_dir" add system/mcp-layer.json 2>/dev/null || true
    git -C "$target_dir" commit --no-edit -q 2>/dev/null || git -C "$target_dir" commit -m "chore(sync): merge upstream Open-Source release" -q 2>/dev/null || true
  fi
}

seed_personal_hub_trackers() {
  local target_dir="$1" node_id
  node_id="$(python3 -c 'import json,pathlib,sys; p=pathlib.Path(sys.argv[1])/"system/mcp-layer.json"; print(json.loads(p.read_text()).get("layer_id") or pathlib.Path(sys.argv[1]).name if p.is_file() else pathlib.Path(sys.argv[1]).name)' "$target_dir" 2>/dev/null || basename "$target_dir")"
  [ -f "$target_dir/WORKTASK.md" ] || cat > "$target_dir/WORKTASK.md" <<EOF
# Active Work Tasks — ${node_id} (private:individual:root-0)

> Personal Sovereign Root 0 Hub task ledger for ${node_id}.

## Active & Queued Tasks

- [x] **[PC-INIT-001]**: Initialize personal sovereign Root 0 Hub (${node_id}).
EOF
  [ -f "$target_dir/WORKROAD.md" ] || cat > "$target_dir/WORKROAD.md" <<EOF
# Personal Sovereign Roadmap — ${node_id} (private:individual:root-0)

## Phase 1: Personal Workstation & Sub-Layer Hub Orchestration — Active
- Maintain sovereign personal context, Human-Stack profile, and cross-project consultation via \`make consult LAYER=workstation\`.
EOF
  [ -f "$target_dir/BACKLOG.md" ] || cat > "$target_dir/BACKLOG.md" <<EOF
# Personal Backlog — ${node_id} (private:individual:root-0)

- [ ] **[BKL-PC-001]**: Mount personal or domain sub-layers under \`layers/\` as needed.
EOF
  if [ "$node_id" != "dotfiles-ubuntu" ]; then
    for trk in WORKTASK.md WORKROAD.md BACKLOG.md; do
      [ -f "$target_dir/$trk" ] && grep -q "dotfiles-ubuntu (private:individual:root-0)" "$target_dir/$trk" && \
        sed -i "s/dotfiles-ubuntu/${node_id}/g" "$target_dir/$trk" || true
    done
  fi
}

run_sync() {
  local quiet_unchanged="${1:-0}" old_ver new_ver dev_dir
  old_ver="$({ tr -d '[:space:]' < "$RUNTIME_DIR/VERSION"; } 2>/dev/null || echo "unknown")"
  dev_dir="$(detect_dev_repo)"
  if [ "$DOTFILES_WORKSTATION_MODE" = "private" ] && [ -f "$RUNTIME_DIR/system/mcp-layer.json" ]; then
    local branch_prof
    branch_prof="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("global_profile",""))' "$RUNTIME_DIR/system/mcp-layer.json" 2>/dev/null || true)"
    [ -n "$branch_prof" ] && DOTFILES_GLOBAL_PROFILE="$branch_prof"
  fi

  apply_push_guard "$DOTFILES_WORKSTATION_MODE"

  if [ -d "$RUNTIME_DIR/.git" ]; then
    if [ "$DOTFILES_WORKSTATION_MODE" = "readonly" ]; then
      git -C "$RUNTIME_DIR" checkout -- antigravity/.gemini/config/AGENTS.md 2>/dev/null || true
    fi
    if [ "${DOTFILES_SKIP_PULL:-0}" != "1" ]; then
      if ! GIT_TERMINAL_PROMPT=0 timeout 4s git -C "$RUNTIME_DIR" pull --ff-only -q 2>/dev/null; then
        if [ "$DOTFILES_WORKSTATION_MODE" = "readonly" ]; then
          local cur_branch
          cur_branch="$(git -C "$RUNTIME_DIR" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "main")"
          GIT_TERMINAL_PROMPT=0 timeout 4s git -C "$RUNTIME_DIR" fetch origin --tags --force -q 2>/dev/null && \
            git -C "$RUNTIME_DIR" reset --hard "origin/$cur_branch" -q 2>/dev/null || true
        fi
      fi
      if git -C "$RUNTIME_DIR" config --get remote.upstream.url >/dev/null 2>&1; then
        merge_upstream_git_preserving_identity "$RUNTIME_DIR" "$(git -C "$RUNTIME_DIR" config --get remote.upstream.url)"
      fi
    fi
    if [ "$DOTFILES_WORKSTATION_MODE" = "private" ] && [ "$RUNTIME_DIR" != "$dev_dir" ] && [[ "$(basename "$RUNTIME_DIR")" != dev-* ]]; then
      seed_personal_hub_trackers "$RUNTIME_DIR"
      [ -x "$RUNTIME_DIR/scripts/layer-config.sh" ] && "$RUNTIME_DIR/scripts/layer-config.sh" apply-project "$RUNTIME_DIR" >/dev/null 2>&1 || true
    fi
    if [ -n "$dev_dir" ] && [ -d "$dev_dir/.git" ] && [ "$dev_dir" != "$RUNTIME_DIR" ]; then
      if git -C "$dev_dir" rev-parse --verify HEAD >/dev/null 2>&1 && git -C "$dev_dir" diff --quiet && git -C "$dev_dir" diff --cached --quiet; then
        copy_sanitized_engine_tree "$dev_dir" "$RUNTIME_DIR" 1
        if [ -x "$RUNTIME_DIR/scripts/layer-config.sh" ]; then
          "$RUNTIME_DIR/scripts/layer-config.sh" set-global-profile "$DOTFILES_GLOBAL_PROFILE" >/dev/null 2>&1 || true
          [ "$DOTFILES_WORKSTATION_MODE" = "private" ] && "$RUNTIME_DIR/scripts/layer-config.sh" apply-project "$RUNTIME_DIR" >/dev/null 2>&1 || true
        fi
        git -C "$RUNTIME_DIR" add -A
        git -C "$RUNTIME_DIR" diff --cached --quiet || \
          git -C "$RUNTIME_DIR" commit -m "chore(sync): synchronize engine from dev ($(git -C "$dev_dir" rev-parse --short HEAD))" -q 2>/dev/null || true
      fi
    fi
  fi

  new_ver="$({ tr -d '[:space:]' < "$RUNTIME_DIR/VERSION"; } 2>/dev/null || echo "unknown")"
  [ -x "$RUNTIME_DIR/scripts/layer-config.sh" ] && "$RUNTIME_DIR/scripts/layer-config.sh" set-global-profile "$DOTFILES_GLOBAL_PROFILE" >/dev/null

  if [ "${DOTFILES_SKIP_STOW:-0}" != "1" ] && command -v stow >/dev/null 2>&1; then
    for p in "$HOME/.gemini/config/skills" "$HOME/.gemini/config" "$HOME/.gemini" "$HOME/.local/share/applications"; do
      [ -L "$p" ] && rm -f "$p"
    done
    mkdir -p "$HOME/.gemini/config/skills" "$HOME/.local/share/applications" 2>/dev/null || true
    if [ "$(dirname "$RUNTIME_DIR")" = "$HOME" ] && [ "$(basename "$RUNTIME_DIR")" != "dotfiles-ubuntu" ]; then
      if [ ! -e "$HOME/dotfiles-ubuntu" ] || [ -L "$HOME/dotfiles-ubuntu" ] || [ ! -d "$HOME/dotfiles-ubuntu/.git" ]; then
        rm -rf "$HOME/dotfiles-ubuntu" 2>/dev/null || true; ln -snfT "$RUNTIME_DIR" "$HOME/dotfiles-ubuntu"
      fi
    fi
    if [ -x "$RUNTIME_DIR/bootstrap.sh" ] && [ ! -L "$HOME/.gemini/config/AGENTS.md" ]; then
      "$RUNTIME_DIR/bootstrap.sh" --antigravity >/dev/null 2>&1 || true
    fi
    for bf in .bashrc .profile .bash_logout; do
      [ -f "$HOME/$bf" ] && [ ! -L "$HOME/$bf" ] && mv "$HOME/$bf" "$HOME/${bf}.backup.$(date +%Y%m%d)" 2>/dev/null || true
    done
    stow -d "$RUNTIME_DIR" -t "$HOME" -R bash antigravity 2>/dev/null || \
      stow -d "$RUNTIME_DIR" -t "$HOME" -R antigravity 2>/dev/null || true
    [ -x "$RUNTIME_DIR/scripts/layer-config.sh" ] && "$RUNTIME_DIR/scripts/layer-config.sh" set-global-profile "$DOTFILES_GLOBAL_PROFILE" --stow >/dev/null 2>&1 || true
    find "$HOME/.gemini/config/skills" -maxdepth 2 -xtype l -delete 2>/dev/null || true
    find "$HOME/.gemini/config/skills" -mindepth 1 -maxdepth 1 -type d -empty -delete 2>/dev/null || true
    if [ "${DOTFILES_STOW_GIT:-0}" = "1" ] || [ -L "$HOME/.gitconfig" ]; then
      stow -d "$RUNTIME_DIR" -t "$HOME" -R git 2>/dev/null || true
    fi
  fi

  mkdir -p "$(dirname "$STAMP_FILE")" 2>/dev/null || true
  printf '%s\n' "$new_ver" > "$STAMP_FILE" 2>/dev/null || true

  if [ "$quiet_unchanged" = "1" ]; then
    [ "$old_ver" != "$new_ver" ] && echo "✨ [dotfiles-ubuntu] Workstation runtime updated: v${old_ver} -> v${new_ver} (profile: ${DOTFILES_GLOBAL_PROFILE}, mode: ${DOTFILES_WORKSTATION_MODE})" || true
  else
    echo "✅ [dotfiles-ubuntu] Workstation synced (v${new_ver}, profile: ${DOTFILES_GLOBAL_PROFILE}, mode: ${DOTFILES_WORKSTATION_MODE})"
  fi
}

run_publish_oss() {
  local dry_run="$1" remote_arg="$2" create_pr="${3:-0}" rel_ver="${4:-}" target_url="$2" ent_kind
  ent_kind="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("entity_kind","open-source"))' "$REPO_DIR/system/mcp-layer.json" 2>/dev/null || echo "open-source")"
  if [ "$ent_kind" != "open-source" ] || { [ "$DOTFILES_WORKSTATION_MODE" = "private" ] && [ "$REPO_DIR" = "$RUNTIME_DIR" ]; }; then
    echo "❌ [OSS_PERSONAL_REPO_PUBLISH_BLOCKED] Open-Source publication must run from the dev repository (${DOTFILES_DEV_REPO_DIR:-dev-dotfiles-ubuntu}), never from a personal or corporate runtime clone ($REPO_DIR)." >&2; exit 2
  fi
  if git -C "$REPO_DIR" config --get "remote.${remote_arg}.url" >/dev/null 2>&1; then
    target_url="$(git -C "$REPO_DIR" config --get "remote.${remote_arg}.url")"
  elif [ -z "$target_url" ]; then target_url="$DEFAULT_OSS_UPSTREAM"; fi
  if [ "$dry_run" != "1" ] && [ "$create_pr" != "1" ]; then
    if [ -z "$rel_ver" ] || [ "$rel_ver" != "$VERSION_STR" ]; then
      echo "❌ [OSS_PUBLISH_GUARD_BLOCKED] Direct Open-Source publication requires --create-pr (Pull Request) or --release-version $VERSION_STR matching VERSION." >&2; exit 2
    fi
    if awk '/^## \[Unreleased\]/{u=1;next} /^## \[/{u=0} u && /^- /{f=1} END{exit !f}' "${DOTFILES_CHANGELOG_PATH:-$REPO_DIR/CHANGELOG.md}"; then
      echo "❌ [OSS_UNRELEASED_CHANGELOG_BLOCKED] CHANGELOG.md contains unversioned [Unreleased] entries; run /release first or use --create-pr." >&2; exit 2
    fi
    if ! "$REPO_DIR/scripts/layer-config.sh" check-authority "$REPO_DIR" --op release >/dev/null 2>&1 || [ -z "$(git -C "$REPO_DIR" config user.email 2>/dev/null || true)" ]; then
      echo "❌ [UNAUTHORIZED_OSS_RELEASE] Direct release requires Layer Owner authority; external contributors must use --create-pr." >&2; exit 2
    fi
  fi
  if [ "${DOTFILES_SKIP_VERIFY:-0}" != "1" ] && [ -x "$REPO_DIR/scripts/verify-repo.sh" ]; then "$REPO_DIR/scripts/verify-repo.sh"; fi
  local tmp_stage; tmp_stage="$(mktemp -d)"; trap 'rm -rf "$tmp_stage"' RETURN
  if ! git clone -q "$target_url" "$tmp_stage/oss" 2>/dev/null; then
    mkdir -p "$tmp_stage/oss" && git -C "$tmp_stage/oss" init -q -b master && git -C "$tmp_stage/oss" remote add origin "$target_url"
  fi
  if [ "$dry_run" != "1" ] && [ "$create_pr" != "1" ] && git -C "$tmp_stage/oss" rev-parse -q --verify "refs/tags/v${VERSION_STR}" >/dev/null 2>&1; then
    echo "❌ [OSS_TAG_ALREADY_PUBLISHED] Tag v${VERSION_STR} already exists on $target_url; bump VERSION before releasing or use --create-pr." >&2; exit 2
  fi
  git -C "$tmp_stage/oss" rm -rf --ignore-unmatch . >/dev/null 2>&1 || true
  copy_sanitized_engine_tree "$REPO_DIR" "$tmp_stage/oss" 0
  git -C "$tmp_stage/oss" add -A
  if [ "$dry_run" = "1" ]; then
    echo "✅ [publish-oss --dry-run] Clean tracker-free Open-Source release v${VERSION_STR} staged for $target_url"
    git -C "$tmp_stage/oss" status --short; return 0
  fi
  if [ "$create_pr" = "1" ]; then
    local pr_branch="contrib/oss-proposal-v${VERSION_STR}"
    git -C "$tmp_stage/oss" checkout -q -b "$pr_branch"
    git -C "$tmp_stage/oss" diff --cached --quiet || git -C "$tmp_stage/oss" commit -m "chore(contrib): propose sanitized Open-Source updates (v${VERSION_STR})" -q
    git -C "$tmp_stage/oss" push origin "$pr_branch" --force-with-lease
    echo "🚀 [publish-oss --create-pr] Pushed proposal branch $pr_branch to $target_url. Open PR via: gh pr create --base master --head $pr_branch"
    return 0
  fi
  git -C "$tmp_stage/oss" diff --cached --quiet || git -C "$tmp_stage/oss" commit -m "chore(release): publish v${VERSION_STR}" -q
  git -C "$tmp_stage/oss" tag -a "v${VERSION_STR}" -m "Release v${VERSION_STR}"
  git -C "$tmp_stage/oss" push origin HEAD:master --follow-tags
  echo "🚀 [publish-oss] Published clean Open-Source release v${VERSION_STR} to $target_url"
}

CMD="${1:-sync}"
case "$CMD" in
  -v|--version) echo "dotfiles-ubuntu v$VERSION_STR"; exit 0 ;;
  -h|--help) usage; exit 0 ;;
  sync|--sync)
    shift || true; QUIET_FLAG=0
    while [ $# -gt 0 ]; do
      case "$1" in
        --quiet-if-unchanged|--auto) QUIET_FLAG=1; shift ;;
        *) echo "❌ Unknown option: $1" >&2; usage >&2; exit 1 ;;
      esac
    done
    run_sync "$QUIET_FLAG"; exit 0
    ;;
  --auto)
    if [ "$DOTFILES_AUTO_SYNC" = "off" ]; then exit 0; fi
    if [ "$DOTFILES_AUTO_SYNC" = "boot" ] && [ -f "$STAMP_FILE" ]; then exit 0; fi
    run_sync 1; exit 0
    ;;
  publish-oss|--publish-oss)
    shift || true; DRY_RUN=0; REMOTE_ARG="upstream"; CREATE_PR=0; REL_VER=""
    while [ $# -gt 0 ]; do
      case "$1" in
        --dry-run) DRY_RUN=1; shift ;;
        --create-pr) CREATE_PR=1; shift ;;
        --release-version) REL_VER="${2:-}"; shift 2 ;;
        --remote) REMOTE_ARG="${2:-upstream}"; shift 2 ;;
        *) echo "❌ Unknown option: $1" >&2; usage >&2; exit 1 ;;
      esac
    done
    run_publish_oss "$DRY_RUN" "$REMOTE_ARG" "$CREATE_PR" "$REL_VER"; exit 0
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
        --mode) MODE_ARG="${2:-}"; shift 2 ;;
        --profile) PROFILE_ARG="${2:-}"; shift 2 ;;
        --auto-sync) AUTO_ARG="${2:-}"; shift 2 ;;
        --dev-repo) DEV_ARG="${2:-}"; shift 2 ;;
        --no-sync) NO_SYNC=1; shift ;;
        *) echo "❌ Unknown option: $1" >&2; usage >&2; exit 1 ;;
      esac
    done
    case "$MODE_ARG" in private|readonly|mutable) ;; *) echo "❌ Invalid --mode '$MODE_ARG' (expected private, readonly, or mutable)" >&2; exit 1 ;; esac
    case "$PROFILE_ARG" in human-base|science|technical|business|full) ;; *) echo "❌ Invalid --profile '$PROFILE_ARG' (expected human-base, science, technical, business, or full)" >&2; exit 1 ;; esac
    case "$AUTO_ARG" in boot|always|off) ;; *) echo "❌ Invalid --auto-sync '$AUTO_ARG' (expected boot, always, or off)" >&2; exit 1 ;; esac
    DOTFILES_WORKSTATION_MODE="$MODE_ARG"; DOTFILES_GLOBAL_PROFILE="$PROFILE_ARG"
    DOTFILES_AUTO_SYNC="$AUTO_ARG"; DOTFILES_DEV_REPO_DIR="$DEV_ARG"
    RESOLVED_DEV="$(detect_dev_repo)"
    mkdir -p "$(dirname "$CONFIG_FILE")"
    cat > "$CONFIG_FILE" <<EOF
# Declarative Workstation Configuration for dotfiles-ubuntu
export DOTFILES_RUNTIME_DIR="$RUNTIME_DIR"
export DOTFILES_WORKSTATION_MODE="$DOTFILES_WORKSTATION_MODE"
export DOTFILES_GLOBAL_PROFILE="$DOTFILES_GLOBAL_PROFILE"
export DOTFILES_AUTO_SYNC="$DOTFILES_AUTO_SYNC"
EOF
    if [ -n "$RESOLVED_DEV" ]; then printf 'export DOTFILES_DEV_REPO_DIR="%s"\n' "$RESOLVED_DEV" >> "$CONFIG_FILE"; fi
    apply_push_guard "$DOTFILES_WORKSTATION_MODE"
    [ -x "$RUNTIME_DIR/scripts/layer-config.sh" ] && "$RUNTIME_DIR/scripts/layer-config.sh" set-global-profile "$DOTFILES_GLOBAL_PROFILE" >/dev/null 2>&1 || true
    echo "✅ Workstation configuration written to $CONFIG_FILE"
    if [ "$NO_SYNC" = "0" ]; then run_sync 0; fi
    exit 0
    ;;
  status|--status)
    RESOLVED_DEV="$(detect_dev_repo)"
    PUSH_GUARD_URL=""
    [ -d "$RUNTIME_DIR/.git" ] && PUSH_GUARD_URL="$(git -C "$RUNTIME_DIR" config --get remote.origin.pushurl 2>/dev/null || true)"
    GUARD_ACTIVE="false"; [ "$PUSH_GUARD_URL" = "$READONLY_PUSH_GUARD" ] && GUARD_ACTIVE="true"
    BOOT_SYNCED="false"; [ -f "$STAMP_FILE" ] && BOOT_SYNCED="true"
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
