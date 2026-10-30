"""Implementation tests for repository parity gates, 1:1:1 traceability, and hook-to-doc sync."""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parents[2]


def test_all_test_init_files_are_strictly_zero_bytes() -> None:
    # Arrange
    init_files = sorted(
        [
            REPO_DIR / "scripts" / "dotfiles_mcp" / "__init__.py",
            *list((REPO_DIR / "tests").rglob("__init__.py")),
        ]
    )

    # Act
    non_empty = [str(p.relative_to(REPO_DIR)) for p in init_files if p.stat().st_size != 0]

    # Assert
    assert len(init_files) == 6
    assert non_empty == []


def test_one_to_one_unit_test_mapping_and_file_size_discipline() -> None:
    # Arrange
    declarative_only = {"__init__.py", "constants.py", "catalogs.py"}
    pkg_modules = sorted(
        p.stem
        for p in (REPO_DIR / "scripts" / "dotfiles_mcp").glob("*.py")
        if p.name not in declarative_only
    )
    all_sized_files = sorted(
        [
            *list((REPO_DIR / "antigravity/.gemini/config/scripts").glob("*.py")),
            *list((REPO_DIR / "scripts").glob("*.py")),
            *list((REPO_DIR / "scripts/dotfiles_mcp").glob("*.py")),
            *list((REPO_DIR / "tests").rglob("*.py")),
            *list((REPO_DIR / "docs").rglob("*.md")),
        ]
    )
    spec_re = re.compile(
        r"^Specification:\s*(docs/architecture/[a-zA-Z0-9_]+\.md)\s*$", re.MULTILINE
    )
    traceable_sources = sorted(
        [
            *list((REPO_DIR / "antigravity/.gemini/config/scripts").glob("*.py")),
            REPO_DIR / "scripts/dotfiles_mcp_server.py",
            *[
                p
                for p in (REPO_DIR / "scripts/dotfiles_mcp").glob("*.py")
                if p.name != "__init__.py"
            ],
        ]
    )

    # Act
    missing_unit_tests = [
        mod
        for mod in pkg_modules
        if not (REPO_DIR / "tests" / "unit" / "dotfiles_mcp" / f"test_{mod}.py").is_file()
    ]
    oversized_files = [
        f"{p.relative_to(REPO_DIR)} ({len(p.read_text(encoding='utf-8').splitlines())} lines)"
        for p in all_sized_files
        if len(p.read_text(encoding="utf-8").splitlines()) >= 465
    ]
    untraced_sources = []
    for src in traceable_sources:
        m = spec_re.search(src.read_text(encoding="utf-8"))
        if not m or src.name not in (REPO_DIR / m.group(1)).read_text(encoding="utf-8"):
            untraced_sources.append(str(src.relative_to(REPO_DIR)))

    # Assert
    assert len(pkg_modules) == 14
    assert missing_unit_tests == []
    assert oversized_files == []
    assert untraced_sources == []


def test_hooks_json_and_hook_scripts_maintain_doc_contract_parity() -> None:
    # Arrange
    import post_invocation_lint
    import pre_tool_guard
    from dotfiles_mcp import constants as mcp_constants

    config_dir = REPO_DIR / "antigravity/.gemini/config"
    hooks_data = json.loads((config_dir / "hooks.json").read_text(encoding="utf-8"))
    agents_md = (config_dir / "AGENTS.md").read_text(encoding="utf-8")
    arch_02 = (REPO_DIR / "docs/architecture/02_antigravity_governance_and_hooks.md").read_text(
        encoding="utf-8"
    )
    arch_03 = (REPO_DIR / "docs/architecture/03_contextual_mcp_and_federation.md").read_text(
        encoding="utf-8"
    )
    arch_04 = (
        REPO_DIR / "docs/architecture/04_compaction_surface_and_promotion_engines.md"
    ).read_text(encoding="utf-8")
    arch_05 = (REPO_DIR / "docs/architecture/05_ephemeral_forks_and_department_bots.md").read_text(
        encoding="utf-8"
    )
    arch_mcp = arch_03 + "\n" + arch_04 + "\n" + arch_05
    security_md = (REPO_DIR / "SECURITY.md").read_text(encoding="utf-8")
    readme_md = (REPO_DIR / "README.md").read_text(encoding="utf-8")
    ext_guide = (REPO_DIR / "docs/reference/developer_and_extension_guide.md").read_text(
        encoding="utf-8"
    )

    # Act
    pre_matcher = set(hooks_data["pre-tool-guard"]["PreToolUse"][0]["matcher"].split("|"))
    post_matcher = set(hooks_data["auto-format"]["PostToolUse"][0]["matcher"].split("|"))

    # Assert
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
        assert token in arch_02
        assert token in security_md
        assert token in readme_md
    for protected_target in (
        "alembic/versions/001_init.py",
        "src/orders/__init__.py",
        "tests/unit/__init__.py",
    ):
        fw_ok, fw_reason = pre_tool_guard._check_file_write(
            {"Path": f"/workspace/app/{protected_target}", "Content": "x = 1"}
        )
        sh_redir_ok, sh_redir_reason = pre_tool_guard._check_command(
            {"CommandLine": f"echo 'x = 1' > {protected_target}"}
        )
        sh_tee_ok, sh_tee_reason = pre_tool_guard._check_command(
            {"CommandLine": f"echo 'x = 1' | tee {protected_target}"}
        )
        assert (fw_ok, sh_redir_ok, sh_tee_ok) == (False, False, False)
        assert fw_reason == sh_redir_reason == sh_tee_reason
    for agents_token in ("0 bytes", "__init__.py", "NEVER run mutating git commands"):
        assert agents_token in agents_md
    for budget_token in (
        "18,000",
        "80,000",
        "TOKEN_BUDGET_EXCEEDED",
        "WORKSPACE_RULES_BUDGET_EXCEEDED",
    ):
        assert budget_token in arch_02
        assert budget_token in arch_mcp
    for mcp_token in (
        "unfold_context_capsule",
        "resolve_surface_governance",
        "orchestrate_ephemeral_fork",
        "ephemeral_fork_policy",
        "surface_bindings",
        "collect_layer_effective_bindings",
        "promotion_routing",
        "SURFACE_PRECEDENCE_COLLISION",
        "SURFACE_ASSET_MISSING",
        "TEMPLATE_PACK_MISSING",
        "EPHEMERAL_FORK_LIMIT_REACHED",
        "EPHEMERAL_FORK_EXPIRED",
        "rcap1",
        "CAPSULE_CAPABILITY_INSUFFICIENT",
        "CAPSULE_RESONANCE_DENIED",
        "CAPSULE_CHAIN_BROKEN",
    ):
        assert mcp_token in arch_mcp
    for sub in (
        "init-fork",
        "list-templates",
        "scaffold-template",
        "apply-project",
        "diff-project",
        "promote-from-project",
        "spawn-ephemeral",
        "inspect-ephemeral",
        "reap-ephemeral",
    ):
        assert sub in readme_md
        assert sub in ext_guide


def test_single_language_english_purity_across_repository_files() -> None:
    # Arrange
    spanish_char_re = re.compile(
        r"[\u00e1\u00e9\u00ed\u00f3\u00fa\u00f1\u00fc\u00c1\u00c9\u00cd\u00d3\u00da\u00d1\u00dc\u00bf\u00a1]"
    )
    spanish_phrase_re = re.compile(
        r"\b(\x66ichero|\x66icheros|\x79a que estamos|\x73iempre enfoque limpio)\b",
        re.IGNORECASE,
    )
    targets = sorted(
        [
            REPO_DIR / "README.md",
            REPO_DIR / "CONTRIBUTING.md",
            REPO_DIR / "SECURITY.md",
            REPO_DIR / "ACCESSIBILITY.md",
            REPO_DIR / "CODE_OF_CONDUCT.md",
            REPO_DIR / "CHANGELOG.md",
            *list((REPO_DIR / "antigravity").rglob("*.md")),
            *list((REPO_DIR / "antigravity").rglob("*.py")),
            *list((REPO_DIR / "docs").rglob("*.md")),
            *list((REPO_DIR / "templates").rglob("*.md")),
            *list((REPO_DIR / "scripts").rglob("*.py")),
            *list((REPO_DIR / "scripts").glob("*.sh")),
            *list((REPO_DIR / "system" / "external").rglob("*.sh")),
            *list((REPO_DIR / "tests").rglob("*.py")),
        ]
    )

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


def test_framework_agnostic_and_compaction_terminology_purity() -> None:
    # Arrange
    retired_token_re = re.compile(
        r"\b(\x6f\x73\x61|\x70romoter_header|\x5fopen_single_capsule"
        r"|\x5flocate_section_with_drift_tolerance)\b|\x6f\x73\x61_|\x6f\x73\x61-",
        re.IGNORECASE,
    )
    arch_04 = (
        REPO_DIR / "docs/architecture/04_compaction_surface_and_promotion_engines.md"
    ).read_text(encoding="utf-8")
    arch_05 = (REPO_DIR / "docs/architecture/05_ephemeral_forks_and_department_bots.md").read_text(
        encoding="utf-8"
    )
    targets = sorted(
        [
            REPO_DIR / "README.md",
            REPO_DIR / "CHANGELOG.md",
            *list((REPO_DIR / "antigravity").rglob("*.md")),
            *list((REPO_DIR / "antigravity").rglob("*.py")),
            *list((REPO_DIR / "docs").rglob("*.md")),
            *list((REPO_DIR / "templates").rglob("*.md")),
            *list((REPO_DIR / "scripts").rglob("*.py")),
            *list((REPO_DIR / "scripts").glob("*.sh")),
            *list((REPO_DIR / "tests").rglob("*.py")),
        ]
    )

    # Act
    violations = [
        f"{p.relative_to(REPO_DIR)}:{idx}"
        for p in targets
        if p.is_file()
        for idx, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1)
        if retired_token_re.search(line)
    ]

    # Assert
    assert violations == []
    for canonical in (
        "promoter_codon",
        "_parse_capsule_envelope",
        "_resolve_ephemeral_issuer_meta",
    ):
        assert canonical in arch_04
    for eph_canonical in (
        "ephemeral_capsules",
        "default_ephemeral_root",
        "_copy_zero_copy",
    ):
        assert eph_canonical in arch_05


def test_test_suite_ast_anti_deception_invariants() -> None:
    # Arrange
    prod_py = sorted(
        [
            *list((REPO_DIR / "antigravity/.gemini/config/scripts").glob("*.py")),
            *list((REPO_DIR / "scripts").glob("*.py")),
            *list((REPO_DIR / "scripts/dotfiles_mcp").glob("*.py")),
        ]
    )
    test_py = sorted((REPO_DIR / "tests").rglob("*.py"))

    # Act
    pragma_violations = [
        f"{p.relative_to(REPO_DIR)}:{idx}"
        for p in prod_py
        for idx, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1)
        if "pragma:" in line and "no cover" in line
    ]
    unmatched_raises: list[str] = []
    blind_subprocess_mocks: list[str] = []
    for tp in test_py:
        tree = ast.parse(tp.read_text(encoding="utf-8"), filename=str(tp))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "raises"
                and not any(kw.arg == "match" for kw in node.keywords)
            ):
                unmatched_raises.append(f"{tp.relative_to(REPO_DIR)}:{node.lineno}")
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "setattr"
                and len(node.args) >= 2
                and isinstance(node.args[0], ast.Constant)
                and node.args[0].value == "subprocess.run"
                and isinstance(node.args[1], ast.Lambda)
            ):
                blind_subprocess_mocks.append(f"{tp.relative_to(REPO_DIR)}:{node.lineno}")

    # Assert
    assert len(prod_py) == 22
    assert pragma_violations == []
    assert unmatched_raises == []
    assert blind_subprocess_mocks == []
