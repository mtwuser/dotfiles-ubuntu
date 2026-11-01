"""Constants, thresholds, and compiled regular expressions for dotfiles-ubuntu MCP.

Specification: docs/architecture/03_contextual_mcp_and_federation.md
"""

from __future__ import annotations

import re
import stat
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = SCRIPT_DIR.parent
PROTOCOL_VERSION = "2024-11-05"
VALID_LAYER_ROLES = (
    "corporate",
    "department",
    "domain-policy",
    "ephemeral-bot",
    "squad",
    "service-node",
    "environment-cluster",
    "workstation",
)
VALID_OPERATING_STATES: tuple[str, ...] = (
    "oss-readonly-appliance",
    "oss-dev",
    "corporate-root",
    "domain-policy",
    "department",
    "squad",
    "service-node",
    "environment-cluster",
    "ephemeral-bot",
    "project",
)
VALID_ENVIRONMENTS = ("dev", "tst", "pre", "pro")
DEFAULT_PROTECTED_BRANCHES: tuple[str, ...] = (
    "main",
    "master",
    "env/tst",
    "env/pre",
    "env/pro",
)
DEFAULT_PROCESS_BRANCH_PREFIXES: dict[str, str] = {
    "feature": "feature/",
    "task": "task/",
    "analysis": "analysis/",
    "validate": "validate/",
    "promote": "promote/",
    "directive": "directive/",
}
DEFAULT_ENV_BRANCH_MAP: dict[str, str] = {
    "dev": "feature/*",
    "tst": "env/tst",
    "pre": "env/pre",
    "pro": "main",
}
VALID_GOVERNANCE_DECISIONS: tuple[str, ...] = ("approve", "reject", "defer", "blocked")
VALID_ROSTER_ROLES: tuple[str, ...] = ("owner", "maintainer", "validator", "member")
VALID_TRACKER_FILES: tuple[str, ...] = (
    "WORKTASK.md",
    "BACKLOG.md",
    "WORKROAD.md",
    "ROADMAP.md",
    "WORKVALI.md",
)
VALID_DELEGATION_DIRS: tuple[str, ...] = ("roadmaps", "rules", "corporate")
VALID_DELEGATION_SURFACES: tuple[str, ...] = (*VALID_TRACKER_FILES, *VALID_DELEGATION_DIRS)
AGENTS_RULES_PREFIX: tuple[str, str] = (".agents", "rules")
AGENTS_SKILLS_PREFIX: tuple[str, str] = (".agents", "skills")
AGENTS_ASSETS_PREFIX: tuple[str, str] = (".agents", "assets")
GIT_CMD_TIMEOUT_SECONDS = 5
MIN_PRIVATE_TOKEN_LEN = 4
MIN_ROUTING_KEYWORD_LEN = 3
MAX_BRANCH_SLUG_TOKENS = 7
MAX_BRANCH_SLUG_CHARS = 48
MAX_DIFF_PREVIEW_LINES = 16
MAX_CONSULT_MATCHES = 5
AUDIT_LOG_TAIL_LINES = 20
MAX_RECENT_GOVERNANCE_ALERTS = 5
STATUS_EXCERPT_MAX_LINES = 35
SKILL_MD_MAX_LINES = 500
OWNER_WRITABLE_MODE_BIT = stat.S_IWUSR
OWNER_DIR_RWX_BITS = stat.S_IRWXU
TEMPLATE_STACK_GROUP_DIRS = (
    "business-stack",
    "squad-stack",
    "tech-stack",
)
VALID_TEMPLATE_KINDS = (
    "core-base",
    "business-stack",
    "squad-stack",
    "tech-stack",
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
    "squad": 50,
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
MATERIALIZED_RULE_RE = re.compile(r"^layer-(\d{2})-([a-z0-9-]+)\.md$")
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
CONSUMER_ALLOWED_OPS: tuple[str, ...] = (
    "list-templates",
    "apply-project",
    "sync-layer",
    "diff-project",
    "promote-from-project",
    "check-authority",
    "inspect-horizon",
    "start-task",
    "complete-task",
    "compare-upstream",
    "consult-layer",
    "check-env-promotion",
    "record-decision",
)
VALIDATOR_ALLOWED_OPS: tuple[str, ...] = (
    "check-env-promotion",
    "record-decision",
)
MAINTAINER_ALLOWED_OPS: tuple[str, ...] = (
    "scaffold-template",
    "manage-roster",
    "configure-git-policy",
    "delegate-to-child",
)
OWNER_RESTRICTED_OPS: tuple[str, ...] = (
    "init-fork",
    "scaffold-template",
    "register-subtree",
    "set-authority",
    "manage-roster",
    "configure-git-policy",
    "delegate-to-child",
    "release",
    "commit-layer",
    "push-layer",
)
_WORKSTATION_DEV_TARGETS: tuple[str, ...] = (
    "status", "setup-dev", "verify", "audit", "test", "test-unit",
    "test-imp", "test-e2e", "lint", "format", "workstation-sync", "docker-build",
)  # fmt: skip
_FULL_LAYER_TARGETS: tuple[str, ...] = (
    "status", "task", "complete", "consult", "horizon", "sync", "upstream-diff",
    "diff", "authority", "roster", "env-gate", "decision", "promote", "delegate", "mcp-test",
)  # fmt: skip
LAYER_ROLE_MAKEFILE_TARGETS: dict[str, tuple[str, ...]] = {
    "workstation": _WORKSTATION_DEV_TARGETS,
    "corporate": tuple(t for t in _FULL_LAYER_TARGETS if t != "complete"),
    "domain-policy": tuple(t for t in _FULL_LAYER_TARGETS if t != "complete"),
    "department": _FULL_LAYER_TARGETS,
    "squad": _FULL_LAYER_TARGETS,
    "project": tuple(
        t for t in _FULL_LAYER_TARGETS if t not in ("delegate", "horizon", "mcp-test")
    ),
}
COMMAND_CONSCIOUSNESS_TIERS: dict[str, tuple[str, ...]] = {
    "auto_reflexive": (
        "status", "diff", "horizon", "upstream-diff", "consult", "authority",
        "mcp-test", "verify", "audit", "test", "test-unit", "test-imp",
        "test-e2e", "lint", "format",
    ),
    "guided_tactical": (
        "task", "sync", "setup-dev", "workstation-sync", "docker-build",
    ),
    "conscious_human_gated": (
        "delegate", "complete", "promote", "env-gate", "decision", "roster",
    ),
}  # fmt: skip
_CLI_RUN = "\t@$(DOTFILES_DIR)/scripts/layer-config.sh"
_PF = "$(CURDIR) $(PARENT_FLAG)"
LAYER_MAKEFILE_RECIPES: dict[str, str] = {
    "status": f"{_CLI_RUN} status {_PF}",
    "task": (
        f'{_CLI_RUN} start-task $(CURDIR) --task "$(TASK)" $(if $(TICKET),--ticket $(TICKET),)'
    ),
    "complete": f'{_CLI_RUN} complete-task {_PF} --task "$(TASK)"',
    "consult": f'{_CLI_RUN} consult-layer $(CURDIR) --layer $(LAYER) --query "$(QUERY)"',
    "horizon": f"{_CLI_RUN} inspect-horizon {_PF}",
    "sync": f"{_CLI_RUN} sync-layer {_PF}",
    "upstream-diff": f"{_CLI_RUN} compare-upstream {_PF}",
    "diff": f"{_CLI_RUN} diff-project $(CURDIR)",
    "authority": f"{_CLI_RUN} check-authority $(CURDIR) --op release",
    "roster": (
        f"{_CLI_RUN} manage-roster $(CURDIR) $(if $(ADD),--add $(ADD),) "
        "$(if $(ROLE),--role $(ROLE),)"
    ),
    "env-gate": f"{_CLI_RUN} check-env-promotion $(CURDIR) --to-env $(if $(ENV),$(ENV),tst)",
    "decision": (
        f'{_CLI_RUN} record-decision $(CURDIR) --item "$(ITEM)" '
        '--decision $(DEC) --reason "$(REASON)"'
    ),
    "promote": f"{_CLI_RUN} promote-from-project $(CURDIR) --source $(SOURCE) $(PR_FLAGS)",
    "delegate": f'{_CLI_RUN} delegate-to-child $(CURDIR) --to-child $(CHILD) --task "$(TASK)"',
    "mcp-test": f"{_CLI_RUN} list-templates $(CURDIR)",
}
GENERIC_LAYER_TOKENS: frozenset[str] = frozenset(
    {
        "root",
        "corp",
        "corporate",
        "dept",
        "department",
        "team",
        "squad",
        "layer",
        "base",
        "pack",
        "policy",
        "project",
        "enterprise",
        "acme",
        "demo",
        "test",
        "tech",
        "legal",
        "finance",
        "supply",
        "design",
        "brand",
        "marketing",
        "social",
        "growth",
        "safety",
        "human",
        "core",
        "technical",
        "business",
    }
)
GENERIC_EMAIL_DOMAINS: frozenset[str] = frozenset(
    {"users.noreply.github.com", "example.com", "acme.com", "localhost"}
)
SECONDS_PER_DAY: int = 86_400
STALE_PROPOSAL_MAX_DAYS: int = 14
STALE_MODULE_REVIEW_DAYS: int = 90
STALE_POLICY_REVIEW_DAYS: int = 180
BUSINESS_PHASE_SEMANTICS: dict[str, str] = {
    "dev": "Drafting & Task Execution",
    "tst": "Department/Squad Peer Analysis",
    "pre": "Cross-Layer / C-Level Pre-Approval (WORKVALI.md)",
    "pro": "Ratified Corporate/Departmental Norm",
}
TECHNICAL_PHASE_SEMANTICS: dict[str, str] = {
    "dev": "Feature Coding & Unit Tests",
    "tst": "Automated Test & Imp Verification",
    "pre": "Staging E2E & QA Validation (WORKVALI.md)",
    "pro": "Production Release",
}
