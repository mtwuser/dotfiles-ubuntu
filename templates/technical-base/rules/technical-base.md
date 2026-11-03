---
trigger: always_on
description: "Universal software engineering, 1:1:1 traceability, refactoring, and 100% AAA testing rules for technical workspaces"
---
# Technical Engineering, Refactoring & Testing Baseline (`technical-base`)

> Universal software engineering, refactoring, and testing rules (`.agents/rules/technical-base.md` or `layer-config.sh set-global-profile technical`).

---

## Software Engineering & Code Integrity

- **Description**: Strict typing, `1:1:1` traceability, generated code verification, and 5-link ripple sweeps
- **Applies**: All software engineering, scripting, and technical repositories

1. **Utility, Stdlib & Import Gate**: Search (`grep`/semantic) before writing helpers, use floor-version C-backed stdlib symbols (`hashlib.file_digest`, `stat.S_IWUSR`, `HTTPStatus`), and use explicit absolute imports (zero `import ... as c` aliases).
2. **Strict Linter, Compiler & Typing Integrity**: Zero compiler, type-checker, or linter (`ruff`/`mypy --strict`, `tsc --noEmit`, `cargo clippy`, `shellcheck`) warnings/errors. Prefer `unknown`/`Protocol`/`interface` over `Any`/`any`.
3. **`1:1:1` Symbiosis & Package-Marker Purity**: Read `docs/{guides,architecture}/` first, `tests/{e2e,imp,unit}/` (`Test<Module>`) second, and code last. Modules declare `Specification: docs/architecture/<spec>.md`, specs (`< 465` lines) keep a `1:1:1` table, and `src/**/__init__.py` / `tests/**/__init__.py` stay `0 bytes`.
4. **Constants, Cut-Points & Data Symmetry**: Zero magic numbers, raw modes (`0o644`), numeric schema IDs (`"1.2"`), raw slices (`[:24]`), or `.update()` packing. Use stdlib symbols, nominal constants (`*_CONTRACT_REV`, `MAX_*`, `MIN_*`, `DEFAULT_*`, `VALID_*`), `{...}` literals, boundary `.get()`, and internal `d["k"]`.

---

## Refactoring & Code Decommissioning

- **Description**: Rules for moving, renaming, extracting, and decommissioning code (`skills/refactoring/SKILL.md`)
- **Applies**: All source code files

1. **Behavioral Invariant & Atomic `1:1:1` Alignment**: When splitting modules, tests pass identically, test count never decreases, coverage stays 100%, and `1:1:1` tests/specs align in the SAME iteration.
2. **Age Review, 5-Stage Escalation & 3-Step Pruning**: Review older (`> 90d`) or compressed code: consolidate if aligned, or escalate (`Inline -> Function -> Class -> Protocol/Catalog -> Module`), name files by role (`tools_*`, `*_engine`, `NN_*`, `test_*`), and execute `[WIRE]` / `[CONSOLIDATE]` / `[PRUNE]` (`1:1` file/symbol purge, non-default tests, zero-literal exclusion).

---

## Testing & `1:1:1` Human-Agent Comprehension (Universal)

- **Description**: Self-documenting `1:1:1` test architecture, bidirectional 3-tier flow, and coverage gates (`skills/testing/SKILL.md`)
- **Applies**: All test files

1. **Human-Agent `1:1:1` Comprehension, Bidirectional 3-Tier Flow & AAA**: Deduce **Top-Down (`E2E -> Imp -> Unit`)**; author **Bottom-Up (`Unit -> Imp -> E2E`)**. Model `E2E` as persona journeys, `Imp` (*Implementation* contracts; never `int`), and `Unit` (`1` `Test<Module>` class/file linked to `Specification: docs/architecture/<spec>.md`) across 4 quadrants (nominal, `N` vs `N ± 1` boundaries, bipolar guards, outbound failures). Pair `test_<subject>_<scenario>_<expected>` names with a **1-line docstring** and `# Arrange`, `# Act`, `# Assert` comments.
2. **Constructor Injection & Runtime Seam Patching**: Inject spec-constrained mocks/fakes in constructors, patch at the consumer lookup seam, and never use argument-ignoring boundary/subprocess stubs.
3. **100% Isolated Unit Coverage (`Unit -> Imp -> E2E`), Cut-Points (`N` vs `N ± 1`) & Speed**: Enforce 100% branch coverage on isolated `tests/unit/` first (`< 1s`/test, 0 deprecations) before `imp`/`e2e`, asserting `N` vs `N ± 1` cut-points.
4. **Anti-Characterization, Bipolar Guards & Scope**: Fix bugs first; never lock in broken behavior. Verify guards on **both poles** (negative first, positive second), testing `1:1` logic + defaults, never framework axiomatics.
