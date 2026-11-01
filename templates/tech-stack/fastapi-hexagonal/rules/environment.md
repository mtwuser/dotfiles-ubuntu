---
trigger: always_on
description: Project paths, workspace structure, and command execution for {PROJECT_NAME}
---
# Environment Rules — {PROJECT_NAME}

## Workspace Layout

```
{PROJECT_PATH}/                        ← Project root (governance + hexagonal contexts)
├── src/{context}/                     ← Hexagonal bounded contexts (domain, application, infrastructure)
├── tests/                             ← Global test suites (or src/{context}/tests/{unit,imp}/)
├── venv/                              ← Python >= 3.14 virtualenv (or backend/venv/ in multi-repo setups)
├── docs/                              ← 3-tier documentation (guides/, architecture/, reference/)
├── roadmaps/                          ← Domain roadmaps
├── .agents/                           ← Workspace rules, skills, LAYER_LINEAGE.md, SESSION.md
├── Makefile                           ← Standard verification & layer-sync targets (make verify, make test-unit)
├── WORKTASK.md / WORKROAD.md / WORKVALI.md / BACKLOG.md / CHANGELOG.md
└── .gitignore
```

> [!NOTE]
> If your project splits `backend/` and `frontend/` into nested subdirectories or sub-repos, place the virtualenv at `{PROJECT_PATH}/backend/venv` (supported automatically by workstation lifecycle hooks).

## Tech Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| **Backend** | Python >= 3.14 (FastAPI) | Hexagonal architecture (ports/adapters), PEP 695 generics, `StrEnum` |
| **Frontend** | Server HTML + HTMX + Islands | Zone Architecture: Z1 (static), Z2 (HTMX), Z3 (Preact/Vue islands), Z4 (dedicated libs) |
| **Async** | Celery / FastAPI BackgroundTasks | Async Continuum Tiers 1-5 |
| **Database** | PostgreSQL | Primary persistence |
| **Templates** | Jinja2 | Server-side rendering for Z1/Z2 |
| **Streaming** | SSE (sse-starlette) | Real-time communication for Z3 |

## Virtual Environment

- **Python requirement**: Python >= 3.14
- **Path**: `./venv/bin/activate` (or `./backend/venv/bin/activate` in nested `backend/` layouts)
- **Absolute**: `{PROJECT_PATH}/venv/bin/activate`
- **ALWAYS activate before ANY Python/FastAPI command**:
  ```bash
  cd {PROJECT_PATH} && source ./venv/bin/activate && <command>
  ```
- Never use system Python. Never use `python3` without activating venv first.

## Project & Backend Commands

All commands run from the project root (or `backend/` if using a nested `backend/` directory) with venv activated:

| Action | Command |
|--------|---------|
| Run dev server | `source ./venv/bin/activate && uvicorn main:app --reload` |
| Run unit tests | `source ./venv/bin/activate && make test-unit` |
| Run context tests | `source ./venv/bin/activate && python -m pytest src/{context}/tests/ --tb=short -q` |
| Coverage all | `source ./venv/bin/activate && make test-all` |
| Type check | `source ./venv/bin/activate && mypy --strict src/` |
| Lint check | `source ./venv/bin/activate && ruff check .` |
| Auto-format | `source ./venv/bin/activate && ruff format .` |

## Frontend Commands (once scaffolded)

Frontend is zero-build by design. No `npm install`, no webpack, no Vite.
Static assets are served directly. Vendor libraries are committed as single files.

## Command Execution Safety

- **NEVER auto-run** `git`, `rm -rf`, or destructive commands
- Commands that only READ (grep, ls, cat, pytest) are safe to auto-run
- Always use `--tb=short -q` for pytest to keep output manageable
- Always `| tail -N` for long-output commands
