---
name: database-migrations
description: "Guide for SQLAlchemy 2.0 Async persistence adapters, Domain <-> ORM mapping, and human-gated Alembic migrations in FastAPI Hexagonal projects"
---
# Skill: SQLAlchemy Async Persistence & Alembic Migrations (`database-migrations`)

---

## 1. Hexagonal Persistence Boundary

Keep SQLAlchemy models strictly inside `src/<context>/infrastructure/persistence/` and map them explicitly to/from `domain/entities.py`:

```text
src/<context>/
├── domain/
│   ├── entities.py              # Pure Python domain entity (NO SQLAlchemy imports)
│   └── ports.py                 # OrderRepositoryPort (typing.Protocol)
└── infrastructure/
    └── persistence/
        ├── models.py            # SQLAlchemy 2.0 DeclarativeBase / Mapped[...] tables
        └── repository.py        # Concrete SQLAlchemyOrderRepository(session: AsyncSession)
```

### Example: Domain Port vs. Concrete SQLAlchemy Async Adapter

```python
# src/orders/domain/ports.py
from typing import Protocol
from src.orders.domain.entities import Order


class OrderRepositoryPort(Protocol):
    """Outbound persistence port for Order aggregates."""

    async def save(self, order: Order) -> None: ...
    async def get_by_id(self, order_id: str) -> Order | None: ...
```

```python
# src/orders/infrastructure/persistence/models.py
from decimal import Decimal
from sqlalchemy import Numeric, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Shared SQLAlchemy 2.0 declarative base."""


class OrderModel(Base):
    """SQLAlchemy ORM model for the orders table."""

    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    customer_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="created")
```

```python
# src/orders/infrastructure/persistence/repository.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.orders.domain.entities import Order
from src.orders.infrastructure.persistence.models import OrderModel


class SQLAlchemyOrderRepository:
    """SQLAlchemy Async implementation of OrderRepositoryPort."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, order: Order) -> None:
        """Insert or update an Order aggregate in the session."""
        record = OrderModel(
            id=order.order_id,
            customer_id=order.customer_id,
            total_amount=order.total_amount,
            status=order.status,
        )
        await self._session.merge(record)
        await self._session.flush()

    async def get_by_id(self, order_id: str) -> Order | None:
        """Retrieve an Order domain entity by primary key."""
        stmt = select(OrderModel).where(OrderModel.id == order_id)
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        if row is None:
            return None
        return Order(
            order_id=row.id,
            customer_id=row.customer_id,
            total_amount=row.total_amount,
            status=row.status,
        )
```

---

## 2. Human-Gated Alembic Migration Workflow

> **CRITICAL (`pre_tool_guard.py`)**: Never run `alembic` commands or create/edit `alembic/versions/*.py` files directly.

1. **Update ORM Models**: Add/modify `Mapped[...]` columns in `src/<context>/infrastructure/persistence/models.py`.
2. **Ensure Metadata Registration**: Verify the model module is imported in `alembic/env.py` so `Base.metadata` discovers the table.
3. **Update Implementation Tests**: Add/update `tests/imp/` for the repository.
4. **Handoff to User**: Provide the exact commands for the user to run:
   ```bash
   source ./venv/bin/activate && alembic revision --autogenerate -m "<describe_change>"
   source ./venv/bin/activate && alembic upgrade head
   ```
