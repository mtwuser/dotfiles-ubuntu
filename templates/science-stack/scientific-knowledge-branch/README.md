# Science-Stack Template: Scientific, Legal & Public-Administration Knowledge Branch (`scientific-knowledge-branch`)

Ready-to-apply **Science-Stack Template Pack** (`kind: "science-stack"`, `extends: "science-base"`) for scientific laboratories, legal/statutory departments, public-administration registries (`dept-justice`, `dept-tax`, `dept-environment`), territorial/geographic catalogs (`geo-*`), and academic research workspaces.

> **Why `scientific-knowledge-branch` Exists (The Epistemic & Physical-Engineering Counterpart to `software-engineering` & `corporate-ops-ledger`)**:
> - Just as `software-engineering` materializes `science-base` into **Executable Computer Science & Software Engineering Rigor** (`fastapi-hexagonal`, `angular-web`, `django-backend`, `nist-csf-security`) and `corporate-ops-ledger` materializes `business-base` into a **Hexagonal Business Ledger Architecture**, `scientific-knowledge-branch` materializes `science-base` across the **6 Canonical Knowledge Trunks (`CANONICAL_SCIENCE_TRUNKS`: `sci-formal`, `sci-nature`, `sci-health`, `sci-engineering`, `sci-social`, `sci-humanities`)** as well as statutory (`gov-*`) and territorial (`geo-*`) corpora:
>   - **Lightweight Epistemic Routing Rules (`.agents/rules/`)**: Defines the discipline's `Trunk -> Branch -> Specialty` taxonomy (supporting both umbrella trunks like `sci-health` / `sci-engineering` and standalone high-volume branch repositories like `sci-medicine` / `sci-physics`), primary-evidence hierarchy, SI/ISO units, and where to locate authoritative references without bloating the `always_on` token budget ($\le 18\text{ KB}$).
>   - **Dual-Ring Corpus (`docs/reference/` for Scientific Truth vs. `docs/guides/` for Academic `M1..M4` Progression)**: Stores complete statutory codes, physical/industrial engineering standards (`sci-engineering`: civil, mechanical, electrical, chemical, telecom, industrial safety), clinical protocols (`sci-health` / `sci-medicine`), or physical laws (`sci-nature` / `sci-physics`) in `docs/reference/` (`E3..E0`, `L0..L3`), while academic curricula in `docs/guides/` link to `docs/reference/` via `citation_receipt` pointers (`CITATION_DRIFT_DETECTED` on upstream scientific updates).
>   - **Orthogonal `Human-Stack` Adaptation (`precedence: 85..95`)**: Keeps the objective scientific/engineering/statutory methodology (`science-stack`) independent from the operator's academic or professional seniority (`domain-<area>:M1..M4` in `.agents/SESSION.md`).

---

## 1. Quick Setup (Deterministic CLI)

Apply the `scientific-knowledge-branch` pack and inherited `science-base` rules with a single CLI command:

```bash
# Materialize science-base + business-base + scientific-knowledge-branch into a public-admin, legal, or research workspace
./scripts/layer-config.sh apply-project /path/to/workspace --template scientific-knowledge-branch --layers all
```

---

## 2. Template Pack Contents

### 2.1. Rules (`.agents/rules/`)

Projected rules enforce `Trunk -> Branch -> Specialty` epistemic routing, primary-source hierarchy, and modular `docs/` indexing:

| File | Scope (`scientific-knowledge-branch` Delta over `science-base`) |
|------|-----------------------------------------------------------------|
| `rules/scientific-methodology.md` | `Trunk -> Branch -> Specialty` epistemic taxonomy (`SCI-01`), primary-source & citation hierarchy (`SCI-02`), lightweight routing rules vs. modular `< 465`-line `docs/` corpus queried via `make consult` (`SCI-03`), and contextual `Human-Stack` (`M1..M4`) didactic adaptation (`SCI-04`) |
