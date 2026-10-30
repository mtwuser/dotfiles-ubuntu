# Antigravity Universal Rules

> These rules apply to ALL projects regardless of tech stack.

---

## Agent Behavior

- **Description**: Agent behavioral mandates, mindset, and strict execution rigor
- **Applies**: Always

### Agent Behavior Manifesto

This file governs the fundamental mindset and operating rigor of the AI Agent. These are absolute meta-cognitive mandates that must be verified mentally before writing any code or proposing solutions.

#### 1. Reusability First (Consistency)
> *"Preserve codebase consistency and maximize reuse before introducing new abstractions."*

**Mandate:** Before proposing a new implementation, function, UI component, or style, explicitly scan the workspace (`grep` or semantic search) for existing patterns. Do not build custom wrappers or components if a generic existing asset already fits.
- **Utility function gate:** Before writing ANY helper function (parsing, detection, formatting), search the project for functions with similar names or signatures. If found → import and reuse. If the existing version lives in the wrong module → move it to a shared location first, then import.

#### 2. Professional Robustness (No Shortcuts)
> *"Always choose the most robust, scalable, and professional implementation approach."*

**Mandate:** Reject the "easiest" fallback if a scalable, dynamic implementation is attainable. Code must be parameterized, strongly typed, and resilient to scale. Never sacrifice architectural integrity for a fast patch.
- **File Size & Pre-Growth Modularity Gate (`< 465` lines)**: Keep every source, test, and navigable `docs/**/*.md` file strictly `< 465` lines (target $\le 400$). If a new feature will push any file past `465` lines, proactively propose extracting cohesive modules, `1:1` test files, and modular `docs/architecture/` specs before or within the plan (mandatory structural hygiene, exempt from `§9.4` scope-creep restrictions).

#### 3. Strict Linter & Typing Integrity
> *"Zero compiler, type-checker, or linter errors."*

**Mandate:** No task is complete if compilations fail or linters complain. Respect strict typing (`unknown`/`Protocol` over `Any`). Never leave untraced typing issues, and resolve linter warnings during modifications.

#### 4. Absolute Test Inclusion
> *"Ship every code change with its associated tests while strictly honoring the testing strategy."*

**Mandate:** Code logic and tests are a single atomic entity. Never propose a code change without simultaneously addressing its test files. Unconditionally enforce the 100% coverage gate and native AAA pattern.

#### 5. Documentation Hierarchy & Discrepancy Scans
> *"Review technical specifications first and proactively detect discrepancies."*

**Mandate:** Approach `docs/` and architectural feature files as supreme law. When planning any component change, parse the relevant specs first. If the codebase has drifted or contradicts documentation, flag it as a P0 discrepancy and unify them immediately.
- **1:1:1 Source $\leftrightarrow$ Unit Test $\leftrightarrow$ Specification Traceability**: Executable modules must declare a `Specification: docs/architecture/<spec>.md` pointer in their module docstring, and navigable architecture specs (`< 465` lines) must maintain a `1:1:1` traceability table linking source modules, unit tests, and specifications.
- **Generation Rule:** When generating ANY template, scaffold, boilerplate, or canonical example, derive the output strictly from the corresponding specification in `docs/` or `ARCHITECTURE.md` — never from context memory: (1) Locate spec → (2) Extract layout/imports/conventions → (3) Instantiate spec → (4) Cross-verify diff.

#### 6. Continuous Consolidation
> *"Consolidate and complete documentation continuously over time."*

**Mandate:** Treat documentation as code. When finishing a roadmap phase, prune or archive completed roadmap files and enrich affected architecture/feature guides immediately.

#### 7. The Zero-Backward Law (Clean Cutovers)
> *"Never leave backward-compatibility shims or legacy fallbacks during refactors — always execute a clean cutover."*

**Mandate:** When refactoring or upgrading code, schemas, or declarative manifests (`schema_version`, JSON/YAML/TOML contracts), execute full surgical replacements. Never leave behind legacy polyfills, dummy aliases (`OldType = NewType`), re-export shims, `if legacy:` branches, multi-version schema fallbacks, or `@deprecated` markers. Hard-cut the implementation and all repository manifests/fixtures to the single canonical version universally across all callers.

#### 8. Mandatory Pre-Commit Hygiene Scan (Zero-Residue Enforcement)
> *"Never finish a task leaving behind script residue or broken side effects from tunnel vision. Always scan the environment."*

**Mandate:** BEFORE deciding an implementation is finished or delivering `git commit` blocks, pause and execute a holistic environment scan:
1. **Pesticide Scan**: Check for and delete any temporary scratchpad files generated during planning/execution.
2. **Side-Effect Coherence**: Verify that changed logic does not break global scripts (`build`, `reset`, `setup`, `test-all`).
3. **Commit Rigor**: Confirm the directory root is sterile before suggesting `git add`.
4. **Transversal Build Verification**: Run isolated tests and full lint/type checks to catch cascading issues.
5. **Multi-Repo Governance Parity**: When a task modifies multiple repositories (e.g., framework + validation verticals), verify `CHANGELOG.md`, `README.md` tree sync (§10), and the full test/lint battery in **every** modified repository individually.

#### 9. Exhaustive Implementation Planning (Anti-Myopia)
> *"Move deliberately rather than rushing: short verified steps backed by comprehensive cross-cutting plans."*

**Mandate:** Never sacrifice structural sanity for speed:
1. **Additive Plans**: `implementation_plan.md` must map transversal side-effects, dependencies, and legacy orphans across all affected files.
2. **No Phase Compression**: Never skip or compress a phase of an approved plan to "go faster".
3. **Execution Block**: Never execute modifying tools during Research and Propose; wait for explicit user approval.
4. **Zero Scope Creep ("While we're at it" edits are forbidden)**: Implement ONLY what the approved plan specifies. Capture adjacent observations in `BACKLOG.md` — never implement them in the current iteration.

#### 10. Documentation Coherence After Structural Changes
> *"When you move, rename, or delete a file, documentation must reflect current reality — not your memory of it."*

**Mandate:** When ANY file or directory is moved, renamed, created, or deleted, verify documentation coherence BEFORE completion:
1. **README Tree Sync**: Compare any README directory tree against `find` / `ls`.
2. **Documentation Index Sync**: Verify every link in documentation indexes points to an existing file (`test -f`).
3. **Cross-Reference Sweep**: Search ALL `.md` files (`grep -rn`) for references to old names/paths.
4. **No Orphaned Ghosts**: Zero references to deleted or moved locations may remain.

#### 11. Scaffolding-First Mandate (CLI over Manual)
> *"The project provides dedicated CLI scaffolding tools — use them."*

**Mandate:** Before manually creating project files, configuration, or boilerplate, check if the project provides CLI scaffolding tools (`osa init`, `osa context`, `osa scaffold`, `osa db`, `layer-config.sh`, etc.). Use the CLI tool exclusively unless no CLI covers the need, the CLI is broken (document in `BACKLOG.md`), or the user explicitly requests manual creation.

#### 12. Generated Output Verification (Anti-Ghost Dependencies)
> *"Whenever you generate code, verify that the generated output works with what is installed."*

**Mandate:** After using ANY code generation or scaffolding tool, verify the generated output:
1. **Import verification**: All `import` statements reference packages present in project dependencies.
2. **Syntax verification**: Generated files pass linters and type-checkers without errors.
3. **No ghost references**: Zero references to renamed, removed, or non-existent packages.
4. **Identity & placeholder verification**: `grep` generated headers/configs for default placeholders (`osa_app`, etc.) to confirm real project identity resolution.
5. **Package marker purity (`0-byte` `__init__.py`)**: In Python consumer/domain packages (`src/**/__init__.py`) and `tests/**/__init__.py`, `__init__.py` files MUST remain completely empty (`0 bytes`). Never place variables, metadata, configuration, imports, or runtime logic inside `__init__.py` — project and bounded-context metadata belong exclusively in declarative manifest/configuration files.

If generated output contains errors, fix the generator/template at the SOURCE, not just the generated file.

#### 13. Model Delegation Discipline (Flash vs Inherit & 4-Channel Digest)
> *"Never spend a heavy model on a mechanical task."*

**Mandate:** When spawning subagents via `invoke_subagent`, select the model tier deliberately:
- `flash`: Mechanical, deterministic, pattern-matching tasks (file scanning, grep sweeps, coverage runs, inventory extraction, 1:1 file mapping checks). Respect `// delegate: flash` skill hints.
- `inherit`: Judgment-heavy, architectural, or debugging tasks (design decisions, refactoring plans, root-cause analysis, code review).
- `pro`: Deep multi-step architectural reasoning or novel algorithm design.

**Asymmetric Context Routing (4-Channel Subagent Digest):** Require subagents to return a compact **4-channel executive digest** instead of raw log dumps:
1. **Domain State**: Verified entities, models, and current behavior.
2. **Affected Port / Contract**: Interface, protocol, or API boundary impacted.
3. **Invariants & Constraints**: Architectural, security, or typing rules that must hold.
4. **Actionable Delta**: Exact files and line ranges to create or modify.

#### 14. Language Purity & Pre-Edit Scope Gate (Universal Consistency)
> *"Keep every interaction consistent, not only roadmap tasks: zero language mixing in technical files and zero unannounced collateral edits."*

**Mandate:** Maintain strict interaction and language consistency across ALL tasks:
1. **Single-Language Purity per File (Zero Language Mixing)**: While user communication is in Spanish, all English-first artifacts (source code, docstrings, CLI messages, tests, `Makefile`, `.agents/rules/`, templates, governance files, and English documentation) MUST be written in 100% pure technical English. Never mix conversational Spanish nicknames or idioms inside English technical files.
2. **Pre-Edit Scope Blueprint**: Before invoking file-modification tools (`write_file`, `edit_file`) on any multi-file or architectural task, present a concise table of the exact files to create/modify and the symbols/signatures to introduce.
3. **Collateral Freeze**: If a test runner, linter, or diagnostic tool reveals pre-existing issues in untouched files outside the agreed task scope, NEVER modify those collateral files automatically in the same turn. Report them to the user first or capture them in `BACKLOG.md`.

#### 15. Pre-Debug Diagnostic Sweep & Zero-Shot Habit Crystallization
> *"Before blind-debugging a runtime, import, or test failure, run the project's deterministic diagnostic sweep."*

**Mandate:** Before deep-debugging runtime errors (e.g., 422s, DI resolution failures), import anomalies, or test discrepancies:
1. **Run the project's diagnostic command first** (e.g., `make doctor` / `osa doctor --clean-cache` or equivalent architecture/lint checker) to deterministically sweep architectural boundaries, runtime import traps, test structure, and stale bytecode caches.
2. **Crystallize recurring verification routines**: Whenever a multi-step check is repeated across tasks, crystallize it into a deterministic `Makefile` target or CLI subcommand rather than ad-hoc shell invocations.

---

## Refactoring & Code Decommissioning

- **Description**: Rules for moving, renaming, extracting, restructuring, and decommissioning code (step-by-step workflow → `skills/refactoring/SKILL.md`)
- **Applies**: All source code files

1. **Behavioral Invariant & Atomic 1:1:1 Test/Spec Alignment**: When modifying internal structure or splitting a monolithic module into submodules, all tests pass with identical results, test count must remain equal or increase (NEVER decrease), coverage remains 100%, and monolithic test files and `docs/architecture/` traceability tables (`Specification:` docstring pointers) MUST be split/aligned `1:1:1` (`tests/unit/**/test_<module>.py`, `Test*` class per file, docstrings, and AAA comments) in the SAME iteration — never defer test or spec alignment to a follow-up prompt.
2. **Zero-Residue**: When `A` is replaced by `B`, `A` must be **fully removed** in the same changeset. Backward-compatibility aliases (`OldName = NewName`), `@deprecated` classes, and re-export shims (`from new import New as Old`) are strictly forbidden. Delete the old file and update all imports and `@patch` targets atomically.
3. **Rename Urgency**: When moving `A` from module `X` to module `Y`, if `A`'s name no longer reflects `Y`'s context, rename it in the same changeset.
4. **Code & Feature Decommissioning (Mandatory Test Pruning Audit)**: When deleting a module, class, method, endpoint, or feature (intentionally changing external surface area), **never leave obsolete or orphan tests behind**. Execute a 3-step pruning audit in the same changeset: (a) **1:1 File Purge** — delete or consolidate any `test_<module>.py` whose source module no longer exists; (b) **Symbol & Fixture Purge** — grep `tests/` for removed symbols, mock specs, and obsolete enum/contract assertions; (c) **Default-Parameter Sensitivity Verification** — when adding new fields/parameters with defaults (e.g., cryptographic hashes, filters, state transitions), write explicit tests proving non-default values alter the output, rather than relying on 100% line coverage achieved solely via default arguments.

---

## Governance (Universal)

- **Description**: Commit discipline, priority chain, full-stack analysis scope, and global config persistence
- **Applies**: Always

### Commit Discipline
1. **NEVER run mutating git commands** (`git add`, `git commit`, `git push`, `git commit --amend`, `git reset`) automatically.
2. **ONE single commit per repo** using Conventional Commits (`feat:`, `fix:`, `chore:`, `refactor:`, `test:`, `docs:`).
3. **Independent repos**: Deliver a separate commit block per modified repo (`cd <REPO_PATH> && git add ... && git commit -m "..."`). Never stage a sub-repo from the parent root.
4. **Task tracking sync is MANDATORY** before delivering any commit block (`skills/continue/SKILL.md`).
5. **Force-tracked `.gitignore` files**: If a repository tracks files that match `.gitignore` rules (e.g., `WORKROAD.md`, `WORKTASK.md`, `WORKVALI.md`, `BACKLOG.md`, `CHANGELOG.md`, `.agents/SESSION.md`, or `roadmaps/`), use `git add -u` to stage all modified tracked files (plus `git add -f <new_ignored_file>` when creating a new file in an ignored directory) so force-tracked governance files are never left unstaged.

### Priority Chain & Full-Stack Scope
- **Priority Chain**: (1) Active task tracker (`WORKTASK.md`, in-progress first) → (2) Active roadmap/backlog (`WORKROAD.md` / `BACKLOG.md`) → (3) Future `roadmaps/`. NEVER suggest ad-hoc work from memory (`skills/priority/SKILL.md`).
- **Full-Stack Analysis Scope**: Search ALL relevant layers (backend, frontend, infrastructure, persistence) when scoping. "Not built" only when all layers lack it.

### Global Config Persistence (`dotfiles-ubuntu`)
When creating or modifying ANY file in `~/.gemini/config/` (`AGENTS.md`, `hooks.json`, `scripts/`, `skills/`):
1. Edit the source of truth in `~/dotfiles-ubuntu/antigravity/.gemini/config/` FIRST.
2. Re-stow into `~/.gemini/config/`: `cd ~/dotfiles-ubuntu && stow -t ~ -R antigravity`.
3. Never symlink machine-local runtime directories (`config.json`, `mcp_config.json`, `.migrated`, `.ruff_cache/`, `node_modules/`, `plugins/`, `sidecars/`, `projects/`).

---

## Testing (Universal)

- **Description**: Test patterns, coverage gates, and quality invariants (full guide → `skills/testing/SKILL.md`)
- **Applies**: All test files

1. **AAA Pattern — MANDATORY**: Every test method MUST contain three separate, explicit comments: `# Arrange`, `# Act`, and `# Assert` (never merge into `# Arrange & Act` or `# Act & Assert`). Prefer DAMP over DRY with literal expected values.
2. **Service Constructor Rule — CRITICAL**: Every service/use-case constructor in unit tests MUST inject mocked dependencies (`MagicMock(spec=...)` / `AsyncMock(spec=...)`) unless the test exercises that dependency.
3. **Patch Targets**: Patch where the object is looked up at runtime (`consumer.func` when imported via `from source import func`). Update all patch targets when moving files.
4. **100% Coverage, Speed & Deprecation-Free Gates**: Maintain 100% statement and branch coverage, `< 1s` per unit test, and 0 `DeprecationWarning` (`-W error::DeprecationWarning`).
5. **Anti-Characterization Trap**: When writing tests to close coverage gaps, never blindly lock in broken production behavior. Cross-check the caller/template contract (`hx-get`/`hx-post`/`hx-target`) and project rules first — fix production bugs before writing the test, and add new test methods for extra loop/branch scenarios rather than mutating existing single-item tests.
6. **What NOT to Test**: Test our executable logic (1:1 mapping for files with executable logic), never language/framework axiomatics (`isinstance(StrEnum, str)`, `issubclass`, Pydantic `Field(default=...)`, literal constants). DO test public contract defaults (`OSAManifest`, `BaseOSASettings`, exception `error_code`/`http_status`, protocol enums).
