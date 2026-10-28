# Architecture 02: Google Antigravity 2.0 Governance, Lifecycle Hooks & Skills

> **Normative Specification — Subsystem 2 (`antigravity/.gemini/config/` & `templates/`)**
>
> This document specifies the runtime architecture, token-budget constraints, lifecycle hook JSON contracts (`PreToolUse`, `PostToolUse`, `PostInvocation`, `Stop`), skill discovery mechanics, and Layer 2 starter templates for Google Antigravity 2.0.

---

## 1. Three-Surface Shared Configuration (`~/.gemini/config/`)

Google Antigravity 2.0 operates across three local developer surfaces that share a single global configuration root at `~/.gemini/config/`:

| Surface | Binary / Install Location | Surface-Specific State | Shared Global Config (Stowed) |
|---------|---------------------------|------------------------|-------------------------------|
| **Antigravity 2.0 (Agents Desktop)** | `/opt/antigravity-agents/antigravity` | `~/.gemini/antigravity/` (`brain/`, MCP schemas) | `~/.gemini/config/{AGENTS.md,hooks.json,scripts/,skills/}` |
| **Antigravity IDE** | `/opt/antigravity-ide/antigravity-ide` | `~/.gemini/antigravity-ide/` | `~/.gemini/config/{AGENTS.md,hooks.json,scripts/,skills/}` |
| **Antigravity CLI (`agy`)** | `~/.local/bin/agy` | `~/.gemini/antigravity-cli/` | `~/.gemini/config/{AGENTS.md,hooks.json,scripts/,skills/}` |

---

## 2. Token Budget Engineering & Progressive Disclosure

Antigravity 2.0 enforces two strict runtime limits when loading rules into the LLM context window:
1. **Per-File Cap**: Individual rule files exceeding **24 KB** are truncated or rejected.
2. **Global Inline Budget (`defaultRulesBudget`)**: The combined size of all `always_on` rules (`~/.gemini/config/AGENTS.md` + all active workspace `.agents/rules/*.md` with `trigger: always_on`) is capped at **20,000 tokens** (~70–75 KB across a multi-repo workspace). If the combined `always_on` payload exceeds this budget, Antigravity evicts global rules from inline injection.

### Architectural Invariants for Rules & Skills

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Tier 1: Always-On Inline Rules (Strict Budget <= 20,000 tokens total)   │
│  • ~/.gemini/config/AGENTS.md (MUST stay <= 18,000 bytes; target ~16KB) │
│  • <project>/.agents/rules/{project,coding,environment}.md (always_on)  │
├─────────────────────────────────────────────────────────────────────────┤
│ Tier 2: Conditional Rules (Loaded on demand via trigger: model_decision)│
│  • <project>/.agents/rules/{governance,testing,documentation}.md        │
├─────────────────────────────────────────────────────────────────────────┤
│ Tier 3: Procedural & Workflow Skills (Loaded only when activated)       │
│  • ~/.gemini/config/skills/<name>/SKILL.md (< 500 lines, kebab-case)    │
│  • <project>/.agents/skills/<name>/SKILL.md                             │
└─────────────────────────────────────────────────────────────────────────┘
```

- **Hard Gate**: `scripts/verify-repo.sh` (Check `[5/6]`) fails CI if `antigravity/.gemini/config/AGENTS.md` exceeds **18,000 bytes**.
- **Rule vs. Skill Separation**: *Rules* govern **what** invariants must hold (concise mandates); *Skills* teach **how** to execute multi-step workflows (loaded on demand).

---

## 3. Lifecycle Hooks Architecture (`hooks.json` + `scripts/*.py`)

Antigravity 2.0 executes deterministic Python 3.14 hook scripts at four points in the agent execution lifecycle. All hooks receive a JSON payload on `stdin` and write a JSON response to `stdout`.

```mermaid
sequenceDiagram
    participant Agent as Antigravity Agent
    participant Pre as PreToolUse (pre_tool_guard.py)
    participant Tool as Workspace Tool (edit_file / run_command)
    participant Post as PostToolUse (post_edit_format.py)
    participant Inv as PostInvocation (post_invocation_lint.py)
    participant Stop as Stop (stop_verify_tests.py)

    Agent->>Pre: Tool call request (stdin JSON)
    alt Violates safety/architecture invariant
        Pre-->>Agent: {"decision": "deny", "reason": "..."}
    else Allowed
        Pre-->>Tool: {"decision": "allow"}
        Tool-->>Post: File modified (.py)
        Post->>Post: ruff format <file>
        Agent->>Inv: Turn completed
        alt Ruff or AST check_project/check_tests fails
            Inv-->>Agent: {"injectSteps": [...], "terminationBehavior": "force_continue"}
        end
        Agent->>Stop: Agent attempts to finish (NO_TOOL_CALL)
        alt Unit tests fail on modified/untracked .py files
            Stop-->>Agent: {"decision": "block", "reason": "..."}
        else All tests pass
            Stop-->>Agent: {"decision": "allow"}
        end
    end
```

### Hook Contract Reference

| Hook Event | Script | Matcher | Input (`stdin` JSON keys) | Output (`stdout` JSON contract) | Enforcement Behavior |
|------------|--------|---------|---------------------------|---------------------------------|----------------------|
| **`PreToolUse`** | [`pre_tool_guard.py`](../../antigravity/.gemini/config/scripts/pre_tool_guard.py) | `write_file\|edit_file\|replace_file_content\|multi_replace_file_content\|write_to_file\|run_command` | `toolName` (`tool_name`), `toolArgs` (`tool_input` / `parameters`) | `{"decision": "allow"}` or `{"decision": "deny", "reason": "...", "systemMessage": "..."}` | **Hard-blocks**:<br>1. Non-empty writes to consumer `src/**/__init__.py` or `tests/**/__init__.py`.<br>2. Manual edits to `alembic/versions/*.py`.<br>3. Automatic execution of mutating `git` (`add`, `commit`, `push`, `reset --hard`, `clean -f`) or `alembic` (`revision`, `upgrade`, `downgrade`) commands. |
| **`PostToolUse`** | [`post_edit_format.py`](../../antigravity/.gemini/config/scripts/post_edit_format.py) | `edit_file\|write_file\|...` | `toolArgs.Path` / `TargetFile`, `workspacePaths` | `{}` (silent formatting) | Runs `ruff format` on any edited `.py` file immediately after the write completes. |
| **`PostInvocation`** | [`post_invocation_lint.py`](../../antigravity/.gemini/config/scripts/post_invocation_lint.py) | *(All turns)* | `workspacePaths`, `invocationCount` | `{"injectSteps": [{"role": "user", "content": "...", "isEphemeral": true}], "terminationBehavior": "force_continue"}` | Detects modified **and untracked** (`git ls-files --others`) `.py` files; runs `ruff check` and AST `check_project`/`check_tests` (when `osa_framework` is present). Forces the agent to fix violations in the same turn (up to `_MAX_FORCE_CONTINUE_INVOCATIONS = 5`). |
| **`Stop`** | [`stop_verify_tests.py`](../../antigravity/.gemini/config/scripts/stop_verify_tests.py) | *(Normal stop: `NO_TOOL_CALL` / `END_TURN`)* | `workspacePaths`, `stopReason` | `{"decision": "allow"}` or `{"decision": "block", "reason": "..."}` | Runs `pytest` on unit tests corresponding to modified/untracked `.py` files and runs AST architecture/test checks before allowing the agent to conclude its turn. |

---

## 4. Global Skills Catalog (`antigravity/.gemini/config/skills/`)

Every skill resides in `antigravity/.gemini/config/skills/<name>/SKILL.md` and must declare YAML frontmatter with a `kebab-case` `name:` and `description:` (verified by `scripts/verify-repo.sh` Check `[6/6]`).

### 4.1. Interactive Slash-Command Skills (`/<name>`)

| Skill / Command | Primary Responsibility | Key Artifacts Read / Updated |
|-----------------|------------------------|------------------------------|
| **[`sopen`](../../antigravity/.gemini/config/skills/sopen/SKILL.md)** (`/sopen`) | Pulls latest `~/dotfiles-ubuntu` (`--ff-only`), restores session context across 3 tiers (`brain/` $\rightarrow$ `.agents/SESSION.md` $\rightarrow$ `git status`), and triggers project `/start` | `.agents/SESSION.md`, `WORKTASK.md`, `WORKROAD.md` |
| **[`continue`](../../antigravity/.gemini/config/skills/continue/SKILL.md)** (`/continue`) | Mid-session checkpoint: snapshots active task progress, promotes completed task blocks (`WORKTASK.md` $\rightarrow$ `CHANGELOG.md`), and delivers commit blocks | `.agents/SESSION.md`, `WORKTASK.md`, `WORKROAD.md`, `CHANGELOG.md` |
| **[`sclose`](../../antigravity/.gemini/config/skills/sclose/SKILL.md)** (`/sclose`) | End-of-session closure: runs governance promotion (Zero-Clutter Invariant), closes `.agents/SESSION.md`, emits knowledge signals, and delivers per-repo commits | `.agents/SESSION.md`, `WORKTASK.md`, `WORKROAD.md`, `BACKLOG.md`, `CHANGELOG.md` |
| **[`priority`](../../antigravity/.gemini/config/skills/priority/SKILL.md)** (`/priority`) | Enforces the deterministic priority chain (`WORKTASK.md` $\rightarrow$ `WORKROAD.md` / `BACKLOG.md` $\rightarrow$ `roadmaps/`) and Phase 0.5 deep-analysis | `WORKTASK.md`, `WORKROAD.md`, `BACKLOG.md`, `roadmaps/*.md` |
| **[`review`](../../antigravity/.gemini/config/skills/review/SKILL.md)** (`/review`) | Audits module architecture, service boundaries, 1:1 test mapping (logic files only), AAA comment separation, and 100% coverage | `src/**`, `tests/unit/**`, `tests/imp/**` |
| **[`enrich`](../../antigravity/.gemini/config/skills/enrich/SKILL.md)** (`/enrich`) | Scans active workspace `.agents/` against `~/dotfiles-ubuntu`, proposes upward promotions (`Layer C → B → A`) and downward syncs, and runs `stow -t ~ -R antigravity` | `.agents/rules/*.md`, `.agents/skills/**`, `~/dotfiles-ubuntu/antigravity/` |

### 4.2. Procedural Engineering Skills (Auto-Activated by Task Context)

| Skill Name | Activation Trigger | Core Methodology |
|------------|--------------------|------------------|
| **[`architecture-review`](../../antigravity/.gemini/config/skills/architecture-review/SKILL.md)** | Designing framework architecture, unifying classifications, or auditing documentation coherence | **5-Step Intersection Audit** + **5-Dimension Pre-Development Gate** (*Normative Specs $\rightarrow$ Reference Docs $\rightarrow$ Diagrams $\rightarrow$ Root Guides $\rightarrow$ Roadmaps*) + **4 Deterministic Verification Gates** |
| **[`governance`](../../antigravity/.gemini/config/skills/governance/SKILL.md)** | Promoting work across tiers or extracting knowledge from raw AI conversations | **One-Way Work Lifecycle** (`roadmaps/ → WORKROAD → WORKTASK → CHANGELOG`) + **3-Stage Conversation Extraction Pipeline** (*Reference Corpus $\rightarrow$ Normative Specs $\rightarrow$ Raw Source Decommissioning*) |
| **[`refactoring`](../../antigravity/.gemini/config/skills/refactoring/SKILL.md)** | Breaking down God Components (`> 400` lines), moving modules, or decommissioning features | **Zero-Residue Cutover** (no shims/aliases) + **3-Step Obsolete Test Pruning Audit** (`orphan-test-file`, dead symbol sweep, default-parameter sensitivity verification) |
| **[`testing`](../../antigravity/.gemini/config/skills/testing/SKILL.md)** | Writing unit/integration tests, fixing coverage gaps, or consolidating test suites | **Explicit 3-Comment AAA**, **Service Constructor Mock Injection**, **Anti-Characterization Trap**, and **5-Phase Test Consolidation** |
| **[`validation`](../../antigravity/.gemini/config/skills/validation/SKILL.md)** | Executing collaborative human-agent manual QA sessions | **5-Layer Validation Protocol** (Render, Interaction, Persistence, Observation, Edge Cases) tracked in `WORKVALI.md` |

---

## 5. Layer 2 Starter Templates (`templates/fastapi-hexagonal/`)

`templates/fastapi-hexagonal/` provides a ready-to-copy Layer 2/3 configuration for Python FastAPI + Hexagonal DDD + HTMX projects:
- **`rules/`**: `coding.md` (always-on), `environment.md` (always-on), `governance.md` (`trigger: model_decision`), `testing.md` (`trigger: model_decision`, including `orphan-test-file` decommissioning).
- **`skills/`**: `start/SKILL.md` (`/start`), `testing/SKILL.md` (`fastapi-testing`), `frontend/SKILL.md` (`fastapi-frontend`), `database/SKILL.md` (`fastapi-database`).
- **`governance/`**: Clean starter files for `WORKTASK.md`, `WORKROAD.md`, `WORKVALI.md`, `BACKLOG.md`, `CHANGELOG.md`, and `SESSION.md`.
