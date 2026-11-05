---
name: frontend-patterns
description: "Standard FastAPI/Starlette Jinja2Templates, progressive HTMX partial rendering, and zero-build Web Component patterns"
---
# Skill: Server-Rendered Views & HTMX in FastAPI (`frontend-patterns`)

> Applies to FastAPI + Hexagonal projects that serve HTML views (`Jinja2Templates` + optional HTMX / Web Components) alongside or instead of JSON APIs. Uses **100% standard FastAPI/Starlette primitives**.

---

## 1. Progressive Presentation Tiers (Standard FastAPI + Jinja2 + HTMX)

Choose the simplest presentation tier that satisfies the interaction:

| Tier | Technology | When to Use |
|------|------------|-------------|
| **1. Full-Page SSR** | FastAPI `Jinja2Templates` + semantic HTML/CSS | Standard page navigation, SEO pages, read-heavy views |
| **2. Partial HTML Swaps (HTMX)** | `hx-get` / `hx-post` + `HX-Request` header check | Inline table filtering, form submission, modal fragments, live polling |
| **3. Isolated Client Widgets** | Native Web Components (`customElements.define`) | Rich client-side interactivity (charts, drag-and-drop, canvas) receiving initial state via HTML attributes or JSON `<script type="application/json">` |

---

## 2. Standard FastAPI `Jinja2Templates` & HTMX Partial Rendering

Keep view rendering in the `infrastructure/` outer ring (`src/<context>/infrastructure/api/` or `infrastructure/web/`). Never enable `from __future__ import annotations` in router files where `Request` is injected:

```python
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from src.orders.application.use_cases import ListOrdersUseCase
from src.orders.infrastructure.api.dependencies import get_list_orders_use_case

router = APIRouter(prefix="/orders", tags=["orders-web"])
templates = Jinja2Templates(directory="templates")


@router.get("", response_class=HTMLResponse)
async def list_orders_view(
    request: Request,
    use_case: ListOrdersUseCase = Depends(get_list_orders_use_case),
) -> HTMLResponse:
    """Render either the full orders page or the HTMX table partial."""
    orders = await use_case.execute()
    context = {"request": request, "orders": orders}
    if request.headers.get("HX-Request") == "true":
        return templates.TemplateResponse(request, "orders/partials/order_table.html", context)
    return templates.TemplateResponse(request, "orders/list.html", context)
```

### HTMX Polling Stop Convention (`HTTP 286`)
When an HTMX polling element (`hx-trigger="every 2s"`) finishes its background work, return HTTP status `286` from the FastAPI endpoint so HTMX automatically stops polling:

```python
STATUS_HTMX_STOP_POLLING = 286
```

---

## 3. Styling & Accessibility Hygiene

- **Design Tokens First**: Use CSS custom properties (`var(--color-surface)`, `var(--space-md)`) in `static/css/` — never scatter hardcoded hex colors or inline `style="..."` attributes across templates.
- **Semantic HTML**: Use `<main>`, `<nav>`, `<section>`, `<dialog>`, `<button type="button">`, and explicit `<label for="...">` bindings on every form control.
