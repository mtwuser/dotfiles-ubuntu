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
    assert len(init_files) == 3
    assert non_empty == []
