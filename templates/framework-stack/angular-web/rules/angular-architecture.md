---
trigger: always_on
description: "Angular Standalone components, Signals reactivity, OnPush change detection, and strict TypeScript architecture rules (angular-web)."
---

# Angular Standalone & Signals Architecture Rules (`angular-web`)

> Inherits universal `1:1:1` traceability, `< 465`-line modularity, and `100%` isolated unit branch coverage from `science-base.md` and `software-engineering.md`. This file defines the **Angular (`upstream_framework: angular`)** frontend architecture invariants.

---

## 1. Feature Domain Structure & Dependency Rule

Every feature domain lives under `src/app/features/<feature>/` with strict separation between presentation, state/application facades, and HTTP infrastructure:

1. **`domain/`**: Pure TypeScript interfaces, value types, and `InjectionToken` port contracts (`0` Angular UI or `HttpClient` imports).
2. **`application/`**: Signals-backed feature stores/facades (`signal()`, `computed()`) orchestrating domain ports via `inject()`.
3. **`infrastructure/`**: Concrete `HttpClient` adapters implementing domain `InjectionToken` ports with typed DTO validation.
4. **`presentation/`**: Standalone UI components (`standalone: true`, `ChangeDetectionStrategy.OnPush`) using `input()`, `output()`, and native control flow (`@if`, `@for`, `@switch`).

---

## 2. Normative Invariants

1. **Signals & `OnPush` Exclusivity**: Every component declares `changeDetection: ChangeDetectionStrategy.OnPush`. Prefer `signal()` and `computed()` over mutable class properties or manual `ChangeDetectorRef` triggers.
2. **Strict TypeScript & Template Checking**: Enforce `"strict": true`, `"noImplicitOverride": true`, and `"strictTemplates": true` in `tsconfig.json`. Zero `any` casts in components, services, or specs.
3. **Zero Direct I/O in Components**: Components never inject `HttpClient`, `localStorage`, or `window` directly; all external I/O crosses an injected facade or `InjectionToken` adapter verified via `1:1` unit tests.
