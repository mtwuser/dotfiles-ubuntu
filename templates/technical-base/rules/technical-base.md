---
trigger: always_on
description: Universal software engineering, 1:1:1 traceability, refactoring, and 100% AAA testing rules for technical workspaces
---
# Technical Engineering, Refactoring & Testing Baseline (`technical-base`)

> Universal, stack-general software engineering, refactoring, and automated testing rules for ANY technical repository. Layers cleanly on top of `human-core` (via `<workspace>/.agents/rules/technical-base.md` or globally via `layer-config.sh set-global-profile technical`).

---

## Software Engineering & Code Integrity

- **Description**: Strict typing, `1:1:1` Human-Agent traceability, generated code verification, and diagnostic sweeps
- **Applies**: All software engineering, scripting, and technical repositories

1. **Utility Function & Pattern Reuse Gate**: Search the project (`grep` or semantic search) before writing helpers; import and reuse.
2. **Strict Linter, Compiler & Typing Integrity**: Zero compiler, type-checker, or linter (`ruff`/`mypy --strict`, `tsc --noEmit`, `cargo clippy`, `shellcheck`) warnings/errors. Prefer `unknown`/`Protocol`/`interface` over `Any`/`any`.
3. **`1:1:1` Human-AI-Technology Symbiosis (`Spec <-> Source <-> Test`)**: Executable modules must declare `Specification: docs/architecture/<spec>.md`, specs (`< 465` lines) must maintain a `1:1:1` table linking sources, `1:1` unit suites (`Test<Module>`), and invariants, and human guides (`docs/guides/`) must align verbatim with CLI/E2E workflows.
4. **Generated Output & Package-Marker Purity**: Verify all `import` packages exist, generated files pass linters, zero ghost placeholders (`my_app`), and package markers remain side-effect-free (in Python, `src/**/__init__.py` and `tests/**/__init__.py` MUST remain `0 bytes`).
5. **Pre-Debug Diagnostic Sweep**: Run `make doctor` / `make verify` before blind-debugging, and crystallize repeated checks into `Makefile` targets.

---

## Refactoring & Code Decommissioning

- **Description**: Rules for moving, renaming, extracting, restructuring, and decommissioning code (`skills/refactoring/SKILL.md`)
- **Applies**: All source code files

1. **Behavioral Invariant & Atomic `1:1:1` Test/Spec Alignment**: When splitting modules, all tests pass with identical results, test count never decreases, coverage stays 100%, and `1:1` unit tests (AAA comments) and `docs/architecture/` tables are aligned `1:1:1` in the SAME iteration.
2. **Zero-Residue & Rename Urgency**: When `A` is replaced by `B`, remove `A` completely in the same changeset (zero `OldName = NewName` aliases, `@deprecated` classes, or re-export shims). Rename symbols moved across modules when context changes.
3. **Code & Feature Decommissioning (3-Step Test Pruning Audit & Zero-Literal Leak Gate)**: When deleting a module/symbol or retiring internal names: (a) **`1:1` File Purge** (delete orphan unit test files); (b) **Symbol & Fixture Purge** (grep `tests/` for removed symbols/mocks); (c) **Default-Parameter Sensitivity** (test non-default parameter values); (d) **Zero-Literal Exclusion** (never embed private downstream identifiers in public tests/scripts; use structural regexes or dynamic discovery).

---

## Testing & `1:1:1` Human-Agent Comprehension (Universal)

- **Description**: Self-documenting `1:1:1` test architecture, coverage gates, and quality invariants (`skills/testing/SKILL.md`)
- **Applies**: All test files

1. **Human-Agent `1:1:1` Comprehension & AAA Pattern**: Encapsulate each `1:1` test file in **one** suite/class (`Test<Module>`) linked to `Specification: docs/architecture/<spec>.md`. Pair natural-language names (`test_<subject>_<scenario>_<expected>`) with a **1-line invariant docstring** and explicit `# Arrange`, `# Act`, `# Assert` comments (never merged) using DAMP literal values.
2. **Constructor Injection & Runtime Seam Patching**: Inject spec-constrained mocks/fakes in constructors, patch at the runtime consumer lookup seam, and never use argument-ignoring boundary/subprocess stubs.
3. **100% Isolated Unit Coverage, Boundary Cut-Points (`N` vs `N ± 1`), Speed & Zero Deprecations**: Maintain 100% statement/branch coverage in isolated unit runs, assert exact boundary cut-points (`N` vs `N ± 1`), `< 1s` per unit test, and 0 deprecation warnings.
4. **Anti-Characterization, Bipolar Guards & Scope**: Never lock in broken production behavior; cross-check caller/API/UI contracts and fix bugs first. Verify guards on **both poles** (negative first, positive second) across all channels, and test executable logic (`1:1`) plus public contract defaults, never language/framework axiomatics.
