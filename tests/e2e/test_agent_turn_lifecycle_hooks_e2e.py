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


def _invoke_hook(script_name: str, payload: dict[str, object]) -> dict[str, object]:
    """Execute a lifecycle hook script over stdio with the given JSON payload."""
    proc = subprocess.run(
        [sys.executable, str(HOOKS_DIR / script_name)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=15,
        check=True,
    )
    return json.loads(proc.stdout) if proc.stdout.strip() else {}


def test_e2e_full_agent_turn_pre_post_invocation_and_stop_hooks(tmp_path: Path) -> None:
    # Arrange
    ws = tmp_path / "sample_project"
    (ws / "src" / "pkg").mkdir(parents=True)
    (ws / "tests" / "unit").mkdir(parents=True)
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
        "    assert res == 5\n",
        encoding="utf-8",
    )
    _invoke_hook(
        "post_edit_format.py",
        {
            "workspacePaths": [str(ws)],
            "toolCall": {"name": "write_file", "args": {"Path": str(calc_file)}},
        },
    )
    post_inv = _invoke_hook(
        "post_invocation_lint.py",
        {"workspacePaths": [str(ws)], "invocationNum": 1},
    )
    stop_res = _invoke_hook(
        "stop_verify_tests.py",
        {"workspacePaths": [str(ws)], "stopReason": "NO_TOOL_CALL"},
    )

    # Assert
    assert deny_init["decision"] == "deny"
    assert allow_calc["decision"] == "allow"
    assert "def add_ints(a: int, b: int) -> int:" in calc_file.read_text(encoding="utf-8")
    assert post_inv == {}
    assert stop_res == {"decision": "stop"}
