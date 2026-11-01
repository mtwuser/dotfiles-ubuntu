---
name: governance
description: "Use when promoting work between tiers (roadmaps → active → done), delegating 1-hop downward directives to child layers, writing CHANGELOG entries, or extracting architectural knowledge from raw conversation files."
---

# Governance Skill

## Part 1 — Promotion Flow and Changelog

> **When to use**: Use this skill when moving items between work tiers (`roadmaps/`, active backlog, task tracker), or when completing a feature and writing the `CHANGELOG.md`.

### Promotion Flow

Work flows strictly from left to right:
`roadmaps/ → WORKROAD.md (or ROADMAP.md) / BACKLOG.md → WORKTASK.md → CHANGELOG.md`

#### 1. Future Roadmap (`roadmaps/`) → Active Roadmap (`WORKROAD.md` / `ROADMAP.md`)
- Select the next roadmap by priority number.
- Execute **deep-analysis** before promotion according to the active `workspace_mode` (`make status` / `.agents/rules/*.md`):
  - **Technical / Hybrid Mode (`technical-base` / `tech-stack/*`)**: `1. Guides/Specs -> 2. Tests [E2E -> Imp -> Unit] -> 3. Code` (audit specs, tests, and code).
  - **Business Mode (`business-base` / `business-stack/*` / `Root 0` / `Department`)**: `1. Normative Policies & Lex Superior (0..100) -> 2. Corporate Ledgers (corporate/) & Traceable IDs ([DEPT]-[TYPE]-[YYYY]-[NNN]) -> 3. Cross-Surface Contracts & Sign-Off Gates` (audit corporate ledgers, policies, and downstream department/squad impact).
- Enrich the roadmap with your findings, then promote its phase checklist to `WORKROAD.md`.

#### 2. Active Roadmap / Backlog (`WORKROAD.md` / `BACKLOG.md`) → Active Tasks (`WORKTASK.md`)
- Promote one phase at a time.
- If `WORKTASK.md` already has items, run cross-task analysis first to detect dependencies and shared components.
- Move the phase to `WORKTASK.md`, renaming the prefix as needed (e.g. `R1` to `T1`).

#### 3. Active Tasks (`WORKTASK.md`) → Done (`CHANGELOG.md`)
- Completed items are DELETED from `WORKTASK.md`, `WORKROAD.md`, and `BACKLOG.md`. Do not leave them as strikethrough (`~~`) or checkmarks.
- Log completed work exclusively in `CHANGELOG.md`.

### Mode Discipline ("Capture, don't act")

When working on a specific task, you might spot unrelated improvements:
1. **Capture**: Add a one-line observation to `BACKLOG.md`.
2. **Continue**: Return to your current task immediately.
3. **Never mix modes**: E.g., do not refactor an unrelated file while writing tests for a new feature.

### CHANGELOG Entries & `[Unreleased]` Release Discipline

Always write for the **USER** (or downstream adopter), not internal scratch notes:
- **Always log ongoing work under `## [Unreleased]`**: During active development, place all `### Added`, `### Changed`, and `### Fixed` entries under `## [Unreleased]` at the top of `CHANGELOG.md`.
- **Never bump `VERSION` prematurely**: Keep `VERSION`, `pyproject.toml`, and `README.md` badges at the last published release on `origin`. Never append `(vX.Y.Z)` to ordinary work commits or chain `git push` by default.
- **Explicit Release Cuts (`/release`)**: Only promote `## [Unreleased]` $\rightarrow$ `## [X.Y.Z] - YYYY-MM-DD`, bump `VERSION`, and deliver a tag/push block when the user explicitly triggers `/release` (`skills/release/SKILL.md`).
- Explain how the user's experience or the system's external behavior changed.
- ✅ *Good*: "Profile section streamlined with real-time notification count."
- ❌ *Bad*: "Refactored ProfileService.get_stats() to use aggregate query and serializers."

---

## Part 2 — Knowledge Extraction & Architectural Integration from Raw Conversations

> **When to use**: Use this procedure when extracting deep architectural knowledge from raw planning conversations or AI chat logs (`input`/`output` transcripts) and integrating the findings into a project's reference and normative architecture documentation.

### The 3-Stage Extraction & Integration Pipeline

#### Stage 1 — Exhaustive Reference Extraction & Gap Analysis (`docs/reference/`)
1. **Sequential Segment Reading**: Read the raw conversation file in complete, non-overlapping line segments (never sample or skip middle sections) to extract 100% of domain insights, invariants, and architectural mechanisms.
2. **Structured Reference Corpus**: Synthesize the extracted concepts into structured reference documents under `docs/reference/<topic>.md` (`< 465` lines per file), updating `docs/README.md` and `README.md`.
3. **Fit & Gap Matrix**: Classify each extracted mechanism against the current architecture (`100% Aligned`, `Conceptual Enrichment`, or `Actionable Gap`) and present the gap analysis before modifying normative specs.

#### Stage 2 — Normative Architectural & Roadmap Integration (`docs/architecture/` & `roadmaps/`)
1. **Theoretical & Reference Foundations**: Add formal sections to the project's reference guides (`docs/reference/*.md`) and human workflow guides (`docs/guides/*.md`).
2. **Normative Specifications (`1:1:1`)**: Integrate the approved mechanisms, `1:1:1` (`Spec <-> Source <-> Unit Test`) tables, and glossary definitions into the authoritative architecture documents (`docs/architecture/*.md`).
3. **Roadmap Propagation**: Update pending roadmap files (`roadmaps/*.md`) so future implementation phases incorporate the newly formalized invariants.

#### Stage 3 — Raw Source Decommissioning (Zero-Residue)
- Once 100% of the extracted insights are verified in `docs/reference/` and `docs/architecture/`, **delete the temporary raw conversation file** so no unindexed chat dumps remain in the repository.
- Alternatively, when processing massive multi-file queues incrementally across multiple turns, apply **Destructive Queue Ingestion** (popping synthesized line ranges from the source file after each checkpoint until the file reaches `0 bytes` and is removed).

---

## Part 3 — 1-Hop Downward Directive & Task Delegation (`Root 0 -> Department -> Squad`)

> **When to use**: Use this procedure in `Root 0` (`corporate`), `domain-policy`, or `Department` (`department`) workspaces when an executive or domain decision requires a concrete action, policy alignment, or deliverable from an immediate 1-hop child layer (`layers/<child-id>` or sibling checkout).

### Delegation Mechanics (`make delegate` / `delegate-to-child`)

1. **Enforce the 1-Hop Horizon**:
   - `Root 0` (`corporate`) delegates exclusively to its immediate child `Department` / `domain-policy` layers.
   - `Department` (`department`) delegates exclusively to its immediate child `Squad` layers.
   - Never bypass an intermediate layer to inject tasks 2 hops down.
2. **Execute Deterministic CLI Delegation**:
   - From a layer workspace with a generated `Makefile`:
     ```bash
     make delegate CHILD=<child-layer-id> TASK="<clear actionable directive>" [PRIORITY=P0|P1|P2]
     ```
   - Or directly via `layer-config.sh`:
     ```bash
     ./scripts/layer-config.sh delegate-to-child [<workspace-dir>] --to-child <child-layer-id> --task "<directive>" [--priority P0|P1|P2] [--tracker WORKTASK.md|BACKLOG.md|WORKROAD.md]
     ```
3. **Traceable Attribution & Sync**:
   - The command verifies caller authority (`verify_layer_operation_authority` for `delegate-to-child`) and appends a traceable entry (`- [ ] **[P1 · Delegated from '<parent-id>' ('<role>', 'precedence: <N>')]**: <directive>`) to the child layer's tracker.
   - When the child layer opens its next session (`/sopen`), `make status` surfaces the delegated directive immediately in `priority_state`.
