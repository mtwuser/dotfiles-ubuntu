"""End-to-end simulation of a complete Antigravity 2.0 agent turn across all 4 hooks."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parents[2]
HOOKS_DIR = REPO_DIR / "antigravity" / ".gemini" / "config" / "scripts"


def _invoke_hook(
    script_name: str, payload: dict[str, object], hooks_dir: Path = HOOKS_DIR
) -> dict[str, object]:
    """Execute a lifecycle hook script over stdio with the given JSON payload."""
    proc = subprocess.run(
        [sys.executable, str(hooks_dir / script_name)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=15,
        check=True,
    )
    return json.loads(proc.stdout) if proc.stdout.strip() else {}


def test_e2e_full_agent_turn_pre_post_invocation_and_stop_hooks(tmp_path: Path) -> None:
    # Arrange
    hook_scripts = tmp_path / "isolated_dotfiles/antigravity/.gemini/config/scripts"
    hook_scripts.mkdir(parents=True)
    for hs in HOOKS_DIR.glob("*.py"):
        shutil.copy2(hs, hook_scripts / hs.name)
    ws = tmp_path / "sample_project"
    (ws / "src" / "pkg").mkdir(parents=True)
    (ws / "tests" / "unit").mkdir(parents=True)
    (ws / "pyproject.toml").write_text(
        '[tool.pytest.ini_options]\npythonpath = ["."]\n', encoding="utf-8"
    )
    (ws / "src" / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (ws / "tests" / "__init__.py").write_text("", encoding="utf-8")
    (ws / "tests" / "unit" / "__init__.py").write_text("", encoding="utf-8")

    venv_bin = ws / "venv" / "bin"
    venv_bin.mkdir(parents=True)
    repo_venv_bin = REPO_DIR / "venv" / "bin"
    py_bin_dir = Path(sys.executable).parent
    for tool in ("python", "pytest", "ruff"):
        candidates = [repo_venv_bin / tool, py_bin_dir / tool]
        which_tool = shutil.which(tool)
        if which_tool:
            candidates.append(Path(which_tool))
        if tool == "python":
            candidates.append(Path(sys.executable))
        for target_bin in candidates:
            if target_bin.exists():
                (venv_bin / tool).symlink_to(target_bin)
                break

    git_env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "Test Bot",
        "GIT_AUTHOR_EMAIL": "bot@example.com",
        "GIT_COMMITTER_NAME": "Test Bot",
        "GIT_COMMITTER_EMAIL": "bot@example.com",
    }
    subprocess.run(["git", "init", "-b", "master"], cwd=ws, env=git_env, check=True)
    subprocess.run(["git", "add", "-A"], cwd=ws, env=git_env, check=True)
    subprocess.run(
        ["git", "commit", "-m", "chore: init workspace"], cwd=ws, env=git_env, check=True
    )

    calc_file = ws / "src" / "pkg" / "calc.py"
    test_file = ws / "tests" / "unit" / "test_calc.py"

    # Act
    deny_init = _invoke_hook(
        "pre_tool_guard.py",
        {
            "toolCall": {
                "name": "write_file",
                "args": {
                    "Path": str(ws / "src" / "pkg" / "__init__.py"),
                    "Content": "__version__ = '1.0'\n",
                },
            }
        },
    )
    allow_calc = _invoke_hook(
        "pre_tool_guard.py",
        {
            "toolCall": {
                "name": "write_file",
                "args": {
                    "Path": str(calc_file),
                    "Content": "def add_ints(a:int,b:int)->int:\n    return a+b\n",
                },
            }
        },
    )
    calc_file.write_text("def add_ints(a:int,b:int)->int:\n    return a+b\n", encoding="utf-8")
    test_file.write_text(
        "from src.pkg.calc import add_ints\n\n\n"
        "def test_add_ints() -> None:\n"
        "    # Arrange\n"
        "    a, b = 2, 3\n\n"
        "    # Act\n"
        "    res = add_ints(a, b)\n\n"
        "    # Assert\n"
        "    assert res == 999\n",
        encoding="utf-8",
    )
    stop_fail = _invoke_hook(
        "stop_verify_tests.py",
        {"workspacePaths": [str(ws)], "terminationReason": "NO_TOOL_CALL"},
        hooks_dir=hook_scripts,
    )
    test_file.write_text(
        "from src.pkg.calc import add_ints\n\n\n"
        "def test_add_ints() -> None:\n"
        "    # Arrange\n"
        "    a, b = 2, 3\n\n"
        "    # Act\n"
        "    res = add_ints(a, b)\n\n"
        "    # Assert\n"
        "    assert res == 5\n",
        encoding="utf-8",
    )
    _invoke_hook(
        "post_edit_format.py",
        {
            "workspacePaths": [str(ws)],
            "toolCall": {"name": "write_file", "args": {"Path": str(calc_file)}},
        },
        hooks_dir=hook_scripts,
    )
    post_inv = _invoke_hook(
        "post_invocation_lint.py",
        {"workspacePaths": [str(ws)], "invocationNum": 1},
        hooks_dir=hook_scripts,
    )
    stop_res = _invoke_hook(
        "stop_verify_tests.py",
        {"workspacePaths": [str(ws)], "terminationReason": "NO_TOOL_CALL"},
        hooks_dir=hook_scripts,
    )

    # Assert
    assert deny_init["decision"] == "deny"
    assert allow_calc["decision"] == "allow"
    assert "def add_ints(a: int, b: int) -> int:" in calc_file.read_text(encoding="utf-8")
    assert post_inv == {}
    assert stop_fail["decision"] == "continue"
    assert "1 failed" in str(stop_fail["reason"])
    assert stop_res == {"decision": "stop"}


def test_e2e_post_invocation_lint_structural_budget_and_ast_violations_in_git_repo(
    tmp_path: Path,
) -> None:
    """Validate post_invocation_lint.py on a real Git repo for doc/spec/AAA/budget/AST gates."""
    # Arrange
    hook_root = tmp_path / "isolated_dotfiles"
    hook_scripts = hook_root / "antigravity" / ".gemini" / "config" / "scripts"
    hook_scripts.mkdir(parents=True)
    isolated_lint = hook_scripts / "post_invocation_lint.py"
    shutil.copy2(HOOKS_DIR / "post_invocation_lint.py", isolated_lint)
    (hook_scripts.parent / "AGENTS.md").write_text("A" * 18500, encoding="utf-8")

    ws = tmp_path / "framework_repo"
    (ws / "src" / "demo_framework" / "core" / "testing").mkdir(parents=True)
    (ws / "tests" / "unit").mkdir(parents=True)
    (ws / "docs" / "architecture").mkdir(parents=True)
    (ws / ".agents" / "rules").mkdir(parents=True)

    venv_bin = ws / "venv" / "bin"
    venv_bin.mkdir(parents=True)
    repo_venv_bin = REPO_DIR / "venv" / "bin"
    py_bin_dir = Path(sys.executable).parent
    for tool in ("python", "ruff"):
        candidates = [repo_venv_bin / tool, py_bin_dir / tool]
        which_tool = shutil.which(tool)
        if which_tool:
            candidates.append(Path(which_tool))
        if tool == "python":
            candidates.append(Path(sys.executable))
        for target_bin in candidates:
            if target_bin.exists():
                (venv_bin / tool).symlink_to(target_bin)
                break

    for pkg_init in (
        ws / "src" / "demo_framework" / "__init__.py",
        ws / "src" / "demo_framework" / "core" / "__init__.py",
        ws / "src" / "demo_framework" / "core" / "testing" / "__init__.py",
        ws / "tests" / "__init__.py",
        ws / "tests" / "unit" / "__init__.py",
    ):
        pkg_init.write_text("", encoding="utf-8")

    (ws / "src" / "demo_framework" / "traced.py").write_text(
        '"""Traced module.\n\nSpecification: docs/architecture/spec.md\n"""\n',
        encoding="utf-8",
    )
    (ws / "src" / "demo_framework" / "core" / "testing" / "architecture_linter.py").write_text(
        '"""Architecture linter stub.\n\nSpecification: docs/architecture/spec.md\n"""\n\n'
        "from dataclasses import dataclass\n"
        "from pathlib import Path\n\n\n"
        "@dataclass\n"
        "class Violation:\n"
        "    file: str\n"
        "    line: int\n"
        "    rule: str\n"
        "    message: str\n\n\n"
        "def check_project(src_dir: Path) -> list[Violation]:\n"
        '    return [Violation("src/demo_framework/untraced.py", 1, '
        '"domain-purity", "Bad import")]\n\n\n'
        "def check_tests(tests_dir: Path) -> list[Violation]:\n"
        '    return [Violation("tests/unit/test_missing_aaa.py", 1, "service-mock", "No spec")]\n',
        encoding="utf-8",
    )

    git_env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "Test Bot",
        "GIT_AUTHOR_EMAIL": "bot@example.com",
        "GIT_COMMITTER_NAME": "Test Bot",
        "GIT_COMMITTER_EMAIL": "bot@example.com",
    }
    subprocess.run(["git", "init", "-b", "master"], cwd=ws, env=git_env, check=True)
    subprocess.run(["git", "add", "-A"], cwd=ws, env=git_env, check=True)
    subprocess.run(["git", "commit", "-m", "chore: base"], cwd=ws, env=git_env, check=True)

    (ws / ".agents" / "rules" / "bloated.md").write_text("B" * 65000, encoding="utf-8")
    (ws / "docs" / "architecture" / "oversized.md").write_text("# Doc\n" * 470, encoding="utf-8")
    (ws / "src" / "demo_framework" / "untraced.py").write_text(
        '"""Module without spec pointer."""\n', encoding="utf-8"
    )
    (ws / "tests" / "unit" / "test_missing_aaa.py").write_text(
        '"""Test file without AAA comments."""\n\n\ndef test_bad() -> None:\n    assert 1 == 1\n',
        encoding="utf-8",
    )

    # Act
    proc = subprocess.run(
        [sys.executable, str(isolated_lint)],
        input=json.dumps({"workspacePaths": [str(ws)], "invocationNum": 1}),
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(ws / "src")},
        timeout=15,
        check=True,
    )
    res = json.loads(proc.stdout)
    msg = res["injectSteps"][0]["ephemeralMessage"]

    # Assert
    assert res["terminationBehavior"] == "force_continue"
    assert "[TOKEN_BUDGET_EXCEEDED]" in msg
    assert "[WORKSPACE_RULES_BUDGET_EXCEEDED]" in msg
    assert "[max-doc-lines]" in msg
    assert "[missing-spec-pointer]" in msg
    assert "[missing-aaa]" in msg
    assert "[domain-purity]" in msg
    assert "[service-mock]" in msg
