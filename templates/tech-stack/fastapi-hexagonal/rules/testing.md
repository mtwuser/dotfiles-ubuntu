---
trigger: always_on
description: "{PROJECT_NAME} Hexagonal 4-layer testing boundaries, FastAPI AsyncClient + dependency_overrides, and async DB imp tests."
---

# {PROJECT_NAME} — FastAPI & Hexagonal Testing Rules (`fastapi-hexagonal`)

> Inherits universal `1:1:1` traceability (`Spec <-> Test <-> Code`), `AAA` (`# Arrange` / `# Act` / `# Assert`), Bidirectional 3-Tier Flow (`E2E -> Imp -> Unit`), and `100%` branch coverage gates from `technical-base.md` and `skills/testing/SKILL.md`. This file defines the **Hexagonal + FastAPI layer testing contracts**.

---

## 1. Hexagonal 4-Layer Test Matrix

Each hexagonal ring has a strict isolation boundary and test location under `src/<context>/tests/`:

| Hexagonal Layer | Test Tier & Directory | Collaborator Strategy | I/O Allowed? |
|-----------------|-----------------------|-----------------------|:------------:|
| **1. Domain (`domain/`)** | `tests/unit/domain/` | **Zero mocks** — instantiate real Entities, Value Objects, and Domain Services with literal values | **No** (`0` I/O) |
| **2. Application (`application/`)** | `tests/unit/application/` | **Constructor-injected `Protocol` mocks** (`MagicMock(spec=Port)` / `AsyncMock(spec=Port)`) | **No** (`0` I/O) |
| **3. API Router (`infrastructure/api/`)** | `tests/unit/infrastructure/` | **`httpx.AsyncClient` + `ASGITransport(app=app)`** + **`app.dependency_overrides[get_use_case]`** | **No** (in-memory ASGI) |
| **4. Persistence & Adapters (`infrastructure/persistence/`)** | `tests/imp/infrastructure/` | **Real transactional `AsyncSession` / test container** verifying SQL queries and ORM $\leftrightarrow$ Domain mapping | **Yes** (`tests/imp/` only) |

---

## 2. FastAPI Router Unit Testing (`httpx.AsyncClient` + `dependency_overrides`)

- **In-Memory ASGI Transport**:
  - Test routers using `AsyncClient(transport=ASGITransport(app=app), base_url="http://test")` — never spin up a live TCP `uvicorn` server in `tests/unit/`.
- **Override via `app.dependency_overrides` (Never `unittest.mock.patch` on FastAPI `Depends`)**:
  - Replace the injected Application Use Case (or auth dependency) using `app.dependency_overrides[get_use_case] = lambda: mock_use_case` and clear `app.dependency_overrides.clear()` in teardown/fixture cleanup.
- **Bipolar Status & Error Mapping**:
  - Assert both nominal HTTP status codes (`200`, `201`, `204`) and domain-exception-to-HTTP error mappings (`400`, `404`, `409`, `422`).

---

## 3. Application Use Case Testing (`Protocol`-Constrained Constructor Mocks)

- Every outbound port injected into a Use Case constructor MUST use `spec=<PortProtocol>` (`MagicMock(spec=OrderRepositoryPort)` or `AsyncMock(spec=OrderRepositoryPort)`).
- Never instantiate a Use Case in `tests/unit/` with a real SQLAlchemy repository or external HTTP client.

---

## 4. What Not to Unit-Test Artificially in FastAPI

- Do **NOT** create `test_schemas.py` / `test_models.py` merely to test that Pydantic `BaseModel` or SQLAlchemy `DeclarativeBase` assigns attributes (unless the class defines custom `@field_validator`, `@model_validator`, or domain conversion methods).
- Do **NOT** create `test_dependencies.py` for 1-line `Depends()` provider functions that are already exercised by router/implementation tests.
