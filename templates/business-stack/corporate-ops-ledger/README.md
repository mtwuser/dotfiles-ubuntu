# Business-Stack Template: Corporate Operations & Ledger Architecture (`corporate-ops-ledger`)

Ready-to-apply **Business-Stack Template Pack** (`kind: "business-stack"`, `extends: "business-base"`) for corporate holdings, legal/IP & finance departments, operations/lab units, and brand/marketing workspaces.

> **Why `corporate-ops-ledger` Exists (The Business Counterpart to `fastapi-hexagonal`)**:
> - Just as `fastapi-hexagonal` materializes `technical-base` into a concrete **Hexagonal Software Architecture** (`domain/ -> application/ -> infrastructure/`), `corporate-ops-ledger` materializes `business-base` into a concrete **Hexagonal Business Architecture**:
>   - **Inner Hexagon (`corporate/ledgers/`)**: Immutable Single Source of Truth registries (unit economics/pricing BOM, legal/IP & patent dockets, contract schedules, and production/lab batch logs).
>   - **Application Ring (`corporate/policies/` & `corporate/sops/`)**: Normative policies and Standard Operating Procedures authored in the **Three-Part Business `AAA` Pattern** (`# Scope & Surface Target` $\rightarrow$ `# Normative Invariants` $\rightarrow$ `# Verification & Sign-Off Gates`).
>   - **Outer Hexagon (`surfaces/{web,forms,print}/`)**: Customer-, partner-, and regulator-facing adapters that project ledger facts onto web pages, commercial contracts/forms, and print/packaging specs without ever inventing numbers or leaking trade secrets.

---

## Quick Setup (Deterministic CLI)

```bash
# Materialize business-base + corporate-ops-ledger into a corporate/department/project workspace
./scripts/layer-config.sh apply-project /path/to/dept-workspace --template corporate-ops-ledger --layers all
```

---

## Template Pack Contents

### Rules (`.agents/rules/`)
| File | Scope (`corporate-ops-ledger` Delta over `business-base`) |
|------|-----------------------------------------------------------|
| `rules/ops-ledger-architecture.md` | Canonical workspace directory layout (`corporate/{ledgers,policies,sops,contracts}/` $\rightarrow$ `surfaces/{web,forms,print}/`), `[DEPT]-[TYPE]-[YYYY]-[NNN]` ledger ID taxonomy, ready-to-copy Business `AAA` policy template, and cross-surface cascade checklist |

### Skills (`.agents/skills/`)
| File | Skill Name & Purpose |
|------|----------------------|
| `skills/ledger-surface-audit/SKILL.md` | `ledger-surface-audit` — Step-by-step audit procedure verifying `1:1:1` Ledger $\leftrightarrow$ Policy $\leftrightarrow$ Surface alignment, zero unbacked claims, and IP/Trade-Secret firewall compliance |
