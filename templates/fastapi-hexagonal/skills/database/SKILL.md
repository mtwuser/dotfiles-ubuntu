---
name: fastapi-database
description: Safe migration practices for Alembic/SQLAlchemy in {PROJECT_NAME}
---
# Skill: Database Migrations — {PROJECT_NAME}

## Zero-Touch Migration Policy

> Defined in `governance.md` §Migration Policy — **HANDS OFF**.
> This skill details the procedural boundaries.

## Safe Guidelines

### What you MAY do:
- Modify SQLAlchemy ORM models (`orm_models.py`)
- Add/remove columns, tables, or constraints in ORM code
- Suggest what migration command the user should run

### What you MUST NOT do:
- Run `alembic revision --autogenerate`
- Run `alembic upgrade head`
- Manually edit files in `alembic/versions/`
- Create migration files by hand

### Recommended User Commands

When ORM model changes are ready, suggest these commands for the user to run:

```bash
# Generate migration from model changes
source venv/bin/activate
alembic revision --autogenerate -m "<descriptive message>"

# Review the generated migration file before applying
# Then apply:
alembic upgrade head

# Rollback if needed:
alembic downgrade -1
```

### Migration Naming Convention
- Use descriptive messages: `add_user_preferences_table`, `add_index_on_created_at`
- Never use generic names: `update`, `fix`, `change`

### Pre-Migration Checklist
1. All ORM model changes are committed and tested
2. No pending migrations exist (`alembic check`)
3. Database backup exists (for production)
4. Migration is reviewed for destructive operations (DROP, ALTER TYPE)
