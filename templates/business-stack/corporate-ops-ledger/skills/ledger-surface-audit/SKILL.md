---
name: ledger-surface-audit
description: Audit 1:1:1 traceability between Inner Ledgers (corporate/ledgers/), Business AAA Policies (corporate/policies/), and Outer Surfaces (surfaces/{web,forms,print}/)
---
# Skill: Ledger-to-Surface `1:1:1` Compliance Audit (`ledger-surface-audit`)

---

## Purpose

Executes a deterministic **Business `1:1:1` Traceability Audit** (`Inner Ledger <-> Policy/SOP <-> Outer Surface`), ensuring that no commercial, web, form, or print surface drifts from official `corporate/ledgers/` records or leaks protected IP.

---

## 4-Step Audit Workflow

### Step 1: Inventory Inner Ledgers (`corporate/ledgers/`)
1. Read the active ledger files under `corporate/ledgers/` (financial/pricing tables, legal/IP docket, operational batch logs).
2. Extract the authoritative `[DEPT]-[TYPE]-[YYYY]-[NNN]` identifiers, exact figures (`EUR`/`USD`), `SI`/`ISO` units, and confidentiality classification (`Public`, `20/80 Summary`, `Restricted <TS-ID>`).

### Step 2: Verify Business `AAA` Structure in Policies & SOPs (`corporate/{policies,sops}/`)
Check every Markdown document in `corporate/policies/` and `corporate/sops/` for the three mandatory sections:
- `## Scope & Surface Target` (*Arrange*)
- `## Normative Invariants` (*Act*)
- `## Verification & Sign-Off Gates` (*Assert*)

Flag any policy missing one of these sections or lacking a `> **Ledger Grounding**:` header.

### Step 3: Cross-Surface Claim & Drift Sweep (`surfaces/{web,forms,print}/`)
Scan all files in `surfaces/web/`, `surfaces/forms/`, and `surfaces/print/`:
1. **Unbacked Claim Detection**: Flag any price, discount, lead time, environmental claim, or technical tolerance that does not cite or match an entry in `corporate/ledgers/`.
2. **Rounding & Unit Drift**: Verify that currencies (`EUR` vs. `USD`), cost basis (`Lean` vs. `Full COTS`, VAT inclusion), and `SI`/`ISO` units match the ledger character-for-character.
3. **Print & Accessibility Pre-Flight**: On `surfaces/print/` and `surfaces/web/` specs, verify WCAG contrast gates (`>= 4.5:1` body, `>= 7:1` safety) and print bleed/resolution gates (`>= 3 mm` bleed, `>= 300 DPI`).

### Step 4: World Novelty & Trade Secret Firewall Check
Confirm that restricted items (`<PAT-ID>` prior to filing date or `<TS-ID>` trade secrets) are referenced only by their opaque registry ID or approved `20/80` functional outcome, never exposing internal chemical/algorithmic ratios or supplier BOM breakdowns on external surfaces.
