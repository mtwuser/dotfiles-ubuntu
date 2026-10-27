---
name: start
description: {PROJECT_NAME}-specific governance, architecture reference, and smart start sequence — run at the beginning of every session
---
# Start — {PROJECT_NAME}

## Purpose

This skill fires at the beginning of every session. It establishes context
and identifies the next work item.

## Startup Sequence

### 1. Read active state
```
Read: WORKTASK.md             → Current in-progress items
Read: WORKROAD.md             → Next pending items
Read: CHANGELOG.md            → Recent completed work
Read: BACKLOG.md              → Pending tech debt observations
Read: WORKVALI.md             → Pending manual validations
Read: .agents/SESSION.md      → Previous session context (if any)
```

### 2. Identify next work item (Priority Chain)
1. `WORKTASK.md` — in-progress items first
2. `WORKROAD.md` — next pending phase items
3. `roadmaps/` — long-term planning

### 3. Report to user
Summarize: what was last done, what is next, any blockers.

---

## Architecture Quick Reference

### {PROJECT_NAME} Layers

| Layer | Name | Purpose |
|:-----:|------|---------|
| L0 | Data Schema | Semantic types, domain primitives, wire↔domain mapping |
| L1 | Domain | Hexagonal DDD, bounded contexts, ports/adapters |
| L2 | Processing | Async Continuum (5 tiers: asyncio → Celery Canvas) |
| L3 | Presentation | Zone Architecture (Z1–Z4: HTML → HTMX → Islands → Dedicated) |
| L4 | Communication | HTTP, SSE, WebSocket, Polling |

### Bounded Context Structure

```
src/{context}/
├── domain/          # Inner hexagon (zero I/O)
├── application/     # Use cases (orchestration)
├── infrastructure/  # Outer hexagon (FastAPI, SQLAlchemy, Jinja2)
└── tests/           # unit/ + imp/
```

### Key Documentation

| Document | Content |
|----------|---------|
| `ARCHITECTURE.md` | High-level system architecture and bounded contexts |
| `docs/architecture/` | Technical specifications per layer and domain |
| `README.md` | Project setup, directory structure, and quickstart |

### Smart Commands

| Action | Command |
|--------|---------|
| Run backend dev | `cd backend && source ./venv/bin/activate && uvicorn main:app --reload` |
| Run tests | `cd backend && source ./venv/bin/activate && python -m pytest --tb=short -q` |
| Run coverage | `cd backend && source ./venv/bin/activate && make test-all` |
| Type check | `cd backend && source ./venv/bin/activate && mypy --strict src/` |
| Lint check | `cd backend && source ./venv/bin/activate && ruff check .` |
| Auto-format | `cd backend && source ./venv/bin/activate && ruff format .` |
| Alembic migrate | `cd backend && source ./venv/bin/activate && alembic upgrade head` |
| Alembic autogen | `cd backend && source ./venv/bin/activate && alembic revision --autogenerate -m "desc"` |

---

## Governance Rules

### Commit Discipline
1. **NEVER auto-run** `git add`, `git commit`, `git push`
2. **ONE commit per repo** — never split
3. **Conventional commits**: `feat:`, `fix:`, `chore:`, `refactor:`, `test:`, `docs:`
4. **Independent repos** — each repo gets its own commit block
5. **WORKTASK sync is MANDATORY** before ANY commit

### Lifecycle Tiers
- Pending work ONLY: `roadmaps/` → `WORKROAD.md` → `WORKTASK.md`
- Completed work ONLY: `CHANGELOG.md`
- Manual validation: `WORKVALI.md` (parallel, continuous)
- Tech debt capture: `BACKLOG.md` (persistent)

### Mode Discipline
> **"Capture, don't act."** Observations go to `BACKLOG.md`, not inline fixes.

### Agent Rules Reference
| Rule | Content |
|------|---------|
| `coding.md` | Hexagonal architecture, zones, async, quality standards |
| `governance.md` | Work lifecycle, mode discipline, documentation convention |
| `testing.md` | Test tiers, FastAPI patterns, coverage gate |
| `environment.md` | Workspace layout, venv, commands |

### Full-Stack Analysis
When scoping changes, analyze ALL relevant layers (backend + frontend).
"Not built" only when ALL layers lack it.
