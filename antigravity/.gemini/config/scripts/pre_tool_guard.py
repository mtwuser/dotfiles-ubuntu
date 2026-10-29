#!/usr/bin/env python3
"""PreToolUse hook: deterministic safety & architectural guard.

Contract: reads JSON from stdin, writes {"decision": "allow"|"deny", ...} to stdout.
Hard-blocks (zero prompt tokens, 100% deterministic):
1. Non-empty writes/edits to consumer ``src/**/__init__.py`` or ``tests/**/__init__.py``.
2. Manual creation/editing of migration files under ``alembic/versions/*.py``.
3. Automatic execution of mutating git commands (``git add``, ``git commit``,
   ``git push``, ``git reset --hard``, ``git clean -f``,
   ``git subtree add|pull|push|merge``) or manual ``alembic revision/upgrade/downgrade``.
"""

from __future__ import annotations

import json
import re
import shlex
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

_DOCUMENTED_GIT_SUBCOMMANDS: tuple[str, ...] = (
    "add",
    "commit",
    "push",
    "reset --hard",
    "clean -f",
    "subtree",
)
_DOCUMENTED_ALEMBIC_SUBCOMMANDS: tuple[str, ...] = (
    "revision",
    "upgrade",
    "downgrade",
)

_SEPARATOR_CHARS = frozenset(";&|()\n")
_COMMAND_WRAPPERS = frozenset({"env", "command", "sudo", "nohup", "nice", "time"})
_SHELL_BINARIES = frozenset({"sh", "bash", "zsh", "dash"})
_GIT_FLAGS_WITH_ARG = frozenset(
    {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--super-prefix", "--config-env"}
)
_ALEMBIC_FLAGS_WITH_ARG = frozenset({"-c", "--config", "-n", "--name", "-x"})

_MUTATING_GIT_RE = re.compile(
    r"(?:^|[;&|(`]\s*|\$\(\s*|\n\s*)git\s+(?:(?:-[Cc]|--git-dir|--work-tree)\s+\S+\s+|-\S+\s+)*(?:add|commit|push|reset\s+--hard|clean\s+-[a-zA-Z]*f|subtree\s+(?:add|pull|push|merge))\b"
)
_ALEMBIC_MUTATE_RE = re.compile(
    r"(?:^|[;&|(`]\s*|\$\(\s*|\n\s*)(?:python[0-9.]*\s+-m\s+)?alembic\s+(?:-[cnxh]\s+\S+\s+|-\S+\s+)*(?:revision|upgrade|downgrade)\b"
)


def _split_shell_segments(cmd: str) -> list[list[str]]:
    """Tokenize a shell command into individual command segments respecting quotes."""
    lexer = shlex.shlex(cmd, posix=True, punctuation_chars=";&|()\n")
    lexer.whitespace = " \t\r"
    lexer.whitespace_split = True
    segments: list[list[str]] = []
    current: list[str] = []
    for token in lexer:
        if set(token) <= _SEPARATOR_CHARS:
            if current:
                segments.append(current)
                current = []
        else:
            current.append(token)
    if current:
        segments.append(current)
    return segments


def _strip_leading_env_and_wrappers(tokens: list[str]) -> list[str]:
    """Strip leading KEY=VALUE env assignments and command wrappers (env, sudo, etc.)."""
    idx = 0
    n = len(tokens)
    while idx < n:
        tok = tokens[idx]
        if "=" in tok and not tok.startswith("-"):
            idx += 1
            continue
        prog = tok.rsplit("/", 1)[-1]
        if prog in _COMMAND_WRAPPERS:
            idx += 1
            while idx < n and tokens[idx].startswith("-"):
                flag = tokens[idx]
                idx += 1
                if flag in {"-u", "-g", "-C"} and idx < n:
                    idx += 1
            continue
        if prog.startswith("python") and idx + 2 < n and tokens[idx + 1] == "-m":
            idx += 2
            continue
        if prog in {"uv", "poetry"} and idx + 1 < n and tokens[idx + 1] == "run":
            idx += 2
            continue
        break
    return tokens[idx:]


def _extract_subshell_command(tokens: list[str]) -> str | None:
    """Return nested command string if tokens invoke sh/bash -c '<cmd>'."""
    if not tokens:
        return None
    prog = tokens[0].rsplit("/", 1)[-1]
    if prog not in _SHELL_BINARIES:
        return None
    for idx in range(1, len(tokens) - 1):
        tok = tokens[idx]
        if tok == "-c" or (tok.startswith("-") and not tok.startswith("--") and tok.endswith("c")):
            return tokens[idx + 1]
    return None


def _is_mutating_git_segment(tokens: list[str]) -> bool:
    """Return True if a tokenized command segment executes a mutating git subcommand."""
    if not tokens or tokens[0].rsplit("/", 1)[-1] != "git":
        return False
    idx = 1
    n = len(tokens)
    while idx < n and tokens[idx].startswith("-"):
        flag = tokens[idx]
        idx += 1
        if flag in _GIT_FLAGS_WITH_ARG and idx < n:
            idx += 1
    if idx >= n:
        return False
    subcmd = tokens[idx]
    rest = tokens[idx + 1 :]
    if subcmd in {"add", "commit", "push"}:
        return True
    if subcmd == "reset":
        return "--hard" in rest
    if subcmd == "clean":
        return any(
            t == "--force" or (t.startswith("-") and not t.startswith("--") and "f" in t)
            for t in rest
        )
    if subcmd == "subtree":
        return any(t in {"add", "pull", "push", "merge"} for t in rest)
    return False


def _is_mutating_alembic_segment(tokens: list[str]) -> bool:
    """Return True if a tokenized command segment executes a mutating alembic subcommand."""
    if not tokens or tokens[0].rsplit("/", 1)[-1] != "alembic":
        return False
    idx = 1
    n = len(tokens)
    while idx < n and tokens[idx].startswith("-"):
        flag = tokens[idx]
        idx += 1
        if flag in _ALEMBIC_FLAGS_WITH_ARG and idx < n:
            idx += 1
    return idx < n and tokens[idx] in {"revision", "upgrade", "downgrade"}


def _inspect_command_string(cmd: str) -> str | None:
    """Inspect a shell command string via shlex tokenization and regex fallback."""
    has_cmd_subst = "$(" in cmd or "`" in cmd
    try:
        segments = _split_shell_segments(cmd)
    except ValueError:
        segments = []
        has_cmd_subst = True

    for raw_seg in segments:
        seg = _strip_leading_env_and_wrappers(raw_seg)
        subshell_cmd = _extract_subshell_command(seg)
        if subshell_cmd is not None:
            nested_hit = _inspect_command_string(subshell_cmd)
            if nested_hit is not None:
                return nested_hit
        if _is_mutating_git_segment(seg):
            return "git"
        if _is_mutating_alembic_segment(seg):
            return "alembic"

    if has_cmd_subst:
        if _MUTATING_GIT_RE.search(cmd):
            return "git"
        if _ALEMBIC_MUTATE_RE.search(cmd):
            return "alembic"

    return None


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
            chunks = args.get("ReplacementChunks")
            has_non_empty_chunks = isinstance(chunks, list) and any(
                isinstance(c, dict) and str(c.get("ReplacementContent") or "") for c in chunks
            )
            if content or has_non_empty_chunks:
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

    hit = _inspect_command_string(cmd)
    if hit == "git":
        msg = (
            "Blocked by pre_tool_guard (Commit Discipline): "
            "Never auto-run mutating git commands (git add, git commit, git push, "
            "git reset --hard, git clean -f, git subtree). "
            "Present commit blocks for the user to run."
        )
        return False, msg

    if hit == "alembic":
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
