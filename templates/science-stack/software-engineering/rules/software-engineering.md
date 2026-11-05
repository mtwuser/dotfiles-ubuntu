---
trigger: always_on
description: "Software engineering, strict typing, 0-byte __init__.py, refactoring, and 100% isolated AAA unit testing rules (software-engineering)"
---
# Software Engineering, Refactoring & Testing Branch (`software-engineering`)

> Software engineering specialization extending `science-base` (`.agents/rules/software-engineering.md` or `layer-config.sh set-global-profile technical`).

---

## Software Engineering, Refactoring & Application/MCP Security

- **Description**: Strict typing, stdlib reuse, refactoring, AppSec (OWASP ASVS), and MCP capability security
- **Applies**: All software engineering, scripting, application, and MCP repositories

1. **Utility, Stdlib, Typing & Package-Marker Gate**: Search (`grep`/semantic) before writing helpers, use C-backed stdlib symbols (`hashlib.file_digest`, `stat.S_IWUSR`, `HTTPStatus`) and explicit absolute imports (`0` aliases). Enforce zero linter/type (`ruff`/`mypy --strict`, `tsc --noEmit`, `cargo clippy`, `shellcheck`) errors (`unknown`/`Protocol` over `Any`), keep `src/**/__init__.py` and `tests/**/__init__.py` `0 bytes`, and avoid raw modes (`0o644`), numeric schema IDs (`"1.2"`), raw slices (`[:24]`), or `.update()` packing.
2. **Refactoring & Relational Cluster Mass ($M_{\text{cluster}}$, `skills/refactoring/SKILL.md`)**: Keep tests passing (`100%` coverage) and align `1:1:1` specs in the SAME iteration. Evaluate line load ($< 465$, target $\le 400$), $M_{\text{cluster}} = \sum_{f \in G} L(f)$ ($\ge 2$ coupled modules $\ge 385$ lines with $M_{\text{cluster}} \ge 1{,}200$; zero cross-peer `_private` imports), and Directory Fan-Out ($< 15$ modules/dir $\rightarrow$ $3\text{--}8$-module subpackages), escalate (`Inline -> Function -> Class -> Protocol -> Module -> Subpackage`), and execute `[WIRE]` / `[CONSOLIDATE]` / `[PRUNE]`.
3. **Application, Technological & Multi-Layer MCP Security (`OWASP ASVS` + `MCP-Sec`)**:
   - **AppSec & Containers**: Enforce boundary schema validation, parameterized queries (`0` raw SQL/shell interpolation; `subprocess` list args without `shell=True`), explicit AuthN/AuthZ, zero secrets/PII, and non-root containers.
   - **MCP Capability & Layer Containment**: Enforce `Path.resolve().is_relative_to(workspace_root)` (`PATH_CONTAINMENT_VIOLATION`), run subagents in `strictly-read-only` sandboxes (`orchestrate_ephemeral_fork`), verify HMAC `DMCP` frames and `citation_receipt` (`CITATION_DRIFT_DETECTED`), and scope MCP tools by `precedence` (`0..100`) and `environment` (`dev|pre|pro`).

---

## Software Testing & 100% Isolated `Unit -> Imp -> E2E` Flow

- **Description**: Self-documenting `1:1:1` test architecture and coverage gates (`skills/testing/SKILL.md`)
- **Applies**: All software test files

1. **Bidirectional 3-Tier Flow & `AAA`**: Deduce **Top-Down (`E2E -> Imp -> Unit`)**; author **Bottom-Up (`Unit -> Imp -> E2E`)**. Model `E2E` as persona journeys, `Imp` (*Implementation* contracts; never `int`), and `Unit` (`1` `Test<Module>` class/file linked to `Specification: docs/architecture/<spec>.md`). Pair `test_<subject>_<scenario>_<expected>` names with a **1-line docstring** and `# Arrange`, `# Act`, `# Assert` comments.
2. **Constructor Injection & 100% Isolated Coverage**: Inject spec-constrained mocks/fakes in constructors, patch at the consumer lookup seam, and enforce 100% branch coverage on isolated `tests/unit/` first (`< 1s`/test, 0 deprecations) before `imp`/`e2e`. Fix bugs first; never lock in broken behavior.
