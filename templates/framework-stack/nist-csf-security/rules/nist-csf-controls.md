---
trigger: always_on
description: "NIST Cybersecurity Framework (CSF 2.0) 6-function control mapping, security evidence ledgers, and zero-trust verification rules (nist-csf-security)."
---

# NIST CSF 2.0 Cybersecurity Control & Ledger Rules (`nist-csf-security`)

> Extends `business-base` with the external **NIST Cybersecurity Framework 2.0 (`GV`, `ID`, `PR`, `DE`, `RS`, `RC`)** control taxonomy and zero-trust verification gates.

---

## Scope & Surface Target

- **Template Pack**: `templates/framework-stack/nist-csf-security/` (`framework-stack`, `extends: business-base`).
- **Applies**: Security departments (`dept-security`), infrastructure/SOC units, and regulated workspaces governing `corporate/**`, `surfaces/**`, and `docs/**`.

---

## Normative Invariants

1. **`NIST-01` — 6-Function Control Ledger Traceability (`GV`, `ID`, `PR`, `DE`, `RS`, `RC`)**:
   - Every security control, threat mitigation, or compliance attestation MUST map `1:1` to a NIST CSF 2.0 subcategory (`GV.OC`, `ID.AM`, `PR.AA`, `DE.CM`, `RS.MA`, `RC.RP`) and cite an immutable ledger entry (`[SEC-CTRL-YYYY-NNN]`) in `corporate/ledgers/security-controls.md`.
2. **`NIST-02` — Business `AAA` Incident & Detection Playbooks**:
   - Author every security policy and incident response SOP under `corporate/policies/` and `corporate/sops/` using `# Scope & Surface Target`, `# Normative Invariants`, and `# Verification & Sign-Off Gates`.
3. **`NIST-03` — Zero-Trust Sanitization & Anti-Exfiltration Gate**:
   - Never expose credentials, internal endpoints, vulnerability PoC payloads, or unredacted audit logs in `surfaces/` or outbound promotion branches.
4. **`NIST-04` — Technological AppSec, Container & Multi-Layer MCP Capability Audit (`PR.AA` / `PR.DS` / `DE.CM`)**:
   - Bridge `business-base` and `software-engineering`: audit `src/**`, `scripts/**`, `Dockerfile`, and `system/mcp-layer.json` to verify OWASP ASVS input validation, parameterized queries (`0` shell/SQL injection), non-root container runtimes, MCP path containment (`PATH_CONTAINMENT_VIOLATION`), HMAC `DMCP` frame verification, and `strictly-read-only` ephemeral fork sandboxes (`dept-secops-auditor`).

---

## Verification & Sign-Off Gates

- [ ] Every security control in `corporate/policies/` cites both a NIST CSF 2.0 subcategory ID and a `[SEC-CTRL-YYYY-NNN]` ledger record.
- [ ] `make verify` and `make diff` report zero secret/literal leaks or unintended policy drift.
