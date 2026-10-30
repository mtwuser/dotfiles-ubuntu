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


def test_get_changed_doc_files_and_check_universal_doc_structure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Arrange
    small_doc = tmp_path / "docs" / "architecture" / "01_spec.md"
    small_doc.parent.mkdir(parents=True)
    small_doc.write_text("# Line\n" * 464, encoding="utf-8")
    big_doc = tmp_path / "docs" / "architecture" / "02_big.md"
    big_doc.write_text("# Line\n" * 465, encoding="utf-8")
    fake_proc = subprocess.CompletedProcess(
        args=["git"],
        returncode=0,
        stdout="docs/architecture/01_spec.md\ndocs/architecture/02_big.md\ndocs/missing.md\nREADME.md\n",
        stderr="",
    )
    monkeypatch.setattr("subprocess.run", lambda *_a, **_k: fake_proc)

    # Act
    changed_docs = post_invocation_lint.get_changed_doc_files(str(tmp_path))
    violations = post_invocation_lint.check_universal_doc_structure(
        [*changed_docs, str(tmp_path / "docs" / "missing.md")]
    )

    # Assert
    assert changed_docs == [str(small_doc), str(big_doc)]
    assert len(violations) == 1
    assert "[max-doc-lines]" in violations[0]


def test_run_project_ast_checks_skips_non_manifest_workspace(tmp_path: Path) -> None:
    # Arrange
    venv_py = "/usr/bin/python3"

    # Act
    violations = post_invocation_lint.run_project_ast_checks(venv_py, str(tmp_path))

    # Assert
    assert violations == []


def test_run_project_ast_checks_returns_violations_when_nonzero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Arrange
    (tmp_path / "app-manifest.yaml").write_text("name: demo\n", encoding="utf-8")
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
    violations = post_invocation_lint.run_project_ast_checks("/usr/bin/python3", str(tmp_path))

    # Assert
    assert violations == ["src/models.py:10 [missing-aaa] Missing AAA comments"]


def test_run_project_ast_checks_returns_empty_when_zero_exit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Arrange
    (tmp_path / "src" / "core_framework").mkdir(parents=True)
    fake_proc = subprocess.CompletedProcess(args=["python"], returncode=0, stdout="", stderr="")
    monkeypatch.setattr("subprocess.run", lambda *_a, **_k: fake_proc)

    # Act
    violations = post_invocation_lint.run_project_ast_checks("/usr/bin/python3", str(tmp_path))

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
    monkeypatch.setattr("post_invocation_lint._DOTFILES_REPO_DIR", tmp_path)
    monkeypatch.setattr("post_invocation_lint.find_ruff", lambda _ws: "/usr/bin/ruff")
    monkeypatch.setattr(
        "post_invocation_lint.get_changed_python_files", lambda ws: [f"{ws}/bad.py"]
    )
    monkeypatch.setattr("post_invocation_lint.find_venv_python", lambda _ws: "/usr/bin/python3")
    monkeypatch.setattr(
        "post_invocation_lint.run_project_ast_checks",
        lambda _py, _ws: [f"ast_err_{i}" for i in range(6)],
    )
    lint_lines = "\n".join(f"lint_err_{i}" for i in range(10))
    fail_proc = subprocess.CompletedProcess(
        args=["ruff"], returncode=1, stdout=lint_lines, stderr=""
    )
    monkeypatch.setattr("subprocess.run", lambda *_a, **_k: fail_proc)
    payload = {"workspacePaths": [str(tmp_path)], "invocationNum": 4}
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    stdout_buf = io.StringIO()
    monkeypatch.setattr("sys.stdout", stdout_buf)

    # Act
    post_invocation_lint.main()

    # Assert
    result = json.loads(stdout_buf.getvalue())
    assert result["terminationBehavior"] == "force_continue"
    msg = result["injectSteps"][0]["ephemeralMessage"]
    assert "... (1 more)" in msg


def test_main_omits_force_continue_when_invocation_limit_reached(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Arrange
    monkeypatch.setattr("post_invocation_lint._DOTFILES_REPO_DIR", tmp_path)
    monkeypatch.setattr("post_invocation_lint.find_ruff", lambda _ws: "/usr/bin/ruff")
    monkeypatch.setattr(
        "post_invocation_lint.get_changed_python_files", lambda ws: [f"{ws}/bad.py"]
    )
    monkeypatch.setattr("post_invocation_lint.find_venv_python", lambda _ws: None)
    exact_15_lines = "\n".join(f"bad.py:{i}:1: F401 unused import" for i in range(1, 16))
    fail_proc = MagicMock(returncode=1, stdout=exact_15_lines)
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
    msg = result["injectSteps"][0]["ephemeralMessage"]
    assert "F401 unused import" in msg
    assert "... (" not in msg


def test_check_rules_token_budget_detects_agents_cap_and_workspace_budget(
    tmp_path: Path,
) -> None:
    # Arrange
    missing_agents = tmp_path / "missing_AGENTS.md"
    exact_agents = tmp_path / "exact_AGENTS.md"
    exact_agents.write_text("A" * 18000, encoding="utf-8")
    oversized_agents = tmp_path / "oversized_AGENTS.md"
    oversized_agents.write_text("A" * 18001, encoding="utf-8")

    ws_dir = tmp_path / "ws"
    rules_dir = ws_dir / ".agents" / "rules"
    rules_dir.mkdir(parents=True)
    always_prefix = "---\ntrigger: always_on\n---\n"
    (rules_dir / "always_rule.md").write_text(
        always_prefix + ("B" * (62000 - len(always_prefix))),
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
    warnings_exact = post_invocation_lint.check_rules_token_budget(
        [str(ws_dir)], agents_md_path=exact_agents
    )
    warnings_exceeded = post_invocation_lint.check_rules_token_budget(
        [str(ws_dir)], agents_md_path=oversized_agents
    )

    # Assert
    assert warnings_missing == []
    assert warnings_exact == []
    assert len(warnings_exceeded) == 2
    assert "[TOKEN_BUDGET_EXCEEDED]" in warnings_exceeded[0]
    assert "[WORKSPACE_RULES_BUDGET_EXCEEDED]" in warnings_exceeded[1]


def test_resolve_effective_workspaces_appends_dotfiles_repo_when_git_present(
    tmp_path: Path,
) -> None:
    # Arrange
    fake_dotfiles = tmp_path / "dotfiles-ubuntu"
    (fake_dotfiles / ".git").mkdir(parents=True)
    no_git_repo = tmp_path / "no-git"
    no_git_repo.mkdir()

    # Act
    empty_res = post_invocation_lint.resolve_effective_workspaces([], dotfiles_repo=fake_dotfiles)
    added_res = post_invocation_lint.resolve_effective_workspaces(
        ["/workspace/app"], dotfiles_repo=fake_dotfiles
    )
    dedup_res = post_invocation_lint.resolve_effective_workspaces(
        [str(fake_dotfiles)], dotfiles_repo=fake_dotfiles
    )
    no_git_res = post_invocation_lint.resolve_effective_workspaces(
        ["/workspace/app"], dotfiles_repo=no_git_repo
    )

    # Assert
    assert empty_res == []
    assert added_res == ["/workspace/app", str(fake_dotfiles)]
    assert dedup_res == [str(fake_dotfiles)]
    assert no_git_res == ["/workspace/app"]


def test_check_universal_python_structure_flags_oversized_and_missing_aaa(
    tmp_path: Path,
) -> None:
    # Arrange
    missing_file = tmp_path / "missing.py"
    init_file = tmp_path / "__init__.py"
    init_file.write_text("", encoding="utf-8")
    sibling_with_spec = tmp_path / "sibling.py"
    sibling_with_spec.write_text(
        '"""Mod.\n\nSpecification: docs/architecture/01_spec.md\n"""\n' + "x = 1\n" * 460,
        encoding="utf-8",
    )
    missing_spec_mod = tmp_path / "untraced.py"
    missing_spec_mod.write_text('"""Mod without spec pointer."""\nx = 1\n', encoding="utf-8")
    plain_dir = tmp_path / "plain_pkg"
    plain_dir.mkdir()
    plain_mod = plain_dir / "app.py"
    plain_mod.write_text('"""App without spec pointer in plain dir."""\nx = 1\n', encoding="utf-8")
    clean_test = tmp_path / "test_clean.py"
    clean_test.write_text(
        "def test_ok() -> None:\n"
        "    # Arrange\n    x = 1\n"
        "    # Act\n    y = x\n"
        "    # Assert\n    assert y == 1\n",
        encoding="utf-8",
    )
    bad_test = tmp_path / "test_missing_aaa.py"
    bad_test.write_text("def test_bad() -> None:\n    assert 1 == 1\n", encoding="utf-8")
    oversized_mod = tmp_path / "big_module.py"
    oversized_mod.write_text(
        '"""Big.\n\nSpecification: docs/architecture/01_spec.md\n"""\n' + "x = 1\n" * 461,
        encoding="utf-8",
    )

    # Act
    violations = post_invocation_lint.check_universal_python_structure(
        [
            str(missing_file),
            str(init_file),
            str(sibling_with_spec),
            str(missing_spec_mod),
            str(plain_mod),
            str(clean_test),
            str(bad_test),
            str(oversized_mod),
        ]
    )

    # Assert
    assert len(violations) == 3
    assert "[missing-spec-pointer]" in violations[0]
    assert "[missing-aaa]" in violations[1]
    assert "[max-file-lines]" in violations[2]
