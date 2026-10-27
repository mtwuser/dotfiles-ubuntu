---
name: fastapi-testing
description: Guide for writing tests following hexagonal patterns with FastAPI
---
# Skill: Write Tests — {PROJECT_NAME}

## Core Principles

1. **AAA Pattern**: Every test method MUST contain three separate, explicit comments: `# Arrange`, `# Act`, and `# Assert` (never merge into `# Arrange & Act` or `# Act & Assert`)
2. **DAMP over DRY**: Tests are readable top-to-bottom with literal values
3. **1:1 File Mapping & Decommissioning (`orphan-test-file`)**: Every source file with **executable logic** (`service.py`, `router.py`, `repository.py`, `tasks.py`, or `models.py` with custom methods/properties) has one test file. Never create artificial `test_models.py` for declarative Pydantic fields or `test_dependencies.py` for 1-line getters already covered by router tests. When deleting a source module or feature, delete or consolidate its unit test file (`orphan-test-file`) in the same changeset.
4. **One Class per File**: `Test{SourceClassName}` — no suffixes (`Expanded`, `Coverage`, `Extended`)
5. **Anti-Characterization Trap**: Never write tests that lock in broken behavior (e.g. an HTMX endpoint returning JSON or a missing ID returning HTTP 200 `{"error": ...}`). Fix the production bug first.

## Hexagonal Architecture Test Strategy

### Domain Layer (Inner Hexagon)
Domain services have ZERO I/O — they are pure functions/methods.

```python
class TestPriceCalculator:
    def test_applies_discount_to_base_price(self):
        # Arrange
        calculator = PriceCalculator()
        base_price = Decimal("100.00")
        discount = Decimal("0.15")

        # Act
        result = calculator.apply_discount(base_price, discount)

        # Assert
        assert result == Decimal("85.00")
```

No mocks needed — domain services receive data through parameters.

### Application Layer (Use Cases)
Use cases orchestrate domain + infrastructure. Mock the ports.

```python
class TestCreateOrderUseCase:
    def test_creates_order_and_persists(self):
        # Arrange
        mock_repo = MagicMock(spec=OrderRepository)
        mock_repo.save.return_value = None
        use_case = CreateOrderUseCase(order_repo=mock_repo)
        order_data = OrderDTO(product_id="abc", quantity=2)

        # Act
        result = use_case.execute(order_data)

        # Assert
        mock_repo.save.assert_called_once()
        assert result.status == "created"
```

### Infrastructure Layer (Adapters)
Imp tests with real DB connections.

```python
class TestSQLAlchemyOrderRepository:
    """Implementation tests for SQLAlchemyOrderRepository."""

    async def test_saves_and_retrieves_order(self, db_session) -> None:
        """Verify save() and find_by_id() persist and hydrate an Order entity."""
        # Arrange
        repo = SQLAlchemyOrderRepository(session=db_session)
        order = Order(product_id="abc", quantity=2)

        # Act
        await repo.save(order)
        retrieved = await repo.find_by_id(order.id)

        # Assert
        assert retrieved is not None
        assert retrieved.product_id == "abc"
        assert retrieved.quantity == 2
```

### API Router (FastAPI + `httpx2.AsyncClient`)
Use `httpx2.AsyncClient` with `ASGITransport` and `app.dependency_overrides`.

```python
from httpx2 import ASGITransport, AsyncClient


class TestOrderRouter:
    """Unit tests for OrderRouter endpoints."""

    async def test_create_order_returns_201(self, app) -> None:
        """Verify POST /api/v1/orders creates an order and returns HTTP 201."""
        # Arrange
        mock_use_case = AsyncMock()
        mock_use_case.execute.return_value = OrderResponse(id="abc-123", status="created")
        app.dependency_overrides[get_create_order_use_case] = lambda: mock_use_case

        # Act
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/v1/orders", json={"product_id": "abc", "quantity": 2})

        # Assert
        assert response.status_code == 201
        assert response.json()["id"] == "abc-123"
```

## Service Constructor Rule — CRITICAL

> **Every service/use case constructor MUST inject mocked dependencies unless the test exercises that dependency.**

```python
# ❌ WRONG — Real dependencies instantiated
use_case = CreateOrderUseCase()

# ✅ RIGHT — All ports mocked
use_case = CreateOrderUseCase(
    order_repo=MagicMock(spec=OrderRepository),
    event_bus=MagicMock(spec=EventBus),
)
```

## File Organization

```
src/{context}/tests/
├── unit/
│   ├── domain/
│   │   ├── test_price_calculator.py      → TestPriceCalculator
│   │   └── test_order_validator.py       → TestOrderValidator
│   ├── application/
│   │   └── test_create_order_use_case.py → TestCreateOrderUseCase
│   └── infrastructure/
│       └── test_order_router.py          → TestOrderRouter
└── imp/
    └── infrastructure/
        └── test_sqlalchemy_order_repo.py → TestSQLAlchemyOrderRepository
```
