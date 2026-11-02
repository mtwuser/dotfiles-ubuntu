# Project Template: FastAPI + Hexagonal DDD (`fastapi-hexagonal`)

Ready-to-apply **Layer 2/3 Tech-Stack Template Pack** (`kind: "tech-stack"`, `extends: "technical-base"`) for Python **FastAPI + Hexagonal Architecture (Domain-Driven Design / Ports & Adapters)** projects.

> **Clean Inheritance Design**:
> - Universal workflow, commit discipline, and `< 465`-line modularity come from **`human-core`** (`~/.gemini/config/AGENTS.md`).
> - Stack-general `1:1:1` traceability (`Spec <-> Test <-> Code`), `AAA` testing, `100%` branch coverage, and `0-byte __init__.py` rules come automatically from **`technical-base`** (`extends: "technical-base"`).
> - This pack focuses **exclusively** on **pure, idiomatic FastAPI + Hexagonal DDD architecture** (Bounded Contexts, `typing.Protocol` ports, constructor-injected use cases, SQLAlchemy Async + Alembic zero-touch safety, Pydantic v2 DTO boundaries, `httpx.AsyncClient` + `ASGITransport` + `app.dependency_overrides`, and optional standard Jinja2/HTMX server-rendered views). Higher-level application frameworks can extend `fastapi-hexagonal` cleanly without inheriting framework-coupled boilerplate.

---

## Quick Setup (Deterministic CLI)

```bash
# Materialize technical-base + fastapi-hexagonal into a target project
./scripts/layer-config.sh apply-project /path/to/your-project --template fastapi-hexagonal --layers all
```

Then replace `{PROJECT_NAME}` placeholders in `.agents/rules/` and `.agents/skills/` with your project name:

```bash
PROJECT_NAME="YourProject"
find /path/to/your-project/.agents -name "*.md" -exec sed -i "s/{PROJECT_NAME}/$PROJECT_NAME/g" {} +
```

---

## Template Pack Contents

### Rules (`.agents/rules/`)
| File | Scope (`fastapi-hexagonal` Delta over `technical-base`) |
|------|---------------------------------------------------------|
| `rules/coding.md` | Hexagonal Bounded Context structure (`domain/`, `application/`, `infrastructure/`), `Protocol` ports, FastAPI `Depends()` & `from __future__ import annotations` guard, Pydantic v2 boundaries, async I/O, and optional Jinja2/HTMX SSR |
| `rules/testing.md` | Hexagonal 4-layer testing matrix (`Domain` pure unit, `Application` mocked ports, `API Router` via `httpx.AsyncClient` + `ASGITransport` + `dependency_overrides`, `Repository` `tests/imp/` against real async DB) |
| `rules/environment.md` | Python `./venv` execution, `uvicorn`, `pytest`, `mypy --strict`, `ruff`, and user-gated `alembic` commands |
| `rules/governance.md` | Bounded Context `1:1:1` specification mapping (`docs/architecture/<context>.md` $\leftrightarrow$ `src/<context>/`) and hexagonal full-slice vertical delivery |

### Skills (`.agents/skills/`)
| File | Skill Name & Purpose |
|------|----------------------|
| `skills/start/SKILL.md` | `start` — Hexagonal bounded-context orientation and FastAPI command cheat-sheet |
| `skills/fastapi-testing/SKILL.md` | `fastapi-testing` — Concrete FastAPI + Hexagonal test recipes (coexists alongside `technical-base`'s `skills/testing/SKILL.md`) |
| `skills/database/SKILL.md` | `database-migrations` — SQLAlchemy 2.0 Async models, Domain $\leftrightarrow$ ORM mappers, and human-gated Alembic workflow |
| `skills/frontend/SKILL.md` | `frontend-patterns` — Standard FastAPI/Starlette `Jinja2Templates`, progressive HTMX partial rendering (`HX-Request`), and Web Components |

### Governance Ledgers (`governance/` $\rightarrow$ Project Root)
| File | Purpose |
|------|---------|
| `governance/WORKROAD.md` | Active release/milestone plan |
| `governance/WORKTASK.md` | Current in-progress vertical-slice tasks |
| `governance/BACKLOG.md` | Captured technical debt (`Capture, don't act`) |
| `governance/WORKVALI.md` | Manual QA & API/UI validation checklist |
| `governance/CHANGELOG.md` | Completed work history (`Keep a Changelog`) |
| `governance/SESSION.md` | `.agents/SESSION.md` cross-session handoff state |
