---
name: angular-testing
description: "Angular Standalone component, Signal store, and HttpTestingController AAA testing recipes"
---
# Skill: Angular Standalone & Signals Testing (`angular-testing`)

> Complements `software-engineering`'s `skills/testing/SKILL.md` with concrete **Angular (`angular-web`)** unit and `imp` testing recipes.

---

## 1. Isolated Signal Store / Facade Unit Tests (`tests/unit/`)

Instantiate facades with mocked `InjectionToken` providers and assert signal state transitions across all 4 quadrants (nominal, `N` vs `N ± 1` boundaries, bipolar guards, and HTTP error recovery) using `# Arrange`, `# Act`, `# Assert`.

## 2. HTTP Adapter Contract Tests (`tests/imp/`)

Verify `HttpClient` adapters using `provideHttpClient()` + `provideHttpClientTesting()` and `HttpTestingController.expectOne()`, asserting exact request method, headers, payload serialization, and status error mapping.
