"""Unit tests for post_edit_format.py (PostToolUse lifecycle hook)."""

from __future__ import annotations

import io
import json
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import post_edit_format

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def test_main_ignores_non_python_file(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    payload = {"toolCall": {"args": {"Path": "/tmp/README.md"}}}
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    stdout_buf = io.StringIO()
    monkeypatch.setattr("sys.stdout", stdout_buf)

    # Act
    post_edit_format.main()

    # Assert
    assert json.loads(stdout_buf.getvalue()) == {}


def test_main_ignores_missing_python_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    missing = tmp_path / "does_not_exist.py"
    payload = {"toolCall": {"args": {"Path": str(missing)}}}
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    stdout_buf = io.StringIO()
    monkeypatch.setattr("sys.stdout", stdout_buf)

    # Act
    post_edit_format.main()

    # Assert
    assert json.loads(stdout_buf.getvalue()) == {}


def test_main_formats_using_workspace_venv_ruff(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Arrange
    py_file = tmp_path / "sample.py"
    py_file.write_text("x=1\n", encoding="utf-8")
    venv_ruff = tmp_path / "venv" / "bin" / "ruff"
    venv_ruff.parent.mkdir(parents=True)
    venv_ruff.write_text("#!/bin/sh\n", encoding="utf-8")
    mock_run = MagicMock()
    monkeypatch.setattr("subprocess.run", mock_run)
    payload = {
        "toolCall": {"args": {"Path": str(py_file)}},
        "workspacePaths": [str(tmp_path / "other"), str(tmp_path)],
    }
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    stdout_buf = io.StringIO()
    monkeypatch.setattr("sys.stdout", stdout_buf)

    # Act
    post_edit_format.main()

    # Assert
    assert json.loads(stdout_buf.getvalue()) == {}
    mock_run.assert_called_once_with(
        [str(venv_ruff), "format", str(py_file)],
        check=False,
        capture_output=True,
        timeout=10,
    )


def test_main_falls_back_to_system_ruff_or_skips_when_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Arrange
    py_file = tmp_path / "sample.py"
    py_file.write_text("x = 1\n", encoding="utf-8")
    monkeypatch.setattr("shutil.which", lambda _cmd: None)
    mock_run = MagicMock()
    monkeypatch.setattr("subprocess.run", mock_run)
    payload = {
        "toolCall": {"args": {"TargetFile": str(py_file)}},
        "workspacePaths": [str(tmp_path)],
    }
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    stdout_buf = io.StringIO()
    monkeypatch.setattr("sys.stdout", stdout_buf)

    # Act
    post_edit_format.main()

    # Assert
    assert json.loads(stdout_buf.getvalue()) == {}
    mock_run.assert_not_called()
