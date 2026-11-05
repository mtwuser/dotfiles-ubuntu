# Framework-Stack Template: NIST CSF 2.0 Cybersecurity Governance (`nist-csf-security`)

Ready-to-apply **Framework-Stack Template Pack** (`kind: "framework-stack"`, `extends: "business-base"`, `upstream_framework: "nist-csf-2.0"`) for CISO/security departments (`dept-security`), SOC squads, and compliance-critical enterprise or public-administration workspaces.

> **Why `nist-csf-security` Lives Under `framework-stack` (`extends: "business-base"`)**:
> - Just as `fastapi-hexagonal`, `angular-web`, and `django-backend` bind software engineering workspaces to concrete technical frameworks, `nist-csf-security` binds security and compliance workspaces to the external **NIST Cybersecurity Framework (CSF 2.0)** standard (`GV`, `ID`, `PR`, `DE`, `RS`, `RC`).
> - Inherits `business-base` normative ledger traceability (`[SEC-CTRL-YYYY-NNN]`) and the Three-Part Business `AAA` verification structure.

---

## 1. Quick Setup (Deterministic CLI)

Apply the `nist-csf-security` pack and inherited `business-base` rules with a single CLI command:

```bash
# Materialize business-base + nist-csf-security into a security or compliance workspace
./scripts/layer-config.sh apply-project /path/to/dept-security --template nist-csf-security --layers all
```

---

## 2. Template Pack Contents

### 2.1. Rules (`.agents/rules/`)

Projected rules map security controls to the six NIST CSF 2.0 functions (`GV`, `ID`, `PR`, `DE`, `RS`, `RC`):

| File | Scope (`nist-csf-security` Delta over `business-base`) |
|------|--------------------------------------------------------|
| `rules/nist-csf-controls.md` | NIST CSF 2.0 6-function control mapping (`GV`, `ID`, `PR`, `DE`, `RS`, `RC`), immutable control evidence ledgers, and zero-trust disclosure firewalls |

### 2.2. Skills (`.agents/skills/`)

Projected skills audit NIST CSF 2.0 control evidence ledgers and outbound disclosure surfaces:

| File | Skill Name & Purpose |
|------|----------------------|
| `skills/nist-csf-audit/SKILL.md` | `nist-csf-audit` — Step-by-step NIST CSF 2.0 control coverage and surface sanitization audit |
