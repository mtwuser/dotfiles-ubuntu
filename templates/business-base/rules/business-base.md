---
trigger: always_on
description: Universal corporate ledger integrity, Lex Superior IP firewall, cross-surface cascade, and functional verification rules
---
# Enterprise, Normative & Functional Governance Baseline (`business-base`)

> Universal corporate, regulatory, financial, industrial, and communicative rules for enterprise holdings, departments, and functional workspaces. Translates software engineering rigor (`1:1:1` traceability, `100%` coverage, and `AAA` verification) to business operations and multi-surface governance.

---

## Corporate Ledger & Normative Integrity

- **Description**: Single Source of Truth ledgers, deontic authority (*Lex Superior*), and confidentiality gates
- **Applies**: All corporate (`corporate/**`), departmental (`layers/dept-*/**`), documentation (`docs/**`), and surface (`surfaces/**`) files

1. **Single Source of Truth Ledger Integrity (`corporate/`)**:
   - Official records under `corporate/` (IP/patent registries, contracts, Master BOM/CAPEX ledgers, batch logs) carry production-schema strictness.
   - **Zero Approximations & Atomic Sync**: Never invent, round, or estimate financial figures, royalty/dilution percentages, physical tolerances, or legal clauses. Claims in `docs/` or `surfaces/` MUST cite their `corporate/` ledger and update atomically.
2. **Deontic Precedence (*Lex Superior*) & Confidentiality Firewall**:
   - Enforce numeric `precedence` (`0..100`) in `system/mcp-layer.json`: Legal/IP (`5`) $\rightarrow$ Corporate Root (`10`) $\rightarrow$ Bio-Safety/QA (`15`) $\rightarrow$ FinOps/Supply (`20`) $\rightarrow$ Tech/Engineering (`25`) $\rightarrow$ Brand/Design (`30`) $\rightarrow$ Marketing/Growth (`35`).
   - Verify zero unpatented inventions (*World Novelty Gates*) or trade secrets leak into `surfaces/{web,forms,print}/`. Reference restricted items by ID (`<PAT-ID>`, `<TS-ID>`, `Family 1..4`, `Lote #NNN`), never embedding secret formulas in rules; use descending `INCI`/`ISO` labels and `20/80` Iceberg gates.
3. **Cross-Surface Cascade Coherence ("Calado Transversal")**:
   - Audit every policy, formulation, pricing, or brand change across all three surface planes: (a) **Web (`surfaces/web/**`)**, (b) **Forms (`surfaces/forms/**`)**, and (c) **Print (`surfaces/print/**`)**.

---

## Functional Verification & Documentary Decommissioning

- **Description**: Business equivalent of `100%` test coverage, `AAA` structure, and zero-residue refactoring
- **Applies**: All policies, contracts, SOPs, financial ledgers, and surface specifications

1. **Three-Part Functional Verification Structure (Business `AAA` Pattern — MANDATORY)**:
   Every policy, departmental rule, contract spec, lab protocol, or surface blueprint MUST contain three sections:
   - **`# Scope & Surface Target`** (*Arrange*): Exact directories, divisions, roles, and file globs governed.
   - **`# Normative Invariants`** (*Act*): Numbered rules (`<DEPT>-01`, `<DEPT>-02`, ...) with exact thresholds, allowed/forbidden states, and required units.
   - **`# Verification & Sign-Off Gates`** (*Assert*): Deterministic pass/fail criteria, required co-signatures, and MCP/CLI audit checks before publication.
2. **Quantitative, Financial & Physical Unit Precision**:
   - Specify exact currency (`€` / `USD`), cost basis (`Lean` vs `Full COTS`, `VAT/IVA` status), physical unit (`°C`, `%` moisture, `Mesh` / `µm`, `m²`, `mm`, `RPM`, `W`), material grade (`AISI 316` vs `AISI 304`), and batch ID (`Lote #NNN`).
3. **Nomenclature, Brand, Packaging QA, Anti-Greenwashing & Zero-Residue Policy Decommissioning**:
   - Enforce canonical corporate casing, phonetic standards, immutable Design (`30`) $\rightarrow$ Marketing (`35`) token locks, WCAG contrast (`>= 4.5:1` body, `>= 7:1` safety labels), print pre-flight (`>= 3 mm` bleed, `>= 300 DPI`), and regional matrices.
   - **Zero-Greenwashing & Pre-Publication Audit Gate**: Ground environmental, circular-economy, or B2B unit-economics claims in `corporate/` ledgers (`Lote #NNN`), prepend a pre-clearance header (`canonical_snippet.md`), and pass a `strictly-read-only` ephemeral audit before promoting to `pre`/`pro`. Remove superseded clauses and log transitions in `CHANGELOG.md`.
