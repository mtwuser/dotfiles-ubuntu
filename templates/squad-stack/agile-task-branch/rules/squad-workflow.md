---
trigger: always_on
description: "Human-agent squad collaboration, task-tag claiming, and Git task-branch workflow rules (agile-task-branch)."
---

# Squad Collaboration & Task-Branch Workflow (`agile-task-branch`)

> Standardizes how human operators and AI agents collaborate inside `Department -> Squad -> Project` workspaces using traceable task tags, isolated Git branches, and 1-hop upward Pull Requests.

---

## Scope & Surface Target

- **Template Pack**: `templates/squad-stack/agile-task-branch/` (`squad-stack`, `target_role: squad`).
- **Applies**: Squad and Project workspaces that coordinate multi-member delivery against `WORKTASK.md` and `WORKROAD.md`.

---

## Normative Invariants

> *"One task tag, one isolated branch, one verified Pull Request."*

1. **Task Onboarding (`make task TASK=<id-or-text>`)**:
   - Start every task by running `./scripts/layer-config.sh start-task . --task "<id-or-text>"` (or `make task TASK="<id-or-text>"`).
   - This marks the item `[/]` in `WORKTASK.md`, records the active task and branch in `.agents/SESSION.md`, and outputs the canonical branch command (`git checkout -b task/<id>-<slug>`).
2. **Traceable Task Tags (`[DEPT-YYYY-NNN]` / `[SQUAD-NNN]`)**:
   - Preserve parent delegation tags (`[P0 · Delegated from <dept> ...]`) and task IDs (`[LEGAL-2026-004]`, `[TECH-042]`) in `WORKTASK.md`, `CHANGELOG.md` (`## [Unreleased]`), and PR descriptions.
3. **1-Hop Escalation & Upward Delivery (`make promote`)**:
   - Never mutate inherited department or corporate rules (`layer-NN-*.md`) in place.
   - Propose rule improvements, roadmap updates, or blocker escalations 1-hop upward via `./scripts/layer-config.sh promote-from-project . --source <rel-path> --create-pr` (`make promote SOURCE=<rel-path>`).
4. **Inter-Department & Cross-Squad Consultation**:
   - When a task requires verifying another department's policy or another squad's contract, use a read-only ephemeral consultation (`orchestrate_ephemeral_fork` with `access_mode="strictly-read-only"`) rather than copying foreign repositories into the workspace.

---

## Verification & Sign-Off Gates

- [ ] Active task is marked `[/]` during execution and `[x]` in `WORKTASK.md` before delivering the commit block.
- [ ] `.agents/SESSION.md` reflects the active task branch (`task/<id>-<slug>`) and latest checkpoint.
- [ ] `make diff` (`layer-config.sh diff-project`) reports zero unintended drift against inherited layer templates.
