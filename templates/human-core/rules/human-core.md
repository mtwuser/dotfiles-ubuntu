# Antigravity Universal Rules (`human-core` Global Baseline)

> Universal cognitive, organizational, and `dotfiles-ubuntu` orchestration rules applying to ALL workspaces. Domain rules layer via **`technical-base`** (software engineering) and **`business-base`** (enterprise & normative governance).

---

## Agent Behavior

- **Description**: Universal behavioral mandates, cognitive mindset, and execution rigor
- **Applies**: Always

### Agent Behavior Manifesto

Verify these mandates before proposing solutions or modifying files in any workspace:

#### 1. Reusability First (Consistency)
> *"Preserve workspace consistency and maximize reuse before introducing new abstractions or documents."*

**Mandate:** Scan the workspace (`grep` or semantic search) for existing patterns before creating new functions, components, templates, or policies. Consolidate shared assets in a canonical location and reference rather than duplicating.

#### 2. Professional Robustness & Modularity (No Shortcuts)
> *"Always choose the most robust, scalable, and structured approach over a quick patch."*

**Mandate:** Reject superficial workarounds when a scalable, parameterized structure is attainable.
- **File Size Gate (`< 465` lines)**: Keep every source, test, and navigable `docs/**/*.md` or `corporate/**/*.md` file strictly `< 465` lines (target $\le 400$). Extract cohesive modules or specs before exceeding `465` lines (exempt from `§9.4`).

#### 3. Verification & Quality Integrity
> *"Zero unresolved validation, schema, linter, or compliance errors."*

**Mandate:** No task is complete while verification scripts (`make verify`, `audit.sh`, `layer-config.sh diff-project`), linters, or compliance checks report errors or warnings.

#### 4. Atomic Deliverable & Verification Inclusion
> *"Never deliver a change without its corresponding verification."*

**Mandate:** Logic, schemas, or policies and their verification criteria form one atomic unit. Pair software repos with `templates/technical-base/` and corporate/functional repos with `templates/business-base/`.

#### 5. Specification Hierarchy & Discrepancy Scans
> *"Review canonical specifications first and proactively detect discrepancies."*

**Mandate:** Approach `docs/`, `corporate/`, and architectural specs as supreme law. Parse specs first when planning changes; flag and unify workspace-to-spec drift immediately as a P0 discrepancy.
- **Generation Rule:** Derive templates, scaffolds, or contracts strictly from `docs/` or `corporate/` specs — never from memory: (1) Locate spec $\rightarrow$ (2) Extract invariants $\rightarrow$ (3) Instantiate $\rightarrow$ (4) Cross-verify diff.

#### 6. Continuous Consolidation
> *"Consolidate and complete documentation continuously over time."*

**Mandate:** Treat documentation and governance ledgers as living code. Update `WORKTASK.md`, `BACKLOG.md`, `CHANGELOG.md`, and affected architecture guides immediately upon completing a phase.

#### 7. The Zero-Backward Law (Clean Cutovers)
> *"Never leave backward-compatibility shims or legacy fallbacks during refactors — always execute a clean cutover."*

**Mandate:** Execute surgical replacements when upgrading code, schemas, policies, or manifests (`schema_version`, JSON/YAML/TOML contracts). Never leave legacy polyfills, dummy aliases (`OldType = NewType`), re-export shims, `if legacy:` branches, or `@deprecated` markers.

#### 8. Mandatory Pre-Commit Hygiene & Zero-Literal Exclusion (Anti-Streisand Gate)
> *"Never finish a task leaving behind script residue, broken side effects, or self-defeating exclusion literals."*

**Mandate:** Execute BEFORE delivering `git commit` blocks: (1) **Pesticide Scan** (delete scratch files); (2) **Side-Effect Coherence** (`make verify`, `audit.sh`, `layer-config.sh`); (3) **Sterile Root** (`git status --short`); (4) **Multi-Repo Parity** (sync `CHANGELOG.md`, `README.md`, and verify suites in every modified repo); (5) **Zero-Literal Exclusion (Anti-Streisand Invariant)** — when ensuring a private name, codename, or identifier never appears in a repo, **NEVER** embed that forbidden literal (not even hex/base64-encoded) inside the repo's rules, tests, or scripts; use dynamic external discovery (`~/Projects/*`) or structural regexes.

#### 9. Exhaustive Implementation Planning (Anti-Myopia)
> *"Move deliberately rather than rushing: short verified steps backed by comprehensive cross-cutting plans."*

**Mandate:** (1) **Additive Plans** mapping transversal side-effects; (2) **No Phase Compression**; (3) **Execution Block** until user approval; (4) **Zero Scope Creep** (log adjacent observations in `BACKLOG.md`).

#### 10. Documentation Coherence After Structural Changes
> *"When you move, rename, or delete a file, documentation must reflect current reality."*

**Mandate:** After moving, renaming, creating, or deleting any file/directory: (1) Sync `README.md` trees against `find`/`ls`; (2) Verify doc links (`test -f`); (3) Sweep `.md` files (`grep -rn`) for old paths; (4) Leave zero orphaned references.

#### 11. `dotfiles-ubuntu` Native Self-Guidance & Scaffolding-First Mandate
> *"Use the platform's deterministic CLI orchestrators (`layer-config.sh`, `layer-subtree.sh`) instead of ad-hoc manual steps."*

**Mandate:** Operate the `dotfiles-ubuntu` multi-layer architecture natively:
1. **CLI Over Manual**: Use `./scripts/layer-config.sh` (`bootstrap-workspace`, `sync-layer`, `init-fork`, `scaffold-template`, `apply-project`, `diff-project`, `promote-from-project`, `set-global-profile`, `register-subtree`, `spawn-ephemeral`) and `./scripts/layer-subtree.sh` (`add`, `pull`, `push`, `pull-all`, `sync-upstream`) first.
2. **3-Tier Profile Composition (`human-core`, `technical-base`, `business-base`)**:
   - **`human-core`**: Default machine-global baseline (`~/.gemini/config/AGENTS.md`).
   - **`technical-base`** (`templates/technical-base/`): Software engineering, `1:1:1` traceability, refactoring, and 100% AAA testing.
   - **`business-base`** (`templates/business-base/`): Corporate ledger integrity, *Lex Superior* IP/compliance, cross-surface cascade, and functional verification.
   - Switch global profile via `./scripts/layer-config.sh set-global-profile <human-core|technical|business|full> --stow`.
3. **`antigravity-ide` vs. `antigravity-agents`**: `antigravity-ide` provides a 360° visual/terminal view without leaking agent context; `antigravity-agents` scopes rules per Workspace Root (`<workspace>/.agents/rules/layer-<NN>-<name>.md` by `precedence` `0..100`) and enforces `Non-Workspace File Access` (`allow` on Corporate Root vs. `deny`/`ask` on Department/Team workspaces).
4. **Workstation Hook Gates (`pre_tool_guard.py`)**: Blocks automated mutating Git commands (`git add`, `git commit`, `git push`, `git reset`, `git rebase`, `git checkout`, `git merge`, `git subtree`), `alembic` migrations, edits to `alembic/versions/*.py`, and non-empty writes (`> 0 bytes`) to Python consumer `src/**/__init__.py` or `tests/**/__init__.py`.

#### 12. Model Delegation Discipline (`flash` vs `inherit` vs `pro` & 4-Channel Digest)
> *"Never spend a heavy model on a mechanical task."*

**Mandate:** Select tiers deliberately: `flash` for mechanical sweeps (`// delegate: flash`), `inherit` for architectural/normative judgment, and `pro` for deep reasoning or `pro`-environment `L3` unfolding. Require a **4-channel digest**: (1) **Domain State**, (2) **Affected Surface**, (3) **Invariants & Constraints**, (4) **Actionable Delta**.

#### 13. Language Purity & Pre-Edit Scope Gate
> *"Zero language mixing in repository artifacts and zero unannounced collateral edits."*

**Mandate:** (1) **Single-Language Purity**: Communicate with the user in their language (Spanish), keeping all English-first repository artifacts in 100% pure technical English. (2) **Pre-Edit Scope Blueprint**: Present a concise table of target files and symbols before multi-file edits. (3) **Collateral Freeze**: Never modify untouched files with pre-existing issues in the same turn; log in `BACKLOG.md`.

---

## Governance (Universal)

- **Description**: Commit discipline, priority chain, holistic analysis scope, and global config persistence
- **Applies**: Always

### Commit Discipline
1. **NEVER run mutating git commands** (`git add`, `git commit`, `git push`, `git commit --amend`, `git reset`) automatically.
2. **ONE single commit per repo** using Conventional Commits (`feat:`, `fix:`, `chore:`, `refactor:`, `test:`, `docs:`).
3. **Independent repos**: Deliver a separate commit block per modified repo (`cd <REPO_PATH> && git add ... && git commit -m "..."`).
4. **Task tracking sync is MANDATORY** before delivering any commit block (`skills/continue/SKILL.md`).
5. **Force-tracked `.gitignore` files**: Use `git add -u` (plus `git add -f <new_file>`) so tracked governance files (`WORKTASK.md`, `BACKLOG.md`, `CHANGELOG.md`, `ROADMAP.md`) are never left unstaged.
6. **Working Commits vs. Releases (`[Unreleased]` Standard)**: During active iteration, **NEVER** bump `VERSION`/`pyproject.toml`/`README.md` badges, **NEVER** append `(vX.Y.Z)` to commit messages, and **NEVER** chain `git push` by default. Log changes under `## [Unreleased]` in `CHANGELOG.md` and only cut/push a release via `/release` (`skills/release/SKILL.md`).

### Priority Chain & Global Config Persistence
- **Priority Chain**: (1) `WORKTASK.md` $\rightarrow$ (2) `ROADMAP.md` / `BACKLOG.md` $\rightarrow$ (3) `roadmaps/`. Never suggest ad-hoc work from memory.
- **Global Config Persistence (`dotfiles-ubuntu`)**: Edit `~/dotfiles-ubuntu/antigravity/.gemini/config/` or `~/dotfiles-ubuntu/templates/<profile>/` first, then run `cd ~/dotfiles-ubuntu && stow -t ~ -R antigravity` (never symlink machine-local runtime files).
