# Template: FastAPI Hexagonal

Project starter template for **FastAPI + Hexagonal Architecture (DDD) + HTMX/Islands** projects.

## Usage

```bash
# Recommended (Scaffolding CLI — projects template + 0..N mounted layers + LAYER_LINEAGE.md):
~/dotfiles-ubuntu/scripts/layer-config.sh apply-project <your-project> \
  --template fastapi-hexagonal \
  --layers all

# Manual alternative:
# 1. Copy template rules, skills & session template to your project's .agents/ directory
mkdir -p <your-project>/.agents
cp -r ~/dotfiles-ubuntu/templates/fastapi-hexagonal/{rules,skills} <your-project>/.agents/
cp ~/dotfiles-ubuntu/templates/fastapi-hexagonal/governance/SESSION.md <your-project>/.agents/SESSION.md

# 2. Copy root governance files (used by /sopen, /continue, /priority, /sclose)
cp ~/dotfiles-ubuntu/templates/fastapi-hexagonal/governance/{WORKTASK,WORKROAD,WORKVALI,BACKLOG,CHANGELOG}.md <your-project>/

# 3. Customize placeholders:
#    - Update .agents/rules/environment.md with your project paths
#    - Update .agents/skills/start/SKILL.md with your documentation references
#    - Adjust .agents/rules/coding.md bounded context pipeline when contexts are defined
```

## What's Included

| File | Purpose |
|------|---------|
| `rules/coding.md` | Hexagonal DDD, `0-byte` `__init__.py` purity, Zone Architecture (Z1–Z4), Async Continuum, SOLID |
| `rules/environment.md` | Workspace layout template with placeholders |
| `rules/governance.md` | 4-Phase Work Lifecycle, Mode Discipline, Cognitive & Agent Governance (`trigger: model_decision`) |
| `rules/testing.md` | Explicit 3-comment AAA (`# Arrange`, `# Act`, `# Assert`), `httpx2` async test patterns, logic-only 1:1 mapping |
| `skills/database/SKILL.md` | Zero-touch Alembic migration policy (`name: fastapi-database`) |
| `skills/frontend/SKILL.md` | HTMX + Islands conventions Z1–Z4 (`name: fastapi-frontend`) |
| `skills/testing/SKILL.md` | FastAPI testing patterns per hexagonal layer (`name: fastapi-testing`) |
| `skills/start/SKILL.md` | Project startup sequence template (`name: start`) |
| `governance/*.md` | Root governance trackers (`WORKTASK.md`, `WORKROAD.md`, `WORKVALI.md`, `BACKLOG.md`, `CHANGELOG.md`) + `.agents/SESSION.md` |

## Placeholders

Files use these placeholders that you should replace:

| Placeholder | Replace with |
|-------------|-------------|
| `{PROJECT_NAME}` | Your project name (e.g., `CheckoutService`, `MyApp`) |
| `{PROJECT_PATH}` | Absolute path (e.g., `/home/<user>/Projects/MyApp`) |
| `{USERNAME}` | Your system username |
