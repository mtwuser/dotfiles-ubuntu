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

from dotfiles_mcp.constants import REPO_DIR, VALID_LAYER_ROLES
from dotfiles_mcp.manifest_helpers import _read_version
from dotfiles_mcp.server import DotfilesMCPServer, run_stdio_loop


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def run_self_test(server: DotfilesMCPServer) -> int:
    """Execute deterministic in-process verification of all MCP capabilities."""
    print(f"═══ dotfiles-ubuntu MCP Server Self-Test (v{_read_version()}) ═══")

    # 1. Initialize
    init_resp = server.handle_request(
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
    )
    _require(bool(init_resp and "result" in init_resp), "initialize failed")
    print("  ✅ initialize handshake ok")

    # 2. Resources list & read all 9 resources
    res_list = (
        server.handle_request({"jsonrpc": "2.0", "id": 2, "method": "resources/list", "params": {}})
        or {}
    )
    _require(
        bool(res_list and len(res_list["result"]["resources"]) == 9),
        "Expected 9 resources",
    )
    for res in res_list["result"]["resources"]:
        uri = res["uri"]
        read_resp = (
            server.handle_request(
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "resources/read",
                    "params": {"uri": uri},
                }
            )
            or {}
        )
        _require(bool(read_resp and "result" in read_resp), f"Failed reading {uri}")
        text = read_resp["result"]["contents"][0]["text"]
        _require(len(text) > 0, f"Empty resource payload for {uri}")
    print("  ✅ resources/list & resources/read verified across all 9 resources")

    # 3. Tools list & call
    tools_list = server.handle_request(
        {"jsonrpc": "2.0", "id": 4, "method": "tools/list", "params": {}}
    )
    _require(
        bool(tools_list and len(tools_list["result"]["tools"]) == 8),
        "Expected 8 tools",
    )

    overview = server.handle_request(
        {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {"name": "get_layer_overview", "arguments": {}},
        }
    )
    _require(
        bool(overview and not overview["result"]["isError"]),
        "get_layer_overview failed",
    )

    doc_read = server.handle_request(
        {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "tools/call",
            "params": {
                "name": "read_layer_document",
                "arguments": {"relative_path": "docs/README.md"},
            },
        }
    )
    _require(
        bool(doc_read and "Documentation Index" in doc_read["result"]["content"][0]["text"]),
        "read_layer_document failed",
    )

    query_res = server.handle_request(
        {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call",
            "params": {
                "name": "query_governance_rules",
                "arguments": {"query": "AAA", "scope": "global", "resolution": "L0"},
            },
        }
    )
    _require(
        bool(query_res and not query_res["result"]["isError"]),
        "query_governance_rules failed",
    )
    query_payload = json.loads(query_res["result"]["content"][0]["text"])  # type: ignore[index]
    first_capsule = query_payload["matches"][0]["capsule_token"]
    unfold_l1 = server.handle_request(
        {
            "jsonrpc": "2.0",
            "id": 71,
            "method": "tools/call",
            "params": {
                "name": "unfold_context_capsule",
                "arguments": {
                    "capsule_token": first_capsule,
                    "target_level": "L1",
                    "agent_tier": "flash",
                },
            },
        }
    )
    _require(
        bool(unfold_l1 and not unfold_l1["result"]["isError"]),
        "unfold_context_capsule (L0->L1) failed",
    )
    l1_payload = json.loads(unfold_l1["result"]["content"][0]["text"])  # type: ignore[index]
    unfold_l3 = server.handle_request(
        {
            "jsonrpc": "2.0",
            "id": 72,
            "method": "tools/call",
            "params": {
                "name": "unfold_context_capsule",
                "arguments": {
                    "capsule_token": l1_payload["next_capsule_token"],
                    "target_level": "L3",
                    "agent_tier": "inherit",
                },
            },
        }
    )
    _require(
        bool(unfold_l3 and not unfold_l3["result"]["isError"]),
        "unfold_context_capsule (L1->L3) failed",
    )

    fed_res = server.handle_request(
        {
            "jsonrpc": "2.0",
            "id": 8,
            "method": "tools/call",
            "params": {"name": "discover_federated_mcps", "arguments": {}},
        }
    )
    _require(
        bool(fed_res and not fed_res["result"]["isError"]),
        "discover_federated_mcps failed",
    )

    cmp_res = server.handle_request(
        {
            "jsonrpc": "2.0",
            "id": 9,
            "method": "tools/call",
            "params": {
                "name": "compare_layer_patterns",
                "arguments": {
                    "project_rules": ["coding.md", "custom-domain.md"],
                    "project_skills": ["sopen", "custom-skill"],
                },
            },
        }
    )
    _require(
        bool(cmp_res and not cmp_res["result"]["isError"]),
        "compare_layer_patterns failed",
    )

    surf_res = server.handle_request(
        {
            "jsonrpc": "2.0",
            "id": 91,
            "method": "tools/call",
            "params": {
                "name": "resolve_surface_governance",
                "arguments": {"target_path": "src/checkout/service.py"},
            },
        }
    )
    _require(
        bool(surf_res and not surf_res["result"]["isError"]),
        "resolve_surface_governance failed",
    )
    surf_payload = json.loads(surf_res["result"]["content"][0]["text"])  # type: ignore[index]
    _require(
        len(surf_payload.get("resolved_bindings", [])) >= 2,
        "resolve_surface_governance did not match expected baseline bindings",
    )

    # 4. Path-containment security gate verification
    traversal_attempt = server.handle_request(
        {
            "jsonrpc": "2.0",
            "id": 10,
            "method": "tools/call",
            "params": {
                "name": "read_layer_document",
                "arguments": {"relative_path": "../../../etc/passwd"},
            },
        }
    )
    _require(
        bool(traversal_attempt and "error" in traversal_attempt),
        "Path traversal must be rejected",
    )
    diag_after = server.handle_request(
        {
            "jsonrpc": "2.0",
            "id": 101,
            "method": "resources/read",
            "params": {"uri": "dotfiles://mcp/diagnostics"},
        }
    )
    _require(
        bool(diag_after and "result" in diag_after),
        "Failed reading dotfiles://mcp/diagnostics after tools",
    )
    print("  ✅ tools/list, tools/call & path-containment security gate verified")

    # 5. Prompts list & get
    prompts_list = (
        server.handle_request({"jsonrpc": "2.0", "id": 11, "method": "prompts/list", "params": {}})
        or {}
    )
    _require(
        bool(prompts_list and len(prompts_list["result"]["prompts"]) == 3),
        "Expected 3 prompts",
    )
    for pr in prompts_list["result"]["prompts"]:
        p_resp = server.handle_request(
            {
                "jsonrpc": "2.0",
                "id": 12,
                "method": "prompts/get",
                "params": {"name": pr["name"], "arguments": {"workflow_goal": "test"}},
            }
        )
        _require(bool(p_resp and "result" in p_resp), f"Failed prompt {pr['name']}")
    print("  ✅ prompts/list & prompts/get verified across all 3 prompts")
    print("🎉 MCP server self-test passed (0 errors)!")
    return 0


def main(argv: list[str] | None = None) -> int:
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
