#!/usr/bin/env python3
"""Stop hook: verify tests pass before the agent stops.

Contract: reads JSON from stdin, writes {"decision": ...} to stdout.
If tests fail, returns decision="continue" to block the stop.
Only fires on normal turn completion ("NO_TOOL_CALL" / "model_stop").
Only fires if Python source files were edited or created (checks git diff + untracked).
"""

import contextlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

_SUMMARY_TAIL_LINES = 3


def find_venv(workspace_paths: list[str]) -> Path | None:
    """Find the first venv/.venv with pytest available."""
    for ws in workspace_paths:
        for venv_dir in ("venv", ".venv"):
            venv_python = Path(ws) / venv_dir / "bin" / "python"
            if venv_python.exists():
                return venv_python
    return None


def has_python_changes(workspace_path: str) -> bool:
    """Check if any .py files have been modified, staged, or newly created."""
    git_bin = shutil.which("git") or "git"
    with contextlib.suppress(subprocess.TimeoutExpired, FileNotFoundError):
        unstaged = subprocess.run(  # noqa: S603
            [git_bin, "diff", "--name-only", "--diff-filter=ACMR", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
            cwd=workspace_path,
            timeout=5,
        )
        staged = subprocess.run(  # noqa: S603
            [git_bin, "diff", "--name-only", "--cached", "--diff-filter=ACMR"],
            check=False,
            capture_output=True,
            text=True,
            cwd=workspace_path,
            timeout=5,
        )
        untracked = subprocess.run(  # noqa: S603
            [git_bin, "ls-files", "--others", "--exclude-standard", "--", "*.py"],
            check=False,
            capture_output=True,
            text=True,
            cwd=workspace_path,
            timeout=5,
        )
        all_files = unstaged.stdout + staged.stdout + untracked.stdout
        return any(f.strip().endswith(".py") for f in all_files.splitlines() if f.strip())
    return True


def run_tests(venv_python: Path, workspace_path: str) -> tuple[bool, str]:
    """Run pytest and return (passed, summary)."""
    try:
        result = subprocess.run(  # noqa: S603
            [str(venv_python), "-m", "pytest", "--tb=line", "-q", "--no-header", "-x"],
            check=False,
            capture_output=True,
            text=True,
            cwd=workspace_path,
            timeout=120,
        )
        lines = result.stdout.strip().splitlines()
        if len(lines) >= _SUMMARY_TAIL_LINES:
            summary = "\n".join(lines[-_SUMMARY_TAIL_LINES:])
        else:
            summary = result.stdout.strip()

        if result.returncode == 0:
            return True, summary
        error_detail = result.stderr.strip()[-200:] if result.stderr else ""
        return False, f"{summary}\n{error_detail}".strip()

    except subprocess.TimeoutExpired:
        return False, "Tests timed out after 120 seconds."


def main() -> None:
    """Verify tests pass across modified workspaces before stopping."""
    payload = json.load(sys.stdin)

    termination_reason = payload.get("terminationReason", "")

    if termination_reason not in ("NO_TOOL_CALL", "model_stop"):
        json.dump({"decision": "stop"}, sys.stdout)
        return

    workspace_paths = payload.get("workspacePaths", [])

    if not workspace_paths:
        json.dump({"decision": "stop"}, sys.stdout)
        return

    failures: list[str] = []
    for ws in workspace_paths:
        if not has_python_changes(ws):
            continue
        venv_python = find_venv([ws, *workspace_paths])
        if venv_python is None:
            continue
        passed, summary = run_tests(venv_python, ws)
        if not passed:
            ws_name = Path(ws).name
            failures.append(f"[{ws_name}]\n{summary}")

    if not failures:
        json.dump({"decision": "stop"}, sys.stdout)
    else:
        joined = "\n\n".join(failures)
        json.dump(
            {
                "decision": "continue",
                "reason": (f"Tests are FAILING. Fix them before stopping.\n\n{joined}"),
            },
            sys.stdout,
        )


if __name__ == "__main__":
    main()
