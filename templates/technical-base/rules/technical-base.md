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

1. **Utility & Pattern Reuse Gate**: Search (`grep` or semantic search) before writing helpers; import and reuse.
2. **Strict Linter, Compiler & Typing Integrity**: Zero compiler, type-checker, or linter (`ruff`/`mypy --strict`, `tsc --noEmit`, `cargo clippy`, `shellcheck`) warnings/errors. Prefer `unknown`/`Protocol`/`interface` over `Any`/`any`.
3. **`1:1:1` Symbiosis & Reading Priority (`1. Guides/Specs -> 2. Tests [E2E -> Imp -> Unit] -> 3. Code`)**: Read `docs/guides/` and `docs/architecture/<spec>.md` first, then `tests/{e2e,imp,unit}/` (`Test<Module>`), and code last. Executable modules declare `Specification: docs/architecture/<spec>.md`, specs (`< 465` lines) maintain a `1:1:1` table, and changes must not restrict valid outbound workflows.
4. **Generated Output & Package-Marker Purity**: Verify all `import` packages exist, generated files pass linters, zero ghost placeholders (`my_app`), and package markers stay side-effect-free (`src/**/__init__.py` and `tests/**/__init__.py` MUST remain `0 bytes`).
5. **Pre-Debug Diagnostic Sweep**: Run `make doctor` / `make verify` before blind-debugging; crystallize repeated checks into `Makefile` targets.

---

## Refactoring & Code Decommissioning

- **Description**: Rules for moving, renaming, extracting, restructuring, and decommissioning code (`skills/refactoring/SKILL.md`)
- **Applies**: All source code files

1. **Behavioral Invariant & Atomic `1:1:1` Alignment**: When splitting modules, tests pass with identical results, test count never decreases, coverage stays 100%, and `1:1:1` tests/specs align in the SAME iteration.
2. **Zero-Residue & Rename Urgency**: When `A` is replaced by `B`, remove `A` completely in the same changeset (zero `OldName = NewName` aliases, `@deprecated` classes, or re-export shims). Rename symbols moved across modules when context changes.
3. **Code Decommissioning (3-Step Test Pruning & Zero-Literal Leak Gate)**: When deleting a module/symbol or retiring internal names: (a) **`1:1` File Purge** (delete orphan unit tests); (b) **Symbol & Fixture Purge** (grep `tests/` for removed symbols/mocks); (c) **Default-Parameter Sensitivity** (test non-default values); (d) **Zero-Literal Exclusion** (never embed private identifiers in tests/scripts; use regexes/dynamic discovery).

---

## Testing & `1:1:1` Human-Agent Comprehension (Universal)

- **Description**: Self-documenting `1:1:1` test architecture, 3-tier deduction, and coverage gates (`skills/testing/SKILL.md`)
- **Applies**: All test files

1. **Human-Agent `1:1:1` Comprehension, 3-Tier Deduction (`E2E -> Imp -> Unit`) & AAA**: Model `E2E` as human persona journeys, `Imp` as cross-dependency/parity contracts, and `Unit` (`1` `Test<Module>` class per file linked to `Specification: docs/architecture/<spec>.md`) via 4 quadrants (nominal, `N` vs `N ± 1` boundaries, bipolar guards, outbound failures). Pair `test_<subject>_<scenario>_<expected>` names with a **1-line invariant docstring** and separate `# Arrange`, `# Act`, `# Assert` comments.
2. **Constructor Injection & Runtime Seam Patching**: Inject spec-constrained mocks/fakes in constructors, patch at the runtime consumer lookup seam, and never use argument-ignoring boundary/subprocess stubs.
3. **100% Isolated Unit Coverage, Boundary Cut-Points (`N` vs `N ± 1`), Speed & Zero Deprecations**: Maintain 100% statement/branch coverage in isolated unit runs, assert exact boundary cut-points (`N` vs `N ± 1`), `< 1s` per unit test, and 0 deprecation warnings.
4. **Anti-Characterization, Bipolar Guards & Scope**: Never lock in broken production behavior; cross-check caller/API/UI contracts and fix bugs first. Verify guards on **both poles** (negative first, positive second) across all channels, and test executable logic (`1:1`) plus public defaults, never framework axiomatics.
