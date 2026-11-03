# Science-Stack Template: Scientific, Legal & Public-Administration Knowledge Branch (`scientific-knowledge-branch`)

Ready-to-apply **Science-Stack Template Pack** (`kind: "science-stack"`, `extends: "business-base"`) for scientific laboratories, legal/statutory departments, public-administration registries (`dept-justice`, `dept-tax`, `dept-environment`), territorial/geographic catalogs (`geo-*`), and academic research workspaces.

> **Why `scientific-knowledge-branch` Exists (The Epistemic Counterpart to `corporate-ops-ledger` & `fastapi-hexagonal`)**:
> - Just as `fastapi-hexagonal` materializes `technical-base` into a **Hexagonal Software Architecture** and `corporate-ops-ledger` materializes `business-base` into a **Hexagonal Business Ledger Architecture**, `scientific-knowledge-branch` materializes `business-base` into a **Modular Scientific & Statutory Knowledge Architecture**:
>   - **Lightweight Epistemic Routing Rules (`.agents/rules/`)**: Defines the discipline's `Trunk -> Branch -> Specialty` taxonomy, primary-evidence hierarchy, SI/ISO units, and where to locate authoritative references without bloating the `always_on` token budget ($\le 80\text{ KB}$).
>   - **3-Tier Modular Reference Corpus (`docs/`, `< 465` lines per file)**: Stores complete statutory codes, jurisprudence, environmental/territorial inventories, or experimental protocols indexed via `docs/README.md` and queried on demand via `make consult LAYER=<id> QUERY="..."` (`rcap1`).
>   - **Orthogonal `Human-Stack` Adaptation (`precedence: 85..95`)**: Keeps the objective scientific/statutory methodology (`science-stack`) independent from the operator's contextual seniority (`domain-<area>:L1..L4` in `.agents/SESSION.md`).

---

## Quick Setup (Deterministic CLI)

```bash
# Materialize business-base + scientific-knowledge-branch into a public-admin, legal, or research workspace
./scripts/layer-config.sh apply-project /path/to/workspace --template scientific-knowledge-branch --layers all
```

---

## Template Pack Contents

### Rules (`.agents/rules/`)
| File | Scope (`scientific-knowledge-branch` Delta over `business-base`) |
|------|------------------------------------------------------------------|
| `rules/scientific-methodology.md` | `Trunk -> Branch -> Specialty` epistemic taxonomy (`SCI-01`), primary-source & citation hierarchy (`SCI-02`), lightweight routing rules vs. modular `< 465`-line `docs/` corpus queried via `make consult` (`SCI-03`), and contextual `Human-Stack` (`L1..L4`) didactic adaptation (`SCI-04`) |
