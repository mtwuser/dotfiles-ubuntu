---
trigger: always_on
description: Universal software engineering, 1:1:1 traceability, refactoring, and 100% AAA testing rules for technical workspaces
---
# Technical Engineering, Refactoring & Testing Baseline (`technical-base`)

> Universal software engineering, refactoring, and automated testing rules for codebases and technical workspaces. Layers cleanly on top of `human-core` (via `<workspace>/.agents/rules/technical-base.md` or globally via `layer-config.sh set-global-profile technical`).

---

## Software Engineering & Code Integrity

- **Description**: Strict typing, `1:1:1` traceability, generated code verification, and diagnostic sweeps
- **Applies**: All software engineering, scripting, and technical repositories

1. **Utility Function & Pattern Reuse Gate**: Search the project (`grep` or semantic search) before writing helpers; import and reuse (moving to a shared module first if needed).
2. **Strict Linter, Compiler & Typing Integrity**: Zero compilation or linter (`ruff`, `mypy --strict`, `shellcheck`) warnings/errors. Prefer `unknown`/`Protocol` over `Any`.
3. **`1:1:1` Source $\leftrightarrow$ Unit Test $\leftrightarrow$ Specification Traceability**: Executable modules must declare `Specification: docs/architecture/<spec>.md`, and architecture specs (`< 465` lines) must maintain a `1:1:1` table linking sources, unit tests (`tests/unit/**/test_<module>.py`), and specs.
4. **Generated Output Verification & Package Marker Purity**: Verify all `import` packages exist, generated files pass linters, zero ghost placeholders (`my_app`), and **Package marker purity (`0-byte` `__init__.py`)** — Python consumer `src/**/__init__.py` and `tests/**/__init__.py` files MUST remain `0 bytes`.
5. **Pre-Debug Diagnostic Sweep**: Run `make doctor` / `make verify` before blind-debugging, and crystallize repeated checks into `Makefile` targets.

---

## Refactoring & Code Decommissioning

- **Description**: Rules for moving, renaming, extracting, restructuring, and decommissioning code (`skills/refactoring/SKILL.md`)
- **Applies**: All source code files

1. **Behavioral Invariant & Atomic `1:1:1` Test/Spec Alignment**: When splitting modules, all tests pass with identical results, test count never decreases, coverage stays 100%, and unit tests (`tests/unit/**/test_<module>.py`, AAA comments) and `docs/architecture/` tables are aligned `1:1:1` in the SAME iteration.
2. **Zero-Residue & Rename Urgency**: When `A` is replaced by `B`, remove `A` completely in the same changeset (zero `OldName = NewName` aliases, `@deprecated` classes, or re-export shims). Rename symbols moved across modules when context changes.
3. **Code & Feature Decommissioning (3-Step Test Pruning Audit & Zero-Literal Leak Gate)**: When deleting a module/symbol or retiring internal names: (a) **`1:1` File Purge** — delete orphan `test_<module>.py`; (b) **Symbol & Fixture Purge** — grep `tests/` for removed symbols/mocks; (c) **Default-Parameter Sensitivity** — test non-default parameter values; (d) **Dynamic Agnosticism Checks** — never embed private downstream repo names (plain or hex-escaped) in public tests; discover local sibling workspaces dynamically (`Path.home() / "Projects"`).

---

## Testing (Universal)

- **Description**: Test patterns, coverage gates, and quality invariants (`skills/testing/SKILL.md`)
- **Applies**: All test files

1. **AAA Pattern — MANDATORY**: Every test method MUST contain three explicit comments: `# Arrange`, `# Act`, and `# Assert` (never merged). Prefer DAMP over DRY with literal expected values.
2. **Service Constructor & Patch Targets**: Inject mocked dependencies (`MagicMock(spec=...)` / `AsyncMock(spec=...)`) in unit test constructors, and patch where the object is looked up at runtime (`consumer.func`).
3. **100% Coverage, Boundary Cut-Point, Speed & Deprecation-Free Gates**: Maintain 100% statement and branch coverage, assert exact boundary cut-points (`N` vs `N ± 1`), `< 1s` per unit test, and 0 `DeprecationWarning` (`-W error::DeprecationWarning`).
4. **Anti-Characterization & Scope**: Never lock in broken production behavior; cross-check caller/template contracts (`hx-get`/`hx-post`/`hx-target`) and fix bugs first. Test executable logic (`1:1` mapping) and public contract defaults (schemas, `BaseSettings`, error codes, enums), never language axiomatics (`isinstance(StrEnum, str)`, literal constants).
