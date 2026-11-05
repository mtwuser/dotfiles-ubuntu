---
trigger: always_on
description: "Modular Django service-layer (services.py), read selector (selectors.py), N+1 query prevention, and migration safety rules (django-backend)."
---

# Modular Django Service & Selector Architecture Rules (`django-backend`)

> Inherits universal `1:1:1` traceability, `< 465`-line modularity, and `100%` isolated unit branch coverage from `science-base.md` and `software-engineering.md`. This file defines the **Django (`upstream_framework: django`)** backend architecture invariants.

---

## 1. App Module Structure (`services.py` vs. `selectors.py`)

Every Django domain app under `apps/<context>/` separates command mutations from query reads:

1. **`models.py`**: Declarative schema definitions, constraints (`CheckConstraint`, `UniqueConstraint`), and pure field validation (`clean()`). Zero cross-app side effects or `post_save` signals for core business flows.
2. **`services.py`**: Keyword-only write functions (`def order_create(*, user: User, ...) -> Order:`) wrapped in `@transaction.atomic` that enforce domain invariants.
3. **`selectors.py`**: Keyword-only read functions (`def order_list_for_user(*, user_id: UUID) -> QuerySet[Order]:`) that explicitly declare `.select_related(...)` and `.prefetch_related(...)`.
4. **`views.py` / `apis.py`**: Thin HTTP adapters that validate input schemas, delegate to `services.py` or `selectors.py`, and serialize responses.

---

## 2. Normative Invariants

1. **Zero-Signal & Zero-View Business Logic**: Never hide domain workflows inside Django `signals.py`, model `.save()` overrides, or serializer `.create()` methods.
2. **N+1 Query Prevention Gate**: Every relational traversal in `selectors.py` must be backed by explicit `select_related` / `prefetch_related` and verified with `django_assert_num_queries` in `tests/imp/`.
3. **Human-Gated Migrations**: Never run `makemigrations` or `migrate` against shared environments without explicit operator review.
