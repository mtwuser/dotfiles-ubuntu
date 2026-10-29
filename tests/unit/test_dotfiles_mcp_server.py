"""Unit tests for scripts/dotfiles_mcp_server.py CLI entrypoint."""

from __future__ import annotations

import tempfile
from typing import TYPE_CHECKING

import dotfiles_mcp_server
import pytest

if TYPE_CHECKING:
    from pathlib import Path


class TestDotfilesMCPServerCLI:
    """Verify CLI flag parsing, in-process self-test runner, and stdio startup."""

    def test_require_raises_runtime_error_when_false(self) -> None:
        """Raise RuntimeError when _require assertion condition is False."""
        # Arrange
        msg = "expected failure"

        # Act
        with pytest.raises(RuntimeError, match="expected failure"):
            dotfiles_mcp_server._require(False, msg)

        # Assert
        dotfiles_mcp_server._require(True, "ok")

    def test_main_runs_self_test_and_stdio_loop(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Run --self-test with temporary/custom/disabled logs and launch run_stdio_loop."""
        # Arrange
        called_stdio: list[bool] = []
        monkeypatch.setattr(
            dotfiles_mcp_server,
            "run_stdio_loop",
            lambda _srv: called_stdio.append(True),
        )

        def _raise_ro_oserror(*_args: object, **_kwargs: object) -> object:
            raise OSError("Read-only file system")

        # Act
        rc_self_test = dotfiles_mcp_server.main(["--self-test"])
        rc_self_test_no_log = dotfiles_mcp_server.main(["--self-test", "--no-log"])
        monkeypatch.setattr(tempfile, "TemporaryDirectory", _raise_ro_oserror)
        rc_self_test_ro = dotfiles_mcp_server.main(["--self-test"])
        rc_stdio = dotfiles_mcp_server.main(
            ["--layer-id", "test-layer", "--layer-role", "team", "--no-log"]
        )
        rc_stdio_log = dotfiles_mcp_server.main(["--log-dir", str(tmp_path / "custom_logs")])

        # Assert
        assert rc_self_test == 0
        assert rc_self_test_no_log == 0
        assert rc_self_test_ro == 0
        assert rc_stdio == 0
        assert rc_stdio_log == 0
        assert called_stdio == [True, True]
