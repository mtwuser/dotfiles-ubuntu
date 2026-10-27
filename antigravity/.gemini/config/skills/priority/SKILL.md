---
name: priority
description: standard prioritization for picking up next work items
---

# Work Prioritization — Agent Execution Rules

> **Always follow this exact priority chain when deciding what to work on next.**
> Do NOT ask the user — follow the chain and act.

## Priority Chain

```
Task Tracker (WORKTASK.md) → Active Roadmap / Backlog (WORKROAD.md / BACKLOG.md) → roadmaps/
```

All work plans and tasks are centralized at the repository root.

## Rules

1. **Task tracker first** — in-progress (`[/]`) and pending (`[ ]`) tasks promoted from the active roadmap/backlog
2. **Within the task tracker**, follow top-to-bottom priority order (`P0` before `P1`)
3. **Never ask** "where do you want to continue?" — the chain answers that

## Naming Convention

- **Active Roadmap / Backlog** items use roadmap/phase prefixes (`R1`, `RV2.1`, `RG.1`, etc.)
- **Task tracker** items use prefix `T` (`T1`, `T2`, `T3`…)
- When promoting to `WORKTASK.md`, assign the next available `T` number

## Promotion Mechanics

### 1. Future Roadmap (`roadmaps/`) → Active Roadmap (`WORKROAD.md`)

When `WORKROAD.md` has no pending items for the current stage, or when a new roadmap is scheduled:

1. **Identify** the next future roadmap in `roadmaps/` by priority
2. **Deep-analysis (Phase 0.5)** — before promoting:
   - Codebase audit → already-implemented detection → implementation strategy → added-value discovery
3. **Present analysis** to the user for review
4. **Enrich** the roadmap file in `roadmaps/` and add its phase checklist into `WORKROAD.md`
5. **Keep the source file in `roadmaps/`** while its phases are pending — it serves as the detailed technical specification until all phases are implemented (at which point it is deleted or archived to `docs/history/`)

### 2. Active Roadmap (`WORKROAD.md`) → Task Tracker (`WORKTASK.md`) (phase by phase)

When starting work on the next phase in `WORKROAD.md`:

> [!IMPORTANT]
> **Granular promotion**: Promote individual phases/blocks one at a time, not the entire roadmap at once.
> `WORKROAD.md` retains the strategic picture; `WORKTASK.md` holds only the active tactical phase.

1. **Identify** the next pending phase/block within `WORKROAD.md`
2. **Execute Promotion Analysis Checklist** — mandatory research:
   - Phase 1: Technical documentation (feature docs, architecture specs, source file in `roadmaps/`)
   - Phase 2: Existing code & precedent analysis
   - Phase 3: Testing structure audit (read testing rules, audit existing tests, plan by tier)
   - Phase 4: Naming & conventions
   - Phase 5: Documentation persistence
3. **Cross-task analysis** — if `WORKTASK.md` already has active items:
   - Scan active tasks → detect relationships → analyze dependencies → present brief report
4. **Move** only that phase into `WORKTASK.md` as a `T` item (`T1`, `T2`, etc.)
5. **Mark** the promoted phase in `WORKROAD.md` as `→ promoted to TN`

### 3. Completion (`WORKTASK.md` → `CHANGELOG.md`)

When a `WORKTASK.md` block is fully completed (all sub-items `[x]`):

1. **Write** the `CHANGELOG.md` entry under `[Unreleased]` (concise, user-facing language)
2. **Update `docs/`** — ensure all new/modified capabilities are documented in permanent architecture/reference docs
3. **Delete** the completed block from `WORKTASK.md` entirely
4. **Delete** the completed phase from `WORKROAD.md` / `BACKLOG.md` and from the source roadmap in `roadmaps/` (if all phases of that roadmap are complete, delete the file from `roadmaps/` or archive it to `docs/history/`)
5. **Promote** the next phase (repeat cycle)

> [!CAUTION]
> **Zero-clutter invariant**: Every document contains ONLY its designated content.
> No completed items in `WORKTASK.md` or `WORKROAD.md`. No `~~strikethrough~~` or `✅ Done` residuals.
> `CHANGELOG.md` (and `docs/history/` for archived milestone roadmaps) is the single record of completed work.
