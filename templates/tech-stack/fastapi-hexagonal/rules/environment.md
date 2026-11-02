---
trigger: always_on
description: "{PROJECT_NAME} Python virtual environment, FastAPI/Uvicorn, Pytest, Mypy, Ruff, and user-gated Alembic workflow."
---

# {PROJECT_NAME} — Environment & Tooling Rules (`fastapi-hexagonal`)

---

## 1. Python Virtual Environment (`./venv`)

All Python, FastAPI, test, and linter commands MUST run inside the project virtual environment:

```bash
source ./venv/bin/activate && <command>
```

Never install packages globally or run system `pytest` / `mypy` / `ruff` outside `./venv`.

---

## 2. Canonical Development & Verification Commands

| Task | Command |
|------|---------|
| **Run FastAPI dev server** | `source ./venv/bin/activate && uvicorn main:app --reload` |
| **Run isolated unit tests** | `source ./venv/bin/activate && pytest src/ tests/unit/ -v` |
| **Run 100% coverage gate** | `source ./venv/bin/activate && pytest --cov=src --cov-branch --cov-fail-under=100` |
| **Run implementation tests (`imp`)** | `source ./venv/bin/activate && pytest src/*/tests/imp/ tests/imp/ -v` |
| **Strict type checking** | `source ./venv/bin/activate && mypy --strict src/` |
| **Linter & import sorting** | `source ./venv/bin/activate && ruff check .` |
| **Auto-format** | `source ./venv/bin/activate && ruff format .` |

---

## 3. Zero-Touch Alembic Migration Gate (`pre_tool_guard.py`)

Database schema migrations are **strictly human-operated** (enforced by workstation `pre_tool_guard.py`):

1. **Agent Responsibility**: Create or update SQLAlchemy 2.0 `Mapped[...]` models in `src/<context>/infrastructure/persistence/models.py` and register them in `alembic/env.py` metadata.
2. **Forbidden for Agent**: NEVER run `alembic revision`, `alembic upgrade`, `alembic downgrade`, or create/edit files inside `alembic/versions/*.py`.
3. **Human Handoff**: Provide the exact commands for the user to run in their terminal:
   ```bash
   source ./venv/bin/activate && alembic revision --autogenerate -m "<concise_schema_change>"
   source ./venv/bin/activate && alembic upgrade head
   ```
