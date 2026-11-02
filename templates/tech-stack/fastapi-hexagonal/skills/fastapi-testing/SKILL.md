---
name: fastapi-testing
description: FastAPI + Hexagonal DDD test recipes across Domain, Application (Protocol mocks), API Router (AsyncClient + ASGITransport + dependency_overrides), and Persistence (async SQLAlchemy imp tests)
---
# Skill: FastAPI & Hexagonal Testing Recipes (`fastapi-testing`)

> Complements `technical-base`'s `skills/testing/SKILL.md` (`1:1:1` traceability, explicit `# Arrange` / `# Act` / `# Assert`, `Top-Down` vs. `Bottom-Up` flow, and `100%` branch coverage) with concrete **FastAPI + Hexagonal Architecture** test patterns.

---

## 1. Domain Layer (`tests/unit/domain/` — Zero Mocks, Zero I/O)

Domain entities, value objects, and domain services are pure Python and require zero mocks:

```python
"""Unit tests for PriceCalculator domain service.

Specification: docs/architecture/orders.md
"""

from decimal import Decimal
import pytest

from src.orders.domain.exceptions import InvalidDiscountError
from src.orders.domain.services import PriceCalculator


class TestPriceCalculator:
    """Unit tests for PriceCalculator pure domain logic."""

    def test_apply_discount_subtracts_percentage_from_base_price(self) -> None:
        """Verify apply_discount() subtracts a valid percentage discount from base_price."""
        # Arrange
        calculator = PriceCalculator()
        base_price = Decimal("100.00")
        discount = Decimal("0.15")

        # Act
        result = calculator.apply_discount(base_price=base_price, discount=discount)

        # Assert
        assert result == Decimal("85.00")

    def test_apply_discount_raises_when_discount_exceeds_one(self) -> None:
        """Verify apply_discount() rejects discount ratios above 1.0 (N vs N+1 boundary)."""
        # Arrange
        calculator = PriceCalculator()

        # Act
        with pytest.raises(InvalidDiscountError, match="between 0 and 1"):
            calculator.apply_discount(base_price=Decimal("100.00"), discount=Decimal("1.01"))

        # Assert
        assert calculator is not None
```

---

## 2. Application Layer (`tests/unit/application/` — `Protocol`-Constrained Constructor Mocks)

Application use cases orchestrate domain objects and outbound `domain/ports.py` protocols. Always inject `AsyncMock(spec=<PortProtocol>)` or `MagicMock(spec=<PortProtocol>)` in the constructor:

```python
"""Unit tests for CreateOrderUseCase application orchestrator.

Specification: docs/architecture/orders.md
"""

from decimal import Decimal
from unittest.mock import AsyncMock

from src.orders.application.dto import CreateOrderCommand
from src.orders.application.use_cases import CreateOrderUseCase
from src.orders.domain.ports import OrderRepositoryPort


class TestCreateOrderUseCase:
    """Unit tests for CreateOrderUseCase with mocked outbound ports."""

    async def test_execute_persists_order_and_returns_created_dto(self) -> None:
        """Verify execute() builds an Order entity, saves it via OrderRepositoryPort, and returns its ID."""
        # Arrange
        mock_repo = AsyncMock(spec=OrderRepositoryPort)
        use_case = CreateOrderUseCase(order_repo=mock_repo)
        command = CreateOrderCommand(customer_id="cust-01", total_amount=Decimal("49.90"))

        # Act
        result = await use_case.execute(command)

        # Assert
        mock_repo.save.assert_awaited_once()
        assert result.customer_id == "cust-01"
        assert result.status == "created"
```

---

## 3. Infrastructure API Router (`tests/unit/infrastructure/` — `AsyncClient` + `ASGITransport` + `dependency_overrides`)

Test FastAPI routers in memory using `httpx.AsyncClient`, `ASGITransport(app=app)`, and `app.dependency_overrides` (always clearing overrides in a `try/finally` block or fixture teardown):

```python
"""Unit tests for Order FastAPI router endpoints.

Specification: docs/architecture/orders.md
"""

from decimal import Decimal
from unittest.mock import AsyncMock
from httpx import ASGITransport, AsyncClient

from src.orders.application.dto import OrderResultDTO
from src.orders.application.use_cases import CreateOrderUseCase
from src.orders.infrastructure.api.dependencies import get_create_order_use_case


class TestOrderRouter:
    """Unit tests for /api/v1/orders HTTP endpoints."""

    async def test_create_order_returns_201_with_order_payload(self, app) -> None:
        """Verify POST /api/v1/orders invokes CreateOrderUseCase and returns HTTP 201."""
        # Arrange
        mock_use_case = AsyncMock(spec=CreateOrderUseCase)
        mock_use_case.execute.return_value = OrderResultDTO(
            order_id="ord-123",
            customer_id="cust-01",
            total_amount=Decimal("49.90"),
            status="created",
        )
        app.dependency_overrides[get_create_order_use_case] = lambda: mock_use_case

        try:
            # Act
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.post(
                    "/api/v1/orders",
                    json={"customer_id": "cust-01", "total_amount": "49.90"},
                )

            # Assert
            assert response.status_code == 201
            assert response.json()["order_id"] == "ord-123"
            mock_use_case.execute.assert_awaited_once()
        finally:
            app.dependency_overrides.clear()
```

---

## 4. Infrastructure Persistence (`tests/imp/infrastructure/` — Real Async DB Session)

Verify concrete SQLAlchemy repositories and ORM $\leftrightarrow$ Domain mappers in `tests/imp/` against a transactional `AsyncSession`:

```python
"""Implementation tests for SQLAlchemyOrderRepository.

Specification: docs/architecture/orders.md
"""

from decimal import Decimal
from src.orders.domain.entities import Order
from src.orders.infrastructure.persistence.repository import SQLAlchemyOrderRepository


class TestSQLAlchemyOrderRepository:
    """Implementation tests for SQLAlchemyOrderRepository against an async DB session."""

    async def test_save_and_get_by_id_round_trips_domain_entity(self, async_db_session) -> None:
        """Verify save() persists an Order and get_by_id() hydrates the matching domain entity."""
        # Arrange
        repo = SQLAlchemyOrderRepository(session=async_db_session)
        order = Order(order_id="ord-100", customer_id="cust-01", total_amount=Decimal("25.00"))

        # Act
        await repo.save(order)
        loaded = await repo.get_by_id("ord-100")

        # Assert
        assert loaded is not None
        assert loaded.order_id == "ord-100"
        assert loaded.total_amount == Decimal("25.00")
```
