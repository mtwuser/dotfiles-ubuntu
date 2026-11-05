---
name: validation
description: Exhaustive manual validation procedure for web applications. Use when validating UI features, testing interactions, or auditing human-agent collaborative QA sessions.
---
# Skill: Manual Web Validation

## 1. Purpose

Codifies the exhaustive manual validation procedure used in human–agent
collaborative QA. When an agent assists a human with manual testing, or
executes validation autonomously (e.g. via browser tools), this skill
defines **what to check, in what order, and how to report findings**.

## 2. Validation Passes (`V1..V5`)

Every web page/feature is validated through 5 orthogonal validation passes (`V1..V5`, distinct from `rcap1` `L0..L3` capsule levels),
executed in this order:

```
V1  Render        →  Does it load? Does it look right?
V2  Interact      →  Do actions work? Do they produce correct results?
V3  Persist       →  Do changes survive a reload?
V4  Observe       →  What does the browser tell us? (console, network, DOM)
V5  Boundary      →  What happens at the edges? (empty states, errors, stress)
```

### 2.1. `V1` — Render Check

Verify initial page rendering, cache-bypass reload, layout integrity, and CSS tokens:

| Step | Action | What to verify |
|------|--------|---------------|
| 1.1 | Navigate to URL | Page loads, no blank screen, no 500 |
| 1.2 | Hard reload (Ctrl+Shift+R) | Same result on cache-bypass |
| 1.3 | Visual scan | Layout correct, no broken elements, no overflow |
| 1.4 | Framework chrome | Header/footer/nav visible if expected by framework |
| 1.5 | CSS tokens | DevTools → Elements → verify CSS custom properties active |
| 1.6 | Debug markers | Dev-mode indicators visible if enabled |

### 2.2. `V2` — Interaction Check

Verify primary, secondary, destructive, and navigation interactions in the UI:

| Step | Action | What to verify |
|------|--------|---------------|
| 2.1 | Primary action (create/submit/search) | Action completes, UI updates |
| 2.2 | Observe DOM update | Does the new element appear in the right container? Correct layout? |
| 2.3 | Secondary action (edit/update) | Changes reflected immediately in UI |
| 2.4 | Destructive action (delete/clear) | Element removed, no orphan state |
| 2.5 | Navigation | Links work, back/forward correct, no broken routes |

### 2.3. `V3` — Persistence Check

Verify that mutations, deletions, edits, and URL query state survive full page reloads:

| Step | Action | What to verify |
|------|--------|---------------|
| 3.1 | After each mutation, reload page | Data survives reload |
| 3.2 | After delete, reload page | Deletion persists |
| 3.3 | After edit, reload page | Edit persists with exact values |
| 3.4 | Check URL state | Search params, query strings preserved on reload |

### 2.4. `V4` — Observation Check (DevTools)

Inspect browser Console, Network XHR/fetch payloads, and DOM container hierarchy during interactions:

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

### 2.5. `V5` — Boundary Check

Exercise empty states, accidental/invalid inputs, rapid double-submits, and large payload rendering:

| Step | Action | What to verify |
|------|--------|---------------|
| 5.1 | Empty state | Page with zero data shows appropriate message, no broken layout |
| 5.2 | Accidental input | Typing in search by accident → no crash, debounce works |
| 5.3 | Invalid input | Required fields empty → validation message, no 500 |
| 5.4 | Rapid actions | Click submit multiple times fast → no duplicates, no race conditions |
| 5.5 | Large data | Long text, many items → layout doesn't break, scrolling works |

## 3. Execution Protocol

### 3.1. For Agent-Assisted Validation (Human tests, agent guides)

1. **Agent prepares checklist** from the project's validation tracker (`WORKVALI.md`), expanded with `V1`–`V5` passes
2. **Human executes** steps in browser, narrating observations
3. **Agent analyzes** the narration in real-time:
   - Classifies each observation as ✅ pass, ⚠️ cosmetic, or 🔴 bug
   - Cross-references errors against application source (following `1. Guides/Specs -> 2. Tests [E2E -> Imp -> Unit] -> 3. Code`)
   - Identifies root cause when possible
4. **Agent updates** `WORKVALI.md` with results and captures issues in `WORKTASK.md` / `BACKLOG.md`
5. **Automated Test Materialization (`V1–V5 -> Unit / Imp / E2E`)**: Whenever a validation defect is fixed, materialize the corresponding automated regression test (`tests/unit/` for isolated logic, `tests/imp/` for boundary/adapter implementation, or `tests/e2e/` for the vertical persona journey) inside its `Test<Module>` suite so manual QA defects never regress
6. **Human confirms** findings and decides priority

### 3.2. For Autonomous Agent Validation (with browser tools)

1. Agent starts the application server
2. Agent navigates each route using browser automation tools
3. Agent captures screenshots at each `V1` step
4. Agent executes `V2` interactions programmatically
5. Agent checks console/network for `V4` observations
6. Agent generates structured validation report

### 3.3. Narration Format (for human reports)

When a human reports observations, use this mental model to parse:

```
"I opened the landing page, looks fine"
 └── V1.1 ✅ (render check: page loads)

"Reloaded the page, all good"
 └── V1.2 ✅ + V3 ✅ (cache bypass + persistence)

"Typed a letter in the search box and the frontend shows an error"
 └── V5.2 ⚠️ (boundary: accidental input) + V4.1 🔴 (console error)

"The new item renders full-width [...] After reload it's in the grid"
 └── V2.2 ⚠️ (DOM update: wrong container) + V3.1 ✅ (persists correctly)

"I can't tell if the header/footer comes from the framework or my code"
 └── V1.4 ⚠️ (framework chrome: not distinguishable → observability gap)
```

## 4. Common Anti-Patterns Detected by This Procedure

The table below maps frequent UI/DOM anti-patterns to the validation pass (`V1..V4`) that detects them:

| Pattern | How it surfaces | Root cause | Prevention |
|---------|----------------|------------|------------|
| Dynamic insert outside wrapper | V2.2: element outside grid/list after create | JS/HTMX inserts before wrapper element | Return full list content, use `innerHTML` swap |
| Browser extension console error | V4.1: error from `<anonymous>` source | Extension injects monitoring scripts | Verify in incognito mode |
| Missing framework observability | V1.4: can't distinguish framework vs app HTML | No visual/DOM markers | Add data attributes + dev-mode overlay |
| State loss on dynamic update | V3.4: URL state lost after partial update | Missing URL push on navigation | Push URL state on search/filter actions |

## 5. Validation Report Template

After completing a validation session, the report follows this structure:

```markdown
## [Application Name] — Validation Report

**Date**: YYYY-MM-DD
**Tester**: human | agent | collaborative
**Environment**: [dev/staging/production]

### Results

| Pass | Check | Result | Notes |
|------|-------|--------|-------|
| V1 | Landing renders | ✅ | |
| V1 | Reload | ✅ | |
| V2 | Create | ✅ | |
| V2 | Edit | ✅ | |
| V2 | Delete | ✅ | |
| V3 | Persistence | ✅ | |
| V4 | Console clean | ⚠️ | Extension error (not app) |
| V4 | Dynamic update | ⚠️ | Layout inconsistency on create |
| V5 | Empty state | ✅ | |

### Issues Found

1. **[BUG/COSMETIC]** Description → promoted to task tracker / captured in backlog
```
