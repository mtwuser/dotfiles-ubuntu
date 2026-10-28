"""Unit tests for post_invocation_lint.py (PostInvocation lifecycle hook)."""

from __future__ import annotations

import io
import json
import subprocess
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import post_invocation_lint

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def test_find_ruff_prefers_workspace_venv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    venv_ruff = tmp_path / "venv" / "bin" / "ruff"
    venv_ruff.parent.mkdir(parents=True)
    venv_ruff.write_text("#!/bin/sh\n", encoding="utf-8")
    monkeypatch.setattr("shutil.which", lambda _name: "/usr/bin/ruff")

    # Act
    found = post_invocation_lint.find_ruff([str(tmp_path / "empty"), str(tmp_path)])

    # Assert
    assert found == str(venv_ruff)


def test_find_ruff_falls_back_to_which(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    monkeypatch.setattr("shutil.which", lambda _name: "/usr/bin/ruff")

    # Act
    found = post_invocation_lint.find_ruff([str(tmp_path)])

    # Assert
    assert found == "/usr/bin/ruff"


def test_find_venv_python_returns_path_or_none(tmp_path: Path) -> None:
    # Arrange
    ws1 = tmp_path / "ws1"
    ws2 = tmp_path / "ws2"
    venv_py = ws2 / "venv" / "bin" / "python"
    venv_py.parent.mkdir(parents=True)
    venv_py.write_text("#!/bin/sh\n", encoding="utf-8")

    # Act
    found = post_invocation_lint.find_venv_python([str(ws1), str(ws2)])
    missing = post_invocation_lint.find_venv_python([str(ws1)])

    # Assert
    assert found == str(venv_py)
    assert missing is None


def test_get_changed_python_files_filters_docs_and_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Arrange
    existing_py = tmp_path / "src" / "app.py"
    existing_py.parent.mkdir(parents=True)
    existing_py.write_text("x = 1\n", encoding="utf-8")
    docs_py = tmp_path / "docs" / "example.py"
    docs_py.parent.mkdir(parents=True)
    docs_py.write_text("y = 2\n", encoding="utf-8")
    fake_proc = subprocess.CompletedProcess(
        args=["git"],
        returncode=0,
        stdout="src/app.py\ndocs/example.py\nREADME.md\nsrc/deleted.py\n",
        stderr="",
    )
    monkeypatch.setattr("subprocess.run", lambda *_a, **_k: fake_proc)

    # Act
    changed = post_invocation_lint.get_changed_python_files(str(tmp_path))

    # Assert
    assert changed == [str(existing_py)]


def test_run_osa_ast_checks_skips_non_osa_workspace(tmp_path: Path) -> None:
    # Arrange
    venv_py = "/usr/bin/python3"

    # Act
    violations = post_invocation_lint.run_osa_ast_checks(venv_py, str(tmp_path))

    # Assert
    assert violations == []


def test_run_osa_ast_checks_returns_violations_when_nonzero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Arrange
    (tmp_path / "osa-manifest.yaml").write_text("name: demo\n", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "tests" / "unit").mkdir(parents=True)
    fake_proc = subprocess.CompletedProcess(
        args=["python"],
        returncode=1,
        stdout="src/models.py:10 [missing-aaa] Missing AAA comments\n",
        stderr="",
    )
    monkeypatch.setattr("subprocess.run", lambda *_a, **_k: fake_proc)

    # Act
    violations = post_invocation_lint.run_osa_ast_checks("/usr/bin/python3", str(tmp_path))

    # Assert
    assert violations == ["src/models.py:10 [missing-aaa] Missing AAA comments"]


def test_run_osa_ast_checks_returns_empty_when_zero_exit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Arrange
    (tmp_path / "src" / "osa_framework").mkdir(parents=True)
    fake_proc = subprocess.CompletedProcess(args=["python"], returncode=0, stdout="", stderr="")
    monkeypatch.setattr("subprocess.run", lambda *_a, **_k: fake_proc)

    # Act
    violations = post_invocation_lint.run_osa_ast_checks("/usr/bin/python3", str(tmp_path))

    # Assert
    assert violations == []


def test_main_returns_empty_when_no_workspaces(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps({"workspacePaths": []})))
    stdout_buf = io.StringIO()
    monkeypatch.setattr("sys.stdout", stdout_buf)

    # Act
    post_invocation_lint.main()

    # Assert
    assert json.loads(stdout_buf.getvalue()) == {}


def test_main_returns_empty_when_ruff_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Arrange
    monkeypatch.setattr("post_invocation_lint.find_ruff", lambda _ws: None)
    payload = {"workspacePaths": [str(tmp_path)]}
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    stdout_buf = io.StringIO()
    monkeypatch.setattr("sys.stdout", stdout_buf)

    # Act
    post_invocation_lint.main()

    # Assert
    assert json.loads(stdout_buf.getvalue()) == {}


def test_main_returns_empty_when_no_changed_files_or_clean_lint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Arrange
    ws_empty = tmp_path / "empty_ws"
    ws_clean = tmp_path / "clean_ws"
    ws_empty.mkdir()
    ws_clean.mkdir()
    monkeypatch.setattr("post_invocation_lint.find_ruff", lambda _ws: "/usr/bin/ruff")
    monkeypatch.setattr(
        "post_invocation_lint.get_changed_python_files",
        lambda ws: [] if ws == str(ws_empty) else [f"{ws}/a.py"],
    )
    monkeypatch.setattr("post_invocation_lint.find_venv_python", lambda _ws: None)
    clean_proc = subprocess.CompletedProcess(args=["ruff"], returncode=0, stdout="", stderr="")
    monkeypatch.setattr("subprocess.run", lambda *_a, **_k: clean_proc)
    payload = {"workspacePaths": [str(ws_empty), str(ws_clean)]}
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    stdout_buf = io.StringIO()
    monkeypatch.setattr("sys.stdout", stdout_buf)

    # Act
    post_invocation_lint.main()

    # Assert
    assert json.loads(stdout_buf.getvalue()) == {}


def test_main_injects_truncated_summary_and_force_continue(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Arrange
    monkeypatch.setattr("post_invocation_lint.find_ruff", lambda _ws: "/usr/bin/ruff")
    monkeypatch.setattr(
        "post_invocation_lint.get_changed_python_files", lambda ws: [f"{ws}/bad.py"]
    )
    monkeypatch.setattr("post_invocation_lint.find_venv_python", lambda _ws: "/usr/bin/python3")
    monkeypatch.setattr(
        "post_invocation_lint.run_osa_ast_checks",
        lambda _py, _ws: [f"ast_err_{i}" for i in range(10)],
    )
    lint_lines = "\n".join(f"lint_err_{i}" for i in range(10))
    fail_proc = subprocess.CompletedProcess(
        args=["ruff"], returncode=1, stdout=lint_lines, stderr=""
    )
    monkeypatch.setattr("subprocess.run", lambda *_a, **_k: fail_proc)
    payload = {"workspacePaths": [str(tmp_path)], "invocationNum": 2}
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    stdout_buf = io.StringIO()
    monkeypatch.setattr("sys.stdout", stdout_buf)

    # Act
    post_invocation_lint.main()

    # Assert
    result = json.loads(stdout_buf.getvalue())
    assert result["terminationBehavior"] == "force_continue"
    msg = result["injectSteps"][0]["ephemeralMessage"]
    assert "... (5 more)" in msg


def test_main_omits_force_continue_when_invocation_limit_reached(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Arrange
    monkeypatch.setattr("post_invocation_lint.find_ruff", lambda _ws: "/usr/bin/ruff")
    monkeypatch.setattr(
        "post_invocation_lint.get_changed_python_files", lambda ws: [f"{ws}/bad.py"]
    )
    monkeypatch.setattr("post_invocation_lint.find_venv_python", lambda _ws: None)
    fail_proc = MagicMock(returncode=1, stdout="bad.py:1:1: F401 unused import\n")
    monkeypatch.setattr("subprocess.run", lambda *_a, **_k: fail_proc)
    payload = {"workspacePaths": [str(tmp_path)], "invocationNum": 5}
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    stdout_buf = io.StringIO()
    monkeypatch.setattr("sys.stdout", stdout_buf)

    # Act
    post_invocation_lint.main()

    # Assert
    result = json.loads(stdout_buf.getvalue())
    assert "terminationBehavior" not in result
    assert "F401 unused import" in result["injectSteps"][0]["ephemeralMessage"]


def test_check_rules_token_budget_detects_agents_cap_and_workspace_budget(
    tmp_path: Path,
) -> None:
    # Arrange
    missing_agents = tmp_path / "missing_AGENTS.md"
    oversized_agents = tmp_path / "oversized_AGENTS.md"
    oversized_agents.write_text("A" * 18500, encoding="utf-8")

    ws_dir = tmp_path / "ws"
    rules_dir = ws_dir / ".agents" / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "always_rule.md").write_text(
        "---\ntrigger: always_on\n---\n" + ("B" * 65000),
        encoding="utf-8",
    )
    (rules_dir / "conditional_rule.md").write_text(
        "---\ntrigger: model_decision\n---\n" + ("C" * 50000),
        encoding="utf-8",
    )

    # Act
    warnings_missing = post_invocation_lint.check_rules_token_budget(
        [str(tmp_path / "no_rules_ws")], agents_md_path=missing_agents
    )
    warnings_exceeded = post_invocation_lint.check_rules_token_budget(
        [str(ws_dir)], agents_md_path=oversized_agents
    )

    # Assert
    assert warnings_missing == []
    assert len(warnings_exceeded) == 2
    assert "[TOKEN_BUDGET_EXCEEDED]" in warnings_exceeded[0]
    assert "[WORKSPACE_RULES_BUDGET_EXCEEDED]" in warnings_exceeded[1]
