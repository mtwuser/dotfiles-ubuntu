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

## Part 3 — Bidirectional 1-Hop Governance Delivery (`Root 0 <-> Department <-> Squad`)

> **When to use**: Use this procedure in `Root 0` (`corporate`), `domain-policy`, `Department` (`department`), or `Squad` (`squad`) workspaces to deliver directives, rules, roadmaps, validation checklists (`WORKVALI.md`), or corporate ledger artifacts 1 hop downward (`make delegate`) or propose them 1 hop upward via Pull Request (`make promote`).

### 1. Top-Down 1-Hop Delivery (`make delegate` / `delegate-to-child`)

1. **Enforce the 1-Hop Horizon**:
   - `Root 0` (`corporate`) delivers exclusively to its immediate child `Department` / `domain-policy` layers.
   - `Department` (`department`) delivers exclusively to its immediate child `Squad` layers.
   - Never bypass an intermediate layer to inject tasks 2 hops down.
2. **Supported Target Governance Surfaces (`SURFACE` / `--surface`)**:
   - **Trackers (`WORKTASK.md`, `BACKLOG.md`, `WORKROAD.md`, `ROADMAP.md`, `WORKVALI.md`)**: Appends a traceable entry (`- [ ] **[P1 · Delegated from '<parent-id>' ('<role>', 'precedence: <N>')]**: ...`) into the child's tracker.
   - **Roadmaps & Corporate Ledgers (`roadmaps`, `corporate`)**: Delivers `--source <rel-path>` into `<child>/roadmaps/<filename>` or `<child>/corporate/<filename>` with a provenance header (`> **Delivered from**: '<parent-id>'`).
   - **Normative Rules (`rules`)**: Delivers `--source <rel-path>` into `<child>/templates/<child-id>/rules/<filename>` and `<child>/.agents/rules/<filename>` with normalized Antigravity frontmatter.
3. **Execute Deterministic CLI Delivery**:
   - From a layer workspace with a generated `Makefile`:
     ```bash
     make delegate CHILD=<child-layer-id> [TASK="<directive>"] [SOURCE=<rel-path>] [SURFACE=WORKTASK.md|BACKLOG.md|WORKROAD.md|WORKVALI.md|roadmaps|rules|corporate] [PRIORITY=P0|P1|P2]
     ```
   - Or directly via `layer-config.sh`:
     ```bash
     ./scripts/layer-config.sh delegate-to-child [<workspace-dir>] --to-child <child-layer-id> [--task "<directive>"] [--source <rel-path>] [--surface <surface>] [--priority P0|P1|P2]
     ```

### 2. Bottom-Up 1-Hop Proposal via Pull Request (`make promote` / `promote-from-project --create-pr`)

- Any child layer (`Squad` -> `Department` -> `Root 0`) can escalate a rule (`.agents/rules/*.md`), skill, roadmap (`roadmaps/*.md`), corporate policy (`corporate/**`), doc (`docs/**`), or governance tracker proposal (`BACKLOG.md`, `WORKROAD.md`, `WORKVALI.md`) 1 hop upward via Pull Request:
  ```bash
  make promote SOURCE=<rel-path> [TEMPLATE=<pack>]
  ```
- The parent layer's owner (`layer_authority.owner_role`) reviews and validates the PR before merging it into the parent's governance flow.
