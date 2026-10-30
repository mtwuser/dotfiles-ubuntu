# Security Policy

## Secret & Identity Isolation Architecture

`dotfiles-ubuntu` is designed from the ground up to be safely published in a public Git repository without exposing personal identity, credentials, or machine-specific secrets:

| Sensitive Asset | Isolation Mechanism |
|-----------------|---------------------|
| **Git Identity (`user.name`, `user.email`, signing keys)** | Stored exclusively in `~/.gitconfig.local` (included by `git/.gitconfig` via `[include] path = ~/.gitconfig.local` and excluded in `.gitignore`). `bootstrap.sh` automatically migrates existing identity into `~/.gitconfig.local`. |
| **Shell Secrets & API Tokens (`export *_API_KEY=...`)** | Stored exclusively in `~/.bashrc.local` (sourced at the end of `bash/.bashrc` and excluded in `.gitignore`). |
| **Antigravity OAuth & IDE State (`~/.gemini/*.json`, `mcp_config.json`, `brain/`)** | Kept machine-local via GNU Stow **tree unfolding**. `bootstrap.sh` ensures `~/.gemini/config/` is a real directory and links only `AGENTS.md`, `hooks.json`, `scripts/`, and shared `skills/<name>/`. |
| **SSH / GPG / Netrc Credentials** | Explicitly blocked in `.gitignore` (`.ssh/id_*`, `.ssh/known_hosts`, `.gnupg/`, `.netrc`). |
| **Agent Tool Execution Safety (`PreToolUse`)** | `antigravity/.gemini/config/scripts/pre_tool_guard.py` deterministically intercepts and denies (`"decision": "deny"`) automatic execution of mutating `git` commands (`add`, `commit`, `push`, `reset --hard`, `clean -f`, `subtree add\|pull\|push\|merge`), manual edits to `alembic/versions/`, and non-empty writes to consumer `__init__.py` files across both structured file tools and `run_command` shell writes (output redirections, heredocs, `tee`, `cp`/`mv`, `dd`, and inline `python -c`). |
| **Contextual MCP Server Isolation (`scripts/dotfiles_mcp/` & `scripts/dotfiles_mcp_server.py`)** | Strictly read-only, zero-dependency `stdio` server ([`docs/architecture/03_contextual_mcp_and_federation.md`](docs/architecture/03_contextual_mcp_and_federation.md)). Exposes zero arbitrary shell execution or file-mutation tools, enforces `Path.resolve()` containment inside the repository root (`REPO_DIR`), and structurally excludes `~/.bashrc.local`, `~/.gitconfig.local`, `.env`, and `~/.gemini/*.json`. |
| **`rcap1` Cryptographic Context Capsules & TOCTOU Protection (`capsule_engine.py`, `tools_unfold.py`)** | Multi-resolution context capsules (`L0` $\rightarrow$ `L3`) are sealed with **key-chained HMAC-SHA256** (`K_{i+1} = \text{HMAC-SHA256}(\text{secret}, \text{layer} \parallel \text{level} \parallel H(\text{Plaintext}_i) \parallel \text{env})`), capability-tier gates (`flash` $\le \text{L1}$, `inherit` $\le \text{L2}$, `pro` $\le \text{L3}$), environment binding (`dev`/`tst`/`pre`/`pro`), and live SHA-256 digest verification against on-disk Markdown sections to detect tampering or TOCTOU drift ([`docs/architecture/04_compaction_surface_and_promotion_engines.md`](docs/architecture/04_compaction_surface_and_promotion_engines.md)). |
| **Ephemeral Fork & Outbound Symlink Escape Prevention (`ephemeral_fork_engine.py`, `promotion_engine.py`)** | On-demand Department Bot forks enforce a hard concurrency cap (`MAX_ACTIVE_EPHEMERAL_FORKS = 16`), automatic TTL expiration (`30..3600s`), read-only container memory fallback, and strict `Path.resolve().is_relative_to(...)` validation that blocks outbound symlink escapes from consumer `.agents/rules/` directories ([`docs/architecture/05_ephemeral_forks_and_department_bots.md`](docs/architecture/05_ephemeral_forks_and_department_bots.md)). |
| **Hardened Docker Container Isolation (`Dockerfile` & `.dockerignore`)** | Runs as an unprivileged non-root user (`USER ubuntu`, UID/GID `1000:1000`), supports air-gapped read-only execution (`docker run -i --rm --read-only --network=none --cap-drop=ALL`), and enforces build-context exclusion via `.dockerignore` (`.git/`, `venv/`, `tests/`, `logs/`, `.env*`, and `*.local` secrets are never copied into the image). |

---

## Supported Versions

| Version | Target OS | Supported |
|---------|-----------|:---------:|
| `1.x` | Ubuntu 26.04 LTS ("Resolute Raccoon") & Google Antigravity 2.0 | ✅ |

---

## Reporting a Vulnerability

If you discover a security issue (for example, a script pattern that could inadvertently capture sensitive dconf keys, environment variables, or local credentials during `./backup.sh`), please report it by opening a security advisory on GitHub or contacting the repository maintainer directly before disclosing it publicly.
