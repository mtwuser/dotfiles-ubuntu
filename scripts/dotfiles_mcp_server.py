#!/usr/bin/env python3
"""Zero-dependency, read-only Model Context Protocol (MCP) server CLI for dotfiles-ubuntu.

Exposes the current repository/fork's declarative Ubuntu system manifests,
Google Antigravity 2.0 governance rules, Layer 2 templates, navigable docs/,
live drift audits, and federated MCP topology over JSON-RPC 2.0 (stdio).

Specification: docs/architecture/03_contextual_mcp_and_federation.md
Configuration guide: docs/reference/contextual_mcp_and_multi_service_orchestration.md
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

from dotfiles_mcp.core.constants import REPO_DIR, VALID_LAYER_ROLES
from dotfiles_mcp.core.manifest_helpers import _read_version
from dotfiles_mcp.mcp_node.server import DotfilesMCPServer, run_stdio_loop


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _rpc(
    server: DotfilesMCPServer, req_id: int, method: str, params: dict[str, object]
) -> dict[str, object]:
    return (
        server.handle_request({"jsonrpc": "2.0", "id": req_id, "method": method, "params": params})
        or {}
    )


def _call_tool_rpc(
    server: DotfilesMCPServer, req_id: int, name: str, **arguments: object
) -> dict[str, object]:
    return _rpc(server, req_id, "tools/call", {"name": name, "arguments": arguments})


def run_self_test(server: DotfilesMCPServer) -> int:
    """Execute deterministic in-process verification of all MCP capabilities."""
    print(f"═══ dotfiles-ubuntu MCP Server Self-Test (v{_read_version()}) ═══")

    # 1. Initialize
    init_resp = _rpc(server, 1, "initialize", {})
    _require("result" in init_resp, "initialize failed")
    print("  ✅ initialize handshake ok")

    # 2. Resources list & read all 9 resources
    res_list = _rpc(server, 2, "resources/list", {})
    _require(
        bool("result" in res_list and len(res_list["result"]["resources"]) == 9),  # type: ignore[index]
        "Expected 9 resources",
    )
    for res in res_list["result"]["resources"]:  # type: ignore[index]
        uri = res["uri"]
        read_resp = _rpc(server, 3, "resources/read", {"uri": uri})
        _require("result" in read_resp, f"Failed reading {uri}")
        text = read_resp["result"]["contents"][0]["text"]  # type: ignore[index]
        _require(len(text) > 0, f"Empty resource payload for {uri}")
    print("  ✅ resources/list & resources/read verified across all 9 resources")

    # 3. Tools list & call
    tools_list = _rpc(server, 4, "tools/list", {})
    _require(
        bool("result" in tools_list and len(tools_list["result"]["tools"]) == 9),  # type: ignore[index]
        "Expected 9 tools",
    )

    overview = _call_tool_rpc(server, 5, "get_layer_overview")
    _require(not overview["result"]["isError"], "get_layer_overview failed")  # type: ignore[index]

    doc_read = _call_tool_rpc(server, 6, "read_layer_document", relative_path="docs/README.md")
    _require(
        "Documentation Index" in doc_read["result"]["content"][0]["text"],  # type: ignore[index]
        "read_layer_document failed",
    )

    query_res = _call_tool_rpc(
        server, 7, "query_governance_rules", query="AAA", scope="global", resolution="L0"
    )
    _require(not query_res["result"]["isError"], "query_governance_rules failed")  # type: ignore[index]
    query_payload = json.loads(query_res["result"]["content"][0]["text"])  # type: ignore[index]
    first_capsule = query_payload["matches"][0]["capsule_token"]
    unfold_l1 = _call_tool_rpc(
        server,
        71,
        "unfold_context_capsule",
        capsule_token=first_capsule,
        target_level="L1",
        agent_tier="flash",
    )
    _require(not unfold_l1["result"]["isError"], "unfold_context_capsule (L0->L1) failed")  # type: ignore[index]
    l1_payload = json.loads(unfold_l1["result"]["content"][0]["text"])  # type: ignore[index]
    unfold_l3 = _call_tool_rpc(
        server,
        72,
        "unfold_context_capsule",
        capsule_token=l1_payload["next_capsule_token"],
        target_level="L3",
        agent_tier="inherit",
    )
    _require(not unfold_l3["result"]["isError"], "unfold_context_capsule (L1->L3) failed")  # type: ignore[index]

    fed_res = _call_tool_rpc(server, 8, "discover_federated_mcps")
    _require(not fed_res["result"]["isError"], "discover_federated_mcps failed")  # type: ignore[index]

    cmp_res = _call_tool_rpc(
        server,
        9,
        "compare_layer_patterns",
        project_rules=["coding.md", "custom-domain.md"],
        project_skills=["sopen", "custom-skill"],
    )
    _require(not cmp_res["result"]["isError"], "compare_layer_patterns failed")  # type: ignore[index]

    surf_res = _call_tool_rpc(
        server, 91, "resolve_surface_governance", target_path="src/checkout/service.py"
    )
    _require(not surf_res["result"]["isError"], "resolve_surface_governance failed")  # type: ignore[index]
    surf_payload = json.loads(surf_res["result"]["content"][0]["text"])  # type: ignore[index]
    _require(
        len(surf_payload.get("resolved_bindings", [])) >= 2,
        "resolve_surface_governance did not match expected baseline bindings",
    )
    eph_spawn = _call_tool_rpc(
        server,
        92,
        "orchestrate_ephemeral_fork",
        action="spawn",
        bot_role="dept-hexagonal-architect",
        target_globs=["src/**"],
    )
    _require(not eph_spawn["result"]["isError"], "ephemeral spawn failed")  # type: ignore[index]
    eph_fid = json.loads(eph_spawn["result"]["content"][0]["text"])["fork_id"]  # type: ignore[index]
    eph_insp = _call_tool_rpc(
        server, 93, "orchestrate_ephemeral_fork", action="inspect", fork_id=eph_fid
    )
    _require(not eph_insp["result"]["isError"], "ephemeral inspect failed")  # type: ignore[index]
    eph_eval = _call_tool_rpc(
        server,
        94,
        "orchestrate_ephemeral_fork",
        action="evaluate",
        fork_id=eph_fid,
        target_path="src/checkout/service.py",
        one_shot=False,
    )
    _require(not eph_eval["result"]["isError"], "ephemeral evaluate failed")  # type: ignore[index]
    eph_payload = json.loads(eph_eval["result"]["content"][0]["text"])  # type: ignore[index]
    eph_unfold = _call_tool_rpc(
        server,
        95,
        "unfold_context_capsule",
        capsule_token=eph_payload["ephemeral_capsule"],
        target_level="L3",
        agent_tier="inherit",
        resonance_key=eph_payload["session_resonance_key"],
    )
    _require(
        not eph_unfold["result"]["isError"],  # type: ignore[index]
        "parent unfold of ephemeral capsule failed",
    )
    eph_cat = _call_tool_rpc(server, 951, "orchestrate_ephemeral_fork", action="catalog")
    _require(not eph_cat["result"]["isError"], "ephemeral catalog failed")  # type: ignore[index]
    cat_payload = json.loads(eph_cat["result"]["content"][0]["text"])  # type: ignore[index]
    _require(
        cat_payload["permanent_ephemeral_symbiosis"]["symbiotic_state"] == "ephemeral-augmented",
        "expected ephemeral-augmented symbiotic state while lease is active",
    )
    eph_seal = _call_tool_rpc(
        server,
        952,
        "orchestrate_ephemeral_fork",
        action="seal-return",
        fork_id=eph_fid,
        digest={
            "channel_1_domain_state": "healthy",
            "channel_2_affected_surface": ["src/checkout/service.py"],
            "channel_3_invariants_and_constraints": ["1:1:1"],
            "channel_4_actionable_delta": "verified",
        },
    )
    _require(not eph_seal["result"]["isError"], "ephemeral seal-return failed")  # type: ignore[index]
    ret_cap = json.loads(eph_seal["result"]["content"][0]["text"])["capsule_token"]  # type: ignore[index]
    eph_ver = _call_tool_rpc(
        server,
        953,
        "orchestrate_ephemeral_fork",
        action="verify-return",
        fork_id=eph_fid,
        capsule_token=ret_cap,
    )
    _require(not eph_ver["result"]["isError"], "ephemeral verify-return failed")  # type: ignore[index]
    eph_reap = _call_tool_rpc(
        server, 96, "orchestrate_ephemeral_fork", action="reap", fork_id=eph_fid
    )
    _require(not eph_reap["result"]["isError"], "ephemeral reap failed")  # type: ignore[index]
    eph_shred = _call_tool_rpc(
        server,
        961,
        "orchestrate_ephemeral_fork",
        action="verify-return",
        fork_id=eph_fid,
        capsule_token=ret_cap,
    )
    _require("error" in eph_shred, "Reaped ephemeral return capsule must be crypto-shredded")
    eph_revoked = _call_tool_rpc(
        server,
        97,
        "unfold_context_capsule",
        capsule_token=eph_payload["ephemeral_capsule"],
        target_level="L2",
        agent_tier="inherit",
        resonance_key=eph_payload["session_resonance_key"],
    )
    _require("error" in eph_revoked, "Reaped ephemeral fork capsule must be rejected")

    # 4. Path-containment security gate verification
    traversal_attempt = _call_tool_rpc(
        server, 10, "read_layer_document", relative_path="../../../etc/passwd"
    )
    _require("error" in traversal_attempt, "Path traversal must be rejected")
    diag_after = _rpc(server, 101, "resources/read", {"uri": "dotfiles://mcp/diagnostics"})
    _require("result" in diag_after, "Failed reading dotfiles://mcp/diagnostics after tools")
    print("  ✅ tools/list, tools/call & path-containment security gate verified")

    # 5. Prompts list & get
    prompts_list = _rpc(server, 11, "prompts/list", {})
    _require(
        bool("result" in prompts_list and len(prompts_list["result"]["prompts"]) == 3),  # type: ignore[index]
        "Expected 3 prompts",
    )
    for pr in prompts_list["result"]["prompts"]:  # type: ignore[index]
        p_resp = _rpc(
            server, 12, "prompts/get", {"name": pr["name"], "arguments": {"workflow_goal": "test"}}
        )
        _require("result" in p_resp, f"Failed prompt {pr['name']}")
    print("  ✅ prompts/list & prompts/get verified across all 3 prompts")
    print("🎉 MCP server self-test passed (0 errors)!")
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for the stdio JSON-RPC MCP server and deterministic self-test runner."""
    parser = argparse.ArgumentParser(
        prog="dotfiles_mcp_server.py",
        description=(
            "Zero-dependency, read-only Model Context Protocol (MCP) server "
            "for dotfiles-ubuntu layer, container, and system introspection."
        ),
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"dotfiles-ubuntu-mcp v{_read_version()}",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run deterministic in-process self-test of all MCP resources, tools, and prompts.",
    )
    parser.add_argument(
        "--layer-id",
        default=None,
        help="Override layer_id from system/mcp-layer.json.",
    )
    parser.add_argument(
        "--layer-role",
        choices=VALID_LAYER_ROLES,
        default=None,
        help="Override layer_role from system/mcp-layer.json.",
    )
    parser.add_argument(
        "--log-dir",
        default=None,
        help="Directory for structured JSONL event & alert logs (default: ./logs).",
    )
    parser.add_argument(
        "--no-log",
        action="store_true",
        help="Disable writing mcp_events.jsonl and mcp_alerts.jsonl to disk.",
    )
    args = parser.parse_args(argv)
    resolved_layer_id = args.layer_id or os.environ.get("DOTFILES_LAYER_ID") or None
    resolved_layer_role = args.layer_role or os.environ.get("DOTFILES_LAYER_ROLE") or None

    if args.self_test:
        if args.no_log:
            return run_self_test(
                DotfilesMCPServer(
                    repo_dir=REPO_DIR,
                    layer_id_override=resolved_layer_id,
                    layer_role_override=resolved_layer_role,
                    log_dir=None,
                )
            )
        try:
            with tempfile.TemporaryDirectory() as tmp_log:
                test_log_dir = Path(args.log_dir or tmp_log)
                server = DotfilesMCPServer(
                    repo_dir=REPO_DIR,
                    layer_id_override=resolved_layer_id,
                    layer_role_override=resolved_layer_role,
                    log_dir=test_log_dir,
                )
                rc = run_self_test(server)
                _require((test_log_dir / "mcp_events.jsonl").is_file(), "Missing mcp_events.jsonl")
                _require((test_log_dir / "mcp_alerts.jsonl").is_file(), "Missing mcp_alerts.jsonl")
                return rc
        except OSError:
            return run_self_test(
                DotfilesMCPServer(
                    repo_dir=REPO_DIR,
                    layer_id_override=resolved_layer_id,
                    layer_role_override=resolved_layer_role,
                    log_dir=None,
                )
            )

    resolved_log_dir = (
        None
        if args.no_log
        else Path(args.log_dir or os.environ.get("DOTFILES_MCP_LOG_DIR", str(REPO_DIR / "logs")))
    )
    server = DotfilesMCPServer(
        repo_dir=REPO_DIR,
        layer_id_override=resolved_layer_id,
        layer_role_override=resolved_layer_role,
        log_dir=resolved_log_dir,
    )
    run_stdio_loop(server)
    return 0


if __name__ == "__main__":
    sys.exit(main())
