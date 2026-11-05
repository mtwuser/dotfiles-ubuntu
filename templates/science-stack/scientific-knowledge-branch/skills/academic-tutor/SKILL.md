---
name: academic-tutor
description: "Personalize scientific, statutory, and engineering knowledge delivery across the Academic (M1..M2) -> Professional (M3) -> Scientific (M4) continuum using Socratic progression and citation_receipt grounding."
---
# Skill: Academic-to-Professional Continuum Tutor (`academic-tutor`)

> Operationalizes the **Consumer Viewpoint (`M1..M4` Adaptive Guardrails)** across `sci-*`, `gov-*`, `geo-*`, and `org-uni-*` knowledge libraries without diluting the underlying `E3/E2` reference corpus.

---

## 1. Dual Viewpoint Separation (`Maintainer` vs. `Consumer`)

1. **Maintainer / Producer Viewpoint (Information Architecture)**:
   - **`sci-*` / `gov-*` / `geo-*` (`docs/reference/` — `E3/E2`)**: Maintains consolidated scientific laws, clinical evidence, and statutes by `Trunk -> Branch -> Specialty`.
   - **`org-uni-*` (`docs/guides/` — `E1`)**: Universities and academic institutions curate degree syllabi, lab exercises, and `M1..M4` learning progressions citing `docs/reference/` via `citation_receipt`.
   - **`org-*` Enterprises (`corporate/` & `src/` — `M3/M4`)**: Post-academic professional practice applying scientific and statutory truth to production products and services.
2. **Consumer Viewpoint (Personalization Guardrails)**:
   - Inspect active `human_stack` facets (`make status` or `query_governance_rules` -> `consumer_viewpoint`).
   - Never expose an `M1` learner to uncontextualized `L3` research proofs when a foundational `docs/guides/` (`L1/E1`) progression exists.

---

## 2. Maturity-Graded Delivery Protocol (`M1 -> M4`)

| Consumer Level | Continuum Stage | Retrieval Priority (`consumer_viewpoint`) | Pedagogical & Operational Guardrails |
| :--- | :--- | :--- | :--- |
| **`M1` (*Novice / Year-1 Undergrad*)** | **Academic Foundation** | `academic-tutor-m1-m2` (`docs/guides/` `L1` first) | Use Socratic questions, intuitive physical/domain mental models, and zero unexplained jargon; link every concept to its `E3` axiom via `citation_receipt`. |
| **`M2` (*Intermediate / Upper Undergrad*)** | **Academic Core** | `academic-tutor-m1-m2` (`docs/guides/` `L1 -> L2`) | Introduce canonical `E2` equations, statutory structure, and worked boundary examples (`N` vs `N ± 1`). |
| **`M3` (*Practitioner / Professional*)** | **Professional Practice** | `professional-scientific-m3-m4` (`docs/reference/` & `docs/architecture/` `E3/E2` `L2`) | Deliver production-ready engineering/clinical/legal contracts, trade-off matrices, and `AAA` verification gates directly. |
| **`M4` (*Researcher / Principal*)** | **Scientific Frontier** | `professional-scientific-m3-m4` (`docs/reference/` `E3/E2` `L3` + `E1/E0` frontier) | Unfold `L3` first-principles proofs, raw empirical datasets, and open `E0` hypotheses with zero introductory boilerplate. |
