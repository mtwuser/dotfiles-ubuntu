---
trigger: always_on
description: Project paths, workspace structure, and command execution for {PROJECT_NAME}
---
# Environment Rules — {PROJECT_NAME}

## Workspace Layout

```
{PROJECT_PATH}/              ← Root repo (governance + docs)
├── backend/                           ← Backend (FastAPI, hexagonal)
│   └── venv/                          ← Python virtualenv
├── frontend/                          ← Frontend assets (HTMX, islands)
├── docs/                              ← Architecture docs
├── roadmaps/                          ← Domain roadmaps
├── .agents/                           ← Rules + skills
├── WORKTASK.md / WORKROAD.md / CHANGELOG.md
└── .gitignore
```

The repos (root, backend, frontend) will be **independent nested repos** once scaffolded. Currently only root exists.

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
- **Path**: `./venv/bin/activate` (relative to `backend/`)
- **Absolute**: `{PROJECT_PATH}/backend/venv/bin/activate`
- **ALWAYS activate before ANY backend command**:
  ```bash
  cd {PROJECT_PATH}/backend && source ./venv/bin/activate && <command>
  ```
- Never use system Python. Never use `python3` without activating venv first.

## Backend Commands (once scaffolded)

All backend commands MUST run from `backend/` with venv activated:

| Action | Command |
|--------|---------|
| Run dev server | `source ./venv/bin/activate && uvicorn main:app --reload` |
| Run tests | `source ./venv/bin/activate && python -m pytest --tb=short -q` |
| Run app tests | `source ./venv/bin/activate && python -m pytest {context}/tests/ --tb=short -q` |
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
