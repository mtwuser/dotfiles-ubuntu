---
name: django-testing
description: "Django service-layer isolated unit tests and pytest-django selector/query-count imp testing recipes"
---
# Skill: Modular Django Testing (`django-testing`)

> Complements `software-engineering`'s `skills/testing/SKILL.md` with concrete **Django (`django-backend`)** unit and `imp` testing recipes.

---

## 1. Pure Domain & Service Unit Tests (`tests/unit/`)

Test domain validation and service orchestration in isolation with `100%` branch coverage and explicit `# Arrange`, `# Act`, `# Assert` comments before touching database persistence.

## 2. Selector & ORM Integration Tests (`tests/imp/`)

Verify `selectors.py` and `services.py` transaction boundaries using `pytest-django` (`@pytest.mark.django_db`) and `django_assert_num_queries` to guarantee zero N+1 regressions.
