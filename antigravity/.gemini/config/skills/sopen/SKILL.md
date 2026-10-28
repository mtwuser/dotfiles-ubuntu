---
name: sopen
description: restore session state and initialize workspace — first command in every conversation
---

# Session Open — `/sopen`

> **Run this FIRST** in every new conversation. It restores context, applies governance rules, and presents the current state.

---

## 0. Global Config Sync (Pre-Recovery)

// delegate: flash
1. **Locate `dotfiles-ubuntu`** — check if `~/dotfiles-ubuntu/` exists (or resolve from workspace metadata)
2. **If found** — run `cd ~/dotfiles-ubuntu && git pull --ff-only`
   - If pull succeeds → config is up to date from other machines
   - If pull fails (conflicts) → notify user: "dotfiles-ubuntu has conflicts. Resolve manually before continuing."
   - Do NOT auto-resolve conflicts in shared config
   - If `~/dotfiles-ubuntu/layers/` has mounted subtrees (`./scripts/layer-subtree.sh list`) or `~/dotfiles-ubuntu/logs/mcp_alerts.jsonl` contains recent `CRITICAL`/`WARN` entries, surface a one-line note in the session header.
3. **If not found** → skip silently (user may not use dotfiles on this machine)

> [!NOTE]
> This step ensures that rules and skills modified on another machine
> are available before the agent loads them. It runs ONCE at session start.

---

## 1. Recover Conversation Context (Tier 1 — richest source)

// delegate: flash
1. **Identify current machine** — resolve the hostname from the system (e.g., workspace metadata or `hostname` command). This is used to match Session Log entries to this machine.
2. **List `~/.gemini/antigravity/brain/`** to find all conversation directories
3. **Read `.agents/SESSION.md`** — find **two** conversation IDs:
   - **Last session (any machine)** — the top (most recent) Session Log entry
   - **Last session (this machine)** — the most recent entry where `**Machine**` matches the current hostname
   - If both are the same → single recovery path. If different → dual recovery (see below)
4. **Match** each relevant conversation ID to brain/ directories and **read** artifacts:
   - `task.md` — what was being worked on and its completion state
   - `walkthrough.md` — what was verified and delivered
   - `implementation_plan.md` — what was planned (may reveal in-progress work)
5. **If no matching brain/ directory**, scan the 2-3 most recent brain/ directories (by modification time) and read their `task.md` files

> [!IMPORTANT]
> This tier is the **primary source of truth** for what was actually done.
> SESSION.md may be stale if the session closed unexpectedly (no `/sclose` was run).
> **NEVER deduce** — always read artifacts before presenting state.

> [!NOTE]
> **New machine / fresh clone**: If `brain/` is empty or doesn't contain the conversation
> referenced in SESSION.md, this is normal. Skip to Tier 2 — `SESSION.md` (portable, git-tracked)
> and Tier 3 (git state) are sufficient to recover context. Report Tier 1 as "not available
> (new machine)" in the status presentation.

---

## 2. Read Session State (Tier 2 — portable cross-device)

// delegate: flash
1. **Read `.agents/SESSION.md`** — extract from the cumulative format:
   - **Top Session Log entry** — most recent session: conversation ID, machine, completed items
   - **Last entry for this machine** — if different from top entry, read it too (reveals this machine's last known state)
   - If any entry has a **Resume from** note → this is the exact continuation point

2. **Cross-reference against Tier 1 artifacts**:
   - If `walkthrough.md` documents verified work not in any Session Log entry → SESSION.md missed it
   - Trust Tier 1 artifacts over SESSION.md when they conflict

> [!CAUTION]
> **Historical `Uncommitted` fields are snapshots, not current state.** Each Session Log entry
> records what was uncommitted *at the time of session close*. After the user commits manually,
> these lines become stale but remain in the log (append-only). **Only Tier 3 (`git status`)
> determines current uncommitted state.** Never treat a past entry's `Uncommitted` field as
> actionable — always verify against git.

---

## 3. Verify Against Code (Tier 3 — ground truth)

// delegate: flash
3. **Check git state across all repos** in a single command.
   Resolve the project root from the workspace metadata (the root workspace folder path).
   Dynamically detect sub-repos and run ONE combined command:

   ```bash
   PROJECT_ROOT="<PROJECT_ROOT>"  # Resolve from workspace metadata
   # Find all git repos: root + immediate subdirectories with .git
   REPOS="$PROJECT_ROOT"
   for d in "$PROJECT_ROOT"/*/; do
     [ -d "$d/.git" ] && REPOS="$REPOS $d"
   done
   for repo in $REPOS; do
     echo "=== $(basename "$repo") ==="
     cd "$repo"
     git status --short
     git log --oneline -3
     BRANCH=$(git branch --show-current)
     echo "unpushed:" && git log --oneline origin/$BRANCH..HEAD 2>/dev/null
     BEHIND=$(git rev-list --count HEAD..origin/$BRANCH 2>/dev/null)
     [ "$BEHIND" -gt 0 ] 2>/dev/null && echo "BEHIND origin by $BEHIND commits"
   done
   ```

   Parse the output to identify: uncommitted changes, unpushed commits, and behind-origin status.
   If any repo is behind origin → flag explicitly with count and recommendation.

4. **Resolve conflicts** — when SESSION.md and git disagree:
   - SESSION.md says "pending commits" but git is clean → already committed, SESSION.md stale (historical snapshot — not an error)
   - SESSION.md says "completed" but no git commit exists → work was lost or not committed
   - Unpushed commits exist → flag them explicitly
   - Local behind origin → another machine pushed changes; recommend `git pull --ff-only`

---

## 4. Present Status

Present a structured summary:

```
## Session Recovery

**Current machine**: [hostname]
**Last session (this machine)**: [date] · conv [id]
**Last session (any machine)**: [date] · conv [id] · machine [name] (only if different)

### 🔍 Recovery Sources
- Tier 1: [brain/ artifacts found/not found]
- Tier 2: [SESSION.md status: current/stale/missing]
- Tier 3: [git state summary + behind-origin status]

### ✅ Completed
- [items verified against Tier 1 artifacts + git commits]

### 📦 Uncommitted / Unpushed
- [repos with uncommitted changes or unpushed commits]
- (only from current git status — NEVER from historical SESSION.md entries)

### 📡 Cross-Machine Sync (only if behind origin)
- [repos behind origin with commit count]
- Recommendation: `git pull --ff-only` in each behind repo before starting work

### 🎯 Next (per /priority)
- [next task from active task tracker → backlog → roadmaps/]
```

---

## 5. Rules

- **NEVER ask** "what do you want to do?" — present the next step per `/priority`
- **NEVER start working** — only present state and propose. Wait for user confirmation
- **NEVER deduce** — always read brain/ artifacts and SESSION.md before presenting state
- **Tier precedence**: brain/ artifacts (richest) → SESSION.md (portable) → git (ground truth for code)
- **When SESSION.md conflicts with git**, trust git for code state (commits, changes)
- **When SESSION.md conflicts with brain/ artifacts**, trust artifacts for work state (what was done)
- **Historical Uncommitted is NOT current state** — SESSION.md `Uncommitted` fields in past entries are snapshots. Only `git status` determines current uncommitted state.
- **Machine identification**: Always determine the current hostname and match against Session Log `**Machine**` entries.
- **New machine**: If Tier 1 is empty, Tier 2 + Tier 3 are sufficient. Do not treat missing brain/ artifacts as an error.
- **Path resolution**: Never hardcode absolute paths. Resolve all repo paths dynamically from workspace metadata.
- **Behind origin**: If any repo is behind origin, present the sync recommendation prominently. Do NOT auto-pull — let the user decide.
- After presenting, the user may:
  - Confirm → proceed with governance rules and work
  - Redirect → user gives a different task
  - Request commits → execute `/continue commits` for uncommitted changes

---

## 6. Edge Cases — Session Lifecycle Gaps

### No `/sopen` before work

**Scenario**: User opens Antigravity and starts working directly without running `/sopen`.

**Agent behavior**: If `/continue` or `/continue commits` is called without a prior `/sopen`, the agent should:
1. **Detect the gap** — check if SESSION.md was updated in this conversation. If not, this is a session without `/sopen`.
2. **Adopt the session gracefully** — create the session entry in SESSION.md as part of the `/continue` snapshot step. Do NOT force the user to re-run `/sopen`.
3. **Warn once**: _"No `/sopen` was run at session start. Session entry created. Consider running `/sopen` when opening each new chat for full context."_

**User action**: Not required. The agent self-heals. For best context, run `/sopen` first next time.

### Unexpected close (no `/sclose`)

**Scenario**: Antigravity closes unexpectedly (crash, closed tab, internet drop) without `/sclose`.

**What becomes stale**: `SESSION.md` still shows the last **committed** session entry, not the work done after. Brain artifacts (`task.md`, `walkthrough.md`) may be partially written.

**Recovery in next `/sopen`**:
1. `/sopen` Step 3 runs `git status` across all repos → detects uncommitted changes from the crashed session
2. `/sopen` Step 1 reads brain artifacts → detects partially completed task.md
3. **Conflict resolution**: git state (Tier 3) is ground truth for what files changed. Brain artifacts (Tier 1) show what the agent was doing. SESSION.md (Tier 2) may be outdated.
4. Present the gap clearly: _"SESSION.md appears outdated. Git shows uncommitted changes not recorded in the last session entry."_

**User action**: Run `/sopen` normally — its multi-tier recovery handles this automatically. Then decide:
- `/continue commits` to commit the orphaned changes
- Or discard them with `git checkout .` if unwanted
