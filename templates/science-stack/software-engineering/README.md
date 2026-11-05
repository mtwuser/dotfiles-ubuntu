# Science-Stack Template: Computer Science & Software Engineering (`software-engineering`)

Ready-to-apply **Science-Stack Template Pack** (`kind: "science-stack"`, `extends: "science-base"`) for software engineering, platform infrastructure, data engineering, and scripting workspaces.

> **Why `software-engineering` Lives Under `science-stack` (`extends: "science-base"`) & How the Engineering Spectrum Fits Together**:
> - Universal scientific and engineering rigor (`Trunk -> Branch -> Specialty` epistemic routing, `1:1:1` Theory/Spec $\leftrightarrow$ Proof/Test $\leftrightarrow$ Corpus/Implementation symmetry, `AAA` Hypothesis-Method-Proof verification, SI/ISO & `N vs N ± 1` boundary precision, and `M1..M4` academic degree progression) lives in **`science-base`**.
> - Within the **`engineering` trunk (`CANONICAL_SCIENCE_TRUNKS["engineering"]`)**, `science-stack` splits cleanly by execution substrate:
>   1. **Physical, Industrial & Non-Software Engineering (`sci-engineering` via `scientific-knowledge-branch`)**: Governs Civil, Mechanical, Electrical, Industrial, Aerospace, Chemical, Telecom, and Functional Safety (`IEC 61508` / `ISO`) engineering corpora in `docs/reference/`.
>   2. **Executable Computer Science & Software Engineering (`software-engineering`)**: Specializes `science-base` when the engineering artifact is **machine-executable code**—enforcing strict compilers/linters (`ruff`, `mypy --strict`, `tsc --noEmit`, `shellcheck`), `0-byte __init__.py` package-marker purity, Relational Cluster Mass ($M_{\text{cluster}}$) refactoring, constructor dependency injection, and `100%` isolated `Unit -> Imp -> E2E` branch coverage.
>   3. **Academic Computer Science & Engineering (`domain-engineering:M1..M4` / `domain-software:M1..M4`)**: Pairs `science-base` + `software-engineering` (or `sci-engineering`) with `Human-Stack` (`M1` introductory programming/engineering $\rightarrow$ `M2` undergraduate software design $\rightarrow$ `M3` postgraduate distributed systems $\rightarrow$ `M4` doctoral/principal systems research).
> - Concrete application frameworks in **`framework-stack`** (`fastapi-hexagonal`, `angular-web`, `django-backend`, `nist-csf-security`) extend `software-engineering` cleanly.

---

## 1. Quick Setup (Deterministic CLI)

Apply the `software-engineering` branch pack and inherited `science-base` rules with a single CLI command:

```bash
# Materialize science-base + software-engineering into a software workspace
./scripts/layer-config.sh apply-project /path/to/workspace --template software-engineering --layers all
```

---

## 2. Template Pack Contents

### 2.1. Rules (`.agents/rules/`)

Projected rules enforce C-backed stdlib reuse, strict typing/linting, `0-byte __init__.py` purity, and 100% isolated `AAA` test coverage:

| File | Scope (`software-engineering` Delta over `science-base`) |
|------|----------------------------------------------------------|
| `rules/software-engineering.md` | C-backed stdlib & import gate, strict compiler/linter/typing integrity, `0-byte __init__.py` purity, $M_{\text{cluster}}$ refactoring escalation, and 100% isolated `Unit -> Imp -> E2E` `AAA` test flow |

### 2.2. Skills (`.agents/skills/`)

Projected skills cover `1:1:1` testing, $M_{\text{cluster}}$ refactoring, manual/automated `V1..V5` validation, and `C3` OSS contributions:

| File | Skill Name & Purpose |
|------|----------------------|
| `skills/testing/SKILL.md` | `testing` — `1:1:1` human-agent test comprehension, `AAA` pattern, constructor injection, and 100% isolated branch coverage |
| `skills/refactoring/SKILL.md` | `refactoring` — Relational Cluster Mass ($M_{\text{cluster}}$), 6-stage modular escalation, and `[WIRE]` / `[CONSOLIDATE]` / `[PRUNE]` |
| `skills/validation/SKILL.md` | `validation` — Exhaustive manual and automated QA validation procedures |
| `skills/oss-contribute/SKILL.md` | `oss-contribute` — Empirical hot-path profiling, C-backed stdlib vectorization, and upstream OSS PR workflow |
