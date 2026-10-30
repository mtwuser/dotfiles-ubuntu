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

## Verification & Safety Checklist

- [ ] `make verify` (`./scripts/verify-repo.sh`) passes with **0 errors** (SemVer, Bash syntax, `ruff check` + `mypy --strict`, `hooks.json`, `AGENTS.md` `< 18 KB` budget, `kebab-case` `SKILL.md` frontmatter, `< 465`-line modularity gate, `1:1:1` spec traceability, MCP/Subtree/Docker contract, and `pytest` **100% isolated unit + 100% total statement/branch coverage** with AST anti-deception gates)
- [ ] Zero personal identity (`user.name`, `user.email`), SSH/GPG keys, OAuth tokens, or machine-local paths are included
- [ ] `VERSION` and `CHANGELOG.md` are updated if this PR cuts a release
