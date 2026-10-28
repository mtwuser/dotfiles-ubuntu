"""Unit tests for pre_tool_guard.py (PreToolUse lifecycle hook)."""

from __future__ import annotations

import io
import json
from typing import TYPE_CHECKING

import pre_tool_guard

if TYPE_CHECKING:
    import pytest


def test_check_file_write_allows_empty_target() -> None:
    # Arrange
    args: dict[str, object] = {}

    # Act
    allowed, reason = pre_tool_guard._check_file_write(args)

    # Assert
    assert allowed is True
    assert reason == ""


def test_check_file_write_blocks_alembic_version_python_file() -> None:
    # Arrange
    args: dict[str, object] = {
        "Path": "/workspace/app/alembic/versions/001_initial.py",
        "Content": "def upgrade(): pass",
    }

    # Act
    allowed, reason = pre_tool_guard._check_file_write(args)

    # Assert
    assert allowed is False
    assert "Zero-Touch Migration Policy" in reason


def test_check_file_write_allows_non_python_in_alembic_versions() -> None:
    # Arrange
    args: dict[str, object] = {
        "Path": "/workspace/app/alembic/versions/README.md",
        "Content": "# Migrations",
    }

    # Act
    allowed, reason = pre_tool_guard._check_file_write(args)

    # Assert
    assert allowed is True
    assert reason == ""


def test_check_file_write_blocks_non_empty_consumer_src_init() -> None:
    # Arrange
    args: dict[str, object] = {
        "Path": "/workspace/app/src/orders/__init__.py",
        "Content": "__all__ = ['Order']",
    }

    # Act
    allowed, reason = pre_tool_guard._check_file_write(args)

    # Assert
    assert allowed is False
    assert "__init__.py Purity" in reason


def test_check_file_write_blocks_non_empty_tests_init_with_replacement_chunks() -> None:
    # Arrange
    args: dict[str, object] = {
        "TargetFile": "/workspace/app/tests/unit/__init__.py",
        "ReplacementChunks": [{"TargetContent": "", "ReplacementContent": "x = 1"}],
    }

    # Act
    allowed, reason = pre_tool_guard._check_file_write(args)

    # Assert
    assert allowed is False
    assert "__init__.py Purity" in reason


def test_check_file_write_allows_empty_consumer_src_init() -> None:
    # Arrange
    args: dict[str, object] = {
        "Path": "/workspace/app/src/orders/__init__.py",
        "Content": "",
    }

    # Act
    allowed, reason = pre_tool_guard._check_file_write(args)

    # Assert
    assert allowed is True
    assert reason == ""


def test_check_file_write_allows_osa_framework_internal_init() -> None:
    # Arrange
    args: dict[str, object] = {
        "Path": "/workspace/OSA/src/osa_framework/core/__init__.py",
        "Content": "from .types import Identifier",
    }

    # Act
    allowed, reason = pre_tool_guard._check_file_write(args)

    # Assert
    assert allowed is True
    assert reason == ""


def test_check_file_write_allows_regular_python_module() -> None:
    # Arrange
    args: dict[str, object] = {
        "Path": "/workspace/app/src/orders/service.py",
        "Content": "class OrderService: pass",
    }

    # Act
    allowed, reason = pre_tool_guard._check_file_write(args)

    # Assert
    assert allowed is True
    assert reason == ""


def test_check_command_allows_empty_command() -> None:
    # Arrange
    args: dict[str, object] = {"CommandLine": ""}

    # Act
    allowed, reason = pre_tool_guard._check_command(args)

    # Assert
    assert allowed is True
    assert reason == ""


def test_check_command_blocks_mutating_git_commands() -> None:
    # Arrange
    args: dict[str, object] = {"CommandLine": "cd repo && git commit -m 'feat: test'"}

    # Act
    allowed, reason = pre_tool_guard._check_command(args)

    # Assert
    assert allowed is False
    assert "Commit Discipline" in reason


def test_check_command_blocks_alembic_mutation_commands() -> None:
    # Arrange
    args: dict[str, object] = {"CommandLine": "alembic upgrade head"}

    # Act
    allowed, reason = pre_tool_guard._check_command(args)

    # Assert
    assert allowed is False
    assert "Migration Policy" in reason


def test_check_command_allows_read_only_git_status_and_pytest() -> None:
    # Arrange
    args: dict[str, object] = {"CommandLine": "git status -s && pytest -q"}

    # Act
    allowed, reason = pre_tool_guard._check_command(args)

    # Assert
    assert allowed is True
    assert reason == ""


def test_main_outputs_allow_for_safe_write_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    payload = {
        "toolCall": {
            "name": "write_file",
            "args": {"Path": "/workspace/app/src/orders/models.py", "Content": "x = 1"},
        }
    }
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    stdout_buf = io.StringIO()
    monkeypatch.setattr("sys.stdout", stdout_buf)

    # Act
    pre_tool_guard.main()

    # Assert
    result = json.loads(stdout_buf.getvalue())
    assert result == {"decision": "allow"}


def test_main_outputs_deny_for_mutating_git_run_command(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    payload = {
        "toolCall": {
            "name": "run_command",
            "args": {"CommandLine": "git push origin main"},
        }
    }
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    stdout_buf = io.StringIO()
    monkeypatch.setattr("sys.stdout", stdout_buf)

    # Act
    pre_tool_guard.main()

    # Assert
    result = json.loads(stdout_buf.getvalue())
    assert result["decision"] == "deny"
    assert "Commit Discipline" in result["reason"]


def test_main_outputs_allow_for_unrelated_tool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    payload = {"toolCall": {"name": "read_file", "args": {"Path": "README.md"}}}
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    stdout_buf = io.StringIO()
    monkeypatch.setattr("sys.stdout", stdout_buf)

    # Act
    pre_tool_guard.main()

    # Assert
    result = json.loads(stdout_buf.getvalue())
    assert result == {"decision": "allow"}
