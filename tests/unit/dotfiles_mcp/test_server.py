"""Unit tests for dotfiles_mcp/server.py."""

from __future__ import annotations

import io
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest
from dotfiles_mcp import server as mcp_server_mod
from dotfiles_mcp.server import DotfilesMCPServer

if TYPE_CHECKING:
    from pathlib import Path


class TestDotfilesMCPServer:
    """Verify JSON-RPC 2.0 request dispatching, error handling, and stdio framing loop."""

    def test_call_tool_raises_on_unknown_tool(self) -> None:
        """Raise ValueError when invoking an unknown tool name."""
        # Arrange
        server = DotfilesMCPServer()

        # Act
        with pytest.raises(ValueError, match="Unknown tool name"):
            server.call_tool("nonexistent_tool", {})

        # Assert
        assert len(server.list_tools()) == 8

    def test_handle_request_covers_notifications_ping_templates_and_errors(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Handle notifications, ping, resource templates, large payloads, and JSON-RPC errors."""
        # Arrange
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "huge.md").write_text("H" * 17000, encoding="utf-8")
        server = DotfilesMCPServer(repo_dir=tmp_path, log_dir=tmp_path / "logs")

        # Act
        notif_resp = server.handle_request(
            {"jsonrpc": "2.0", "method": "notifications/initialized"}
        )
        ping_resp = server.handle_request({"jsonrpc": "2.0", "id": 10, "method": "ping"})
        tpl_resp = server.handle_request(
            {"jsonrpc": "2.0", "id": 11, "method": "resources/templates/list"}
        )
        not_found_resp = server.handle_request(
            {"jsonrpc": "2.0", "id": 12, "method": "unknown/method"}
        )
        invalid_param_resp = server.handle_request(
            {
                "jsonrpc": "2.0",
                "id": 13,
                "method": "resources/read",
                "params": {"uri": "dotfiles://invalid"},
            }
        )
        large_resp = server.handle_request(
            {
                "jsonrpc": "2.0",
                "id": 15,
                "method": "tools/call",
                "params": {
                    "name": "read_layer_document",
                    "arguments": {"relative_path": "docs/huge.md"},
                },
            }
        )

        def _boom() -> list[dict[str, object]]:
            raise RuntimeError("unexpected failure")

        monkeypatch.setattr(server, "list_resources", _boom)
        internal_err_resp = server.handle_request(
            {"jsonrpc": "2.0", "id": 14, "method": "resources/list"}
        )

        # Assert
        assert notif_resp is None
        assert ping_resp == {"jsonrpc": "2.0", "id": 10, "result": {}}
        assert tpl_resp == {"jsonrpc": "2.0", "id": 11, "result": {"resourceTemplates": []}}
        assert not_found_resp is not None and not_found_resp["error"]["code"] == -32601
        assert invalid_param_resp is not None and invalid_param_resp["error"]["code"] == -32602
        assert large_resp is not None and "result" in large_resp
        assert internal_err_resp is not None and internal_err_resp["error"]["code"] == -32603

    def test_run_stdio_loop_processes_line_and_content_length_and_invalid_json(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Process line-delimited JSON, Content-Length framed requests, and parse errors."""
        # Arrange
        server = DotfilesMCPServer()
        line_req = b'{"jsonrpc": "2.0", "id": 1, "method": "ping"}\n'
        notif_req = b'{"jsonrpc": "2.0", "method": "notifications/initialized"}\n'
        bad_json = b"{not-valid-json}\n"
        cl_body = b'{"jsonrpc": "2.0", "id": 2, "method": "ping"}'
        cl_req = f"Content-Length: {len(cl_body)}\r\nX-Extra: 1\r\n\r\n".encode("ascii") + cl_body
        raw_input = b"\n" + line_req + notif_req + bad_json + cl_req
        stdin_buffer = io.BytesIO(raw_input)
        stdout_buffer = io.BytesIO()
        monkeypatch.setattr("sys.stdin", SimpleNamespace(buffer=stdin_buffer))
        monkeypatch.setattr("sys.stdout", SimpleNamespace(buffer=stdout_buffer))

        # Act
        mcp_server_mod.run_stdio_loop(server)

        # Assert
        output = stdout_buffer.getvalue().decode("utf-8")
        assert '"id": 1' in output
        assert '"code": -32700' in output
        assert "Content-Length:" in output

    def test_run_stdio_loop_handles_eof_during_headers(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Gracefully handle EOF encountered while reading Content-Length headers."""
        # Arrange
        server = DotfilesMCPServer()
        raw_input = b"Content-Length: 39\r\n"
        stdin_buffer = io.BytesIO(raw_input)
        stdout_buffer = io.BytesIO()
        monkeypatch.setattr("sys.stdin", SimpleNamespace(buffer=stdin_buffer))
        monkeypatch.setattr("sys.stdout", SimpleNamespace(buffer=stdout_buffer))

        # Act
        mcp_server_mod.run_stdio_loop(server)

        # Assert
        assert b'"code": -32700' in stdout_buffer.getvalue()
