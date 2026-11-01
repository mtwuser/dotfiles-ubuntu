---
name: full-audit
description: "Execute a deep, structured, multi-pass and multi-perspective repository audit (Conceptual 4-Perspective Matrix -> Pragmatic Technical & Stack Currency -> 1:1:1 Human-Agent Test Symbiosis -> Governance Spillover Gate into roadmaps/WORKROAD/WORKTASK/BACKLOG)."
---

# Full Repository Audit — `/full-audit`

> **Purpose**: Execute an exhaustive, zero-myopia, multi-perspective audit of the active repository without hallucinations, half-finished findings, or context loss.
> Combines a **Conceptual & Normative Pass (4-Perspective Lifecycle Matrix)** with a **Pragmatic Technical & `1:1:1` Human-Agent Test Comprehension Pass**, and automatically routes large finding sets into the repository's governance pipeline (`roadmaps/` $\rightarrow$ `WORKROAD.md` $\rightarrow$ `WORKTASK.md` / `BACKLOG.md`).

---

## Core Audit Principles

1. **Repository & Stack Agnosticism**: Never assume rules or counts from another repository. Always discover the active repository's stack, manifests, and rule hierarchy first.
2. **4-Scope Rule Separation**:
   - **Scope 1 (`$HOME` Read-Only Workstation Base)**: Universal cognitive, session, and commit governance (`human-core`).
   - **Scope 2 (General Technical Baseline — `technical-base`)**: Stack-general software engineering, `1:1:1` traceability, refactoring, and testing invariants applicable to any language or framework.
   - **Scope 3 (Stack-Specific Template Pack)**: Language- and framework-specific conventions (e.g., Python 3.14 PEP 695, FastAPI/HTMX, TypeScript/React, Rust, Go).
   - **Scope 4 (Repository-Local Specifications & Gates)**: Architecture specs (`docs/architecture/`), domain invariants, and verification gates specific to the active repository.
3. **Modern Stack Currency & Zero-Backward Law**: Always target the latest stable language/framework idioms declared by the project; flag and eliminate legacy shims, aliases, and deprecated fallbacks.
4. **Execution Block Until Approval**: Present structured findings and the Pre-Edit Scope Blueprint first; never mutate repository files before explicit user confirmation.

---

## Phase 0 — Context, Stack & Rule-Scope Discovery

// delegate: flash

1. **Discover Stack & Toolchain**:
   - Inspect project manifests (`pyproject.toml`, `package.json`, `Cargo.toml`, `go.mod`, `Makefile`, `Dockerfile`, CI workflows) to determine target language versions, linters, type-checkers, and test runners.
2. **Classify Active Rules by Scope**:
   - Read `.agents/rules/*.md`, `.agents/LAYER_LINEAGE.md`, and `docs/architecture/*.md`.
   - Separate **generic inherited rules** (`technical-base`, `business-base`) from **stack-specific rules** and **repository-local specs**; flag any leak where repository-local counts or single-stack literals contaminate a generic rule or skill.
3. **Establish Baseline Health**:
   - Run the repository's non-mutating diagnostic/verification command (`make verify`, `make doctor`, or equivalent) to record baseline status.

---

## Phase 1 — Pass 1: Conceptual Coherence, Stack Currency & 4-Perspective Lifecycle Matrix

Trace every core domain flow and rule across **4 operational perspectives** to uncover hidden contradictions that single-file reviews miss:

| Perspective | Question to Verify Across Every Flow |
| :--- | :--- |
| **1. Setup / Bootstrap / Scaffolding** | Do initializers, templates, manifests, and environment setup scripts materialize files and paths in the exact locations expected at runtime? |
| **2. Runtime / Execution / Skills / Hooks** | Do runtime modules, CLI entrypoints, lifecycle hooks, and agent skills invoke the current commands, flags, and paths without legacy fallbacks? |
| **3. Verification / Testing / Gates** | Do automated linters, parity gates, and tests actually exercise the real runtime structure (e.g., class-indented methods, multi-channel guards, isolated unit coverage)? |
| **4. Federation / Integration / Extrapolation** | Do cross-layer interactions, MCP contracts, and shared templates remain 100% extrapolable without leaking local repository assumptions? |

### Pass 1 Checklist
- [ ] **3-Tier Documentation Coherence (`README.md` $\rightarrow$ `docs/guides/` $\rightarrow$ `docs/architecture/` & `docs/reference/`)**: Verify directory trees against disk (`find`/`ls`), relative links (`test -f`), CLI flag tables, and `< 465`-line modularity.
- [ ] **Modern Stack Currency**: Verify that docs, rules, templates, and code use the target modern stack version consistently (zero outdated version ranges or legacy typing syntax).
- [ ] **Zero-Backward Law Scan**: Confirm zero `@deprecated` markers, compatibility aliases (`OldName = NewName`), dual CLI flags, or dead transition branches.
- [ ] **Generic vs. Local Rule Purity**: Confirm that reusable base rules (`technical-base`) and shared skills contain zero hardcoded counts, paths, or assumptions tied to a single repository.

Record all findings in a structured table (`[P1-01]`, `[P1-02]`, ...) with severity, conflicting perspectives, exact `file:line` evidence, and clean-cutover remediation.

---

## Phase 2 — Pass 2: Pragmatic Technical Architecture & Stack Exploitation

Once conceptual and normative requirements from Pass 1 are aligned, audit their **code representation** for engineering excellence:

1. **Idiomatic Stack Exploitation**:
   - Evaluate whether the implementation leverages modern language features (e.g., native generic syntax, pattern matching, strict protocols/interfaces, zero-copy/stdlib primitives) rather than verbose boilerplate.
2. **Functional vs. Object-Oriented Balance**:
   - Prefer pure, stateless functions for deterministic transformations, parsing, and validation; reserve classes/objects for stateful lifecycle coordination, protocol dispatch, or dependency-injected services.
3. **Modularity, Reuse & File Size (`< 465` Lines)**:
   - Identify duplicated helpers across modules or scripts, oversized files ($\ge 465$ lines, target $\le 400$), circular dependencies, or mixed architectural responsibilities.
4. **Strict Typing & Error Contracts**:
   - Verify explicit parameter and return types on 100% of functions/methods, specific domain exceptions/error codes, and zero linter or type-checker warnings.

Record all technical improvements in a structured table (`[P2-01]`, `[P2-02]`, ...) with `file:line` references and concrete refactoring actions.

---

## Phase 3 — Pass 3: `1:1:1` (`Spec <-> Source <-> Test`) Human-Agent Comprehension Symbiosis

Audit the alignment between **Normative Specifications**, **Executable Source Modules**, and **Unit Test Suites** so tests serve as self-documenting executable specifications for both **Agent** and **Human**:

1. **Level 1 — Bidirectional `1:1:1` Specification Table (`docs/architecture/<spec>.md`)**:
   - Every executable source module declares `Specification: docs/architecture/<spec>.md`.
   - Every architecture spec (`< 465` lines) maintains a `1:1:1` table mapping `Source Module <-> 1:1 Unit Test Suite (Test<Module>) <-> Functional Responsibility & Key Verified Invariants`.
2. **Level 2 — Single Canonical Test Container per File (`Test<Module>`)**:
   - Every `1:1` test file (`tests/unit/**/test_<module>.*` or `<module>.test.*`) encapsulates its tests inside **one** canonical class/suite (`class Test<Module>` / `describe('<Module>')`) whose docstring/header links back to the source module and specification.
3. **Level 3 — Self-Documenting Behavioral Test Names + 1-Line Invariant Docstrings**:
   - **Test Method Name (`test_<subject>_<scenario_or_condition>_<expected_outcome>`)**: Reads as a natural-language functional proposition for human scanning.
   - **1-Line Invariant Docstring**: States *why* the test exists — the normative invariant, security pole, or boundary cut-point (`N` vs `N ± 1`) proven — eliminating the need for noisy inline narrative comments.
   - **Explicit AAA & Anti-Deception Gates**: Separate `# Arrange`, `# Act`, and `# Assert` comments, 100% isolated unit branch coverage, exact `N` vs `N ± 1` boundary cut-points, bipolar guard verification (negative pole first, positive pole second), explicit error matching (`match=`), and zero blind boundary/subprocess mocks.

---

## Phase 4 — Scale & Governance Spillover Gate (`WORKROAD` / `WORKTASK` / `BACKLOG`)

Before executing fixes, evaluate the total approved scope to prevent rushed execution or mid-audit context loss:

| Regime | Threshold | Mandatory Orchestration Flow |
| :--- | :--- | :--- |
| **Regime A — Atomic In-Session Execution** | $\le 15$ cohesive findings completable within the current session with 100% verification | 1. Present the **Master Audit Plan** artifact with a Pre-Edit Scope Blueprint.<br>2. Upon user approval, execute in ordered batches (`P0 Runtime/Hooks` $\rightarrow$ `P1 Rules/Skills` $\rightarrow$ `P2 Docs/Templates` $\rightarrow$ `P3 1:1:1 Tests & Gates`).<br>3. Run full verification (`make verify`) after each batch and close via `/continue`. |
| **Regime B — Multi-Phase Governance Spillover** | $> 15$ findings, cross-cutting architectural refactors, or multi-session scope | 1. Crystallize the full audit blueprint into `roadmaps/audit_<YYYY_MM_DD>.md`.<br>2. Register the ordered audit phases (`RA.1`, `RA.2`, ...) in `WORKROAD.md` and capture independent backlog items in `BACKLOG.md`.<br>3. Promote **only the first phase (`RA.1` $\rightarrow$ `T1`)** into `WORKTASK.md` per `/priority` and `/governance`.<br>4. Execute and verify `T1` atomically, then checkpoint via `/continue` so zero findings are ever left half-done across sessions. |
