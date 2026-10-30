---
description: Hexagonal DDD architecture patterns and coding standards for {PROJECT_NAME}
trigger: always_on
---
# Coding Rules — {PROJECT_NAME}

## Hexagonal Architecture (Layer 1: Domain)

{PROJECT_NAME} uses **Hexagonal DDD** with Bounded Contexts as the unit of architecture.

### Structure per Bounded Context

```
src/{context}/
├── domain/                          # INNER HEXAGON — Zero I/O, zero framework
│   ├── __init__.py
│   ├── models.py                    # Pydantic domain entities
│   ├── enums.py                     # StrEnum definitions
│   ├── types.py                     # TypeAlias, TypeVar
│   ├── constants.py                 # Pure constants
│   ├── exceptions.py                # Domain-specific exceptions
│   ├── ports.py                     # Abstract interfaces (Protocol/ABC)
│   └── services/                    # Pure business logic (NO I/O)
│       └── {name}.py                # Max ~400 lines, single class
│
├── application/                     # USE CASES — Orchestrates domain + infra
│   ├── use_cases.py                 # Or split per action if > 400 lines
│   └── dto.py                       # Data Transfer Objects (optional)
│
├── infrastructure/                  # OUTER HEXAGON — All I/O, all framework
│   ├── persistence/                 # ORM models + repositories
│   │   ├── orm_models.py            # SQLAlchemy ORM
│   │   └── repositories.py         # Port implementations
│   ├── api/                         # JSON API (inbound adapter)
│   │   ├── router.py                # FastAPI router
│   │   ├── schemas.py               # Request/response schemas (Pydantic)
│   │   └── dependencies.py         # DI wiring
│   ├── web/                         # HTML presentation (inbound adapter)
│   │   ├── views.py                 # Routes returning respond_template / HTMLResponse
│   │   └── templates/{context}/     # Jinja2 templates
│   │       ├── list.html
│   │       ├── detail.html
│   │       └── partials/            # HTMX swap fragments
│   ├── adapters/                    # External service adapters (outbound)
│   │   └── {service}_adapter.py     # Implements domain ports
│   └── tasks/                       # Background task definitions
│       └── {task_group}.py          # Thin wrappers → use cases
│
└── tests/
    ├── unit/                        # 0 DB access, all deps mocked
    └── imp/                         # DB/integration verification only
```

### Layer Call Direction

```
INFRASTRUCTURE (API/Web/Tasks)  → Trigger layer (when)
APPLICATION (Use Cases)         → Orchestration layer (what)
DOMAIN (Services/Ports)         → Business logic layer (how)
INFRASTRUCTURE (Persistence)    → Adapter layer (I/O)
```

- **Dependency Rule**: Domain NEVER imports from Infrastructure or Application.
- **Port Purity**: Ports are abstract interfaces (Protocol/ABC) in `domain/ports.py`. Infrastructure implements them.
- **Service Purity**: Domain services have ZERO I/O. They receive data through method parameters, not by fetching it.
- **`__init__.py` Purity**: All `__init__.py` files in consumer `src/` and `tests/` MUST remain **100% empty (`0 bytes`)**. Never place variables, configuration, imports, docstrings, or logic inside `__init__.py`. Bounded context configuration and `exclude_contexts` live exclusively in `osa-manifest.yaml` (`domain.bounded_contexts`).

## Zone Architecture (Layer 3: Presentation)

| Zone | Interactivity | Client JS | Technology | Use Case |
|:----:|:-------------:|:---------:|-----------|----------|
| **Z1** | None | 0 KB | Server HTML (Jinja2) | Landing, docs, legal, static pages |
| **Z2** | Low-Medium | ~30 KB | HTMX + Alpine.js | CRUD, forms, tables, search, filters |
| **Z3** | High | ~35 KB/island | Preact/Vue Island + SSE | Chat, dashboards, streaming, timelines |
| **Z4** | Extreme | ~200+ KB | Dedicated library | 3D viewers, code editors, collaborative tools |

### Zone Rules

- **Z1 by default**: Every page starts as Z1 (server HTML). Promote only when justified.
- **HTMX fragments**: Z2 uses HTMX partial swaps via `partials/` templates. Never full page reloads for CRUD.
- **Islands are isolated**: Z3/Z4 components mount into `<div data-island="...">` containers. They do NOT control the page layout.
- **Zero-build**: No webpack, no Vite. Vendor libraries as single ES module files. CSS is vanilla.

### HTMX Response Safety Rules

| Rule | Enforcement |
|------|------------|
| `respond_template(partial=)` for Z2 | NEVER use raw `TemplateResponse()` — bypasses HTMX detection and channel headers |
| `respond_poll(done=)` for polling | Returns HTTP 286 to stop HTMX. NEVER return raw 200 for polled endpoints |
| List CRUD: full list partial + `innerHTML` | NEVER use `afterbegin`/`beforeend` on conditional containers |
| No manual `HX-Request` checks | Use `is_htmx_request()` or `respond_template(partial=)` |

## Async Continuum (Layer 2: Processing)

| Tier | Technology | Duration | Use Case |
|:----:|-----------|----------|----------|
| 1 | `await` (native asyncio) | < 200ms | DB queries, cache lookups |
| 2 | `FastAPI.BackgroundTasks` | < 30s | Email, notifications, light ML |
| 3 | SSE / WebSocket | Streaming | LLM streaming, live dashboards |
| 4 | Celery / Taskiq | > 30s | Simulations, batch processing |
| 5 | Celery Canvas / Prefect | Multi-step | ML training, CDC pipelines |

## Semantic Typing (Layer 0: Data Substrate)

Data types are NOT just wire types — they are **semantic types** from the Universal Type Ontology (UTO).

```python
# ❌ WRONG — Generic wire types
class User(BaseModel):
    name: str
    email: str

# ✅ CORRECT — Semantic types
from core.types import Identifier, NaturalText, EmailAddress

class User(BaseModel):
    name: NaturalText          # Implies: searchable, NLP-processable
    email: EmailAddress        # Implies: validatable, deliverable
    user_id: Identifier        # Implies: unique, hashable, URI-safe
```

## Manifest System (YAML-driven)

Application behavior is configured via `osa-manifest.yaml`, NOT hardcoded conditionals:

```yaml
# osa-manifest.yaml
project:
  name: my_app
  scale: medium
domain:
  bounded_contexts:
    - orders
    - payments
presentation:
  default_zone: Z1
processing:
  default_tier: T1
```

## Bounded Context Dependency Pipeline

**Dependency direction** (imports flow left → right, NEVER reverse):

```
core ← {domain contexts} ← shared_kernel
```

> [!IMPORTANT]
> The exact pipeline will be defined when the bounded contexts are created.
> The invariant is: **a context may only depend on contexts to its LEFT**.
> Cross-cutting concerns live in `core`. Shared domain types live in `shared_kernel`.

### Forbidden Import Patterns

```python
# ❌ FORBIDDEN — Domain importing from Infrastructure
from src.orders.infrastructure.persistence.orm_models import OrderORM

# ❌ FORBIDDEN — Context importing from a context to its RIGHT
from src.analytics.domain.models import AnalyticsEvent  # if analytics depends on orders

# ✅ CORRECT — Infrastructure importing from Domain
from src.orders.domain.models import Order
from src.orders.domain.ports import OrderRepository
```

## Code Quality Standards

### Clean Code Principles
- **Intention-revealing names**: Names must answer: _why does it exist?_, _what does it do?_, _how is it used?_
- **Small functions**: Functions do ONE thing at ONE level of abstraction. Target 5-15 lines.
- **Command-Query Separation (CQS)**: A method performs an action OR returns data, never both.
- **Boy Scout Rule**: Leave code better than you found it.
- **No dead code**: Remove unused functions, imports, and commented-out code immediately.

### SOLID in {PROJECT_NAME}
| Principle | {PROJECT_NAME} Application |
|-----------|----------------|
| **SRP** | Each service class has ONE reason to change. Split at ~400 lines. |
| **OCP** | Extend via new port implementations, not by modifying domain services. |
| **LSP** | All port implementations must be substitutable for their Protocol. |
| **ISP** | Ports define minimal interfaces. Split large protocols into focused ones. |
| **DIP** | Domain depends on Protocols. Infrastructure implements them. Never reverse. |

### Technical Standards
- **Strong typing**: Use `mypy --strict`. Prefer `Protocol` over ABC. No `Any`.
- **Pydantic models**: Domain entities are Pydantic `BaseModel`. Infrastructure ORM is SQLAlchemy.
- **Max file size**: Strictly `< 465` lines per source, test, and `docs/**/*.md` file (target `<= 400` lines). Split when exceeded.
- **Naming**: Descriptive names. No single-letter variables in business logic. Classes as nouns, methods as verbs.
- **Constants**: Centralized in `constants.py` per context. Search before creating.
- **StrEnum**: All enumerations use `StrEnum` for serialization safety.
- **Tests & Specs (`1:1:1`)**: `1:1:1` mapping (`Source <-> Unit Test <-> Specification: docs/architecture/<spec>.md`). 100% branch coverage gate. AAA pattern. Unit tests have zero DB access.

### CRITICAL: FastAPI + `from __future__ import annotations` Pitfall

> **Runtime 422 errors, invisible in unit tests, only manifests with uvicorn.**

With `from __future__ import annotations`, ALL type annotations become **lazy strings**.
FastAPI can't identify `Request` as a special injectable → treats it as query param → 422.

```python
# ❌ FORBIDDEN
if TYPE_CHECKING:
    from fastapi import Request  # invisible at runtime → 422

# ✅ CORRECT
from fastapi import Request  # always available at runtime
```

**Rules**:
1. `Request`, `Response`, `WebSocket` MUST be **runtime imports** (never under `TYPE_CHECKING`)
2. Other types (e.g. `AsyncSession`) CAN stay under `TYPE_CHECKING`
3. Applies to ALL files in the dependency chain — not just route handlers
