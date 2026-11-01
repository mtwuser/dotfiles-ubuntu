---
name: priority
description: standard prioritization for picking up next work items
---

# Work Prioritization — Agent Execution Rules

> **Always follow this exact priority chain when deciding what to work on next.**
> Do NOT ask the user — follow the chain and act.

## Priority Chain

```
Task Tracker (WORKTASK.md) → Active Roadmap / Backlog (WORKROAD.md / ROADMAP.md / BACKLOG.md) → roadmaps/
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

1. **Identify** the next pending phase/block within `WORKROAD.md` (or `ROADMAP.md` / `BACKLOG.md`)
2. **Execute Promotion Analysis Checklist (Mode-Aware Reading Priority)** — mandatory research in strict top-down order based on `workspace_mode` (`make status` / `.agents/rules/*.md`):
   - **In `technical` or `hybrid` mode (`technical-base` / `tech-stack/*`)**:
     - Phase 1: Human guides & normative specifications (`docs/guides/`, `docs/architecture/<spec>.md` `1:1:1` tables, and source file in `roadmaps/`)
     - Phase 2: Self-documenting test hierarchy (`tests/e2e/` persona journeys $\rightarrow$ `tests/imp/` boundary implementation $\rightarrow$ `tests/unit/` 4-quadrant `Test<Module>` suites)
     - Phase 3: Existing source code, staleness (`> 90d`), & consistency analysis (`src/` / `scripts/` — verify new code does not diverge from adjacent existing code; propose atomic refactoring or log in `BACKLOG.md` if touched modules use older idioms or over-compression)
     - Phase 4: Structural evolution (`Inline -> Function -> Class -> Protocol/Catalog -> Module`), file-prefix/suffix naming (`tools_*`, `*_engine`, `NN_*`, `test_*`), & outbound non-restriction alignment
     - Phase 5: Documentation & `1:1:1` traceability persistence plan
   - **In `business` mode (`business-base` / `business-stack/*` / `Root 0` / `Department`)**:
     - Phase 1: Normative policies, *Lex Superior* hierarchy (`0..100`), and cross-departmental precedence (`5..35`) in `corporate/`, `docs/`, and `.agents/rules/*.md`
     - Phase 2: Single Source of Truth ledgers (`corporate/`), quantitative/unit precision, and Traceable Ledger IDs (`[DEPT]-[TYPE]-[YYYY]-[NNN]`)
     - Phase 3: Three-Part Functional Verification Structure (`# Scope & Surface Target`, `# Normative Invariants`, `# Verification & Sign-Off Gates`) and IP/confidentiality firewall gates
     - Phase 4: Cross-Surface Cascade (`surfaces/web/`, `surfaces/forms/`, `surfaces/print/`) and 1-hop child delegation needs (`make delegate`)
3. **Cross-task analysis** — if `WORKTASK.md` already has active items:
   - Scan active tasks → detect relationships → analyze dependencies → present brief report
4. **Move** only that phase into `WORKTASK.md` as a `T` item (`T1`, `T2`, etc.)
5. **Mark** the promoted phase in `WORKROAD.md` as `→ promoted to TN`
6. **Claim & Start the Task (`make task`)**: Run `./scripts/layer-config.sh start-task . --task "<id-or-text>" [--ticket <TICKET-ID>]` (or `make task TASK="<id-or-text>" [TICKET=<TICKET-ID>]`) to mark the item `[/]` in `WORKTASK.md`, record the active task, `Ticket ID`, `Origin Layer`, and branch in `.agents/SESSION.md`, and emit the canonical Git branch command (`git checkout -b feature/<TICKET-ID>-<slug>` when a ticket ID is present, or `git checkout -b task/<slug>`).

### 3. Completion (`WORKTASK.md` → `make complete` → `CHANGELOG.md`)

When a `WORKTASK.md` block is fully completed (all sub-items `[x]`):

1. **Send Reciprocal Upward Completion Receipt (`make complete`, when delegated or ticketed)**: Run `./scripts/layer-config.sh complete-task . --task "<id-or-text>" [--deliverable <rel-path>]` (or `make complete TASK="<id-or-text>" [DELIVERABLE=<rel-path>]`) so the parent layer's `WORKTASK.md` (`## Outbound Delegations`) is reciprocally updated to `stage: completed (pro)` (or a non-destructive completion receipt `.agents/proposals/to-<parent>/completion-<ticket>.md` + PR plan is staged) before removing the local item.
2. **Write** the `CHANGELOG.md` entry under `[Unreleased]` (concise, user-facing language)
3. **Update `docs/`** — ensure all new/modified capabilities are documented in permanent architecture/reference docs
4. **Delete** the completed block from `WORKTASK.md` entirely
5. **Delete** the completed phase from `WORKROAD.md` / `BACKLOG.md` and from the source roadmap in `roadmaps/` (if all phases of that roadmap are complete, delete the file from `roadmaps/` or archive it to `docs/history/`)
6. **Promote** the next phase (repeat cycle)

> [!CAUTION]
> **Zero-clutter invariant**: Every document contains ONLY its designated content.
> No completed items in `WORKTASK.md` or `WORKROAD.md`. No `~~strikethrough~~` or `✅ Done` residuals.
> `CHANGELOG.md` (and `docs/history/` for archived milestone roadmaps) is the single record of completed work.
