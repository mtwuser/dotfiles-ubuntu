"""DotfilesMCPServer JSON-RPC 2.0 dispatcher and stdio transport loop.

Specification: docs/architecture/03_contextual_mcp_and_federation.md
"""

from __future__ import annotations

import json
import sys
import time
from datetime import UTC, datetime
from typing import Any

from dotfiles_mcp.capsule_engine import CapsuleError
from dotfiles_mcp.catalogs import MCP_TOOLS_CATALOG
from dotfiles_mcp.constants import MCP_PAYLOAD_WARN_BYTES, PROTOCOL_VERSION
from dotfiles_mcp.manifest_helpers import (
    _count_result_warnings,
    _extract_compaction_event_fields,
    _read_version,
)
from dotfiles_mcp.resources import ResourcesMixin
from dotfiles_mcp.tools_federation import FederationToolsMixin
from dotfiles_mcp.tools_surface import SurfaceToolsMixin


class DotfilesMCPServer(ResourcesMixin, FederationToolsMixin, SurfaceToolsMixin):
    """Read-only MCP server exposing dotfiles-ubuntu system & governance context."""

    def list_tools(self) -> list[dict[str, Any]]:
        return [dict(item) for item in MCP_TOOLS_CATALOG]

    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        args = arguments or {}
        if name == "get_layer_overview":
            return self._tool_get_layer_overview(args)
        if name == "audit_node_drift":
            return self._tool_audit_node_drift(args)
        if name == "read_layer_document":
            return self._tool_read_layer_document(args)
        if name == "query_governance_rules":
            return self._tool_query_governance_rules(args)
        if name == "unfold_context_capsule":
            return self._tool_unfold_context_capsule(args)
        if name == "discover_federated_mcps":
            return self._tool_discover_federated_mcps(args)
        if name == "compare_layer_patterns":
            return self._tool_compare_layer_patterns(args)
        if name == "resolve_surface_governance":
            return self._tool_resolve_surface_governance(args)
        raise ValueError(f"Unknown tool name: {name!r}")

    def handle_request(self, message: dict[str, Any]) -> dict[str, Any] | None:
        method = message.get("method", "")
        msg_id = message.get("id")
        params = message.get("params") or {}

        if msg_id is None:
            return None

        t0 = time.perf_counter()
        raw_args = params.get("arguments")
        tool_args: dict[str, Any] = raw_args if isinstance(raw_args, dict) else {}
        logged_layer = str(tool_args.get("layer") or "root")
        logged_env = str(tool_args.get("environment") or "all")

        try:
            if method == "initialize":
                result: dict[str, Any] = {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {
                        "resources": {"subscribe": False, "listChanged": False},
                        "tools": {"listChanged": False},
                        "prompts": {"listChanged": False},
                    },
                    "serverInfo": {
                        "name": "dotfiles-ubuntu-mcp",
                        "version": _read_version(),
                    },
                }
            elif method == "ping":
                result = {}
            elif method == "resources/list":
                result = {"resources": self.list_resources()}
            elif method == "resources/templates/list":
                result = {"resourceTemplates": []}
            elif method == "resources/read":
                uri = str(params.get("uri", ""))
                result = {"contents": [self.read_resource(uri)]}
            elif method == "tools/list":
                result = {"tools": self.list_tools()}
            elif method == "tools/call":
                tool_name = str(params.get("name", ""))
                result = self.call_tool(tool_name, tool_args)
            elif method == "prompts/list":
                result = {"prompts": self.list_prompts()}
            elif method == "prompts/get":
                prompt_name = str(params.get("name", ""))
                result = self.get_prompt(prompt_name, tool_args)
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}",
                    },
                }
            duration_ms = round((time.perf_counter() - t0) * 1000, 2)
            resp: dict[str, Any] = {"jsonrpc": "2.0", "id": msg_id, "result": result}
            resp_bytes = len(json.dumps(resp).encode("utf-8"))
            warning_count = _count_result_warnings(result)
            if resp_bytes > MCP_PAYLOAD_WARN_BYTES:
                warning_count += 1
                self._emit_warning(
                    "WARN",
                    "LARGE_MCP_PAYLOAD_WARNING",
                    f"MCP response for {method!r} is {resp_bytes} bytes "
                    f"(~{resp_bytes // 4} tokens > {MCP_PAYLOAD_WARN_BYTES}-byte soft cap).",
                    {"method": method, "response_bytes": resp_bytes},
                )
            target_name = str(params.get("name") or params.get("uri") or method)
            self._write_jsonl(
                "mcp_events.jsonl",
                {
                    "ts": datetime.now(UTC).isoformat(),
                    "method": method,
                    "target": target_name,
                    "layer": logged_layer,
                    "environment": logged_env,
                    "duration_ms": duration_ms,
                    "status": "ok",
                    "response_bytes": resp_bytes,
                    "estimated_tokens": resp_bytes // 4,
                    "warning_count": warning_count,
                    **_extract_compaction_event_fields(target_name, result),
                },
            )
            return resp
        except (ValueError, FileNotFoundError, KeyError) as exc:
            duration_ms = round((time.perf_counter() - t0) * 1000, 2)
            if not isinstance(exc, CapsuleError):
                self._emit_warning(
                    "WARN",
                    "SECURITY_OR_VALIDATION_ERROR",
                    str(exc),
                    {"method": method},
                )
            self._write_jsonl(
                "mcp_events.jsonl",
                {
                    "ts": datetime.now(UTC).isoformat(),
                    "method": method,
                    "target": str(params.get("name") or params.get("uri") or method),
                    "layer": logged_layer,
                    "environment": logged_env,
                    "duration_ms": duration_ms,
                    "status": "error",
                    "warning_count": 1,
                    "error": str(exc),
                },
            )
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": -32602, "message": str(exc)},
            }
        except Exception as exc:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": -32603, "message": f"Internal error: {exc}"},
            }


def run_stdio_loop(server: DotfilesMCPServer) -> None:
    """Serve JSON-RPC 2.0 over stdio (supports line-delimited and Content-Length framing)."""
    stdin_buf = sys.stdin.buffer
    stdout_buf = sys.stdout.buffer

    while True:
        first_line = stdin_buf.readline()
        if not first_line:
            break

        stripped = first_line.strip()
        if not stripped:
            continue

        use_content_length = False
        if stripped.lower().startswith(b"content-length:"):
            use_content_length = True
            length = int(stripped.split(b":", 1)[1].strip())
            while True:
                header_line = stdin_buf.readline()
                if not header_line or header_line in (b"\r\n", b"\n"):
                    break
            raw_body = stdin_buf.read(length)
        else:
            raw_body = stripped

        try:
            request = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            err_resp = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": f"Parse error: {exc}"},
            }
            payload = json.dumps(err_resp).encode("utf-8")
            stdout_buf.write(payload + b"\n")
            stdout_buf.flush()
            continue

        response = server.handle_request(request)
        if response is None:
            continue

        out_bytes = json.dumps(response).encode("utf-8")
        if use_content_length:
            header = f"Content-Length: {len(out_bytes)}\r\n\r\n".encode("ascii")
            stdout_buf.write(header + out_bytes)
        else:
            stdout_buf.write(out_bytes + b"\n")
        stdout_buf.flush()
