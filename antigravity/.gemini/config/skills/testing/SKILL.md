---
name: testing
description: "Use when writing new tests, auditing test suites for quality, or consolidating tests during refactors. Covers AAA pattern, mock strategies, naming conventions, and coverage audits."
---

# How to Write and Audit Tests

## Part 1 — Writing Tests

### Test Writing Standards (AAA / DAMP)

All tests follow the **AAA pattern**:
1. **Arrange** (`# Arrange`) — set up state and mocks
2. **Act** (`# Act`) — execute the single action
3. **Assert** (`# Assert`) — verify the result

**Explicit AAA comment separation**: Always write `# Arrange`, `# Act`, and `# Assert` as **three separate comments** in every test method. Never combine them into `# Arrange & Act` or `# Act & Assert` (which violates automated test linters such as `check_tests`).
**DAMP over DRY**: Each test should be readable top-to-bottom. Use literal values; do not use computed expectations.
Every test class and method **MUST** have a docstring explaining _what_ it's testing and _why_.

### Service Constructor Rule — CRITICAL

> **Every service constructor MUST inject mocked dependencies unless the test exercises that dependency.**

This applies to **all** test tiers. Services often create other services in `__init__`. Bare `MyService()` instantiates the entire dependency tree with real imports — this is the #1 cause of slow tests.

```
# ❌ WRONG — ExternalService() imports heavy dependencies (~20s)
factory = FactoryService()

# ✅ RIGHT — Inject mock, no real imports
factory = FactoryService(external_service=mock())
```

**Self-check**: Does the constructor create other objects? If yes → mock or inject them.

### Patch Targets & Boundary Mock Verification
- Patch where the object is **looked up at runtime**. When a module uses `from source import func`, patch at `consumer.func` (the consumer holds its own reference). When it uses `import source` and calls `source.func`, patch at `source.func`.
- When code moves between modules, ALL patch targets in tests must be updated.
- **No Blind Boundary/Subprocess Mocks (`lambda *_a, **_k`)**: Never stub `subprocess.run`, HTTP clients, or external I/O boundaries with argument-ignoring lambdas (`lambda *_a, **_k: fake_proc`). Always capture and assert the invoked command/arguments (`mock_run.call_args`, `assert_called_once_with`) so corrupted CLI flags or missing `--no-fix` / `-x` arguments fail the unit test immediately.

### Test Naming Convention & Human-Agent `1:1:1` Comprehension Symbiosis

Test files: `test_{source_file}.py` (or `<source>.test.ts`, `<source>_test.go`, `<Source>Test.java` for your stack).
Test suites/classes: `Test{SourceClassName}` — **ONE** suite/class per test file (`0` top-level `def test_*` functions in class-based suites). NEVER append suffixes like `Coverage`, `Expanded`, `Extended`.
Test methods: `test_<subject>_<scenario>_<expected>`.

Every `1:1:1` unit test must serve **both** the **Human** (who reads the `pytest -v` / test runner output or `docs/architecture/` spec table in natural language without opening the source file) and the **Agent** (which parses AST/symbols to map invariants to lines/branches):
1. **Spec Layer (`docs/architecture/<spec>.md`)**: Maps `Source Module` $\leftrightarrow$ `1:1 Unit Test File (TestClass)` $\leftrightarrow$ `Verified Functional & Security Invariants`.
2. **Suite/Class Layer (`class Test<Module>`)**: Declares a module-level docstring with `Specification: docs/architecture/<spec>.md` and encapsulates all tests for that module in one class.
3. **Method Layer (`test_<subject>_<scenario>_<expected>`)**:
   - **Natural-Language Behavioral Name**: Reads as an executable sentence (`subject` + `condition/scenario` + `expected outcome`).
   - **1-Line Domain Invariant Docstring**: States *why* the invariant exists (not just *what* function is called), eliminating the need for explanatory inline prose comments inside the test body.
   - **AAA Body (`# Arrange`, `# Act`, `# Assert`)**: Uses DAMP literal values and exact boundary cut-points (`N` vs `N ± 1`).

### Pre-Edit Reading Priority & 3-Tier Case-Deduction Matrix (`E2E -> Imp -> Unit`)

Before modifying any production module or rule, read the `1:1:1` triad in strict descending radius of impact so implementation changes never break outbound cross-perspective contracts:
1. **Priority 1 — Human Guides & Normative Spec (`docs/guides/` $\rightarrow$ `docs/architecture/<spec>.md`)**: Understand the *WHAT* and *WHY* (human persona journeys, normative invariants, and the `1:1:1` traceability table).
2. **Priority 2 — Self-Documenting Test Hierarchy (`tests/e2e/` $\rightarrow$ `tests/imp/` $\rightarrow$ `tests/unit/`)**: Read the `Test<Module>` suites, natural-language method names, and 1-line invariant docstrings from outermost workflow (`E2E`) to innermost unit (`Unit`) *before* reading the code.
3. **Priority 3 — Source Implementation (`src/` / `scripts/`)**: Read and modify the *HOW* with all outbound constraints and edge cases already loaded in context.

Conceptualize and deduce test cases across the 3 tiers without overlapping responsibilities:

| Test Tier | Conceptual Focus | Systematic Case-Deduction Target |
| :--- | :--- | :--- |
| **`tests/e2e/` (Human Persona & Vertical Journeys)** | Complete multi-step human workflows from public entrypoint to final state. | **Cross-Perspective / Outbound Cases**: Verify that tightening a rule or state transition in Step A does not restrict a valid downstream workflow in Step B. |
| **`tests/imp/` (Cross-Dependency, Boundary I/O & Parity)** | Real inter-component contracts (CLI flags/exit codes, stdio/IPC/HTTP protocols, filesystem permissions, and `Spec <-> Code <-> Doc` parity). | **Integration & Drift Cases**: Verify parser flags match guides/Makefiles, read-only boundaries (`$HOME` vs workspace), and cross-surface synchronization. |
| **`tests/unit/` (`1:1` Algorithmic Exhaustiveness — 4 Quadrants)** | Isolated single-module logic (`Test<Module>`, `100%` isolated branch coverage). | Deduce all **4 Quadrants**: (1) *Nominal Happy Path*, (2) *Exact Boundary Cut-Points (`N` vs `N ± 1`)*, (3) *Bipolar Security/Guard Poles (`Negative -> Positive`)*, and (4) *Outbound/Hostile Environment Failures* (malformed input, missing files, permission errors). |

### Anti-Characterization Trap & Bipolar Guard Verification — CRITICAL

When adding tests to close coverage gaps or testing security/lifecycle guards:
1. **Cross-check the caller/API/UI contract**: Before writing a controller, router, or service test, check the caller contract (API schema, CLI contract, UI template, and project rules). If an endpoint or handler violates its declared contract (e.g., returning `200 {"error": ...}` instead of an error status or wrong content type), **fix the production code first** — never write a test that locks in the bug.
2. **Never mutate existing test scenarios for branch coverage**: If a loop branch requires multiple items to execute, add a new test method (`test_<method>_second_item`) instead of altering an existing single-item test.
3. **Bipolar Guard Verification (Negative-First, Positive-Second)**: Any test for a security gate, lifecycle hook (`PreToolUse`, `PostToolUse`, `Stop`), schema validator, or drift auditor that only asserts the passing ("allow"/"stop") state is vulnerable to silent early-return/short-circuit bugs (e.g., mismatched JSON keys returning a default pass). Every guard test MUST execute **both poles**:
   - **Negative Pole First**: Feed a deliberate violation (failing test, syntax error, forbidden command, expired token) and assert the guard blocks or flags it (`"deny"`, `"continue"`, or specific error code).
   - **Positive Pole Second**: Fix the violation and assert the guard transitions cleanly to the passing state.
4. **Cross-Channel Guard Equivalence (Structured Tools vs. Shell/Interpreter Channels)**: Whenever a security or governance guard protects a **resource** (e.g., protected file paths like `alembic/versions/*.py` or `0-byte` `__init__.py`), never scope the guard or its test matrix solely to structured file-editing tools (`write_file`, `edit_file`). Verify the orthogonal matrix `(Protected Resource Invariant) × (Execution Channel)` across structured tools, shell redirections/heredocs (`>`, `>>`, `<<EOF`), stream/file utilities (`tee`, `cp`, `mv`, `dd`), unwrapped subshells (`sh/bash -c`), and inline interpreters (`python -c`).

---

## Part 2 — Auditing and Consolidating Tests

> **When to use**: Use this skill when asked to review, align, or consolidate tests for a module, or when migrating tests during a code refactor.

### Test Consolidation Checklist

When asked to consolidate tests, follow these phases strictly:

**Phase 1 — Scope (Know what to ignore)**

// delegate: flash
1. **Identify excluded directories**: Framework-generated boilerplate (admin, config, migrations) and ops-only management commands. Skip testing these entirely.
2. **Identify testable base files**: All logic files NOT in the standard coverage omit list.

**Phase 2 — Classification Audit**
Find and fix misclassifications:
3. **Database access in unit tier**: If a test uses real database calls, migrate it to an integration tier.
4. **Mocking in integration tier**: If an integration test uses `@patch` to mock database objects, it is a disguised unit test. Convert it or delete it if redundant.

**Phase 3 — Structural Verification**

// delegate: flash
5. **File mapping (logic files only)**: Ensure every source file with **executable logic** has a corresponding test file. Purely declarative schema/model files without custom methods or validators and trivial 1-line DI singleton getters already covered by router/controller tests should NOT have artificial test files that only test framework/ORM/Pydantic defaults.
6. **One Class per File**: All test methods within the file MUST reside under a single class named `Test{SourceClassName}`. Fragmented mini-classes are strictly forbidden.
7. **File placement**: Test content matches the file name (no view tests living inside model test files).
8. **No redundancy**: Unit + integration should together cover 100%. No single line should be redundantly tested in both tiers if a mock solves it in unit.

**Phase 4 — Execution & Verification**
9. Run full test suite → 0 failures, 100% coverage maintained.
10. Ensure performance metrics stay fast (e.g., `< 1s` per unit test).

**Phase 5 — Diagnosing False-Positive Coverage & Drops**
11. **The 100% Coverage Illusion**: If the suite shows 100% coverage but contains failing tests, it usually means a unit test is correctly covering the logic, while an outdated integration test executes the same path and fails. **Solution**: Purge the redundant integration test.
12. **Transitive Coverage Drops & Isolated Unit Gate**: If deleting an integration/E2E test or CLI `--self-test` drops coverage in a module, it means the higher-tier test was masking incomplete `1:1` unit tests (often via shallow `len(text) > 0` smoke loops without schema verification). **Solution**: Enforce 100% coverage on `tests/unit/` in strict isolation (`pytest tests/unit/ --cov=<pkg> --cov-fail-under=100`) before running `imp`/`e2e`, and assert full response contracts for every cataloged resource/endpoint.

### Refactoring Tests (File Migrations)

When moving source files between modules, **tests MUST be migrated in the same changeset.** A test count decrease after a refactor implies orphaned tests.

#### Unit Tests (Low Risk)
1. Move the test file alongside the source file.
2. Update all import paths inside the test file to point to the new source module.
3. Update all `@patch` targets to reflect the new module path.

#### Integration Tests (Higher Risk)
1. Search for ALL integration test files referencing the moved module.
2. Update all imports and patch targets in affected test files.
3. If an integration test now covers lines that could easily be covered by unit mocks, convert it to a unit test.

#### Post-Refactor Verification
1. **Pure Refactor**: Test count must equal or exceed the pre-refactor count.
2. **Feature Decommissioning**: When production modules, classes, or endpoints are intentionally deleted, purge their corresponding unit test files (`orphan-test-file` gate) and obsolete test methods in the same changeset (`skills/refactoring/SKILL.md` §Code Decommissioning).
3. **Boundary Cut-Point & Default-Parameter Sensitivity (Zero-Dependency Mutation Hardening)**:
   - **Boundary Cut-Point Invariant (`N` vs `N ± 1`)**: Branch coverage alone only checks one `True` and one `False` sample (allowing off-by-one `<` vs `<=` and `>` vs `>=` mutants to survive). Whenever production logic compares against a numeric threshold (line caps, byte/token budgets, TTLs, capacity limits, hop counts, pagination bounds), unit tests MUST assert the exact cut-point pair (`threshold` and `threshold ± 1`).
   - **Default-Parameter Sensitivity**: Never rely on default parameter values alone to satisfy 100% line/branch coverage. When a function computes a hash, query filter, or state transition over fields with defaults, include explicit tests proving that mutating each field changes the output.
   - **AST Anti-Deception Invariants**: Enforce zero `# pragma: no cover` in production code, zero `pytest.raises(...)` without an explicit `match=` pattern, and zero argument-ignoring `subprocess.run` lambdas across the test suite.
4. Compare coverage before and after. Any new uncovered lines correlate to a missed test migration.
5. Verify no orphaned test files exist. Every unit test file must map to an actual current source file.
