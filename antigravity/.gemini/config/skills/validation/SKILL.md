---
name: validation
description: Exhaustive manual validation procedure for web applications. Use when validating UI features, testing interactions, or auditing human-agent collaborative QA sessions.
---
# Skill: Manual Web Validation

## Purpose

Codifies the exhaustive manual validation procedure used in human–agent
collaborative QA. When an agent assists a human with manual testing, or
executes validation autonomously (e.g. via browser tools), this skill
defines **what to check, in what order, and how to report findings**.

## Validation Layers

Every web page/feature is validated through 5 orthogonal layers,
executed in this order:

```
L1  Render        →  Does it load? Does it look right?
L2  Interact      →  Do actions work? Do they produce correct results?
L3  Persist       →  Do changes survive a reload?
L4  Observe       →  What does the browser tell us? (console, network, DOM)
L5  Boundary      →  What happens at the edges? (empty states, errors, stress)
```

### L1 — Render Check

| Step | Action | What to verify |
|------|--------|---------------|
| 1.1 | Navigate to URL | Page loads, no blank screen, no 500 |
| 1.2 | Hard reload (Ctrl+Shift+R) | Same result on cache-bypass |
| 1.3 | Visual scan | Layout correct, no broken elements, no overflow |
| 1.4 | Framework chrome | Header/footer/nav visible if expected by framework |
| 1.5 | CSS tokens | DevTools → Elements → verify CSS custom properties active |
| 1.6 | Debug markers | Dev-mode indicators visible if enabled |

### L2 — Interaction Check

| Step | Action | What to verify |
|------|--------|---------------|
| 2.1 | Primary action (create/submit/search) | Action completes, UI updates |
| 2.2 | Observe DOM update | Does the new element appear in the right container? Correct layout? |
| 2.3 | Secondary action (edit/update) | Changes reflected immediately in UI |
| 2.4 | Destructive action (delete/clear) | Element removed, no orphan state |
| 2.5 | Navigation | Links work, back/forward correct, no broken routes |

### L3 — Persistence Check

| Step | Action | What to verify |
|------|--------|---------------|
| 3.1 | After each mutation, reload page | Data survives reload |
| 3.2 | After delete, reload page | Deletion persists |
| 3.3 | After edit, reload page | Edit persists with exact values |
| 3.4 | Check URL state | Search params, query strings preserved on reload |

### L4 — Observation Check (DevTools)

| Step | Action | What to verify |
|------|--------|---------------|
| 4.1 | Console tab open during ALL interactions | No errors (red), no unexpected warnings |
| 4.2 | Network tab: XHR/fetch requests | Correct request method, headers, response format |
| 4.3 | Network tab: status codes | 200/201 for success, 4xx for client errors, no 500s |
| 4.4 | Elements tab: DOM after dynamic update | New element inside correct parent container |
| 4.5 | Source attribution | External errors (browser extensions, 3rd-party) vs application code |

> **Key heuristic**: If a JS error shows `<anonymous>:2:NNNNN` with minified
> function names like `et.reportAllChanges`, it's likely a browser extension,
> not application code. Verify by testing in incognito without extensions.

### L5 — Boundary Check

| Step | Action | What to verify |
|------|--------|---------------|
| 5.1 | Empty state | Page with zero data shows appropriate message, no broken layout |
| 5.2 | Accidental input | Typing in search by accident → no crash, debounce works |
| 5.3 | Invalid input | Required fields empty → validation message, no 500 |
| 5.4 | Rapid actions | Click submit multiple times fast → no duplicates, no race conditions |
| 5.5 | Large data | Long text, many items → layout doesn't break, scrolling works |

## Execution Protocol

### For Agent-Assisted Validation (Human tests, agent guides)

1. **Agent prepares checklist** from project validation tracker, expanded with L1–L5 layers
2. **Human executes** steps in browser, narrating observations
3. **Agent analyzes** the narration in real-time:
   - Classifies each observation as ✅ pass, ⚠️ cosmetic, or 🔴 bug
   - Cross-references errors against application source (grep for stack trace symbols)
   - Identifies root cause when possible
4. **Agent updates** validation tracker with results and captures issues in task tracker/backlog
5. **Human confirms** findings and decides priority

### For Autonomous Agent Validation (with browser tools)

1. Agent starts the application server
2. Agent navigates each route using browser automation tools
3. Agent captures screenshots at each L1 step
4. Agent executes L2 interactions programmatically
5. Agent checks console/network for L4 observations
6. Agent generates structured validation report

### Narration Format (for human reports)

When a human reports observations, use this mental model to parse:

```
"I opened the landing page, looks fine"
 └── L1.1 ✅ (render check: page loads)

"Reloaded the page, all good"
 └── L1.2 ✅ + L3 ✅ (cache bypass + persistence)

"Typed a letter in the search box and the frontend shows an error"
 └── L5.2 ⚠️ (boundary: accidental input) + L4.1 🔴 (console error)

"The new item renders full-width [...] After reload it's in the grid"
 └── L2.2 ⚠️ (DOM update: wrong container) + L3.1 ✅ (persists correctly)

"I can't tell if the header/footer comes from the framework or my code"
 └── L1.4 ⚠️ (framework chrome: not distinguishable → observability gap)
```

## Common Anti-Patterns Detected by This Procedure

| Pattern | How it surfaces | Root cause | Prevention |
|---------|----------------|------------|------------|
| Dynamic insert outside wrapper | L2.2: element outside grid/list after create | JS/HTMX inserts before wrapper element | Return full list content, use `innerHTML` swap |
| Browser extension console error | L4.1: error from `<anonymous>` source | Extension injects monitoring scripts | Verify in incognito mode |
| Missing framework observability | L1.4: can't distinguish framework vs app HTML | No visual/DOM markers | Add data attributes + dev-mode overlay |
| State loss on dynamic update | L3.4: URL state lost after partial update | Missing URL push on navigation | Push URL state on search/filter actions |

## Validation Report Template

After completing a validation session, the report follows this structure:

```markdown
## [Application Name] — Validation Report

**Date**: YYYY-MM-DD
**Tester**: human | agent | collaborative
**Environment**: [dev/staging/production]

### Results

| Layer | Check | Result | Notes |
|-------|-------|--------|-------|
| L1 | Landing renders | ✅ | |
| L1 | Reload | ✅ | |
| L2 | Create | ✅ | |
| L2 | Edit | ✅ | |
| L2 | Delete | ✅ | |
| L3 | Persistence | ✅ | |
| L4 | Console clean | ⚠️ | Extension error (not app) |
| L4 | Dynamic update | ⚠️ | Layout inconsistency on create |
| L5 | Empty state | ✅ | |

### Issues Found

1. **[BUG/COSMETIC]** Description → promoted to task tracker / captured in backlog
```
