---
description: >-
  MUST activate when working on test files (tests/), pytest configuration,
  coverage analysis, conftest.py, or any testing-related task. Contains test
  classification (unit/imp), tier placement, AAA pattern enforcement, FastAPI
  test patterns, and hexagonal testing boundaries for {PROJECT_NAME}.
trigger: model_decision
---
# Testing Rules — {PROJECT_NAME}

## Test Classification, Bidirectional Flow & Placement

1. **Unit tests** (`tests/unit/`): 0 DB access, all deps mocked, ms/test (`1:1` algorithmic exhaustiveness across 4 quadrants).
2. **Imp tests** (`tests/imp/` — **Implementation tests**, never `int`): Real cross-component boundary contracts (DB persistence, I/O adapters, parity). Named `imp` both to avoid colliding with the primitive `int` type and because they verify how internal components are *implemented* together (whereas *integration* is deploying/integrating into production). Keep `imp` tests strictly for real DB/adapter boundary verification.
3. **Bidirectional 3-Tier Flow**: Read, deduce cases, and validate **Top-Down (`E2E -> Imp -> Unit`)** to preserve macroscopic persona/boundary invariants; author, isolate coverage, and execute **Bottom-Up (`Unit -> Imp -> E2E`)** so `tests/unit/` achieves 100% isolated branch coverage first without higher-tier masking.

## Architecture Invariants — MANDATORY

- **1:1:1 File & Spec Mapping & Decommissioning (`orphan-test-file`)**: Every production file with **executable logic** (`service.py`, `router.py`, `repository.py`, `tasks.py`, or `models.py` with custom methods/properties/validators) MUST have a corresponding `test_<file>.py` and a bidirectional `Specification: docs/architecture/<spec>.md` pointer (`< 465` lines per file). Do NOT create artificial `test_models.py` for purely declarative Pydantic models/DTOs or `test_dependencies.py` for 1-line singleton getters already covered by router tests. Conversely, every `tests/unit/**/test_<name>.py` file MUST map to an existing source module in `src/` — when decommissioning a module or feature, purge or consolidate its test file in the same changeset.
- **One Class & Human-Agent `1:1:1` Comprehension Symbiosis**: Each test file contains ONE test class named `Test{SourceClassName}` linked via `Specification: docs/architecture/<spec>.md` in the module docstring. NEVER append suffixes like `Coverage`, `Expanded`, `Extended`. Every test method pairs a natural-language behavioral name (`test_<subject>_<scenario>_<expected>`) with a **1-line invariant docstring** stating *why* and explicit `# Arrange`, `# Act`, `# Assert` comments.
- **DB Guards**: NEVER use database fixtures or markers inside `tests/unit/`. Unit tests are pure.
- **Service Constructors**: Every service constructor in tests MUST inject mocked dependencies (`MagicMock(spec=...)` / `AsyncMock(spec=...)`) unless specifically testing that sub-dependency.
- **Patch Targets**: Patch where the object is **looked up at runtime**. When a module uses `from source import func`, patch at `consumer.func`. When it uses `import source` and calls `source.func`, patch at `source.func`.
- **100% Coverage Gate & Boundary Cut-Points (`N` vs `N ± 1`)**: Coverage must remain at 100% (statement + branch) in isolated unit runs (`tests/unit/`) and across `unit + imp`, asserting exact boundary cut-points (`N` vs `N ± 1`).
- **Deprecation-Free Gate**: Tests MUST pass with `-W error::DeprecationWarning`.
- **Anti-Characterization Trap (HTMX & Pydantic Contracts)**: Never write tests that rubber-stamp broken behavior (e.g., an HTMX `hx-get`/`hx-post`/`hx-target` endpoint returning JSON instead of an HTML partial, or a missing resource returning HTTP 200 `{"error": ...}` instead of raising `NotFoundError` → 404). Cross-check caller/template contracts and public `BaseSettings`/schema defaults first, and fix the production bug before writing the test.
- **Speed**: No single unit test may exceed 1 second.

## AAA Pattern — MANDATORY

Every test method MUST contain three separate, explicit comments:
1. `# Arrange` — set up state and mocks
2. `# Act` — execute the single action
3. `# Assert` — verify the result

**NEVER** merge comments into `# Arrange & Act` or `# Act & Assert`.
**DAMP over DRY**: Each test should be readable top-to-bottom. Use literal values; do not use computed expectations.

## FastAPI Async Test Patterns (`httpx`)

### AsyncClient + ASGITransport Usage
```python
from unittest.mock import AsyncMock
from httpx import ASGITransport, AsyncClient


class TestMyRouter:
    """Unit tests for MyRouter endpoints."""

    async def test_endpoint_returns_data(self, app) -> None:
        """Verify GET /api/v1/my-resource/{id} returns serialized item."""
        # Arrange
        mock_service = AsyncMock()
        mock_service.get_by_id.return_value = {"id": "abc-123"}
        app.dependency_overrides[get_my_service] = lambda: mock_service

        # Act
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/my-resource/abc-123")

        # Assert
        assert response.status_code == 200
        assert response.json()["id"] == "abc-123"
```

### Async Service Test Pattern
```python
from unittest.mock import AsyncMock


class TestMyService:
    """Unit tests for MyService domain logic."""

    async def test_process_completes_successfully(self) -> None:
        """Verify process() delegates to repository and returns completed entity."""
        # Arrange
        service = MyService(repo=AsyncMock())

        # Act
        result = await service.process(data)

        # Assert
        assert result.status == "completed"
```

## What NOT to Test

- **Don't test built-in or framework behavior**: Do not test Pydantic field assignment, `StrEnum` inheritance, or framework health probes/primitives in consumer test suites.
- **Don't test literal constants**: Test the logic that consumes the constant, not the constant itself.
- **Don't duplicate tests across files**: Each class/function is tested only in its corresponding test file.

## Test Commands

All commands run from project root with venv activated.

| Command | Purpose | Speed |
|---------|---------|-------|
| `make test-unit` | Unit tests — fast iteration | ⚡ |
| `make test-unit COV=1` | Unit tests + coverage | 📊 |
| `make test-imp` | Implementation tests | ⚡ |
| `make test-all` | Full suite + coverage baseline | 📊 |
| `python -m pytest path/` | Specific test file/directory | instant |

## Hexagonal Testing Boundaries

| Layer | What to test | How |
|-------|-------------|-----|
| Domain Services | Pure business logic | Direct call, no mocks needed (no I/O) |
| Domain Ports | Interface contracts | Verify implementations satisfy Protocol |
| Application Use Cases | Orchestration flow | Mock ports/repositories |
| Infrastructure Adapters | Real I/O & DB implementation | Imp tests (`tests/imp/`) with real DB/services |
| API Routers | Request/response contracts | `httpx.AsyncClient` + dependency override |
| Templates (HTMX) | HTML fragment responses | `httpx.AsyncClient` (`HX-Request: true`) + assert HTML content |
