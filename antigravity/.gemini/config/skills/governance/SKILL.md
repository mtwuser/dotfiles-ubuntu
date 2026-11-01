---
name: governance
description: "Use when promoting work between tiers (roadmaps → active → done), writing CHANGELOG entries, or extracting architectural knowledge from raw conversation files."
---

# Governance Skill

## Part 1 — Promotion Flow and Changelog

> **When to use**: Use this skill when moving items between work tiers (`roadmaps/`, active backlog, task tracker), or when completing a feature and writing the `CHANGELOG.md`.

### Promotion Flow

Work flows strictly from left to right:
`roadmaps/ → WORKROAD.md (or ROADMAP.md) / BACKLOG.md → WORKTASK.md → CHANGELOG.md`

#### 1. Future Roadmap (`roadmaps/`) → Active Roadmap (`WORKROAD.md` / `ROADMAP.md`)
- Select the next roadmap by priority number.
- Execute **deep-analysis** before promotion (`1. Guides/Specs -> 2. Tests [E2E -> Imp -> Unit] -> 3. Code`): audit existing specs, tests, and code, detect already-implemented items, and identify synergies.
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
