"""Implementation/integration tests for Bash CLI scripts and repository invariants."""

from __future__ import annotations

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
]


@pytest.mark.parametrize("script_path", CLI_SCRIPTS, ids=lambda p: p.name)
def test_cli_scripts_support_help_and_version_flags(script_path: Path) -> None:
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
def test_cli_scripts_reject_unknown_flags(script_path: Path) -> None:
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


def test_all_shell_scripts_pass_bash_syntax_check() -> None:
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


def test_layer_config_script_supports_list_init_scaffold_and_apply(tmp_path: Path) -> None:
    # Arrange
    script = str(REPO_DIR / "scripts" / "layer-config.sh")

    # Act
    list_proc = subprocess.run(
        [script, "list-templates"], cwd=REPO_DIR, capture_output=True, text=True
    )
    init_proc = subprocess.run(
        [
            script,
            "--dry-run",
            "init-fork",
            "--id",
            "acme-dept-design",
            "--role",
            "department",
            "--prune-default-templates",
        ],
        cwd=REPO_DIR,
        capture_output=True,
        text=True,
    )
    scaffold_proc = subprocess.run(
        [
            script,
            "--dry-run",
            "scaffold-template",
            "brand-tokens",
            "--kind",
            "department-pack",
            "--register-binding",
        ],
        cwd=REPO_DIR,
        capture_output=True,
        text=True,
    )
    apply_proc = subprocess.run(
        [
            script,
            "--dry-run",
            "apply-project",
            str(tmp_path / "target_proj"),
            "--template",
            "fastapi-hexagonal",
        ],
        cwd=REPO_DIR,
        capture_output=True,
        text=True,
    )

    # Assert
    assert list_proc.returncode == 0
    assert "fastapi-hexagonal" in list_proc.stdout
    assert init_proc.returncode == 0
    assert '"precedence": 30' in init_proc.stdout
    assert scaffold_proc.returncode == 0
    assert '"template_id": "brand-tokens"' in scaffold_proc.stdout
    assert apply_proc.returncode == 0
    assert '"applied_template": "fastapi-hexagonal"' in apply_proc.stdout


def test_layer_subtree_script_supports_dry_run_and_list_commands() -> None:
    # Arrange
    script = str(REPO_DIR / "scripts" / "layer-subtree.sh")

    # Act
    list_proc = subprocess.run([script, "list"], cwd=REPO_DIR, capture_output=True, text=True)
    pull_all_proc = subprocess.run(
        [script, "pull-all"], cwd=REPO_DIR, capture_output=True, text=True
    )
    add_proc = subprocess.run(
        [
            script,
            "--dry-run",
            "add",
            "dept-security",
            "https://example.com/dept-sec.git",
            "main",
        ],
        cwd=REPO_DIR,
        capture_output=True,
        text=True,
    )
    pull_proc = subprocess.run(
        [
            script,
            "--dry-run",
            "pull",
            "dept-security",
            "https://example.com/dept-sec.git",
            "main",
        ],
        cwd=REPO_DIR,
        capture_output=True,
        text=True,
    )
    push_proc = subprocess.run(
        [
            script,
            "--dry-run",
            "push",
            "dept-security",
            "https://example.com/dept-sec.git",
            "feat/rule",
        ],
        cwd=REPO_DIR,
        capture_output=True,
        text=True,
    )
    sync_proc = subprocess.run(
        [script, "--dry-run", "sync-upstream"],
        cwd=REPO_DIR,
        capture_output=True,
        text=True,
    )
    bad_name_proc = subprocess.run(
        [script, "--dry-run", "add", "INVALID_NAME", "https://example.com/repo.git"],
        cwd=REPO_DIR,
        capture_output=True,
        text=True,
    )

    # Assert
    assert list_proc.returncode == 0
    assert "Mounted Context Subtree Layers" in list_proc.stdout
    assert pull_all_proc.returncode == 0
    assert "Pulling All Mounted Subtree Layers" in pull_all_proc.stdout
    assert add_proc.returncode == 0
    assert (
        "[dry-run] git subtree add --prefix=layers/dept-security "
        "https://example.com/dept-sec.git main --squash" in add_proc.stdout
    )
    assert pull_proc.returncode == 0
    assert (
        "[dry-run] git subtree pull --prefix=layers/dept-security "
        "https://example.com/dept-sec.git main --squash" in pull_proc.stdout
    )
    assert push_proc.returncode == 0
    assert (
        "[dry-run] git subtree push --prefix=layers/dept-security "
        "https://example.com/dept-sec.git feat/rule" in push_proc.stdout
    )
    assert sync_proc.returncode == 0
    assert "[dry-run] git pull --ff-only" in sync_proc.stdout
    assert bad_name_proc.returncode != 0
    assert "kebab-case" in bad_name_proc.stderr


def test_layer_subtree_auto_resolves_upstream_url_for_pull_push_and_pull_all(
    tmp_path: Path,
) -> None:
    # Arrange
    script = str(REPO_DIR / "scripts" / "layer-subtree.sh")
    (tmp_path / "VERSION").write_text("1.4.0\n", encoding="utf-8")
    dept_sys = tmp_path / "layers" / "dept-data" / "system"
    dept_sys.mkdir(parents=True)
    (dept_sys / "mcp-layer.json").write_text(
        '{"layer_id": "acme-dept-data", "layer_role": "department", '
        '"upstream_layer": {"repository": "https://example.com/dept-data.git", "branch": "main"}}',
        encoding="utf-8",
    )
    env = {"PATH": "/usr/bin:/bin", "DOTFILES_REPO_DIR": str(tmp_path)}

    # Act
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
    assert list_proc.returncode == 0
    assert "layers/dept-data  [id=acme-dept-data, role=department" in list_proc.stdout
    assert pull_auto.returncode == 0
    assert (
        "[dry-run] git subtree pull --prefix=layers/dept-data "
        "https://example.com/dept-data.git main --squash" in pull_auto.stdout
    )
    assert push_auto.returncode == 0
    assert (
        "[dry-run] git subtree push --prefix=layers/dept-data "
        "https://example.com/dept-data.git feat/promote-rule" in push_auto.stdout
    )
    assert pull_all.returncode == 0
    assert (
        "[dry-run] git subtree pull --prefix=layers/dept-data "
        "https://example.com/dept-data.git main --squash" in pull_all.stdout
    )


def test_dockerfile_dockerignore_and_makefile_docker_targets_contract() -> None:
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
        'ENTRYPOINT ["python3", "/opt/dotfiles-ubuntu/scripts/dotfiles_mcp_server.py"]' in df_text
    )
    assert ".git/" in di_text
    assert "venv/" in di_text
    assert "tests/" in di_text
    assert "docker-build:" in mk_text
    assert "docker-self-test:" in mk_text
    assert "docker-mcp:" in mk_text
