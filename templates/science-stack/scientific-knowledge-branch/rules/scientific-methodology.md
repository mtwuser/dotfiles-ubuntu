---
trigger: always_on
description: "Scientific, legal, and territorial knowledge-branch methodology, 3-tier docs indexing, and primary source citation rules (scientific-knowledge-branch)."
---

# Scientific & Disciplinary Knowledge-Branch Rules (`scientific-knowledge-branch`)

> Standardizes how scientific, legal, public-administration, and territorial workspaces structure formal branches of knowledge (`science-stack`), combining lightweight routing rules in `.agents/rules/` with modular, on-demand reference libraries in `docs/` and `corporate/`.

---

## Scope & Surface Target

- **Template Pack**: `templates/science-stack/scientific-knowledge-branch/` (`science-stack`, `extends: science-base`).
- **Applies**: Public-administration (`public-gov-root` at `1..2`, and public departments `dept-justice`, `dept-tax`, `dept-territorial` / `geo-*`, `dept-environment` at `3..4`), research/laboratory (`dept-bio-lab`), legal, and academic workspaces governing `docs/**`, `corporate/**`, and `surfaces/**`.

---

## Normative Invariants

> *"Lightweight epistemic rules in `.agents/rules/`; exhaustive, indexed primary sources in `docs/`."*

1. **`SCI-01` — Epistemic Routing vs. Dual-Ring Reference (`docs/reference/`) & Academic Curriculum (`docs/guides/`) Architecture**:
   - **Never dump entire codes of law, flora/fauna catalogs, or empirical tables into `.agents/rules/*.md`**. Keep rule files concise (`< 4 KB`) as **epistemic routers** that specify: (a) the hierarchy of norms or scientific axioms, (b) mandatory citation formats, and (c) the directory or federated library map (`gov-<country>`, `sci-<discipline>`, `geo-<region>`, `org-<entity>`) of where detailed knowledge lives in `docs/`.
   - **Dual-Ring Intra-Library Separation & Dual Viewpoint Model (`Maintainer/Producer` vs. `Consumer M1..M4` Adaptive Guardrails)**:
     - **Maintainer / Producer Viewpoint (`sci-*`, `org-uni-*`, `org-*`)**:
       - **Ring 1 — Pure Scientific, Technical & Statutory Corpus (`docs/reference/` & `docs/architecture/`, `< 465` lines/file)**: Maintained in `sci-*`, `gov-*`, and `geo-*` libraries by `Trunk -> Branch -> Specialty`, graded by **Epistemic Credibility (`E3..E0`)** and **Density (`L0..L3`)** with zero pedagogical dilution.
       - **Ring 2 — Academic Curricula (`org-uni-*` / `docs/guides/`) & Post-Academic Professional Practice (`org-*` Enterprises)**: Universities (`org-uni-*`) curate structured degree curricula across `M1..M4` in `docs/guides/`, citing Ring 1 via **`citation_receipt`** pointers (so any update in `docs/reference/` triggers `CITATION_DRIFT_DETECTED` on dependent academic lessons). Enterprises (`org-*` with `business-stack` + `software-engineering`) maintain the post-academic **Professional Practice (`M3/M4`)** layer, applying `sci-*` and `gov-*` to production systems.
     - **Consumer Viewpoint (`consumer_viewpoint` Guardrails in `query_governance_rules` & `skills/academic-tutor/SKILL.md`)**:
       - **Academic / Foundational Consumer (`domain-<branch>:M1..M2` or `soft-socratic-coach` $\rightarrow$ `consumer_viewpoint: "academic-tutor-m1-m2"`)**: A learner with `M1/M2` mastery cannot productively consume raw `L3`/`E3` research papers first; retrieval prioritizes `docs/guides/` (`E1` pedagogical progressions, Socratic scaffolding, and `M1/M2` analogies) before raw research substrates.
       - **Professional / Scientific Consumer (`domain-<branch>:M3..M4` or default $\rightarrow$ `consumer_viewpoint: "professional-scientific-m3-m4"`)**: Practitioners and researchers receive `E3 -> E2 -> E1` primary reference sources (`docs/reference/`, `docs/architecture/`, and `L2/L3` equations or statutory clauses) directly.
2. **`SCI-02` — 6 Canonical Knowledge Trunks (`CANONICAL_SCIENCE_TRUNKS`), Fractal `Trunk <-> Branch` Granularity & 4-Plane Security Disambiguation**:
   - Structure `sci-*` libraries across the **6 universal UNESCO/Frascati knowledge trunks** (`CANONICAL_SCIENCE_TRUNKS`): **`sci-formal`** (`math`, `logic`, `statistics`, `cs-theory`), **`sci-nature`** (`physics`, `chemistry`, `earth`, `biology`, `astronomy`, `ecology`), **`sci-health`** (`medicine`, `pharmacology`, `nursing`, `public-health`, `nutrition`, `psychology`, `veterinary`), **`sci-engineering`** (`civil`, `industrial`, `mechanical`, `electrical`, `telecom`, `aerospace`, `chemical`, `software`, `security`), **`sci-social`** (`economics`, `sociology`, `demographics`, `education`, `pedagogy`, `jurisprudence`), and **`sci-humanities`** (`philosophy`, `ethics`, `history`, `linguistics`, `arts`).
   - **Fractal `Trunk <-> Branch` Evolution**: A discipline may live inside its umbrella trunk repository (`sci-health` with `docs/reference/{medicine,nursing,pharmacology}/`, `granularity: "trunk-repository"`) or split into a standalone branch repository when volume warrants (`sci-medicine` $\rightarrow$ `canonical_trunk: "health"`, `sci-physics` $\rightarrow$ `canonical_trunk: "nature"`, `granularity: "branch-repository"`).
   - **4-Plane Security & Safety Disambiguation**: Never conflate security domains—route **Public/National/Civil-Protection Security** to `gov-*` (`precedence: 1..4`, `E3`), **Territorial/Geohazard Safety** to `geo-*` (`precedence: 3..4`, `E3`), **Technical/Cyber/Industrial Functional Safety** to `sci-engineering` (`security-engineering`) + `framework-stack/nist-csf-security` (`precedence: 20..50`, `E2`), and **Corporate Fiduciary InfoSec & IP Firewall** to `org-*` / `business-base` (`dept-security` / `dept-legal-ip`, `precedence: 5..9`, `E2`).
   - Every factual, statutory, or scientific statement in a deliverable MUST cite its verifiable primary record (`[LAW-ID · Art. N]`, `[ISO-NNNN]`, `[TAXON-ID]`, `[DEPT]-[TYPE]-[YYYY]-[NNN]`, or canonical `citation_receipt` `<layer_id>::<path>#<section_slug>@<sha256_prefix>:<grade>`) with exact SI/ISO units, dates, and tolerances.
3. **`SCI-03` — Zero-Idle-Token Cross-Layer Consultation (`make consult`), `DMCP`/`GRCC` & Deep-Wiki `L0 -> L3` Gradient**:
   - When a workspace crosses multiple disciplines or public-administration layers (e.g., consulting `layers/gov-*`, `layers/sci-*`, `layers/geo-*`, `specialty/*` branches, or `refs/capsules/*`), query on demand via `make consult LAYER=<id> QUERY="<text>"` or `query_governance_rules(min_epistemic_grade="E2", branch_ref="...")` rather than duplicating foreign reference libraries.
   - Structure documents along the inverse context-to-density gradient: keep `L0/L1` highly contextualized (with `l3_targets` SHA-256 beacons and `citation_receipt` pointers), `L2` as operational contracts/tables, and `L3` as deep-wiki first-principles substrates (mathematical proofs, physical mechanisms, or literal statutory articles).
4. **`SCI-04` — Epistemic Credibility Monotonicity (`E3 > E2 > E1 > E0`), Citation Drift & `Age × Empirical Usage` Lifecycle Radar (`M1..M4`)**:
   - Enforce `100%` of statutory, empirical, and *Lex Superior* (`0..80`) invariants and epistemic monotonicity (`E3` Inviolable Law/Axiom $>$ `E2` Standard/Theorem $>$ `E1` Bounded Theory/Guideline $>$ `E0` Hypothesis/Draft) via `verify_epistemic_context_claims` (primary-source SHA-256 hash grounding, `EPISTEMIC_PRECEDENCE_VIOLATION` guard, `CUT_POINT_BOUNDARY_VIOLATION`, and `CITATION_DRIFT_DETECTED`), and classify corpus sections across the 4-Quadrant `Age × Empirical Usage` Lifecycle Radar (`Q1_HOT_CORE`, `Q2_HIGH_FRICTION`, `Q3_EMERGING_NICHE`, `Q4_NORMATIVE_OBSOLESCENCE`).
   - Adapt explanation depth to the operator's academic/professional maturity in the **active workspace's branch** (`domain-<branch>:M1..M4`): provide step-by-step Socratic guidance and cross-discipline analogies at `M1/M2` (*Undergrad / Foundational*), and execute directly with terse technical precision at `M3/M4` (*Doctoral / Principal*).

---

## Verification & Sign-Off Gates

- [ ] Every statutory, geographic, or scientific claim cites an indexed primary source in `docs/reference/` or `corporate/` (`0` unverified approximations).
- [ ] All reference files under `docs/**` and `corporate/**` are `< 465` lines and reachable from `docs/README.md`.
- [ ] `make diff` (`layer-config.sh diff-project`) reports zero unintended drift against inherited layer templates.
