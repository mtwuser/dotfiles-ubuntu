---
name: start
description: {PROJECT_NAME} FastAPI + Hexagonal DDD architecture orientation and verification command reference
---
# Skill: FastAPI Hexagonal Orientation (`start`)

> Complements the global `/sopen` session-opening skill with **{PROJECT_NAME}**'s Hexagonal Bounded Context map and FastAPI verification commands.

---

## 1. Hexagonal Bounded Context Orientation

Before modifying any Bounded Context under `src/<context>/`, follow the `1:1:1` reading order (`technical-base.md` Rule 3):
1. **Bounded Context Spec**: `docs/architecture/<context>.md`
2. **Context Tests (`E2E -> Imp -> Unit`)**: `src/<context>/tests/imp/` $\rightarrow$ `src/<context>/tests/unit/`
3. **Hexagonal Rings (`Inner -> Outer`)**:
   ```text
   src/<context>/
   ├── domain/          # Inner hexagon: entities, value_objects, services, exceptions, ports (Protocol)
   ├── application/     # Use case ring: use_cases (constructor-injected ports), dto
   └── infrastructure/  # Outer hexagon: persistence (SQLAlchemy), api (FastAPI router/schemas/dependencies)
   ```

---

## 2. FastAPI + Hexagonal Invariant Checklist

- **Dependency Direction**: `infrastructure -> application -> domain` (`domain/` has zero I/O and zero FastAPI/SQLAlchemy/Pydantic imports).
- **Runtime Annotations**: Never put `from __future__ import annotations` in FastAPI `router.py` or `dependencies.py` modules.
- **Zero-Touch Migrations**: Never run `alembic` or edit `alembic/versions/*.py`; update SQLAlchemy models and hand the `alembic` commands to the user.

---

## 3. Canonical Commands (`./venv`)

| Action | Command |
|--------|---------|
| **Run dev server** | `source ./venv/bin/activate && uvicorn main:app --reload` |
| **Run unit tests** | `source ./venv/bin/activate && pytest src/ tests/unit/ -v` |
| **Run 100% coverage** | `source ./venv/bin/activate && pytest --cov=src --cov-branch --cov-fail-under=100` |
| **Run imp tests** | `source ./venv/bin/activate && pytest src/*/tests/imp/ tests/imp/ -v` |
| **Type check** | `source ./venv/bin/activate && mypy --strict src/` |
| **Lint & format** | `source ./venv/bin/activate && ruff check . && ruff format --check .` |
