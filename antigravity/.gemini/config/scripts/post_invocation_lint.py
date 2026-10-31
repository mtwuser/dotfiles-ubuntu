#!/usr/bin/env python3
"""PostInvocation hook: lint & architecture check on modified Python files.

Specification: docs/architecture/02_antigravity_governance_and_hooks.md
Contract: reads JSON from stdin, writes {"injectSteps": [...], ...} to stdout.
Runs ruff check, universal structural gates (< 465 lines, AAA test comments),
and hexagonal AST check_project/check_tests (when available) on Python files with
uncommitted or untracked changes across active workspaces and dotfiles-ubuntu.
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
_AGENTS_MD_MAX_BYTES = 18000
_TOTAL_RULES_BUDGET_MAX_BYTES = 80000
_MAX_PYTHON_FILE_LINES = 465
_DOTFILES_REPO_DIR = Path(__file__).resolve().parents[4]


def resolve_effective_workspaces(
    workspace_paths: list[str],
    dotfiles_repo: Path | None = None,
) -> list[str]:
    """Return workspace_paths plus the dotfiles-ubuntu repo if present and distinct."""
    effective = list(workspace_paths)
    if not effective:
        return []
    candidate = dotfiles_repo if dotfiles_repo is not None else _DOTFILES_REPO_DIR
    candidate_str = str(candidate)
    if (candidate / ".git").exists() and candidate_str not in effective:
        effective.append(candidate_str)
    return effective


def check_universal_python_structure(py_files: list[str]) -> list[str]:
    """Enforce universal < 465-line file cap, AAA test comments, and 1:1:1 spec pointers."""
    violations: list[str] = []
    for file_str in py_files:
        p = Path(file_str)
        if not p.is_file():
            continue
        text = p.read_text(encoding="utf-8", errors="ignore")
        line_count = len(text.splitlines())
        if line_count >= _MAX_PYTHON_FILE_LINES:
            violations.append(
                f"{file_str}:1 [max-file-lines] File has {line_count} lines "
                f"(must be < {_MAX_PYTHON_FILE_LINES}; extract modules and 1:1 tests)"
            )
        norm = "/" + str(p).replace("\\", "/").lstrip("/")
        if "/alembic/versions/" in norm:
            violations.append(
                f"{file_str}:1 [zero-touch-migration] Never create or modify "
                "alembic/versions/*.py files manually"
            )
        if p.name == "__init__.py":
            if ("/tests/" in norm or ("/src/" in norm and "_framework/" not in norm)) and text:
                violations.append(
                    f"{file_str}:1 [init-purity] Consumer src/**/__init__.py and "
                    "tests/**/__init__.py must remain 0 bytes"
                )
        elif p.name.startswith("test_") and "def test_" in text:
            missing_aaa = [
                marker for marker in ("# Arrange", "# Act", "# Assert") if marker not in text
            ]
            if missing_aaa:
                violations.append(
                    f"{file_str}:1 [missing-aaa] Test file missing {', '.join(missing_aaa)}"
                )
        elif "Specification: docs/architecture/" not in text:
            sibling_has_spec = any(
                "Specification: docs/architecture/"
                in sib.read_text(encoding="utf-8", errors="ignore")
                for sib in p.parent.glob("*.py")
                if sib != p and sib.name != "__init__.py"
            )
            if sibling_has_spec:
                violations.append(
                    f"{file_str}:1 [missing-spec-pointer] Module missing "
                    "'Specification: docs/architecture/<spec>.md' docstring header"
                )
    return violations


def check_universal_doc_structure(doc_files: list[str]) -> list[str]:
    """Enforce universal < 465-line file cap on root README.md and navigable docs/**/*.md files."""
    violations: list[str] = []
    for file_str in doc_files:
        p = Path(file_str)
        if not p.is_file():
            continue
        line_count = len(p.read_text(encoding="utf-8", errors="ignore").splitlines())
        if line_count >= _MAX_PYTHON_FILE_LINES:
            violations.append(
                f"{file_str}:1 [max-doc-lines] Documentation file has {line_count} lines "
                f"(must be < {_MAX_PYTHON_FILE_LINES}; split into modular guides/specs)"
            )
    return violations


def check_rules_token_budget(
    workspace_paths: list[str],
    agents_md_path: Path | None = None,
) -> list[str]:
    """Check if active always_on rules exceed token budget limits."""
    global_agents = agents_md_path or (Path(__file__).resolve().parent.parent / "AGENTS.md")
    total_bytes = 0
    warnings: list[str] = []
    if global_agents.is_file():
        agents_size = global_agents.stat().st_size
        total_bytes += agents_size
        if agents_size > _AGENTS_MD_MAX_BYTES:
            warnings.append(
                f"[TOKEN_BUDGET_EXCEEDED] {global_agents}: {agents_size} bytes "
                f"(exceeds {_AGENTS_MD_MAX_BYTES}-byte AGENTS.md cap; context truncation risk)"
            )
    for ws in workspace_paths:
        rules_dir = Path(ws) / ".agents" / "rules"
        if rules_dir.is_dir():
            for rf in sorted(rules_dir.glob("*.md")):
                content = rf.read_text(encoding="utf-8", errors="ignore")
                if "trigger: model_decision" not in content[:300]:
                    total_bytes += len(content.encode("utf-8"))
    if total_bytes > _TOTAL_RULES_BUDGET_MAX_BYTES:
        warnings.append(
            f"[WORKSPACE_RULES_BUDGET_EXCEEDED] Combined always_on rules total "
            f"{total_bytes} bytes (~{total_bytes // 4} tokens > 20,000-token budget)"
        )
    return warnings


def find_ruff(workspace_paths: list[str]) -> str | None:
    """Find ruff: check venv/.venv in each workspace, then fall back to PATH."""
    for ws in workspace_paths:
        for venv_dir in ("venv", ".venv"):
            venv_ruff = Path(ws) / venv_dir / "bin" / "ruff"
            if venv_ruff.exists():
                return str(venv_ruff)
    return shutil.which("ruff")


def find_venv_python(workspace_paths: list[str]) -> str | None:
    """Find the first venv/.venv Python interpreter across workspaces."""
    for ws in workspace_paths:
        for venv_dir in ("venv", ".venv"):
            venv_py = Path(ws) / venv_dir / "bin" / "python"
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


def get_changed_doc_files(workspace_path: str) -> list[str]:
    """Get root README.md and navigable docs/**/*.md files with uncommitted or untracked changes."""
    git_bin = shutil.which("git") or "git"
    files: set[str] = set()
    for cmd in [
        [git_bin, "diff", "--name-only", "--diff-filter=ACMR", "--", "README.md", "docs/"],
        [
            git_bin,
            "diff",
            "--name-only",
            "--cached",
            "--diff-filter=ACMR",
            "--",
            "README.md",
            "docs/",
        ],
        [
            git_bin,
            "ls-files",
            "--others",
            "--exclude-standard",
            "--",
            "README.md",
            "docs/*.md",
            "docs/**/*.md",
        ],
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
                if rel_file == "README.md" or (
                    rel_file.startswith("docs/") and rel_file.endswith(".md")
                ):
                    full = Path(workspace_path) / rel_file
                    if full.exists():
                        files.add(str(full))
    return sorted(files)


def run_project_ast_checks(venv_python: str, workspace_path: str) -> list[str]:
    """Run fast AST check_project and check_tests if workspace is a manifest/framework repo."""
    ws = Path(workspace_path)
    fw_dirs = sorted(ws.glob("src/*_framework"))
    has_manifest = any(ws.glob("*-manifest.yaml"))
    if not has_manifest and not fw_dirs:
        return []

    src_dir = fw_dirs[0] if fw_dirs else ws / "src"
    tests_dir = ws / "tests" / "unit" if (ws / "tests" / "unit").exists() else ws / "tests"
    snippet = (
        "import importlib, pkgutil, sys; from pathlib import Path; "
        "pkgs = [m.name for m in pkgutil.iter_modules() if m.name.endswith('_framework')]; "
        "mod = importlib.import_module("
        "f'{pkgs[0]}.core.testing.architecture_linter') if pkgs else None; "
        f"p1, p2 = Path({str(src_dir)!r}), Path({str(tests_dir)!r}); "
        "v1 = mod.check_project(p1) if (mod and p1.is_dir()) else []; "
        "v2 = mod.check_tests(p2) if (mod and p2.is_dir()) else []; "
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
    """Run ruff check, structural gates, and project AST checks on modified Python files."""
    payload = json.load(sys.stdin)
    raw_workspaces = payload.get("workspacePaths", [])
    invocation_num = int(payload.get("invocationNum") or 0)

    workspace_paths = resolve_effective_workspaces(raw_workspaces)
    if not workspace_paths:
        json.dump({}, sys.stdout)
        return

    ruff = find_ruff(workspace_paths)
    if ruff is None:
        json.dump({}, sys.stdout)
        return

    all_lines: list[str] = check_rules_token_budget(workspace_paths)
    for ws in workspace_paths:
        all_lines.extend(check_universal_doc_structure(get_changed_doc_files(ws)))
        ws_files = get_changed_python_files(ws)
        if not ws_files:
            continue
        all_lines.extend(check_universal_python_structure(ws_files))
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
            all_lines.extend(run_project_ast_checks(venv_py, ws))

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
