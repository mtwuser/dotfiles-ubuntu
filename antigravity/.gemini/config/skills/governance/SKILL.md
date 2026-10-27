---
name: governance
description: "Use when promoting work between tiers (roadmaps → active → done), writing CHANGELOG entries, or extracting architectural knowledge from raw conversation files."
---

# Governance Skill

## Part 1 — Promotion Flow and Changelog

> **When to use**: Use this skill when moving items between work tiers (`roadmaps/`, active backlog, task tracker), or when completing a feature and writing the `CHANGELOG.md`.

### Promotion Flow

Work flows strictly from left to right:
`roadmaps/ → backlog → active tasks → CHANGELOG.md`

#### 1. Roadmap → Backlog
- Select the next roadmap by priority number.
- Execute **deep-analysis** before promotion: audit existing code, detect already-implemented items, identify synergies.
- Enrich the roadmap with your findings, then promote it to the active backlog.

#### 2. Backlog → Active Tasks
- Promote one phase at a time.
- If the task tracker already has items, run cross-task analysis first to detect dependencies and shared components.
- Move the phase to active tasks, renaming the prefix as needed (e.g. `R1` to `T1`).

#### 3. Active Tasks → Done
- Completed items are DELETED from the task tracker and backlog. Do not leave them as strikethrough (`~~`) or checkmarks.
- Log completed work exclusively in `CHANGELOG.md`.

### Mode Discipline ("Capture, don't act")

When working on a specific task, you might spot unrelated improvements:
1. **Capture**: Add a one-line observation to `BACKLOG.md`.
2. **Continue**: Return to your current task immediately.
3. **Never mix modes**: E.g., do not refactor an unrelated file while writing tests for a new feature.

### CHANGELOG Entries

Always write for the **USER**, not the developer.
- **No file names**, **no function names**, **no implementation details**.
- Explain how the user's experience or the system's external behavior changed.
- ✅ *Good*: "Profile section streamlined with real-time notification count."
- ❌ *Bad*: "Refactored ProfileService.get_stats() to use aggregate query and serializers."

---

## Part 2 — Knowledge Extraction & Architectural Integration from Raw Conversations

> **When to use**: Use this procedure when extracting deep architectural knowledge from raw planning conversations or AI chat logs (`input`/`output` transcripts) and integrating the findings into a project's reference and normative architecture documentation.

### The 3-Stage Extraction & Integration Pipeline

#### Stage 1 — Exhaustive Reference Extraction & Gap Analysis (`docs/reference/`)
1. **Sequential Segment Reading**: Read the raw conversation file in complete, non-overlapping line segments (never sample or skip middle sections) to extract 100% of domain insights, mathematical laws, and architectural mechanisms.
2. **Structured Reference Corpus**: Synthesize the extracted concepts into structured reference documents (e.g., `docs/reference/isomorphic_extraction/NN_<topic>.md`), updating the corpus index (`README.md` / `README_es.md`) and master synthesis.
3. **Fit & Gap Matrix**: Classify each extracted mechanism against the current architecture (`100% Aligned`, `Conceptual Enrichment`, or `Actionable Gap`) and present the gap analysis before modifying normative specs.

#### Stage 2 — Normative Architectural & Roadmap Integration (`docs/architecture/` & `roadmaps/`)
1. **Theoretical Foundations**: Add formal mathematical/theoretical sections to the project's foundation reference (e.g., `docs/reference/biotech_foundations*.md`) with full bilingual parity.
2. **Normative Specifications**: Integrate the approved mechanisms and glossary definitions into the authoritative architecture documents (`docs/architecture/01`–`04`, ES and EN).
3. **Roadmap Propagation**: Update pending roadmap files (`roadmaps/*.md`) so future implementation phases incorporate the newly formalized invariants.

#### Stage 3 — Raw Source Decommissioning (Zero-Residue)
- Once 100% of the extracted insights are verified in `docs/reference/` and `docs/architecture/`, **delete the temporary raw conversation file** so no unindexed chat dumps remain in the repository.
- Alternatively, when processing massive multi-file queues incrementally across multiple turns, apply **Destructive Queue Ingestion** (popping synthesized line ranges from the source file after each checkpoint until the file reaches `0 bytes` and is removed).
