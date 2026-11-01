---
name: review
description: audit code structure, quality, and testing alignment against project rules
---

# Review — `/review`

> **The quality guard.** Systematically audit a scope (module, component, test suite) against the project's rules, architecture, and testing standards.

---

## Scopes & Mode Selection (`workspace_mode`)

Check `workspace_mode` from `make status` (or `.agents/rules/*.md`):
- **`technical` / `hybrid` mode (`technical-base` / `tech-stack/*`)**: Execute §1–§5 below (plus §6 when `hybrid`).
- **`business` mode (`business-base` / `business-stack/*` / `Root 0` / `Department`)**: Skip code/unit-test checks (§1–§4) and execute **§6 Business & Normative Governance Audit (`corporate/`, `templates/`, `docs/`, `surfaces/`)** plus **§5 Zero-Residue Scan**.

| Scope | What it audits |
|-------|---------------|
| `/review <module>` | Full module audit (Technical §1–§5) or Corporate/Department pack audit (Business §6) |
| `/review <module>/tests` | Test-only audit: classification, file mapping, coverage, patterns (Technical §2) |
| `/review <module>/services` | Service layer audit: boundaries, dead code, naming, dependencies (Technical §3) |
| `/review corporate` | Business & normative ledger audit: *Lex Superior*, SSoT ledgers, Traceable IDs, 3-part verification, IP firewall (Business §6) |
| `/review imports` | Cross-module import direction audit (Technical §4) |
| `/review residue` | Zero-residue scan: shims, deprecated markers, backward compat aliases (§5) |

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

### 2.1 Classification (`Unit` vs. `Imp` vs. `E2E`)

For each test file, verify classification matches our 3-tier ontology (`imp` = **Implementation tests**, never `int`):

| Check | Rule |
|-------|------|
| **Unit tests (`tests/unit/`)** | No real DB/subprocess/network access, all dependencies mocked, `< 1s`/test, `100%` isolated branch coverage across 4 quadrants |
| **Implementation tests (`tests/imp/`)** | Real internal boundary implementation (DB persistence, CLI/`stdio` subprocesses, FS permissions, `Spec <-> Code <-> Doc` parity) |
| **E2E tests (`tests/e2e/`)** | Complete multi-step human persona journeys from entrypoint to final state |
| **Misclassified** | Unit test with real DB/subprocess I/O → move to `tests/imp/`. Implementation test that mocks the boundary under test → move to `tests/unit/` |

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

### 2.4 Structure, Bidirectional 3-Tier Flow & Human-Agent `1:1:1` Comprehension Symbiosis

- [ ] **Bidirectional 3-Tier Flow (`Top-Down E2E -> Imp -> Unit` vs. `Bottom-Up Unit -> Imp -> E2E`)** — read normative specs and self-documenting test suites **Top-Down (`E2E` persona journeys $\rightarrow$ `Imp` boundary/parity implementation $\rightarrow$ `Unit` 4-quadrant suites)** before inspecting or mutating source code; execute verification **Bottom-Up (`Unit` in strict isolation first $\rightarrow$ `Imp` $\rightarrow$ `E2E`)** so higher tiers never mask missing unit branch coverage
- [ ] **Single `Test<Module>` suite/class per file** — 1 class per test file, 0 loose top-level `test_*` functions, and `Specification: docs/architecture/<spec>.md` in the module docstring
- [ ] **AAA pattern** — `# Arrange` / `# Act` / `# Assert` clearly separated (never merged)
- [ ] **Self-documenting behavioral test names** — `test_<subject>_<scenario>_<expected>` readable in natural language
- [ ] **1-line invariant docstrings & 4-quadrant unit deduction** — every test class and test method states the functional/security invariant it proves (covering nominal, `N` vs `N ± 1` boundaries, bipolar guards, and outbound failure modes)

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

## 6. Business & Normative Governance Audit (`/review corporate` or `workspace_mode == "business"`)

When operating in `Root 0` (`corporate`), `domain-policy`, or `Department` (`business-base` / `business-stack/*`) workspaces, audit normative documents, corporate ledgers, and template packs against `.agents/rules/business-base.md`:

- [ ] **1. Lex Superior (`0..100`) & Cross-Departmental Precedence (`5..35`)** — lower-tier packs (`department` `30`, `squad` `50`) never weaken or contradict higher-authority invariants (`domain-policy` `5`, `corporate` `10`); Legal/Compliance (`5..15`) > Finance/Supply (`20..25`) > Brand/Design (`30`) > Growth/Marketing (`35`).
- [ ] **2. Single Source of Truth (SSoT) Ledgers & Quantitative Precision** — every financial, operational, pricing, or SLA figure resides in ONE canonical ledger table under `corporate/` or `docs/` with explicit ISO 4217 currency and SI/time units; downstream docs link to the ledger instead of duplicating numbers in prose.
- [ ] **3. Traceable Artifact & Ledger IDs (`[DEPT]-[TYPE]-[YYYY]-[NNN]`)** — every normative policy, contract, pricing table, and sign-off gate carries a unique stable identifier.
- [ ] **4. Three-Part Functional Verification Structure** — every normative document in `corporate/**/*.md`, `templates/**/rules/*.md`, and `docs/**/*.md` contains: (1) `# Scope & Surface Target`, (2) `# Normative Invariants`, and (3) `# Verification & Sign-Off Gates` (with `- [ ]` checklists).
- [ ] **5. IP & Confidentiality Firewall & Crisis Escalation SLAs (`P0/P1/P2`)** — zero restricted formulas, supplier margins, or internal codenames leaked into public/external surfaces; crisis response playbooks define explicit `P0`/`P1`/`P2` SLAs and named owner roles.
- [ ] **6. Cross-Surface Cascade & Modularity (`< 465` Lines)** — changes in `corporate/` cascade across `surfaces/web/`, `surfaces/forms/`, and `surfaces/print/`, and every `.md` file stays strictly `< 465` lines (`make diff` reports zero drift).

---

## Rules

1. **Read the relevant rule files first** — always re-read project rules before auditing
2. **Report, don't fix** — `/review` is read-only. Capture findings, present recommendations
3. **Capture to BACKLOG.md** — if fixes are non-trivial, add items there
4. **Prioritize findings** — ❌ Critical (breaks rules) > ⚠️ Warning (should fix) > 💡 Suggestion
5. **Link evidence** — include file paths and line numbers for every finding
