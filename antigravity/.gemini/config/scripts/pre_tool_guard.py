#!/usr/bin/env python3
"""PreToolUse hook: deterministic safety & architectural guard.

Contract: reads JSON from stdin, writes {"decision": "allow"|"deny", ...} to stdout.
Hard-blocks (zero prompt tokens, 100% deterministic):
1. Non-empty writes/edits to consumer ``src/**/__init__.py`` or ``tests/**/__init__.py``.
2. Manual creation/editing of migration files under ``alembic/versions/*.py``.
3. Automatic execution of mutating git commands (``git add``, ``git commit``,
   ``git push``, ``git reset --hard``) or manual ``alembic revision/upgrade``.
"""

import json
import re
import sys

_FILE_WRITE_TOOLS = frozenset(
    {
        "write_file",
        "edit_file",
        "replace_file_content",
        "multi_replace_file_content",
        "write_to_file",
    }
)

_MUTATING_GIT_RE = re.compile(
    r"(?:^|[;&|]\s*|\n\s*)git\s+(?:-C\s+\S+\s+)*(?:add|commit|push|reset\s+--hard|clean\s+-[a-zA-Z]*f|subtree\s+(?:add|pull|push|merge))\b"
)
_ALEMBIC_MUTATE_RE = re.compile(r"(?:^|[;&|]\s*|\n\s*)alembic\s+(?:revision|upgrade|downgrade)\b")


def _check_file_write(args: dict[str, object]) -> tuple[bool, str]:
    """Validate file write/edit targets against architectural invariants."""
    target = str(args.get("Path") or args.get("TargetFile") or "").replace("\\", "/")
    if not target:
        return True, ""

    # 1. Zero-Touch Migration Policy: never write/edit alembic/versions/*.py manually
    if "/alembic/versions/" in target and target.endswith(".py"):
        msg = (
            "Blocked by pre_tool_guard (Zero-Touch Migration Policy): "
            "Never create or modify files in alembic/versions/*.py manually. "
            "Ask the user to run 'osa db revision' / 'osa db upgrade'."
        )
        return False, msg

    # 2. 0-byte __init__.py purity in consumer src/** and all tests/**
    if target.endswith("/__init__.py"):
        is_tests_init = "/tests/" in target
        is_consumer_src_init = "/src/" in target and "/src/osa_framework/" not in target
        if is_tests_init or is_consumer_src_init:
            content = str(
                args.get("Content") or args.get("Replacement") or args.get("CodeContent") or ""
            )
            if content or args.get("ReplacementChunks"):
                msg = (
                    "Blocked by pre_tool_guard (__init__.py Purity): "
                    "Consumer src/**/__init__.py and tests/**/__init__.py files "
                    "MUST remain 100% empty (0 bytes). Declare bounded-context "
                    "metadata and exclude_contexts in osa-manifest.yaml."
                )
                return False, msg

    return True, ""


def _check_command(args: dict[str, object]) -> tuple[bool, str]:
    """Validate shell commands against commit and migration discipline."""
    cmd = str(args.get("CommandLine") or "")
    if not cmd:
        return True, ""

    if _MUTATING_GIT_RE.search(cmd):
        msg = (
            "Blocked by pre_tool_guard (Commit Discipline): "
            "Never auto-run mutating git commands (git add, git commit, git push, "
            "git reset --hard). Present commit blocks for the user to run."
        )
        return False, msg

    if _ALEMBIC_MUTATE_RE.search(cmd):
        msg = (
            "Blocked by pre_tool_guard (Migration Policy): "
            "Never run 'alembic revision/upgrade/downgrade' directly. "
            "The user handles migrations interactively via 'osa db'."
        )
        return False, msg

    return True, ""


def main() -> None:
    """Evaluate PreToolUse guard rules."""
    payload = json.load(sys.stdin)
    tool_call = payload.get("toolCall", {})
    tool_name = str(tool_call.get("name") or "")
    args = tool_call.get("args") or {}

    allowed = True
    reason = ""

    if tool_name in _FILE_WRITE_TOOLS and isinstance(args, dict):
        allowed, reason = _check_file_write(args)
    elif tool_name == "run_command" and isinstance(args, dict):
        allowed, reason = _check_command(args)

    if allowed:
        json.dump({"decision": "allow"}, sys.stdout)
    else:
        json.dump({"decision": "deny", "reason": reason}, sys.stdout)


if __name__ == "__main__":
    main()
