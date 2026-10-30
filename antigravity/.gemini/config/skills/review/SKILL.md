---
name: review
description: audit code structure, quality, and testing alignment against project rules
---

# Review — `/review`

> **The quality guard.** Systematically audit a scope (module, component, test suite) against the project's rules, architecture, and testing standards.

---

## Scopes

| Scope | What it audits |
|-------|---------------|
| `/review <module>` | Full module audit: architecture, services, models, tests, coverage |
| `/review <module>/tests` | Test-only audit: classification, file mapping, coverage, patterns |
| `/review <module>/services` | Service layer audit: boundaries, dead code, naming, dependencies |
| `/review imports` | Cross-module import direction audit (full project) |
| `/review residue` | Zero-residue scan: shims, deprecated markers, backward compat aliases |

---

## 1. Full Module Audit (`/review <module>`)

Execute these checks **in order**:

### 1.1 Architecture

- [ ] **Service layer compliance** — views/controllers call services, never raw data access
- [ ] **Import direction** — no downstream module importing from upstream (check project's dependency hierarchy)
- [ ] **Dead code** — unused imports, unreachable functions, commented-out blocks
- [ ] **Naming conventions** — models as nouns, services as verbs, consistent suffixes

### 1.2 Models & Serializers

- [ ] **Field naming** — follows framework conventions, consistent with domain
- [ ] **Serializers** — 1:1 with models (or justified), no business logic in serializers
- [ ] **Choices** — use typed enumerations, no raw strings

### 1.3 Tests

Run the test audit (§2 below) as part of the full audit.

### 1.4 Coverage

// delegate: flash

```bash
# Run project-specific coverage command for the target module
<test-runner> <module>/tests/ --cov=<module> --cov-report=term-missing -q
```

- [ ] **100% target** — identify uncovered lines, classify the gap
- [ ] **Coverage quality** — not just line coverage, verify assertions exist

### 1.5 Report

Present findings as a structured table:

| Area | Status | Finding | Recommendation |
|------|--------|---------|---------------|
| Service layer | ✅/⚠️/❌ | ... | ... |

---

## 2. Test Audit (`/review <module>/tests`)

The most common source of regressions. Check against project testing rules:

### 2.1 Classification

For each test file, verify classification is correct:

| Check | Rule |
|-------|------|
| **Unit tests** | No real DB access, no real external calls, all dependencies mocked |
| **Integration tests** | Uses real DB operations or external services |
| **Misclassified** | Unit test that needs DB → move to integration. Integration test that doesn't need DB → move to unit |

### 2.2 1:1:1 File & Specification Mapping (`< 465` Lines)

// delegate: flash

Every production file with **executable logic** must have a corresponding unit test file and a bidirectional specification pointer (`Specification: docs/architecture/<spec>.md` in its docstring $\leftrightarrow$ `1:1:1` traceability table in `docs/architecture/`), and every source, test, and navigable `docs/**/*.md` file must stay strictly `< 465` lines (do NOT require artificial unit test files for purely declarative models/DTOs/catalogs without custom executable logic):

```
<module>/services/foo.py       →  <module>/tests/unit/services/test_foo.py  ↔  docs/architecture/<spec>.md
<module>/models/bar.py         →  <module>/tests/unit/models/test_bar.py    ↔  docs/architecture/<spec>.md (if bar.py has custom methods)
```

- [ ] List missing unit test files or missing `Specification: docs/architecture/...` docstring pointers
- [ ] List orphan test files (testing deleted code)
- [ ] List any source, test, or `docs/**/*.md` file $\ge 465$ lines

### 2.3 Patch Targets

- [ ] **Patch at consumption** — `@patch('<module>.services.foo.ExternalDep')` not `@patch('external.module.ExternalDep')`
- [ ] **No real external calls** in unit tests — all mocked

### 2.4 Structure

- [ ] **AAA pattern** — Arrange / Act / Assert clearly separated
- [ ] **Descriptive test names** — `test_<method>_<scenario>_<expected>`
- [ ] **Docstrings** — every test class and method has one

### 2.5 Structural Integrity (Anti-Duplication)

// delegate: flash

```bash
# Banned class name patterns (adapt glob to your language: *.py, *.ts, *.go):
grep -rn "class.*Expanded\|class.*100Coverage\|class.*Extended\|class.*Additional\|class.*Coverage" \
  <module>/tests/

# Multi-class files (target: 1 class per file):
find <module>/tests/ -name "test_*" \
  -exec sh -c 'count=$(grep -c "^class " "$1" 2>/dev/null); \
  if [ "$count" -gt 1 ]; then echo "$count: $1"; fi' _ {} \; | sort -rn

# Duplicate method names within the same file:
find <module>/tests/ -name "test_*" -exec sh -c \
  'dups=$(grep -oP "def (test_\w+)" "$1" | sort | uniq -d); \
  if [ -n "$dups" ]; then echo "$1: $dups"; fi' _ {} \;
```

- [ ] **No banned class names** — no `Expanded`, `Coverage`, `Extended`, `Additional`
- [ ] **Prefer one class per file** — justified exceptions documented
- [ ] **No duplicate method names** — each test method unique within file
- [ ] **No library testing** — tests exercise our code, not third-party libraries

---

## 3. Service Layer Audit (`/review <module>/services`)

- [ ] **Single owner** — each domain concept has ONE service owning it
- [ ] **Trigger layer is thin** — one-liner service calls, no raw data access in controllers/views/handlers
- [ ] **No circular imports** — services don't import from views
- [ ] **Dead code** — methods never called from anywhere
- [ ] **Error handling** — proper exceptions from `<module>/exceptions.py`, not generic

---

## 4. Import Direction Audit (`/review imports`)

// delegate: flash

Verify the dependency hierarchy is respected. Upstream modules must NEVER import from downstream modules.

```bash
# Scan for violations based on your project's dependency chain:
# Adapt these patterns to your module hierarchy
grep -rn "from <downstream>" <upstream>/ --include="*.py"
```

Allowed exceptions:
- `TYPE_CHECKING` blocks (runtime-safe, no circular import)
- Lazy imports inside functions (documented as intentional)

---

## 5. Zero-Residue Scan (`/review residue`)

// delegate: flash

```bash
# Find forbidden patterns (adapt glob to your language):
grep -rn "DEPRECATED\|@deprecated\|BACKWARD COMPAT\|backward.compat" . | grep -v node_modules/ | grep -v venv/ | grep -v __pycache__
grep -rn "= .*  # noqa.*alias\|# shim\|# transitional" . | grep -v node_modules/ | grep -v venv/
```

- [ ] **No deprecated markers** — code is deleted or moved atomically
- [ ] **No backward-compat aliases** — `OldName = NewName` not allowed
- [ ] **No re-export shims** — moved code is imported from its new location

---

## Rules

1. **Read the relevant rule files first** — always re-read project rules before auditing
2. **Report, don't fix** — `/review` is read-only. Capture findings, present recommendations
3. **Capture to BACKLOG.md** — if fixes are non-trivial, add items there
4. **Prioritize findings** — ❌ Critical (breaks rules) > ⚠️ Warning (should fix) > 💡 Suggestion
5. **Link evidence** — include file paths and line numbers for every finding
