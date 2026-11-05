---
name: oss-contribute
description: "Conscious C3 workflow for empirical hot-path profiling, C-backed stdlib vectorization, optional PEP 7 C-accelerators, and upstream OSS-to-OSS pull request contributions."
---

# Conscious C-Substrate Optimization & Upstream Contribution — `oss-contribute`

> **When to use (`C3 — Conscious Human-Gated`)**: Invoke this skill **explicitly and consciously** as a standalone engineering task **after** the active repository has reached `/full-audit` **Regime 0 (`0` compliance gaps)**.
> Never mix this exploratory optimization and multi-repository contribution workflow into routine pre-release compliance audits (`/full-audit`) or internal governance rule promotions (`/enrich`).

---

## 1. Three-Pillar Separation of Responsibilities

The table below separates convergent compliance audits (`/full-audit`), internal refactoring (`refactoring`), and conscious substrate/OSS contributions (`oss-contribute`):

| Workflow Skill | Consciousness Tier | Primary Responsibility | Boundary |
| :--- | :--- | :--- | :--- |
| **`/full-audit`** | `C2` (Convergent Gate) | **Closed-World Gap & Compliance Detection**: Verify `0` discrepancies against existing specs, rules, `1:1:1` test symbiosis, and 5-link parity before `/release`. | Never invents open-ended refactors, `PEP 7` extensions, or external OSS PRs when invariants pass. |
| **`/architecture-review` + `refactoring`** | `C2 / C3` (Internal Evolution) | **Internal Architectural & Code Optimization**: Orthogonal dimension matrices, SSoT consolidation, and 6-Stage Structural Evolution Ladder (`Inline -> Function -> Class -> Protocol/Catalog -> 1:1:1 Module -> 1:1:1 Bounded-Domain Subpackage`). | Strictly internal to the active repository's domain architecture and module structure. |
| **`oss-contribute` (This Skill)** | `C3` (Conscious Culmination) | **C-Substrate Optimization & External `OSS-to-OSS` Contribution**: Empirical profiling, C-backed stdlib vectorization, optional `PEP 7` C-accelerators, and upstream PRs to external open-source packages (`Tier -1`). | Invoked deliberately when pushing internal hot paths or upstream OSS dependencies to their performance ceiling. |

---

## 2. Phase 1 — Empirical Hot-Path Profiling (Zero Blind Optimization)

1. **Measure Before Touching Code**:
   - Run deterministic micro-benchmarks (`python3 -m timeit`, `cProfile`, `tracemalloc`) on realistic payload sizes (`L0..L3` capsules, multi-layer surface trees, SHA-256 tree diffs, or request pipelines).
2. **Locate the Exact Substrate Bottleneck**:
   - Classify whether the bottleneck is:
     - **(A) Pure-Python Bytecode Loop Overhead**: Byte-by-byte iteration, repeated regex compilation, or heap-loading whole files when C-backed stdlib primitives exist.
     - **(B) Algorithmic / CPU Ceiling Inside the Active Repo**: Compute-bound cryptographic, parsing, or graph-traversal hot paths where even C-backed stdlib primitives saturate.
     - **(C) Upstream Open-Source Library / Runtime Limitation (`Tier -1`)**: A bug, missing fast-path, or suboptimal C/Python implementation in `CPython`, `FastAPI`, `Starlette`, `Pydantic` (`pydantic-core`), `SQLAlchemy`, or `GNU Stow`.
3. **Present the Empirical Baseline Table**:
   - Report `Target Symbol -> Current Latency/Memory -> Bottleneck Category (A / B / C) -> Projected Gain` and wait for human confirmation before proceeding to Phase 2 or Phase 3.

---

## 3. Phase 2 — 3-Tier Substrate Escalation Matrix

Escalate strictly in order of lowest maintenance friction and zero supply-chain bloat:

| Escalation Step | Target Substrate Tier | Actionable Engineering Pattern | Verification Gate |
| :--- | :--- | :--- | :--- |
| **Step 1 (Always First)** | **Tier 1 — Floor-Version C-Backed Stdlib Primitives** | Replace Python bytecode loops with C-backed stdlib operations already shipped in `CPython`:<br/>• `hashlib.file_digest(f, "sha256")` (`Modules/_hashopenssl.c` streaming buffer)<br/>• `int.from_bytes(...) ^ int.from_bytes(...)` (`Objects/longobject.c` word-level XOR)<br/>• `os.scandir`, `stat.S_IWUSR` (`Modules/posixmodule.c`)<br/>• `zlib.compress`, `json.loads` (`Modules/_json.c`) | 100% identical output bytes, `0` new dependencies, 100% isolated unit branch coverage, measurable latency reduction. |
| **Step 2 (When Stdlib Saturates)** | **Tier 0 — Optional `PEP 7` C-Accelerator + `1:1` Fallback** | Isolate the hot path into an optional C extension module (`_<module>_accel.c` following `PEP 7` C coding style) paired with a **mandatory `1:1` pure-Python fallback** so `dependencies = []` and hermetic portability remain intact. | Unit tests run against **both** the C accelerator and the pure-Python fallback, asserting bit-for-bit output equivalence and memory safety. |
| **Step 3 (External Bottleneck)** | **Tier -1 — Upstream `OSS-to-OSS` Contribution** | When the improvement belongs upstream in `CPython` or a primary stack dependency, execute **Phase 3 (Isolated External Upstream Sandbox)** below. | Zero unrequested mutations inside the local workspace; upstream PR follows the external maintainer's exact contribution contract. |

---

## 4. Phase 3 — Isolated External Upstream Sandbox & PR Protocol (`Tier -1`)

When a bottleneck or defect identified in Phase 1–2 warrants contributing upstream to an external open-source project (`CPython`, `FastAPI`, `Pydantic`, `GNU Stow`, etc.):

1. **Strict Workspace Isolation (`~/Projects/oss-contrib-<repo>`)**:
   - **Never** clone external repositories inside the active workspace or its `layers/*` directory.
   - Ask the human operator for confirmation to clone/fork the target upstream repository into an isolated sibling directory (`~/Projects/oss-contrib-<repo>`).
2. **Upstream Governance & Issue Alignment**:
   - Read the external repository's `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, C/Python style guide (e.g., `PEP 7` for C extensions, `PEP 8` for Python stdlib), and issue tracker requirements first.
3. **Minimal Reproducible Benchmark & Bipolar Regression Test**:
   - Author a standalone reproduction script or benchmark proving the bug or speedup, plus unit tests following the external repository's native test runner (`libregrtest` for CPython, `pytest` for FastAPI/Pydantic).
4. **Conscious Human-Gated Delivery (`--create-pr`)**:
   - Present the exact diff, benchmark before/after table, and `git commit` / `gh pr create` commands for the human operator to review and execute consciously.
   - Log the upstream PR reference in the local repository's `BACKLOG.md` or `CHANGELOG.md` only if a local workaround or floor-version note depends on it.
