# Security Policy

## Secret & Identity Isolation Architecture

`dotfiles-ubuntu` is designed from the ground up to be safely published in a public Git repository without exposing personal identity, credentials, or machine-specific secrets:

| Sensitive Asset | Isolation Mechanism |
|-----------------|---------------------|
| **Git Identity (`user.name`, `user.email`, signing keys)** | Stored exclusively in `~/.gitconfig.local` (included by `git/.gitconfig` via `[include] path = ~/.gitconfig.local` and excluded in `.gitignore`). `bootstrap.sh` automatically migrates existing identity into `~/.gitconfig.local`. |
| **Shell Secrets & API Tokens (`export *_API_KEY=...`)** | Stored exclusively in `~/.bashrc.local` (sourced at the end of `bash/.bashrc` and excluded in `.gitignore`). |
| **Antigravity OAuth & IDE State (`~/.gemini/*.json`, `mcp_config.json`, `brain/`)** | Kept machine-local via GNU Stow **tree unfolding**. `bootstrap.sh` ensures `~/.gemini/config/` is a real directory and links only `AGENTS.md`, `hooks.json`, `scripts/`, and shared `skills/<name>/`. |
| **SSH / GPG / Netrc Credentials** | Explicitly blocked in `.gitignore` (`.ssh/id_*`, `.ssh/known_hosts`, `.gnupg/`, `.netrc`). |
| **Agent Tool Execution Safety (`PreToolUse`)** | `antigravity/.gemini/config/scripts/pre_tool_guard.py` deterministically intercepts and denies (`"decision": "deny"`) automatic execution of mutating `git` commands (`add`, `commit`, `push`, `reset --hard`, `clean -f`), manual edits to `alembic/versions/`, and non-empty writes to consumer `__init__.py` files. |
| **Contextual MCP Server Isolation (`scripts/dotfiles_mcp_server.py`)** | Strictly read-only, zero-dependency `stdio` server ([`docs/architecture/03_contextual_mcp_and_federation.md`](docs/architecture/03_contextual_mcp_and_federation.md)). Exposes zero arbitrary shell execution or file-mutation tools, enforces `Path.resolve()` containment inside the repository root (`REPO_DIR`), and structurally excludes `~/.bashrc.local`, `~/.gitconfig.local`, `.env`, and `~/.gemini/*.json`. |

---

## Supported Versions

| Version | Target OS | Supported |
|---------|-----------|:---------:|
| `1.x` | Ubuntu 26.04 LTS ("Resolute Raccoon") & Google Antigravity 2.0 | ✅ |

---

## Reporting a Vulnerability

If you discover a security issue (for example, a script pattern that could inadvertently capture sensitive dconf keys, environment variables, or local credentials during `./backup.sh`), please report it by opening a security advisory on GitHub or contacting the repository maintainer directly before disclosing it publicly.
