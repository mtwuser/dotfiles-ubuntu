---
trigger: always_on
description: Universal corporate ledger integrity, Lex Superior IP firewall, cross-surface cascade, and functional verification rules
---
# Enterprise, Normative & Functional Governance Baseline (`business-base`)

> Universal corporate, regulatory, financial, and communicative rules for enterprise holdings, departments, and functional workspaces (`1:1:1` traceability, `100%` coverage, `AAA` verification).

---

## Corporate Ledger & Normative Integrity

- **Description**: Single Source of Truth ledgers, deontic authority (*Lex Superior*), and confidentiality gates
- **Applies**: All corporate (`corporate/**`), departmental (`layers/dept-*/**`), documentation (`docs/**`), and surface (`surfaces/**`) files

1. **Single Source of Truth Ledger Integrity (`corporate/`)**:
   - Official records under `corporate/` (IP/patent registries, contracts, BOM/CAPEX ledgers, batch logs) carry production-schema strictness.
   - **Zero Approximations & Atomic Sync**: Never invent, round, or estimate figures, tolerances, or clauses. Claims in `docs/` or `surfaces/` MUST cite `corporate/` ledgers (`[DEPT]-[TYPE]-[YYYY]-[NNN]`).
2. **Deontic Precedence (*Lex Superior*), Entity Lineage & Confidentiality Firewall**:
   - Enforce `precedence` (`0..100`) and `entity_kind` (`public-government` `1..4`, `enterprise` `5..84`, `individual` `85..95`) with `governing_root_id` in `system/mcp-layer.json`: Territorial (`1`) $\rightarrow$ State `Root 0` (`2`) $\rightarrow$ Public Dept (`3..4`) $\rightarrow$ Legal/IP (`5`) $\rightarrow$ Corporate (`10`) $\rightarrow$ Finance (`15`) $\rightarrow$ Ops (`20`) $\rightarrow$ Tech (`25`) $\rightarrow$ Brand (`30`) $\rightarrow$ Squad (`50`) $\rightarrow$ `Human-Stack` (`85..95`).
   - Verify zero trade secrets leak into `surfaces/{web,forms,print}/`; cite IDs (`<PAT-ID>`, `<TS-ID>`, `Batch #NNN`) and enforce `ISO` / `20/80` disclosure gates.
3. **Cross-Surface Cascade, $N$-Layer Consensus & Escalation SLAs**:
   - Audit changes across `surfaces/{web,forms,print}/**`, enforcing SLAs (`P0 < 1h`, `P1 < 4h`, `P2 < 24h`) and 4-state consensus (`RECONCILED_FLOW`, `ITERATION_REQUIRED`, `ESCALATE_TO_ROOT`, `ESCALATE_INTER_ENTITY_ROOTS`).

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
3. **Nomenclature, Brand, Packaging QA & Anti-Greenwashing Gate**:
   - Enforce corporate casing, phonetic standards, Design (`30`) $\rightarrow$ Marketing (`35`) token locks, WCAG contrast (`>= 4.5:1` body, `>= 7:1` safety), and print pre-flight (`>= 3 mm` bleed, `>= 300 DPI`).
   - **Zero-Greenwashing Gate**: Ground claims in `corporate/` ledgers (`Batch #NNN`), include sign-off headers, pass `strictly-read-only` audits before `pre`/`pro`, and log in `CHANGELOG.md`.
