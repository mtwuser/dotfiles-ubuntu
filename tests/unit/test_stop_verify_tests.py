"""Unit tests for stop_verify_tests.py (Stop lifecycle hook).

Specification: docs/architecture/02_antigravity_governance_and_hooks.md
"""

from __future__ import annotations

import io
import json
import subprocess
from typing import TYPE_CHECKING

import stop_verify_tests

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


class TestStopVerifyTests:
    """1:1 unit test suite for stop_verify_tests.py."""

    def test_find_venv_returns_first_existing_venv(self, tmp_path: Path) -> None:
        """Discover the first existing virtualenv python binary across candidate workspaces."""
        # Arrange
        ws1 = tmp_path / "ws1"
        ws2 = tmp_path / "ws2"
        venv_py = ws2 / "venv" / "bin" / "python"
        venv_py.parent.mkdir(parents=True)
        venv_py.write_text("#!/bin/sh\n", encoding="utf-8")

        # Act
        found = stop_verify_tests.find_venv([str(ws1), str(ws2)])
        missing = stop_verify_tests.find_venv([str(ws1)])

        # Assert
        assert found == venv_py
        assert missing is None

    def test_has_python_changes_detects_modified_py_files(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Return True when git diff/ls-files reports modified or untracked .py files."""
        # Arrange
        recorded_cmds: list[list[str]] = []
        fake_proc = subprocess.CompletedProcess(
            args=["git"], returncode=0, stdout="README.md\nsrc/service.py\n", stderr=""
        )

        def _fake_git(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
            recorded_cmds.append(list(cmd))
            return fake_proc

        monkeypatch.setattr("subprocess.run", _fake_git)

        # Act
        changed = stop_verify_tests.has_python_changes(str(tmp_path))

        # Assert
        assert changed is True
        assert recorded_cmds[0][0].endswith("git")
        assert recorded_cmds[0][1] == "diff"

    def test_has_python_changes_returns_true_on_git_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Fail safe to True when git is unavailable or times out."""

        # Arrange
        def _raise_not_found(*_args: object, **_kwargs: object) -> None:
            raise FileNotFoundError("git not found")

        monkeypatch.setattr("subprocess.run", _raise_not_found)

        # Act
        changed = stop_verify_tests.has_python_changes(str(tmp_path))

        # Assert
        assert changed is True

    def test_run_tests_returns_true_on_passing_pytest(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Return (True, tail_summary) when pytest exits with code 0."""
        # Arrange
        recorded_cmds: list[list[str]] = []
        fake_proc = subprocess.CompletedProcess(
            args=["pytest"],
            returncode=0,
            stdout="line1\nline2\nline3\n5 passed in 0.12s\n",
            stderr="",
        )

        def _fake_pytest(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
            recorded_cmds.append(list(cmd))
            return fake_proc

        monkeypatch.setattr("subprocess.run", _fake_pytest)

        # Act
        passed, summary = stop_verify_tests.run_tests(tmp_path / "python", str(tmp_path))

        # Assert
        expected_prefix = [str(tmp_path / "python"), "-m", "pytest"]
        assert passed is True
        assert summary == "line2\nline3\n5 passed in 0.12s"
        assert recorded_cmds[0][: len(expected_prefix)] == expected_prefix

    def test_run_tests_returns_false_with_stderr_on_failure(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Return (False, combined_output) and pass -x when pytest fails."""
        # Arrange
        recorded_cmds: list[list[str]] = []
        fake_proc = subprocess.CompletedProcess(
            args=["pytest"],
            returncode=1,
            stdout="1 failed in 0.20s\n",
            stderr="AssertionError: expected 1 == 2",
        )

        def _fake_pytest_fail(
            cmd: list[str], **_kwargs: object
        ) -> subprocess.CompletedProcess[str]:
            recorded_cmds.append(list(cmd))
            return fake_proc

        monkeypatch.setattr("subprocess.run", _fake_pytest_fail)

        # Act
        passed, summary = stop_verify_tests.run_tests(tmp_path / "python", str(tmp_path))

        # Assert
        assert passed is False
        assert "1 failed in 0.20s" in summary
        assert "AssertionError" in summary
        assert "-x" in recorded_cmds[0]

    def test_run_tests_handles_timeout(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Return (False, timeout_message) when pytest exceeds the 120s timeout."""

        # Arrange
        def _raise_timeout(*_args: object, **_kwargs: object) -> None:
            raise subprocess.TimeoutExpired(cmd="pytest", timeout=120)

        monkeypatch.setattr("subprocess.run", _raise_timeout)

        # Act
        passed, summary = stop_verify_tests.run_tests(tmp_path / "python", str(tmp_path))

        # Assert
        assert passed is False
        assert "timed out" in summary

    def test_main_stops_immediately_for_non_model_stop_reason(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Allow immediate stop when terminationReason is USER_CANCEL rather than model_stop."""
        # Arrange
        payload = {"terminationReason": "USER_CANCEL", "workspacePaths": ["/tmp/ws"]}
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
        stdout_buf = io.StringIO()
        monkeypatch.setattr("sys.stdout", stdout_buf)

        # Act
        stop_verify_tests.main()

        # Assert
        assert json.loads(stdout_buf.getvalue()) == {"decision": "stop"}

    def test_main_stops_when_workspace_paths_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Allow immediate stop when no workspacePaths are provided."""
        # Arrange
        payload = {"terminationReason": "NO_TOOL_CALL", "workspacePaths": []}
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
        stdout_buf = io.StringIO()
        monkeypatch.setattr("sys.stdout", stdout_buf)

        # Act
        stop_verify_tests.main()

        # Assert
        assert json.loads(stdout_buf.getvalue()) == {"decision": "stop"}

    def test_main_stops_when_no_py_changes_or_no_venv_or_tests_pass(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Output decision=stop when all modified Python workspaces pass pytest."""
        # Arrange
        ws_no_changes = str(tmp_path / "ws1")
        ws_no_venv = str(tmp_path / "ws2")
        ws_passing = str(tmp_path / "ws3")
        monkeypatch.setattr(
            "stop_verify_tests.has_python_changes",
            lambda ws: ws != ws_no_changes,
        )
        monkeypatch.setattr(
            "stop_verify_tests.find_venv",
            lambda paths: None if paths[0] == ws_no_venv else tmp_path / "python",
        )
        monkeypatch.setattr(
            "stop_verify_tests.run_tests",
            lambda _py, _ws: (True, "10 passed"),
        )
        payload = {
            "terminationReason": "model_stop",
            "workspacePaths": [ws_no_changes, ws_no_venv, ws_passing],
        }
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
        stdout_buf = io.StringIO()
        monkeypatch.setattr("sys.stdout", stdout_buf)

        # Act
        stop_verify_tests.main()

        # Assert
        assert json.loads(stdout_buf.getvalue()) == {"decision": "stop"}

    def test_main_returns_continue_when_tests_fail(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Block agent turn completion (decision=continue) when pytest reports failures."""
        # Arrange
        monkeypatch.setattr("stop_verify_tests.has_python_changes", lambda _ws: True)
        monkeypatch.setattr("stop_verify_tests.find_venv", lambda _paths: tmp_path / "python")
        monkeypatch.setattr(
            "stop_verify_tests.run_tests",
            lambda _py, _ws: (False, "FAILED tests/unit/test_demo.py"),
        )
        payload = {
            "terminationReason": "NO_TOOL_CALL",
            "workspacePaths": [str(tmp_path)],
        }
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
        stdout_buf = io.StringIO()
        monkeypatch.setattr("sys.stdout", stdout_buf)

        # Act
        stop_verify_tests.main()

        # Assert
        result = json.loads(stdout_buf.getvalue())
        assert result["decision"] == "continue"
        assert "Tests are FAILING" in result["reason"]

    def test_resolve_effective_workspaces_appends_dotfiles_repo_when_git_present(
        self, tmp_path: Path
    ) -> None:
        """Append dotfiles-ubuntu repo to effective workspaces when it is a valid git clone."""
        # Arrange
        fake_dotfiles = tmp_path / "dotfiles-ubuntu"
        (fake_dotfiles / ".git").mkdir(parents=True)
        no_git_repo = tmp_path / "no-git"
        no_git_repo.mkdir()

        # Act
        empty_res = stop_verify_tests.resolve_effective_workspaces([], dotfiles_repo=fake_dotfiles)
        added_res = stop_verify_tests.resolve_effective_workspaces(
            ["/workspace/app"], dotfiles_repo=fake_dotfiles
        )
        dedup_res = stop_verify_tests.resolve_effective_workspaces(
            [str(fake_dotfiles)], dotfiles_repo=fake_dotfiles
        )
        no_git_res = stop_verify_tests.resolve_effective_workspaces(
            ["/workspace/app"], dotfiles_repo=no_git_repo
        )

        # Assert
        assert empty_res == []
        assert added_res == ["/workspace/app", str(fake_dotfiles)]
        assert dedup_res == [str(fake_dotfiles)]
        assert no_git_res == ["/workspace/app"]
