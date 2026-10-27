#!/usr/bin/env python3
"""PostInvocation hook: lint & architecture check on modified Python files.

Contract: reads JSON from stdin, writes {"injectSteps": [...], ...} to stdout.
Runs ruff check (and OSA check_project/check_tests when available) on Python
files with uncommitted or untracked changes.
If issues are found, injects an ephemeral message and forces continuation so the
agent resolves them in the same turn.
"""

import contextlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

_MAX_SUMMARY_LINES = 15
_MAX_FORCE_CONTINUE_INVOCATIONS = 5


def find_ruff(workspace_paths: list[str]) -> str | None:
    """Find ruff: check venv in each workspace, then fall back to PATH."""
    for ws in workspace_paths:
        venv_ruff = Path(ws) / "venv" / "bin" / "ruff"
        if venv_ruff.exists():
            return str(venv_ruff)
    return shutil.which("ruff")


def find_venv_python(workspace_paths: list[str]) -> str | None:
    """Find the first venv Python interpreter across workspaces."""
    for ws in workspace_paths:
        venv_py = Path(ws) / "venv" / "bin" / "python"
        if venv_py.exists():
            return str(venv_py)
    return None


def get_changed_python_files(workspace_path: str) -> list[str]:
    """Get Python files with uncommitted changes (unstaged, staged, or untracked)."""
    git_bin = shutil.which("git") or "git"
    files: set[str] = set()
    for cmd in [
        [git_bin, "diff", "--name-only", "--diff-filter=ACMR"],
        [git_bin, "diff", "--name-only", "--cached", "--diff-filter=ACMR"],
        [git_bin, "ls-files", "--others", "--exclude-standard", "--", "*.py"],
    ]:
        with contextlib.suppress(subprocess.TimeoutExpired, FileNotFoundError):
            result = subprocess.run(  # noqa: S603
                cmd,
                check=False,
                capture_output=True,
                text=True,
                cwd=workspace_path,
                timeout=5,
            )
            for raw_line in result.stdout.splitlines():
                rel_file = raw_line.strip()
                if rel_file.endswith(".py") and not rel_file.startswith("docs/"):
                    full = Path(workspace_path) / rel_file
                    if full.exists():
                        files.add(str(full))
    return sorted(files)


def run_osa_ast_checks(venv_python: str, workspace_path: str) -> list[str]:
    """Run fast AST check_project and check_tests if workspace is an OSA repo."""
    ws = Path(workspace_path)
    if (
        not (ws / "osa-manifest.yaml").exists()
        and not (ws / "src" / "osa_framework").exists()
    ):
        return []

    src_dir = (
        ws / "src" / "osa_framework"
        if (ws / "src" / "osa_framework").exists()
        else ws / "src"
    )
    tests_dir = (
        ws / "tests" / "unit" if (ws / "tests" / "unit").exists() else ws / "tests"
    )
    snippet = (
        "import sys; from pathlib import Path; "
        "from osa_framework.core.testing.architecture_linter import check_project, check_tests; "
        f"v1 = check_project(Path({str(src_dir)!r})) if Path({str(src_dir)!r}).is_dir() else []; "
        f"v2 = check_tests(Path({str(tests_dir)!r})) if Path({str(tests_dir)!r}).is_dir() else []; "
        "lines = [f'{v.file}:{v.line} [{v.rule}] {v.message}' for v in (*v1, *v2)]; "
        "print('\\n'.join(lines)); sys.exit(1 if lines else 0)"
    )
    with contextlib.suppress(subprocess.TimeoutExpired, OSError):
        result = subprocess.run(  # noqa: S603
            [venv_python, "-c", snippet],
            check=False,
            capture_output=True,
            text=True,
            cwd=workspace_path,
            timeout=8,
        )
        if result.returncode != 0 and result.stdout.strip():
            return result.stdout.strip().splitlines()
    return []


def main() -> None:
    """Run ruff check and OSA AST checks on modified Python files."""
    payload = json.load(sys.stdin)
    workspace_paths = payload.get("workspacePaths", [])
    invocation_num = int(payload.get("invocationNum") or 0)

    if not workspace_paths:
        json.dump({}, sys.stdout)
        return

    ruff = find_ruff(workspace_paths)
    if ruff is None:
        json.dump({}, sys.stdout)
        return

    all_lines: list[str] = []
    for ws in workspace_paths:
        ws_files = get_changed_python_files(ws)
        if not ws_files:
            continue
        ws_ruff = find_ruff([ws, *workspace_paths]) or ruff
        with contextlib.suppress(subprocess.TimeoutExpired):
            result = subprocess.run(  # noqa: S603
                [ws_ruff, "check", "--no-fix", "--output-format=concise", *ws_files],
                check=False,
                capture_output=True,
                text=True,
                cwd=ws,
                timeout=10,
            )
            if result.returncode != 0 and result.stdout.strip():
                all_lines.extend(result.stdout.strip().splitlines())

        venv_py = find_venv_python([ws, *workspace_paths])
        if venv_py is not None:
            all_lines.extend(run_osa_ast_checks(venv_py, ws))

    if not all_lines:
        json.dump({}, sys.stdout)
        return

    if len(all_lines) > _MAX_SUMMARY_LINES:
        extra = len(all_lines) - _MAX_SUMMARY_LINES
        summary = "\n".join(all_lines[:_MAX_SUMMARY_LINES]) + f"\n... ({extra} more)"
    else:
        summary = "\n".join(all_lines)

    response: dict[str, object] = {
        "injectSteps": [
            {
                "ephemeralMessage": (
                    f"⚠️ Lint / architecture issues detected in modified files:\n\n"
                    f"```\n{summary}\n```\n\n"
                    f"Fix these before stopping."
                ),
            }
        ],
    }
    if invocation_num < _MAX_FORCE_CONTINUE_INVOCATIONS:
        response["terminationBehavior"] = "force_continue"

    json.dump(response, sys.stdout)


if __name__ == "__main__":
    main()
