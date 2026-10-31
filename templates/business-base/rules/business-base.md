# Enterprise, Normative & Functional Governance Baseline (`business-base`)

> Universal corporate, regulatory, financial, industrial, and communicative rules for enterprise holdings, departments, and functional workspaces. Translates software engineering rigor (`1:1:1` traceability, `100%` coverage, and `AAA` verification) to business operations and multi-surface governance.

---

## Corporate Ledger & Normative Integrity

- **Description**: Single Source of Truth ledgers, deontic authority (*Lex Superior*), and confidentiality gates
- **Applies**: All corporate (`corporate/**`), departmental (`layers/dept-*/**`), documentation (`docs/**`), and surface (`surfaces/**`) files

1. **Single Source of Truth Ledger Integrity (`corporate/`)**:
   - Official records under `corporate/` (IP/patent registries, investment contracts, Master BOM/CAPEX ledgers, batch logs) carry production-schema strictness.
   - **Zero Unverified Approximations & Atomic Sync**: Never invent, round, or estimate financial figures, royalty/dilution percentages, physical tolerances, or legal clauses. Every claim in `docs/` or `surfaces/` MUST cite its canonical ledger in `corporate/` and be updated atomically in the same changeset.
2. **Deontic Precedence (*Lex Superior*) & Confidentiality Firewall**:
   - Enforce numeric `precedence` (`0..100`) in `system/mcp-layer.json`: Statutory/Legal/IP (`5`) $\rightarrow$ Corporate Root (`10`) $\rightarrow$ Bio-Safety/QA (`15`) $\rightarrow$ FinOps/Supply (`20`) $\rightarrow$ Technical/Engineering (`25`) $\rightarrow$ Brand/Design (`30`) $\rightarrow$ Marketing/Growth (`35`).
   - Verify zero unpatented inventions (*World Novelty Gates*) or trade secrets leak into public surfaces (`surfaces/web/`, `surfaces/forms/`, `surfaces/print/`). Reference restricted items by classification ID (`Family 1..4`, `Lote #NNN`), never embedding secret formulas or codenames inside prohibitory rules.
3. **Cross-Surface Cascade Coherence ("Calado Transversal")**:
   - Audit every policy, formulation, pricing, or brand change across all three surface planes: (a) **Digital/Web (`surfaces/web/**`)**, (b) **Contractual/Operational Forms (`surfaces/forms/**`)**, and (c) **Physical/Printable Assets (`surfaces/print/**`)**.

---

## Functional Verification & Documentary Decommissioning

- **Description**: Business equivalent of `100%` test coverage, `AAA` structure, and zero-residue refactoring
- **Applies**: All policies, contracts, SOPs, financial ledgers, and surface specifications

1. **Three-Part Functional Verification Structure (Business `AAA` Pattern — MANDATORY)**:
   Every normative policy, departmental rule, contract spec, lab protocol, or surface blueprint MUST contain three explicit sections:
   - **`# Scope & Surface Target`** (*Arrange*): Exact directories, business divisions, roles, and file globs governed.
   - **`# Normative Invariants`** (*Act*): Explicit numbered rules (`<DEPT>-01`, `<DEPT>-02`, ...) with exact quantitative thresholds, allowed/forbidden states, and required units.
   - **`# Verification & Sign-Off Gates`** (*Assert*): Deterministic pass/fail acceptance criteria, required departmental co-signatures, and MCP/CLI audit checks before publication.
2. **Quantitative, Financial & Physical Unit Precision**:
   - Specify exact currency (`€` / `USD`), cost basis (`Lean` vs `Full COTS`, `VAT/IVA` status), physical unit (`°C`, `%` moisture, `Mesh` / `µm`, `m²`, `mm`, `RPM`, `W`), material grade (`AISI 316` vs `AISI 304`), and batch ID (`Lote #NNN`).
3. **Nomenclature, Brand & Zero-Residue Policy Decommissioning**:
   - Enforce canonical corporate casing, phonetic standards, visual palette invariants, and regional communication matrices. Remove superseded business clauses from active documents and record transitions in `CHANGELOG.md`.
