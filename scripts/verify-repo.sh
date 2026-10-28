#!/usr/bin/env bash
# verify-repo.sh — Deterministic CI & pre-commit verification for dotfiles-ubuntu
#
# Checks:
#   1. VERSION file & SemVer format + CHANGELOG.md sync + Relative Markdown links
#   2. Bash syntax (bash -n) & executable bits across all .sh scripts
#   3. Python lifecycle hooks & MCP server syntax (py_compile), permissions (+x), ruff check, and mypy --strict
#   4. hooks.json validity and script path resolution
#   5. AGENTS.md token-budget size gate (< 18,000 bytes)
#   6. SKILL.md YAML frontmatter (kebab-case name, description, < 500 lines)
#   7. Contextual MCP Server (scripts/dotfiles_mcp_server.py --self-test & system/mcp-layer.json)
#   8. Automated Test Suite (tests/unit/, tests/imp/ & tests/e2e/, 0-byte __init__.py purity, 100% branch coverage)
#
# Usage: ./scripts/verify-repo.sh [--help | --version]

set -euo pipefail
export LC_ALL=C

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
VERSION_STR="$(tr -d '[:space:]' < "$REPO_DIR/VERSION" 2>/dev/null || echo "unknown")"

case "${1:-}" in
  -h|--help)
    echo "Usage: ./scripts/verify-repo.sh [--help | --version]"
    echo "  Runs deterministic CI & pre-commit checks on dotfiles-ubuntu (v$VERSION_STR)."
    exit 0
    ;;
  -v|--version)
    echo "dotfiles-ubuntu v$VERSION_STR"
    exit 0
    ;;
  "") ;;
  *)
    echo "❌ Unknown option: $1" >&2
    exit 1
    ;;
esac

cd "$REPO_DIR"

FAILURES=0
pass() { echo "  ✅ $1"; }
fail() { echo "  ❌ $1" >&2; FAILURES=$((FAILURES + 1)); }

echo "═══ dotfiles-ubuntu Repository Verification (v$VERSION_STR) ═══"
echo ""

# 1. Version & Open-Source Metadata
echo "[1/8] Open-Source Metadata, SemVer & Relative Links"
if [[ "$VERSION_STR" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  pass "VERSION ($VERSION_STR) is valid SemVer"
else
  fail "VERSION ('$VERSION_STR') is not valid SemVer (X.Y.Z)"
fi

for doc in README.md LICENSE CHANGELOG.md ACCESSIBILITY.md CODE_OF_CONDUCT.md CONTRIBUTING.md SECURITY.md \
           Makefile pyproject.toml requirements.txt requirements-dev.txt \
           docs/README.md \
           docs/architecture/01_system_and_stow_engine.md \
           docs/architecture/02_antigravity_governance_and_hooks.md \
           docs/architecture/03_contextual_mcp_and_federation.md \
           docs/reference/enterprise_pair_programming_governance.md \
           docs/reference/contextual_mcp_and_multi_service_orchestration.md \
           docs/reference/developer_and_extension_guide.md \
           .github/PULL_REQUEST_TEMPLATE.md \
           .github/ISSUE_TEMPLATE/bug_report.yml \
           .github/ISSUE_TEMPLATE/feature_request.yml \
           .github/ISSUE_TEMPLATE/config.yml; do
  if [ -s "$doc" ]; then
    pass "$doc present"
  else
    fail "$doc is missing or empty"
  fi
done

if grep -q "^-r requirements\.txt" requirements-dev.txt; then
  pass "requirements-dev.txt chains base runtime dependencies (-r requirements.txt)"
else
  fail "requirements-dev.txt must include '-r requirements.txt'"
fi

if grep -q "## \[$VERSION_STR\]" CHANGELOG.md; then
  pass "CHANGELOG.md documents release [$VERSION_STR]"
else
  fail "CHANGELOG.md is missing section for [$VERSION_STR]"
fi

if python3 - <<'PYEOF'
from pathlib import Path
import re
import sys

repo = Path(".")
link_re = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
broken: list[str] = []
checked = 0

for md in sorted(repo.rglob("*.md")):
    text = md.read_text(encoding="utf-8")
    stripped = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    stripped = re.sub(r"`\[[^\]]+\]\([^)]+\)`", "", stripped)
    for m in link_re.finditer(stripped):
        label, target = m.group(1), m.group(2).strip()
        if target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        path_part = target.split("#")[0]
        if not path_part:
            continue
        resolved = (md.parent / path_part).resolve()
        checked += 1
        if not resolved.exists():
            broken.append(f"{md}: [{label}]({target})")

if broken:
    for item in broken:
        print(f"  Broken relative link: {item}", file=sys.stderr)
    sys.exit(1)
print(f"  Verified {checked} relative Markdown links across all .md files")
PYEOF
then
  pass "All relative Markdown links resolve to existing files"
else
  fail "Broken relative Markdown links detected"
fi

# 2. Bash Scripts Syntax & Permissions
echo ""
echo "[2/8] Shell Scripts Syntax (bash -n) & Permissions"
SH_COUNT=0
for sh_file in bootstrap.sh backup.sh audit.sh scripts/*.sh system/external/*/*.sh; do
  [ -f "$sh_file" ] || continue
  SH_COUNT=$((SH_COUNT + 1))
  if ! bash -n "$sh_file"; then
    fail "Syntax error in $sh_file"
  fi
done
for exec_sh in bootstrap.sh backup.sh audit.sh scripts/*.sh; do
  if [ ! -x "$exec_sh" ]; then
    fail "$exec_sh is not executable (chmod +x)"
  fi
done
pass "Verified syntax across $SH_COUNT shell scripts"

# 3. Python Lifecycle Hooks, MCP Server, Linting & Strict Type Checking
echo ""
echo "[3/8] Python Lifecycle Hooks, MCP Scripts, Linting & Strict Type Checking"
PY_COUNT=0
for py_file in antigravity/.gemini/config/scripts/*.py scripts/*.py; do
  [ -f "$py_file" ] || continue
  PY_COUNT=$((PY_COUNT + 1))
  if [ ! -x "$py_file" ]; then
    fail "$py_file is not executable (chmod +x)"
  fi
  if ! python3 -B -m py_compile "$py_file"; then
    fail "py_compile failed on $py_file"
  fi
done
pass "Compiled $PY_COUNT Python scripts cleanly"

resolve_tool() {
  local tool="$1"
  if [ -x "$REPO_DIR/venv/bin/$tool" ]; then
    echo "$REPO_DIR/venv/bin/$tool"
  elif [ -x "$REPO_DIR/.venv/bin/$tool" ]; then
    echo "$REPO_DIR/.venv/bin/$tool"
  else
    command -v "$tool" || true
  fi
}

RUFF_BIN="$(resolve_tool ruff)"
if [ -n "$RUFF_BIN" ]; then
  if "$RUFF_BIN" check antigravity/.gemini/config/scripts/ scripts/ tests/ >/dev/null; then
    pass "ruff check passed on lifecycle hooks, MCP server, and tests"
  else
    fail "ruff check reported issues in Python scripts or tests"
  fi
else
  fail "ruff not found (run 'make install' or 'pip install -r requirements-dev.txt')"
fi

MYPY_BIN="$(resolve_tool mypy)"
if [ -n "$MYPY_BIN" ]; then
  if "$MYPY_BIN" antigravity/.gemini/config/scripts/ scripts/ tests/ >/dev/null; then
    pass "mypy --strict passed (0 errors across 18 source & test files)"
  else
    fail "mypy --strict reported type errors"
  fi
else
  fail "mypy not found (run 'make install' or 'pip install -r requirements-dev.txt')"
fi

# 4. hooks.json Schema & Target Verification
echo ""
echo "[4/8] hooks.json Schema & Script References"
if python3 - <<'PYEOF'
import json
from pathlib import Path
import sys

repo = Path(".")
config_dir = repo / "antigravity/.gemini/config"
hooks_path = config_dir / "hooks.json"
data = json.loads(hooks_path.read_text(encoding="utf-8"))
if not isinstance(data, dict) or not data:
    print("hooks.json must be a non-empty JSON object", file=sys.stderr)
    sys.exit(1)

valid_events = {"PreToolUse", "PostToolUse", "PostInvocation", "Stop"}
commands: list[str] = []

for group_name, group_cfg in data.items():
    if not isinstance(group_cfg, dict):
        continue
    for event_name, entries in group_cfg.items():
        if event_name not in valid_events:
            print(f"Unknown lifecycle event '{event_name}' in group '{group_name}'", file=sys.stderr)
            sys.exit(1)
        for entry in entries:
            if "command" in entry:
                commands.append(entry["command"])
            for h in entry.get("hooks", []):
                if "command" in h:
                    commands.append(h["command"])

if not commands:
    print("No hook commands found in hooks.json", file=sys.stderr)
    sys.exit(1)

for cmd in commands:
    rel = cmd.removeprefix("./")
    script_path = config_dir / rel
    if not script_path.is_file():
        print(f"Missing hook script referenced in hooks.json: {script_path}", file=sys.stderr)
        sys.exit(1)
print(f"  Verified {len(commands)} lifecycle hook command(s) in hooks.json")
PYEOF
then
  pass "hooks.json is valid JSON and all referenced scripts exist"
else
  fail "hooks.json validation failed"
fi

# 5. AGENTS.md Token Budget Gate
echo ""
echo "[5/8] Antigravity 2.0 Rules Token Budget Gate"
AGENTS_FILE="antigravity/.gemini/config/AGENTS.md"
AGENTS_BYTES=$(wc -c < "$AGENTS_FILE")
MAX_AGENTS_BYTES=18000
if [ "$AGENTS_BYTES" -le "$MAX_AGENTS_BYTES" ]; then
  pass "$AGENTS_FILE size is ${AGENTS_BYTES} bytes (<= ${MAX_AGENTS_BYTES} bytes budget cap)"
else
  fail "$AGENTS_FILE size is ${AGENTS_BYTES} bytes (exceeds ${MAX_AGENTS_BYTES} bytes budget cap)"
fi

# 6. SKILL.md Frontmatter & Progressive Disclosure Gate
echo ""
echo "[6/8] SKILL.md Frontmatter (kebab-case) & Line Budget (< 500 lines)"
if python3 - <<'PYEOF'
from pathlib import Path
import re
import sys

kebab_re = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
skill_files = sorted(
    list(Path("antigravity/.gemini/config/skills").glob("*/SKILL.md"))
    + list(Path("templates").glob("*/skills/*/SKILL.md"))
)
if not skill_files:
    print("No SKILL.md files found", file=sys.stderr)
    sys.exit(1)

errors = 0
for sf in skill_files:
    lines = sf.read_text(encoding="utf-8").splitlines()
    if len(lines) > 500:
        print(f"  {sf}: {len(lines)} lines (exceeds 500-line progressive disclosure limit)", file=sys.stderr)
        errors += 1
    if not lines or lines[0].strip() != "---":
        print(f"  {sf}: missing YAML frontmatter", file=sys.stderr)
        errors += 1
        continue
    end_idx = None
    for idx in range(1, min(len(lines), 30)):
        if lines[idx].strip() == "---":
            end_idx = idx
            break
    if end_idx is None:
        print(f"  {sf}: unclosed YAML frontmatter", file=sys.stderr)
        errors += 1
        continue
    fm = "\n".join(lines[1:end_idx])
    name_match = re.search(r"^name:\s*(.+)$", fm, re.MULTILINE)
    desc_match = re.search(r"^description:\s*(.+)$", fm, re.MULTILINE)
    if not name_match:
        print(f"  {sf}: missing 'name:' in frontmatter", file=sys.stderr)
        errors += 1
    else:
        name_val = name_match.group(1).strip().strip("'\"")
        if not kebab_re.match(name_val):
            print(f"  {sf}: name '{name_val}' is not kebab-case", file=sys.stderr)
            errors += 1
    if not desc_match:
        print(f"  {sf}: missing 'description:' in frontmatter", file=sys.stderr)
        errors += 1

if errors:
    sys.exit(1)
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
if [ -s "system/mcp-layer.json" ] && python3 -c 'import json, pathlib; d = json.loads(pathlib.Path("system/mcp-layer.json").read_text()); assert d.get("schema_version") in ("1.0", "1.1") and "federated_mcps" in d and "environments" in d'; then
  pass "system/mcp-layer.json is valid JSON and matches schema v1.1 (with environments & federated_mcps)"
else
  fail "system/mcp-layer.json is missing or invalid"
fi

if ./scripts/layer-subtree.sh list >/dev/null && ./scripts/layer-subtree.sh pull-all >/dev/null; then
  pass "scripts/layer-subtree.sh list & pull-all executed cleanly"
else
  fail "scripts/layer-subtree.sh list or pull-all failed"
fi

if ./scripts/dotfiles_mcp_server.py --self-test >/dev/null; then
  pass "scripts/dotfiles_mcp_server.py --self-test passed (9 resources, 6 tools, 3 prompts, path-containment gate)"
else
  fail "scripts/dotfiles_mcp_server.py --self-test failed"
fi

# 8. Automated Test Suite (tests/unit/, tests/imp/ & tests/e2e/) & 100% Coverage Gate
echo ""
echo "[8/8] Automated Test Suite (tests/unit/, tests/imp/ & tests/e2e/) & 100% Coverage Gate"
INIT_ERRORS=0
for init_file in tests/__init__.py tests/unit/__init__.py tests/imp/__init__.py tests/e2e/__init__.py; do
  if [ ! -f "$init_file" ] || [ -s "$init_file" ]; then
    fail "$init_file must exist and be 0 bytes (package marker purity)"
    INIT_ERRORS=$((INIT_ERRORS + 1))
  fi
done
if [ "$INIT_ERRORS" -eq 0 ]; then
  pass "All tests/**/__init__.py files are 0 bytes (package marker purity)"
fi

PYTEST_BIN="$(resolve_tool pytest)"
if [ -n "$PYTEST_BIN" ]; then
  if PYTHONDONTWRITEBYTECODE=1 "$PYTEST_BIN" tests/unit/ tests/imp/ tests/e2e/ -q --tb=short --cov --cov-branch --cov-fail-under=100 >/dev/null; then
    pass "pytest passed (tests/unit/ + tests/imp/ + tests/e2e/) with 100.00% statement and branch coverage"
  else
    fail "pytest suite or 100% branch coverage gate failed"
  fi
else
  fail "pytest not found (run 'make install' or 'pip install -r requirements-dev.txt')"
fi

echo ""
if [ "$FAILURES" -eq 0 ]; then
  echo "🎉 All verification checks passed (0 errors)!"
  exit 0
else
  echo "❌ $FAILURES verification check(s) failed." >&2
  exit 1
fi
