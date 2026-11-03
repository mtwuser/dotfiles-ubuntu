---
trigger: always_on
description: Universal corporate ledger integrity, Lex Superior IP firewall, cross-surface cascade, and functional verification rules
---
# Enterprise, Normative & Functional Governance Baseline (`business-base`)

> Universal corporate, regulatory, financial, and communicative rules for enterprise holdings, departments, and functional workspaces. Translates software engineering rigor (`1:1:1` traceability, `100%` coverage, `AAA` verification) to business operations and multi-surface governance.

---

## Corporate Ledger & Normative Integrity

- **Description**: Single Source of Truth ledgers, deontic authority (*Lex Superior*), and confidentiality gates
- **Applies**: All corporate (`corporate/**`), departmental (`layers/dept-*/**`), documentation (`docs/**`), and surface (`surfaces/**`) files

1. **Single Source of Truth Ledger Integrity (`corporate/`)**:
   - Official records under `corporate/` (IP/patent registries, contracts, BOM/CAPEX ledgers, batch logs) carry production-schema strictness.
   - **Zero Approximations & Atomic Sync**: Never invent, round, or estimate financial figures, royalty/dilution percentages, tolerances, or legal clauses. Claims in `docs/` or `surfaces/` MUST cite their `corporate/` ledger (`[DEPT]-[TYPE]-[YYYY]-[NNN]`) and update atomically.
2. **Deontic Precedence (*Lex Superior*) & Confidentiality Firewall**:
   - Enforce `precedence` (`0..100`) in `system/mcp-layer.json`: Territorial/Geo (`1`) $\rightarrow$ Public State `Root 0` (`2`) $\rightarrow$ Public Admin Dept (`3..4`) $\rightarrow$ Legal/IP (`5`) $\rightarrow$ Corporate (`10`) $\rightarrow$ Finance (`15`) $\rightarrow$ Ops/HSE (`20`) $\rightarrow$ Tech (`25`) $\rightarrow$ Brand (`30`) $\rightarrow$ Squad (`50`) $\rightarrow$ Contextual `Human-Stack` (`85..95`).
   - Verify zero unpatented inventions (*World Novelty Gates*) or trade secrets leak into `surfaces/{web,forms,print}/`. Reference restricted items by ID (`<PAT-ID>`, `<TS-ID>`, `Batch #NNN`), never embedding secret formulas in rules; use `ISO` and `20/80` disclosure gates.
3. **Cross-Surface Cascade & Escalation SLAs**:
   - Audit policy, spec, pricing, or brand changes across `surfaces/web/**`, `surfaces/forms/**`, and `surfaces/print/**`, enforcing SLAs (`P0 < 1h`, `P1 < 4h`, `P2 < 24h`).

---

## Functional Verification & Documentary Decommissioning

- **Description**: Business equivalent of `100%` test coverage, `AAA` structure, and zero-residue refactoring
- **Applies**: All policies, contracts, SOPs, financial ledgers, and surface specifications

1. **Three-Part Functional Verification Structure (Business `AAA` Pattern — MANDATORY)**:
   Every policy, departmental rule, contract spec, SOP, or surface blueprint MUST contain:
   - **`# Scope & Surface Target`** (*Arrange*): Exact directories, divisions, roles, and file globs governed.
   - **`# Normative Invariants`** (*Act*): Numbered rules (`<DEPT>-01`, `<DEPT>-02`, ...) with exact thresholds, states, and units.
   - **`# Verification & Sign-Off Gates`** (*Assert*): Deterministic pass/fail criteria, co-signatures, and MCP/CLI audit checks.
2. **Quantitative, Financial & Unit Precision**:
   - Specify exact currency (`EUR` / `USD`), cost basis (`Lean` vs `Full COTS`, tax/VAT), SI/ISO unit, grade, and batch ID (`Batch #NNN`).
3. **Nomenclature, Brand, Packaging QA, Anti-Greenwashing & Policy Decommissioning**:
   - Enforce corporate casing, phonetic standards, Design (`30`) $\rightarrow$ Marketing (`35`) token locks, WCAG contrast (`>= 4.5:1` body, `>= 7:1` safety), print pre-flight (`>= 3 mm` bleed, `>= 300 DPI`), and regional matrices.
   - **Zero-Greenwashing & Pre-Publication Audit Gate**: Ground environmental, compliance, or unit-economics claims in `corporate/` ledgers (`Batch #NNN`), include a sign-off header, and pass a `strictly-read-only` audit before `pre`/`pro`. Remove superseded clauses and log in `CHANGELOG.md`.
