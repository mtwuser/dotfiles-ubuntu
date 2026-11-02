---
trigger: always_on
description: "{PROJECT_NAME} FastAPI + Hexagonal DDD architecture, bounded contexts, Protocol ports, and dependency rules."
---

# {PROJECT_NAME} — FastAPI & Hexagonal Architecture Rules (`fastapi-hexagonal`)

> Inherits universal engineering, typing, and `< 465`-line modularity from `technical-base.md`. This file defines the **FastAPI + Hexagonal DDD (Ports & Adapters)** architecture invariants.

---

## 1. Hexagonal Bounded Context Structure & Dependency Rule

Every Bounded Context lives under `src/<context>/` and is divided into three concentric rings:

```text
src/<context>/
├── domain/                  # INNER HEXAGON — Pure business logic (Zero I/O)
│   ├── entities.py          # Domain entities & aggregate roots
│   ├── value_objects.py     # Immutable value objects (@dataclass(frozen=True))
│   ├── services.py          # Pure domain services & business rules
│   ├── exceptions.py        # Domain-specific exceptions (no HTTP status codes)
│   └── ports.py             # Outbound & inbound contracts (typing.Protocol)
├── application/             # APPLICATION RING — Use case orchestration
│   ├── use_cases.py         # Command/Query handlers (inject Protocol ports in __init__)
│   └── dto.py               # Application Data Transfer Objects / command inputs
├── infrastructure/          # OUTER HEXAGON — Frameworks, I/O & Adapters
│   ├── persistence/         # SQLAlchemy Async models, mappers, concrete Repositories
│   ├── api/                 # FastAPI APIRouter, Pydantic v2 schemas, dependencies.py
│   └── adapters/            # External HTTP clients (httpx), task queues, mailers
└── tests/                   # Context-scoped test suite
    ├── unit/                # Isolated unit tests (domain/, application/, api/)
    └── imp/                 # Implementation tests (persistence/, external adapters)
```

### Strict Dependency Direction (`Outer -> Inner`)
```text
infrastructure  ──►  application  ──►  domain
```
- **`domain/`**:
  - **ZERO I/O** (no network, database, filesystem, or environment reads).
  - **ZERO framework imports**: `domain/` MUST NEVER import from `fastapi`, `starlette`, `sqlalchemy`, `pydantic`, `httpx`, `application/`, or `infrastructure/`.
  - Define outbound contracts (repositories, event publishers, gateways) as `typing.Protocol` interfaces inside `domain/ports.py`.
- **`application/`**:
  - Orchestrates `domain/` objects and outbound `domain/ports.py` protocols.
  - Receives all outbound ports via explicit constructor injection (`def __init__(self, repo: OrderRepositoryPort) -> None:`).
  - NEVER imports concrete adapters from `infrastructure/` or HTTP primitives from `fastapi`.
- **`infrastructure/`**:
  - Implements `domain/ports.py` protocols (e.g., `SQLAlchemyOrderRepository`, `HttpxPaymentGateway`).
  - Wires concrete adapters into application use cases inside `infrastructure/api/dependencies.py` using `fastapi.Depends`.
- **Cross-Context Isolation**:
  - Bounded contexts (`src/orders/`, `src/billing/`) MUST NOT import each other's `infrastructure/` or internal `persistence/` models. Cross-context communication flows through explicit application ports or domain events.

---

## 2. Domain Modeling & Pydantic v2 Boundary Discipline

- **Domain Value Objects (`domain/value_objects.py`)**:
  - Represent domain concepts (`OrderId`, `Money`, `EmailAddress`, `Percentage`) as immutable `@dataclass(frozen=True, slots=True)` or `typing.NewType` with domain validation in `__post_init__`.
  - Raise domain exceptions (`InvalidDiscountError`, `InsufficientFundsError`) in `domain/exceptions.py`, never `fastapi.HTTPException`.
- **API Wire Schemas (`infrastructure/api/schemas.py`)**:
  - Use **Pydantic v2** (`BaseModel`, `Field`, `ConfigDict(from_attributes=True, extra="forbid")`) strictly at the HTTP/serialization boundary (`infrastructure/api/` or `application/dto.py`).
  - Map between Domain Entities/Value Objects and Pydantic/SQLAlchemy models explicitly in the adapter layer; never leak SQLAlchemy ORM instances into `domain/` or return raw ORM models directly from routers without a response schema.

---

## 3. FastAPI Router, Dependency Injection & Runtime Annotation Rules

- **NO `from __future__ import annotations` in FastAPI Runtime Modules**:
  - NEVER add `from __future__ import annotations` to `router.py`, `dependencies.py`, or any module where FastAPI inspects `Request`, `WebSocket`, `BackgroundTasks`, `Depends()`, `Query()`, `Path()`, or `Body()` at runtime. Deferred string annotations break FastAPI/Pydantic parameter resolution when combined with local/private symbols.
- **Thin Routers (`infrastructure/api/router.py`)**:
  - Routers only parse/validate HTTP input, invoke one Application Use Case injected via `Depends(get_<use_case>)`, and map Domain results/exceptions to HTTP responses (`status.HTTP_201_CREATED`, `HTTPException`).
  - Zero SQL queries, zero `AsyncSession` manipulation, and zero business branching inside `router.py`.
- **Explicit Dependency Wiring (`infrastructure/api/dependencies.py`)**:
  - Build the dependency graph with dedicated factory functions (`get_db_session -> get_order_repository -> get_create_order_use_case`) so unit tests can override any seam cleanly via `app.dependency_overrides[get_create_order_use_case]`.

---

## 4. Async I/O & Background Execution

- **Non-Blocking Event Loop**:
  - Every `async def` endpoint, use case, or adapter MUST use non-blocking async I/O (`AsyncSession`, `httpx.AsyncClient`, `aiofiles`).
  - Never call blocking `time.sleep()`, `requests.*`, or synchronous subprocess/DB calls inside `async def`.
- **Background Tasks & Worker Queues**:
  - Use FastAPI `BackgroundTasks` only for lightweight, best-effort post-response notifications (`< 500ms`).
  - Route durable, retryable, or CPU/IO-heavy jobs through a Domain Port (`TaskQueuePort` in `domain/ports.py`) backed by an async worker adapter (e.g., Celery, ARQ, or Dramatiq) in `infrastructure/adapters/`.

---

## 5. Optional Server-Rendered Views (Jinja2 + HTMX)

When a project serves HTML alongside or instead of JSON APIs:
- Render templates via Starlette/FastAPI `Jinja2Templates` in `infrastructure/api/` or `infrastructure/web/`.
- For progressive enhancement with HTMX, inspect `request.headers.get("HX-Request") == "true"` to return either the partial HTML fragment or the full page layout.
- Keep all business state in the backend use case; templates only format view context dictionaries.
