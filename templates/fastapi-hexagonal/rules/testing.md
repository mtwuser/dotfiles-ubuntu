---
description: >-
  MUST activate when working on test files (tests/), pytest configuration,
  coverage analysis, conftest.py, or any testing-related task. Contains test
  classification (unit/imp), tier placement, AAA pattern enforcement, FastAPI
  test patterns, and hexagonal testing boundaries for {PROJECT_NAME}.
trigger: model_decision
---
# Testing Rules — {PROJECT_NAME}

## Test Classification & Placement

1. **Unit tests** (`tests/unit/`): 0 DB access, all deps mocked, ms/test.
2. **Imp tests** (`tests/imp/`): Gap closers that strictly require DB access. Keep imp tests ONLY for DB/integration verification.

## Architecture Invariants — MANDATORY

- **1:1 File Mapping & Decommissioning (`orphan-test-file`)**: Every production file with **executable logic** (`service.py`, `router.py`, `repository.py`, `tasks.py`, or `models.py` with custom methods/properties/validators) MUST have a corresponding `test_<file>.py`. Do NOT create artificial `test_models.py` for purely declarative Pydantic models/DTOs or `test_dependencies.py` for 1-line singleton getters already covered by router tests. Conversely, every `tests/unit/**/test_<name>.py` file MUST map to an existing source module in `src/` — when decommissioning a module or feature, purge or consolidate its test file in the same changeset.
- **One Class**: Each test file contains ONE test class named `Test{SourceClassName}`. NEVER append suffixes like `Coverage`, `Expanded`, `Extended`.
- **DB Guards**: NEVER use database fixtures or markers inside `tests/unit/`. Unit tests are pure.
- **Service Constructors**: Every service constructor in tests MUST inject mocked dependencies unless specifically testing that sub-dependency.
- **Patch Targets**: Patch where the object is **looked up at runtime**. When a module uses `from source import func`, patch at `consumer.func`. When it uses `import source` and calls `source.func`, patch at `source.func`.
- **100% Coverage Gate**: Coverage must remain at 100% (statement + branch) before and after any task. Unit + Imp combined = 100%.
- **Deprecation-Free Gate**: Tests MUST pass with `-W error::DeprecationWarning`.
- **Anti-Characterization Trap**: Never write tests that rubber-stamp broken behavior (e.g., an HTMX endpoint returning JSON instead of a partial, or a missing resource returning HTTP 200 `{"error": ...}` instead of raising `NotFoundError` → 404). Cross-check caller/template contracts first and fix the production bug before writing the test.
- **Speed**: No single unit test may exceed 1 second.

## AAA Pattern — MANDATORY

Every test method MUST contain three separate, explicit comments:
1. `# Arrange` — set up state and mocks
2. `# Act` — execute the single action
3. `# Assert` — verify the result

**NEVER** merge comments into `# Arrange & Act` or `# Act & Assert`.
**DAMP over DRY**: Each test should be readable top-to-bottom. Use literal values; do not use computed expectations.

## FastAPI Async Test Patterns (`httpx2`)

### AsyncClient + ASGITransport Usage
```python
from unittest.mock import AsyncMock
from httpx2 import ASGITransport, AsyncClient


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
| Infrastructure Adapters | I/O integration | Imp tests with real DB/services |
| API Routers | Request/response contracts | `httpx2.AsyncClient` + dependency override |
| Templates (HTMX) | HTML fragment responses | `httpx2.AsyncClient` (`HX-Request: true`) + assert HTML content |
