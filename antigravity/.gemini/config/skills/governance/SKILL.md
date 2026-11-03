---
name: governance
description: "Use when promoting work between tiers (roadmaps → active → done), delegating 1-hop downward directives to child layers, writing CHANGELOG entries, or extracting architectural knowledge from raw conversation files."
---

# Governance Skill

## Part 1 — Promotion Flow and Changelog

> **When to use**: Use this skill when moving items between work tiers (`roadmaps/`, active backlog, task tracker), or when completing a feature and writing the `CHANGELOG.md`.

### Promotion Flow

Work flows strictly from left to right:
`roadmaps/ → WORKROAD.md (or ROADMAP.md) / BACKLOG.md → WORKTASK.md → CHANGELOG.md`

#### 1. Future Roadmap (`roadmaps/`) → Active Roadmap (`WORKROAD.md` / `ROADMAP.md`)
- Select the next roadmap by priority number.
- Execute **deep-analysis** before promotion according to the active `workspace_mode` (`make status` / `.agents/rules/*.md`):
  - **Technical / Hybrid Mode (`technical-base` / `tech-stack/*`)**: `1. Guides/Specs -> 2. Tests [E2E -> Imp -> Unit] -> 3. Code` (audit specs, tests, and code).
  - **Business Mode (`business-base` / `business-stack/*` / `Root 0` / `Department`)**: `1. Normative Policies & Lex Superior (0..100) -> 2. Corporate Ledgers (corporate/) & Traceable IDs ([DEPT]-[TYPE]-[YYYY]-[NNN]) -> 3. Cross-Surface Contracts & Sign-Off Gates` (audit corporate ledgers, policies, and downstream department/squad impact).
- Enrich the roadmap with your findings, then promote its phase checklist to `WORKROAD.md`.

#### 2. Active Roadmap / Backlog (`WORKROAD.md` / `BACKLOG.md`) → Active Tasks (`WORKTASK.md`)
- Promote one phase at a time.
- If `WORKTASK.md` already has items, run cross-task analysis first to detect dependencies and shared components.
- Move the phase to `WORKTASK.md`, renaming the prefix as needed (e.g. `R1` to `T1`).

#### 3. Active Tasks (`WORKTASK.md`) → Done (`CHANGELOG.md`)
- Completed items are DELETED from `WORKTASK.md`, `WORKROAD.md`, and `BACKLOG.md`. Do not leave them as strikethrough (`~~`) or checkmarks.
- Log completed work exclusively in `CHANGELOG.md`.

### Mode Discipline ("Capture, don't act")

When working on a specific task, you might spot unrelated improvements:
1. **Capture**: Add a one-line observation to `BACKLOG.md`.
2. **Continue**: Return to your current task immediately.
3. **Never mix modes**: E.g., do not refactor an unrelated file while writing tests for a new feature.

### CHANGELOG Entries & `[Unreleased]` Release Discipline

Always write for the **USER** (or downstream adopter), not internal scratch notes:
- **Always log ongoing work under `## [Unreleased]`**: During active development, place all `### Added`, `### Changed`, and `### Fixed` entries under `## [Unreleased]` at the top of `CHANGELOG.md`.
- **Never bump `VERSION` prematurely**: Keep `VERSION`, `pyproject.toml`, and `README.md` badges at the last published release on `origin`. Never append `(vX.Y.Z)` to ordinary work commits or chain `git push` by default.
- **Explicit Release Cuts (`/release`)**: Only promote `## [Unreleased]` $\rightarrow$ `## [X.Y.Z] - YYYY-MM-DD`, bump `VERSION`, and deliver a tag/push block when the user explicitly triggers `/release` (`skills/release/SKILL.md`).
- Explain how the user's experience or the system's external behavior changed.
- ✅ *Good*: "Profile section streamlined with real-time notification count."
- ❌ *Bad*: "Refactored ProfileService.get_stats() to use aggregate query and serializers."

---

## Part 2 — Knowledge Extraction & Architectural Integration from Raw Conversations

> **When to use**: Use this procedure when extracting deep architectural knowledge from raw planning conversations or AI chat logs (`input`/`output` transcripts) and integrating the findings into a project's reference and normative architecture documentation.

### The 3-Stage Extraction & Integration Pipeline

#### Stage 1 — Exhaustive Reference Extraction & Gap Analysis (`docs/reference/`)
1. **Sequential Segment Reading**: Read the raw conversation file in complete, non-overlapping line segments (never sample or skip middle sections) to extract 100% of domain insights, invariants, and architectural mechanisms.
2. **Structured Reference Corpus**: Synthesize the extracted concepts into structured reference documents under `docs/reference/<topic>.md` (`< 465` lines per file), updating `docs/README.md` and `README.md`.
3. **Fit & Gap Matrix**: Classify each extracted mechanism against the current architecture (`100% Aligned`, `Conceptual Enrichment`, or `Actionable Gap`) and present the gap analysis before modifying normative specs.

#### Stage 2 — Normative Architectural & Roadmap Integration (`docs/architecture/` & `roadmaps/`)
1. **Theoretical & Reference Foundations**: Add formal sections to the project's reference guides (`docs/reference/*.md`) and human workflow guides (`docs/guides/*.md`).
2. **Normative Specifications (`1:1:1`)**: Integrate the approved mechanisms, `1:1:1` (`Spec <-> Source <-> Unit Test`) tables, and glossary definitions into the authoritative architecture documents (`docs/architecture/*.md`).
3. **Roadmap Propagation**: Update pending roadmap files (`roadmaps/*.md`) so future implementation phases incorporate the newly formalized invariants.

#### Stage 3 — Raw Source Decommissioning (Zero-Residue)
- Once 100% of the extracted insights are verified in `docs/reference/` and `docs/architecture/`, **delete the temporary raw conversation file** so no unindexed chat dumps remain in the repository.
- Alternatively, when processing massive multi-file queues incrementally across multiple turns, apply **Destructive Queue Ingestion** (popping synthesized line ranges from the source file after each checkpoint until the file reaches `0 bytes` and is removed).

---

## Part 3 — Inter-Layer Operational & Business Governance (`Root 0 <-> Department <-> Squad <-> Project`)

> **When to use**: Use this procedure in `corporate-root` (`corporate`), `domain-policy`, `department`, `squad`, or `project` workspaces to orchestrate reciprocal task delegation (`make delegate`), ticket-linked branch execution (`make task`), inter-layer consultation (`make consult`), upward completion receipts (`make complete`), bottom-up roadmap/ledger proposals (`make promote`), isomorphic `dev -> tst -> pre -> pro` stage gates (`make env-gate`), 4-role roster management (`make roster`), and non-destructive proposal decisions (`make decision`).
> *(For promoting Antigravity agent rules `.agents/rules/*.md`, skills `.agents/skills/*/SKILL.md`, or reusable `templates/**`, use **`/enrich`** instead.)*

### 0. Command Cadence & Human-Consciousness Tiers (`command_tiers` in `make status`)

Match execution autonomy to the operation's cadence, consolidation level, and blast radius:
- **`C1: auto_reflexive` (High-Frequency / Consolidated & Automated — `0` cross-layer mutation)**: `make status`, `make diff`, `make horizon`, `make upstream-diff`, `make consult`, `make authority`, `make mcp-test`, `make lint`, `make format`, `make test-unit`, `make test-imp`, `make test-e2e`, `make verify`, `/sopen`, `/review`. Safe for the agent to run autonomously (`// delegate: flash`).
- **`C2: guided_tactical` (Per-Task / Intra-Layer Transitions — local workspace state)**: `make task`, `make sync`, `compare-upstream --apply-safe`, `make setup-dev`, `make workstation-sync`, `/priority`, `/continue`, `/sclose`, `/full-audit`. Agent prepares local trackers/state and presents the branch/commit block or blueprint for user execution.
- **`C3: conscious_human_gated` (Low-Frequency / High-Consciousness Inter-Layer & Authority Gates)**: `make delegate`, `make complete`, `make promote`, `make env-gate`, `make decision`, `make roster`, `/enrich` (§4), `/release`. Never auto-chain silently; always surface the **1-Hop Impact Summary** (`origin -> target`, ticket/proposal ID, authority check) and require explicit human intent.

### 1. Top-Down 1-Hop Directive & Artifact Delivery (`make delegate` / `delegate-to-child`)

1. **Enforce the 1-Hop Horizon, Strict Intra-Workspace Subtree Containment (`layers/<child>/`) & Dual Authority Gate**:
   - `Root 0` (`corporate`) delivers exclusively to its immediate child `Department` / `domain-policy` layers mounted under `layers/<child-layer-id>/` (`Department` delivers to `Squad`). Never skip tiers and **never mutate or suggest `cd <sibling-repo> && git commit` on external sibling directories outside `<PROJECT_ROOT>`**.
   - **Same-Owner Direct Subtree Mode (`delivery_mode: "direct_subtree"`)**: When the parent actor is also an authorized `owner` or `maintainer` of `layers/<child>/system/mcp-layer.json`, `make delegate` updates `layers/<child>/<surface>` in place and emits `./scripts/layer-subtree.sh push <child> <branch>`.
   - **Cross-Owner Proposal / PR Mode (`delivery_mode: "proposal_pr"`, `--create-pr` or `CROSS_OWNER_CHILD_DELEGATION`)**: When the parent actor is not an authorized owner/maintainer of the child layer (or `--create-pr` is passed), `make delegate` stages the directive or artifact non-destructively under `layers/<child>/.agents/proposals/from-<parent-id>/`, adds a `P0` review item in `layers/<child>/WORKTASK.md`, and emits `./scripts/layer-subtree.sh push <child> delegate/<TICKET-ID>` for child-owner PR review.
2. **Traceable Ticket Registration (`## Outbound Delegations`) & Non-Destructive Staging**:
   - **Trackers (`WORKTASK.md`, `BACKLOG.md`, `WORKROAD.md`, `ROADMAP.md`, `WORKVALI.md`)**: Appends a traceable directive (`- [ ] **[P1 · [<TICKET-ID>] · Delegated from '<parent-id>']**: ...`) into `layers/<child>/<tracker>` (or stages a proposal if cross-owner) and logs `- [/] **[<TICKET-ID> -> <child-id> (<surface>, stage: delegated)]**` under `## Outbound Delegations` in the parent's `WORKTASK.md`.
   - **Roadmaps, Corporate Ledgers & Rules (`roadmaps`, `corporate`, `rules`)**: Delivers `--source <rel-path>` into `layers/<child>/<surface>`. If the target file already exists and `--force` is not passed (or if cross-owner), stages non-destructively at `layers/<child>/.agents/proposals/from-<parent-id>/<file>` and adds a `P0` review item in `layers/<child>/WORKTASK.md`.
   ```bash
   make delegate CHILD=<child-layer-id> [TASK="<directive>"] [TICKET=<TICKET-ID>] [SOURCE=<rel-path>] [SURFACE=WORKTASK.md|BACKLOG.md|WORKROAD.md|WORKVALI.md|roadmaps|rules|corporate] [PRIORITY=P0|P1|P2]
   ```

### 2. Child Execution (`make task`), Ephemeral Consultation (`make consult`) & Reciprocal Completion (`make complete`)

1. **Claim Task & Create Ticket-Linked Feature Branch (`make task` / `start-task`)**:
   ```bash
   make task TASK="<ticket-id-or-text>" [TICKET=<TICKET-ID>]
   # Marks item [/] in WORKTASK.md, records Ticket ID & Origin Layer in .agents/SESSION.md,
   # and emits: git checkout -b feature/<TICKET-ID>-<descriptive-slug>
   ```
2. **One-Shot Read-Only Inter-Layer Consultation (`make consult` / `consult-layer`)**:
   ```bash
   make consult LAYER=<target-layer-or-template> QUERY="<question>"
   # Spawns a strictly-read-only ephemeral fork, returns a 4-Channel Executive Digest + rcap1 capsules, and auto-reaps.
   ```
3. **Close Task & Emit Upward Completion Receipt (`make complete` / `complete-task`)**:
   ```bash
   make complete TASK="<ticket-id-or-text>" [DELIVERABLE=<rel-path>]
   # Marks item [x] in child WORKTASK.md and reciprocally updates parent WORKTASK.md
   # (## Outbound Delegations -> [x] ... stage: completed (pro)), or stages
   # .agents/proposals/to-<parent>/completion-<ticket>.md + PR plan (feature/<TICKET-ID>-completed).
   ```

### 3. Bottom-Up Operational Proposals (`make promote`), Stage Gates (`make env-gate`), Roster (`make roster`) & Decisions (`make decision`)

1. **Bottom-Up Roadmap, Ledger & Tracker Proposals (`make promote` / `promote-from-project --create-pr`)**:
   - Escalates operational/business artifacts (`roadmaps/*.md`, `corporate/**`, `docs/**`, `BACKLOG.md`, `WORKROAD.md`, `WORKVALI.md`) 1 hop upward via PR (staging non-destructively at `.agents/proposals/to-<parent>/` when protected):
     ```bash
     make promote SOURCE=<roadmaps/file.md|corporate/policy.md|WORKVALI.md|BACKLOG.md>
     ```
2. **Isomorphic Business & Technical `dev -> tst -> pre -> pro` Promotion Gate (`make env-gate`)**:
   - Verifies stage readiness (`0` open `P0` in `WORKTASK.md` for `tst`, `0` unchecked items in `WORKVALI.md` + `validator` / `owner` authority for `pre`, `CHANGELOG.md` + `owner` release authority for `pro`):
     ```bash
     make env-gate ENV=<tst|pre|pro>
     ```
3. **4-Role Roster & `.github/CODEOWNERS` Sync (`make roster` / `manage-roster`)**:
   - Maintains `owners`, `maintainers`, `validators`, and `members` in `system/mcp-layer.json` and syncs `.github/CODEOWNERS`:
     ```bash
     make roster [ADD=<email>] [REMOVE=<email>] [ROLE=owner|maintainer|validator|member]
     ```
4. **Human Governance Decision Recording (`make decision` / `record-decision`)**:
   - Resolves pending staged proposals or blocked governance items in `WORKTASK.md`, `.agents/SESSION.md`, and `logs/governance_audit.jsonl`:
     ```bash
     make decision ITEM=<proposal-or-ticket> DEC=<approve|reject|defer|blocked> REASON="<justification>"
     ```
