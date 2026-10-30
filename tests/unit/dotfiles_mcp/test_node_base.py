"""Unit tests for dotfiles_mcp/node_base.py."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
from dotfiles_mcp.server import DotfilesMCPServer

if TYPE_CHECKING:
    from pathlib import Path


class TestMCPNodeBase:
    """Verify manifest loading, path-containment security gates, warnings, and prompts."""

    def test_load_layer_manifest_applies_overrides_and_handles_missing_file(
        self,
        tmp_path: Path,
    ) -> None:
        """Apply CLI layer_id and layer_role overrides when loading root manifest."""
        # Arrange
        server = DotfilesMCPServer(
            repo_dir=tmp_path,
            layer_id_override="acme-corp",
            layer_role_override="corporate",
        )

        # Act
        manifest = server._load_layer_manifest()

        # Assert
        assert manifest["layer_id"] == "acme-corp"
        assert manifest["layer_role"] == "corporate"

    def test_load_layer_manifest_ignores_non_dict_json_and_rejects_bad_schema(
        self,
        tmp_path: Path,
    ) -> None:
        """Ignore non-dict JSON payloads and reject unsupported schema_version values."""
        # Arrange
        sys_dir = tmp_path / "system"
        sys_dir.mkdir()
        (sys_dir / "mcp-layer.json").write_text("[1, 2, 3]", encoding="utf-8")
        server = DotfilesMCPServer(repo_dir=tmp_path)

        bad_dir = tmp_path / "bad_schema"
        (bad_dir / "system").mkdir(parents=True)
        (bad_dir / "system/mcp-layer.json").write_text(
            json.dumps({"schema_version": "1.0"}), encoding="utf-8"
        )

        # Act
        manifest = server._load_layer_manifest()
        with pytest.raises(ValueError, match="Unsupported"):
            DotfilesMCPServer(repo_dir=bad_dir)._load_layer_manifest()

        # Assert
        assert manifest["layer_id"] == "dotfiles-ubuntu-default"

    def test_resolve_safe_path_blocks_invalid_paths_and_missing_files(
        self,
        tmp_path: Path,
    ) -> None:
        """Block path traversal, symlink escapes, non-whitelisted files, and missing docs."""
        # Arrange
        server = DotfilesMCPServer(repo_dir=tmp_path)
        (tmp_path / "bootstrap.sh").write_text("#!/bin/sh\n", encoding="utf-8")
        outside_file = tmp_path.parent / "outside_secret.txt"
        outside_file.write_text("secret", encoding="utf-8")
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        escape_link = docs_dir / "escape.md"
        escape_link.symlink_to(outside_file)

        # Act
        with pytest.raises(ValueError, match="Invalid or forbidden"):
            server._resolve_safe_path("")
        with pytest.raises(ValueError, match="Invalid or forbidden"):
            server._resolve_safe_path("../outside.txt")
        with pytest.raises(ValueError, match="Path escapes repository root"):
            server._resolve_safe_path("docs/escape.md")
        with pytest.raises(ValueError, match="Access denied"):
            server._resolve_safe_path("bootstrap.sh")
        with pytest.raises(FileNotFoundError, match="Document not found"):
            server._resolve_safe_path("docs/missing.md")

        # Assert
        outside_file.unlink()
        assert escape_link.is_symlink()

    def test_list_prompts_and_get_prompt_rejects_unknown_prompt(self) -> None:
        """Return all 3 prompt templates and raise ValueError on unknown prompt names."""
        # Arrange
        server = DotfilesMCPServer()

        # Act
        prompts = server.list_prompts()
        orient = server.get_prompt("orient-on-layer", {"task_description": "test"})
        audit = server.get_prompt("audit-container-or-node", {"target_service": "api"})
        orch = server.get_prompt("orchestrate-federated-mcps", {"workflow_goal": "deploy"})
        with pytest.raises(ValueError, match="Unknown prompt name"):
            server.get_prompt("nonexistent_prompt", {})

        # Assert
        assert len(prompts) == 3
        assert "4-Channel Executive Digest" in orient["messages"][0]["content"]["text"]
        assert "audit_node_drift" in audit["messages"][0]["content"]["text"]
        assert "discover_federated_mcps" in orch["messages"][0]["content"]["text"]

    def test_evaluate_layer_warnings_and_log_rotation_boundary_cutpoints(
        self,
        tmp_path: Path,
    ) -> None:
        """Verify exact cut-points for budget alerts, log rotation, and memory fork reaping."""
        # Arrange
        from dotfiles_mcp import constants

        (tmp_path / "system").mkdir(parents=True)
        (tmp_path / "templates" / "existing-pack").mkdir(parents=True)
        (tmp_path / "system/mcp-layer.json").write_text(
            json.dumps(
                {
                    "schema_version": "1.2",
                    "layer_id": "acme-team",
                    "default_stack_templates": ["existing-pack", "missing-pack"],
                }
            ),
            encoding="utf-8",
        )
        log_dir = tmp_path / "logs"
        log_dir.mkdir()
        log_file = log_dir / "test.jsonl"
        log_file.write_text("X" * (constants.MAX_LOG_FILE_BYTES - 1), encoding="utf-8")
        server = DotfilesMCPServer(repo_dir=tmp_path, log_dir=log_dir)
        server._ephemeral_memory_store = {
            "f-exact": {"expires_at_epoch": 200.0},
            "f-future": {"expires_at_epoch": 201.0},
        }

        # Act
        reaped = server._reap_expired_memory_forks(now_epoch=200.0)
        server._write_jsonl("test.jsonl", {"step": 1})
        rotated_after_below_cap = (log_dir / "test.jsonl.1").is_file()
        log_file.write_text("X" * constants.MAX_LOG_FILE_BYTES, encoding="utf-8")
        server._write_jsonl("test.jsonl", {"step": 2})
        rotated_at_exact_cap = (log_dir / "test.jsonl.1").is_file()
        w_15999 = server._evaluate_layer_warnings(tmp_path, 15999)
        w_16000 = server._evaluate_layer_warnings(tmp_path, 16000)
        w_18000 = server._evaluate_layer_warnings(tmp_path, 18000)
        w_18001 = server._evaluate_layer_warnings(tmp_path, 18001)

        # Assert
        assert reaped == ["f-exact"]
        assert list(server._ephemeral_memory_store) == ["f-future"]
        assert rotated_after_below_cap is False
        assert rotated_at_exact_cap is True
        assert [w["code"] for w in w_15999] == ["TEMPLATE_PACK_MISSING"]
        assert [w["code"] for w in w_16000] == [
            "TOKEN_BUDGET_NEAR_LIMIT",
            "TEMPLATE_PACK_MISSING",
        ]
        assert [w["code"] for w in w_18000] == [
            "TOKEN_BUDGET_NEAR_LIMIT",
            "TEMPLATE_PACK_MISSING",
        ]
        assert [w["code"] for w in w_18001] == [
            "TOKEN_BUDGET_EXCEEDED",
            "TEMPLATE_PACK_MISSING",
        ]
