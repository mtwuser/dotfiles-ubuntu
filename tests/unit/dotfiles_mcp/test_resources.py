"""Unit tests for dotfiles_mcp/resources.py."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
from dotfiles_mcp.server import DotfilesMCPServer

if TYPE_CHECKING:
    from pathlib import Path


class TestResourcesMixin:
    """Verify MCP resource listing, reading, and edge-case directory handling."""

    def test_read_resource_handles_empty_nvm_and_templates_with_files(
        self,
        tmp_path: Path,
    ) -> None:
        """Default nvm_default to 'none' and ignore non-directory entries in templates/."""
        # Arrange
        (tmp_path / "system").mkdir()
        tpl_root = tmp_path / "templates"
        tpl_root.mkdir()
        (tpl_root / "README.txt").write_text("not a dir", encoding="utf-8")
        server = DotfilesMCPServer(repo_dir=tmp_path)

        # Act
        manifests_res = json.loads(server.read_resource("dotfiles://system/manifests")["text"])
        templates_res = json.loads(server.read_resource("dotfiles://governance/templates")["text"])

        # Assert
        assert manifests_res["nvm_default"] == "none"
        assert templates_res["count"] == 0

    def test_read_resource_handles_missing_templates_dir(self, tmp_path: Path) -> None:
        """Return empty templates catalog when templates/ directory does not exist."""
        # Arrange
        server = DotfilesMCPServer(repo_dir=tmp_path)

        # Act
        templates_res = json.loads(server.read_resource("dotfiles://governance/templates")["text"])

        # Assert
        assert templates_res == {"count": 0, "templates": []}

    def test_read_resource_raises_on_unknown_uri(self) -> None:
        """Raise ValueError when reading an unknown resource URI."""
        # Arrange
        server = DotfilesMCPServer()

        # Act
        with pytest.raises(ValueError, match="Unknown resource URI"):
            server.read_resource("dotfiles://unknown/resource")

        # Assert
        assert len(server.list_resources()) == 9
