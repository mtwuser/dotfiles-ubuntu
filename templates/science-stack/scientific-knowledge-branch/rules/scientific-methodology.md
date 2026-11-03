---
trigger: always_on
description: "Scientific, legal, and territorial knowledge-branch methodology, 3-tier docs indexing, and primary source citation rules (scientific-knowledge-branch)."
---

# Scientific & Disciplinary Knowledge-Branch Rules (`scientific-knowledge-branch`)

> Standardizes how scientific, legal, public-administration, and territorial workspaces structure formal branches of knowledge (`science-stack`), combining lightweight routing rules in `.agents/rules/` with modular, on-demand reference libraries in `docs/` and `corporate/`.

---

## Scope & Surface Target

- **Template Pack**: `templates/science-stack/scientific-knowledge-branch/` (`science-stack`, `extends: business-base`).
- **Applies**: Public-administration (`public-gov-root` at `1..2`, and public departments `dept-justice`, `dept-tax`, `dept-territorial` / `geo-*`, `dept-environment` at `3..4`), research/laboratory (`dept-bio-lab`), legal, and academic workspaces governing `docs/**`, `corporate/**`, and `surfaces/**`.

---

## Normative Invariants

> *"Lightweight epistemic rules in `.agents/rules/`; exhaustive, indexed primary sources in `docs/`."*

1. **`SCI-01` — Epistemic Routing vs. 3-Tier Indexed Reference Library (`docs/`)**:
   - **Never dump entire codes of law, flora/fauna catalogs, or empirical tables into `.agents/rules/*.md`**. Keep rule files concise (`< 4 KB`) as **epistemic routers** that specify: (a) the hierarchy of norms or scientific axioms, (b) mandatory citation formats, and (c) the directory map of where detailed knowledge lives in `docs/`.
   - Store the full body of statutes, treaties, geographic/ecological inventories, or scientific manuals as modular Markdown files (`< 465` lines per file) under `docs/reference/` or `corporate/` (indexed in `docs/README.md` with step-by-step procedural guides in `docs/guides/`).
2. **`SCI-02` — Arboreal Knowledge Specialization (`Trunk -> Branch -> Specialty`)**:
   - Structure domain knowledge from foundational axioms (`Trunk`: e.g., Constitutional/Administrative Law, General Ecology, Classical Mechanics) $\rightarrow$ specialized disciplines (`Branch`: e.g., Tax Law, Botany/Fauna, Organic Chemistry) $\rightarrow$ applied cross-domain practice (`Specialty`: e.g., R&D Tax Credits, Protected-Area Impact Assessment).
   - Every factual, statutory, or scientific statement in a deliverable MUST cite its verifiable primary record (`[LAW-ID · Art. N]`, `[ISO-NNNN]`, `[TAXON-ID]`, or `[DEPT]-[TYPE]-[YYYY]-[NNN]`) with exact SI/ISO units, dates, and tolerances.
3. **`SCI-03` — Zero-Idle-Token Cross-Layer Consultation (`make consult`)**:
   - When a workspace crosses multiple disciplines or public-administration layers (e.g., a corporate legal or bio-lab workspace consulting `layers/dept-justice`, `layers/dept-tax`, or `layers/dept-territorial`), query the target layer's `docs/` on demand via `./scripts/layer-config.sh consult-layer . --layer <id> --query "<text>"` (`make consult LAYER=<id> QUERY="<text>"`) rather than duplicating foreign reference libraries.
4. **`SCI-04` — Contextual `Human-Stack` Didactic Adaptation (`L1..L4`)**:
   - Enforce `100%` of statutory, empirical, and *Lex Superior* (`0..80`) invariants regardless of operator seniority.
   - Adapt explanation depth to the operator's maturity in the **active workspace's branch**: provide step-by-step Socratic guidance and cross-discipline analogies when the operator is at `L1/L2` in that science branch, and execute directly with terse technical precision when the operator is at `L3/L4`.

---

## Verification & Sign-Off Gates

- [ ] Every statutory, geographic, or scientific claim cites an indexed primary source in `docs/reference/` or `corporate/` (`0` unverified approximations).
- [ ] All reference files under `docs/**` and `corporate/**` are `< 465` lines and reachable from `docs/README.md`.
- [ ] `make diff` (`layer-config.sh diff-project`) reports zero unintended drift against inherited layer templates.
