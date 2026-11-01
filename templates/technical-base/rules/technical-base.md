---
trigger: always_on
description: Universal software engineering, 1:1:1 traceability, refactoring, and 100% AAA testing rules for technical workspaces
---
# Technical Engineering, Refactoring & Testing Baseline (`technical-base`)

> Universal, stack-general software engineering, refactoring, and testing rules for ANY technical repository. Layers on top of `human-core` (`.agents/rules/technical-base.md` or `layer-config.sh set-global-profile technical`).

---

## Software Engineering & Code Integrity

- **Description**: Strict typing, `1:1:1` traceability, generated code verification, and diagnostic sweeps
- **Applies**: All software engineering, scripting, and technical repositories

1. **Utility, Stdlib & Import Gate**: Search (`grep`/semantic) before writing helpers, use floor-version C-backed stdlib symbols (`hashlib.file_digest`, `stat.S_IWUSR`, `HTTPStatus`), and use explicit absolute imports (zero `import ... as c` aliases).
2. **Strict Linter, Compiler & Typing Integrity**: Zero compiler, type-checker, or linter (`ruff`/`mypy --strict`, `tsc --noEmit`, `cargo clippy`, `shellcheck`) warnings/errors. Prefer `unknown`/`Protocol`/`interface` over `Any`/`any`.
3. **`1:1:1` Symbiosis & Reading Priority (`1. Guides/Specs -> 2. Tests [E2E -> Imp -> Unit] -> 3. Code`)**: Read `docs/{guides,architecture}/` first, `tests/{e2e,imp,unit}/` (`Test<Module>`) second, and code last. Modules declare `Specification: docs/architecture/<spec>.md` and specs (`< 465` lines) keep a `1:1:1` table.
4. **Generated Output & Package-Marker Purity**: Verify `import` packages exist, generated files pass linters, zero placeholders (`my_app`), and `src/**/__init__.py` / `tests/**/__init__.py` remain `0 bytes`.
5. **Pre-Debug Diagnostic Sweep**: Run `make doctor` / `make verify` before blind-debugging; crystallize repeated checks into `Makefile` targets.
6. **Domain Cut-Points & Anti-Magic-Number Hygiene**: Never embed magic numbers, raw modes (`0o644`), arbitrary slices (`[:35]`), or tuple sub-slices (`SURFACES[:5]`) in logic. Use stdlib symbols first and named constants (`MAX_*`, `MIN_*`, `DEFAULT_*`, `VALID_*`) second for `N` vs `N ± 1` clarity.

---

## Refactoring & Code Decommissioning

- **Description**: Rules for moving, renaming, extracting, and decommissioning code (`skills/refactoring/SKILL.md`)
- **Applies**: All source code files

1. **Behavioral Invariant & Atomic `1:1:1` Alignment**: When splitting modules, tests pass identically, test count never decreases, coverage stays 100%, and `1:1:1` tests/specs align in the SAME iteration.
2. **Zero-Residue, Age Review & File-Prefix Naming**: Remove replaced symbols atomically (zero aliases/shims). On every edit/feature, review older (`> 90d`) or compressed code: if aligned, consolidate/automate; if drifted, escalate (`Inline -> Function -> Class -> Protocol/Catalog -> Module`), name files by role (`tools_*`, `*_engine`, `NN_*`, `test_*`), and log in `BACKLOG.md`.
3. **Code Decommissioning (3-Step Test Pruning & Zero-Literal Leak Gate)**: When deleting a module/symbol: (a) **`1:1` File Purge** (delete orphan unit tests); (b) **Symbol & Fixture Purge** (grep `tests/` for removed symbols/mocks); (c) **Default-Parameter Sensitivity** (test non-defaults); (d) **Zero-Literal Exclusion** (regexes/dynamic discovery, never private literals).

---

## Testing & `1:1:1` Human-Agent Comprehension (Universal)

- **Description**: Self-documenting `1:1:1` test architecture, bidirectional 3-tier flow, and coverage gates (`skills/testing/SKILL.md`)
- **Applies**: All test files

1. **Human-Agent `1:1:1` Comprehension, Bidirectional 3-Tier Flow & AAA**: Deduce/validate **Top-Down (`E2E -> Imp -> Unit`)**; author/execute **Bottom-Up (`Unit -> Imp -> E2E`)**. Model `E2E` as persona journeys, `Imp` (*Implementation* boundary/parity contracts; never `int`), and `Unit` (`1` `Test<Module>` class/file linked to `Specification: docs/architecture/<spec>.md`) across 4 quadrants (nominal, `N` vs `N ± 1` boundaries, bipolar guards, outbound failures). Pair `test_<subject>_<scenario>_<expected>` names with a **1-line invariant docstring** and `# Arrange`, `# Act`, `# Assert` comments.
2. **Constructor Injection & Runtime Seam Patching**: Inject spec-constrained mocks/fakes in constructors, patch at the runtime consumer lookup seam, and never use argument-ignoring boundary/subprocess stubs.
3. **100% Isolated Unit Coverage (`Unit -> Imp -> E2E`), Cut-Points (`N` vs `N ± 1`) & Speed**: Enforce 100% branch coverage on isolated `tests/unit/` first (`< 1s`/test, 0 deprecations) before `imp`/`e2e`, asserting exact `N` vs `N ± 1` cut-points.
4. **Anti-Characterization, Bipolar Guards & Scope**: Never lock in broken behavior; cross-check contracts and fix bugs first. Verify guards on **both poles** (negative first, positive second) across all channels, and test executable logic (`1:1`) plus public defaults, never framework axiomatics.
