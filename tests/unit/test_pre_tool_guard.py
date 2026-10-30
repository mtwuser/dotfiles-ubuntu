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
    args_non_empty: dict[str, object] = {
        "TargetFile": "/workspace/app/tests/unit/__init__.py",
        "ReplacementChunks": [{"TargetContent": "", "ReplacementContent": "x = 1"}],
    }
    args_empty_chunk: dict[str, object] = {
        "TargetFile": "/workspace/app/tests/unit/__init__.py",
        "ReplacementChunks": [{"TargetContent": "x = 1", "ReplacementContent": ""}],
    }

    # Act
    allowed, reason = pre_tool_guard._check_file_write(args_non_empty)
    allowed_empty, reason_empty = pre_tool_guard._check_file_write(args_empty_chunk)

    # Assert
    assert allowed is False
    assert "__init__.py Purity" in reason
    assert allowed_empty is True
    assert reason_empty == ""


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


def test_check_file_write_allows_framework_package_internal_init() -> None:
    # Arrange
    args: dict[str, object] = {
        "Path": "/workspace/core/src/core_framework/kernel/__init__.py",
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
    args_commit: dict[str, object] = {"CommandLine": "cd repo && git commit -m 'feat: test'"}
    args_subtree: dict[str, object] = {
        "CommandLine": (
            "git subtree add --prefix=layers/sec https://example.com/sec.git main --squash"
        )
    }

    # Act
    allowed_commit, reason_commit = pre_tool_guard._check_command(args_commit)
    allowed_subtree, reason_subtree = pre_tool_guard._check_command(args_subtree)

    # Assert
    assert allowed_commit is False
    assert "Commit Discipline" in reason_commit
    assert allowed_subtree is False
    assert "Commit Discipline" in reason_subtree


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
    args: dict[str, object] = {"CommandLine": "git status -s && pytest -q && uv && python3"}

    # Act
    allowed, reason = pre_tool_guard._check_command(args)

    # Assert
    assert allowed is True
    assert reason == ""


def test_check_command_tokenizes_global_flags_wrappers_and_subshells() -> None:
    # Arrange
    cmd_global_flags = (
        "cd /tmp && GIT_PAGER=cat sudo -u ubuntu -n /usr/bin/git "
        "-C /repo --no-pager -c color.ui=false commit -m 'msg'"
    )
    cmd_reset_hard = "git --bare reset --hard HEAD~1"
    cmd_clean_force = "git clean -fd"
    cmd_clean_long_force = "git clean --force"
    cmd_subshell_git = "bash -lc 'cd /repo && git push origin master'"
    cmd_subshell_alembic = "/bin/sh -x -c 'alembic -c alembic.ini --raiseerr downgrade -1'"
    cmd_py_m_alembic = "python3 -m alembic upgrade head"
    cmd_uv_run_alembic = "uv run alembic revision -m 'init'"

    # Act
    ok_flags, _ = pre_tool_guard._check_command({"CommandLine": cmd_global_flags})
    ok_reset, _ = pre_tool_guard._check_command({"CommandLine": cmd_reset_hard})
    ok_clean, _ = pre_tool_guard._check_command({"CommandLine": cmd_clean_force})
    ok_clean_long, _ = pre_tool_guard._check_command({"CommandLine": cmd_clean_long_force})
    ok_sub_git, _ = pre_tool_guard._check_command({"CommandLine": cmd_subshell_git})
    ok_sub_alembic, reason_alembic = pre_tool_guard._check_command(
        {"CommandLine": cmd_subshell_alembic}
    )
    ok_py_m, _ = pre_tool_guard._check_command({"CommandLine": cmd_py_m_alembic})
    ok_uv_run, _ = pre_tool_guard._check_command({"CommandLine": cmd_uv_run_alembic})

    # Assert
    assert ok_flags is False
    assert ok_reset is False
    assert ok_clean is False
    assert ok_clean_long is False
    assert ok_sub_git is False
    assert ok_sub_alembic is False
    assert ok_py_m is False
    assert ok_uv_run is False
    assert "Migration Policy" in reason_alembic


def test_check_command_ignores_quoted_strings_and_non_mutating_variants() -> None:
    # Arrange
    cmd_quoted_echo = 'echo "To publish: git add . && git commit -m msg && alembic upgrade head"'
    cmd_python_inline = "python3 -c 'print(\"git push && git reset --hard\")'"
    cmd_reset_soft = "git reset --soft HEAD~1"
    cmd_clean_dry = "git clean -n -d"
    cmd_subtree_list = "git subtree split --prefix=layers/sec"
    cmd_bare_git_flags = (
        "(git --version ; alembic --help ; FOO=bar ; sudo -u root ; uv --version ; bash -i);"
    )
    cmd_benign_subshell = "bash -c 'git status && echo ok'"

    # Act
    ok_echo, _ = pre_tool_guard._check_command({"CommandLine": cmd_quoted_echo})
    ok_py, _ = pre_tool_guard._check_command({"CommandLine": cmd_python_inline})
    ok_soft, _ = pre_tool_guard._check_command({"CommandLine": cmd_reset_soft})
    ok_clean_dry, _ = pre_tool_guard._check_command({"CommandLine": cmd_clean_dry})
    ok_subtree_split, _ = pre_tool_guard._check_command({"CommandLine": cmd_subtree_list})
    ok_bare, _ = pre_tool_guard._check_command({"CommandLine": cmd_bare_git_flags})
    ok_subshell, _ = pre_tool_guard._check_command({"CommandLine": cmd_benign_subshell})
    empty_subshell = pre_tool_guard._extract_subshell_command([])

    # Assert
    assert ok_echo is True
    assert ok_py is True
    assert ok_soft is True
    assert ok_clean_dry is True
    assert ok_subtree_split is True
    assert ok_bare is True
    assert ok_subshell is True
    assert empty_subshell is None


def test_check_command_regex_fallback_catches_cmd_substitution_and_unclosed_quotes() -> None:
    # Arrange
    cmd_subst_git = 'echo "$(git push origin master)"'
    cmd_subst_alembic = 'echo "`alembic upgrade head`"'
    cmd_subst_benign = 'echo "$(git status -s)"'
    cmd_unclosed_git = 'git commit -m "unclosed quote'

    # Act
    ok_subst_git, _ = pre_tool_guard._check_command({"CommandLine": cmd_subst_git})
    ok_subst_alembic, _ = pre_tool_guard._check_command({"CommandLine": cmd_subst_alembic})
    ok_subst_benign, _ = pre_tool_guard._check_command({"CommandLine": cmd_subst_benign})
    ok_unclosed, _ = pre_tool_guard._check_command({"CommandLine": cmd_unclosed_git})

    # Assert
    assert ok_subst_git is False
    assert ok_subst_alembic is False
    assert ok_subst_benign is True
    assert ok_unclosed is False


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
