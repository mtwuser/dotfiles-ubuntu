"""Implementation tests for Bash CLI scripts and repository invariants.

Specification: docs/architecture/01_system_and_stow_engine.md
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

REPO_DIR = Path(__file__).resolve().parents[2]
CLI_SCRIPTS = [
    REPO_DIR / "bootstrap.sh",
    REPO_DIR / "backup.sh",
    REPO_DIR / "audit.sh",
    REPO_DIR / "scripts" / "verify-repo.sh",
    REPO_DIR / "scripts" / "layer-subtree.sh",
    REPO_DIR / "scripts" / "layer-config.sh",
    REPO_DIR / "scripts" / "workstation-sync.sh",
    REPO_DIR / "scripts" / "antigravity-install.sh",
    REPO_DIR / "scripts" / "audit-global-config.sh",
]


class TestCLIScripts:
    """Implementation tests for Bash CLI scripts and repository contracts."""

    @pytest.mark.parametrize("script_path", CLI_SCRIPTS, ids=lambda p: p.name)
    def test_cli_scripts_support_help_and_version_flags(self, script_path: Path) -> None:
        """Verify every CLI script supports --help and --version flags."""
        # Arrange
        expected_version = (REPO_DIR / "VERSION").read_text(encoding="utf-8").strip()

        # Act
        help_proc = subprocess.run(
            [str(script_path), "--help"],
            cwd=REPO_DIR,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        version_proc = subprocess.run(
            [str(script_path), "--version"],
            cwd=REPO_DIR,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

        # Assert
        assert help_proc.returncode == 0
        assert "Usage:" in help_proc.stdout
        assert version_proc.returncode == 0
        assert expected_version in version_proc.stdout

    @pytest.mark.parametrize("script_path", CLI_SCRIPTS, ids=lambda p: p.name)
    def test_cli_scripts_reject_unknown_flags(self, script_path: Path) -> None:
        """Verify every CLI script exits non-zero on unknown options."""
        # Arrange
        invalid_flag = "--definitely-invalid-flag"

        # Act
        proc = subprocess.run(
            [str(script_path), invalid_flag],
            cwd=REPO_DIR,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

        # Assert
        assert proc.returncode != 0
        assert "Unknown option" in proc.stderr

    def test_all_shell_scripts_pass_bash_syntax_check(self) -> None:
        """Verify all repository shell scripts pass bash -n syntax validation."""
        # Arrange
        sh_files = sorted(
            [
                REPO_DIR / "bootstrap.sh",
                REPO_DIR / "backup.sh",
                REPO_DIR / "audit.sh",
                *list((REPO_DIR / "scripts").glob("*.sh")),
                *list((REPO_DIR / "system" / "external").glob("*/*.sh")),
            ]
        )

        # Act
        failures = [
            str(sh.relative_to(REPO_DIR))
            for sh in sh_files
            if subprocess.run(["bash", "-n", str(sh)], check=False).returncode != 0
        ]

        # Assert
        assert len(sh_files) >= 16
        assert failures == []

    def test_layer_config_script_supports_list_init_scaffold_and_apply(
        self, tmp_path: Path
    ) -> None:
        """Verify layer-config.sh list-templates, init-fork, scaffold, apply, and bootstrap."""
        # Arrange
        script = str(REPO_DIR / "scripts" / "layer-config.sh")
        init_cmd = [
            script, "--dry-run", "init-fork", "--id", "acme-dept-design",
            "--role", "department", "--prune-default-templates",
        ]  # fmt: skip
        scaf_cmd = [
            script, "--dry-run", "scaffold-template", "brand-tokens",
            "--kind", "business-stack", "--register-binding",
        ]  # fmt: skip
        apply_cmd = [
            script, "--dry-run", "apply-project", str(tmp_path / "target_proj"),
            "--template", "fastapi-hexagonal",
        ]  # fmt: skip
        boot_cmd = [
            script, "--dry-run", "bootstrap-workspace", str(tmp_path / "dept_ws"),
            "--id", "dept-legal-ip", "--role", "domain-policy",
            "--precedence", "5", "--templates", "business-base",
        ]  # fmt: skip

        # Act
        list_proc = subprocess.run(
            [script, "list-templates"], cwd=REPO_DIR, capture_output=True, text=True
        )
        init_proc = subprocess.run(init_cmd, cwd=REPO_DIR, capture_output=True, text=True)
        scaffold_proc = subprocess.run(scaf_cmd, cwd=REPO_DIR, capture_output=True, text=True)
        apply_proc = subprocess.run(apply_cmd, cwd=REPO_DIR, capture_output=True, text=True)
        prof_proc = subprocess.run(
            [script, "--dry-run", "set-global-profile", "full"],
            cwd=REPO_DIR,
            capture_output=True,
            text=True,
        )
        boot_proc = subprocess.run(boot_cmd, cwd=REPO_DIR, capture_output=True, text=True)
        status_proc = subprocess.run(
            [script, "status"], cwd=REPO_DIR, capture_output=True, text=True
        )

        # Assert
        assert list_proc.returncode == 0
        for tpl in (
            "fastapi-hexagonal", "angular-web", "django-backend", "nist-csf-security",
            "human-base", "science-base", "software-engineering", "business-base",
        ):  # fmt: skip
            assert tpl in list_proc.stdout
        assert init_proc.returncode == 0 and '"precedence": 30' in init_proc.stdout
        assert scaffold_proc.returncode == 0 and '"template_id": "brand-tokens"' in (
            scaffold_proc.stdout
        )
        assert apply_proc.returncode == 0 and '"applied_template": "fastapi-hexagonal"' in (
            apply_proc.stdout
        )
        assert prof_proc.returncode == 0 and '"profile": "full"' in prof_proc.stdout
        assert boot_proc.returncode == 0 and '"layer_id": "dept-legal-ip"' in boot_proc.stdout
        assert status_proc.returncode == 0 and '"workspace_mode":' in status_proc.stdout

    def test_layer_subtree_script_supports_dry_run_and_list_commands(self) -> None:
        """Verify layer-subtree.sh list, pull-all, add, pull, push, and sync-upstream commands."""
        # Arrange
        script = str(REPO_DIR / "scripts" / "layer-subtree.sh")
        url = "https://example.com/dept-sec.git"

        # Act
        list_proc = subprocess.run([script, "list"], cwd=REPO_DIR, capture_output=True, text=True)
        pull_all_proc = subprocess.run(
            [script, "pull-all"], cwd=REPO_DIR, capture_output=True, text=True
        )
        add_proc = subprocess.run(
            [script, "--dry-run", "add", "dept-security", url, "main"],
            cwd=REPO_DIR,
            capture_output=True,
            text=True,
        )
        pull_proc = subprocess.run(
            [script, "--dry-run", "pull", "dept-security", url, "main"],
            cwd=REPO_DIR,
            capture_output=True,
            text=True,
        )
        push_proc = subprocess.run(
            [script, "--dry-run", "push", "dept-security", url, "feat/rule"],
            cwd=REPO_DIR,
            capture_output=True,
            text=True,
        )
        sync_proc = subprocess.run(
            [script, "--dry-run", "sync-upstream"], cwd=REPO_DIR, capture_output=True, text=True
        )
        bad_name_proc = subprocess.run(
            [script, "--dry-run", "add", "INVALID_NAME", "https://example.com/repo.git"],
            cwd=REPO_DIR,
            capture_output=True,
            text=True,
        )

        # Assert
        assert list_proc.returncode == 0 and "Mounted Context Subtree Layers" in list_proc.stdout
        assert pull_all_proc.returncode == 0 and "Pulling All Mounted Subtree Layers" in (
            pull_all_proc.stdout
        )
        assert add_proc.returncode == 0 and (
            f"[dry-run] git subtree add --prefix=layers/dept-security {url} main --squash"
            in add_proc.stdout
        )
        assert pull_proc.returncode == 0 and (
            f"[dry-run] git subtree pull --prefix=layers/dept-security {url} main --squash"
            in pull_proc.stdout
        )
        assert push_proc.returncode == 0 and (
            f"[dry-run] git subtree push --prefix=layers/dept-security {url} feat/rule"
            in push_proc.stdout
        )
        assert sync_proc.returncode == 0 and "[dry-run] git pull --ff-only" in sync_proc.stdout
        assert bad_name_proc.returncode != 0 and "kebab-case" in bad_name_proc.stderr

    def test_layer_subtree_auto_resolves_upstream_url_for_pull_push_and_pull_all(
        self,
        tmp_path: Path,
    ) -> None:
        """Verify layer-subtree.sh auto-resolves upstream repository URLs from mcp-layer.json."""
        # Arrange
        script = str(REPO_DIR / "scripts" / "layer-subtree.sh")
        (tmp_path / "VERSION").write_text("1.4.0\n", encoding="utf-8")
        dept_sys = tmp_path / "layers" / "dept-data" / "system"
        dept_sys.mkdir(parents=True)
        (dept_sys / "mcp-layer.json").write_text(
            '{"layer_id": "acme-dept-data", "layer_role": "department", '
            '"upstream_layer": {"repository": "https://example.com/dept-data.git", '
            '"branch": "main"}}',
            encoding="utf-8",
        )
        no_ver_dir = tmp_path / "no_ver_repo"
        no_ver_dir.mkdir(parents=True)
        sys_path = os.environ.get("PATH", "/usr/bin:/bin")
        env = {"PATH": sys_path, "DOTFILES_REPO_DIR": str(tmp_path)}
        no_ver_env = {"PATH": sys_path, "DOTFILES_REPO_DIR": str(no_ver_dir)}

        # Act
        no_ver_proc = subprocess.run(
            [script, "--version"], cwd=no_ver_dir, env=no_ver_env, capture_output=True, text=True
        )
        list_proc = subprocess.run(
            [script, "list"], cwd=tmp_path, env=env, capture_output=True, text=True
        )
        pull_auto = subprocess.run(
            [script, "--dry-run", "pull", "dept-data"],
            cwd=tmp_path,
            env=env,
            capture_output=True,
            text=True,
        )
        push_auto = subprocess.run(
            [script, "--dry-run", "push", "dept-data", "feat/promote-rule"],
            cwd=tmp_path,
            env=env,
            capture_output=True,
            text=True,
        )
        pull_all = subprocess.run(
            [script, "--dry-run", "pull-all"],
            cwd=tmp_path,
            env=env,
            capture_output=True,
            text=True,
        )

        # Assert
        assert no_ver_proc.returncode == 0 and no_ver_proc.stderr == ""
        assert "unknown" in no_ver_proc.stdout
        assert list_proc.returncode == 0
        assert "layers/dept-data  [id=acme-dept-data, role=department" in list_proc.stdout
        assert pull_auto.returncode == 0 and (
            "[dry-run] git subtree pull --prefix=layers/dept-data "
            "https://example.com/dept-data.git main --squash" in pull_auto.stdout
        )
        assert push_auto.returncode == 0 and (
            "[dry-run] git subtree push --prefix=layers/dept-data "
            "https://example.com/dept-data.git feat/promote-rule" in push_auto.stdout
        )
        assert pull_all.returncode == 0 and (
            "[dry-run] git subtree pull --prefix=layers/dept-data "
            "https://example.com/dept-data.git main --squash" in pull_all.stdout
        )

    def test_dockerfile_dockerignore_and_makefile_docker_targets_contract(self) -> None:
        """Verify Dockerfile, .dockerignore, and Makefile preserve Ubuntu 26.04 and MCP targets."""
        # Arrange
        dockerfile = REPO_DIR / "Dockerfile"
        dockerignore = REPO_DIR / ".dockerignore"
        makefile = REPO_DIR / "Makefile"

        # Act
        df_text = dockerfile.read_text(encoding="utf-8")
        di_text = dockerignore.read_text(encoding="utf-8")
        mk_text = makefile.read_text(encoding="utf-8")

        # Assert
        assert "FROM ubuntu:26.04" in df_text
        assert "WORKDIR /opt/dotfiles-ubuntu" in df_text
        assert "USER ubuntu" in df_text
        assert (
            'ENTRYPOINT ["python3", "/opt/dotfiles-ubuntu/scripts/dotfiles_mcp_server.py"]'
            in df_text
        )
        assert "composed global profile:" in (REPO_DIR / "audit.sh").read_text(encoding="utf-8")
        assert "STOW_BASE_DIR=" in (REPO_DIR / "audit.sh").read_text(encoding="utf-8")
        for ign in (".git/", "venv/", "tests/"):
            assert ign in di_text
        for target in (
            "docker-build:", "docker-self-test:", "docker-mcp:", "setup-dev reset-dev:",
            "publish-oss:", "workstation-setup:", "workstation-sync:", "workstation-status:",
        ):  # fmt: skip
            assert target in mk_text

    def test_workstation_sync_script_setup_status_and_auto(self, tmp_path: Path) -> None:
        """Verify workstation-sync.sh --setup, --auto, and --status lifecycle."""
        # Arrange
        script = str(REPO_DIR / "scripts" / "workstation-sync.sh")
        runtime_dir = tmp_path / "dotfiles-ubuntu"
        runtime_dir.mkdir(parents=True)
        (runtime_dir / "VERSION").write_text("2.2.1\n", encoding="utf-8")
        conf_file = tmp_path / "workstation.conf"
        stamp_dir = tmp_path / "runtime"
        stamp_dir.mkdir(parents=True)
        env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": str(tmp_path),
            "DOTFILES_RUNTIME_DIR": str(runtime_dir), "DOTFILES_WORKSTATION_CONF": str(conf_file),
            "XDG_RUNTIME_DIR": str(stamp_dir), "DOTFILES_SKIP_PULL": "1", "DOTFILES_SKIP_STOW": "1",
        }  # fmt: skip

        # Act
        setup_cmd = [
            script, "--setup", "--mode", "readonly", "--profile",
            "science", "--auto-sync", "boot", "--no-sync",
        ]  # fmt: skip
        setup_proc = subprocess.run(
            setup_cmd, cwd=REPO_DIR, env=env, capture_output=True, text=True
        )
        auto_proc = subprocess.run(
            [script, "--auto"], cwd=REPO_DIR, env=env, capture_output=True, text=True
        )
        status_proc = subprocess.run(
            [script, "--status"], cwd=REPO_DIR, env=env, capture_output=True, text=True
        )
        pub_env = {**env, "DOTFILES_SKIP_VERIFY": "1"}
        pub_proc = subprocess.run(
            [script, "--publish-oss", "--dry-run", "--remote", str(runtime_dir)],
            cwd=REPO_DIR, env=pub_env, capture_output=True, text=True,
        )  # fmt: skip
        blk_no_ver = subprocess.run(
            [script, "--publish-oss", "--remote", str(runtime_dir)],
            cwd=REPO_DIR, env=pub_env, capture_output=True, text=True,
        )  # fmt: skip
        unrel_cl = tmp_path / "CHANGELOG_UNREL.md"
        unrel_cl.write_text("## [Unreleased]\n- Pending item\n", encoding="utf-8")
        cur_ver = (REPO_DIR / "VERSION").read_text(encoding="utf-8").strip()
        blk_unrel = subprocess.run(
            [script, "--publish-oss", "--release-version", cur_ver, "--remote", str(runtime_dir)],
            cwd=REPO_DIR, env={**pub_env, "DOTFILES_CHANGELOG_PATH": str(unrel_cl)},
            capture_output=True, text=True,
        )  # fmt: skip
        pers_env = {
            **pub_env, "DOTFILES_WORKSTATION_CONF": str(tmp_path / "none.conf"),
            "DOTFILES_WORKSTATION_MODE": "private", "DOTFILES_RUNTIME_DIR": str(REPO_DIR),
        }  # fmt: skip
        blk_pers = subprocess.run(
            [script, "--publish-oss", "--dry-run"],
            cwd=REPO_DIR, env=pers_env, capture_output=True, text=True,
        )  # fmt: skip

        # Assert
        assert setup_proc.returncode == 0 and "Workstation configuration" in setup_proc.stdout
        assert (
            auto_proc.returncode == 0 and status_proc.returncode == 0 and pub_proc.returncode == 0
        )
        assert blk_no_ver.returncode == 2 and "OSS_PUBLISH_GUARD_BLOCKED" in blk_no_ver.stderr
        assert blk_unrel.returncode == 2 and "OSS_UNRELEASED_CHANGELOG_BLOCKED" in blk_unrel.stderr
        assert blk_pers.returncode == 2 and "OSS_PERSONAL_REPO_PUBLISH_BLOCKED" in blk_pers.stderr
        assert (
            '"mode": "readonly"' in status_proc.stdout
            and '"profile": "science"' in status_proc.stdout
            and '"boot_synced": true' in status_proc.stdout
            and "[publish-oss --dry-run]" in pub_proc.stdout
        )

    def test_workstation_sync_never_locks_dev_repo_pushurl_and_heals_stale_guard(
        self, tmp_path: Path
    ) -> None:
        """Ensure workstation-sync.sh routes dev-* clones to runtime and heals dev pushurl."""
        # Arrange
        script = str(REPO_DIR / "scripts" / "workstation-sync.sh")
        runtime_dir, dev_dir = tmp_path / "sample-repo", tmp_path / "Projects" / "dev-sample-repo"
        (runtime_dir / "system").mkdir(parents=True)
        (runtime_dir / "templates" / "obsolete-dir").mkdir(parents=True)
        (runtime_dir / "templates" / "obsolete-dir" / "stale.md").write_text(
            "x\n", encoding="utf-8"
        )
        (dev_dir / "system").mkdir(parents=True)
        (runtime_dir / "VERSION").write_text("2.4.0\n", encoding="utf-8")
        (runtime_dir / "system/mcp-layer.json").write_text(
            '{"layer_id": "workstation-user-pc", "entity_kind": "individual", "precedence": 90}\n',
            encoding="utf-8",
        )
        (dev_dir / "VERSION").write_text("3.0.3\n", encoding="utf-8")
        (dev_dir / "WORKTASK.md").write_text("# Private Dev Task\n", encoding="utf-8")
        (dev_dir / "system/mcp-layer.json").write_text(
            '{"layer_id": "dotfiles-ubuntu-default", "precedence": 10}\n',
            encoding="utf-8",
        )
        git_cmds = (
            ["init", "-q"], ["config", "user.email", "t@e.com"],
            ["config", "user.name", "T"], ["add", "-A"], ["commit", "-m", "i", "-q"],
            ["remote", "add", "origin", "https://example.com/repo.git"],
        )  # fmt: skip
        for rdir in (runtime_dir, dev_dir):
            for c in git_cmds:
                subprocess.run(["/usr/bin/git", *c], cwd=rdir, check=True)
        guard_val = "VALIDATION_BLOCKED_READONLY_RUNTIME"
        subprocess.run(
            ["/usr/bin/git", "config", "remote.origin.pushurl", guard_val], cwd=dev_dir, check=True
        )
        env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": str(tmp_path),
            "DOTFILES_RUNTIME_DIR": str(runtime_dir),
            "DOTFILES_WORKSTATION_CONF": str(tmp_path / "workstation.conf"),
            "XDG_RUNTIME_DIR": str(tmp_path / "rt"),
            "DOTFILES_SKIP_PULL": "1", "DOTFILES_SKIP_STOW": "1",
        }  # fmt: skip

        # Act
        sync_proc = subprocess.run(
            [script, "--sync"], cwd=dev_dir, env=env, capture_output=True, text=True
        )
        rt_pushurl = subprocess.run(
            ["/usr/bin/git", "config", "--get", "remote.origin.pushurl"],
            cwd=runtime_dir, capture_output=True, text=True,
        )  # fmt: skip
        dev_pushurl = subprocess.run(
            ["/usr/bin/git", "config", "--get", "remote.origin.pushurl"],
            cwd=dev_dir, capture_output=True, text=True,
        )  # fmt: skip

        # Assert
        assert sync_proc.returncode == 0
        assert (runtime_dir / "VERSION").read_text(encoding="utf-8").strip() == "3.0.3"
        assert not (runtime_dir / "WORKTASK.md").exists()
        assert not (runtime_dir / "templates" / "obsolete-dir").exists()
        assert '"layer_id": "workstation-user-pc"' in (
            runtime_dir / "system/mcp-layer.json"
        ).read_text(encoding="utf-8")
        assert rt_pushurl.stdout.strip() == guard_val
        assert dev_pushurl.returncode != 0 and dev_pushurl.stdout.strip() == ""
