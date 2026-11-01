---
name: refactoring
description: "Use when breaking down massive monolithic files, resolving 'God Components', or performing major architectural refactors."
---

# How to Extract God Components and Refactor

> **When to use**: Use this skill when breaking down massive monolithic files, resolving "God Components", or performing major architectural refactors.

## Zero-Residue Pattern (Forbidden vs Required)

When `A` is replaced by `B`, `A` must be **fully removed** in the same changeset:

```python
# ❌ FORBIDDEN — backward compatibility shim, deprecated class, or re-export alias
OldName = NewName
from new_module.services.impl import NewClass as OldClass

# ✅ REQUIRED — move the code, delete the old file, update all imports & @patch targets
from new_module.services.impl import NewClass
```

## God Component Criteria
Identify candidates for extraction when a file meets any of these thresholds:
- **Line count**: $\ge 465$ lines (target $\le 400$ lines across source, test, and navigable `docs/**/*.md` files).
- **Test classes**: > 1 unrelated class in a single unit test file (prefer 1 `Test*` class per `test_<module>.py`).
- **Source files tested**: > 1 source file per unit test file (`1:1:1` mapping: `Source <-> Unit Test <-> Specification`).

## Execution Workflow
Follow this sequence strictly to ensure no behavioral changes are introduced.

1. **Baseline**: Run tests (`Unit -> Imp -> E2E`), confirm 100% isolated unit coverage, and record the total test count.
2. **Pre-Edit Reading & Impact Audit (`Top-Down: E2E -> Imp -> Unit`)**:
   - Read (1) `docs/guides/` & `docs/architecture/<spec>.md` $\rightarrow$ (2) `tests/e2e/` $\rightarrow$ `tests/imp/` $\rightarrow$ `tests/unit/` $\rightarrow$ (3) source code.
   - List all files that will be changed and all imports/`@patch` seams that will need updating.
3. **Plan**: Document exact targets (which code → which new source files, `1:1` unit test files, and `docs/architecture/` `1:1:1` specification entries).
4. **Execute per file (`Bottom-Up Verification: Unit -> Imp -> E2E`)**:
   - Move the isolated logic and include the `Specification: docs/architecture/<spec>.md` header in the module docstring.
   - Split/align the corresponding `1:1` unit test file (`test_<module>.py`, `class Test<Module>`) and update the `1:1:1` traceability table in `docs/architecture/<spec>.md`.
   - Fix all imports and runtime `@patch` targets across `tests/{unit,imp,e2e}/`.
   - Run tests **Bottom-Up (`tests/unit/` isolated first $\rightarrow$ `tests/imp/` $\rightarrow$ `tests/e2e/`)** after EACH move to isolate breakages in milliseconds without coverage masking.
5. **Final verification**: Ensure the test count is identical (or higher), isolated unit and full coverage are 100%, and every source, test, and `docs/**/*.md` file is `< 465` lines.
6. **Commit**: One atomic commit per logical change.

## Move Protocol Between Modules
When a component moves from Module A to Module B:
1. Create the new file in the target module (`Module B`).
2. Update **EVERY** import across the entire codebase (`grep` for the old path).
3. Update **EVERY** `@patch()` target in test files.
4. Update **EVERY** docstring and comment reference.
5. **DELETE the old file** in `Module A` — do not leave a backward compatibility shim, alias, or re-export. Let the code fail loud if an import was missed.

## Naming Protocol & Self-Indexing File Taxonomy (`O(1)` Glob Discovery)
- Choose the architecturally correct name **in the same changeset** (never defer to a "later rename" task).
- **Enforce Canonical File Prefixes, Suffixes & Extensions**: Every new or extracted file (Stage 5) MUST use a deterministic role prefix/suffix and extension so `glob`, `find`, and MCP `target_globs` classify its responsibility without reading file contents:
  - **Code Modules**: `tools_<domain>.py` (MCP/API tool dispatchers), `<domain>_engine.py` (core domain/orchestration engines), `<domain>_helpers.py` / `*_weaver.py` / `*_configurator.py` / `*_bootstrapper.py` (stateless utilities or lifecycle coordinators), `constants.py` / `catalogs.py` (`0-logic` declarative constants), and `test_<module_stem>.py` (`1:1` test suites).
  - **Governance & Documentation**: `NN_<topic>.md` (`01_`, `02_` reading-order prefix in `docs/guides/` and `docs/architecture/`), `layer-<NN>-<id>.md` (`00..100` precedence prefix in `.agents/rules/`), and `WORK*.md` (`WORKROAD.md`, `WORKTASK.md`, `WORKVALI.md` active root trackers).
- **Continuous Consistency on Every Edit / Feature**: Whenever modifying a file for a bugfix, concrete change request, or new feature, never introduce split-idiom drift between the new code and older (`> 90d`) or over-compressed surrounding code in that file; align the touched scope atomically or proactively propose refactoring (and capture in `BACKLOG.md`).

## Code Decommissioning & Obsolete Test Pruning

> **When to use**: Whenever a feature, module, class, endpoint, or behavior is intentionally **removed or replaced** (as opposed to a behavior-preserving refactor).

Unlike pure refactoring (where test count must remain `>=` baseline), **feature decommissioning requires decreasing or replacing obsolete tests** so dead test files and trivial assertions never accumulate:

1. **1:1 Test File Mapping Audit (`orphan-test-file`)**:
   - Every unit test file (`tests/unit/**/test_<name>.py`) must correspond to an existing source module in `src/`.
   - If `src/.../<name>.py` is deleted, delete `tests/unit/.../test_<name>.py` in the same changeset (or merge still-relevant boundary/workflow tests into the canonical owner's implementation `tests/imp/` or E2E `tests/e2e/` test file).
2. **Dead Symbol & Fixture Sweep**:
   - `grep -rn` across `tests/` for removed class names, functions, routes, fixtures, and `@patch` paths.
   - Remove any test method that existed solely to exercise the decommissioned behavior or axiomatic enum literal counts (`test_member_count`, `test_all_values`).
3. **Default-Parameter Sensitivity Check (Anti-False-100% Coverage)**:
   - When decommissioning is paired with new fields that carry default values (e.g., `action="accept"`, `source="autonomous"`), 100% statement/branch coverage can be reached even if non-default values are never tested in cryptographic hashes, serialization, or filtering.
   - Always add explicit sensitivity and tampering tests proving that changing each new field alters the resulting hash, state, or filter output.

## 5-Stage Structural Evolution & De-Compression Ladder

While semantic conciseness (clean comprehensions, native stdlib primitives) is desirable in consolidated code, **defensive syntactic compression** (opaque short variable names like `d_rec` or `out_h`, chained `.update()` packing, or dense inline blocks used to stay under `< 465` lines) is a deterministic signal to escalate up the abstraction ladder:

| Stage | Saturation / Over-Compression Signal | Escalation Target | Architectural & Cognitive Benefit |
| :--- | :--- | :--- | :--- |
| **1. Inline Compact Expression** | Expression repeats $\ge 2$ times, needs $> 3$ conditions, or forces cryptic short identifiers to save lines. | **$\rightarrow$ Stage 2: Pure Helper Function (`def _verb_noun`)** | Names the intent at the call site while restoring descriptive local variable names inside the isolated function. |
| **2. Pure Function Cluster** | $\ge 3$ functions thread the same $\ge 4$ context parameters (`repo_dir, target_dir, manifest, dry_run` — *Data Clump*). | **$\rightarrow$ Stage 3: Cohesive Class / `@dataclass(frozen=True)`** | Binds shared state once in `self`, eliminating repetitive parameter threading and grouping cohesive methods. |
| **3. Branching Function / Class** | `if / elif / else` or `match` chains branching across $\ge 3$–$4$ roles, surfaces, or kinds in multiple places. | **$\rightarrow$ Stage 4: Declarative Catalog (`dict`) or `Protocol` Polymorphism** | Uses O(1) declarative tables (`constants.py`) when data varies, or `typing.Protocol` / polymorphic dispatch when algorithms vary. |
| **4. Multi-Cluster Module (`> 400` lines)** | File approaches `400–464` lines and relies on horizontal/syntactic compression to avoid `< 465` lines. | **$\rightarrow$ Stage 5: `1:1:1` Sub-Module Extraction** | Extracts a dedicated `<subdomain>.py` (`+ Test<Subdomain> + Spec row`), returning both modules to $\sim 200$–$350$ uncompressed lines. |

## Adaptive Co-Evolution & Bifurcated Age Evaluation (`Human <-> AI Model <-> Technology Substrate`)

Code representation is a living equilibrium across three evolving surfaces:
1. **Technology Substrate**: As language floor versions and C-backed standard libraries evolve, replace verbose manual loops/state with native runtime primitives.
2. **AI Reasoning & Specificity**: As model reasoning and context capabilities advance, favor higher specificity (strict `Protocol` contracts, declarative strategy tables, exact cut-point constants) over repetitive procedural boilerplate.
3. **Human Comprehension Anchor (`1:1:1`)**: Production code can increase in semantic specificity and execution efficiency as long as **Tier 1–3 Documentation (`README -> Guides -> Architecture Specs`)** and **Self-Documenting `1:1:1` Tests (`test_<subject>_<scenario>_<expected>` + 1-line invariant docstring + AAA)** remain 100% transparent to the human operator, flowing refinements bidirectionally via `/enrich` (upward) and `make sync` (downward).
4. **Bifurcated Evaluation of Prolonged Unedited Use (`> 90d` Code/Specs, `> 180d` Policies/Workflows)**:
   - **Trajectory A — Aligned in Active Use (`Zero Drift -> Consolidate & Automate`)**: When an untouched module, rule, or command remains 100% consistent with current architecture and runs without friction, its age indicates **structural maturity**. Flow it toward **higher automation** (crystallizing manual/guided steps into `C1` automated `Makefile`/hook checks), **compaction** into a shared helper/primitive, or **1-hop upward promotion (`/enrich`)**.
   - **Trajectory B — Misaligned or Divergent (`Drift Detected -> Adjust, Refactor & Audit`)**: When an untouched artifact diverges from newer surrounding idioms, current floor-version primitives, or its `1:1:1` specification (`Source` newer than `Spec`), its age indicates **obsolescence or technical debt**. Escalate it via the 5-Stage Ladder, align its `1:1:1` spec/tests, or decommission it (`Zero-Backward Law`).
