---
description: >-
  MUST activate when working on WORKTASK.md, WORKROAD.md, WORKVALI.md,
  BACKLOG.md, CHANGELOG.md, roadmaps/, or any governance, promotion, or
  migration task in {PROJECT_NAME}.
trigger: model_decision
---
# Governance Rules — {PROJECT_NAME}

## Work Lifecycle — roadmaps/ → WORKROAD → WORKTASK → CHANGELOG

> **Every piece of work flows in one direction. No exceptions. No residuals.**

```
roadmaps/ (future) → WORKROAD.md (active plan) → WORKTASK.md (active work) → CHANGELOG.md (done)
                                    ↕                      ↕
                                WORKVALI.md              (manual validation, continuous)
```

### Phase 0: Conceptualize
When a new need is identified:
1. **Check** existing docs — does this extend an existing feature or is it new?
2. **Create or update** a roadmap in `roadmaps/` with the technical plan
3. **Add** to `WORKROAD.md` when ready to schedule

### Phase 0.5: Roadmap Deep-Analysis (before promotion)
> Every roadmap must pass through deep-analysis before moving to WORKROAD.md.

1. **Codebase audit** — scan existing bounded contexts for partial implementations
2. **Already-implemented detection** — flag items fully or partially done
3. **Implementation strategy** — identify best approach given existing infrastructure
4. **Added-value discovery** — identify synergies, edge cases, low-effort enrichments
5. **Present analysis to user** — structured report before moving anything

### Phase 1: Promote (WORKROAD → WORKTASK — phase by phase)
> WORKROAD.md is the strategic plan; WORKTASK.md is tactical execution.
> Promote individual phases, not the entire WORKROAD block at once.

1. **Identify** the next phase/block within the WORKROAD item
2. **Execute Cross-Task Analysis** if WORKTASK.md already has items
3. **Move** only that phase into `WORKTASK.md` as a `T` item
4. **Rename** from `R` prefix to next available `T` number
5. **Mark** the promoted phase in WORKROAD.md as "→ promoted to T*N*"

### Phase 1.5: Cross-Task Analysis
When WORKTASK.md **already has items**, execute before promoting:
1. **Scan active tasks** — read all `[/]` and `[ ]` items
2. **Relationship detection** — shared services, schemas, components
3. **Dependency analysis** — should incoming phase wait for active work?
4. **Present findings** — brief report to user before promoting

### Phase 2: Track (work in WORKTASK)
- `WORKTASK.md` is the **single source of truth** for in-progress work
- Use `[ ]`, `[/]`, `[x]` checkboxes for granular tracking
- When a sub-phase is fully `[x]`: collapse to summary, proceed immediately

### Phase 2.5: Documentation Persistence
> **Document while you build, not after.**

Documentation is mandatory at every lifecycle stage:
- During analysis: document planned capabilities and architectural decisions
- During implementation: update incrementally as you build
- After completion: verify completeness before CHANGELOG entry

### Phase 3: Complete (WORKTASK → CHANGELOG)
When a WORKTASK block is fully done:
1. **Write** the CHANGELOG entry in `[Unreleased]` (user-facing language)
2. **Delete** the completed block from `WORKTASK.md` entirely
3. **Promote** the next item

### Parallel: Manual Validation (WORKVALI.md)
Runs parallel to the main pipeline. Validation items accumulate from releases, features, and discoveries. Executed while developing other tasks.

## Mode Discipline

> **"Capture, don't act."** When working on a task, stay focused on that task.

During any work session, you will spot improvement opportunities. **Do not act on them during your current task.** Instead:

1. **Capture** → add a one-line observation to `BACKLOG.md`
2. **Continue** → return to your current task without context-switching
3. **Promote** → address items in dedicated sessions, promoted to WORKTASK.md when ready

| Mode | Focus | Observations go to |
|------|-------|-----|
| Testing | Writing/fixing tests | `BACKLOG.md` |
| Implementing | Building features | `BACKLOG.md` |
| Refactoring | Structural improvements (dedicated session) | Execute directly |

## The Golden Rule

> **Before writing any code, understand what already exists.**

Every implementation begins with an infrastructure audit:
- Map the concept to existing bounded contexts and services
- Trace the full execution chain from trigger → use case → domain service → adapter
- Identify where the system already solves this problem (even partially)
- If an existing service handles the domain, **extend it**. Do not bypass it.

## Documentation Convention

| Location | Content |
|---|---|
| **Root** | Governance: WORKTASK, WORKROAD, WORKVALI, BACKLOG, CHANGELOG |
| **`docs/`** | Architecture and technical documentation (permanent) |
| **`docs/reference/`** | Research, analysis, and source material (reference) |
| **`roadmaps/`** | Future planned roadmaps |
| **`.agents/`** | AI agent rules and skills |

### Documentation Invariants

| Document | Contains ONLY |
|----------|--------------|
| `roadmaps/` | Future planned work |
| `BACKLOG.md` | Persistent maintenance debt observations |
| `WORKROAD.md` | Active planned work (current cycle) |
| `WORKTASK.md` | Active/in-progress work |
| `WORKVALI.md` | Manual validation items |
| `CHANGELOG.md` | Completed work (user-facing) |

> **Zero-clutter invariant**: Each document contains ONLY its designated content.
> No completed items anywhere except CHANGELOG. Promoted items are deleted from source.

## Lifecycle Tiers
Pending work ONLY: `roadmaps/` → `WORKROAD.md` → `WORKTASK.md`.
Completed work ONLY: `CHANGELOG.md`.

## Migration Policy — HANDS OFF
- NEVER write/modify/run Alembic migration files manually.
- The user handles ALL migrations interactively.

## Priority Chain
When deciding what to work on next:
1. `WORKTASK.md` (in-progress items first)
2. `WORKROAD.md`
3. `roadmaps/`
NEVER suggest ad-hoc work from memory.

## Cognitive & Agent Governance (DNA)
- **Epigenetic Context Cap (`0-byte` `__init__.py`)**: All `__init__.py` files in consumer `src/` and `tests/` MUST remain completely empty (`0 bytes`). Bounded context metadata and `exclude_contexts` belong in declarative manifest configuration (`osa-manifest.yaml`).
- **Asymmetric Context Routing (4-Channel Subagent Digest)**: When delegating research or scanning tasks to subagents, require a 4-channel digest (`Domain State`, `Affected Port/Contract`, `Invariants & Constraints`, `Actionable Delta`) instead of raw file dumps.
- **Pre-Debug Diagnostic Sweep**: Before deep-debugging runtime errors (422s, DI failures) or import anomalies, run `make doctor` / `osa doctor --clean-cache` first.
