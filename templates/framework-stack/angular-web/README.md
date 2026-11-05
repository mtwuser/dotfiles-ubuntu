# Framework-Stack Template: Angular Standalone & Signals (`angular-web`)

Ready-to-apply **Framework-Stack Template Pack** (`kind: "framework-stack"`, `extends: "software-engineering"`, `upstream_framework: "angular"`) for frontend engineering departments, web squads, and TypeScript/Angular enterprise single-page applications.

> **Clean Inheritance Design**:
> - Universal workflow, commit discipline, and `< 465`-line modularity come from **`human-base`**.
> - Universal `1:1:1` traceability (`Spec <-> Test <-> Code`), `AAA` testing, and `100%` isolated unit branch coverage come automatically from **`science-base`** + **`software-engineering`** (`extends: "software-engineering"`).
> - Tracks upstream **`angular/angular`** (`upstream_framework`) so framework-level discoveries can be proposed 2 hops upward (`make promote` $\rightarrow$ `make publish-oss --dry-run`).

---

## 1. Quick Setup (Deterministic CLI)

Apply the `angular-web` framework pack and inherited `software-engineering` rules with a single CLI command:

```bash
# Materialize science-base + software-engineering + angular-web into a target project
./scripts/layer-config.sh apply-project /path/to/your-angular-app --template angular-web --layers all
```

---

## 2. Template Pack Contents

### 2.1. Rules (`.agents/rules/`)

Projected rules enforce standalone Angular 19+ components, `OnPush` change detection, and Signals state:

| File | Scope (`angular-web` Delta over `software-engineering`) |
|------|---------------------------------------------------------|
| `rules/angular-architecture.md` | Standalone components, `ChangeDetectionStrategy.OnPush`, Signals-first state (`signal()`, `computed()`, `input()`, `output()`), `inject()` boundary separation, and `strictTemplates: true` |

### 2.2. Skills (`.agents/skills/`)

Projected skills provide isolated `TestBed` and `HttpTestingController` `AAA` test recipes:

| File | Skill Name & Purpose |
|------|----------------------|
| `skills/angular-testing/SKILL.md` | `angular-testing` — Isolated `TestBed` + `HttpTestingController` unit & `imp` testing recipes following `AAA` (`# Arrange`, `# Act`, `# Assert`) |
