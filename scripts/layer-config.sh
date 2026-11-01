#!/usr/bin/env bash
# layer-config.sh — Fork parameterization, polymorphic template scaffolding,
# and static project projection (Without MCP <-> With MCP bridge).

set -euo pipefail
export LC_ALL=C

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="${DOTFILES_REPO_DIR:-$(cd "$SCRIPT_DIR/.." && pwd)}"
VERSION_STR="$({ tr -d '[:space:]' < "$REPO_DIR/VERSION"; } 2>/dev/null || echo "unknown")"
DRY_RUN=false

usage() {
  cat <<EOF
Usage: ./scripts/layer-config.sh [--dry-run] <command> [args...]

Commands:
  list-templates [<target-dir>]
      List all template packs discovered across templates/* and layers/*/templates/*.
  init-fork --id <layer-id> [--role <role>] [--precedence <0..100>] [--upstream-url <url>]
            [--upstream-id <id>] [--upstream-branch <branch>] [--description <text>]
            [--prune-default-templates]
      Configure system/mcp-layer.json (schema v1.2) for this fork's organizational purpose.
  scaffold-template <template-name> [--kind <kind>] [--description <text>]
                    [--rule-file <filename.md>] [--register-binding]
      Scaffold templates/<template-name>/ and optionally register its surface_binding.
  apply-project <target-project-dir> [--template <[layer:]name>] [--layers <all|csv>]
      Materialize template pack + 0..N participating layers into <target-project-dir>/.agents/.
  diff-project <target-project-dir>
      Compare SHA-256 digests between <target-project-dir>/.agents/ and fork layers/templates.
  promote-from-project <target-project-dir> --source <rel-path> [--to-layer <root|subtree>]
                       [--to-template <template-name>] [--upstream-dir|--target-repo <dir>]
                       [--create-pr] [--email <proposer-email>] [--org <name>]
                       [--contributors <list>] [--context <text>]
      Promote a matured rule, skill, or asset from <target-project-dir> into the target layer.
  set-authority [<target-dir>] --owner-role <role> [--emails <csv>] [--contact <text>]
      Configure layer_authority in <target-dir>/system/mcp-layer.json.
  check-authority [<target-dir>] --op <operation> [--email <email>] [--file <rel-path>]
      Verify whether the caller's git user.email (or --email) may execute <operation>.
  inspect-horizon [<target-dir>] [--parent-dir <dir>] [--email <email>]
      Inspect 1-hop downward propagation status and upward promotion candidates.
  spawn-ephemeral --role <bot-role> [--templates <csv>] [--layers <csv>] [--globs <csv>]
                  [--project-bridge <dir>] [--tier <flash|inherit|pro>] [--ttl <sec>]
      Materialize a zero-copy, TTL-bounded ephemeral Department Bot fork.
  inspect-ephemeral [--id <fork-id>]
      List active ephemeral forks (after automatic TTL reaping) or inspect one fork.
  reap-ephemeral --id <fork-id|all>
      Destroy a specific ephemeral fork or all active ephemeral forks ('--id all').
  set-global-profile <human-core|technical|business|full> [--stow]
      Compose antigravity/.gemini/config/AGENTS.md from modular base templates.
  register-subtree <layer-name> <repo-url> [branch]
      Upsert a mounted subtree entry inside root system/mcp-layer.json -> mounted_layers.
  bootstrap-workspace <target-dir> --id <layer-id> [--role <role>] [--precedence <0..100>]
                      [--parent-dir <dir>] [--upstream-url <url>] [--upstream-id <id>]
                      [--upstream-branch <branch>] [--description <text>] [--templates <csv>]
                      [--template-name <name>] [--no-scaffold-own]
      One-shot workspace initializer: inherits templates/lineage and runs apply-project.
  sync-layer <target-dir> [--parent-dir <dir>] [--templates <csv>]
      Propagate upstream template pack improvements and re-materialize <target-dir>/.agents/.

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
  echo "❌ Missing subcommand (see './scripts/layer-config.sh --help' for all 16 subcommands)." >&2
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
from dotfiles_mcp.authority_engine import configure_layer_authority, verify_layer_operation_authority  # noqa: E402
from dotfiles_mcp.ephemeral_fork_engine import inspect_ephemeral_forks, reap_ephemeral_fork, spawn_ephemeral_fork  # noqa: E402
from dotfiles_mcp.fork_configurator import apply_fork_to_project, configure_fork_manifest, discover_templates_catalog, scaffold_template_pack  # noqa: E402
from dotfiles_mcp.node_base import MCPNodeBase  # noqa: E402
from dotfiles_mcp.promotion_engine import diff_project_against_layers, inspect_layer_horizon, promote_project_asset_to_layer  # noqa: E402
from dotfiles_mcp.workspace_bootstrapper import bootstrap_layer_workspace, register_mounted_subtree, set_global_agents_profile, sync_layer_workspace  # noqa: E402


def _die(msg: str, code: int = 1) -> None:
    print(f"❌ {msg}", file=sys.stderr)
    sys.exit(code)


def _enforce_authority_or_exit(target: Path, op: str) -> None:
    verdict = verify_layer_operation_authority(target, operation=op)
    if not verdict["allowed"]:
        print(f"❌ {verdict['remediation']}", file=sys.stderr)
        print(json.dumps(verdict, indent=2))
        sys.exit(2)


def _parse_opts(
    args: list[str],
    value_flags: dict[str, str],
    bool_flags: dict[str, str] | None = None,
) -> dict[str, object]:
    out: dict[str, object] = {}
    bflags = bool_flags or {}
    i = 0
    while i < len(args):
        arg = args[i]
        if arg in value_flags and i + 1 < len(args):
            out[value_flags[arg]] = args[i + 1]
            i += 2
        elif arg in bflags:
            out[bflags[arg]] = True
            i += 1
        else:
            _die(f"Unknown or incomplete {subcmd} argument: {arg}")
    return out


def _csv(val: object) -> list[str] | None:
    return [x.strip() for x in str(val).split(",") if x.strip()] if val else None


def _opt_str(opts: dict[str, object], key: str) -> str | None:
    return str(opts[key]) if key in opts else None


def _opt_path(opts: dict[str, object], key: str) -> Path | None:
    return Path(str(opts[key])).resolve() if key in opts else None


if subcmd == "list-templates":
    target_dir = Path(rest[0]).resolve() if rest and not rest[0].startswith("-") else repo_dir
    node = MCPNodeBase(repo_dir=target_dir)
    catalog = discover_templates_catalog(target_dir, node._discover_mounted_layers())
    print(json.dumps({"count": len(catalog), "templates": catalog}, indent=2))
    sys.exit(0)

if subcmd == "init-fork":
    opts = _parse_opts(
        rest,
        {"--id": "id", "--role": "role", "--precedence": "prec", "--description": "desc", "--upstream-url": "up_url", "--upstream-id": "up_id", "--upstream-branch": "up_branch"},
        {"--prune-default-templates": "prune"},
    )
    if not opts.get("id"):
        _die("Missing required --id <layer-id> for init-fork.")
    _enforce_authority_or_exit(repo_dir, "init-fork")
    manifest = configure_fork_manifest(
        repo_dir,
        layer_id=str(opts["id"]),
        layer_role=str(opts.get("role", "team")),
        precedence=int(str(opts["prec"])) if "prec" in opts else None,
        description=_opt_str(opts, "desc"),
        upstream_url=_opt_str(opts, "up_url"),
        upstream_id=_opt_str(opts, "up_id"),
        upstream_branch=_opt_str(opts, "up_branch"),
        prune_default_templates=bool(opts.get("prune", False)),
        dry_run=dry_run,
    )
    print(json.dumps({"dry_run": dry_run, "manifest": manifest}, indent=2))
    sys.exit(0)

if subcmd == "scaffold-template":
    if not rest or rest[0].startswith("-"):
        _die("Usage: ./scripts/layer-config.sh scaffold-template <template-name> [options]")
    opts = _parse_opts(rest[1:], {"--kind": "kind", "--description": "desc", "--rule-file": "rule"}, {"--register-binding": "bind"})
    _enforce_authority_or_exit(repo_dir, "scaffold-template")
    res = scaffold_template_pack(
        repo_dir,
        template_name=rest[0],
        kind=str(opts.get("kind", "stack-starter")),
        description=_opt_str(opts, "desc"),
        register_binding=bool(opts.get("bind", False)),
        rule_filename=_opt_str(opts, "rule"),
        dry_run=dry_run,
    )
    print(json.dumps(res, indent=2))
    sys.exit(0)

if subcmd == "apply-project":
    if not rest or rest[0].startswith("-"):
        _die("Usage: ./scripts/layer-config.sh apply-project <target-project-dir> [options]")
    opts = _parse_opts(rest[1:], {"--template": "tpl", "--layers": "layers"})
    res = apply_fork_to_project(repo_dir, Path(rest[0]).resolve(), template_ref=_opt_str(opts, "tpl"), layers_filter=_csv(opts.get("layers")), dry_run=dry_run)
    print(json.dumps(res, indent=2))
    sys.exit(0)

if subcmd == "diff-project":
    if not rest or rest[0].startswith("-"):
        _die("Usage: ./scripts/layer-config.sh diff-project <target-project-dir>")
    target_dir = Path(rest[0]).resolve()
    base_dir = target_dir if (target_dir / "system" / "mcp-layer.json").is_file() else repo_dir
    print(json.dumps(diff_project_against_layers(base_dir, target_dir), indent=2))
    sys.exit(0)

if subcmd == "promote-from-project":
    if not rest or rest[0].startswith("-"):
        _die("Usage: ./scripts/layer-config.sh promote-from-project <target-project-dir> --source <rel-path> [options]")
    opts = _parse_opts(
        rest[1:],
        {"--source": "src", "--to-layer": "layer", "--to-template": "tpl", "--upstream-dir": "up_dir", "--target-repo": "up_dir", "--email": "email", "--org": "org", "--contributors": "contrib", "--context": "ctx"},
        {"--create-pr": "pr"},
    )
    if not opts.get("src"):
        _die("Missing required --source <rel-path> for promote-from-project.")
    res = promote_project_asset_to_layer(
        repo_dir,
        Path(rest[0]).resolve(),
        source_rel_path=str(opts["src"]),
        target_layer=str(opts.get("layer", "root")),
        target_template=_opt_str(opts, "tpl"),
        upstream_dir=_opt_path(opts, "up_dir"),
        prepare_pr=bool(opts.get("pr", False)),
        actor_email=_opt_str(opts, "email"),
        contributing_org=_opt_str(opts, "org"),
        contributors=_opt_str(opts, "contrib"),
        validation_context=_opt_str(opts, "ctx"),
        dry_run=dry_run,
    )
    print(json.dumps(res, indent=2))
    sys.exit(0)

if subcmd == "spawn-ephemeral":
    opts = _parse_opts(rest, {"--role": "role", "--templates": "tpls", "--layers": "layers", "--globs": "globs", "--project-bridge": "bridge", "--tier": "tier", "--ttl": "ttl"})
    if not opts.get("role"):
        _die("Missing required --role <bot-role> for spawn-ephemeral.")
    node = MCPNodeBase(repo_dir=repo_dir)
    res = spawn_ephemeral_fork(
        repo_dir,
        node._load_layer_manifest(),
        bot_role=str(opts["role"]),
        target_globs=_csv(opts.get("globs")),
        mount_templates=_csv(opts.get("tpls")),
        mount_layers=_csv(opts.get("layers")),
        mount_project_rules_from=_opt_path(opts, "bridge"),
        model_tier=str(opts.get("tier", "flash")),
        ttl_seconds=int(str(opts.get("ttl", 300))),
        dry_run=dry_run,
    )
    print(json.dumps(res, indent=2))
    sys.exit(0)

if subcmd == "inspect-ephemeral":
    opts = _parse_opts(rest, {"--id": "id"})
    print(json.dumps(inspect_ephemeral_forks(repo_dir, fork_id=_opt_str(opts, "id")), indent=2))
    sys.exit(0)

if subcmd == "reap-ephemeral":
    opts = _parse_opts(rest, {"--id": "id"})
    if not opts.get("id"):
        _die("Missing required --id <fork-id|all> for reap-ephemeral.")
    print(json.dumps(reap_ephemeral_fork(repo_dir, fork_id=str(opts["id"]), dry_run=dry_run), indent=2))
    sys.exit(0)

if subcmd == "set-global-profile":
    if not rest:
        _die("Usage: ./scripts/layer-config.sh set-global-profile <human-core|technical|business|full> [--stow]")
    print(json.dumps(set_global_agents_profile(repo_dir, rest[0], run_stow="--stow" in rest[1:], dry_run=dry_run), indent=2))
    sys.exit(0)

if subcmd == "register-subtree":
    if len(rest) < 2:
        _die("Usage: ./scripts/layer-config.sh register-subtree <layer-name> <repo-url> [branch]")
    _enforce_authority_or_exit(repo_dir, "register-subtree")
    branch = rest[2] if len(rest) >= 3 else "master"
    print(json.dumps(register_mounted_subtree(repo_dir, rest[0], rest[1], branch, dry_run=dry_run), indent=2))
    sys.exit(0)

if subcmd == "set-authority":
    has_pos = bool(rest and not rest[0].startswith("--"))
    target_dir = Path(rest[0]).resolve() if has_pos else repo_dir
    opts = _parse_opts(rest[1:] if has_pos else rest, {"--owner-role": "role", "--emails": "emails", "--contact": "contact"})
    if not opts.get("role"):
        _die("Missing required --owner-role <role> for set-authority.")
    res = configure_layer_authority(target_dir, owner_role=str(opts["role"]), authorized_emails=_csv(opts.get("emails")) or [], escalation_contact=_opt_str(opts, "contact"), dry_run=dry_run)
    print(json.dumps(res, indent=2))
    sys.exit(0)

if subcmd == "check-authority":
    has_pos = bool(rest and not rest[0].startswith("--"))
    target_dir = Path(rest[0]).resolve() if has_pos else repo_dir
    opts = _parse_opts(rest[1:] if has_pos else rest, {"--op": "op", "--email": "email", "--file": "file"})
    if not opts.get("op"):
        _die("Missing required --op <operation> for check-authority.")
    verdict = verify_layer_operation_authority(target_dir, operation=str(opts["op"]), actor_email=_opt_str(opts, "email"), target_rel_path=_opt_str(opts, "file"))
    print(json.dumps(verdict, indent=2))
    if not verdict["allowed"]:
        _die(str(verdict["remediation"]), code=2)
    sys.exit(0)

if subcmd == "bootstrap-workspace":
    if not rest or rest[0].startswith("--"):
        _die("Usage: ./scripts/layer-config.sh bootstrap-workspace <target-dir> --id <layer-id> [...]")
    opts = _parse_opts(
        rest[1:],
        {"--id": "id", "--role": "role", "--precedence": "prec", "--description": "desc", "--parent-dir": "parent", "--upstream-url": "up_url", "--upstream-id": "up_id", "--upstream-branch": "up_branch", "--templates": "tpls", "--template-name": "tpl_name"},
        {"--no-scaffold-own": "no_own"},
    )
    if not opts.get("id"):
        _die("Missing required --id <layer-id> for bootstrap-workspace.")
    res = bootstrap_layer_workspace(
        repo_dir,
        Path(rest[0]).resolve(),
        layer_id=str(opts["id"]),
        layer_role=str(opts.get("role", "department")),
        precedence=int(str(opts["prec"])) if "prec" in opts else None,
        description=_opt_str(opts, "desc"),
        upstream_repo=_opt_str(opts, "up_url"),
        upstream_branch=str(opts.get("up_branch", "master")),
        upstream_layer_id=_opt_str(opts, "up_id"),
        parent_dir=_opt_path(opts, "parent"),
        templates=_csv(opts.get("tpls")),
        own_template_name=_opt_str(opts, "tpl_name"),
        scaffold_own_template=not bool(opts.get("no_own", False)),
        dry_run=dry_run,
    )
    print(json.dumps(res, indent=2))
    sys.exit(0)

if subcmd == "sync-layer":
    if not rest or rest[0].startswith("--"):
        _die("Usage: ./scripts/layer-config.sh sync-layer <target-dir> [--parent-dir <dir>] [--templates <csv>]")
    opts = _parse_opts(rest[1:], {"--parent-dir": "parent", "--templates": "tpls"})
    res = sync_layer_workspace(repo_dir, Path(rest[0]).resolve(), parent_dir=_opt_path(opts, "parent"), templates=_csv(opts.get("tpls")), dry_run=dry_run)
    print(json.dumps(res, indent=2))
    sys.exit(0)

if subcmd == "inspect-horizon":
    has_pos = bool(rest and not rest[0].startswith("--"))
    target_dir = Path(rest[0]).resolve() if has_pos else repo_dir
    opts = _parse_opts(rest[1:] if has_pos else rest, {"--parent-dir": "parent", "--email": "email"})
    print(json.dumps(inspect_layer_horizon(repo_dir, target_dir, parent_dir=_opt_path(opts, "parent"), actor_email=_opt_str(opts, "email")), indent=2))
    sys.exit(0)

_die(f"Unknown subcommand: {subcmd}")
PYEOF
