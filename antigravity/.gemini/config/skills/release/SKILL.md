---
name: release
description: "Cut and publish an explicit SemVer release (vX.Y.Z) — promotes [Unreleased] in CHANGELOG.md, syncs VERSION/pyproject.toml/README.md, runs agnosticism & verification gates, and delivers the release commit + tag + push block."
---

# Release Workflow — `/release`

Execute this workflow **ONLY** when the user explicitly requests cutting or publishing a new versioned release (`vX.Y.Z`). During normal development (`/continue`, `/sclose`), changes remain under `## [Unreleased]` in `CHANGELOG.md` and `VERSION` is never bumped prematurely.

---

## 1. Layer Authority, Agnosticism & Zero-Residue Scan

1. **Layer Owner vs. Consumer Authority Gate (`check-authority --op release`)**:
   - When releasing a governance layer repository (`system/mcp-layer.json`), verify caller authority via `./scripts/layer-config.sh check-authority <repo-dir> --op release`.
   - If the caller is a downstream consumer (or their `git config user.email` does not match `layer_authority.authorized_emails`), **STOP**: a consumer team/squad must **never** publish upstream department/corporate rules directly. Instead, run `./scripts/layer-config.sh promote-from-project <your-workspace> --source <file> --to-layer <upstream-layer> --prepare-pr` to open a Pull Request from the originating layer's context and coordinate with `layer_authority.escalation_contact`.
2. **Open-Source Agnosticism & Zero-Literal Exclusion Gate (Public / Upstream Repos)**:
   - Verify that zero private downstream organization names, internal project codenames, or private backlog ticket IDs appear anywhere in `CHANGELOG.md`, `README.md`, `docs/`, `templates/`, `scripts/`, or `tests/`.
   - **Anti-Streisand Invariant**: Never hardcode forbidden private names (not even hex- or base64-encoded) inside the repository's own tests or scripts; rely on dynamic local discovery (`Path.home() / "Projects"`) or structural regex patterns.
3. **Sterile Working Tree & Residue Scan**:
   - Check `git status --short` and remove any temporary scratch files, `.svg` renders, or untracked artifacts.

---

## 2. Target SemVer Resolution & Multi-File Version Sync

1. **Determine Target Version (`X.Y.Z`)**:
   - Read the current published version from `VERSION` (and `git tag --list` / `origin`).
   - Apply the requested increment (`patch`, `minor`, `major`, or explicit `X.Y.Z` based on `## [Unreleased]` scope: `### Added` $\rightarrow$ `minor`, `### Fixed` only $\rightarrow$ `patch`).
2. **Promote `## [Unreleased]` in `CHANGELOG.md`**:
   - Replace `## [Unreleased]` with `## [X.Y.Z] - YYYY-MM-DD` (using today's ISO date).
   - Ensure all entries under the new version heading are clean, accurate, and free of internal ticket references.
3. **Synchronize Version Markers in Lockstep**:
   - Update `VERSION` to `X.Y.Z`.
   - If `pyproject.toml` exists, update `version = "X.Y.Z"`.
   - If `README.md` contains version badges (`version-X.Y.Z-blue.svg`) or inline version references (`VERSION` (`X.Y.Z`)), update them to `X.Y.Z`.

---

## 3. Deterministic Verification Gate

1. Run the repository's full verification suite (`make verify` or `./scripts/verify-repo.sh`).
2. If any linter, type-check, unit/E2E test, coverage gate, or parity check fails, **STOP** and fix all issues before delivering the release commit block.

---

## 4. Deliver Explicit Release Commit, Tag & Push Block

Never execute mutating git commands automatically. Present the ready-to-run release block to the user:

```bash
### Release vX.Y.Z (<Repo Name>)
cd <REPO_PATH>
git add -A
git commit -m "chore(release): publish vX.Y.Z"
git tag -a vX.Y.Z -m "Release vX.Y.Z"
git push origin <branch> --follow-tags
```
