---
name: nist-csf-audit
description: "Audit workspace security policies, control ledgers, and outward surfaces against NIST CSF 2.0 (GV, ID, PR, DE, RS, RC) invariants"
---
# Skill: NIST CSF 2.0 Control & Surface Audit (`nist-csf-audit`)

> Verifies `1:1:1` alignment between `corporate/ledgers/security-controls.md`, `corporate/policies/`, and outward `surfaces/` against NIST CSF 2.0.

---

## Audit Steps

1. **Control Coverage Check**: Verify every active policy in `corporate/policies/` maps to a valid NIST CSF 2.0 function (`GV`, `ID`, `PR`, `DE`, `RS`, `RC`) and cites `[SEC-CTRL-YYYY-NNN]`.
2. **Evidence Verification**: Confirm each `[SEC-CTRL-YYYY-NNN]` record specifies an automated check command or dated sign-off artifact.
3. **Zero-Trust Surface Sweep**: Scan `surfaces/**` and `.agents/proposals/**` to ensure zero internal IPs, secrets, or restricted threat-model details are exposed.
4. **Technological Application & MCP Capability Audit (`PR.AA`, `PR.DS`, `DE.CM`)**: Audit `src/**`, `scripts/**`, `Dockerfile`, and `system/mcp-layer.json` (`ephemeral_fork_policy`) to verify OWASP ASVS boundary validation, non-root containers, MCP path containment (`PATH_CONTAINMENT_VIOLATION`), `citation_receipt` verification, and `strictly-read-only` subagent execution.
