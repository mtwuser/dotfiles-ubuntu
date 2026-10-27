---
name: fastapi-frontend
description: Frontend patterns for HTMX, Jinja2 templates, and Preact/Vue Islands in {PROJECT_NAME}
---
# Skill: HTMX & Islands Conventions — {PROJECT_NAME}

## Zone Architecture Quick Reference

| Zone | Tech | Client JS | When |
|:----:|------|:---------:|------|
| Z1 | Server HTML (Jinja2) | 0 KB | Landing, docs, static |
| Z2 | HTMX + Alpine.js | ~30 KB | CRUD, forms, tables, filters |
| Z3 | Preact/Vue Island + SSE | ~35 KB/island | Chat, dashboards, streaming |
| Z4 | Dedicated library | ~200+ KB | 3D viewers, code editors |

## Z1: Pure Server HTML

```html
{# templates/{context}/list.html #}
{% extends "base.html" %}
{% block content %}
  <h1>{{ title }}</h1>
  <ul>
    {% for item in items %}
      <li>{{ item.name }}</li>
    {% endfor %}
  </ul>
{% endblock %}
```

- No JavaScript. No HTMX attributes.
- Every page starts as Z1. Promote only when justified.

## Z2: HTMX Patterns

### Partial Swap (Core Pattern)
```html
{# templates/{context}/list.html #}
<div id="item-list">
  {% include "{context}/partials/item_table.html" %}
</div>

<button hx-get="/api/{context}/items?page=2"
        hx-target="#item-list"
        hx-swap="innerHTML">
  Load More
</button>
```

### Form Submission (List CRUD)
```html
{# ✅ CORRECT — return full list partial, swap innerHTML #}
<form hx-post="/api/{context}/items"
      hx-target="#item-list"
      hx-swap="innerHTML">
  <input name="name" required />
  <button type="submit">Add</button>
</form>
```

> **Anti-pattern**: Never use `hx-swap="afterbegin"` or `"beforeend"` on targets
> that wrap conditional containers (e.g. grid vs empty state). The inserted element
> lands outside the wrapper. Always return the full list partial and use `innerHTML`.

### Search with Debounce
```html
<input type="search"
       name="q"
       hx-get="/api/{context}/items/search"
       hx-trigger="input changed delay:300ms"
       hx-target="#results" />
```

### Template Organization
```
templates/{context}/
├── list.html              # Full page (extends base.html)
├── detail.html            # Full page (extends base.html)
└── partials/              # HTMX swap fragments
    ├── item_table.html    # Table body fragment
    ├── item_row.html      # Single row fragment
    └── item_form.html     # Form fragment
```

### FastAPI Endpoint Pattern (Canonical)

Always use the centralized `respond_template(request, template, context, partial=...)` helper (and `respond_poll(..., done=...)` for polled endpoints returning HTTP 286 on completion) instead of manual `HX-Request` header checks or raw `TemplateResponse()`:

```python
@router.get("/{context}/items", response_class=HTMLResponse)
async def list_items(
    request: Request,
    q: str | None = None,
) -> Response:
    items = await service.list_items(search=q)
    return respond_template(
        request,
        "{context}/list.html",
        {"items": items, "query": q or ""},
        partial="{context}/partials/_item_table.html",
    )
```

> **Best practice**: Centralize HTMX partial detection in `respond_template(request, template=..., partial=...)` so endpoints never return a full HTML document (or raw JSON) into an HTMX swap target.

## Z3: Islands Architecture

### Island Mount Point
```html
{# In Jinja2 template #}
<div data-island="chat-widget"
     data-props='{{ island_props | tojson }}'
     data-sse-url="/api/chat/stream">
  <p>Loading...</p>  {# SSR fallback #}
</div>
```

### Island Loader (vanilla JS)
```javascript
// static/js/island-loader.js (~2 KB)
document.querySelectorAll('[data-island]').forEach(async (el) => {
  const name = el.dataset.island;
  const props = JSON.parse(el.dataset.props || '{}');
  const { mount } = await import(`/static/islands/${name}.js`);
  mount(el, props);
});
```

### IslandBus (Inter-Island Communication)
```javascript
// static/js/island-bus.js
const IslandBus = {
  listeners: new Map(),
  emit(event, data) {
    (this.listeners.get(event) || []).forEach(cb => cb(data));
  },
  on(event, callback) {
    if (!this.listeners.has(event)) this.listeners.set(event, []);
    this.listeners.get(event).push(callback);
  }
};
export default IslandBus;
```

## Rules

1. **Z1 by default**: Every page starts as server HTML. Promote only when justified.
2. **HTMX fragments are partials**: Always in `partials/` subdirectory.
3. **Always use `respond_template` with `partial`**: Never use `TemplateResponse()` directly for Z2.
4. **List CRUD uses `innerHTML`**: Return full list partial, never `afterbegin`/`beforeend`.
5. **Islands are isolated**: Z3/Z4 mount into `data-island` containers. They do NOT control page layout.
6. **Zero-build**: No webpack, no Vite. Vendor libraries as single ES module files. CSS is vanilla.
7. **SSE for streaming**: Z3 islands connect via SSE for real-time data.
8. **Progressive enhancement**: Page works without JS (Z1 fallback). JS enhances, never replaces.
