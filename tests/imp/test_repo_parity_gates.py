"""Implementation tests for repository parity gates, 1:1:1 traceability, and hook-to-doc sync.

Specification: docs/architecture/02_antigravity_governance_and_hooks.md
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parents[2]


class TestRepoParityGates:
    """Repository parity gates for 1:1:1 traceability, hook-to-doc sync, and AST hygiene."""

    def test_all_test_init_files_are_strictly_zero_bytes(self) -> None:
        """Verify all package and test __init__.py markers remain strictly 0 bytes."""
        # Arrange
        init_files = sorted([
            *list((REPO_DIR / "scripts/dotfiles_mcp").rglob("__init__.py")),
            *list((REPO_DIR / "tests").rglob("__init__.py")),
        ])  # fmt: skip

        # Act
        non_empty = [str(p.relative_to(REPO_DIR)) for p in init_files if p.stat().st_size != 0]

        # Assert
        assert (len(init_files), non_empty) == (14, [])

    def test_one_to_one_unit_test_mapping_and_file_size_discipline(self) -> None:
        """Verify 1:1:1 source-to-test-to-spec mapping and < 465-line file size discipline."""
        # Arrange
        declarative_only = {"__init__.py", "constants.py", "catalogs.py"}
        mcp_root = REPO_DIR / "scripts" / "dotfiles_mcp"
        pkg_modules = sorted(
            p.relative_to(mcp_root)
            for p in mcp_root.rglob("*.py")
            if p.name not in declarative_only
        )
        all_sized_files = sorted([
            REPO_DIR / "README.md", *list(REPO_DIR.glob("*.sh")),
            *list((REPO_DIR / "scripts").glob("*.sh")),
            *list((REPO_DIR / "antigravity/.gemini/config/scripts").glob("*.py")),
            *list((REPO_DIR / "scripts").glob("*.py")),
            *list(mcp_root.rglob("*.py")),
            *list((REPO_DIR / "tests").rglob("*.py")), *list((REPO_DIR / "docs").rglob("*.md")),
            *list((REPO_DIR / "templates").rglob("*.md")),
        ])  # fmt: skip
        spec_re = re.compile(
            r"^Specification:\s*(docs/architecture/[a-zA-Z0-9_]+\.md)\s*$", re.MULTILINE
        )
        traceable_sources = sorted([
            *list((REPO_DIR / "antigravity/.gemini/config/scripts").glob("*.py")),
            REPO_DIR / "scripts/dotfiles_mcp_server.py",
            *[p for p in mcp_root.rglob("*.py") if p.name != "__init__.py"],
        ])  # fmt: skip

        # Act
        unit_root = REPO_DIR / "tests/unit/dotfiles_mcp"
        missing_unit_tests = [
            str(rel) for rel in pkg_modules
            if not (unit_root / rel.parent / f"test_{rel.stem}.py").is_file()
        ]  # fmt: skip
        oversized_files = [
            f"{p.relative_to(REPO_DIR)} ({len(p.read_text(encoding='utf-8').splitlines())} lines)"
            for p in all_sized_files if len(p.read_text(encoding="utf-8").splitlines()) >= 465
        ]  # fmt: skip
        untraced_sources = []
        for src in traceable_sources:
            m = spec_re.search(src.read_text(encoding="utf-8"))
            if not m or src.name not in (REPO_DIR / m.group(1)).read_text(encoding="utf-8"):
                untraced_sources.append(str(src.relative_to(REPO_DIR)))
        template_rules = sorted((REPO_DIR / "templates").rglob("rules/*.md"))
        missing_rule_frontmatter = [
            str(rf.relative_to(REPO_DIR)) for rf in template_rules
            if not rf.read_text(encoding="utf-8").startswith("---\n")
            or "trigger:" not in rf.read_text(encoding="utf-8").split("---", 2)[1]
        ]  # fmt: skip

        # Assert
        assert (len(pkg_modules), len(template_rules)) == (22, 13)
        assert (REPO_DIR / "docs/guides/01_ubuntu_system_and_multi_machine_guide.md").is_file()
        assert (REPO_DIR / "docs/guides/02_hierarchical_layers_and_team_workflows.md").is_file()
        assert (
            missing_unit_tests, oversized_files, untraced_sources, missing_rule_frontmatter
        ) == ([], [], [], [])  # fmt: skip
        arch_docs = (REPO_DIR / "docs/architecture").glob("0*.md")
        assert all("1:1:1" in p.read_text("utf-8") for p in arch_docs)
        agents_p = REPO_DIR / "antigravity/.gemini/config/AGENTS.md"
        assert not agents_p.read_text().startswith("---\n")

    def test_hooks_json_and_hook_scripts_maintain_doc_contract_parity(self) -> None:
        """Verify hooks.json matchers, guard regexes, and MCP/CLI contracts match docs."""
        # Arrange
        import post_invocation_lint
        import pre_tool_guard
        from dotfiles_mcp.core import constants as mcp_constants
        from dotfiles_mcp.governance import cli_dispatcher

        config_dir = REPO_DIR / "antigravity/.gemini/config"
        hooks_data = json.loads((config_dir / "hooks.json").read_text(encoding="utf-8"))
        agents_md = (config_dir / "AGENTS.md").read_text(encoding="utf-8")
        arch_02 = (REPO_DIR / "docs/architecture/02_antigravity_governance_and_hooks.md").read_text(
            encoding="utf-8"
        )
        arch_mcp = "\n".join(
            (REPO_DIR / f"docs/architecture/{n}").read_text(encoding="utf-8")
            for n in (
                "03_contextual_mcp_and_federation.md",
                "04_compaction_surface_and_promotion_engines.md",
                "05_ephemeral_forks_and_department_bots.md",
                "06_layer_governance_and_promotion_engines.md",
            )
        )
        security_md = (REPO_DIR / "SECURITY.md").read_text(encoding="utf-8")
        readme_md = (REPO_DIR / "README.md").read_text(encoding="utf-8")
        ext_guide = (REPO_DIR / "docs/reference/developer_and_extension_guide.md").read_text(
            encoding="utf-8"
        )
        guide_02 = (
            REPO_DIR / "docs/guides/02_hierarchical_layers_and_team_workflows.md"
        ).read_text(encoding="utf-8")
        full_audit_skill = (
            REPO_DIR / "antigravity/.gemini/config/skills/full-audit/SKILL.md"
        ).read_text(encoding="utf-8")
        layer_cfg_sh = (REPO_DIR / "scripts/layer-config.sh").read_text(encoding="utf-8")

        # Act
        pre_matcher = set(hooks_data["pre-tool-guard"]["PreToolUse"][0]["matcher"].split("|"))
        post_matcher = set(hooks_data["auto-format"]["PostToolUse"][0]["matcher"].split("|"))
        all_subs = (
            *cli_dispatcher.C1_DISCOVERY_SUBCOMMANDS,
            *cli_dispatcher.C2_LIFECYCLE_SUBCOMMANDS,
            *cli_dispatcher.C3_GOVERNANCE_SUBCOMMANDS,
            *cli_dispatcher.EPHEMERAL_BOT_SUBCOMMANDS,
        )

        # Assert
        assert "--upstream-repo" not in guide_02 and len(all_subs) == 26
        assert "Vertical Human Persona & Use-Case Journey Matrix" in full_audit_skill
        assert "Conceptual & Semantic Documentation Reading Pass" in full_audit_skill
        assert mcp_constants.VALID_TEMPLATE_KINDS == (
            "base-stack", "business-stack", "science-stack", "framework-stack"
        )  # fmt: skip
        assert pre_matcher == set(pre_tool_guard._FILE_WRITE_TOOLS) | {"run_command"}
        assert post_matcher == set(pre_tool_guard._FILE_WRITE_TOOLS)
        assert post_invocation_lint._AGENTS_MD_MAX_BYTES == mcp_constants.AGENTS_MD_MAX_BYTES
        for token in (
            *pre_tool_guard._DOCUMENTED_GIT_SUBCOMMANDS,
            "alembic/versions/",
            "__init__.py",
            "heredoc",
            "tee",
        ):
            assert token in arch_02 and token in security_md and token in readme_md
        for protected_target in (
            "alembic/versions/001_init.py",
            "src/orders/__init__.py",
            "tests/unit/__init__.py",
            ".agents/rules/layer-05-dept-legal.md",
        ):
            fw_ok, fw_reason = pre_tool_guard._check_file_write(
                {"Path": f"/workspace/app/{protected_target}", "Content": "x = 1"}
            )
            for cmd in (
                f"echo 'x = 1' > {protected_target}",
                f"echo 'x = 1' | tee {protected_target}",
                f"sed -i 's/a/b/' {protected_target}",
                f"python3 -c \"open('{protected_target}', 'w').write('x')\"",
            ):
                sh_ok, sh_reason = pre_tool_guard._check_command({"CommandLine": cmd})
                assert not fw_ok and not sh_ok and fw_reason == sh_reason
        for agents_token in ("0 bytes", "__init__.py", "NEVER run mutating git commands"):
            assert agents_token in agents_md
        for bt in ("18,000", "80,000", "TOKEN_BUDGET_EXCEEDED", "WORKSPACE_RULES_BUDGET_EXCEEDED"):
            assert bt in arch_02 and bt in arch_mcp
        for mcp_token in (
            "unfold_context_capsule", "resolve_surface_governance", "orchestrate_ephemeral_fork",
            "ephemeral_fork_policy", "surface_bindings", "collect_layer_effective_bindings",
            "promotion_routing", "SURFACE_PRECEDENCE_COLLISION", "SURFACE_ASSET_MISSING",
            "TEMPLATE_PACK_MISSING", "EPHEMERAL_FORK_LIMIT_REACHED", "EPHEMERAL_FORK_EXPIRED",
            "rcap1", "CAPSULE_CAPABILITY_INSUFFICIENT", "CAPSULE_RESONANCE_DENIED",
            "CAPSULE_CHAIN_BROKEN", "MCP_PERMISSION_RINGS", "BOT_ARCHETYPE_CATALOG",
            "resolve_mcp_capability_profile", "seal_ephemeral_digest_capsule",
            "unseal_ephemeral_digest_capsule", "EPHEMERAL_LEASE_EXPIRED_OR_SHREDDED",
            "SURFACE_BOUNDARY_VIOLATION",
        ):  # fmt: skip
            assert mcp_token in arch_mcp
        for sub in all_subs:
            assert sub in readme_md and sub in ext_guide and sub in arch_mcp and sub in layer_cfg_sh
        assert "All 26 Subcommands" in readme_md and "all 26 subcommands" in layer_cfg_sh
        recipes = mcp_constants.LAYER_MAKEFILE_RECIPES
        del_flags = ("--ticket", "--priority", "--surface", "--source")
        prom_flags = ("--upstream-dir $(TARGET_REPO)", "--to-layer", "--to-template")
        assert all(f in recipes["delegate"] for f in del_flags)
        assert all(f in recipes["promote"] for f in prom_flags)
        assert all(f in recipes["complete"] for f in ("--deliverable", "--summary", "--create-pr"))
        assert "--apply-safe" in recipes["upstream-diff"] and "--remove" in recipes["roster"]
        assert "--strategy" in recipes["sync"] and "--tier" in recipes["consult"]

    def test_single_language_english_purity_across_repository_files(self) -> None:
        """Verify 100% pure technical English across all repository docs, rules, and code."""
        # Arrange
        spanish_char_re = re.compile(
            r"[\u00e1\u00e9\u00ed\u00f3\u00fa\u00f1\u00fc\u00c1\u00c9\u00cd\u00d3\u00da\u00d1\u00dc\u00bf\u00a1]"
        )
        spanish_phrase_re = re.compile(
            r"\b(\x66ichero|\x66icheros|\x79a que estamos|\x73iempre enfoque limpio)\b",
            re.IGNORECASE,
        )
        targets = sorted([
            REPO_DIR / "README.md", REPO_DIR / "CONTRIBUTING.md", REPO_DIR / "SECURITY.md",
            REPO_DIR / "ACCESSIBILITY.md", REPO_DIR / "CODE_OF_CONDUCT.md",
            REPO_DIR / "CHANGELOG.md", *list((REPO_DIR / "antigravity").rglob("*.md")),
            *list((REPO_DIR / "antigravity").rglob("*.py")),
            *list((REPO_DIR / "docs").rglob("*.md")), *list((REPO_DIR / "templates").rglob("*.md")),
            *list((REPO_DIR / "scripts").rglob("*.py")), *list((REPO_DIR / "scripts").glob("*.sh")),
            *list((REPO_DIR / "system" / "external").rglob("*.sh")),
            *list((REPO_DIR / "tests").rglob("*.py")),
        ])  # fmt: skip

        # Act
        violations = [
            f"{p.relative_to(REPO_DIR)}:{idx}"
            for p in targets
            if p.is_file()
            for idx, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1)
            if spanish_char_re.search(line) or spanish_phrase_re.search(line)
        ]

        # Assert
        assert len(targets) >= 80
        assert violations == []

    def test_framework_agnostic_and_compaction_terminology_purity(self) -> None:
        """Verify zero sibling-project leaks, canonical symbols, and 4-Scope Extrapolation."""
        # Arrange
        local_project_tokens = sorted({
            variant for d in (Path.home() / "Projects").glob("*")
            if d.is_dir() and len(d.name) >= 5
            and not d.name.lower().startswith(("dev-", "gov-", "sci-", "geo-"))
            for variant in (d.name.lower(), d.name.lower().replace("_", "-"))
        })  # fmt: skip
        dynamic_tokens = [
            re.escape(tok)
            for tok in (
                *local_project_tokens, "\x70romoter_header", "\x5fopen_single_capsule",
                "\x5flocate_section_with_drift_tolerance", "\x4dCP_LAYER_SCHEMA_VERSION",
                "\x54EMPLATE_SCHEMA_VERSION", "\x44EFAULT_INITIAL_LAYER_VERSION",
                "\x46ALLBACK_UNKNOWN_VERSION", "\x4eEW_LAYER_INITIAL_SEMVER",
                "\x68uman-core", "\x63ore-base",
            )
        ]  # fmt: skip
        retired_token_re = re.compile(
            r"\b(" + "|".join(dynamic_tokens) + r")\b|\[DOTFILES-" + r"\d+\]"
            r"|`?(?:19|20|21|23)`?\s+"
            + r"modules\b|\b\x35-Stage\b|scripts/dotfiles_mcp/"
            + r"\*\.py|\b\x48uman-Specs?\b|domain-[a-z<>-]+:\x4c[1-4]"
            + r"|\b\x4c1\.\.\x4c4\b|\b\x4cayer\s+[ABCD]\b",
            re.IGNORECASE,
        )
        extrapolable_technical_targets = [
            REPO_DIR / "templates/base-stack/science-base/rules/science-base.md",
            REPO_DIR / "templates/science-stack/software-engineering/rules/software-engineering.md",
            REPO_DIR / "templates/base-stack/business-base/rules/business-base.md",
            REPO_DIR / "templates/science-stack/software-engineering/skills/testing/SKILL.md",
            REPO_DIR / "templates/science-stack/software-engineering/skills/refactoring/SKILL.md",
            REPO_DIR / "antigravity/.gemini/config/skills/review/SKILL.md",
            REPO_DIR / "antigravity/.gemini/config/skills/full-audit/SKILL.md",
            REPO_DIR / "antigravity/.gemini/config/skills/priority/SKILL.md",
            REPO_DIR / "templates/science-stack/software-engineering/skills/validation/SKILL.md",
            REPO_DIR
            / "templates/science-stack/software-engineering/skills/oss-contribute/SKILL.md",
            REPO_DIR / "antigravity/.gemini/config/skills/architecture-review/SKILL.md",
            REPO_DIR / "antigravity/.gemini/config/skills/governance/SKILL.md",
        ]
        scope_leak_re = re.compile(
            r"\b(24\s+test|25\s+test|16\s+modules|8\s+verification\s+gates"
            r"|hx-post|hx-get|hx-target|--prepare-pr|isomorphic_extraction"
            r"|\x69ntegration\s+tests?|\x69ntegration\s+tier)\b",
            re.IGNORECASE,
        )
        arch_dir = REPO_DIR / "docs/architecture"
        arch_04 = (arch_dir / "04_compaction_surface_and_promotion_engines.md").read_text("utf-8")
        arch_05 = (arch_dir / "05_ephemeral_forks_and_department_bots.md").read_text("utf-8")
        arch_06 = (arch_dir / "06_layer_governance_and_promotion_engines.md").read_text("utf-8")
        bus_md = (REPO_DIR / "templates/base-stack/business-base/rules/business-base.md").read_text(
            "utf-8"
        )
        targets = sorted([
            REPO_DIR / "README.md", REPO_DIR / "CONTRIBUTING.md", REPO_DIR / "CHANGELOG.md",
            *list((REPO_DIR / "antigravity").rglob("*.md")),
            *list((REPO_DIR / "antigravity").rglob("*.py")),
            *list((REPO_DIR / "docs").rglob("*.md")),
            *list((REPO_DIR / "templates").rglob("*.md")),
            *list((REPO_DIR / "scripts").rglob("*.py")),
            *list((REPO_DIR / "scripts").glob("*.sh")),
            *list((REPO_DIR / "tests").rglob("*.py")),
        ])  # fmt: skip

        # Act
        violations = [
            f"{p.relative_to(REPO_DIR)}:{idx}"
            for p in targets if p.is_file()
            for idx, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1)
            if retired_token_re.search(line) and (p.name != "CHANGELOG.md" or idx < 36)
        ]  # fmt: skip
        scope_violations = [
            f"{p.relative_to(REPO_DIR)}:{idx}"
            for p in extrapolable_technical_targets
            for idx, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1)
            if scope_leak_re.search(line)
        ]

        # Assert
        assert violations == [] and scope_violations == []
        assert (
            "./scripts/layer-config.sh apply-project $(CURDIR) --template software-engineering"
            in (REPO_DIR / "Makefile").read_text(encoding="utf-8")
        )
        assert all(
            c in arch_04
            for c in ("promoter_codon", "_parse_capsule_envelope", "_resolve_ephemeral_issuer_meta")
        )
        assert all(
            c in arch_06 and c in bus_md
            for c in ("RECONCILED_FLOW", "ESCALATE_TO_ROOT", "ESCALATE_INTER_ENTITY_ROOTS")
        )
        assert all(
            c in arch_06
            for c in (
                "diff-project <dir> [--parent-dir <dir>]", "configure_fork_manifest",
                "inspect_layer_horizon", "verify_layer_operation_authority",
            )
        )  # fmt: skip
        assert "entity_kind" in bus_md
        assert all(
            c in arch_05
            for c in ("ephemeral_capsules", "default_ephemeral_root", "_copy_zero_copy")
        )

    def test_test_suite_ast_anti_deception_invariants(self) -> None:
        """Verify single Test* class, 100% test method docstrings, and AST anti-deception gates."""
        # Arrange
        prod_py = sorted([
            *list((REPO_DIR / "antigravity/.gemini/config/scripts").glob("*.py")),
            *list((REPO_DIR / "scripts").glob("*.py")),
            *list((REPO_DIR / "scripts/dotfiles_mcp").rglob("*.py")),
        ])  # fmt: skip
        test_py = sorted(p for p in (REPO_DIR / "tests").rglob("test_*.py"))

        # Act
        pragma_violations = [
            f"{p.relative_to(REPO_DIR)}:{idx}"
            for p in prod_py
            for idx, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1)
            if "pragma:" in line and "no cover" in line
        ]
        prod_style_violations = [
            f"{p.relative_to(REPO_DIR)}:{getattr(n, 'lineno', 0)}"
            for p in prod_py
            for n in ast.walk(ast.parse(p.read_text(encoding="utf-8"), filename=str(p)))
            if (
                isinstance(n, ast.Call)
                and isinstance(n.func, ast.Attribute)
                and n.func.attr == "update"
                and bool(n.keywords)
            )
            or (
                isinstance(n, ast.Slice)
                and any(
                    isinstance(b, ast.Constant) and isinstance(b.value, int) and abs(b.value) > 2
                    for b in (n.lower, n.upper)
                )
            )
            or (
                isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                and (not n.name.startswith("_") or n.name == "__init__")
                and not ast.get_docstring(n)
            )
            or (
                p.name.endswith("_engine.py")
                and isinstance(n, ast.ImportFrom)
                and bool(n.module and n.module.endswith("_engine"))
                and any(a.name.startswith("_") for a in n.names)
            )
            or (
                p.parent.name in ("core", "capsules", "mcp_node")
                and isinstance(n, ast.ImportFrom) and n.module is not None
                and n.module.startswith("dotfiles_mcp.")
                and (
                    (p.parent.name == "core" and not n.module.startswith("dotfiles_mcp.core"))
                    or (p.parent.name == "capsules" and "governance" in n.module)
                    or (p.name.endswith(("_engine.py", "_weaver.py")) and "mcp_node" in n.module)
                    or (p.parent.name == "mcp_node" and p.name != "tools_federation.py" and "governance" in n.module)  # noqa: E501
                )
            )
        ]  # fmt: skip
        unmatched_raises, blind_subprocess_mocks, structure_violations = [], [], []
        for tp in test_py:
            rel_tp = str(tp.relative_to(REPO_DIR))
            tree = ast.parse(tp.read_text(encoding="utf-8"), filename=str(tp))
            top_tests = [
                s.name for s in tree.body
                if isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef))
                and s.name.startswith("test_")
            ]  # fmt: skip
            test_classes = [
                s for s in tree.body if isinstance(s, ast.ClassDef) and s.name.startswith("Test")
            ]
            mod_doc = ast.get_docstring(tree) or ""
            if (
                top_tests
                or len(test_classes) != 1
                or "Specification: docs/architecture/" not in mod_doc
            ):
                structure_violations.append(f"{rel_tp}: classes={len(test_classes)}")
            for node in ast.walk(tree):
                has_raw_slice = isinstance(node, ast.Slice) and any(
                    isinstance(b, ast.Constant) and isinstance(b.value, int) and abs(b.value) > 2
                    for b in (node.lower, node.upper)
                )
                if (
                    isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and not node.name.startswith("_")
                    and not ast.get_docstring(node)
                ) or has_raw_slice:
                    structure_violations.append(f"{rel_tp}:{getattr(node, 'lineno', 0)}")
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "raises"
                    and not any(kw.arg == "match" for kw in node.keywords)
                ):
                    unmatched_raises.append(f"{rel_tp}:{node.lineno}")
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "setattr"
                    and len(node.args) >= 2
                    and isinstance(node.args[0], ast.Constant)
                    and node.args[0].value == "subprocess.run"
                    and isinstance(node.args[1], ast.Lambda)
                ):
                    blind_subprocess_mocks.append(f"{rel_tp}:{node.lineno}")

        # Assert
        assert (len(prod_py), len(test_py)) == (34, 35)
        assert pragma_violations == [] and prod_style_violations == []
        assert unmatched_raises == [] and blind_subprocess_mocks == []
        assert structure_violations == []
        const_p = REPO_DIR / "scripts/dotfiles_mcp/core/constants.py"
        const_text = const_p.read_text(encoding="utf-8")
        other_py = "\n".join(
            p.read_text(encoding="utf-8") for p in [*prod_py, *test_py] if p.name != "constants.py"
        )
        assert [
            m.group(1)
            for m in re.finditer(r"^([A-Z][A-Z0-9_]+)\b", const_text, re.M)
            if m.group(1) not in other_py
        ] == []
