# Framework-Stack Template: Modular Django Services & Selectors (`django-backend`)

Ready-to-apply **Framework-Stack Template Pack** (`kind: "framework-stack"`, `extends: "software-engineering"`, `upstream_framework: "django"`) for Python/Django backend departments, squads, and modular monolith workspaces.

> **Clean Inheritance Design**:
> - Universal workflow, commit discipline, and `< 465`-line modularity come from **`human-base`**.
> - Universal `1:1:1` traceability (`Spec <-> Test <-> Code`), `AAA` testing, and `100%` isolated unit branch coverage come automatically from **`science-base`** + **`software-engineering`** (`extends: "software-engineering"`).
> - Tracks upstream **`django/django`** (`upstream_framework`) for 2-hop open-source promotion (`make promote` $\rightarrow$ `make publish-oss --dry-run`).

---

## 1. Quick Setup (Deterministic CLI)

Apply the `django-backend` framework pack and inherited `software-engineering` rules with a single CLI command:

```bash
# Materialize science-base + software-engineering + django-backend into a target project
./scripts/layer-config.sh apply-project /path/to/your-django-app --template django-backend --layers all
```

---

## 2. Template Pack Contents

### 2.1. Rules (`.agents/rules/`)

Projected rules enforce modular Django service/selector separation, transaction boundaries, and N+1 query guards:

| File | Scope (`django-backend` Delta over `software-engineering`) |
|------|------------------------------------------------------------|
| `rules/django-architecture.md` | Modular Django app layout (`models.py`, `services.py`, `selectors.py`, `views.py`), `@transaction.atomic` write boundaries, `select_related`/`prefetch_related` N+1 guards, and human-gated migrations |

### 2.2. Skills (`.agents/skills/`)

Projected skills provide isolated service unit test and `pytest-django` implementation test recipes:

| File | Skill Name & Purpose |
|------|----------------------|
| `skills/django-testing/SKILL.md` | `django-testing` — Isolated service unit tests + `pytest-django` selector/migration `imp` test recipes |
