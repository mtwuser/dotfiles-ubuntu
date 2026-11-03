---
name: review
description: "Tactical C1 read-only audit of the active session delta (default) or a targeted path/dimension (/review [path | docs | arch | 1:1:1 | layer]) across the 4 canonical quality dimensions."
---

# Tactical & Target-Scoped Review — `/review`

> **Purpose (`C1 — Tactical Incremental Radius, ~5–15s`)**: Quickly audit the **files modified in the current task/branch** (default when invoked as `/review` with no arguments) or a **specific target path / single dimension** (`/review <path | docs | arch | 1:1:1 | layer>`) before `/continue` or commit.
> Shares the exact same **4 Canonical Dimensions** as `/full-audit`, differing only in its **Radius of Action**: `/review` inspects a targeted delta or single dimension in seconds, whereas `/full-audit` certifies 100% of the repository in closed-world mode before `/release`.

---

## 1. Radius of Action & Invocation Modes

Check `operating_state` and `workspace_mode` (`"technical"`, `"business"`, or `"hybrid"`) from `make status`:

| Invocation | Target Radius Inspected | When to Use |
| :--- | :--- | :--- |
| **`/review`** *(no args — default)* | **Active Session / Git Delta (`git status --short` / modified files)** | Default mid-session check before `/continue`: evaluates Dimensions 1–4 **only on files touched in the current task**. |
| **`/review <path>`** | **Specific Module, Directory, or Template Pack** | After editing a specific module (`scripts/dotfiles_mcp/capsules/capsule_engine.py`), directory (`corporate/`), or template pack (`templates/tech-stack/fastapi-hexagonal/`). |
| **`/review docs`** | **Dimension 1 Only (`3-Tier Docs & 5-Link Ripple`)** | After updating CLI flags, `Makefile` targets, architecture specs, or user guides. |
| **`/review arch`** | **Dimension 2 Only (`Technical Code` or `Business Ledgers`)** | After refactoring code (`technical`) or updating policies, ledgers, and `surfaces/` (`business`). |
| **`/review 1:1:1`** | **Dimension 3 Only (`Spec <-> Source <-> Test` or `Policy <-> Ledger <-> Gate`)** | After adding/modifying functions, unit tests (`Test<Module>`), or normative policy checklists. |
| **`/review layer`** | **Dimension 4 Only (`Layer Manifest, Bindings & 1-Hop Horizon`)** | When validating or aligning a `Root 0`, `domain-policy`, `department`, `squad`, or project workspace. |

---

## 2. Deterministic Fast Probes (Run First on Target Radius)

// delegate: flash

```bash
# 1. Workspace & layer drift digest (< 0.2s):
make status && make diff

# 2. Isolated unit branch coverage on touched module(s) (technical/hybrid mode):
venv/bin/pytest <test_file> --cov=<module_import_path> --cov-branch --cov-report=term-missing -q

# 3. Zero-residue & anti-duplication scan on touched files:
grep -rn "DEPRECATED\|@deprecated\|BACKWARD COMPAT\|# shim\|# transitional" <target_paths>
grep -rn "class.*Expanded\|class.*100Coverage\|class.*Extended\|class.*Additional\|class.*Coverage" <target_test_paths>

# 4. Unpushed commit triangulation & cross-layer version/escape sweep (when HEAD is ahead of origin/<branch>):
git diff origin/$(git branch --show-current) --stat
grep -rn "\\\\u[0-9a-fA-F]\\{4\\}" system/ templates/ layers/ 2>/dev/null || true
```

---

## 3. The 4 Canonical Audit Dimensions (Applied to Target Radius)

// delegate: flash

Evaluate only the dimensions relevant to the selected target radius and `workspace_mode`:

### Dimension 1 — `docs`: 3-Tier Documentation, Conceptual Isomorphism & 5-Link Change-Ripple
- [ ] **3-Tier Progressive Disclosure & `< 465`-Line Gate**: Touched `README.md` ($\le 400$ target), `docs/guides/*.md`, `docs/architecture/*.md`, and `docs/reference/*.md` stay strictly `< 465` lines and match actual disk trees (`find` / `ls`).
- [ ] **Conceptual & Semantic Prose Isomorphism**: Read touched documentation tables and prose word-for-word against `constants.py` and `templates/**/template.json` to ensure zero retired taxonomy terms (`core-base`, `business-stack`, `science-stack`, `tech-stack` only), complete skill/template inventories, domain-neutral Level 3 (**Squad, Case, or Operational Unit**) framing, and single-surface `antigravity-agents` guidance.
- [ ] **5-Link Change-Ripple & Flag-Signature Parity**: Any modified capability is synchronized across all 5 links (`1. Engine/Service Function <-> 2. CLI/Router Parser <-> 3. Makefile Recipe / Hook <-> 4. Spec Table (docs/architecture/) <-> 5. Root/Guide Docs & Parity Tests`), verifying that Link 3 (`Makefile` recipes) forwards all optional CLI flags exposed by Link 2.
- [ ] **Links, Mermaid & Language Purity**: 100% of relative Markdown links resolve on disk, Mermaid node labels containing `()` or `[]` are double-quoted, and repository artifacts remain in 100% pure technical English.

### Dimension 2 — `arch`: Pragmatic Code Architecture (`technical`) OR SSoT Ledgers (`business`)
- **In `technical` / `hybrid` mode**:
  - [ ] **Single-Owner Boundaries, Import Direction & Specific Exceptions**: Entrypoints/routers/CLI stay thin and delegate to domain engines/services; upstream never imports from downstream (except runtime-safe `TYPE_CHECKING` blocks); raise specific domain exceptions/error codes (never generic `Exception`); keep consumer `src/**/__init__.py` and `tests/**/__init__.py` at `0 bytes`.
  - [ ] **5-Stage Structural Evolution, Relational Cluster Mass ($M_{\text{cluster}}$) & Anti-Compression (`< 465` Lines)**: Flag defensive syntactic compression (cryptic short names, chained `.update()` packing), repeated inline blocks ($\ge 2 \rightarrow$ Function), data clumps ($\ge 3$ functions sharing $\ge 4$ params $\rightarrow$ Class/`@dataclass`), multi-branch `if/elif` chains ($\ge 3\text{–}4 \rightarrow$ Catalog/`Protocol`), modules $> 400$ lines, or **Relational Cluster Saturation** ($\ge 2$ coupled sibling modules $\ge 385$ lines with combined $M_{\text{cluster}} \ge 1{,}200$ lines, or peer `*_engine.py` modules importing `_private` helpers from one another $\rightarrow$ extract/consolidate into a `1:1:1` module or `*_helpers.py`).
  - [ ] **Data Symmetry, Bidirectional Constants & Zero-Residue Forensics**: Purpose-named constants (`*_CONTRACT_REV`, `DEFAULT_*`, `MAX_*` with nominal wire strings like `"mcp-layer-v1"`, never SemVer schema strings like `"1.2"` or raw slices `[:24]`), `{...}` literals, `.get()` at external boundaries vs. `d["k"]` internally, 100% public docstrings & return types, zero shims/aliases, and explicit **`[WIRE]` / `[CONSOLIDATE]` / `[PRUNE]`** forensics (`git log -S` + `docs/architecture/`) before removing any unreferenced symbol.
  - [ ] **Bifurcated Age Radar (`14d / 90d / 180d`)**: Check `stale_proposals` (`> 14d`), modules/specs (`> 90d`), and policies/templates (`> 180d`): classify aligned artifacts (`0` drift) for consolidation/automation/`/enrich` and drifted artifacts (`Source > Spec`) for refactoring.
- **In `business` / `hybrid` mode (`business-base` / `business-stack/*` / `science-stack/*`)**:
  - [ ] **Lex Superior (`0..100`) & Deontic Precedence (`1..95`)**: Lower-tier packs never weaken higher-authority invariants (`Territorial/Geo 1 > Public State Root 0 2 > Public Admin Dept 3..4 > Legal/IP 5..15 > Finance/Ops 15..20 > Tech 25 > Brand 30 > Marketing 35 > Squad 50..80 > Contextual Human-Stack 85..95`).
  - [ ] **Single Source of Truth (SSoT) Ledgers & IP Firewall**: Financial, pricing, and SLA figures live in one canonical table under `corporate/` or `docs/` with ISO 4217 / SI units; zero restricted formulas or internal codenames leak to external surfaces; crisis playbooks define `P0/P1/P2` SLAs.
  - [ ] **Cross-Surface Cascade (`< 465` Lines)**: Changes in `corporate/` cascade across `surfaces/{web,forms,print}/` with `0` drift.

### Dimension 3 — `1:1:1`: Executable Test Symbiosis (`technical`) OR Normative Sign-Off (`business`)
- **In `technical` / `hybrid` mode**:
  - [ ] **Bidirectional `1:1:1` Mapping, 3-Tier Flow (`Unit -> Imp -> E2E`) & Scope**: Every executable module declares `Specification: docs/architecture/<spec>.md` and maps `1:1` to `tests/unit/**/test_<module>.*` (`1` canonical `class Test<Module>`, `0` loose top-level `test_*` functions, `0` banned `*Expanded`/`*Coverage` class suffixes, `0` duplicate method names, and `0` artificial unit test files for purely declarative DTOs/models/catalogs). Verify no real DB/subprocess/network I/O in `tests/unit/` (move to `tests/imp/`) and no mocked boundaries in `tests/imp/`.
  - [ ] **Constructor Injection, Patch-at-Consumption, Single-File `1:1:1` Isolation & Anti-Deception Gates**: Inject spec-constrained mocks in constructors; patch at the consumer lookup seam (`@patch('consumer.Dep')`, never `@patch('external.Dep')`); enforce 1-line invariant docstrings on every `test_<subject>_<scenario>_<expected>`, separated `# Arrange` / `# Act` / `# Assert` comments, `match=` on `pytest.raises`, zero blind `subprocess.run` lambdas, and `100%` single-file isolated unit branch coverage (`0` *Cross-Unit Coverage Masking*) across all 4 quadrants (*Nominal*, *`N` vs `N ± 1` Numeric, Input-Cardinality (`1-token` vs `multi-token`) & Lifecycle (`greenfield t=0` vs `brownfield N-1 -> N`) Boundaries*, *Negative-First Bipolar Guards*, *Outbound Failures*).
- **In `business` / `hybrid` mode**:
  - [ ] **Traceable IDs & Three-Part Verification**: Every normative artifact carries `[DEPT]-[TYPE]-[YYYY]-[NNN]` and contains `# Scope & Surface Target`, `# Normative Invariants`, and `# Verification & Sign-Off Gates` (`- [ ]`).

### Dimension 4 — `layer`: Multi-Layer Topology, Manifest & 1-Hop Horizon
- [ ] **Manifest & Surface Binding Contracts (`mcp-layer-v1` & `template-pack-v1`)**: `system/mcp-layer.json` and `templates/**/template.json` declare valid contracts and existing `rule_files` / `canonical_templates`.
- [ ] **Horizon, Upgrade Reconciliation & Projection Sync (`make status`, `make horizon`, `make diff`)**: Verify `makefile_outdated: false`, `manifest_contracts_outdated: false`, `downward_sync_needed: false`, `modified_in_project: []`, and `.agents/LAYER_LINEAGE.md` parity.
- [ ] **Authority & Roster Gates (`make authority`)**: Verify `layer_authority` (`authorized_emails`, `maintainer_emails`, `validator_emails`) and `git_governance` (`protected_branches`, `.github/CODEOWNERS`).

---

## 4. Output Format & Read-Only Rules

1. **Re-Read Active Rules First & Stay Read-Only**: Read `.agents/rules/*.md` before auditing; report findings without mutating files (capture non-trivial deferred items in `BACKLOG.md`).
2. **Structured Prioritized Table**: Report `Dimension (docs|arch|1:1:1|layer) | Severity (❌ Critical / ⚠️ Warning / 💡 Suggestion) | File:Line Evidence | Clean-Cutover Recommendation`.
