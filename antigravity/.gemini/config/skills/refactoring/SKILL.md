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
- **Line count**: > 500 lines.
- **Test classes**: > 5 unrelated classes in one file.
- **Source files tested**: > 1 source file per test file.

## Execution Workflow
Follow this sequence strictly to ensure no behavioral changes are introduced.

1. **Baseline**: Run tests, confirm 100% coverage, record the test count.
2. **Audit**: List all files that will be changed and all imports that will need updating.
3. **Plan**: Document exact targets (which code → which new files).
4. **Execute per file**: 
   - Move the isolated logic.
   - Fix all imports.
   - Run tests after EACH move to isolate breakages immediately.
5. **Final verification**: Ensure the test count is identical (or higher) and coverage is 100%.
6. **Commit**: One atomic commit per logical change.

## Move Protocol Between Modules
When a component moves from Module A to Module B:
1. Create the new file in the target module (`Module B`).
2. Update **EVERY** import across the entire codebase (`grep` for the old path).
3. Update **EVERY** `@patch()` target in test files.
4. Update **EVERY** docstring and comment reference.
5. **DELETE the old file** in `Module A` — do not leave a backward compatibility shim, alias, or re-export. Let the code fail loud if an import was missed.

## Naming Protocol
- Choose the architecturally correct name **in the same changeset**.
- Never defer naming to a "later rename" task.
- If the unit has a specific responsibility now, pick naming patterns that match the target module's domain.

## Code Decommissioning & Obsolete Test Pruning

> **When to use**: Whenever a feature, module, class, endpoint, or behavior is intentionally **removed or replaced** (as opposed to a behavior-preserving refactor).

Unlike pure refactoring (where test count must remain `>=` baseline), **feature decommissioning requires decreasing or replacing obsolete tests** so dead test files and trivial assertions never accumulate:

1. **1:1 Test File Mapping Audit (`orphan-test-file`)**:
   - Every unit test file (`tests/unit/**/test_<name>.py`) must correspond to an existing source module in `src/`.
   - If `src/.../<name>.py` is deleted, delete `tests/unit/.../test_<name>.py` in the same changeset (or merge still-relevant macro/integration tests into the canonical owner's test file).
2. **Dead Symbol & Fixture Sweep**:
   - `grep -rn` across `tests/` for removed class names, functions, routes, fixtures, and `@patch` paths.
   - Remove any test method that existed solely to exercise the decommissioned behavior or axiomatic enum literal counts (`test_member_count`, `test_all_values`).
3. **Default-Parameter Sensitivity Check (Anti-False-100% Coverage)**:
   - When decommissioning is paired with new fields that carry default values (e.g., `action="accept"`, `source="autonomous"`), 100% statement/branch coverage can be reached even if non-default values are never tested in cryptographic hashes, serialization, or filtering.
   - Always add explicit sensitivity and tampering tests proving that changing each new field alters the resulting hash, state, or filter output.
