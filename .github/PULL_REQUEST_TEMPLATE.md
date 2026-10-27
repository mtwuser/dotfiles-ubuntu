## Summary

<!-- Briefly describe what this Pull Request adds, fixes, or updates. -->

## Affected Layer / Component

- [ ] **System Engine (`bootstrap.sh`, `backup.sh`, `audit.sh`, `system/`)**
- [ ] **GNU Stow Modules (`bash/`, `git/`, `antigravity/`)**
- [ ] **Antigravity 2.0 Global Rules & Hooks (`AGENTS.md`, `hooks.json`, `scripts/*.py`)**
- [ ] **Antigravity 2.0 Global Skills (`antigravity/.gemini/config/skills/`)**
- [ ] **Project Starter Templates (`templates/fastapi-hexagonal/`)**
- [ ] **Documentation / CI (`README.md`, `CHANGELOG.md`, `scripts/verify-repo.sh`)**

## Verification & Safety Checklist

- [ ] `./scripts/verify-repo.sh` passes with **0 errors** (SemVer, Bash syntax, Python/Ruff hooks, `hooks.json`, `AGENTS.md` `< 18 KB` budget, `kebab-case` `SKILL.md` frontmatter)
- [ ] Zero personal identity (`user.name`, `user.email`), SSH/GPG keys, OAuth tokens, or machine-local paths are included
- [ ] `VERSION` and `CHANGELOG.md` are updated if this PR cuts a release
