---
trigger: always_on
description: Universal cognitive, organizational, and dotfiles-ubuntu orchestration rules applying to all workspaces
---
# Antigravity Universal Rules (`human-base` Global Baseline)

> Universal cognitive, organizational, and `dotfiles-ubuntu` orchestration rules applying to ALL workspaces. Domain rules layer via **`science-base`** (`science-stack/software-engineering`) and **`business-base`** (enterprise & normative governance).

---

## Agent Behavior

- **Description**: Universal behavioral mandates, cognitive mindset, and execution rigor
- **Applies**: Always

### Agent Behavior Manifesto

Verify these mandates before proposing solutions or modifying files in any workspace:

#### 1. Reusability First (Consistency)
> *"Preserve workspace consistency and maximize reuse before introducing new abstractions."*

**Mandate:** Scan (`grep`/semantic) for existing patterns before creating functions, components, templates, or policies; consolidate shared assets in a canonical location.

#### 2. Professional Robustness & Modularity (No Shortcuts)
> *"Always choose the most robust, scalable, and structured approach over a quick patch."*

**Mandate:** Reject superficial workarounds when a scalable, parameterized structure is attainable.
- **File Size Gate (`< 465` lines)**: Keep every source, test, root `README.md`, and `docs/**/*.md` or `corporate/**/*.md` file `< 465` lines (target $\le 400$); extract modules, `docs/guides/`, or specs before `465` lines.

#### 3. Verification & Quality Integrity
> *"Zero unresolved validation, schema, linter, or compliance errors."*

**Mandate:** No task is complete while verification (`make verify`, `audit.sh`, `layer-config.sh diff-project`), linters, or compliance checks report errors or warnings.

#### 4. Atomic Deliverable & Verification Inclusion
> *"Never deliver a change without its corresponding verification."*

**Mandate:** Pair logic/policies with `AAA` verification (`science-base` / `business-base`). Report **`1:1` verified** (`Code <-> Test`) or **`1:1:1` verified — `100.00%` coverage (`stmts`, `branches`; `1:1` isolated) & Markdown links verified** (`Spec/Docs <-> Test <-> Code`).

#### 5. Specification Hierarchy, Reading Priority & 5-Surface Ripple
> *"Review canonical specifications first and propagate changes across all linked surfaces."*

**Mandate:** Run `make status` / `make verify` first, follow **`1. Guides/Specs/Policies -> 2. Verification/Tests -> 3. Implementation`**, and treat `docs/`, `corporate/`, and specs as supreme law.
- **5-Surface Ripple:** Derive from `docs/` or `corporate/` specs (`Locate -> Extract -> Instantiate -> Cross-verify`) across **5 surfaces**: `1. Rule/Function -> 2. CLI/Process -> 3. Makefile/Hook -> 4. Spec/Ledger Table -> 5. Docs/Verification`.

#### 6. Continuous Consolidation
> *"Consolidate and complete documentation continuously over time."*

**Mandate:** Treat documentation and governance ledgers as living code. Update `WORKTASK.md`, `BACKLOG.md`, `CHANGELOG.md`, and architecture guides upon completing a phase.

#### 7. The Zero-Backward Law & Forensic Intent Resolution (`[WIRE]` / `[CONSOLIDATE]` / `[PRUNE]`)
> *"Never leave backward-compatibility shims or delete unreferenced items without forensic check."*

**Mandate:** Execute clean cutovers on code, schemas, policies, or manifests (`schema_version`, JSON/YAML/TOML) — zero polyfills, aliases (`OldType = NewType`), shims, `if legacy:`, or `@deprecated`. Check `git log -S` + `docs/` before deleting and classify as **`[WIRE]`**, **`[CONSOLIDATE]`**, or **`[PRUNE]`**.

#### 8. Mandatory Pre-Commit Hygiene & Zero-Literal Exclusion (Anti-Streisand Gate)
> *"Never finish a task leaving script residue, broken side effects, or exclusion literals."*

**Mandate:** Before delivering `git commit` blocks: (1) **Pesticide Scan** (delete scratch files); (2) **Side-Effect Coherence** (`make verify`, `audit.sh`, `layer-config.sh`); (3) **Sterile Root** (`git status --short`); (4) **Multi-Repo Parity** (`CHANGELOG.md`, `README.md`, tests); (5) **Zero-Literal Exclusion** (zero private identifiers in rules/tests/scripts).

#### 9. Exhaustive Planning, Bounded-Lot Execution & Persona Validation (`Human <-> AI <-> Tech`)
> *"Validate every plan and change by walking each human user archetype end-to-end."*

**Mandate:** (1) **Additive Plans** mapping side-effects; (2) **Persona Journey Walkthrough** (*Individual*, *Root 0*, *Department*, *Consumer* from `docs/guides/` to CLI); (3) **Bounded-Lot Execution (`3–5` files/lot for `> 6`-file sweeps)**, **No Phase Compression** & **Execution Block** until approval; (4) **Zero Scope Creep** (`BACKLOG.md`).

#### 10. Documentation Coherence, 2D Disclosure, Closed-Loop Libraries & `L1` Exon Readiness
> *"Keep rules as concise guardrails and delegate deep corpora to Federated Knowledge Libraries."*

**Mandate:**
1. **3-Tier & 2D Progressive Disclosure (`README.md` $\rightarrow$ `docs/guides/` $\rightarrow$ `docs/{architecture,reference}/`)**:
   - **Tiers 1–3**: `README.md` ($\le 400$ lines) $\rightarrow$ `docs/guides/*.md` (`< 465` lines, `E1` `M1..M4` guides) $\rightarrow$ `docs/{architecture,reference}/*.md` (`< 465` lines, `E3/E2` `1:1:1` specs).
   - **2D Geometry & `L1` Exons**: Put conceptual columns left and file/test pointers right; order `#..####` (`H1..H4` cap, `0` `#####`) top-to-bottom with a **1-line lead sentence** before tables/diagrams/code and **`###` (`H3`) subsections**.
2. **Closed-Loop Guardrail-to-Library Reference (`Stacks` $\leftrightarrow$ `Libraries` `gov-*`, `sci-*`, `geo-*`, `org-*`) & Context Comprehension**:
   - Keep `.agents/rules/` as concise guardrails; link deep technical, statutory, territorial, academic, or corporate corpora in Federated Libraries via `citation_receipt` (`<layer>::<file>#<slug>@<digest16>:<E3..E0>`) and `l3_targets`.
   - Consume extensive corpora via `rcap1` (`L0 -> L1 -> L2 -> L3`), `consumer_viewpoint` (`M1..M2` $\rightarrow$ `docs/guides/` + `academic-tutor`; `M3..M4` $\rightarrow$ `docs/reference/` `E3/E2`), `GRCC`/`DMCP`, and `Q1..Q4` telemetry. Sync trees (`find`/`ls`) and verify links (`test -f`).

#### 11. `dotfiles-ubuntu` Native Self-Guidance, Task-Branch & Inter-Layer Lifecycle
> *"Use deterministic CLI orchestrators (`layer-config.sh`, `layer-subtree.sh`) over ad-hoc steps."*

**Mandate:** Operate the `dotfiles-ubuntu` multi-layer architecture natively:
1. **CLI & Task-Branch Cycle (`make status`, `make task`, `make complete`, `make consult`, `make delegate`, `make promote`, `make sync`)**:
   - Claim via `make task TASK="<id>"` (`[/]` in `WORKTASK.md`, `.agents/SESSION.md`, `git checkout -b feature/<TICKET-ID>-<slug>`); close via `make complete TASK="<id>"` (`[x]`).
   - Query via `make consult LAYER=<id> QUERY="<text>"` (`rcap1`), delegate 1 hop down (`make delegate`), and propose 1 hop up (`make promote`).
2. **3 Universal Bases (`base-stack`: `human-base`, `science-base`, `business-base`) + 3 Stacks + Libraries (`gov-*`, `sci-*`, `geo-*`, `org-*`)**:
   - **`$HOME` vs. `Workspace`**: `$HOME` (`~/.gemini/config/AGENTS.md`) holds the baseline; `Workspace` (`<repo>/.agents/`) projects the active layer + `layers/*` (`0..80`) + `Human-Stack` (`85..95`: `M1..M4`). Switch via `./scripts/layer-config.sh set-global-profile <human-base|science|technical|business|full> --stow`.
3. **Scoped Workspace Execution (`antigravity-agents`) & Layer Authority**: Scopes rules per Workspace Root (`.agents/rules/layer-<NN>-<name>.md` by `precedence` `0..100`, `Non-Workspace File Access: allow|deny|ask`). Layer owners (`set-authority` / `check-authority`) govern releases; consumers propose 1-hop PRs (`promote-from-project --create-pr` / `inspect-horizon`).
4. **Workstation Hook Gates (`pre_tool_guard.py`)**: Blocks automated mutating Git commands (`git add`, `git commit`, `git push`, `git reset --hard`, `git clean -f`, `git subtree`), `alembic` migrations, edits to `alembic/versions/*.py` or `.agents/rules/layer-*.md`, and writes (`> 0 bytes`) to `src/**/__init__.py` or `tests/**/__init__.py`.

#### 12. Model Delegation Discipline (`flash` vs `inherit` vs `pro` & 4-Channel Digest)
> *"Never spend a heavy model on a mechanical task."*

**Mandate:** Select tiers deliberately: `flash` for mechanical sweeps (`// delegate: flash`), `inherit` for architectural judgment, and `pro` for deep reasoning or `L3` unfolding. Require a **4-channel digest**: (1) **Domain State**, (2) **Affected Surface**, (3) **Invariants & Constraints**, (4) **Actionable Delta**.

#### 13. Language Purity, Semantic Naming Synthesis & Pre-Edit Scope Gate
> *"Zero language mixing, synthesize intent into canonical terminology, and zero unannounced edits."*

**Mandate:** (1) **Single-Language Purity**: Respond in Spanish; keep repository artifacts in 100% technical English. (2) **Semantic Naming Synthesis**: Deduce intent and propose canonical naming over literal conversational phrasing. (3) **Pre-Edit Scope Blueprint**: Present target files/symbols before multi-file edits. (4) **Collateral Freeze**: Never modify untouched files in the same turn; log in `BACKLOG.md`.

---

## Governance (Universal)

- **Description**: Commit discipline, priority chain, holistic analysis scope, and global config persistence
- **Applies**: Always

### Commit Discipline
1. **NEVER run mutating git commands** (`git add`, `git commit`, `git push`, `git commit --amend`, `git reset`) automatically.
2. **ONE single commit per repo** using Conventional Commits (`feat:`, `fix:`, `chore:`, `refactor:`, `test:`, `docs:`).
3. **Independent repos**: Deliver a separate commit block per repo (`cd <REPO_PATH> && git add ... && git commit -m "..."`).
4. **Task tracking sync is MANDATORY** before delivering commits (`skills/continue/SKILL.md`).
5. **Force-tracked `.gitignore` files**: Use `git add -u` (`+ git add -f <new_file>`) so `WORKTASK.md`, `WORKROAD.md`, `BACKLOG.md`, and `CHANGELOG.md` stay staged.
6. **Working Commits vs. Releases (`[Unreleased]` Standard)**: **NEVER** bump `VERSION`/`pyproject.toml`/`README.md`, append `(vX.Y.Z)`, or chain `git push` during iteration; log under `## [Unreleased]` in `CHANGELOG.md` and release only via `/release` (`skills/release/SKILL.md`).

### Priority Chain & Global Config Persistence
- **Priority Chain**: (1) `WORKTASK.md` $\rightarrow$ (2) `WORKROAD.md` / `ROADMAP.md` / `BACKLOG.md` $\rightarrow$ (3) `roadmaps/`. Never suggest ad-hoc work.
- **Global Config & Skills**: `$HOME/dotfiles-ubuntu` (`~/<user-pc>` in `mode=private`, read-only in `mode=readonly`); author upstream in `DOTFILES_DEV_REPO_DIR` (`make setup-dev`/`promote`) and prefer `.agents/skills/`.
