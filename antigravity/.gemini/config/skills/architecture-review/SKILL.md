---
name: architecture-review
description: "Use when designing framework architecture, reviewing multi-dimensional specifications, unifying orthogonal classifications, or enforcing cross-document naming coherence."
---

# Architecture Review — Universal Skill

> **When to use**: Activate this skill when working on framework design, architectural specifications, or cross-document terminology refactoring.

---

## Intersection Audit Pattern

When working on framework design or architecture, apply this pattern systematically
to discover unifying concepts (like `DeliveryChannel` emerged from Zone × Tier):

### The 5-Step Process

1. **Identify orthogonal dimensions**: Search for independent classification
   pairs — two axes that describe different aspects of the same system
   (e.g., *where* something renders × *how fast* it processes).

2. **Build the complete matrix**: For each pair, construct the full combination
   table. Ask: "Does each cell have a name? Is it valid? What's the reason
   for invalid cells?"

3. **Evaluate atomicity**: If the intersection defines a unit that the
   developer needs to choose or implement → formalize it with a name
   and an enum. One cell = one atomic decision.

4. **New developer test**: Would a developer unfamiliar with the framework
   understand this combination as ONE decision or N separate decisions?
   If N > 1, there is a simplification opportunity.

5. **Impact assessment**: Does naming this intersection reduce the number
   of independent configuration choices? If yes → formalize. If the name
   doesn't reduce complexity, it's premature abstraction.

### When to Trigger

- You notice two classification systems referenced together without a unified name
- A configuration requires choosing values from two independent dimensions
- A developer asks "how do I combine X with Y?" and no single answer exists
- Documentation describes the same concept under different names in different contexts

### Anti-Pattern: Premature Intersection

Not every pair of dimensions produces a useful intersection. Before formalizing:
- Verify that at least 60% of cells are valid (otherwise the dimensions are coupled, not orthogonal)
- Confirm that a developer would encounter this combination in practice
- Check that the name captures **purpose**, not just structure

---

## Cross-Document Coherence & 5-Dimension Pre-Development Gate

After any architectural change that affects terminology, structure, or core mechanisms, execute this **5-Dimension Sweep** in order before resuming code implementation:

1. **Normative Specifications (`docs/architecture/`)**: Update the authoritative specs first, including code snippets, imports, directory trees, and glossary appendices.
2. **Reference Guides & Indexes (`docs/reference/`, `docs/verticals/`)**: Align conceptual guides, ADR documents, and vertical indexes so zero contradictions exist with normative specs.
3. **Diagrams (`docs/diagrams/*.mmd`)**: Verify that diagram node labels, edges, and filenames match canonical terminology and are written in 100% pure English.
4. **Root Guides & Agent Rules (`WHITEPAPER*.md`, `ARCHITECTURE.md`, `README.md`, `.agents/rules/`)**: Synchronize root entry points, directory trees, and agent rules.
5. **Future Roadmaps (`roadmaps/*.md`)**: Propagate new enums, invariants, dimensions, and test paths into pending roadmap phases so future implementation tasks do not reintroduce obsolete designs.

### Deterministic Verification Gates

1. **Zero-Residue Grep**: Search ALL documentation and diagrams for retired terms (`grep -rn "old_term" docs/ roadmaps/` = 0 results).
2. **Bilingual Structural Parity**: For projects maintaining bilingual pairs (`*.md` and `*_es.md`), verify 1:1 parity in heading counts (`#`–`######`) and fenced code block counts (` ``` `) across every pair.
3. **Language Purity**: Verify 0 non-English characters or untranslated labels in English `.md` and `.mmd` files.
4. **Relative Link Integrity**: Verify that every relative markdown link (`[label](path/to/file.md)`) resolves to an existing file on disk.

---

## Naming Governance (Generic)

When naming architectural concepts:

- Each term should have exactly ONE meaning across the entire project
- If a term is overloaded (means different things in different contexts),
  create distinct names immediately — don't defer
- Names should capture **purpose** (what it DOES), not structure (how it's BUILT)
- When renaming, execute a full surgical replacement across ALL files in the
  same changeset (Zero-Backward Law)
