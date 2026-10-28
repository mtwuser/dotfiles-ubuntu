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


def test_all_test_init_files_are_strictly_zero_bytes() -> None:
    # Arrange
    init_files = sorted((REPO_DIR / "tests").rglob("__init__.py"))

    # Act
    non_empty = [str(p.relative_to(REPO_DIR)) for p in init_files if p.stat().st_size != 0]

    # Assert
    assert len(init_files) == 4
    assert non_empty == []


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
