"""Unit tests for dotfiles_mcp.fork_configurator (TestForkConfigurator).

Specification: docs/architecture/04_compaction_surface_and_promotion_engines.md
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
from dotfiles_mcp.fork_configurator import (
    apply_fork_to_project,
    configure_fork_manifest,
    scaffold_template_pack,
)

if TYPE_CHECKING:
    from pathlib import Path


class TestForkConfigurator:
    """Verify fork parameterization, polymorphic template scaffolding, and project projection."""

    def test_configure_fork_manifest_parameterizes_role_precedence_and_prunes_defaults(
        self,
        tmp_path: Path,
    ) -> None:
        """Parameterize system/mcp-layer.json and prune default fastapi-hexagonal bindings."""
        # Arrange
        sys_dir = tmp_path / "system"
        sys_dir.mkdir(parents=True)
        (sys_dir / "mcp-layer.json").write_text(
            json.dumps(
                {
                    "schema_version": "mcp-layer-v1",
                    "layer_id": "old-id",
                    "layer_role": "workstation",
                    "default_stack_templates": [
                        "human-core",
                        "technical-base",
                        "fastapi-hexagonal",
                        "custom-pack",
                    ],
                    "surface_bindings": [
                        "invalid-entry",
                        {
                            "binding_id": "keep-universal",
                            "rule_files": ["antigravity/.gemini/config/AGENTS.md"],
                        },
                        {
                            "binding_id": "drop-fastapi",
                            "rule_files": ["templates/fastapi-hexagonal/rules/coding.md"],
                        },
                    ],
                }
            ),
            encoding="utf-8",
        )

        # Act
        dry_manifest = configure_fork_manifest(
            tmp_path,
            layer_id="acme-dept-legal",
            layer_role="domain-policy",
            dry_run=True,
        )
        saved_manifest = configure_fork_manifest(
            tmp_path,
            layer_id="acme-dept-legal",
            layer_role="domain-policy",
            precedence=7,
            description="Statutory legal layer",
            upstream_url="https://example.com/corp.git",
            upstream_id="acme-corp",
            upstream_branch="main",
            prune_default_templates=True,
            dry_run=False,
        )
        fresh_dir = tmp_path / "fresh_repo"
        fresh_dir.mkdir()
        fresh_manifest = configure_fork_manifest(
            fresh_dir,
            layer_id="acme-squad-core",
            layer_role="squad",
        )
        non_dict_dir = tmp_path / "non_dict_repo"
        (non_dict_dir / "system").mkdir(parents=True)
        (non_dict_dir / "system/mcp-layer.json").write_text("[]", encoding="utf-8")
        configure_fork_manifest(non_dict_dir, layer_id="acme-squad-core")

        # Assert
        assert dry_manifest["precedence"] == 5
        assert json.loads((sys_dir / "mcp-layer.json").read_text(encoding="utf-8"))["layer_id"] == (
            "acme-dept-legal"
        )
        assert saved_manifest["precedence"] == 7
        assert saved_manifest["description"] == "Statutory legal layer"
        assert saved_manifest["upstream_layer"] == {
            "layer_id": "acme-corp",
            "repository": "https://example.com/corp.git",
            "branch": "main",
        }
        assert saved_manifest["default_stack_templates"] == ["custom-pack"]
        assert len(saved_manifest["surface_bindings"]) == 1
        assert saved_manifest["surface_bindings"][0]["binding_id"] == "keep-universal"
        assert fresh_manifest["precedence"] == 50

    def test_configure_fork_manifest_validates_id_role_and_precedence(
        self,
        tmp_path: Path,
    ) -> None:
        """Reject invalid layer_id, layer_role, or out-of-bounds precedence and accept 0..100."""
        # Arrange
        bad_id = "INVALID_ID"
        bad_role = "invalid-role"

        # Act
        prec_zero = configure_fork_manifest(
            tmp_path, layer_id="valid-id", precedence=0, dry_run=True
        )
        prec_hundred = configure_fork_manifest(
            tmp_path, layer_id="valid-id", precedence=100, dry_run=True
        )
        with pytest.raises(ValueError, match="must be kebab-case"):
            configure_fork_manifest(tmp_path, layer_id=bad_id)
        with pytest.raises(ValueError, match="Invalid layer_role"):
            configure_fork_manifest(tmp_path, layer_id="valid-id", layer_role=bad_role)
        with pytest.raises(ValueError, match="Invalid precedence"):
            configure_fork_manifest(tmp_path, layer_id="valid-id", precedence=-1)
        with pytest.raises(ValueError, match="Invalid precedence"):
            configure_fork_manifest(tmp_path, layer_id="valid-id", precedence=101)

        # Assert
        assert prec_zero["precedence"] == 0
        assert prec_hundred["precedence"] == 100

    def test_scaffold_template_pack_creates_files_and_registers_surface_binding(
        self,
        tmp_path: Path,
    ) -> None:
        """Scaffold tech-stack and business-stack templates and register surface bindings."""
        # Arrange
        (tmp_path / "system").mkdir(parents=True)
        (tmp_path / "system/mcp-layer.json").write_text(
            json.dumps(
                {
                    "schema_version": "mcp-layer-v1",
                    "layer_id": "acme-legal",
                    "default_stack_templates": [],
                    "surface_bindings": [],
                }
            ),
            encoding="utf-8",
        )

        # Act
        dry_res = scaffold_template_pack(
            tmp_path,
            template_name="gdpr-policy",
            kind="business-stack",
            register_binding=True,
            dry_run=True,
        )
        real_res = scaffold_template_pack(
            tmp_path,
            template_name="gdpr-policy",
            kind="business-stack",
            description="EU GDPR compliance pack",
            register_binding=True,
            scopes=["checkout"],
            planes=["presentation"],
            traits=["pii"],
            globs=["templates/**"],
            dry_run=False,
        )
        starter_res = scaffold_template_pack(
            tmp_path,
            template_name="rust-axum",
            kind="tech-stack",
            rule_filename="rust-axum.md",
            register_binding=False,
            dry_run=False,
        )
        non_dict_repo = tmp_path / "non_dict_manifest_repo"
        (non_dict_repo / "system").mkdir(parents=True)
        (non_dict_repo / "system/mcp-layer.json").write_text("[]", encoding="utf-8")
        scaffold_template_pack(non_dict_repo, template_name="demo-pack")
        no_manifest_repo = tmp_path / "no_manifest_repo"
        no_manifest_repo.mkdir()
        scaffold_template_pack(no_manifest_repo, template_name="demo-pack")

        # Assert
        assert dry_res["dry_run"] is True
        assert real_res["binding_registered"] is True
        assert (tmp_path / "templates/gdpr-policy/assets/canonical_snippet.md").is_file()
        assert (tmp_path / "templates/rust-axum/governance/WORKTASK.md").is_file()
        assert (tmp_path / "templates/rust-axum/governance/Makefile").is_file()
        assert (tmp_path / "templates/rust-axum/rules/rust-axum.md").is_file()
        assert starter_res["kind"] == "tech-stack"
        updated_manifest = json.loads(
            (tmp_path / "system/mcp-layer.json").read_text(encoding="utf-8")
        )
        assert updated_manifest["default_stack_templates"] == ["gdpr-policy", "rust-axum"]
        assert len(updated_manifest["surface_bindings"]) == 1
        assert updated_manifest["surface_bindings"][0]["mode"] == "authoritative"

        with pytest.raises(ValueError, match="must be kebab-case"):
            scaffold_template_pack(tmp_path, template_name="BAD_NAME")
        with pytest.raises(ValueError, match="Invalid template kind"):
            scaffold_template_pack(tmp_path, template_name="good-name", kind="invalid")
        with pytest.raises(ValueError, match="Invalid rule_filename"):
            scaffold_template_pack(tmp_path, template_name="good-name", rule_filename="../bad.md")
        with pytest.raises(ValueError, match="already exists"):
            scaffold_template_pack(tmp_path, template_name="rust-axum")

    def test_apply_fork_to_project_materializes_templates_layers_and_lineage(
        self,
        tmp_path: Path,
    ) -> None:
        """Materialize template pack, mounted layer rules by precedence, and LAYER_LINEAGE.md."""
        # Arrange
        fork_dir = tmp_path / "fork"
        (fork_dir / "system").mkdir(parents=True)
        (fork_dir / "system/mcp-layer.json").write_text(
            json.dumps(
                {
                    "schema_version": "mcp-layer-v1",
                    "layer_id": "acme-squad-web",
                    "layer_role": "squad",
                    "precedence": 40,
                    "default_stack_templates": ["human-core", "web-starter"],
                    "surface_bindings": [{"binding_id": "b1"}],
                }
            ),
            encoding="utf-8",
        )
        (fork_dir / "templates/human-core/rules").mkdir(parents=True)
        (fork_dir / "templates/human-core/rules/human-core.md").write_text(
            "# Global Baseline\n", encoding="utf-8"
        )
        (fork_dir / "templates/technical-base/rules").mkdir(parents=True)
        (fork_dir / "templates/technical-base/rules/technical-base.md").write_text(
            "# Technical Baseline\n", encoding="utf-8"
        )
        scaffold_template_pack(
            fork_dir,
            template_name="web-starter",
            kind="tech-stack",
            dry_run=False,
        )
        (fork_dir / "templates/web-starter/rules/subdir").mkdir(parents=True)
        (fork_dir / "templates/web-starter/assets/subdir").mkdir(parents=True)
        (fork_dir / "templates/web-starter/governance/SESSION.md").write_text(
            "# Session Log\n", encoding="utf-8"
        )
        (fork_dir / "antigravity/.gemini/config").mkdir(parents=True)
        (fork_dir / "antigravity/.gemini/config/AGENTS.md").write_text(
            "# Root Team Rules\n", encoding="utf-8"
        )

        legal_sub = fork_dir / "layers" / "dept-legal"
        (legal_sub / "system").mkdir(parents=True)
        (legal_sub / "antigravity/.gemini/config").mkdir(parents=True)
        (legal_sub / "system/mcp-layer.json").write_text(
            json.dumps(
                {
                    "schema_version": "mcp-layer-v1",
                    "layer_id": "acme-legal",
                    "layer_role": "domain-policy",
                    "precedence": 5,
                    "surface_bindings": [],
                }
            ),
            encoding="utf-8",
        )
        (legal_sub / "antigravity/.gemini/config/AGENTS.md").write_text(
            "# Legal Rules\n", encoding="utf-8"
        )
        scaffold_template_pack(
            legal_sub,
            template_name="gdpr-pack",
            kind="business-stack",
            dry_run=False,
        )
        no_manifest_sub = fork_dir / "layers" / "dept-nometa"
        no_manifest_sub.mkdir(parents=True)
        (fork_dir / "layers" / ".hidden").mkdir(parents=True)
        (fork_dir / "layers" / "file.txt").write_text("ignore", encoding="utf-8")

        project_dir = tmp_path / "my_project"
        project_dir.mkdir()

        # Act
        dry_res = apply_fork_to_project(fork_dir, project_dir, dry_run=True)
        real_res = apply_fork_to_project(fork_dir, project_dir, dry_run=False)
        second_res = apply_fork_to_project(
            fork_dir,
            project_dir,
            template_ref="dept-legal:gdpr-pack",
            layers_filter=["root", "dept-legal"],
            dry_run=False,
        )
        by_name_res = apply_fork_to_project(
            fork_dir,
            project_dir,
            template_ref="web-starter",
            layers_filter=["all"],
            dry_run=False,
        )
        bare_fork = tmp_path / "bare_fork"
        (bare_fork / "system").mkdir(parents=True)
        (bare_fork / "system/mcp-layer.json").write_text(
            json.dumps({"default_stack_templates": ["ghost-tpl"]}), encoding="utf-8"
        )
        (bare_fork / "templates/minimal-tpl").mkdir(parents=True)
        bare_res = apply_fork_to_project(bare_fork, tmp_path / "bare_proj", dry_run=False)
        minimal_res = apply_fork_to_project(
            bare_fork,
            tmp_path / "minimal_proj",
            template_ref="minimal-tpl,scientific-knowledge-branch,fastapi-hexagonal,corporate-ops-ledger",
            include_layer_defaults=False,
            dry_run=False,
        )
        inc_def_res = apply_fork_to_project(
            fork_dir,
            tmp_path / "inc_def_proj",
            template_ref="dept-legal:gdpr-pack",
            include_layer_defaults=True,
            dry_run=False,
        )
        no_sys_fork = tmp_path / "no_sys_fork"
        no_sys_fork.mkdir()
        apply_fork_to_project(no_sys_fork, tmp_path / "no_sys_proj", dry_run=False)
        apply_fork_to_project(fork_dir, fork_dir, dry_run=True)
        apply_fork_to_project(fork_dir, fork_dir, dry_run=False)

        # Assert
        assert dry_res["dry_run"] is True
        assert (
            not (project_dir / ".agents/LAYER_LINEAGE.md").exists() or real_res["dry_run"] is False
        )
        assert real_res["applied_template"] == "web-starter"
        assert real_res["participating_layers"] == ["dept-legal", "root", "dept-nometa"]
        assert (project_dir / ".agents/rules/layer-05-dept-legal.md").is_file()
        assert (project_dir / ".agents/rules/layer-40-root.md").is_file()
        assert (fork_dir / "antigravity/.gemini/config/AGENTS.md").read_text(
            encoding="utf-8"
        ) == "# Root Team Rules\n"
        assert (
            (project_dir / ".agents/rules/layer-40-root.md")
            .read_text(encoding="utf-8")
            .startswith("---\n")
        )
        assert (project_dir / ".agents/LAYER_LINEAGE.md").is_file()
        assert (project_dir / ".agents/SESSION.md").is_file()
        assert not (project_dir / "SESSION.md").exists()
        assert (project_dir / "WORKTASK.md").is_file()
        assert second_res["applied_template"] == "gdpr-pack"
        assert by_name_res["applied_template"] == "web-starter"
        assert bare_res["applied_template"] is None
        assert (
            minimal_res["applied_template"]
            == "minimal-tpl,scientific-knowledge-branch,fastapi-hexagonal,corporate-ops-ledger"
        )
        assert (tmp_path / "minimal_proj/.agents/skills/testing/SKILL.md").is_file()
        assert (tmp_path / "minimal_proj/.agents/skills/fastapi-testing/SKILL.md").is_file()
        assert (tmp_path / "minimal_proj/.agents/rules/business-base.md").is_file()
        assert (tmp_path / "minimal_proj/.agents/rules/scientific-methodology.md").is_file()
        assert (tmp_path / "minimal_proj/.agents/rules/ops-ledger-architecture.md").is_file()
        assert (tmp_path / "minimal_proj/.agents/skills/ledger-surface-audit/SKILL.md").is_file()
        assert inc_def_res["applied_template"] == "web-starter,gdpr-pack"

        with pytest.raises(ValueError, match="not found in selected layers"):
            apply_fork_to_project(fork_dir, project_dir, template_ref="nonexistent")
        with pytest.raises(ValueError, match="not found in selected layers"):
            apply_fork_to_project(fork_dir, project_dir, template_ref="root:nonexistent")
