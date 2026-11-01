#!/usr/bin/env bash
# verify-repo.sh — Deterministic CI & pre-commit verification for dotfiles-ubuntu
# Usage: ./scripts/verify-repo.sh [--help | --version]

set -euo pipefail
export LC_ALL=C
export PYTHONDONTWRITEBYTECODE=1

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
VERSION_STR="$(tr -d '[:space:]' < "$REPO_DIR/VERSION" 2>/dev/null || echo "unknown")"

case "${1:-}" in
  -h|--help)
    echo "Usage: ./scripts/verify-repo.sh [--help | --version]"
    echo "  Runs deterministic CI & pre-commit checks on dotfiles-ubuntu (v$VERSION_STR)."
    exit 0 ;;
  -v|--version) echo "dotfiles-ubuntu v$VERSION_STR"; exit 0 ;;
  "") ;;
  *) echo "❌ Unknown option: $1" >&2; exit 1 ;;
esac

cd "$REPO_DIR"
FAILURES=0
pass() { echo "  ✅ $1"; }
fail() { echo "  ❌ $1" >&2; FAILURES=$((FAILURES + 1)); }

echo "═══ dotfiles-ubuntu Repository Verification (v$VERSION_STR) ═══"
echo ""

# 1. Version & Open-Source Metadata
echo "[1/8] Open-Source Metadata, SemVer & Relative Links"
[[ "$VERSION_STR" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] && pass "VERSION ($VERSION_STR) is valid SemVer" || fail "VERSION ('$VERSION_STR') is not valid SemVer (X.Y.Z)"

for doc in README.md LICENSE CHANGELOG.md ACCESSIBILITY.md CODE_OF_CONDUCT.md CONTRIBUTING.md SECURITY.md \
           Makefile Dockerfile .dockerignore pyproject.toml requirements.txt requirements-dev.txt docs/README.md \
           docs/guides/01_ubuntu_system_and_multi_machine_guide.md docs/guides/02_hierarchical_layers_and_team_workflows.md \
           docs/architecture/01_system_and_stow_engine.md docs/architecture/02_antigravity_governance_and_hooks.md \
           docs/architecture/03_contextual_mcp_and_federation.md docs/architecture/04_compaction_surface_and_promotion_engines.md \
           docs/architecture/05_ephemeral_forks_and_department_bots.md docs/reference/enterprise_pair_programming_governance.md \
           docs/reference/contextual_mcp_and_multi_service_orchestration.md docs/reference/developer_and_extension_guide.md \
           .github/PULL_REQUEST_TEMPLATE.md .github/ISSUE_TEMPLATE/bug_report.yml \
           .github/ISSUE_TEMPLATE/feature_request.yml .github/ISSUE_TEMPLATE/config.yml; do
  [ -s "$doc" ] && pass "$doc present" || fail "$doc is missing or empty"
done

grep -q "^-r requirements\.txt" requirements-dev.txt && pass "requirements-dev.txt chains base runtime dependencies (-r requirements.txt)" || fail "requirements-dev.txt must include '-r requirements.txt'"
grep -q "## \[$VERSION_STR\]" CHANGELOG.md && pass "CHANGELOG.md documents release [$VERSION_STR]" || fail "CHANGELOG.md is missing section for [$VERSION_STR]"
if grep -q "^version = \"$VERSION_STR\"" pyproject.toml && grep -q "version-${VERSION_STR}-blue\.svg" README.md && grep -q "(\`$VERSION_STR\`)" README.md; then
  pass "VERSION ($VERSION_STR) is synchronized across pyproject.toml and README.md"
else
  fail "Version mismatch between VERSION ($VERSION_STR), pyproject.toml, and README.md"
fi

if python3 - <<'PYEOF'
from pathlib import Path
import re, sys

repo = Path(".")
link_re = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
latex_re = re.compile(r"\\text(?:tt|rm|sf|it|bf)?\{[^}]*_[^}]*\}")
broken, math_issues, checked = [], [], 0
for md in sorted(repo.rglob("*.md")):
    if any(p in {".git", "venv", ".venv", ".agents"} for p in md.parts):
        continue
    stripped = re.sub(r"```.*?```", "", md.read_text(encoding="utf-8"), flags=re.DOTALL)
    for line_no, line in enumerate(stripped.splitlines(), 1):
        for m in re.finditer(r"\$\$?[^\$]+\$\$?", re.sub(r"`[^`]*`", "", line)):
            if latex_re.search(m.group(0)):
                math_issues.append(f"{md}:{line_no}: {m.group(0)}")
    for m in link_re.finditer(re.sub(r"`\[[^\]]+\]\([^)]+\)`", "", stripped)):
        label, target = m.group(1), m.group(2).strip()
        if not target.startswith(("http://", "https://", "mailto:", "#")):
            path_part = target.split("#")[0]
            if path_part:
                checked += 1
                if not (md.parent / path_part).resolve().exists():
                    broken.append(f"{md}: [{label}]({target})")
if broken or math_issues:
    sys.exit("\n".join((*broken, *math_issues)))
print(f"  Verified {checked} relative Markdown links and GitHub LaTeX math syntax across all .md files")
PYEOF
then
  pass "All relative Markdown links & GitHub LaTeX math expressions verified"
else
  fail "Broken relative Markdown links or invalid GitHub LaTeX math expressions detected"
fi

# 2. Bash Scripts Syntax & Permissions
echo ""
echo "[2/8] Shell Scripts Syntax (bash -n), ShellCheck & Permissions"
SH_COUNT=0
SH_FILES=()
for sh_file in bootstrap.sh backup.sh audit.sh scripts/*.sh system/external/*/*.sh; do
  [ -f "$sh_file" ] || continue
  SH_COUNT=$((SH_COUNT + 1))
  SH_FILES+=("$sh_file")
  bash -n "$sh_file" || fail "Syntax error in $sh_file"
done
for exec_sh in bootstrap.sh backup.sh audit.sh scripts/*.sh; do
  [ -x "$exec_sh" ] || fail "$exec_sh is not executable (chmod +x)"
done
pass "Verified syntax across $SH_COUNT shell scripts"
if command -v shellcheck >/dev/null 2>&1; then
  shellcheck -S warning "${SH_FILES[@]}" >/dev/null && pass "shellcheck passed across $SH_COUNT shell scripts" || fail "shellcheck reported warnings/errors"
fi

# 3. Python Lifecycle Hooks, MCP Server, Linting & Strict Type Checking
echo ""
echo "[3/8] Python Lifecycle Hooks, MCP Scripts, Linting & Strict Type Checking"
PY_COUNT=0
for py_file in antigravity/.gemini/config/scripts/*.py scripts/*.py; do
  [ -f "$py_file" ] || continue
  PY_COUNT=$((PY_COUNT + 1))
  [ -x "$py_file" ] || fail "$py_file is not executable (chmod +x)"
  python3 -B -c 'import pathlib, sys; compile(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"), sys.argv[1], "exec")' "$py_file" || fail "Python bytecode compilation failed on $py_file"
done
for pkg_py in scripts/dotfiles_mcp/*.py; do
  [ -f "$pkg_py" ] || continue
  PY_COUNT=$((PY_COUNT + 1))
  python3 -B -c 'import pathlib, sys; compile(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"), sys.argv[1], "exec")' "$pkg_py" || fail "Python bytecode compilation failed on $pkg_py"
done
pass "Compiled $PY_COUNT Python scripts & package modules cleanly (in-memory bytecode check)"

resolve_tool() {
  local tool="$1"
  if [ -x "$REPO_DIR/venv/bin/$tool" ]; then echo "$REPO_DIR/venv/bin/$tool"
  elif [ -x "$REPO_DIR/.venv/bin/$tool" ]; then echo "$REPO_DIR/.venv/bin/$tool"
  else command -v "$tool" || true; fi
}

RUNTIME_CONTAINER_MODE=false
[ -f "/.dockerenv" ] && [ ! -d "$REPO_DIR/tests" ] && RUNTIME_CONTAINER_MODE=true

RUFF_BIN="$(resolve_tool ruff)"
if [ -n "$RUFF_BIN" ]; then
  "$RUFF_BIN" check antigravity/.gemini/config/scripts/ scripts/ tests/ >/dev/null && pass "ruff check passed on lifecycle hooks, MCP server, and tests" || fail "ruff check reported issues in Python scripts or tests"
elif [ "$RUNTIME_CONTAINER_MODE" = true ]; then
  pass "ruff check skipped in minimal runtime container image (verified at CI/build time)"
else
  fail "ruff not found (run 'make install' or 'pip install -r requirements-dev.txt')"
fi

MYPY_BIN="$(resolve_tool mypy)"
if [ -n "$MYPY_BIN" ]; then
  "$MYPY_BIN" antigravity/.gemini/config/scripts/ scripts/ tests/ >/dev/null && pass "mypy --strict passed (0 errors across all source & test files)" || fail "mypy --strict reported type errors"
elif [ "$RUNTIME_CONTAINER_MODE" = true ]; then
  pass "mypy --strict skipped in minimal runtime container image (verified at CI/build time)"
else
  fail "mypy not found (run 'make install' or 'pip install -r requirements-dev.txt')"
fi

# 4. hooks.json Schema, Script References & Hook-to-Doc Contract Parity
echo ""
echo "[4/8] hooks.json Schema, Script References & Hook-to-Doc Contract Parity"
if python3 - <<'PYEOF'
import json, re, sys
from pathlib import Path

repo = Path(".").resolve()
config_dir = repo / "antigravity/.gemini/config"
data = json.loads((config_dir / "hooks.json").read_text(encoding="utf-8"))
if not isinstance(data, dict) or not data:
    sys.exit("hooks.json must be a non-empty JSON object")

valid_events = {"PreToolUse", "PostToolUse", "PostInvocation", "Stop"}
commands, event_matchers = [], {}
for group_name, group_cfg in data.items():
    if isinstance(group_cfg, dict):
        for event_name, entries in group_cfg.items():
            if event_name not in valid_events:
                sys.exit(f"Unknown lifecycle event '{event_name}' in group '{group_name}'")
            for entry in entries:
                if isinstance(entry.get("matcher"), str) and entry["matcher"]:
                    event_matchers.setdefault(event_name, set()).update(entry["matcher"].split("|"))
                if "command" in entry:
                    commands.append(entry["command"])
                commands.extend(h["command"] for h in entry.get("hooks", []) if "command" in h)

if not commands or any(not (config_dir / c.removeprefix("./")).is_file() for c in commands):
    sys.exit("Missing hook command in hooks.json")

sys.path.insert(0, str(config_dir / "scripts"))
sys.path.insert(0, str(repo / "scripts"))
import pre_tool_guard, post_invocation_lint  # noqa: E402
from dotfiles_mcp import constants as mcp_constants  # noqa: E402

if event_matchers.get("PreToolUse") != set(pre_tool_guard._FILE_WRITE_TOOLS) | {"run_command"} or event_matchers.get("PostToolUse") != set(pre_tool_guard._FILE_WRITE_TOOLS):
    sys.exit("hooks.json matcher mismatch")

for git_sub in pre_tool_guard._DOCUMENTED_GIT_SUBCOMMANDS:
    sample = f"git {git_sub} arg" if git_sub != "subtree" else "git subtree add --prefix=layers/x repo main"
    if not pre_tool_guard._MUTATING_GIT_RE.search(sample):
        sys.exit(f"pre_tool_guard._MUTATING_GIT_RE missing {git_sub}")
for alembic_sub in pre_tool_guard._DOCUMENTED_ALEMBIC_SUBCOMMANDS:
    if not pre_tool_guard._ALEMBIC_MUTATE_RE.search(f"alembic {alembic_sub} head"):
        sys.exit(f"pre_tool_guard._ALEMBIC_MUTATE_RE missing {alembic_sub}")

agents_md = (config_dir / "AGENTS.md").read_text(encoding="utf-8")
arch_02 = (repo / "docs/architecture/02_antigravity_governance_and_hooks.md").read_text(encoding="utf-8")
arch_mcp = "\n".join((repo / f"docs/architecture/{n}").read_text(encoding="utf-8") for n in ("03_contextual_mcp_and_federation.md", "04_compaction_surface_and_promotion_engines.md", "05_ephemeral_forks_and_department_bots.md"))
security_md = (repo / "SECURITY.md").read_text(encoding="utf-8")
readme_md = (repo / "README.md").read_text(encoding="utf-8")
ext_guide = (repo / "docs/reference/developer_and_extension_guide.md").read_text(encoding="utf-8")

for doc_text in (arch_02, security_md, readme_md):
    for tok in (*pre_tool_guard._DOCUMENTED_GIT_SUBCOMMANDS, "alembic/versions/", "__init__.py", "heredoc", "tee"):
        if tok not in doc_text:
            sys.exit(f"Hook-to-doc drift: '{tok}' missing")

for target in ("alembic/versions/001_init.py", "src/orders/__init__.py", "tests/unit/__init__.py", ".agents/rules/layer-05-dept-legal.md"):
    fw_ok, fw_r = pre_tool_guard._check_file_write({"Path": f"/workspace/app/{target}", "Content": "x = 1"})
    sh_ok, sh_r = pre_tool_guard._check_command({"CommandLine": f"cat << 'EOF' > {target}\nx = 1\nEOF"})
    if fw_ok or sh_ok or fw_r != sh_r:
        sys.exit(f"Cross-channel guard parity failure on {target}")

if any(t not in agents_md for t in ("0 bytes", "__init__.py", "NEVER run mutating git commands", "git add", "git commit", "git push")):
    sys.exit("Hook-to-doc drift in AGENTS.md")
if post_invocation_lint._AGENTS_MD_MAX_BYTES != mcp_constants.AGENTS_MD_MAX_BYTES:
    sys.exit("Token budget cap mismatch")
if any(btok not in arch_02 or btok not in arch_mcp for btok in ("18,000", "80,000", "TOKEN_BUDGET_EXCEEDED", "WORKSPACE_RULES_BUDGET_EXCEEDED")):
    sys.exit("Budget token missing from Architecture docs")

for mod_py in sorted((repo / "scripts/dotfiles_mcp").glob("*.py")):
    if mod_py.name != "__init__.py" and (mod_py.name not in arch_mcp or mod_py.name not in readme_md):
        sys.exit(f"Module-to-doc drift: '{mod_py.name}'")

spec_re = re.compile(r"^Specification:\s*(docs/architecture/[a-zA-Z0-9_]+\.md)\s*$", re.MULTILINE)
for src_py in sorted([*list((config_dir / "scripts").glob("*.py")), repo / "scripts/dotfiles_mcp_server.py", *[p for p in (repo / "scripts/dotfiles_mcp").glob("*.py") if p.name != "__init__.py"]]):
    m = spec_re.search(src_py.read_text(encoding="utf-8"))
    if not m or not (repo / m.group(1)).is_file() or src_py.name not in (repo / m.group(1)).read_text(encoding="utf-8"):
        sys.exit(f"1:1:1 Traceability drift: {src_py}")

warn_re = re.compile(r'_emit_warning\(\s*"(?:WARN|ERROR|CRITICAL)"\s*,\s*"([A-Z0-9_]+)"')
for mod_py in sorted((repo / "scripts/dotfiles_mcp").glob("*.py")):
    for code in warn_re.findall(mod_py.read_text(encoding="utf-8")):
        if code not in arch_mcp:
            sys.exit(f"Warning-to-doc drift: '{code}'")

for cli_sub in ("init-fork", "list-templates", "scaffold-template", "apply-project", "diff-project", "promote-from-project", "spawn-ephemeral", "inspect-ephemeral", "reap-ephemeral", "set-global-profile", "register-subtree", "bootstrap-workspace", "sync-layer", "set-authority", "check-authority", "inspect-horizon"):
    if cli_sub not in readme_md or cli_sub not in ext_guide:
        sys.exit(f"CLI-to-doc drift: '{cli_sub}'")

if "(v1.1)" in (repo / "docs/README.md").read_text(encoding="utf-8"):
    sys.exit("Stale schema version '(v1.1)' in docs/README.md")
print(f"  Verified {len(commands)} lifecycle hook command(s) and full hook-to-doc contract parity")
PYEOF
then
  pass "hooks.json schema, matcher sets, and hook-to-doc parity verified (AGENTS.md, Arch 02/03, SECURITY.md, README.md)"
else
  fail "hooks.json or hook-to-doc parity validation failed"
fi

# 5. AGENTS.md Token Budget & Single-Language Purity Gate
echo ""
echo "[5/8] Antigravity 2.0 Rules Token Budget & Language Purity Gate"
AGENTS_FILE="antigravity/.gemini/config/AGENTS.md"
AGENTS_BYTES=$(wc -c < "$AGENTS_FILE")
[ "$AGENTS_BYTES" -le 18000 ] && pass "$AGENTS_FILE size is ${AGENTS_BYTES} bytes (<= 18000 bytes budget cap)" || fail "$AGENTS_FILE size is ${AGENTS_BYTES} bytes (exceeds 18000 bytes budget cap)"

if python3 -B - <<'PYEOF'
from pathlib import Path
import re, sys

repo = Path(".").resolve()
sp_char = re.compile(r"[\u00e1\u00e9\u00ed\u00f3\u00fa\u00f1\u00fc\u00c1\u00c9\u00cd\u00d3\u00da\u00d1\u00dc\u00bf\u00a1]")
sp_phr = re.compile(r"\b(\x66ichero|\x66icheros|\x79a que estamos|\x73iempre enfoque limpio)\b", re.IGNORECASE)
targets = sorted([
    repo / "README.md", repo / "CONTRIBUTING.md", repo / "SECURITY.md",
    repo / "ACCESSIBILITY.md", repo / "CODE_OF_CONDUCT.md", repo / "CHANGELOG.md",
    *list((repo / "antigravity").rglob("*.md")), *list((repo / "antigravity").rglob("*.py")),
    *list((repo / "docs").rglob("*.md")), *list((repo / "templates").rglob("*.md")),
    *list((repo / "scripts").rglob("*.py")), *list((repo / "scripts").glob("*.sh")),
    *list((repo / "system/external").rglob("*.sh")), *list((repo / "tests").rglob("*.py")),
])
violations = [f"{p.relative_to(repo)}:{i}" for p in targets if p.is_file() for i, ln in enumerate(p.read_text(encoding="utf-8").splitlines(), 1) if sp_char.search(ln) or sp_phr.search(ln)]
if violations:
    sys.exit("\n".join(violations))
print(f"  Verified 100% pure technical English across {len(targets)} repository files")
PYEOF
then
  pass "Single-language English purity verified across AGENTS.md, skills, templates, docs, scripts, and tests"
else
  fail "Spanish characters or phrases detected in English technical files (violates AGENTS.md §13.1)"
fi

# 6. SKILL.md Frontmatter & Progressive Disclosure Gate
echo ""
echo "[6/8] SKILL.md Frontmatter (kebab-case) & Line Budget (< 500 lines)"
if python3 - <<'PYEOF'
from pathlib import Path
import re, sys

kebab_re = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
skill_files = sorted(list(Path("antigravity/.gemini/config/skills").glob("*/SKILL.md")) + list(Path("templates").glob("*/skills/*/SKILL.md")))
if not skill_files:
    sys.exit("No SKILL.md files found")
for sf in skill_files:
    lines = sf.read_text(encoding="utf-8").splitlines()
    end_idx = next((i for i in range(1, min(len(lines), 30)) if lines[i].strip() == "---"), None) if lines and lines[0].strip() == "---" else None
    if len(lines) > 500 or end_idx is None:
        sys.exit(f"Invalid SKILL.md header or size: {sf}")
    fm = "\n".join(lines[1:end_idx])
    nm, dm = re.search(r"^name:\s*(.+)$", fm, re.MULTILINE), re.search(r"^description:\s*(.+)$", fm, re.MULTILINE)
    if not nm or not dm or not kebab_re.match(nm.group(1).strip().strip("'\"")):
        sys.exit(f"Invalid name/description in frontmatter: {sf}")
print(f"  Verified {len(skill_files)} SKILL.md files (all kebab-case, < 500 lines)")
PYEOF
then
  pass "All SKILL.md files comply with Antigravity 2.0 frontmatter & size standards"
else
  fail "SKILL.md frontmatter verification failed"
fi

# 7. Contextual MCP Server, Subtree Orchestrator & Layer Topology Manifest
echo ""
echo "[7/8] Contextual MCP Server, Subtree Orchestrator & Layer Topology Manifest"
if [ -s "system/mcp-layer.json" ] && python3 -c 'import json, pathlib; d = json.loads(pathlib.Path("system/mcp-layer.json").read_text()); assert d.get("schema_version") == "1.2" and "federated_mcps" in d and "environments" in d and "surface_bindings" in d'; then
  pass "system/mcp-layer.json is valid JSON and matches schema v1.2 (with precedence, surface_bindings, environments & federated_mcps)"
else
  fail "system/mcp-layer.json is missing or invalid"
fi

./scripts/layer-subtree.sh list >/dev/null && ./scripts/layer-subtree.sh pull-all >/dev/null && ./scripts/layer-config.sh list-templates >/dev/null \
  && pass "scripts/layer-subtree.sh (list, pull-all) & scripts/layer-config.sh (list-templates) executed cleanly" \
  || fail "scripts/layer-subtree.sh or scripts/layer-config.sh failed"

./scripts/dotfiles_mcp_server.py --self-test >/dev/null \
  && pass "scripts/dotfiles_mcp_server.py --self-test passed (9 resources, 9 tools, 3 prompts, surface projection, ephemeral forks, rcap1 L0->L3 compaction, path-containment gate)" \
  || fail "scripts/dotfiles_mcp_server.py --self-test failed"

grep -q "^FROM ubuntu:26.04" Dockerfile && grep -q "^USER ubuntu" Dockerfile && grep -q "dotfiles_mcp_server\.py" Dockerfile \
  && pass "Dockerfile matches Ubuntu 26.04 non-root MCP container contract" \
  || fail "Dockerfile is missing required Ubuntu 26.04, non-root USER, or MCP ENTRYPOINT contract"

# 8. Automated Test Suite (tests/unit/, tests/imp/ & tests/e2e/) & 100% Coverage Gate
echo ""
echo "[8/8] Automated Test Suite (tests/unit/, tests/imp/ & tests/e2e/) & 100% Coverage Gate"
if [ "$RUNTIME_CONTAINER_MODE" = true ]; then
  pass "Runtime container mode (/.dockerenv without tests/): test suite excluded from production image via .dockerignore"
else
  INIT_ERRORS=0
  for init_file in scripts/dotfiles_mcp/__init__.py tests/__init__.py tests/unit/__init__.py tests/unit/dotfiles_mcp/__init__.py tests/imp/__init__.py tests/e2e/__init__.py; do
    if [ ! -f "$init_file" ] || [ -s "$init_file" ]; then
      fail "$init_file must exist and be 0 bytes (package marker purity)"
      INIT_ERRORS=$((INIT_ERRORS + 1))
    fi
  done
  [ "$INIT_ERRORS" -eq 0 ] && pass "All package and test __init__.py files are 0 bytes (package marker purity)"

  if python3 - <<'PYEOF'
from pathlib import Path
import sys

repo = Path(".").resolve()
for mod in sorted((repo / "scripts/dotfiles_mcp").glob("*.py")):
    if mod.name not in {"__init__.py", "constants.py", "catalogs.py"} and not (repo / "tests/unit/dotfiles_mcp" / f"test_{mod.stem}.py").is_file():
        sys.exit(f"Missing 1:1 unit test file for {mod}")

all_sized_files = sorted([
    repo / "README.md", *list(repo.glob("*.sh")), *list((repo / "scripts").glob("*.sh")),
    *list((repo / "antigravity/.gemini/config/scripts").glob("*.py")), *list((repo / "scripts").glob("*.py")),
    *list((repo / "scripts/dotfiles_mcp").glob("*.py")), *list((repo / "tests").rglob("*.py")),
    *list((repo / "docs").rglob("*.md")), *list((repo / "templates").rglob("*.md")),
])
for p in all_sized_files:
    lines = len(p.read_text(encoding="utf-8").splitlines())
    if lines >= 465:
        sys.exit(f"{p.relative_to(repo)}: {lines} lines (exceeds 465-line cap)")

import ast
for tp in sorted((repo / "tests").rglob("test_*.py")):
    tree = ast.parse(tp.read_text(encoding="utf-8"), filename=str(tp))
    top_tests = [s.name for s in tree.body if isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef)) and s.name.startswith("test_")]
    test_classes = [s for s in tree.body if isinstance(s, ast.ClassDef) and s.name.startswith("Test")]
    if top_tests or len(test_classes) != 1:
        sys.exit(f"{tp.relative_to(repo)}: must define 1 Test* class and 0 top-level test_* functions")
    for item in test_classes[0].body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name.startswith("test_") and not ast.get_docstring(item):
            sys.exit(f"{tp.relative_to(repo)}:{item.lineno}: missing docstring on {item.name}")
PYEOF
  then
    pass "1:1:1 unit test & spec mapping and < 465-line file size discipline verified across all Python, Bash, docs/, and templates/ files"
  else
    fail "1:1:1 mapping or < 465-line file size gate failed"
  fi

  PYTEST_BIN="$(resolve_tool pytest)"
  if [ -n "$PYTEST_BIN" ]; then
    if UNIT_COV_OUT="$(PYTHONDONTWRITEBYTECODE=1 "$PYTEST_BIN" tests/unit/dotfiles_mcp/ -q --tb=short --cov=scripts/dotfiles_mcp --cov-branch --cov-report=term-missing --cov-fail-under=100 2>&1)"; then
      pass "Isolated 1:1 unit test coverage verified (100.00% on scripts/dotfiles_mcp without E2E/self-test masking)"
    else
      echo "$UNIT_COV_OUT" >&2
      fail "Isolated unit test coverage failed on scripts/dotfiles_mcp (< 100%)"
    fi
    if PYTEST_OUT="$(PYTHONDONTWRITEBYTECODE=1 "$PYTEST_BIN" tests/unit/ tests/imp/ tests/e2e/ -q --tb=short --cov --cov-branch --cov-report=term-missing --cov-fail-under=100 2>&1)"; then
      pass "pytest passed (tests/unit/ + tests/imp/ + tests/e2e/) with 100.00% statement and branch coverage"
    else
      echo "$PYTEST_OUT" >&2
      fail "pytest suite or 100% branch coverage gate failed"
    fi
  else
    fail "pytest not found (run 'make install' or 'pip install -r requirements-dev.txt')"
  fi
fi

echo ""
if [ "$FAILURES" -eq 0 ]; then
  echo "🎉 All verification checks passed (0 errors)!"
  exit 0
else
  echo "❌ $FAILURES verification check(s) failed." >&2
  exit 1
fi
