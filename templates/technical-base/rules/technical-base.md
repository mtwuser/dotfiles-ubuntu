# Technical Engineering, Refactoring & Testing Baseline (`technical-base`)

> Universal software engineering, refactoring, and automated testing rules for codebases and technical workspaces. Layers cleanly on top of `human-core` (via `<workspace>/.agents/rules/technical-base.md` or globally via `layer-config.sh set-global-profile technical`).

---

## Software Engineering & Code Integrity

- **Description**: Strict typing, `1:1:1` traceability, generated code verification, and diagnostic sweeps
- **Applies**: All software engineering, scripting, and technical repositories

1. **Utility Function & Pattern Reuse Gate**: Search the project (`grep` or semantic search) for similar signatures before writing helpers. If found $\rightarrow$ import and reuse (moving to a shared module first if needed).
2. **Strict Linter, Compiler & Typing Integrity**: Zero compilation or linter (`ruff`, `mypy --strict`, `shellcheck`) warnings/errors. Prefer `unknown`/`Protocol` over `Any`.
3. **`1:1:1` Source $\leftrightarrow$ Unit Test $\leftrightarrow$ Specification Traceability**: Executable modules must declare `Specification: docs/architecture/<spec>.md` in their docstring, and architecture specs (`< 465` lines) must maintain a `1:1:1` traceability table linking sources, unit tests (`tests/unit/**/test_<module>.py`), and specs.
4. **Generated Output Verification & Package Marker Purity**: After scaffolding, verify: (a) all `import` packages exist in dependencies; (b) generated files pass linters/type-checkers; (c) zero ghost placeholders (`my_app`); (d) **Package marker purity (`0-byte` `__init__.py`)** — Python consumer `src/**/__init__.py` and `tests/**/__init__.py` files MUST remain completely empty (`0 bytes`).
5. **Pre-Debug Diagnostic Sweep**: Run the project's diagnostic command (`make doctor`, `make verify`) before blind-debugging, and crystallize repeated checks into `Makefile` targets.

---

## Refactoring & Code Decommissioning

- **Description**: Rules for moving, renaming, extracting, restructuring, and decommissioning code (`skills/refactoring/SKILL.md`)
- **Applies**: All source code files

1. **Behavioral Invariant & Atomic `1:1:1` Test/Spec Alignment**: When splitting or restructuring modules, all tests pass with identical results, test count never decreases, coverage remains 100%, and unit tests (`tests/unit/**/test_<module>.py`, `Test*` class per file, AAA comments) and `docs/architecture/` traceability tables are aligned `1:1:1` in the SAME iteration.
2. **Zero-Residue**: When `A` is replaced by `B`, `A` must be fully removed in the same changeset. Backward-compatibility aliases (`OldName = NewName`), `@deprecated` classes, and re-export shims are forbidden.
3. **Rename Urgency**: When moving `A` from module `X` to module `Y`, rename `A` in the same changeset if its name no longer reflects `Y`'s context.
4. **Code & Feature Decommissioning (3-Step Test Pruning Audit & Zero-Literal Leak Gate)**: When deleting a module, class, method, or retiring internal names, execute in the same changeset: (a) **`1:1` File Purge** — delete orphan `test_<module>.py`; (b) **Symbol & Fixture Purge** — grep `tests/` for removed symbols/mocks; (c) **Default-Parameter Sensitivity** — write explicit tests proving non-default parameter values alter output; (d) **Dynamic Agnosticism Checks** — never embed private downstream repo names (plain or hex-escaped) in public parity tests; discover local sibling workspaces dynamically (`Path.home() / "Projects"`).

---

## Testing (Universal)

- **Description**: Test patterns, coverage gates, and quality invariants (`skills/testing/SKILL.md`)
- **Applies**: All test files

1. **AAA Pattern — MANDATORY**: Every test method MUST contain three separate, explicit comments: `# Arrange`, `# Act`, and `# Assert` (never merged). Prefer DAMP over DRY with literal expected values.
2. **Service Constructor Rule — CRITICAL**: Inject mocked dependencies (`MagicMock(spec=...)` / `AsyncMock(spec=...)`) in unit test service/use-case constructors unless exercising that dependency.
3. **Patch Targets**: Patch where the object is looked up at runtime (`consumer.func` when imported via `from source import func`).
4. **100% Coverage, Boundary Cut-Point, Speed & Deprecation-Free Gates**: Maintain 100% statement and branch coverage, assert exact boundary cut-points (`N` vs `N ± 1`), `< 1s` per unit test, and 0 `DeprecationWarning` (`-W error::DeprecationWarning`).
5. **Anti-Characterization Trap**: Never blindly lock in broken production behavior when closing coverage gaps; cross-check caller/template contracts (`hx-get`/`hx-post`/`hx-target`) and fix production bugs first.
6. **What NOT to Test**: Test executable logic (`1:1` mapping), never language/framework axiomatics (`isinstance(StrEnum, str)`, `issubclass`, literal constants). DO test public contract defaults (manifest schemas, `BaseSettings`, exception `error_code`/`http_status`, protocol enums).
