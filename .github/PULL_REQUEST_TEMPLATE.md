## Summary

<!-- Briefly describe what this Pull Request adds, fixes, or updates. -->

## Affected Layer / Component

- [ ] **System Engine (`bootstrap.sh`, `backup.sh`, `audit.sh`, `system/`)**
- [ ] **GNU Stow Modules (`bash/`, `git/`, `antigravity/`)**
- [ ] **Antigravity 2.0 Global Rules & Hooks (`AGENTS.md`, `hooks.json`, `scripts/*.py`)**
- [ ] **Antigravity 2.0 Global Skills (`antigravity/.gemini/config/skills/`)**
- [ ] **Contextual MCP Server, N-Layer Surface Weaver, `rcap1` Compaction & Ephemeral Forks (`scripts/dotfiles_mcp/`, `scripts/dotfiles_mcp_server.py`, `scripts/layer-config.sh`, `scripts/layer-subtree.sh`, `system/mcp-layer.json`, `Dockerfile`)**
- [ ] **Polymorphic Templates & Overlays (`templates/`)**
- [ ] **Automated Test Suite (`tests/unit/`, `tests/imp/`, `tests/e2e/`)**
- [ ] **Documentation / CI (`README.md`, `docs/`, `CHANGELOG.md`, `scripts/verify-repo.sh`)**

## Community Attribution & Upward Promotion Metadata (Optional)

<!-- All fields below are optional. Leave defaults if contributing anonymously from an Enterprise Root 0. -->

| Field | Value |
| :--- | :--- |
| **Origin Layer / Template Pack** | `e.g., enterprise-root-0 -> templates/business-base` |
| **Contributing Organization / Company (Optional)** | `Anonymous Organization (default)` |
| **Contributors / Roles Involved (Optional)** | `e.g., Principal Enterprise Architect, CLO, CTO, CMO (@github-handles or roles)` |
| **Real-World Validation Context** | `e.g., Validated across Root 0 + 5 Department layers + Squad workspaces` |
| **Release Notes Credit** | `[ ] Credit organization/contributors in CHANGELOG.md` / `[x] Keep anonymous` |

## Verification & Safety Checklist

- [ ] `make verify` (`./scripts/verify-repo.sh`) passes with **0 errors** (SemVer, Bash syntax, `ruff check` + `mypy --strict`, `hooks.json`, `AGENTS.md` `< 18 KB` budget, `kebab-case` `SKILL.md` frontmatter, `< 465`-line modularity gate, `1:1:1` spec traceability, MCP/Subtree/Docker contract, and `pytest` **100% isolated unit + 100% total statement/branch coverage** with AST anti-deception gates)
- [ ] Passed `OSS_AGNOSTICISM_VIOLATION` zero-leak gate (zero private brand, domain, personal identity, or machine-local paths)
- [ ] `VERSION` and `CHANGELOG.md` are updated if this PR cuts a release
