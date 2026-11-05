---
trigger: always_on
description: "Hexagonal business workspace layout (corporate/ledgers/ -> corporate/policies/ -> surfaces/), [DEPT]-[TYPE]-[YYYY]-[NNN] citation contracts, and Business AAA policy templates (corporate-ops-ledger)."
---

# Corporate Operations & Multi-Surface Ledger Architecture (`corporate-ops-ledger`)

> Inherits universal *Lex Superior* precedence (`0..100`), Single Source of Truth integrity, and quantitative precision from `business-base.md`. This pack defines the **concrete directory architecture, ID taxonomy, and operational templates** for business, legal, financial, and operational workspaces.

---

## 1. Scope & Surface Target

- **Template Pack**: `templates/business-stack/corporate-ops-ledger/` (`kind: "business-stack"`, `extends: "business-base"`).
- **Applies**: Corporate holding repositories, departmental workspaces (`dept-legal`, `dept-finance`, `dept-ops`, `dept-brand`), and cross-functional business projects governing `corporate/**` and `surfaces/**`.

### 1.1. Canonical Hexagonal Business Directory Structure

Organize the workspace into inner factual ledgers (`corporate/ledgers/`), application policies/SOPs (`corporate/{policies,sops}/`), and external channel surfaces (`surfaces/`):

```text
<workspace-root>/
├── corporate/                        # INNER & APPLICATION RINGS — Normative Single Source of Truth
│   ├── ledgers/                      # INNER HEXAGON — Immutable factual registries (Zero narrative inflation)
│   │   ├── finance-pricing.md        # Unit economics, BOM, CAPEX/OPEX, official price & tax tables
│   │   ├── legal-ip-docket.md        # Patent filings (<PAT-ID>), trade secrets (<TS-ID>), trademarks
│   │   └── ops-batch-registry.md     # Production/lab batch records (Batch #NNN), tolerances, QA certs
│   ├── policies/                     # APPLICATION RING — Department & corporate policies (Business AAA)
│   ├── sops/                         # APPLICATION RING — Standard Operating Procedures (Business AAA)
│   └── contracts/                    # Master agreements, NDAs, and SLA schedules
└── surfaces/                         # OUTER HEXAGON — External & Cross-Channel Adapters
    ├── web/                          # Public website copy, landing specs, and digital product sheets
    ├── forms/                        # Commercial order forms, onboarding questionnaires, partner decks
    └── print/                        # Packaging artwork specs (>= 3 mm bleed, >= 300 DPI), labels, brochures
```

### Dependency Direction (`Outer Surfaces -> Normative Policies -> Inner Ledgers`)
```text
surfaces/{web,forms,print}  ──cites──►  corporate/{policies,sops}  ──grounds in──►  corporate/ledgers/
```
- **`corporate/ledgers/`** is the **Inner Hexagon**: it holds raw, audited facts (exact `EUR`/`USD` amounts, `SI`/`ISO` units, filing dates, batch metrics). It never depends on marketing copy or channel formatting.
- **`surfaces/{web,forms,print}/`** is the **Outer Hexagon**: every price, technical tolerance, regulatory claim, or warranty clause published on a surface MUST cite its authoritative Ledger ID (`[DEPT]-[TYPE]-[YYYY]-[NNN]`).

---

## 2. Normative Invariants

1. **`CORP-OPS-01` — Traceable Record ID Taxonomy (`[DEPT]-[TYPE]-[YYYY]-[NNN]`)**:
   - Every ledger entry, policy, SOP, or contract clause MUST carry a stable canonical identifier:
     - `LEGAL-PAT-2026-001` / `LEGAL-TS-2026-004` / `LEGAL-MSA-2026-012`
     - `FIN-BOM-2026-003` / `FIN-PRC-2026-008`
     - `OPS-BAT-2026-104` (`Batch #104`) / `OPS-SOP-2026-007`
     - `BRAND-TOK-2026-002`
2. **`CORP-OPS-02` — Canonical Business `AAA` Document Template**:
   - Every file in `corporate/policies/*.md` and `corporate/sops/*.md` MUST be authored using this exact three-section skeleton:
     ```markdown
     # [DEPT]-[TYPE]-[YYYY]-[NNN]: <Title>

     > **Ledger Grounding**: `corporate/ledgers/<file>.md` (`<ID>`)
     > **Deontic Precedence**: `<0..100>` (`<Role/Department>`)

     ## Scope & Surface Target
     - **Governed Directories**: `corporate/...`, `surfaces/...`
     - **Accountable Roles**: `<Owner / Validator / Operator>`

     ## Normative Invariants
     1. **`<DEPT>-01`**: <Rule with exact threshold, currency/SI unit, and state transition>.
     2. **`<DEPT>-02`**: <Confidentiality / disclosure boundary or operational constraint>.

     ## Verification & Sign-Off Gates
     - [ ] All quantitative claims match `corporate/ledgers/<file>.md` (`<ID>`) with zero rounding drift.
     - [ ] World Novelty / IP firewall verified (no unfiled invention details or secret ratios exposed).
     - [ ] Cross-surface cascade completed across `surfaces/web/`, `surfaces/forms/`, and `surfaces/print/`.
     ```
3. **`CORP-OPS-03` — Cross-Surface Cascade & Zero Orphan Claims**:
   - Updating a price, specification, or legal term in `corporate/ledgers/` requires updating all dependent documents in `surfaces/{web,forms,print}/` in the same task (or logging a `P0`/`P1` outbound delegation in `WORKTASK.md`).
4. **`CORP-OPS-04` — Federated Statutory/Territorial Library Grounding (`gov-*`, `geo-*`, `org-*`) & `Q1..Q4` Lifecycle Radar**:
   - Corporate policies, contracts, and compliance SOPs that depend on external statutory (`gov-<country>`), territorial/zoning (`geo-<territory>`), or holding-federation (`org-<holding>`) corpora MUST record the canonical `citation_receipt` (`<layer_id>::<rel_file>#<section_slug>@<h2_digest16>:<epistemic_grade>`) emitted by `query_governance_rules` / `unfold_context_capsule`.
   - Before promoting a policy or surface change (`make env-gate`), verify that `verify_epistemic_context_claims` reports zero `CITATION_DRIFT_DETECTED` violations against mounted `layers/{gov-*,geo-*,org-*}` clones (`local-mcp-clone -> private-mirror-remote -> public-canonical-remote`), and review `Q4_NORMATIVE_OBSOLESCENCE` (`> 180d` and `0` citations in `.agents/telemetry/citation_stats.json`) for policy consolidation or repeal without overriding higher epistemic authority (`E3 > E2 > E1 > E0`, `epistemic_override_allowed: false`).

---

## 3. Verification & Sign-Off Gates

- [ ] Every policy and SOP under `corporate/{policies,sops}/` contains explicit `## Scope & Surface Target`, `## Normative Invariants`, and `## Verification & Sign-Off Gates` sections.
- [ ] Every quantitative figure, percentage, or regulatory claim in `surfaces/{web,forms,print}/` cites an active `[DEPT]-[TYPE]-[YYYY]-[NNN]` entry in `corporate/ledgers/` (and a verified `citation_receipt` when grounded in mounted `gov-*`, `geo-*`, or `org-*` libraries).
- [ ] Zero unfiled patent mechanisms or trade-secret compositions appear in `surfaces/**`.
