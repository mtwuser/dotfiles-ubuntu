# Documentation Index — `dotfiles-ubuntu`

> **Navigable Knowledge Hub for Humans and AI Agents**
>
> This `docs/` directory provides a structured, navigable map of `dotfiles-ubuntu`'s internal architecture, enterprise Human-AI governance model, and maintainer extension workflows.
>
> When an AI agent (Google Antigravity 2.0, Gemini Code Assist, GitHub Copilot, or Google Jules) works on this repository, reading this index first allows it to locate exact subsystem contracts, JSON hook schemas, and script invariants immediately — without brute-force scanning across all shell and Python files.

---

## 1. Document Hierarchy & Navigation Map

```
docs/
├── README.md                                          ← You are here (Navigable Index & Subsystem Map)
├── architecture/                                      ← Normative technical specifications (how it works)
│   ├── 01_system_and_stow_engine.md                   ← Ubuntu 26.04 engine, 3-stage APT filter, Stow tree unfolding
│   └── 02_antigravity_governance_and_hooks.md         ← Token budget (<18KB), 4 lifecycle hook JSON contracts, 11 skills
└── reference/                                         ← Conceptual guides, enterprise use cases & extension playbooks
    ├── enterprise_pair_programming_governance.md      ← Enterprise "pAIr programming" governance, Google AI docs tools & Copilot mapping
    └── developer_and_extension_guide.md               ← Maintainer playbook: adding stow/non-stow dirs, templates, recipes & hooks
```

| Layer / Category | Document | Scope & Key Contents |
|------------------|----------|----------------------|
| **Architecture 01** | **[`docs/architecture/01_system_and_stow_engine.md`](architecture/01_system_and_stow_engine.md)** | Tripartite lifecycle (`backup.sh` $\leftrightarrow$ `audit.sh` $\leftrightarrow$ `bootstrap.sh`), 3-stage APT filtering pipeline, `system/external/{apt-repo,deb-url,script}/` plugin contracts, GNU Stow tree-unfolding invariants, and non-stow root directory exclusions (`system`, `scripts`, `templates`, `docs`). |
| **Architecture 02** | **[`docs/architecture/02_antigravity_governance_and_hooks.md`](architecture/02_antigravity_governance_and_hooks.md)** | Three-surface shared `~/.gemini/config/` architecture, Antigravity 2.0 20,000-token `defaultRulesBudget` & 18 KB `AGENTS.md` cap, sequence diagram and `stdin`/`stdout` JSON contracts for all 4 Python 3.14 lifecycle hooks (`PreToolUse`, `PostToolUse`, `PostInvocation`, `Stop`), 11 global skills catalog, and Layer 2 starter templates. |
| **Reference 01 (Enterprise Use Case)** | **[`docs/reference/enterprise_pair_programming_governance.md`](reference/enterprise_pair_programming_governance.md)** | **Distributed Human-AI Governance ("pAIr programming") at Scale**: 3-tier organizational fork hierarchy (`Corporate → Team → Project`), bidirectional organic knowledge evolution (`/learn` $\rightarrow$ `/enrich`), the 4th Pillar (navigable `docs/` + **Google Jules**, **Gemini Code Assist Enterprise**, **NotebookLM**, **Developer Knowledge MCP**), and 1:1 portability matrix to **VS Code & GitHub Copilot**, **Cursor**, and **Claude Code**. |
| **Reference 02 (Maintainer Guide)** | **[`docs/reference/developer_and_extension_guide.md`](reference/developer_and_extension_guide.md)** | Step-by-step extension guide for `dotfiles-ubuntu`: adding new stow vs. non-stow root directories safely, creating new Layer 2 stack templates (`templates/<stack>/`), adding external Ubuntu package recipes, and running pre-release verification (`verify-repo.sh`, `audit-global-config.sh`, `audit.sh`). |
| **Root Guides & Policies** | **[`README.md`](../README.md)** · **[`CONTRIBUTING.md`](../CONTRIBUTING.md)** · **[`SECURITY.md`](../SECURITY.md)** · **[`ACCESSIBILITY.md`](../ACCESSIBILITY.md)** · **[`CHANGELOG.md`](../CHANGELOG.md)** | Quick Start (3 adoption paths), contributor standards, secret/identity isolation policy (`~/.gitconfig.local`, `~/.bashrc.local`), terminal/screen-reader accessibility, and SemVer release history. |

---

## 2. End-to-End Architecture Overview

```mermaid
flowchart TD
    subgraph Corp["Subsystem 1: Declarative Ubuntu 26.04 & GNU Stow Engine (Architecture 01)"]
        SYS["system/* Manifests & External Catalog\n(APT, Snaps, NPM, DEB822 Repos, GNOME)"]
        ENG["System Engine Scripts\n(bootstrap.sh · backup.sh · audit.sh)"]
        STOW["GNU Stow Modules\n(bash/ · git/ · antigravity/)"]
        SYS <--> ENG
        ENG --> STOW
    end

    subgraph AI["Subsystem 2: Distributed Human-AI Governance & Hooks (Architecture 02 & Reference 01)"]
        L1["Layer A: Corporate / Global Baseline\n(antigravity/.gemini/config/AGENTS.md + hooks.json + 11 skills)"]
        L2["Layer B: Team / Stack Starter Templates\n(templates/fastapi-hexagonal/*)"]
        L3["Layer C: Project-Local Context\n(<project>/.agents/rules & skills + WORKTASK.md)"]
        L4["Layer D: Navigable Repository Docs\n(<project>/docs/README.md + architecture/ + reference/)"]
        L1 -->|"Downward Inheritance"| L2
        L2 -->|"Scaffolds"| L3
        L3 <-->|"Grounded by"| L4
        L3 -.->|"/learn & /enrich\nUpward Promotion"| L1
    end

    STOW -->|"Tree-Unfolded Symlinks\n~/.gemini/config/"| L1
```

---

## 3. Quick Lookup for AI Agents Working on `dotfiles-ubuntu`

| If your task involves... | Read this specification first | Run this verification command after editing |
|--------------------------|-------------------------------|---------------------------------------------|
| Modifying `bootstrap.sh`, `backup.sh`, `audit.sh`, or `system/` | [`docs/architecture/01_system_and_stow_engine.md`](architecture/01_system_and_stow_engine.md) | `./scripts/verify-repo.sh && ./audit.sh` |
| Modifying `AGENTS.md`, `hooks.json`, `scripts/*.py`, or `skills/*/SKILL.md` | [`docs/architecture/02_antigravity_governance_and_hooks.md`](architecture/02_antigravity_governance_and_hooks.md) | `stow -t ~ -R antigravity && ./scripts/verify-repo.sh && ./scripts/audit-global-config.sh` |
| Adding a new root directory or Layer 2 project template (`templates/`) | [`docs/reference/developer_and_extension_guide.md`](reference/developer_and_extension_guide.md) | `./scripts/verify-repo.sh && ./audit.sh` |
| Explaining or adapting the model for enterprise teams or VS Code / Copilot | [`docs/reference/enterprise_pair_programming_governance.md`](reference/enterprise_pair_programming_governance.md) | `./scripts/verify-repo.sh` |
