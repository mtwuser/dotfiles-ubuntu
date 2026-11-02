---
trigger: always_on
description: "{PROJECT_NAME} Bounded Context 1:1:1 specification mapping and full-vertical-slice hexagonal delivery rules."
---

# {PROJECT_NAME} — Hexagonal Architecture Governance (`fastapi-hexagonal`)

> Inherits universal work lifecycle (`roadmaps/ -> WORKROAD.md -> WORKTASK.md -> CHANGELOG.md` + `BACKLOG.md`), commit discipline, and `< 465`-line limits from `human-core` (`AGENTS.md`) and `technical-base.md`. This file defines how `1:1:1` traceability maps to **Hexagonal Bounded Contexts**.

---

## 1. Bounded Context `1:1:1` Traceability (`Spec <-> Context <-> Tests`)

Every Bounded Context `src/<context>/` maps `1:1:1` to an architectural specification in `docs/architecture/<context>.md`:

| Artifact | Canonical Path | Responsibility |
|----------|----------------|----------------|
| **Bounded Context Spec** | `docs/architecture/<context>.md` (`< 465` lines) | Defines domain invariants, ubiquitous language, inbound/outbound `Protocol` ports, API wire contracts, and the `1:1:1` traceability table |
| **Hexagonal Source** | `src/<context>/{domain,application,infrastructure}/` | Implements the context across `domain/` (pure logic + `ports.py`), `application/` (use cases), and `infrastructure/` (SQLAlchemy + FastAPI) |
| **Hexagonal Tests** | `src/<context>/tests/{unit,imp}/` | Verifies every executable module (`Test<ClassName>`) with `Specification: docs/architecture/<context>.md` in the module docstring |

---

## 2. Full Vertical-Slice Scoping Across the Hexagon

When planning, auditing, or delivering a feature inside `WORKTASK.md`:
1. **Inspect All Rings Before Declaring Status**: Check `domain/` (entities, value objects, `ports.py`), `application/` (use cases, DTOs), `infrastructure/persistence/` (SQLAlchemy models, repositories), `infrastructure/api/` (schemas, `dependencies.py`, `router.py`), and `tests/{unit,imp}/`.
2. **No Orphan Layers**: Never deliver a domain port without its application orchestration and test, or an API router endpoint that bypasses the application use case layer.
3. **Decommissioning Symmetry**: When removing an endpoint, use case, or bounded context, remove its DTOs/schemas, dependency provider, `1:1` unit/imp tests, and spec entry in the same atomic changeset.
