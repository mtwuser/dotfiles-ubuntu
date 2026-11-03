"""Tiered CLI dispatcher for scripts/layer-config.sh (C1/C2/C3 & Ephemeral Bot families).

Specification: docs/architecture/06_layer_governance_and_promotion_engines.md
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from dotfiles_mcp.core import manifest_helpers
from dotfiles_mcp.governance import (
    authority_engine,
    fork_configurator,
    git_governance_engine,
    horizon_engine,
    promotion_engine,
    workflow_engine,
    workspace_bootstrapper,
)
from dotfiles_mcp.mcp_node import capability_registry, ephemeral_fork_engine, node_base

# fmt: off
C1_DISCOVERY_SUBCOMMANDS: tuple[str, ...] = (
    "list-templates", "status", "inspect-horizon", "compare-upstream",
    "diff-project", "check-authority", "consult-layer",
)
C2_LIFECYCLE_SUBCOMMANDS: tuple[str, ...] = (
    "bootstrap-workspace", "sync-layer", "apply-project", "set-global-profile",
    "start-task", "scaffold-template", "init-fork", "register-subtree",
)
C3_GOVERNANCE_SUBCOMMANDS: tuple[str, ...] = (
    "complete-task", "delegate-to-child", "promote-from-project", "manage-roster",
    "set-authority", "configure-git-policy", "check-env-promotion", "record-decision",
)
EPHEMERAL_BOT_SUBCOMMANDS: tuple[str, ...] = (
    "spawn-ephemeral", "inspect-ephemeral", "reap-ephemeral",
)


class _CLIUsageError(ValueError):
    """Raised when CLI arguments or subcommands are missing or invalid."""


class _CLIAuthorityBlockedError(RuntimeError):
    """Raised when a layer authority or environment gate blocks an operation (exit code 2)."""

    def __init__(self, payload: dict[str, Any], message: str) -> None:
        """Initialize blocked error with JSON verdict payload and stderr message."""
        super().__init__(message)
        self.payload, self.message = payload, message


def _parse_opts(
    subcmd: str, args: list[str], vflags: tuple[str, ...], bflags: tuple[str, ...] = ()
) -> dict[str, object]:
    """Parse CLI flag arguments into snake_case keys or raise _CLIUsageError."""
    out: dict[str, object] = {}
    i = 0
    while i < len(args):
        arg, key = args[i], args[i].removeprefix("--").replace("-", "_")
        if arg in vflags and i + 1 < len(args):
            out[key], i = args[i + 1], i + 2
        elif arg in bflags:
            out[key], i = True, i + 1
        else:
            raise _CLIUsageError(f"Unknown or incomplete {subcmd} argument: {arg}")
    return out


def _csv(val: object) -> list[str] | None:
    """Split a comma-separated CLI option string into a stripped list of strings."""
    return [x.strip() for x in str(val).split(",") if x.strip()] if val else None


def _opt_str(opts: dict[str, object], key: str) -> str | None:
    """Return an optional string parameter from parsed CLI options."""
    return str(opts[key]) if key in opts else None


def _opt_path(opts: dict[str, object], key: str) -> Path | None:
    """Return an optional resolved Path parameter from parsed CLI options."""
    return Path(str(opts[key])).resolve() if key in opts else None


def _req_pos(rest: list[str], usage: str) -> Path:
    """Require a leading positional directory argument or raise _CLIUsageError."""
    if not rest or rest[0].startswith("-"):
        raise _CLIUsageError(f"Usage: ./scripts/layer-config.sh {usage}")
    return Path(rest[0]).resolve()


def _req_opt(opts: dict[str, object], key: str, message: str) -> str:
    """Require a parsed option key to be non-empty or raise _CLIUsageError."""
    if not opts.get(key):
        raise _CLIUsageError(message)
    return str(opts[key])


def _pos_opts(
    repo_dir: Path, subcmd: str, args: list[str], vflags: tuple[str, ...],
    bflags: tuple[str, ...] = (),
) -> tuple[Path, dict[str, object]]:
    """Extract an optional leading positional path (defaulting to repo_dir) and parsed flags."""
    has_pos = bool(args and not args[0].startswith("--"))
    target = Path(args[0]).resolve() if has_pos else repo_dir
    return target, _parse_opts(subcmd, args[1:] if has_pos else args, vflags, bflags)


def _enforce_authority(target: Path, op: str) -> None:
    """Verify layer operation authority or raise _CLIAuthorityBlockedError (exit code 2)."""
    verdict = authority_engine.verify_layer_operation_authority(target, operation=op)
    if not verdict["allowed"]:
        raise _CLIAuthorityBlockedError(verdict, str(verdict["remediation"]))


def _dispatch_c1_subcommand(
    repo_dir: Path, dry_run: bool, subcmd: str, rest: list[str]
) -> dict[str, Any]:
    """Dispatch Tier C1 (Discovery, Status, Horizon & Read-Only Consultation) subcommands."""
    if subcmd == "list-templates":
        tdir = Path(rest[0]).resolve() if rest and not rest[0].startswith("-") else repo_dir
        layers = node_base.MCPNodeBase(repo_dir=tdir)._discover_mounted_layers()
        cat = manifest_helpers.discover_templates_catalog(tdir, layers)
        return {"count": len(cat), "templates": cat}
    if subcmd == "status":
        tdir, opts = _pos_opts(repo_dir, subcmd, rest, ("--parent-dir",))
        p_dir = _opt_path(opts, "parent_dir")
        return workspace_bootstrapper.inspect_workspace_status(repo_dir, tdir, parent_dir=p_dir)
    if subcmd == "inspect-horizon":
        tdir, opts = _pos_opts(repo_dir, subcmd, rest, ("--parent-dir", "--email"))
        return horizon_engine.inspect_layer_horizon(
            repo_dir, tdir, parent_dir=_opt_path(opts, "parent_dir"),
            actor_email=_opt_str(opts, "email"),
        )
    if subcmd == "compare-upstream":
        tdir, opts = _pos_opts(
            repo_dir, subcmd, rest, ("--parent-dir", "--template"), ("--apply-safe",)
        )
        return horizon_engine.compare_upstream_templates(
            repo_dir, tdir, parent_dir=_opt_path(opts, "parent_dir"),
            template_filter=_opt_str(opts, "template"),
            apply_upstream_only=bool(opts.get("apply_safe", False)), dry_run=dry_run,
        )
    if subcmd == "diff-project":
        tdir = _req_pos(rest, "diff-project <target-project-dir> [--parent-dir <dir>]")
        opts = _parse_opts(subcmd, rest[1:], ("--parent-dir",))
        has_m = (tdir / "system/mcp-layer.json").is_file()
        bdir = tdir if has_m else (_opt_path(opts, "parent_dir") or repo_dir)
        return promotion_engine.diff_project_against_layers(bdir, tdir)
    if subcmd == "check-authority":
        vf = ("--op", "--email", "--file", "--parent-dir")
        tdir, opts = _pos_opts(repo_dir, subcmd, rest, vf)
        op = _req_opt(opts, "op", "Missing required --op <operation> for check-authority.")
        verdict = authority_engine.verify_layer_operation_authority(
            tdir, operation=op, actor_email=_opt_str(opts, "email"),
            target_rel_path=_opt_str(opts, "file"), parent_dir=_opt_path(opts, "parent_dir"),
        )
        if not verdict["allowed"]:
            raise _CLIAuthorityBlockedError(verdict, str(verdict["remediation"]))
        return verdict
    tdir, opts = _pos_opts(repo_dir, subcmd, rest, ("--layer", "--query", "--path", "--tier"))
    u_msg = "Usage: ./scripts/layer-config.sh consult-layer [<dir>] --layer <id> --query <text>"
    return workflow_engine.consult_layer_ephemeral(
        repo_dir, tdir, target_layer=_req_opt(opts, "layer", u_msg),
        query=_req_opt(opts, "query", u_msg),
        target_path=str(opts.get("path", "corporate/policy.md")),
        model_tier=str(opts.get("tier", "flash")), dry_run=dry_run,
    )


def _dispatch_c2_subcommand(
    repo_dir: Path, dry_run: bool, subcmd: str, rest: list[str]
) -> dict[str, Any]:
    """Dispatch Tier C2 (Workspace, Profile, Template & Task Lifecycle) subcommands."""
    if subcmd == "bootstrap-workspace":
        tdir = _req_pos(rest, "bootstrap-workspace <target-dir> --id <layer-id> [...]")
        vf: tuple[str, ...] = (
            "--id", "--role", "--precedence", "--description", "--parent-dir", "--upstream-url",
            "--upstream-id", "--upstream-branch", "--templates", "--template-name",
        )
        opts = _parse_opts(subcmd, rest[1:], vf, ("--no-scaffold-own",))
        lid = _req_opt(opts, "id", "Missing required --id <layer-id> for bootstrap-workspace.")
        return workspace_bootstrapper.bootstrap_layer_workspace(
            repo_dir, tdir, layer_id=lid, layer_role=str(opts.get("role", "department")),
            precedence=int(str(opts["precedence"])) if "precedence" in opts else None,
            description=_opt_str(opts, "description"), upstream_repo=_opt_str(opts, "upstream_url"),
            upstream_branch=str(opts.get("upstream_branch", "master")),
            upstream_layer_id=_opt_str(opts, "upstream_id"),
            parent_dir=_opt_path(opts, "parent_dir"), templates=_csv(opts.get("templates")),
            own_template_name=_opt_str(opts, "template_name"),
            scaffold_own_template=not bool(opts.get("no_scaffold_own", False)), dry_run=dry_run,
        )
    if subcmd == "sync-layer":
        tdir, opts = _pos_opts(
            repo_dir, subcmd, rest, ("--parent-dir", "--templates", "--strategy")
        )
        return workspace_bootstrapper.sync_layer_workspace(
            repo_dir, tdir, parent_dir=_opt_path(opts, "parent_dir"),
            templates=_csv(opts.get("templates")), strategy=str(opts.get("strategy", "reconcile")),
            dry_run=dry_run,
        )
    if subcmd == "apply-project":
        tdir = _req_pos(rest, "apply-project <target-project-dir> [options]")
        opts = _parse_opts(
            subcmd, rest[1:], ("--template", "--layers", "--parent-dir"), ("--include-defaults",)
        )
        p_dir, mp = _opt_path(opts, "parent_dir"), tdir / "system/mcp-layer.json"
        is_non_ws = (
            mp.is_file() and json.loads(mp.read_text("utf-8")).get("layer_role") != "workstation"
        )
        bdir = p_dir if p_dir is not None else (tdir if is_non_ws else repo_dir)
        inc_def = bool(opts.get("include_defaults", False)) or p_dir is not None or is_non_ws
        return fork_configurator.apply_fork_to_project(
            bdir, tdir, template_ref=_opt_str(opts, "template"),
            layers_filter=_csv(opts.get("layers")), include_layer_defaults=inc_def, dry_run=dry_run,
        )
    if subcmd == "set-global-profile":
        if not rest:
            raise _CLIUsageError(
                "Usage: ./scripts/layer-config.sh set-global-profile <profile> [--stow]"
            )
        return workspace_bootstrapper.set_global_agents_profile(
            repo_dir, rest[0], run_stow="--stow" in rest[1:], dry_run=dry_run
        )
    if subcmd == "start-task":
        vf = ("--task", "--tracker", "--ticket", "--prefix")
        tdir, opts = _pos_opts(repo_dir, subcmd, rest, vf)
        u_msg = "Usage: ./scripts/layer-config.sh start-task [<dir>] --task <id>"
        return workflow_engine.start_task_workflow(
            tdir, task_query=_req_opt(opts, "task", u_msg),
            tracker=str(opts.get("tracker", "WORKTASK.md")), ticket_id=_opt_str(opts, "ticket"),
            branch_prefix=str(opts.get("prefix", "feature")), dry_run=dry_run,
        )
    if subcmd == "scaffold-template":
        _req_pos(rest, "scaffold-template <template-name> [options]")
        opts = _parse_opts(
            subcmd, rest[1:], ("--kind", "--description", "--rule-file"), ("--register-binding",)
        )
        _enforce_authority(repo_dir, "scaffold-template")
        return fork_configurator.scaffold_template_pack(
            repo_dir, template_name=rest[0], kind=str(opts.get("kind", "tech-stack")),
            description=_opt_str(opts, "description"),
            register_binding=bool(opts.get("register_binding", False)),
            rule_filename=_opt_str(opts, "rule_file"), dry_run=dry_run,
        )
    if subcmd == "init-fork":
        vf = (
            "--id", "--role", "--precedence", "--description", "--upstream-url",
            "--upstream-id", "--upstream-branch", "--entity-kind", "--governing-root",
        )
        opts = _parse_opts(subcmd, rest, vf, ("--prune-default-templates",))
        lid = _req_opt(opts, "id", "Missing required --id <layer-id> for init-fork.")
        _enforce_authority(repo_dir, "init-fork")
        manifest = fork_configurator.configure_fork_manifest(
            repo_dir, layer_id=lid, layer_role=str(opts.get("role", "squad")),
            precedence=int(str(opts["precedence"])) if "precedence" in opts else None,
            description=_opt_str(opts, "description"), upstream_url=_opt_str(opts, "upstream_url"),
            upstream_id=_opt_str(opts, "upstream_id"),
            upstream_branch=_opt_str(opts, "upstream_branch"),
            entity_kind=_opt_str(opts, "entity_kind"),
            governing_root_id=_opt_str(opts, "governing_root"),
            prune_default_templates=bool(opts.get("prune_default_templates", False)),
            dry_run=dry_run,
        )
        return {"dry_run": dry_run, "manifest": manifest}
    if len(rest) < 2:
        raise _CLIUsageError(
            "Usage: ./scripts/layer-config.sh register-subtree <layer-name> <repo-url> [branch]"
        )
    _enforce_authority(repo_dir, "register-subtree")
    tail = rest[1:]
    branch = tail[1] if len(tail) >= 2 else "master"
    return workspace_bootstrapper.register_mounted_subtree(
        repo_dir, rest[0], tail[0], branch, dry_run=dry_run
    )


def _dispatch_c3_subcommand(
    repo_dir: Path, dry_run: bool, subcmd: str, rest: list[str]
) -> dict[str, Any]:
    """Dispatch Tier C3 (Inter-Layer Governance, Roster & Environment Promotion) subcommands."""
    if subcmd == "complete-task":
        vf: tuple[str, ...] = (
            "--task", "--deliverable", "--summary", "--tracker", "--parent-dir", "--email"
        )
        tdir, opts = _pos_opts(repo_dir, subcmd, rest, vf, ("--create-pr",))
        u_msg = "Usage: ./scripts/layer-config.sh complete-task [<dir>] --task <id>"
        return workflow_engine.complete_task_workflow(
            tdir, task_query=_req_opt(opts, "task", u_msg),
            deliverable=str(opts.get("deliverable", "")), summary=str(opts.get("summary", "")),
            tracker=str(opts.get("tracker", "WORKTASK.md")),
            parent_dir=_opt_path(opts, "parent_dir"), actor_email=_opt_str(opts, "email"),
            create_pr=bool(opts.get("create_pr", False)), dry_run=dry_run,
        )
    if subcmd == "delegate-to-child":
        vf = ("--to-child", "--task", "--source", "--ticket", "--priority", "--surface", "--email")
        tdir, opts = _pos_opts(repo_dir, subcmd, rest, vf, ("--force", "--create-pr"))
        u_msg = "Usage: ./scripts/layer-config.sh delegate-to-child [<dir>] --to-child <layer>"
        child = _req_opt(opts, "to_child", u_msg)
        if not opts.get("task") and not opts.get("source"):
            raise _CLIUsageError(u_msg)
        return workflow_engine.delegate_directive_to_child(
            tdir, child_layer=child, directive=str(opts.get("task", "")),
            source_rel_path=_opt_str(opts, "source"), ticket_id=_opt_str(opts, "ticket"),
            priority=str(opts.get("priority", "P1")),
            tracker=str(opts.get("surface", "WORKTASK.md")),
            actor_email=_opt_str(opts, "email"), force_overwrite=bool(opts.get("force", False)),
            create_pr=bool(opts.get("create_pr", False)), dry_run=dry_run,
        )
    if subcmd == "promote-from-project":
        tdir = _req_pos(
            rest, "promote-from-project <target-project-dir> --source <rel-path> [options]"
        )
        vf = (
            "--source", "--to-layer", "--to-template", "--upstream-dir",
            "--email", "--org", "--contributors", "--context",
        )
        opts = _parse_opts(subcmd, rest[1:], vf, ("--create-pr", "--force"))
        src = _req_opt(
            opts, "source", "Missing required --source <rel-path> for promote-from-project."
        )
        return promotion_engine.promote_project_asset_to_layer(
            repo_dir, tdir, source_rel_path=src, target_layer=str(opts.get("to_layer", "root")),
            target_template=_opt_str(opts, "to_template"),
            upstream_dir=_opt_path(opts, "upstream_dir"),
            prepare_pr=bool(opts.get("create_pr", False)), actor_email=_opt_str(opts, "email"),
            contributing_org=_opt_str(opts, "org"), contributors=_opt_str(opts, "contributors"),
            validation_context=_opt_str(opts, "context"),
            force_overwrite=bool(opts.get("force", False)), dry_run=dry_run,
        )
    if subcmd == "manage-roster":
        vf = ("--add", "--remove", "--role", "--title", "--squad")
        tdir, opts = _pos_opts(repo_dir, subcmd, rest, vf, ("--no-codeowners",))
        return git_governance_engine.manage_layer_roster(
            tdir, add_email=_opt_str(opts, "add"), remove_email=_opt_str(opts, "remove"),
            member_role=str(opts.get("role", "member")), title=str(opts.get("title", "")),
            squad=str(opts.get("squad", "")), dry_run=dry_run,
        )
    if subcmd == "set-authority":
        tdir, opts = _pos_opts(repo_dir, subcmd, rest, ("--owner-role", "--emails", "--contact"))
        role = _req_opt(
            opts, "owner_role", "Missing required --owner-role <role> for set-authority."
        )
        return authority_engine.configure_layer_authority(
            tdir, owner_role=role, authorized_emails=_csv(opts.get("emails")) or [],
            escalation_contact=_opt_str(opts, "contact"), dry_run=dry_run,
        )
    if subcmd == "configure-git-policy":
        tdir, opts = _pos_opts(
            repo_dir, subcmd, rest, ("--protected",), ("--no-codeowners", "--no-require-pr")
        )
        return git_governance_engine.configure_git_governance_policy(
            tdir, protected_branches=_csv(opts.get("protected")),
            require_pr_on_protected=not bool(opts.get("no_require_pr", False)),
            sync_codeowners=not bool(opts.get("no_codeowners", False)), dry_run=dry_run,
        )
    if subcmd == "check-env-promotion":
        vf = ("--to-env", "--branch", "--email", "--parent-dir", "--files")
        tdir, opts = _pos_opts(repo_dir, subcmd, rest, vf)
        u_msg = "Usage: ./scripts/layer-config.sh check-env-promotion [<dir>] --to-env <env>"
        res = git_governance_engine.evaluate_environment_promotion(
            tdir, target_env=_req_opt(opts, "to_env", u_msg),
            current_branch=_opt_str(opts, "branch"), actor_email=_opt_str(opts, "email"),
            parent_dir=_opt_path(opts, "parent_dir"), changed_files=_csv(opts.get("files")),
            dry_run=dry_run,
        )
        if not res["allowed"]:
            msg = "Environment promotion blocked: " + "; ".join(res["failed_gates"])
            raise _CLIAuthorityBlockedError(res, msg)
        return res
    vf = ("--item", "--decision", "--reason", "--tracker", "--email")
    tdir, opts = _pos_opts(repo_dir, subcmd, rest, vf)
    u_msg = "Usage: ./scripts/layer-config.sh record-decision [<dir>] --item <ref> --decision <dec>"
    return git_governance_engine.record_governance_decision(
        tdir, item_ref=_req_opt(opts, "item", u_msg), decision=_req_opt(opts, "decision", u_msg),
        reason=_req_opt(opts, "reason", u_msg), tracker=str(opts.get("tracker", "WORKTASK.md")),
        actor_email=str(opts.get("email", "")), dry_run=dry_run,
    )


def _dispatch_ephemeral_subcommand(
    repo_dir: Path, dry_run: bool, subcmd: str, rest: list[str]
) -> dict[str, Any]:
    """Dispatch Ephemeral Department Bot subcommands (spawn, inspect, reap)."""
    if subcmd == "spawn-ephemeral":
        vf = ("--role", "--templates", "--layers", "--globs", "--project-bridge", "--tier", "--ttl")
        opts = _parse_opts(subcmd, rest, vf)
        role = _req_opt(opts, "role", "Missing required --role <bot-role> for spawn-ephemeral.")
        manifest = node_base.MCPNodeBase(repo_dir=repo_dir)._load_layer_manifest()
        return ephemeral_fork_engine.spawn_ephemeral_fork(
            repo_dir, manifest, bot_role=role,
            target_globs=_csv(opts.get("globs")), mount_templates=_csv(opts.get("templates")),
            mount_layers=_csv(opts.get("layers")),
            mount_project_rules_from=_opt_path(opts, "project_bridge"),
            model_tier=str(opts.get("tier", "flash")), ttl_seconds=int(str(opts.get("ttl", 300))),
            dry_run=dry_run,
        )
    if subcmd == "inspect-ephemeral":
        opts = _parse_opts(subcmd, rest, ("--id", "--family"), ("--catalog",))
        if opts.get("catalog"):
            forks = ephemeral_fork_engine.inspect_ephemeral_forks(repo_dir)["forks"]
            return capability_registry.resolve_mcp_capability_profile(
                node_base.MCPNodeBase(repo_dir=repo_dir)._load_layer_manifest(),
                active_ephemeral_forks=forks, family_filter=_opt_str(opts, "family"),
            )
        return ephemeral_fork_engine.inspect_ephemeral_forks(repo_dir, fork_id=_opt_str(opts, "id"))
    opts = _parse_opts(subcmd, rest, ("--id",))
    fid = _req_opt(opts, "id", "Missing required --id <fork-id|all> for reap-ephemeral.")
    return ephemeral_fork_engine.reap_ephemeral_fork(repo_dir, fork_id=fid, dry_run=dry_run)
# fmt: on


def dispatch_layer_config_cli(
    repo_dir: Path, dry_run: bool, subcmd: str, raw_args: list[str]
) -> tuple[int, dict[str, Any] | None, str | None]:
    """Route a layer-config.sh subcommand by family and return (exit_code, payload, error_msg)."""
    eff_dry = dry_run or "--dry-run" in raw_args or "-n" in raw_args
    rest = [a for a in raw_args if a not in ("--dry-run", "-n")]
    try:
        if subcmd in C1_DISCOVERY_SUBCOMMANDS:
            return 0, _dispatch_c1_subcommand(repo_dir, eff_dry, subcmd, rest), None
        if subcmd in C2_LIFECYCLE_SUBCOMMANDS:
            return 0, _dispatch_c2_subcommand(repo_dir, eff_dry, subcmd, rest), None
        if subcmd in C3_GOVERNANCE_SUBCOMMANDS:
            return 0, _dispatch_c3_subcommand(repo_dir, eff_dry, subcmd, rest), None
        if subcmd in EPHEMERAL_BOT_SUBCOMMANDS:
            return 0, _dispatch_ephemeral_subcommand(repo_dir, eff_dry, subcmd, rest), None
        raise _CLIUsageError(f"Unknown subcommand: {subcmd}")
    except _CLIAuthorityBlockedError as exc:
        return 2, exc.payload, exc.message
    except _CLIUsageError as exc:
        return 1, None, str(exc)


def main(argv: list[str]) -> int:
    """Execute the layer-config CLI dispatcher and write JSON/error output to stdio."""
    repo_dir = Path(argv[0]).resolve()
    tail = argv[1:]
    dry_run = tail[0].lower() == "true"
    sub_tail = tail[1:]
    code, payload, err_msg = dispatch_layer_config_cli(repo_dir, dry_run, sub_tail[0], sub_tail[1:])
    if err_msg is not None:
        print(f"❌ {err_msg}", file=sys.stderr)
    if payload is not None:
        print(json.dumps(payload, indent=2))
    return code
