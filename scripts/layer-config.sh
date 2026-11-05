#!/usr/bin/env bash
# layer-config.sh — Tiered CLI entrypoint for C1/C2/C3 layer governance,
# polymorphic template scaffolding, and Ephemeral Department Bot orchestration.

set -euo pipefail
export LC_ALL=C

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="${DOTFILES_REPO_DIR:-$(cd "$SCRIPT_DIR/.." && pwd)}"
VERSION_STR="$({ tr -d '[:space:]' < "$REPO_DIR/VERSION"; } 2>/dev/null || echo "unknown")"
DRY_RUN=false

usage() {
  cat <<EOF
Usage: ./scripts/layer-config.sh [--dry-run] <command> [args...]

Commands (grouped by operational family — 26 total):

  [C1 · Discovery, Status, Horizon & Read-Only Consultation (7)]
  list-templates [<target-dir>]
      List all template packs discovered across templates/* and layers/*/templates/*.
  status [<target-dir>] [--parent-dir <dir>]
      Return a single-call consolidated status digest (session, git, priority, horizon & diff).
  inspect-horizon [<target-dir>] [--parent-dir <dir>] [--email <email>]
      Inspect 3-bucket bilateral layer_report, 1-hop propagation status & promotion candidates.
  compare-upstream [<target-dir>] [--parent-dir <dir>] [--template <name>] [--apply-safe]
      Compare rule sections between upstream (parent/OSS) and local workspace templates.
  diff-project <target-project-dir> [--parent-dir <dir>]
      Compare SHA-256 digests between <target-project-dir>/.agents/ and fork layers/templates.
  check-authority [<target-dir>] --op <operation> [--email <email>] [--file <rel-path>] [--parent-dir <dir>]
      Verify whether the caller's git user.email (or --email) may execute <operation>.
  consult-layer [<target-dir>] --layer <layer-or-template> --query <text> [--path <rel-path>]
                [--tier <flash|inherit|pro>]
      Run a zero-residue, one-shot read-only ephemeral consultation against a layer or template.

  [C2 · Workspace, Profile, Template & Task Lifecycle (8)]
  bootstrap-workspace <target-dir> --id <layer-id> [--role <role>] [--precedence <0..100>]
                      [--parent-dir <dir>] [--upstream-url <url>] [--upstream-id <id>]
                      [--upstream-branch <branch>] [--description <text>] [--templates <csv>]
                      [--template-name <name>] [--no-scaffold-own]
      One-shot workspace initializer: inherits templates/lineage and runs apply-project.
  sync-layer [<target-dir>] [--parent-dir <dir>] [--templates <csv>]
             [--strategy <reconcile|accept-upstream|keep-local|merge>]
      Propagate upstream template pack improvements and re-materialize <target-dir>/.agents/.
  apply-project <target-project-dir> [--parent-dir <dir>] [--template <[layer:]name>] [--layers <all|csv>]
      Materialize template pack + 0..N participating layers into <target-project-dir>/.agents/.
  set-global-profile <human-base|science|technical|business|full> [--stow]
      Compose antigravity/.gemini/config/AGENTS.md from modular base templates.
  start-task [<target-dir>] --task <id-or-text> [--tracker <tracker>] [--ticket <id>] [--prefix <pfx>]
      Claim a task item, mark it [/], update .agents/SESSION.md, and emit feature/<TICKET>-<slug>.
  scaffold-template <template-name> [--kind <kind>] [--description <text>]
                    [--rule-file <filename.md>] [--register-binding]
      Scaffold templates/<template-name>/ and optionally register its surface_binding.
  init-fork --id <layer-id> [--role <role>] [--precedence <0..100>] [--upstream-url <url>]
            [--upstream-id <id>] [--upstream-branch <branch>] [--description <text>]
            [--entity-kind <public-government|enterprise|individual|open-source>]
            [--governing-root <root-id>] [--prune-default-templates]
      Configure system/mcp-layer.json (schema mcp-layer-v1) for this fork's organizational purpose.
  register-subtree <layer-name> <repo-url> [branch]
      Upsert a mounted subtree entry inside root system/mcp-layer.json -> mounted_layers.

  [C3 · Inter-Layer Governance, Roster & Environment Promotion (8)]
  complete-task [<target-dir>] --task <id-or-text> [--deliverable <path>] [--summary <text>]
                [--tracker <tracker>] [--parent-dir <dir>] [--email <email>] [--create-pr]
      Mark a task [x] and report reciprocal completion upward to the parent layer's WORKTASK.md.
  delegate-to-child [<target-dir>] --to-child <layer> [--task <text>] [--source <rel-path>]
                    [--ticket <id>] [--priority <P0|P1|P2>] [--surface <surface>]
                    [--email <email>] [--create-pr] [--force]
      Delegate a 1-hop downward directive or governance artifact into a child layer surface.
  promote-from-project <target-project-dir> --source <rel-path> [--to-layer <root|subtree>]
                       [--to-template <template-name>] [--upstream-dir <dir>]
                       [--create-pr] [--email <proposer-email>] [--org <name>]
                       [--contributors <list>] [--context <text>] [--force]
      Promote a matured rule, skill, or asset from <target-project-dir> into the target layer.
  manage-roster [<target-dir>] [--add <email>] [--remove <email>]
                [--role <owner|maintainer|validator|member>] [--no-codeowners]
      Inspect or update the layer roster (owners, maintainers, validators, members) and CODEOWNERS.
  set-authority [<target-dir>] --owner-role <role> [--emails <csv>] [--contact <text>]
      Configure layer_authority in <target-dir>/system/mcp-layer.json.
  configure-git-policy [<target-dir>] [--protected <csv>] [--no-codeowners] [--no-require-pr]
      Configure Git branch protection, process stages, env promotion branches, and CODEOWNERS.
  check-env-promotion [<target-dir>] --to-env <dev|tst|pre|pro> [--branch <branch>]
                      [--email <email>] [--parent-dir <dir>] [--files <csv>]
      Evaluate intrinsic dev -> tst -> pre -> pro environment and cross-layer surface gates.
  record-decision [<target-dir>] --item <ref> --decision <approve|reject|defer|blocked> --reason <text>
      Record a human review decision in trackers, SESSION.md, and logs/governance_audit.jsonl.

  [Ephemeral Department Bots (3)]
  spawn-ephemeral --role <bot-role> [--templates <csv>] [--layers <csv>] [--globs <csv>]
                  [--project-bridge <dir>] [--tier <flash|inherit|pro>] [--ttl <sec>]
      Materialize a zero-copy, TTL-bounded ephemeral Department Bot fork.
  inspect-ephemeral [--id <fork-id>] [--catalog] [--family <family>]
      List active ephemeral forks, inspect one fork, or query OOP capability rings & bot catalog.
  reap-ephemeral --id <fork-id|all>
      Destroy a specific ephemeral fork or all active ephemeral forks ('--id all').

Options:
  -n, --dry-run   Preview changes in JSON output without modifying files on disk
  -h, --help      Show this help message and exit
  -v, --version   Show version information and exit
EOF
}

while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    -v|--version) echo "dotfiles-ubuntu layer-config v$VERSION_STR"; exit 0 ;;
    -n|--dry-run) DRY_RUN=true; shift ;;
    -*) echo "❌ Unknown option: $1" >&2; usage >&2; exit 1 ;;
    *) break ;;
  esac
done

SUBCOMMAND="${1:-}"
if [ -z "$SUBCOMMAND" ]; then
  echo "❌ Missing subcommand (see './scripts/layer-config.sh --help' for all 26 subcommands)." >&2
  usage >&2
  exit 1
fi
shift

PYTHONPATH="$SCRIPT_DIR${PYTHONPATH:+:$PYTHONPATH}" exec python3 -B -c \
  "import sys; from dotfiles_mcp.governance.cli_dispatcher import main; raise SystemExit(main(sys.argv[1:]))" \
  "$REPO_DIR" "$DRY_RUN" "$SUBCOMMAND" "$@"
