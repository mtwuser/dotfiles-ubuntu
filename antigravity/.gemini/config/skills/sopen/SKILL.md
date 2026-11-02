---
name: sopen
description: restore session state and initialize workspace — first command in every conversation
---

# Session Open — `/sopen`

> **Run this FIRST** in every new conversation. It restores context, applies governance rules, and presents the current state.

---

## 0. Single-Shot Global Sync & Consolidated Workspace Status

// delegate: flash
1. **Run ONE combined command** in `<PROJECT_ROOT>` to fast-forward `~/dotfiles-ubuntu` and collect the entire workspace status digest in `< 0.2s`:
   ```bash
   ~/dotfiles-ubuntu/scripts/workstation-sync.sh --sync 2>/dev/null || true
   ~/dotfiles-ubuntu/scripts/layer-config.sh status "<PROJECT_ROOT>"
   ```
   *(If `Makefile` defines `status:`, `make status` runs `layer-config.sh status` with `PARENT_DIR` automatically.)*
2. **Parse the returned JSON digest** — it provides in a single call:
   - `operating_state` (`"oss-readonly-appliance"` | `"oss-dev"` | `"corporate-root"` | `"domain-policy"` | `"department"` | `"squad"` | `"project"`), `workspace_mode` (`"business"` | `"technical"` | `"hybrid"`), `layer_id`, `layer_role`, `precedence`, `active_templates`, `active_rules`, and `command_tiers` (`auto_reflexive`, `guided_tactical`, `conscious_human_gated`)
   - **Read-Only Appliance Gate**: If `operating_state == "oss-readonly-appliance"` (`~/dotfiles-ubuntu` with `.workstation-state.json`), warn immediately that `$HOME/dotfiles-ubuntu` is a read-only runtime appliance and redirect any authoring to `DOTFILES_DEV_REPO_DIR` (`make setup-dev`).
   - `has_project_start_skill` (`bool` — if `false`, do NOT search for `.agents/skills/start/SKILL.md`)
   - `session_state` (`exists`, `last_conversation_id`, and `excerpt` of `.agents/SESSION.md`)
   - `priority_state` (`active_tracker` and `excerpt` of `WORKTASK.md` / `WORKROAD.md` / `ROADMAP.md` / `BACKLOG.md` / `README.md`)
   - `git_state` (`is_git_repo`, `status_short` including branch and ahead/behind status, `recent_commits`)
   - `horizon` (`oss_root_version`, `upstream_version`, `workspace_version`, `downward_sync_needed`, `child_sync_needed`, `shared_template_drifts`, `downstream_layer_drifts`, `upward_promotion_suggestions`)
   - `git_governance` (`current_branch`, `active_environment`, `makefile_outdated`, `manifest_contracts_outdated`, `staged_proposals`, `stale_proposals`)
   - `agent_diff` (`in_sync`, `modified_in_project`, `novel_in_project`)
3. **Assisted Upgrade Reconciliation (`make sync`)**:
   - **If `horizon.downward_sync_needed`, `horizon.child_sync_needed`, `git_governance.makefile_outdated`, or `git_governance.manifest_contracts_outdated` is `true`**, run `make sync` (or `~/dotfiles-ubuntu/scripts/layer-config.sh sync-layer "<PROJECT_ROOT>"`) using the default non-destructive `--strategy reconcile`. This self-heals generated `# Role-Specialized Layer Makefile` targets in place (preserving any `# --- Custom Targets ---` block), normalizes `mcp-layer-v1` / `squad` manifest contracts, and updates unmodified upstream template packs and mounted child layers (`layers/*`).
   - **If `reconciliation_conflicts` or `git_governance.staged_proposals` (`from-upstream/*`) are present**, run `make upstream-diff` (`~/dotfiles-ubuntu/scripts/layer-config.sh compare-upstream "<PROJECT_ROOT>"`) to inspect section-level differences (`upstream_only_sections`, `local_only_sections`, `diverged_sections`) and ask the user which reconciliation strategy to apply:
     - `make sync STRATEGY=accept-upstream` — adopt the upstream template pack in full
     - `make sync STRATEGY=merge` — adopt upstream updates while preserving local-only `# / ## / ###` rule sections
     - `make sync STRATEGY=keep-local` — keep local rule customizations untouched and clear the staged proposal

> [!NOTE]
> This single-command pre-flight replaces separate calls to `make horizon`, `make diff`, `git status`, `git log`, `.agents/SESSION.md`, and tracker file probes.

---

## 1. Recover Conversation Context (Tier 1 — richest source)

// delegate: flash
1. **Check `session_state.last_conversation_id`** from the Step 0 JSON digest:
   - **If `last_conversation_id` is non-null**: read `~/.gemini/antigravity/brain/<last_conversation_id>/task.md` (and `walkthrough.md` / `implementation_plan.md` if present) directly by path.
   - **If `last_conversation_id` is `null`** (fresh workspace or `.agents/SESSION.md` was just initialized): **skip `brain/` scanning completely** — do NOT run `ls -lt ~/.gemini/antigravity/brain/` or inspect conversations belonging to other workspaces.
2. **If `.agents/SESSION.md` lists a separate entry for the current hostname**, read that conversation's `brain/<id>/task.md` directly as well.

> [!IMPORTANT]
> When `last_conversation_id` is present in `.agents/SESSION.md`, `brain/<last_conversation_id>/` is the **primary source of truth** for what was done in the previous session. Never blind-scan unrelated `brain/` directories when `last_conversation_id` is `null`.

> [!NOTE]
> **New machine / fresh clone**: If `brain/` is empty or doesn't contain the conversation
> referenced in SESSION.md, this is normal. Skip to Tier 2 — `SESSION.md` (portable, git-tracked)
> and Tier 3 (git state) are sufficient to recover context. Report Tier 1 as "not available
> (new machine)" in the status presentation.

---

## 2. Read Session State & Active `Human-Stack` Profile (Tier 2 — portable cross-device)

// delegate: flash
1. **Use `session_state.excerpt` from Step 0** (or read `.agents/SESSION.md` in full only if the excerpt is truncated):
   - **Top Session Log entry** — most recent session: conversation ID, machine, completed items
   - **Last entry for this machine** — if different from top entry, read it too (reveals this machine's last known state)
   - If any entry has a **Resume from** note → this is the exact continuation point
2. **Adopt the Operator's Optional `Human-Stack Profile` (`precedence: 85..95`)**:
   - Inspect `.agents/SESSION.md` (*Case 2: personal evolving `Human-Stack`*), `.agents/LAYER_LINEAGE.md` or `README.md` (*Case 3: Squad/Department onboarding directive*), or any punctual in-chat request (*Case 1*) using the specificity chain `In-Chat Override -> Personal .agents/SESSION.md -> Team Blueprint -> Default (Case 0 when blank/omitted)`.
   - When one or more atomic `Human-Specs` (`domain-<area>:L1..L4`, `bridge-*`, `soft-*`, `hat-*`) are declared, adapt explanation depth, cross-discipline vocabulary bridges (`bridge-tech-for-business` / `bridge-business-for-tech`), and Socratic guidance accordingly while keeping all organizational and technical gates (`precedence: 0..80`) strictly invariant.

3. **Cross-reference against Tier 1 artifacts**:
   - If `walkthrough.md` documents verified work not in any Session Log entry → SESSION.md missed it
   - Trust Tier 1 artifacts over SESSION.md when they conflict

> [!CAUTION]
> **Historical `Uncommitted` fields are snapshots, not current state.** Each Session Log entry
> records what was uncommitted *at the time of session close*. After the user commits manually,
> these lines become stale but remain in the log (append-only). **Only Tier 3 (`git_state`)
> determines current uncommitted state.** Never treat a past entry's `Uncommitted` field as
> actionable — always verify against git.

---

## 3. Verify Against Code & Priority (Tier 3 — ground truth)

// delegate: flash
1. **Use `git_state` and `priority_state` from the Step 0 JSON digest** (`status_short`, `recent_commits`, `active_tracker`, and `excerpt`). Do NOT re-run `git status`, `git log`, or probe `WORKTASK.md` / `WORKROAD.md` / `BACKLOG.md` separately for a single-repo workspace.
2. **Multi-Repo Parent Workspace Only**: If `<PROJECT_ROOT>` is a parent folder containing multiple independent git repositories (`*/.git`), run a single loop across sub-repos to check `git status --short --branch` and `git log --oneline -3`.

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
- **`.agents/SESSION.md` preservation**: Never run `rm -rf .agents` inside an active workspace (even to simulate clean CI checkouts), because `.agents/` is gitignored and contains `.agents/SESSION.md` (Tier 2 session recovery state).
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
