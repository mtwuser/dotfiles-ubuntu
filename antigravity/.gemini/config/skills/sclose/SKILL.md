---
name: sclose
description: full session close — recap, consolidation, commits, and summary
---

# Session Close — `/sclose`

> **End of work session.** Closes the session entry, delivers final commits, and provides a summary.
> For task-level cleanup (task tracker, CHANGELOG), see `/continue` §2.5 — that happens between tasks, not at session close.

---

## 1. Session Recap

Summarize **everything accomplished** in the session:

```markdown
## Session Summary — [date]

### Completed
- [Item 1: brief description]
- [Item 2: brief description]

### Deferred
- [Items started but not finished, with reason]
```

---

## 2. Close SESSION.md Entry

1. **Update the current session entry** in `.agents/SESSION.md`:
   - Finalize **Completed** list
   - Update **Uncommitted** to reflect any remaining changes
2. **Prune Session Log** — keep a maximum of 5 entries (oldest are already captured in CHANGELOG)

> [!IMPORTANT]
> **SESSION.md content is preserved within a session.** Only prune entries from *previous* sessions,
> never delete work logged in the current session.

---

## 2.5. Governance Promotion (if applicable)

> [!IMPORTANT]
> `/sclose` **MUST** run governance promotion before delivering commits. This is the same
> logic as `/continue` §2.5, ensuring completed work is always finalized regardless of
> whether `/continue` was run during the session.

Scan the task tracker for **fully completed task blocks** (every item `[x]`):

1. **Detect completion** — if a task block has ALL sub-items marked `[x]` (deferred items count as complete)
2. **If found**, execute governance promotion in ONE step:
   a. **Write CHANGELOG entry** — add user-facing summary under `[Unreleased]` (user language, no filenames)
   b. **Delete the task block** — remove entire block from the task tracker (`WORKTASK.md`) + remove row from Priority Summary table
   c. **Clean active roadmap/backlog** — delete the completed phase/item from `WORKROAD.md` / `BACKLOG.md` (Zero-clutter invariant: never leave `~~strikethrough~~`)
   d. **Delete implemented phases from source roadmap** — remove the completed phase section(s) from the origin roadmap file in `roadmaps/`. If ALL phases of a roadmap are implemented, delete the entire file.
3. **If no completed blocks** → proceed to Inline Work scan (do NOT skip entirely)

**Inline Work scan** (MANDATORY — always runs):

> [!IMPORTANT]
> Even if no task blocks are found, scan `BACKLOG.md` and `WORKROAD.md` for items completed during this session
> without task block promotion (inline/direct implementation). If found:
> a. **Delete the completed item** from `BACKLOG.md` / `WORKROAD.md` (Zero-clutter invariant)
> b. **Write CHANGELOG entry** if the work is user-facing
> c. **Delete implemented phases from source roadmap** if applicable
> d. **Multi-Repo Parity**: If multiple repositories (e.g., shared platform + consumer services) were modified during the session, update `CHANGELOG.md` and verify `README.md` directory trees (§10) in **every** modified repository before delivering commits.

---

## 3. Deliver Commits

Follow commit rules in `/continue` (`skills/continue/SKILL.md` §3) — provide commit commands for **all repos with changes**.

> [!IMPORTANT]
> Steps 1–2.5 must be fully complete before this step. All edits (SESSION.md, task tracker, backlog, CHANGELOG)
> must be saved BEFORE delivering commits — commits are always the absolute last output.

> [!NOTE]
> **Post-commit convention**: The `**Uncommitted**` field written in Step 2 records the state
> *before* commits are delivered. Future agents running `/sopen` must treat historical
> `Uncommitted` fields as snapshots, not current state — only `git status` determines current state.

---

## 3.5. Global Config Sync (Post-Commits)

If any shared rules, skills, or system config in `dotfiles-ubuntu` were modified during this session, run `cd ~/dotfiles-ubuntu && make verify` first to confirm all 8 verification gates pass, log changes under `## [Unreleased]` in `CHANGELOG.md` without bumping `VERSION`, and include a local commit block (do NOT append `git push` or `(vX.Y.Z)` unless explicitly requested via `/release`):

```bash
### dotfiles-ubuntu
cd ~/dotfiles-ubuntu
git add -A
git commit -m "<summary of config changes>"
```

> [!NOTE]
> Only include this commit block if files in `dotfiles-ubuntu` were actually edited.
> Check agent memory for file writes to paths containing `dotfiles-ubuntu`.
> If no changes → skip silently.

---

## 3.6. Knowledge Signal (active reflection)

Two-part scan for knowledge enrichment:

### Part A — File Change Detection (passive)

1. **Check**: Were any files in `.agents/rules/`, `.agents/skills/`, or `dotfiles-ubuntu/` modified during this session?
2. **If YES** → append to the session summary:
   ```
   💡 Rules/skills were modified. Consider running `/enrich` to evaluate upstream promotion.
   ```

### Part B — Behavioral Pattern Detection (active)

3. **Reflect**: Did the user correct the agent's behavior, catch recurring errors, or point out patterns that the agent should have detected autonomously during this session?
4. **If YES** → analyze each correction:
   - **Root cause**: Why did the agent fail? Missing mandate? Mandate too vague? Agent not following an existing mandate?
   - **Rule gap or rule drift?**: Is this a NEW pattern that no existing rule covers, or is it an existing rule that the agent failed to apply?
   - **Propose**: Suggest a concrete rule addition or refinement targeting the specific failure mode.
   - Append to the session summary:
   ```
   💡 Behavioral pattern detected: [brief description]. Consider adding/refining rule in [target layer].
   ```
5. **If NO** → skip silently (zero overhead)

---

## 4. Final Summary

One-paragraph natural language recap for the user — what was done, what's next per `/priority`.

---

## 5. Rules

- **ALWAYS update SESSION.md** — this is mandatory, no exceptions
- **ALWAYS deliver commits** — do not ask whether the user wants them
- **ALWAYS run governance promotion** — `/sclose` is the last chance to finalize completed work
- **Keep the recap concise** — bullet points, not paragraphs
