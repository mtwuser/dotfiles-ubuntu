---
name: review
description: audit code structure, quality, and testing alignment against project rules
---

# Review — `/review`

> **The quality guard.** Systematically audit a scope (module, component, test suite) against the project's rules, architecture, and testing standards.

---

## Scopes & Mode Selection (`operating_state` & `workspace_mode`)

Check `operating_state` and `workspace_mode` from `make status` (or `.agents/rules/*.md`):
- **`technical` / `hybrid` mode (`technical-base` / `tech-stack/*`)**: Execute §1–§5 below (plus §6 when `hybrid`). Scope §1.2 (`Models & Serializers`) and `views/controllers` checks strictly to web/ORM application stacks (`tech-stack/*`); in CLI/MCP/library repositories (such as `operating_state == "oss-dev"`), audit `engine / tools / protocol / cli` boundaries instead.
- **`business` mode (`business-base` / `business-stack/*` / `corporate-root` / `domain-policy` / `department`)**: Skip code/unit-test checks (§1–§4) and execute **§6 Business & Normative Governance Audit (`corporate/`, `templates/`, `docs/`, `surfaces/`)** plus **§5 Zero-Residue Scan**.

| Scope | What it audits |
|-------|---------------|
| `/review <module>` | Full module audit (Technical §1–§5) or Corporate/Department pack audit (Business §6) |
| `/review <module>/tests` | Test-only audit: classification, file mapping, coverage, patterns (Technical §2) |
| `/review <module>/services` | Service layer audit: boundaries, dead code, naming, dependencies (Technical §3) |
| `/review 1:1:1` | Bidirectional `Spec <-> Source <-> Test` (`Test<Module>`, 1-line invariant docstrings, AAA, isolated unit coverage) or `Policy <-> Ledger <-> Sign-Off Gate` symbiosis (§2.2, §2.4 & §6) |
| `/review docs` | 3-Tier documentation coherence (`README -> guides -> architecture/reference`), relative links, Mermaid diagrams & 5-Link Change-Ripple parity (§7) |
| `/review layer` | Multi-layer topology, `system/mcp-layer.json` (`mcp-layer-v1`), `templates/**/template.json`, `surface_bindings`, `layer_authority`, `make diff` & `make horizon` (§8) |
| `/review corporate` | Business & normative ledger audit: *Lex Superior*, SSoT ledgers, Traceable IDs, 3-part verification, IP firewall (Business §6) |
| `/review imports` | Cross-module import direction audit (Technical §4) |
| `/review residue` | Zero-residue scan: shims, deprecated markers, backward compat aliases, and `[WIRE]/[CONSOLIDATE]/[PRUNE]` forensics (§5) |

---

## 1. Full Module Audit (`/review <module>`)

Execute these checks **in order**:

### 1.1 Architecture

- [ ] **Service layer compliance** — views/controllers call services, never raw data access
- [ ] **Import direction** — no downstream module importing from upstream (check project's dependency hierarchy)
- [ ] **Dead code** — unused imports, unreachable functions, commented-out blocks
- [ ] **Naming conventions** — models as nouns, services as verbs, consistent suffixes
- [ ] **Structural Evolution & Anti-Over-Compression (`Inline -> Function -> Class -> Protocol/Polymorphism -> Module`)** — flag defensive syntactic compression (opaque short variable names like `d_rec` / `out_h`, chained `.update()` packing near `< 465` lines), $\ge 3$ functions sharing $\ge 4$ context parameters (*Data Clump* $\rightarrow$ Class/`@dataclass`), or $\ge 3$–$4$ `if/elif` role/surface branches ($\rightarrow$ declarative catalog or `Protocol` polymorphism)
- [ ] **Structural Data Symmetry, Bidirectional Constant Wiring & 5-Link Ripple Parity** — verify purpose-named constants (`*_CONTRACT_REV`, `*_PROTOCOL_REV`, `*_SENTINEL`, `DEFAULT_*`, `MAX_*`, `MIN_*`) with nominal wire identifiers (`"mcp-layer-v1"`, `"template-pack-v1"`, `"unversioned"` — reserving `X.Y.Z` strictly for repository releases in `VERSION`; zero SemVer-like schema strings like `"1.2"` or `"0.0.0"`, raw slices like `[:24]`, or hardcoded precedences), declarative `{...}` dictionary literals (zero chained `.update()` construction), strict indexing symmetry (`.get(k, default)` at external/untrusted JSON/CLI boundaries vs. direct `d["k"]` indexing on guaranteed internal engine contracts), **bidirectional constant wiring** (every policy/constant in `constants.py` is actively referenced by its consumer module), and **5-link ripple parity** (`Engine Function <-> CLI Parser <-> Makefile Recipe/Hook <-> Arch Spec Table <-> Root/Guide Docs`)
- [ ] **Bifurcated Age & Staleness Radar (`14d / 90d / 180d`)** — check `stale_proposals` (`> 14d`) in `make status`, and evaluate modules/specs untouched for `> 90d` (or policies/templates untouched for `> 180d`) along two branches: (a) **Aligned in Active Use (`0` drift)** $\rightarrow$ candidate for **consolidation, automation (`C1` target/hook), or upward `/enrich`**; (b) **Drifted / Misaligned** (differs from newer idioms or `Source` newer than its `1:1:1` `Spec`) $\rightarrow$ candidate for **refactoring, adjustment, or decommissioning**

### 1.2 Models & Serializers

- [ ] **Field naming** — follows framework conventions, consistent with domain
- [ ] **Serializers** — 1:1 with models (or justified), no business logic in serializers
- [ ] **Choices** — use typed enumerations, no raw strings

### 1.3 Tests

Run the test audit (§2 below) as part of the full audit.

### 1.4 Coverage

// delegate: flash

```bash
# Run project-specific coverage command for the target module
<test-runner> <module>/tests/ --cov=<module> --cov-report=term-missing -q
```

- [ ] **100% target** — identify uncovered lines, classify the gap
- [ ] **Coverage quality** — not just line coverage, verify assertions exist

### 1.5 Report

Present findings as a structured table:

| Area | Status | Finding | Recommendation |
|------|--------|---------|---------------|
| Service layer | ✅/⚠️/❌ | ... | ... |

---

## 2. Test Audit (`/review <module>/tests`)

The most common source of regressions. Check against project testing rules:

### 2.1 Classification (`Unit` vs. `Imp` vs. `E2E`)

For each test file, verify classification matches our 3-tier ontology (`imp` = **Implementation tests**, never `int`):

| Check | Rule |
|-------|------|
| **Unit tests (`tests/unit/`)** | No real DB/subprocess/network access, all dependencies mocked, `< 1s`/test, `100%` isolated branch coverage across 4 quadrants |
| **Implementation tests (`tests/imp/`)** | Real internal boundary implementation (DB persistence, CLI/`stdio` subprocesses, FS permissions, `Spec <-> Code <-> Doc` parity) |
| **E2E tests (`tests/e2e/`)** | Complete multi-step human persona journeys from entrypoint to final state |
| **Misclassified** | Unit test with real DB/subprocess I/O → move to `tests/imp/`. Implementation test that mocks the boundary under test → move to `tests/unit/` |

### 2.2 1:1:1 File & Specification Mapping (`< 465` Lines)

// delegate: flash

Every production file with **executable logic** must have a corresponding unit test file and a bidirectional specification pointer (`Specification: docs/architecture/<spec>.md` in its docstring $\leftrightarrow$ `1:1:1` traceability table in `docs/architecture/`), and every source, test, and navigable `docs/**/*.md` file must stay strictly `< 465` lines (do NOT require artificial unit test files for purely declarative models/DTOs/catalogs without custom executable logic):

```
<module>/services/foo.py       →  <module>/tests/unit/services/test_foo.py  ↔  docs/architecture/<spec>.md
<module>/models/bar.py         →  <module>/tests/unit/models/test_bar.py    ↔  docs/architecture/<spec>.md (if bar.py has custom methods)
```

- [ ] List missing unit test files or missing `Specification: docs/architecture/...` docstring pointers
- [ ] List orphan test files (testing deleted code)
- [ ] List any source, test, or `docs/**/*.md` file $\ge 465$ lines

### 2.3 Patch Targets

- [ ] **Patch at consumption** — `@patch('<module>.services.foo.ExternalDep')` not `@patch('external.module.ExternalDep')`
- [ ] **No real external calls** in unit tests — all mocked

### 2.4 Structure, Bidirectional 3-Tier Flow & Human-Agent `1:1:1` Comprehension Symbiosis

- [ ] **Bidirectional 3-Tier Flow (`Top-Down E2E -> Imp -> Unit` vs. `Bottom-Up Unit -> Imp -> E2E`)** — read normative specs and self-documenting test suites **Top-Down (`E2E` persona journeys $\rightarrow$ `Imp` boundary/parity implementation $\rightarrow$ `Unit` 4-quadrant suites)** before inspecting or mutating source code; execute verification **Bottom-Up (`Unit` in strict isolation first $\rightarrow$ `Imp` $\rightarrow$ `E2E`)** so higher tiers never mask missing unit branch coverage
- [ ] **Single `Test<Module>` suite/class per file** — 1 class per test file, 0 loose top-level `test_*` functions, and `Specification: docs/architecture/<spec>.md` in the module docstring
- [ ] **AAA pattern** — `# Arrange` / `# Act` / `# Assert` clearly separated (never merged)
- [ ] **Self-documenting behavioral test names** — `test_<subject>_<scenario>_<expected>` readable in natural language
- [ ] **1-line invariant docstrings & 4-quadrant unit deduction** — every test class and test method states the functional/security invariant it proves (covering nominal, `N` vs `N ± 1` boundaries, bipolar guards, and outbound failure modes)

### 2.5 Structural Integrity (Anti-Duplication)

// delegate: flash

```bash
# Banned class name patterns (adapt glob to your language: *.py, *.ts, *.go):
grep -rn "class.*Expanded\|class.*100Coverage\|class.*Extended\|class.*Additional\|class.*Coverage" \
  <module>/tests/

# Multi-class files (target: 1 class per file):
find <module>/tests/ -name "test_*" \
  -exec sh -c 'count=$(grep -c "^class " "$1" 2>/dev/null); \
  if [ "$count" -gt 1 ]; then echo "$count: $1"; fi' _ {} \; | sort -rn

# Duplicate method names within the same file:
find <module>/tests/ -name "test_*" -exec sh -c \
  'dups=$(grep -oP "def (test_\w+)" "$1" | sort | uniq -d); \
  if [ -n "$dups" ]; then echo "$1: $dups"; fi' _ {} \;
```

- [ ] **No banned class names** — no `Expanded`, `Coverage`, `Extended`, `Additional`
- [ ] **Prefer one class per file** — justified exceptions documented
- [ ] **No duplicate method names** — each test method unique within file
- [ ] **No library testing** — tests exercise our code, not third-party libraries

---

## 3. Service Layer Audit (`/review <module>/services`)

- [ ] **Single owner** — each domain concept has ONE service owning it
- [ ] **Trigger layer is thin** — one-liner service calls, no raw data access in controllers/views/handlers
- [ ] **No circular imports** — services don't import from views
- [ ] **Dead code** — methods never called from anywhere
- [ ] **Error handling** — proper exceptions from `<module>/exceptions.py`, not generic

---

## 4. Import Direction Audit (`/review imports`)

// delegate: flash

Verify the dependency hierarchy is respected. Upstream modules must NEVER import from downstream modules.

```bash
# Scan for violations based on your project's dependency chain:
# Adapt these patterns to your module hierarchy
grep -rn "from <downstream>" <upstream>/ --include="*.py"
```

Allowed exceptions:
- `TYPE_CHECKING` blocks (runtime-safe, no circular import)
- Lazy imports inside functions (documented as intentional)

---

## 5. Zero-Residue Scan (`/review residue`)

// delegate: flash

```bash
# Find forbidden patterns (adapt glob to your language):
grep -rn "DEPRECATED\|@deprecated\|BACKWARD COMPAT\|backward.compat" . | grep -v node_modules/ | grep -v venv/ | grep -v __pycache__
grep -rn "= .*  # noqa.*alias\|# shim\|# transitional" . | grep -v node_modules/ | grep -v venv/
```

- [ ] **No deprecated markers** — code is deleted or moved atomically
- [ ] **No backward-compat aliases** — `OldName = NewName` not allowed
- [ ] **No re-export shims** — moved code is imported from its new location
- [ ] **Forensic Intent Resolution before pruning unreferenced symbols (`[WIRE]` vs. `[CONSOLIDATE]` vs. `[PRUNE]`)** — never recommend deleting an unreferenced constant or helper without checking `git log -S <symbol>` and `docs/architecture/`: distinguish **unwired design intent (`[WIRE]`)** that must be connected to its consumer engine from **duplicate SSoT (`[CONSOLIDATE]`)** and **proven obsolete residue (`[PRUNE]`)**

---

## 6. Business & Normative Governance Audit (`/review corporate` or `workspace_mode == "business"`)

When operating in `Root 0` (`corporate`), `domain-policy`, or `Department` (`business-base` / `business-stack/*`) workspaces, audit normative documents, corporate ledgers, and template packs against `.agents/rules/business-base.md`:

- [ ] **1. Lex Superior (`0..100`) & Cross-Departmental Precedence (`5..35`)** — lower-tier packs (`department` `30`, `squad` `50`) never weaken or contradict higher-authority invariants (`domain-policy` `5`, `corporate` `10`); Legal/Compliance (`5..15`) > Finance/Supply (`20..25`) > Brand/Design (`30`) > Growth/Marketing (`35`).
- [ ] **2. Single Source of Truth (SSoT) Ledgers & Quantitative Precision** — every financial, operational, pricing, or SLA figure resides in ONE canonical ledger table under `corporate/` or `docs/` with explicit ISO 4217 currency and SI/time units; downstream docs link to the ledger instead of duplicating numbers in prose.
- [ ] **3. Traceable Artifact & Ledger IDs (`[DEPT]-[TYPE]-[YYYY]-[NNN]`)** — every normative policy, contract, pricing table, and sign-off gate carries a unique stable identifier.
- [ ] **4. Three-Part Functional Verification Structure** — every normative document in `corporate/**/*.md`, `templates/**/rules/*.md`, and `docs/**/*.md` contains: (1) `# Scope & Surface Target`, (2) `# Normative Invariants`, and (3) `# Verification & Sign-Off Gates` (with `- [ ]` checklists).
- [ ] **5. IP & Confidentiality Firewall & Crisis Escalation SLAs (`P0/P1/P2`)** — zero restricted formulas, supplier margins, or internal codenames leaked into public/external surfaces; crisis response playbooks define explicit `P0`/`P1`/`P2` SLAs and named owner roles.
- [ ] **6. Cross-Surface Cascade & Modularity (`< 465` Lines)** — changes in `corporate/` cascade across `surfaces/web/`, `surfaces/forms/`, and `surfaces/print/`, and every `.md` file stays strictly `< 465` lines (`make diff` reports zero drift).

---

## 7. Documentation & 5-Link Change-Ripple Audit (`/review docs`)

// delegate: flash

Use this fast tactical scope after modifying CLI flags, `Makefile` targets, architecture specs, or user guides:

- [ ] **1. 3-Tier Progressive Disclosure & `< 465`-Line Gate** — `README.md` ($\le 400$ lines target), `docs/guides/*.md`, `docs/architecture/*.md`, and `docs/reference/*.md` stay strictly `< 465` lines and match actual disk trees (`find` / `ls`).
- [ ] **2. 5-Link Change-Ripple Parity** — every touched capability is synchronized across all 5 links: `1. Engine/Service Function <-> 2. CLI/Router Parser <-> 3. Makefile Recipe / Hook <-> 4. Spec Table (docs/architecture/) <-> 5. Root/Guide Docs & Parity Tests`.
- [ ] **3. Relative Links, Mermaid Syntax & Language Purity** — 100% of relative Markdown links (`[label](path.md)`) resolve on disk, Mermaid node labels containing `()` or `[]` are double-quoted, and repository docs remain in 100% pure technical English.

---

## 8. Multi-Layer Topology, Manifest & Horizon Audit (`/review layer`)

// delegate: flash

Use this tactical scope when validating or aligning a `Root 0`, `domain-policy`, `department`, `squad`, or consumer `project` workspace:

- [ ] **1. Manifest & Template Contract Validity (`mcp-layer-v1` & `template-pack-v1`)** — `system/mcp-layer.json` declares valid `schema_version`, `layer_id`, `layer_role`, numeric `precedence` (`0..100`), `default_stack_templates`, and `surface_bindings` whose `rule_files` and `canonical_templates` exist on disk.
- [ ] **2. Horizon, Upstream Section Diff & Projection Sync (`make status`, `make horizon`, `make upstream-diff`, `make diff`)** — check `makefile_outdated`, `manifest_contracts_outdated`, `downward_sync_needed`, `child_sync_needed`, and `.agents/proposals/`; confirm `make diff` reports `0` unintended `modified_in_project` drift and `.agents/LAYER_LINEAGE.md` is current.
- [ ] **3. Layer Authority, Roster & Environment Promotion Readiness (`make authority`)** — verify `layer_authority` (`authorized_emails`, `maintainer_emails`, `validator_emails`) and `git_governance` (`protected_branches`, `.github/CODEOWNERS`) match the organizational tier's ownership policy.

---

## Rules

1. **Read the relevant rule files first** — always re-read project rules before auditing
2. **Report, don't fix** — `/review` is read-only. Capture findings, present recommendations
3. **Capture to BACKLOG.md** — if fixes are non-trivial, add items there
4. **Prioritize findings** — ❌ Critical (breaks rules) > ⚠️ Warning (should fix) > 💡 Suggestion
5. **Link evidence** — include file paths and line numbers for every finding
