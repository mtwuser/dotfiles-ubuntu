"""Unit tests for dotfiles_mcp/manifest_helpers.py.

Specification: docs/architecture/03_contextual_mcp_and_federation.md
"""

from __future__ import annotations

import json
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
        """Return 'unversioned' when VERSION file does not exist in target repository."""
        # Arrange
        monkeypatch.setattr(manifest_helpers, "REPO_DIR", tmp_path)

        # Act
        version = manifest_helpers._read_version()

        # Assert
        assert version == "unversioned"

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

    def test_ensure_rule_file_frontmatter_normalizes_missing_and_preserves_existing(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Normalize missing trigger: always_on frontmatter and resolve oss_contrib_dir."""
        # Arrange
        plain_h1 = tmp_path / "custom-rule.md"
        plain_h1.write_text('# Custom "Dept" Rule\n\nBody.\n', encoding="utf-8")
        plain_no_h1 = tmp_path / "fallback.md"
        plain_no_h1.write_text("Body without heading.\n", encoding="utf-8")
        existing = tmp_path / "existing.md"
        existing.write_text("---\ntrigger: model_decision\n---\n# Existing\n", encoding="utf-8")
        up_repo = tmp_path / "home" / "oss-repo"
        up_repo.mkdir(parents=True)
        dev_sibling = tmp_path / "home" / "Projects" / "dev-oss-repo"
        env_contrib = tmp_path / "custom-contrib"
        (env_contrib / "system").mkdir(parents=True)
        (env_contrib / "system/mcp-layer.json").write_text("{}", encoding="utf-8")
        stale_tpl_biz = tmp_path / "biz-template.json"
        stale_tpl_biz.write_text(
            '{"schema_version": "template-pack-v1", "kind": "legacy-policy", '
            '"target_role": "domain-policy"}',
            encoding="utf-8",
        )
        stale_tpl_tech = tmp_path / "tech-template.json"
        stale_tpl_tech.write_text(
            '{"schema_version": "template-pack-v1", "kind": "legacy-starter", '
            '"target_role": "squad"}',
            encoding="utf-8",
        )

        # Act
        res_h1 = manifest_helpers._ensure_rule_file_frontmatter(plain_h1, sync_in_place=True)
        res_no_h1 = manifest_helpers._ensure_rule_file_frontmatter(plain_no_h1, sync_in_place=False)
        res_existing = manifest_helpers._ensure_rule_file_frontmatter(existing, sync_in_place=True)
        manifest_helpers._stamp_schema_rev(stale_tpl_biz, "template-pack-v1")
        manifest_helpers._stamp_schema_rev(stale_tpl_tech, "template-pack-v1")
        monkeypatch.delenv("DOTFILES_DEV_REPO_DIR", raising=False)
        fallback_contrib = manifest_helpers._resolve_oss_contrib_repo_dir(up_repo)
        (dev_sibling / "system").mkdir(parents=True)
        (dev_sibling / "system/mcp-layer.json").write_text("{}", encoding="utf-8")
        sibling_contrib = manifest_helpers._resolve_oss_contrib_repo_dir(up_repo)
        monkeypatch.setenv("DOTFILES_DEV_REPO_DIR", str(env_contrib))
        env_resolved = manifest_helpers._resolve_oss_contrib_repo_dir(up_repo)
        src_tech_tpl = tmp_path / "src_repo/templates/tech-stack/fastapi-hexagonal"
        src_tech_tpl.mkdir(parents=True)
        (tmp_path / "src_repo/templates/tech-stack/.gitkeep").write_text("", encoding="utf-8")
        (up_repo / "templates/fastapi-hexagonal").mkdir(parents=True)
        iter_tpls = manifest_helpers._iter_layer_template_dirs(tmp_path / "src_repo")
        empty_resolved = manifest_helpers._resolve_template_dir(up_repo, "tech-stack")
        dest_from_src = manifest_helpers._resolve_template_dest_dir(
            up_repo, "fastapi-hexagonal", src_tpl=src_tech_tpl
        )
        dest_existing_flat = manifest_helpers._resolve_template_dest_dir(
            up_repo, "fastapi-hexagonal"
        )
        dest_from_kind = manifest_helpers._resolve_template_dest_dir(
            up_repo, "crm-ops", kind="business-stack"
        )

        # Assert
        assert res_h1.startswith(
            "---\ntrigger: always_on\ndescription: \"Custom 'Dept' Rule\"\n---\n"
        )
        assert plain_h1.read_text(encoding="utf-8") == res_h1
        assert 'description: "Governance rules for fallback"' in res_no_h1
        assert plain_no_h1.read_text(encoding="utf-8") == "Body without heading.\n"
        assert res_existing.startswith("---\ntrigger: model_decision\n---\n")
        assert '"kind": "business-stack"' in stale_tpl_biz.read_text(encoding="utf-8")
        assert '"kind": "tech-stack"' in stale_tpl_tech.read_text(encoding="utf-8")
        assert fallback_contrib == up_repo
        assert sibling_contrib == dev_sibling.resolve()
        assert env_resolved == env_contrib.resolve()
        assert iter_tpls == [("fastapi-hexagonal", src_tech_tpl)]
        assert empty_resolved is None
        assert dest_from_src == up_repo / "templates/tech-stack/fastapi-hexagonal"
        assert dest_existing_flat == up_repo / "templates/fastapi-hexagonal"
        assert dest_from_kind == up_repo / "templates/business-stack/crm-ops"

    def test_load_manifest_dict_and_discover_templates_catalog_across_layers(
        self, tmp_path: Path
    ) -> None:
        """Load manifest dictionaries, detect OSS roots, and discover template catalogs."""
        # Arrange
        empty_names = manifest_helpers.discover_layer_template_names(tmp_path)
        empty_m = manifest_helpers._load_manifest_dict(tmp_path)
        root_tpl = tmp_path / "templates" / "web-stack"
        (root_tpl / "rules").mkdir(parents=True)
        (root_tpl / "skills" / "web-start").mkdir(parents=True)
        (root_tpl / "governance").mkdir(parents=True)
        (root_tpl / "assets").mkdir(parents=True)
        (tmp_path / "templates" / ".hidden").mkdir(parents=True)
        (tmp_path / "templates" / "not-a-dir.txt").write_text("ignore", encoding="utf-8")
        (root_tpl / "template.json").write_text(
            json.dumps(
                {
                    "schema_version": "template-pack-v1",
                    "template_id": "web-stack",
                    "kind": "tech-stack",
                    "target_role": "squad",
                    "description": "Web starter pack",
                }
            ),
            encoding="utf-8",
        )
        (root_tpl / "rules" / "coding.md").write_text("# Coding\n", encoding="utf-8")
        (root_tpl / "skills" / "web-start" / "SKILL.md").write_text(
            "---\nname: web-start\ndescription: start\n---\n", encoding="utf-8"
        )
        (root_tpl / "governance" / "WORKTASK.md").write_text("# Tasks\n", encoding="utf-8")
        (root_tpl / "assets" / "base.html").write_text("<html></html>\n", encoding="utf-8")

        sub_layer = tmp_path / "layers" / "dept-legal"
        sub_tpl = sub_layer / "templates" / "gdpr-pack"
        (sub_tpl / "rules").mkdir(parents=True)
        (sub_tpl / "template.json").write_text("[]", encoding="utf-8")
        (sub_tpl / "rules" / "privacy.md").write_text("# Privacy\n", encoding="utf-8")
        bare_tpl = sub_layer / "templates" / "no-meta-pack"
        bare_tpl.mkdir(parents=True)
        no_tpl_layer = tmp_path / "layers" / "dept-empty"
        no_tpl_layer.mkdir(parents=True)
        mounted = [
            {"name": "dept-legal", "relative_path": "layers/dept-legal"},
            {"name": "dept-empty", "relative_path": "layers/dept-empty"},
            {"name": "invalid", "relative_path": ""},
        ]

        # Act
        found_names = manifest_helpers.discover_layer_template_names(tmp_path)
        catalog = manifest_helpers.discover_templates_catalog(tmp_path, mounted)
        is_oss = manifest_helpers._is_oss_root_manifest({"layer_role": "workstation"})
        is_corp = manifest_helpers._is_oss_root_manifest(
            {"layer_id": "acme-root", "layer_role": "corporate"}
        )

        # Assert
        assert empty_names == []
        assert empty_m == {}
        assert is_oss is True
        assert is_corp is False
        assert found_names == ["web-stack"]
        assert len(catalog) == 3
        assert catalog[0]["template_name"] == "web-stack"
        assert catalog[0]["assets"] == ["templates/web-stack/assets/base.html"]
        assert catalog[1]["template_name"] == "gdpr-pack"
        assert catalog[2]["template_name"] == "no-meta-pack"
