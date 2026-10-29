#!/usr/bin/env bash
# layer-config.sh — Fork parameterization, polymorphic template scaffolding,
# and static project projection (Without MCP <-> With MCP bridge).
#
# Subcommands:
#   list-templates                                List discovered template packs in Root and layers/*
#   init-fork --id <id> [--role <role>] [...]     Parameterize system/mcp-layer.json (v1.2) for a fork
#   scaffold-template <name> [--kind <kind>]      Create a polymorphic template pack in templates/<name>/
#   apply-project <target-dir> [--template <ref>] Materialize template + 0..N layer rules into <target-dir>/.agents/
#
# Flags:
#   -n, --dry-run   Preview operations without writing files
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
Usage: ./scripts/layer-config.sh [--dry-run] <command> [args...]

Parameterize fork identity (system/mcp-layer.json), scaffold polymorphic template
packs (templates/<name>/), and project multi-layer governance into target projects.

Commands:
  list-templates
      List all template packs discovered across templates/* and layers/*/templates/*.

  init-fork --id <layer-id> [--role <role>] [--precedence <0..100>] [--upstream-url <url>]
            [--upstream-id <id>] [--upstream-branch <branch>] [--description <text>]
            [--prune-default-templates]
      Configure system/mcp-layer.json (schema v1.2) for this fork's organizational purpose
      (corporate, domain-policy, department, team, service-node, environment-cluster, workstation).

  scaffold-template <template-name> [--kind <kind>] [--description <text>] [--register-binding]
      Scaffold templates/<template-name>/ (kind: stack-starter, domain-policy-pack,
      department-pack, or project-overlay) and optionally register its surface_binding.

  apply-project <target-project-dir> [--template <[layer:]name>] [--layers <all|csv>]
      Materialize the selected template pack plus 0..N participating layers ordered by
      precedence (0..100) into <target-project-dir>/.agents/ and generate LAYER_LINEAGE.md.

  diff-project <target-project-dir>
      Compare SHA-256 digests between <target-project-dir>/.agents/ and fork layers/templates
      to detect in_sync, modified_in_project, and novel_in_project files.

  promote-from-project <target-project-dir> --source <rel-path> [--to-layer <root|subtree>]
                       [--to-template <template-name>]
      Promote a matured rule, skill, or asset from <target-project-dir> into the target
      fork layer or template pack (enforcing AGENTS.md budget and SKILL.md frontmatter gates).

Options:
  -n, --dry-run   Preview changes in JSON output without modifying files on disk
  -h, --help      Show this help message and exit
  -v, --version   Show version information and exit
EOF
}

while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    -v|--version)
      echo "dotfiles-ubuntu layer-config v$VERSION_STR"
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
  echo "❌ Missing subcommand (expected: list-templates, init-fork, scaffold-template, or apply-project)." >&2
  usage >&2
  exit 1
fi
shift

python3 -B - "$SCRIPT_DIR" "$REPO_DIR" "$DRY_RUN" "$SUBCOMMAND" "$@" <<'PYEOF'
import json
from pathlib import Path
import sys

script_dir = Path(sys.argv[1]).resolve()
repo_dir = Path(sys.argv[2]).resolve()
dry_run = sys.argv[3].lower() == "true"
subcmd = sys.argv[4]
rest = sys.argv[5:]

sys.path.insert(0, str(script_dir))
from dotfiles_mcp.fork_configurator import (  # noqa: E402
    apply_fork_to_project,
    configure_fork_manifest,
    discover_templates_catalog,
    scaffold_template_pack,
)
from dotfiles_mcp.node_base import MCPNodeBase  # noqa: E402
from dotfiles_mcp.promotion_engine import (  # noqa: E402
    diff_project_against_layers,
    promote_project_asset_to_layer,
)

if subcmd == "list-templates":
    node = MCPNodeBase(repo_dir=repo_dir)
    catalog = discover_templates_catalog(repo_dir, node._discover_mounted_layers())
    print(json.dumps({"count": len(catalog), "templates": catalog}, indent=2))
    sys.exit(0)

if subcmd == "init-fork":
    layer_id = ""
    layer_role = "team"
    precedence = None
    description = None
    upstream_url = None
    upstream_id = None
    upstream_branch = None
    prune_default = False
    i = 0
    while i < len(rest):
        arg = rest[i]
        if arg == "--id" and i + 1 < len(rest):
            layer_id = rest[i + 1]
            i += 2
        elif arg == "--role" and i + 1 < len(rest):
            layer_role = rest[i + 1]
            i += 2
        elif arg == "--precedence" and i + 1 < len(rest):
            precedence = int(rest[i + 1])
            i += 2
        elif arg == "--description" and i + 1 < len(rest):
            description = rest[i + 1]
            i += 2
        elif arg == "--upstream-url" and i + 1 < len(rest):
            upstream_url = rest[i + 1]
            i += 2
        elif arg == "--upstream-id" and i + 1 < len(rest):
            upstream_id = rest[i + 1]
            i += 2
        elif arg == "--upstream-branch" and i + 1 < len(rest):
            upstream_branch = rest[i + 1]
            i += 2
        elif arg == "--prune-default-templates":
            prune_default = True
            i += 1
        else:
            print(f"❌ Unknown or incomplete init-fork argument: {arg}", file=sys.stderr)
            sys.exit(1)
    if not layer_id:
        print("❌ Missing required --id <layer-id> for init-fork.", file=sys.stderr)
        sys.exit(1)
    manifest = configure_fork_manifest(
        repo_dir,
        layer_id=layer_id,
        layer_role=layer_role,
        precedence=precedence,
        description=description,
        upstream_url=upstream_url,
        upstream_id=upstream_id,
        upstream_branch=upstream_branch,
        prune_default_templates=prune_default,
        dry_run=dry_run,
    )
    print(json.dumps({"dry_run": dry_run, "manifest": manifest}, indent=2))
    sys.exit(0)

if subcmd == "scaffold-template":
    if not rest or rest[0].startswith("-"):
        print("❌ Usage: ./scripts/layer-config.sh scaffold-template <template-name> [options]", file=sys.stderr)
        sys.exit(1)
    tpl_name = rest[0]
    kind = "stack-starter"
    description = None
    register_binding = False
    i = 1
    while i < len(rest):
        arg = rest[i]
        if arg == "--kind" and i + 1 < len(rest):
            kind = rest[i + 1]
            i += 2
        elif arg == "--description" and i + 1 < len(rest):
            description = rest[i + 1]
            i += 2
        elif arg == "--register-binding":
            register_binding = True
            i += 1
        else:
            print(f"❌ Unknown or incomplete scaffold-template argument: {arg}", file=sys.stderr)
            sys.exit(1)
    res = scaffold_template_pack(
        repo_dir,
        template_name=tpl_name,
        kind=kind,
        description=description,
        register_binding=register_binding,
        dry_run=dry_run,
    )
    print(json.dumps(res, indent=2))
    sys.exit(0)

if subcmd == "apply-project":
    if not rest or rest[0].startswith("-"):
        print("❌ Usage: ./scripts/layer-config.sh apply-project <target-project-dir> [options]", file=sys.stderr)
        sys.exit(1)
    target_dir = Path(rest[0]).resolve()
    template_ref = None
    layers_filter = None
    i = 1
    while i < len(rest):
        arg = rest[i]
        if arg == "--template" and i + 1 < len(rest):
            template_ref = rest[i + 1]
            i += 2
        elif arg == "--layers" and i + 1 < len(rest):
            layers_filter = [x.strip() for x in rest[i + 1].split(",") if x.strip()]
            i += 2
        else:
            print(f"❌ Unknown or incomplete apply-project argument: {arg}", file=sys.stderr)
            sys.exit(1)
    res = apply_fork_to_project(
        repo_dir,
        target_dir,
        template_ref=template_ref,
        layers_filter=layers_filter,
        dry_run=dry_run,
    )
    print(json.dumps(res, indent=2))
    sys.exit(0)

if subcmd == "diff-project":
    if not rest or rest[0].startswith("-"):
        print("❌ Usage: ./scripts/layer-config.sh diff-project <target-project-dir>", file=sys.stderr)
        sys.exit(1)
    target_dir = Path(rest[0]).resolve()
    res = diff_project_against_layers(repo_dir, target_dir)
    print(json.dumps(res, indent=2))
    sys.exit(0)

if subcmd == "promote-from-project":
    if not rest or rest[0].startswith("-"):
        print("❌ Usage: ./scripts/layer-config.sh promote-from-project <target-project-dir> --source <rel-path> [options]", file=sys.stderr)
        sys.exit(1)
    target_dir = Path(rest[0]).resolve()
    source_rel = ""
    target_layer = "root"
    target_template = None
    i = 1
    while i < len(rest):
        arg = rest[i]
        if arg == "--source" and i + 1 < len(rest):
            source_rel = rest[i + 1]
            i += 2
        elif arg == "--to-layer" and i + 1 < len(rest):
            target_layer = rest[i + 1]
            i += 2
        elif arg == "--to-template" and i + 1 < len(rest):
            target_template = rest[i + 1]
            i += 2
        else:
            print(f"❌ Unknown or incomplete promote-from-project argument: {arg}", file=sys.stderr)
            sys.exit(1)
    if not source_rel:
        print("❌ Missing required --source <rel-path> for promote-from-project.", file=sys.stderr)
        sys.exit(1)
    res = promote_project_asset_to_layer(
        repo_dir,
        target_dir,
        source_rel_path=source_rel,
        target_layer=target_layer,
        target_template=target_template,
        dry_run=dry_run,
    )
    print(json.dumps(res, indent=2))
    sys.exit(0)

print(f"❌ Unknown subcommand: {subcmd}", file=sys.stderr)
sys.exit(1)
PYEOF
