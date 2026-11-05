"""Implementation tests for MCP server and lifecycle hooks over stdio.

Specification: docs/architecture/03_contextual_mcp_and_federation.md
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parents[2]
MCP_SERVER = REPO_DIR / "scripts" / "dotfiles_mcp_server.py"
HOOKS_DIR = REPO_DIR / "antigravity" / ".gemini" / "config" / "scripts"


class TestMCPAndHooksStdio:
    """Implementation tests for MCP server and lifecycle hooks over stdio."""

    def test_mcp_server_stdio_line_delimited_and_content_length_roundtrip(
        self,
        tmp_path: Path,
    ) -> None:
        """Verify line-delimited and Content-Length JSON-RPC framing over stdio."""
        # Arrange
        log_dir = tmp_path / "mcp_logs"
        line_req = (
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {"name": "get_layer_overview", "arguments": {}},
                }
            )
            + "\n"
            + json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {"name": "query_governance_rules", "arguments": {"query": "e"}},
                }
            )
            + "\n"
        )
        body = json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "discover_federated_mcps",
                    "arguments": {"filter_role": "documentation"},
                },
            }
        ).encode("utf-8")
        framed_req = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii") + body

        # Act
        proc_line = subprocess.run(
            [sys.executable, str(MCP_SERVER), "--log-dir", str(log_dir)],
            input=line_req.encode("utf-8"),
            capture_output=True,
            timeout=10,
            check=True,
        )
        proc_framed = subprocess.run(
            [sys.executable, str(MCP_SERVER), "--log-dir", str(log_dir)],
            input=framed_req,
            capture_output=True,
            timeout=10,
            check=True,
        )

        # Assert
        resp_line = json.loads(proc_line.stdout.decode("utf-8").strip().splitlines()[0])
        overview = json.loads(resp_line["result"]["content"][0]["text"])
        assert "channel_1_node_and_system_state" in overview
        assert proc_framed.stdout.startswith(b"Content-Length:")
        _, payload = proc_framed.stdout.split(b"\r\n\r\n", 1)
        resp_framed = json.loads(payload.decode("utf-8"))
        fed = json.loads(resp_framed["result"]["content"][0]["text"])
        assert fed["federated_mcp_count"] == 1
        assert (log_dir / "mcp_events.jsonl").is_file()
        assert (log_dir / "mcp_alerts.jsonl").is_file()

    def test_pre_tool_guard_subprocess_denies_git_push_and_allows_pytest(self) -> None:
        """Verify pre_tool_guard.py subprocess denies git push and allows pytest."""
        # Arrange
        guard_script = HOOKS_DIR / "pre_tool_guard.py"
        deny_payload = json.dumps(
            {
                "toolCall": {
                    "name": "run_command",
                    "args": {"CommandLine": "git push origin master"},
                }
            }
        )
        allow_payload = json.dumps(
            {
                "toolCall": {
                    "name": "run_command",
                    "args": {"CommandLine": "pytest -q"},
                }
            }
        )

        # Act
        deny_proc = subprocess.run(
            [sys.executable, str(guard_script)],
            input=deny_payload,
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
        allow_proc = subprocess.run(
            [sys.executable, str(guard_script)],
            input=allow_payload,
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )

        # Assert
        assert json.loads(deny_proc.stdout)["decision"] == "deny"
        assert json.loads(allow_proc.stdout)["decision"] == "allow"

    def test_spanish_quartet_libraries_compaction_drift_and_q1_q4_radar(
        self, tmp_path: Path
    ) -> None:
        """Validate gov-es, geo-es, sci-medicine, and sci-physics compaction and Q1..Q4 radar."""
        # Arrange
        sys.path.insert(0, str(REPO_DIR / "scripts"))
        from dotfiles_mcp.capsules.tools_compaction import verify_epistemic_context_claims
        from dotfiles_mcp.mcp_node.server import DotfilesMCPServer

        ws = tmp_path / "org-acme"
        (ws / "system").mkdir(parents=True)
        (ws / "antigravity/.gemini/config").mkdir(parents=True)
        (ws / "antigravity/.gemini/config/AGENTS.md").write_text("# Root\n", encoding="utf-8")
        libs = {
            "geo-es": (
                1,
                "01_territorial_thresholds.md",
                "## 1.1. ISO 3166-2:ES Thermal Alert Zones\n"
                "[E3] AEMET red alert threshold is 40.0 C (313.15 K) across southern basins.\n\n"
                "| Zone | ISO Code | Red Alert Cut-Point | Notes |\n"
                "| :--- | :--- | :--- | :--- |\n"
                "| Guadalquivir | ES-AN | 40.0 C (313.15 K) | Continuous monitoring |\n"
                + ("Detailed cartographic and meteorological station series.\n" * 6),
            ),
            "gov-es": (
                2,
                "01_sns_statutes.md",
                "## 1.1. Ley 14/1986 General de Sanidad & Ley 33/2011 Salud Publica\n"
                "[E3] Universal thermal emergency triage coverage is mandatory.\n\n"
                + ("Statutory administrative procedure and inter-territorial coordination.\n" * 6)
                + "\n## 1.2. Disposicion Transitoria 1986 Paper Ledger\n"
                "[E1] Transitional paper-stamp registry clause from 1986.\n",
            ),
            "sci-medicine": (
                5,
                "01_heatstroke_triage.md",
                "## 1.1. Hyperthermia Clinical Triage Protocol\n"
                "[E2] Initiate rapid thermal cooling when core temperature exceeds 40.0 C.\n\n"
                + ("Clinical pathophysiology, fluid resuscitation, and monitoring steps.\n" * 6),
            ),
            "sci-physics": (
                5,
                "01_radiative_heat_balance.md",
                "## 1.1. Radiative and Convective Heat Transfer\n"
                "[E3] Net thermal radiative heat flux exceeds 500 W/m^2 above 313.15 K.\n\n"
                + ("Thermodynamic derivation and boundary layer convection equations.\n" * 6),
            ),
        }
        mounted_entries = []
        for lid, (prec, fname, content) in libs.items():
            ldir = ws / "layers" / lid
            (ldir / "system").mkdir(parents=True)
            (ldir / "docs/architecture").mkdir(parents=True)
            (ldir / "docs/architecture" / fname).write_text(content, encoding="utf-8")
            (ldir / "system/mcp-layer.json").write_text(
                json.dumps({"schema_version": "mcp-layer-v1", "layer_id": lid, "precedence": prec}),
                encoding="utf-8",
            )
            mounted_entries.append(
                {
                    "name": lid,
                    "relative_path": f"layers/{lid}",
                    "remote_url": f"https://example.org/{lid}.git",
                }
            )
        (ws / "system/mcp-layer.json").write_text(
            json.dumps(
                {
                    "schema_version": "mcp-layer-v1",
                    "layer_id": "org-acme",
                    "layer_role": "corporate",
                    "mounted_layers": mounted_entries,
                }
            ),
            encoding="utf-8",
        )
        server = DotfilesMCPServer(repo_dir=ws)

        # Act
        ov_res = server._tool_get_layer_overview({})
        ov_payload = json.loads(ov_res["content"][0]["text"])
        q_res = server._tool_query_governance_rules({"query": "thermal", "resolution": "L1"})
        q_payload = json.loads(q_res["content"][0]["text"])
        gov_rec = "gov-es::docs/architecture/01_sns_statutes.md#1-1-ley-14-1986:E3@a1b2c3d4:E3"
        med_rec = "sci-medicine::docs/architecture/01_heatstroke_triage.md#1-1-triage@11223344:E2"
        phy_rec = "sci-physics::docs/architecture/01_radiative_heat_balance.md#1-1-flux@55667788:E3"
        obs_rec = "gov-es::docs/architecture/01_sns_statutes.md#1-2-disposicion-1986@9900aabb:E1"
        claims: list[dict[str, object]] = [
            {"claim_id": "c1", "citation_receipt": gov_rec, "official_digest": "a1b2c3d4"},
            {"claim_id": "c2", "citation_receipt": gov_rec, "official_digest": "a1b2c3d4"},
            {"claim_id": "c3", "citation_receipt": gov_rec, "official_digest": "a1b2c3d4"},
            {
                "claim_id": "c4",
                "citation_receipt": med_rec,
                "official_digest": "deadbeef",
                "age_days": 90,
            },
            {
                "claim_id": "c5",
                "citation_receipt": phy_rec,
                "official_digest": "55667788",
                "age_days": 15,
            },
            {
                "claim_id": "c6",
                "citation_receipt": obs_rec,
                "age_days": 365,
                "count_citation": False,
            },
        ]
        ver_report = verify_epistemic_context_claims(claims, ws)
        radar = ver_report["citation_lifecycle_radar"]

        # Assert
        disc_libs = ov_payload["channel_4_navigable_docs_and_federated_mcps"]["deep_context_index"][
            "knowledge_libraries"
        ]
        assert len(disc_libs) == 4
        assert all(item["resolution_mode"] == "local-mcp-clone" for item in disc_libs)
        trunk_map = {item["layer_id"]: item["canonical_trunk"] for item in disc_libs}
        assert trunk_map["sci-medicine"] == "health" and trunk_map["sci-physics"] == "nature"
        assert q_payload["token_compaction_metrics"]["savings_pct"] > 0
        assert all("::" in m["citation_receipt"] for m in q_payload["matches"])
        assert ver_report["verified"] is False
        assert ver_report["error_code"] == "CITATION_DRIFT_DETECTED"
        assert (ws / ".agents/telemetry/citation_stats.json").is_file()
        assert radar["epistemic_override_allowed"] is False
        assert radar["quadrant_counts"] == {
            "Q1_HOT_CORE": 1,
            "Q2_HIGH_FRICTION": 1,
            "Q3_EMERGING_NICHE": 1,
            "Q4_NORMATIVE_OBSOLESCENCE": 1,
        }
        assert radar["obsolescence_candidates"][0]["section_key"].startswith("gov-es::")
