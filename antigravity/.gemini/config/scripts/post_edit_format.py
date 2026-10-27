#!/usr/bin/env python3
"""PostToolUse hook: auto-format edited Python files.

Contract: reads JSON from stdin, writes {} to stdout.
Only acts on Python files (.py) and only if ruff is available.
"""

import contextlib
import json
import shutil
import subprocess
import sys
from pathlib import Path


def main() -> None:
    """Format the edited Python file with ruff if available."""
    payload = json.load(sys.stdin)

    # Extract edited file path (Path in edit_file/write_file, TargetFile legacy)
    args = payload.get("toolCall", {}).get("args", {})
    target = args.get("Path") or args.get("TargetFile", "")

    if not target or not target.endswith(".py"):
        json.dump({}, sys.stdout)
        return

    target_path = Path(target)
    if not target_path.exists():
        json.dump({}, sys.stdout)
        return

    # Find ruff: check venv in each workspace, then fall back to PATH
    workspace_paths = payload.get("workspacePaths", [])
    ruff_bin: str | None = None

    for ws in workspace_paths:
        candidate = Path(ws) / "venv" / "bin" / "ruff"
        if candidate.exists():
            ruff_bin = str(candidate)
            break

    if not ruff_bin:
        ruff_bin = shutil.which("ruff")

    if ruff_bin:
        with contextlib.suppress(subprocess.TimeoutExpired, OSError):
            subprocess.run(  # noqa: S603
                [ruff_bin, "format", str(target_path)],
                check=False,
                capture_output=True,
                timeout=10,
            )

    # PostToolUse contract: empty JSON object
    json.dump({}, sys.stdout)


if __name__ == "__main__":
    main()
