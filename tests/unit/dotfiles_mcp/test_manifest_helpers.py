"""Unit tests for dotfiles_mcp/manifest_helpers.py."""

from __future__ import annotations

import os
import subprocess
from typing import TYPE_CHECKING

from dotfiles_mcp import manifest_helpers

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


class TestManifestHelpers:
    """Verify system, manifest, frontmatter, and telemetry helper functions."""

    def test_read_version_returns_default_when_missing(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Return '0.0.0' when VERSION file does not exist in target repository."""
        # Arrange
        monkeypatch.setattr(manifest_helpers, "REPO_DIR", tmp_path)

        # Act
        version = manifest_helpers._read_version()

        # Assert
        assert version == "0.0.0"

    def test_read_os_pretty_name_parses_os_release_or_falls_back(self, tmp_path: Path) -> None:
        """Extract PRETTY_NAME from os-release or fall back to platform system/release."""
        # Arrange
        fake_os_release = tmp_path / "os-release"
        fake_os_release.write_text(
            'NAME="Ubuntu"\nPRETTY_NAME="Ubuntu 26.04 LTS"\n', encoding="utf-8"
        )

        # Act
        pretty = manifest_helpers._read_os_pretty_name(fake_os_release)
        default_pretty = manifest_helpers._read_os_pretty_name()

        # Assert
        assert pretty == "Ubuntu 26.04 LTS"
        assert len(default_pretty) > 0

    def test_read_os_pretty_name_fallback_when_file_missing_or_without_key(
        self,
        tmp_path: Path,
    ) -> None:
        """Fall back to platform name when os-release lacks PRETTY_NAME or is missing."""
        # Arrange
        fake_os_release = tmp_path / "os-release-no-pretty"
        fake_os_release.write_text("ID=ubuntu\n", encoding="utf-8")
        missing_os_release = tmp_path / "does-not-exist"

        # Act
        pretty_no_key = manifest_helpers._read_os_pretty_name(fake_os_release)
        pretty_missing = manifest_helpers._read_os_pretty_name(missing_os_release)

        # Assert
        assert len(pretty_no_key) > 0
        assert len(pretty_missing) > 0

    def test_read_git_commit_handles_missing_git_and_container_marker(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Use DOTFILES_GIT_COMMIT fallback when git binary is absent and detect /.dockerenv."""
        # Arrange
        monkeypatch.setattr("shutil.which", lambda _name: None)
        monkeypatch.delenv("DOTFILES_GIT_COMMIT", raising=False)
        fake_marker = tmp_path / ".dockerenv"
        fake_marker.write_text("", encoding="utf-8")

        # Act
        no_git_result = manifest_helpers._read_git_commit()
        monkeypatch.setenv("DOTFILES_GIT_COMMIT", "abc1234")
        env_fallback_result = manifest_helpers._read_git_commit()
        in_container_true = manifest_helpers._is_running_in_container(fake_marker)
        in_container_false = manifest_helpers._is_running_in_container(tmp_path / "missing")

        # Assert
        assert no_git_result == "unknown"
        assert env_fallback_result == "abc1234"
        assert in_container_true is True
        assert in_container_false is False

    def test_read_git_commit_handles_nonzero_and_oserror_with_git_present(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Return short SHA on zero exit and 'unknown' on non-zero exit or OSError."""
        # Arrange
        monkeypatch.setattr("shutil.which", lambda _name: "/usr/bin/git")
        recorded_cmds: list[list[str]] = []
        ok_proc = subprocess.CompletedProcess(
            args=["git"], returncode=0, stdout="deadbeef\n", stderr=""
        )
        fail_proc = subprocess.CompletedProcess(
            args=["git"], returncode=1, stdout="", stderr="fatal"
        )
        procs = iter([ok_proc, fail_proc])

        def _fake_run(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
            recorded_cmds.append(list(cmd))
            return next(procs)

        monkeypatch.setattr("subprocess.run", _fake_run)

        # Act
        ok_result = manifest_helpers._read_git_commit()
        nonzero_result = manifest_helpers._read_git_commit()
        no_warn_count = manifest_helpers._count_result_warnings(
            {"content": [{"text": '{"status": "ok"}'}]}
        )

        def _raise_oserror(*_args: object, **_kwargs: object) -> None:
            raise OSError("failed to spawn")

        monkeypatch.setattr("subprocess.run", _raise_oserror)
        oserror_result = manifest_helpers._read_git_commit()

        # Assert
        assert ok_result == "deadbeef"
        assert recorded_cmds[0] == ["/usr/bin/git", "rev-parse", "--short", "HEAD"]
        assert nonzero_result == "unknown"
        assert no_warn_count == 0
        assert oserror_result == "unknown"

    def test_parse_skill_frontmatter_handles_missing_frontmatter_and_fields(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Fallback to parent folder name when SKILL.md lacks frontmatter or fields."""
        # Arrange
        monkeypatch.setattr(manifest_helpers, "REPO_DIR", tmp_path)
        skill_dir = tmp_path / "custom-skill"
        skill_dir.mkdir()
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("# No frontmatter here\n", encoding="utf-8")
        partial_dir = tmp_path / "partial-skill"
        partial_dir.mkdir()
        partial_md = partial_dir / "SKILL.md"
        partial_md.write_text("---\nother: value\n---\n# Body\n", encoding="utf-8")
        unclosed_dir = tmp_path / "unclosed-skill"
        unclosed_dir.mkdir()
        unclosed_md = unclosed_dir / "SKILL.md"
        unclosed_md.write_text("---\nname: unclosed\n", encoding="utf-8")

        # Act
        meta_none = manifest_helpers._parse_skill_frontmatter(skill_md)
        meta_partial = manifest_helpers._parse_skill_frontmatter(partial_md)
        meta_unclosed = manifest_helpers._parse_skill_frontmatter(unclosed_md)

        # Assert
        assert meta_none["name"] == "custom-skill"
        assert meta_none["description"] == ""
        assert meta_partial["name"] == "partial-skill"
        assert meta_partial["description"] == ""
        assert meta_unclosed["name"] == "unclosed-skill"

    def test_read_non_empty_lines_and_merge_unique_strings(self, tmp_path: Path) -> None:
        """Strip comments/blank lines and deduplicate string groups preserving order."""
        # Arrange
        sample = tmp_path / "packages.txt"
        sample.write_text("# comment\n\ncurl\ngit\n", encoding="utf-8")

        # Act
        missing_lines = manifest_helpers._read_non_empty_lines(tmp_path / "missing.txt")
        valid_lines = manifest_helpers._read_non_empty_lines(sample)
        merged = manifest_helpers._merge_unique_strings(["a", " ", "b"], ["b", "c"])

        # Assert
        assert missing_lines == []
        assert valid_lines == ["curl", "git"]
        assert merged == ["a", "b", "c"]

    def test_is_dest_template_newer_and_mounted_child_drift_sync(self, tmp_path: Path) -> None:
        """Detect newer destination templates and synchronize mounted child layers from siblings."""
        # Arrange
        src_tpl = tmp_path / "src_tpl"
        dest_tpl = tmp_path / "dest_tpl"
        newer_missing = manifest_helpers._is_dest_template_newer(src_tpl, dest_tpl)
        (src_tpl / "rules").mkdir(parents=True)
        (dest_tpl / "rules").mkdir(parents=True)
        src_rf = src_tpl / "rules/base.md"
        dest_rf = dest_tpl / "rules/base.md"
        (dest_tpl / "rules/extra.md").write_text("# extra\n", encoding="utf-8")
        src_rf.write_text("# v1\n", encoding="utf-8")
        dest_rf.write_text("# v2\n", encoding="utf-8")
        os.utime(src_rf, ns=(1_000_000_000, 1_000_000_000))
        os.utime(dest_rf, ns=(2_000_000_000, 2_000_000_000))
        newer_true = manifest_helpers._is_dest_template_newer(src_tpl, dest_tpl)
        os.utime(dest_rf, ns=(1_000_000_000, 1_000_000_000))
        newer_equal = manifest_helpers._is_dest_template_newer(src_tpl, dest_tpl)

        parent_ws = tmp_path / "corp-root"
        (parent_ws / "system").mkdir(parents=True)
        (parent_ws / "system/mcp-layer.json").write_text(
            '{"layer_id": "corp-root"}', encoding="utf-8"
        )
        mounted_child = parent_ws / "layers/dept-alpha"
        (mounted_child / "system").mkdir(parents=True)
        (mounted_child / "system/mcp-layer.json").write_text(
            '{"layer_id": "dept-alpha"}', encoding="utf-8"
        )
        (mounted_child / "README.md").write_text("# Old\n", encoding="utf-8")

        org_child = tmp_path / "corp-root-org/dept-alpha"
        (org_child / "system").mkdir(parents=True)
        (org_child / "system/mcp-layer.json").write_text(
            '{"layer_id": "dept-alpha"}', encoding="utf-8"
        )
        (org_child / "README.md").write_text("# New\n", encoding="utf-8")
        (org_child / "docs").mkdir(parents=True)
        (org_child / "docs/guide.md").write_text("# Guide\n", encoding="utf-8")
        (org_child / "docs/sub").mkdir(parents=True)
        (org_child / "templates/dept-alpha/rules").mkdir(parents=True)
        (org_child / "templates/dept-alpha/rules/alpha.md").write_text(
            "# Alpha\n", encoding="utf-8"
        )
        mounted_entries: list[object] = [
            "invalid",
            {"name": ""},
            {"name": "dept-missing"},
            {"name": "dept-alpha"},
        ]

        # Act
        missing_resolved = manifest_helpers._resolve_mounted_child_dir(parent_ws, "dept-missing")
        drifts_before = manifest_helpers._inspect_mounted_children_drifts(
            parent_ws, mounted_entries
        )
        dry_synced = manifest_helpers._sync_mounted_children_into_parent(
            parent_ws, mounted_entries, dry_run=True
        )
        readme_after_dry = (mounted_child / "README.md").read_text(encoding="utf-8")
        live_synced = manifest_helpers._sync_mounted_children_into_parent(
            parent_ws, mounted_entries, dry_run=False
        )
        drifts_after = manifest_helpers._inspect_mounted_children_drifts(parent_ws, mounted_entries)

        # Assert
        assert newer_missing is False
        assert newer_true is True
        assert newer_equal is False
        assert missing_resolved is None
        assert len(drifts_before) == 1
        assert "README.md" in drifts_before[0]["drift_files"]
        assert "docs/guide.md" in drifts_before[0]["drift_files"]
        assert dry_synced == ["dept-alpha"]
        assert readme_after_dry == "# Old\n"
        assert live_synced == ["dept-alpha"]
        assert (mounted_child / "README.md").read_text(encoding="utf-8") == "# New\n"
        assert (mounted_child / "docs/guide.md").is_file()
        assert drifts_after == []
