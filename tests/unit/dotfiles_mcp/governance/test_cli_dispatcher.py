"""Unit tests for scripts/dotfiles_mcp/governance/cli_dispatcher.py.

Specification: docs/architecture/06_layer_governance_and_promotion_engines.md
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from dotfiles_mcp.core import manifest_helpers
from dotfiles_mcp.governance import (
    authority_engine,
    cli_dispatcher,
    fork_configurator,
    git_governance_engine,
    horizon_engine,
    promotion_engine,
    workflow_engine,
    workspace_bootstrapper,
)
from dotfiles_mcp.mcp_node import capability_registry, ephemeral_fork_engine, node_base


class TestCliDispatcher:
    """1:1 unit tests for cli_dispatcher (C1/C2/C3/Ephemeral routing & exit codes)."""

    def test_dispatch_c1_subcommands_routes_all_seven_read_only_commands(
        self, tmp_path: Path
    ) -> None:
        """Verify all 7 C1 subcommands route to their corresponding engines with parsed options."""
        # Arrange
        proj_with_m = tmp_path / "proj_m"
        (proj_with_m / "system").mkdir(parents=True)
        (proj_with_m / "system/mcp-layer.json").write_text('{"layer_role": "squad"}', "utf-8")
        proj_no_m = tmp_path / "proj_no_m"
        proj_no_m.mkdir()

        with (
            patch.object(node_base.MCPNodeBase, "_discover_mounted_layers", return_value=[]),
            patch.object(
                manifest_helpers,
                "discover_templates_catalog",
                return_value=[{"name": "t1"}],
            ),
            patch.object(
                workspace_bootstrapper, "inspect_workspace_status", return_value={"status": "ok"}
            ),
            patch.object(horizon_engine, "inspect_layer_horizon", return_value={"horizon": "ok"}),
            patch.object(
                horizon_engine, "compare_upstream_templates", return_value={"compare": "ok"}
            ),
            patch.object(
                promotion_engine, "diff_project_against_layers", return_value={"diff": "ok"}
            ) as mock_diff,
            patch.object(
                authority_engine,
                "verify_layer_operation_authority",
                return_value={"allowed": True, "remediation": ""},
            ),
            patch.object(
                workflow_engine, "consult_layer_ephemeral", return_value={"consult": "ok"}
            ),
        ):
            # Act
            c_lt1, p_lt1, _ = cli_dispatcher.dispatch_layer_config_cli(
                tmp_path, True, "list-templates", []
            )
            c_lt2, _, _ = cli_dispatcher.dispatch_layer_config_cli(
                tmp_path, False, "list-templates", [str(proj_no_m), "--dry-run"]
            )
            c_st, _, _ = cli_dispatcher.dispatch_layer_config_cli(
                tmp_path, True, "status", ["--parent-dir", str(tmp_path)]
            )
            c_ih, _, _ = cli_dispatcher.dispatch_layer_config_cli(
                tmp_path, True, "inspect-horizon", [str(proj_no_m), "--email", "a@b.c"]
            )
            c_cu, _, _ = cli_dispatcher.dispatch_layer_config_cli(
                tmp_path, True, "compare-upstream", ["--template", "t1", "--apply-safe"]
            )
            c_dp1, _, _ = cli_dispatcher.dispatch_layer_config_cli(
                tmp_path, True, "diff-project", [str(proj_with_m)]
            )
            c_dp2, _, _ = cli_dispatcher.dispatch_layer_config_cli(
                tmp_path, True, "diff-project", [str(proj_no_m)]
            )
            c_ca, _, _ = cli_dispatcher.dispatch_layer_config_cli(
                tmp_path, True, "check-authority", ["--op", "sync-layer", "--email", "a@b.c"]
            )
            c_cl, _, _ = cli_dispatcher.dispatch_layer_config_cli(
                tmp_path, True, "consult-layer", ["--layer", "corp", "--query", "policy?"]
            )

        # Assert
        assert (c_lt1, c_lt2, c_st, c_ih, c_cu, c_dp1, c_dp2, c_ca, c_cl) == (0,) * 9
        assert p_lt1 == {
            "count": 1,
            "templates": [{"name": "t1"}],
            "federated_mcps": [],
            "ephemeral_bots": [],
        }
        assert mock_diff.call_count == 2

    def test_dispatch_c2_subcommands_routes_all_eight_lifecycle_commands(
        self, tmp_path: Path
    ) -> None:
        """Verify all 8 C2 lifecycle subcommands route with positional/flag variations."""
        # Arrange
        non_ws = tmp_path / "non_ws"
        (non_ws / "system").mkdir(parents=True)
        (non_ws / "system/mcp-layer.json").write_text('{"layer_role": "department"}', "utf-8")
        plain = tmp_path / "plain"
        plain.mkdir()

        with (
            patch.object(
                workspace_bootstrapper, "bootstrap_layer_workspace", return_value={"boot": True}
            ),
            patch.object(
                workspace_bootstrapper, "sync_layer_workspace", return_value={"sync": True}
            ),
            patch.object(fork_configurator, "apply_fork_to_project", return_value={"apply": True}),
            patch.object(
                workspace_bootstrapper, "set_global_agents_profile", return_value={"prof": True}
            ),
            patch.object(workflow_engine, "start_task_workflow", return_value={"task": True}),
            patch.object(
                authority_engine,
                "verify_layer_operation_authority",
                return_value={"allowed": True, "remediation": ""},
            ),
            patch.object(fork_configurator, "scaffold_template_pack", return_value={"scaf": True}),
            patch.object(
                fork_configurator, "configure_fork_manifest", return_value={"layer_id": "x"}
            ),
            patch.object(
                workspace_bootstrapper, "register_mounted_subtree", return_value={"reg": True}
            ) as mock_reg,
        ):
            # Act
            c1, _, _ = cli_dispatcher.dispatch_layer_config_cli(
                tmp_path,
                True,
                "bootstrap-workspace",
                [
                    str(plain),
                    "--id",
                    "dept-a",
                    "--precedence",
                    "30",
                    "--templates",
                    "t1,t2",
                    "--no-scaffold-own",
                ],
            )
            c2, _, _ = cli_dispatcher.dispatch_layer_config_cli(
                tmp_path, True, "sync-layer", ["--strategy", "reconcile"]
            )
            c3, _, _ = cli_dispatcher.dispatch_layer_config_cli(
                tmp_path, True, "apply-project", [str(non_ws)]
            )
            c4, _, _ = cli_dispatcher.dispatch_layer_config_cli(
                tmp_path, True, "apply-project", [str(plain), "--parent-dir", str(tmp_path)]
            )
            c5, _, _ = cli_dispatcher.dispatch_layer_config_cli(
                tmp_path, True, "apply-project", [str(plain), "--include-defaults"]
            )
            c6, _, _ = cli_dispatcher.dispatch_layer_config_cli(
                tmp_path, True, "set-global-profile", ["technical", "--stow"]
            )
            c7, _, _ = cli_dispatcher.dispatch_layer_config_cli(
                tmp_path, True, "start-task", ["--task", "T-1"]
            )
            c8, _, _ = cli_dispatcher.dispatch_layer_config_cli(
                tmp_path, True, "scaffold-template", ["my-pack", "--register-binding"]
            )
            c9, p9, _ = cli_dispatcher.dispatch_layer_config_cli(
                tmp_path, True, "init-fork", ["--id", "sq-1", "--precedence", "60"]
            )
            c10, _, _ = cli_dispatcher.dispatch_layer_config_cli(
                tmp_path, True, "init-fork", ["--id", "sq-2"]
            )
            c11, _, _ = cli_dispatcher.dispatch_layer_config_cli(
                tmp_path, True, "register-subtree", ["corp", "https://example.com/r.git"]
            )
            c12, _, _ = cli_dispatcher.dispatch_layer_config_cli(
                tmp_path, True, "register-subtree", ["corp", "https://example.com/r.git", "main"]
            )

        # Assert
        assert (c1, c2, c3, c4, c5, c6, c7, c8, c9, c10, c11, c12) == (0,) * 12
        assert p9 == {"dry_run": True, "manifest": {"layer_id": "x"}}
        assert mock_reg.call_count == 2

    def test_dispatch_c3_and_ephemeral_subcommands_routes_all_eleven_commands(
        self, tmp_path: Path
    ) -> None:
        """Verify all 8 C3 governance and 3 Ephemeral Bot subcommands route cleanly."""
        # Arrange
        with (
            patch.object(workflow_engine, "complete_task_workflow", return_value={"done": True}),
            patch.object(
                workflow_engine, "delegate_directive_to_child", return_value={"del": True}
            ),
            patch.object(
                promotion_engine, "promote_project_asset_to_layer", return_value={"prom": True}
            ),
            patch.object(git_governance_engine, "manage_layer_roster", return_value={"rost": True}),
            patch.object(
                authority_engine, "configure_layer_authority", return_value={"auth": True}
            ),
            patch.object(authority_engine, "resolve_git_user_email", return_value="git@x.io"),
            patch.object(
                git_governance_engine, "configure_git_governance_policy", return_value={"git": True}
            ),
            patch.object(
                git_governance_engine,
                "evaluate_environment_promotion",
                return_value={"allowed": True, "failed_gates": []},
            ),
            patch.object(
                git_governance_engine, "record_governance_decision", return_value={"rec": True}
            ),
            patch.object(node_base.MCPNodeBase, "_load_layer_manifest", return_value={}),
            patch.object(ephemeral_fork_engine, "spawn_ephemeral_fork", return_value={"sp": True}),
            patch.object(
                ephemeral_fork_engine, "inspect_ephemeral_forks", return_value={"forks": []}
            ),
            patch.object(
                capability_registry, "resolve_mcp_capability_profile", return_value={"cap": True}
            ),
            patch.object(ephemeral_fork_engine, "reap_ephemeral_fork", return_value={"reap": True}),
        ):
            # Act
            r1, _, _ = cli_dispatcher.dispatch_layer_config_cli(
                tmp_path, True, "complete-task", ["--task", "T-1", "--create-pr"]
            )
            r2, _, _ = cli_dispatcher.dispatch_layer_config_cli(
                tmp_path,
                True,
                "delegate-to-child",
                ["--to-child", "dept-a", "--task", "Do X", "--force"],
            )
            r3, _, _ = cli_dispatcher.dispatch_layer_config_cli(
                tmp_path,
                True,
                "promote-from-project",
                [str(tmp_path), "--source", "README.md", "--force"],
            )
            r4, _, _ = cli_dispatcher.dispatch_layer_config_cli(
                tmp_path, True, "manage-roster", ["--add", "u@x.io", "--no-codeowners"]
            )
            r5, _, _ = cli_dispatcher.dispatch_layer_config_cli(
                tmp_path, True, "set-authority", ["--owner-role", "dept", "--emails", "a@x.io"]
            )
            r6, _, _ = cli_dispatcher.dispatch_layer_config_cli(
                tmp_path, True, "configure-git-policy", ["--protected", "main", "--no-require-pr"]
            )
            r7, _, _ = cli_dispatcher.dispatch_layer_config_cli(
                tmp_path,
                True,
                "check-env-promotion",
                ["--to-env", "tst", "--files", "corporate/policy.md"],
            )
            r8, _, _ = cli_dispatcher.dispatch_layer_config_cli(
                tmp_path,
                True,
                "record-decision",
                ["--item", "X", "--decision", "ACCEPT", "--reason", "ok"],
            )
            r9, _, _ = cli_dispatcher.dispatch_layer_config_cli(
                tmp_path, True, "spawn-ephemeral", ["--role", "qa-bot"]
            )
            r10, _, _ = cli_dispatcher.dispatch_layer_config_cli(
                tmp_path, True, "inspect-ephemeral", ["--catalog"]
            )
            r11, _, _ = cli_dispatcher.dispatch_layer_config_cli(
                tmp_path, True, "inspect-ephemeral", ["--id", "f-1"]
            )
            r12, _, _ = cli_dispatcher.dispatch_layer_config_cli(
                tmp_path, True, "reap-ephemeral", ["--id", "all"]
            )

        # Assert
        assert (r1, r2, r3, r4, r5, r6, r7, r8, r9, r10, r11, r12) == (0,) * 12

    def test_dispatch_usage_and_authority_errors_return_exit_codes_1_and_2(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Verify invalid flags/missing args return code 1 and blocked gates return code 2."""
        # Arrange / Act: usage errors (code 1)
        u1 = cli_dispatcher.dispatch_layer_config_cli(tmp_path, True, "unknown-cmd", [])
        u2 = cli_dispatcher.dispatch_layer_config_cli(tmp_path, True, "status", ["--bad-flag"])
        u3 = cli_dispatcher.dispatch_layer_config_cli(tmp_path, True, "diff-project", [])
        u4 = cli_dispatcher.dispatch_layer_config_cli(tmp_path, True, "check-authority", [])
        u5 = cli_dispatcher.dispatch_layer_config_cli(tmp_path, True, "set-global-profile", [])
        u6 = cli_dispatcher.dispatch_layer_config_cli(
            tmp_path, True, "register-subtree", ["only-one"]
        )
        u7 = cli_dispatcher.dispatch_layer_config_cli(
            tmp_path, True, "delegate-to-child", ["--to-child", "c"]
        )

        with (
            patch.object(
                authority_engine,
                "verify_layer_operation_authority",
                return_value={"allowed": False, "remediation": "Denied by owner"},
            ),
            patch.object(
                git_governance_engine,
                "evaluate_environment_promotion",
                return_value={"allowed": False, "failed_gates": ["Protected branch"]},
            ),
        ):
            # Act: authority / promotion blocks (code 2) and main() stdio contract
            b1 = cli_dispatcher.dispatch_layer_config_cli(
                tmp_path, True, "check-authority", ["--op", "init-fork"]
            )
            b2 = cli_dispatcher.dispatch_layer_config_cli(
                tmp_path, True, "init-fork", ["--id", "x"]
            )
            m_ok = cli_dispatcher.main([str(tmp_path), "true", "inspect-ephemeral"])
            m_err = cli_dispatcher.main([str(tmp_path), "false", "unknown-cmd"])
            m_blk = cli_dispatcher.main(
                [str(tmp_path), "true", "check-env-promotion", "--to-env", "pro"]
            )

        captured = capsys.readouterr()

        # Assert
        assert all(res[0] == 1 and res[1] is None for res in (u1, u2, u3, u4, u5, u6, u7))
        assert b1[0] == 2 and b2[0] == 2
        assert (m_ok, m_err, m_blk) == (0, 1, 2)
        assert "❌ Unknown subcommand: unknown-cmd" in captured.err
        assert "❌ Environment promotion blocked: Protected branch" in captured.err
        assert json.loads(captured.out.split("\n}\n")[0] + "\n}")["forks"] == []
