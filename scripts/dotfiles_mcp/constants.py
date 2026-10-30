"""Constants, thresholds, and compiled regular expressions for dotfiles-ubuntu MCP.

Specification: docs/architecture/03_contextual_mcp_and_federation.md
"""

from __future__ import annotations

import re
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = SCRIPT_DIR.parent
PROTOCOL_VERSION = "2024-11-05"
VALID_LAYER_ROLES = (
    "corporate",
    "department",
    "domain-policy",
    "ephemeral-bot",
    "team",
    "service-node",
    "environment-cluster",
    "workstation",
)
VALID_ENVIRONMENTS = ("dev", "tst", "pre", "pro")
VALID_TEMPLATE_KINDS = (
    "stack-starter",
    "domain-policy-pack",
    "department-pack",
    "project-overlay",
)
ROLE_DEFAULT_PRECEDENCE: dict[str, int] = {
    "domain-policy": 5,
    "corporate": 10,
    "workstation": 10,
    "ephemeral-bot": 15,
    "department": 30,
    "team": 50,
    "service-node": 60,
    "environment-cluster": 70,
}
VALID_ARCHITECTURAL_PLANES = (
    "schema",
    "domain",
    "application",
    "presentation",
    "infrastructure",
    "testing",
)
PLANE_PATH_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("testing", ("tests/", "e2e/", "__tests__/", "test_", "_test.", ".spec.")),
    (
        "presentation",
        (
            "templates/",
            "static/",
            "ui/",
            "views/",
            "components/",
            "pages/",
            ".html",
            ".css",
            ".scss",
            ".tsx",
            ".jsx",
            ".vue",
        ),
    ),
    (
        "schema",
        (
            "models.py",
            "schema.py",
            "schemas/",
            "migrations/",
            "alembic/",
            "entities/",
            ".sql",
            ".prisma",
        ),
    ),
    ("domain", ("service.py", "domain.py", "ports.py", "domain/", "services/", "policies/")),
    (
        "application",
        (
            "router.py",
            "controller.py",
            "use_cases.py",
            "tasks.py",
            "dependencies.py",
            "application/",
            "use_cases/",
            "routers/",
            "api/",
            "handlers/",
        ),
    ),
    (
        "infrastructure",
        (
            "repository.py",
            "dockerfile",
            "repositories/",
            "adapters/",
            "infrastructure/",
            "infra/",
            "db/",
        ),
    ),
)
STRUCTURAL_PATH_SEGMENTS = frozenset(
    {
        "src",
        "app",
        "internal",
        "pkg",
        "lib",
        "templates",
        "static",
        "partials",
        "components",
        "css",
        "js",
        "tests",
        "unit",
        "imp",
        "e2e",
        "docs",
        "architecture",
        "reference",
    }
)
CAPSULE_PREFIX = "rcap1"
VALID_BINDING_MODES = ("authoritative", "transversal")
VALID_RESOLUTIONS = ("L0", "L1", "L2")
VALID_CAPSULE_LEVELS = ("L0", "L1", "L2", "L3")
VALID_AGENT_TIERS = ("flash", "inherit", "pro")
VALID_EPHEMERAL_ACTIONS = ("spawn", "inspect", "evaluate", "reap")
VALID_EPHEMERAL_ACCESS_MODES = (
    "strictly-read-only",
    "read-and-test-trigger",
    "read-write-scoped",
)
DEFAULT_EPHEMERAL_TTL_SECONDS = 300
MIN_EPHEMERAL_TTL_SECONDS = 10
MAX_EPHEMERAL_TTL_SECONDS = 3600
MAX_ACTIVE_EPHEMERAL_FORKS = 16
AGENT_TIER_RANK: dict[str, int] = {"flash": 1, "inherit": 2, "pro": 3}
LEVEL_INDEX: dict[str, int] = {"L0": 0, "L1": 1, "L2": 2, "L3": 3}
NEXT_LEVEL_MAP: dict[str, str] = {"L0": "L1", "L1": "L2", "L2": "L3"}
LEVEL_MIN_TIER: dict[str, str] = {"L0": "flash", "L1": "flash", "L2": "inherit", "L3": "inherit"}
AGENTS_MD_WARN_BYTES = 16000
AGENTS_MD_MAX_BYTES = 18000
MCP_PAYLOAD_WARN_BYTES = 16000
MAX_LOG_FILE_BYTES = 524288
ALLOWED_READ_PREFIXES = ("docs/", "templates/", "antigravity/", "system/")
ALLOWED_ROOT_FILES = {
    "README.md",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "ACCESSIBILITY.md",
    "CODE_OF_CONDUCT.md",
    "VERSION",
}
ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")
KEBAB_ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
MD_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
BACKTICK_PATH_RE = re.compile(r"`([a-zA-Z0-9_./-]+\.(?:md|html|j2|css))`")
BOLD_TERM_RE = re.compile(r"\*\*([^*]{3,40})\*\*")
WORD_TOKEN_RE = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_-]{2,}")
CODON_STOPWORDS = frozenset(
    {
        "the",
        "and",
        "for",
        "with",
        "that",
        "this",
        "from",
        "are",
        "must",
        "never",
        "when",
        "all",
        "any",
        "not",
        "use",
        "only",
        "into",
        "over",
    }
)
