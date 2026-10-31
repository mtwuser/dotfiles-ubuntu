---
name: continue
description: mid-session checkpoint — safety valve to prevent context loss between tasks
---

# Continue — `/continue`

> **The universal checkpoint.** Snapshot state, clean completed work, deliver commits, and present what's next.

---

## Scopes

| Scope | What it does |
|-------|-------------|
| `/continue` | Full flow: snapshot → alignment → cleanup → commits → next step |
| `/continue commits [scope]` | Commits only (scope: specific repo name or all) — skip next-step |

> [!NOTE]
> `/continue` always includes commits when there are changes. Use `/continue commits` only when you want commits without the full flow.

---

## 1. Snapshot Current State

1. **Update `.agents/SESSION.md`** — prepend new entry or update existing one in place.
2. **Sync task tracker progress** — mark completed sub-items `[x]`, in-progress `[/]`, update metrics
3. **Track changed repos from agent memory** — list affected repos in SESSION.md. **Do NOT run `git status`.**
4. **Document context** — if task is partially done, note the exact stopping point

---

## 2. Verify Alignment

1. **Re-read task tracker** — confirm no drift from active task scope
2. **Anti-drift check**: Compare work against original task description → flag if drifted
3. **Staleness check**: Scan open items for obsolescence from design changes → flag and propose removal

---

## 2.5. Clean Completed Work (Governance Promotion)

After alignment, scan for **all completed work** — task blocks, backlogs, AND inline work:

### Task Blocks (promoted tasks from backlog)

1. **Detect completion** — task block has ALL sub-items `[x]` (deferred = complete)
2. **Check repos are clean** — if uncommitted changes exist:
   - Deliver commits first (§3)
   - **STOP** — promotion deferred to next `/continue` after commits are clean
3. **If repos are clean** — execute full promotion in ONE step:
   a. **CHANGELOG entry** — ONE bullet per feature under `[Unreleased]`. Max 2 lines. User-facing language only — no filenames, test counts, class names.
   b. **Delete the task block** from task tracker (`WORKTASK.md`) + Priority Summary table row
   c. **Clean active roadmap/backlog** — delete the completed phase/item from `WORKROAD.md` / `BACKLOG.md` (Zero-clutter invariant: never leave completed items or `~~strikethrough~~`)
   d. **Delete implemented phases** from source roadmap in `roadmaps/`. If ALL phases done, delete the file.
   e. **No completed tracking** in the backlog — completed work lives in CHANGELOG only.

### Inline Work (completed without task block promotion)

> [!IMPORTANT]
> **Catches work implemented directly without task block promotion.** Task block governance only fires
> for promoted tasks. Inline work silently skips governance without this step.

1. **Scan backlog (`BACKLOG.md` / `WORKROAD.md`)** — compare session work (SESSION.md + conversation) against pending items
2. **If any item was fully implemented** without a task block:
   a. Delete the completed item from `BACKLOG.md` / `WORKROAD.md` (Zero-clutter invariant)
   b. Write CHANGELOG entry if user-facing
   c. Delete implemented phases from source roadmap if applicable
3. **MANDATORY** — runs every `/continue` and `/sclose`, regardless of task block state

### Backlogs (standing sections in task tracker)

1. **Delete `### Completed ✅` sections** — historical noise, already in CHANGELOG/git
2. **Delete fully-completed backlog blocks** — no remaining `[ ]` items → delete entire block
3. **Keep only actionable items** — header, context note, and pending `[ ]` items

> [!IMPORTANT]
> **Safety margin**: Promotion NEVER runs in same `/continue` that marks last item `[x]` — uncommitted changes force a commit-first pause. `[x]` items are transient — once promoted, delete them. Completed work lives in CHANGELOG and git only.

---

## 3. Scope-Specific Action

### Default (`/continue`)

1. **Idempotency** — skip commits if already delivered with no new changes; skip snapshot if unchanged
2. **Deliver commits** — if uncommitted changes exist, deliver commit commands (§3 Commits)
3. **Conversation context** — if last interaction concluded with an agreement → **execute it directly**; if no actionable conclusion → step 4
4. **In-progress work** — if `[/]` items exist in task tracker, present remaining items first
5. **Follow `/priority`** — only if no context and no in-progress work: `task tracker → backlog → roadmaps/`
6. **Present next task** — user approves (→ execute) or closes

> [!IMPORTANT]
> **Conversation context always wins.** `/continue` does NOT jump to the priority chain if the user just approved something. The priority chain is a fallback.

### Commits (`/continue commits [scope]`)

#### Pre-Commit Verification Checklist

> [!IMPORTANT]
> **Before writing ANY commit**, answer these 4 questions:
> 1. Which repos did I actually edit files in?
> 2. Did I already deliver commits earlier? → only include repos with NEW changes since.
> 3. Did I remove all completed items from `BACKLOG.md` / `WORKROAD.md`? (§2.5 Inline Work — Zero-clutter invariant)
> 4. Is SESSION.md updated and saved?

#### Strict Rules

1. **NEVER run mutating git commands** — no `git add/commit/push/amend`. User handles all git mutations.
2. **Agent memory = source of truth** — deliver commits for edited repos directly. No `git status` verification.
3. **If uncertain** (context loss) — run `git status --short` per-repo individually.
4. **ONE commit per repo** — never split.
5. **Format** — resolve `<PROJECT_ROOT>` from workspace metadata. Dynamically detect sub-repos. Only include repos with changes. **NEVER** append `(vX.Y.Z)` to working commit messages, **NEVER** bump `VERSION` mid-iteration, and **NEVER** include `git push` by default unless the user explicitly asks to push or runs `/release` (`skills/release/SKILL.md`):

```bash
### <Root Repo>
cd <PROJECT_ROOT>
git add -A
git commit -m "<summary of ALL root changes>"

### <Sub-Repo>
cd <PROJECT_ROOT>/<sub-repo>
git add -A
git commit -m "<summary of ALL sub-repo changes>"
```

Same pattern for any additional sub-repos when applicable.

6. Commit message = concise summary, not a list. No commentary around commits.
7. **Sub-repos are INDEPENDENT nested repos, NOT submodules.** Listed in `.gitignore`. NEVER stage a sub-repo from root.
8. **Force-tracked `.gitignore` files**: If a repository force-tracks files listed in `.gitignore` (such as `WORKROAD.md`, `WORKTASK.md`, `WORKVALI.md`, `BACKLOG.md`, `.agents/SESSION.md`, or `roadmaps/*.md`), use `git add -u` (plus `git add -f <new_file>` for newly created files inside ignored directories) instead of passing individual ignored pathspecs without `-f`, ensuring modified governance files are never left unstaged.
9. **Commit frequency**: after each plan execution, after accumulated changes, before session end.
10. **Sync task tracker before commits** — mark `[x]`/`[/]` sub-items first.
11. **Global config repo** — if `dotfiles-ubuntu` files were modified (antigravity config, shell config, or system manifests), include a separate commit block for it (same format, `cd ~/dotfiles-ubuntu`).

> [!IMPORTANT]
> **Auto-commit after plan execution**: When plan finishes (all `[x]`), deliver commits **immediately** as final step — snapshot → sync task tracker → commits → present next step. Never require the user to invoke `/continue` just for commits.

---

## 4. Rules

- **NEVER skip the snapshot** — persist state before looking ahead
- **NEVER start new work** without presenting pending items first
- **SESSION.md is mandatory** — the lifeline for session continuity
- **Task tracker sync before ANY commit** — even ad-hoc requests must sync `[x]`/`[/]` first
- **Plan execution = one fluid unit** — implement, commit, present next step in one flow
- **Idempotent** — no repeated commits if nothing changed since last delivery
