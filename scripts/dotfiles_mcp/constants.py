"""Constants, thresholds, and compiled regular expressions for dotfiles-ubuntu MCP.

Specification: docs/architecture/03_contextual_mcp_and_federation.md
"""

from __future__ import annotations

import re
import stat
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parents[2]
MCP_JSONRPC_PROTOCOL_REV = "2024-11-05"
LAYER_MANIFEST_CONTRACT_REV = "mcp-layer-v1"
TEMPLATE_MANIFEST_CONTRACT_REV = "template-pack-v1"
MISSING_VERSION_SENTINEL = "unversioned"
VALID_LAYER_ROLES = (
    "corporate", "department", "domain-policy", "ephemeral-bot",
    "squad", "service-node", "environment-cluster", "workstation",
)  # fmt: skip
MCP_OPERATING_MODES: dict[str, str] = {
    "oss-readonly-appliance": "workstation-baseline-provider",
    "oss-dev": "self-test-and-dev-only",
    "corporate-root": "enterprise-governance-hub",
    "domain-policy": "departmental-policy-hub",
    "department": "departmental-policy-hub",
    "squad": "squad-execution-hub",
    "service-node": "infrastructure-node-provider",
    "environment-cluster": "infrastructure-node-provider",
    "ephemeral-bot": "scoped-ephemeral-sandbox",
    "project": "project-consumer-only",
}
VALID_ENVIRONMENTS = ("dev", "tst", "pre", "pro")
DEFAULT_PROTECTED_BRANCHES: tuple[str, ...] = (
    "main", "master", "env/tst", "env/pre", "env/pro",
)  # fmt: skip
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
VALID_SYNC_STRATEGIES: tuple[str, ...] = ("reconcile", "accept-upstream", "keep-local", "merge")
MAKEFILE_ROLE_HEADER_PREFIX: str = "# Role-Specialized Layer Makefile"
MAKEFILE_CUSTOM_TARGETS_MARKER: str = "# --- Custom Targets ---"
VALID_ROSTER_ROLES: tuple[str, ...] = ("owner", "maintainer", "validator", "member")
VALID_TRACKER_FILES: tuple[str, ...] = (
    "WORKTASK.md", "BACKLOG.md", "WORKROAD.md", "ROADMAP.md", "WORKVALI.md",
)  # fmt: skip
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
FORK_ID_HASH_HEX_LEN = 8
CAPSULE_DIGEST_HEX_LEN = 16
CAPSULE_HMAC_HEX_LEN = 24
CAPSULE_ALERT_PREFIX_CHARS = 32
CAPSULE_BRIEF_PREVIEW_CHARS = 48
SHA256_BLOCK_BYTES = 32
ZLIB_MAX_COMPRESSION_LEVEL = 9
EPOCH_DECIMAL_PLACES = 3
CHARS_PER_TOKEN_ESTIMATE = 4
CODON_SLUG_MAX_CHARS = 36
CODON_MAX_SEMANTIC_TAGS = 5
EXON_HEADING_MAX_CHARS = 160
EXON_BULLET_MAX_CHARS = 120
EXON_MAX_BULLETS = 4
L1_FALLBACK_EST_TOKENS = 60
L2_EXCERPT_MAX_CHARS = 1500
L2_SECTION_MAX_CHARS = 8000
L3_EXCERPT_MAX_CHARS = 4000
MAX_UNFOLDED_L3_LINKS = 5
MAX_QUERY_GOVERNANCE_MATCHES = 15
MAX_SURFACE_SECTIONS_PER_RULE = 3
MAX_BRIEF_INVARIANTS = 8
SPECIFICITY_WEIGHT_TRAIT = 4
SPECIFICITY_WEIGHT_SCOPE = 3
SPECIFICITY_WEIGHT_PLANE = 2
SPECIFICITY_WEIGHT_GLOB = 1
MAX_RECOMMENDED_MCP_FANOUT = 3
DIAGNOSTICS_RECENT_ALERTS_LIMIT = 5
DIAGNOSTICS_RECENT_EVENTS_LIMIT = 10
MS_PER_SECOND = 1000
JSONRPC_PARSE_ERROR = -32700
JSONRPC_METHOD_NOT_FOUND = -32601
JSONRPC_INVALID_PARAMS = -32602
JSONRPC_INTERNAL_ERROR = -32603
TEMPLATE_STACK_GROUP_DIRS = ("business-stack", "squad-stack", "tech-stack")
PRUNABLE_STARTER_TEMPLATES = (
    "agile-task-branch", "business-base", "corporate-ops-ledger",
    "fastapi-hexagonal", "human-core", "technical-base",
)  # fmt: skip
BUSINESS_MODE_TEMPLATES = ("business-base", "corporate-ops-ledger")
BUSINESS_MODE_RULE_FILES = ("business-base.md", "ops-ledger-architecture.md")
TECHNICAL_MODE_TEMPLATES = ("technical-base", "fastapi-hexagonal")
TECHNICAL_MODE_RULE_FILES = ("technical-base.md", "coding.md")
VALID_TEMPLATE_KINDS = (
    "core-base", "business-stack", "squad-stack", "tech-stack",
    "stack-starter", "domain-policy-pack", "department-pack", "project-overlay",
)  # fmt: skip
ROLE_DEFAULT_PRECEDENCE: dict[str, int] = {
    "domain-policy": 5,
    "corporate": 10,
    "workstation": 10,
    "ephemeral-bot": 15,
    "bridge": 20,
    "department": 30,
    "squad": 50,
    "service-node": 60,
    "environment-cluster": 70,
    "project": 80,
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
STRUCTURAL_PATH_SEGMENTS = frozenset({
    "src", "app", "internal", "pkg", "lib", "templates", "static", "partials", "components",
    "css", "js", "tests", "unit", "imp", "e2e", "docs", "architecture", "reference",
})  # fmt: skip
CAPSULE_PREFIX = "rcap1"
VALID_BINDING_MODES = ("authoritative", "transversal")
VALID_RESOLUTIONS = ("L0", "L1", "L2")
VALID_CAPSULE_LEVELS = ("L0", "L1", "L2", "L3")
VALID_AGENT_TIERS = ("flash", "inherit", "pro")
VALID_EPHEMERAL_ACTIONS = ("spawn", "inspect", "evaluate", "reap")
VALID_EPHEMERAL_SCOPES: tuple[str, ...] = ("inter-layer", "intra-layer")
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
    "README.md", "CHANGELOG.md", "CONTRIBUTING.md", "SECURITY.md",
    "ACCESSIBILITY.md", "CODE_OF_CONDUCT.md", "VERSION",
}  # fmt: skip
ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")
KEBAB_ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
MATERIALIZED_RULE_RE = re.compile(r"^layer-(\d{2})-([a-z0-9-]+)\.md$")
MD_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
BACKTICK_PATH_RE = re.compile(r"`([a-zA-Z0-9_./-]+\.(?:md|html|j2|css))`")
BOLD_TERM_RE = re.compile(r"\*\*([^*]{3,40})\*\*")
WORD_TOKEN_RE = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_-]{2,}")
CODON_STOPWORDS = frozenset({
    "the", "and", "for", "with", "that", "this", "from", "are", "must",
    "never", "when", "all", "any", "not", "use", "only", "into", "over",
})  # fmt: skip
CONSUMER_ALLOWED_OPS: tuple[str, ...] = (
    "list-templates", "apply-project", "sync-layer", "diff-project", "promote-from-project",
    "check-authority", "inspect-horizon", "start-task", "complete-task",
    "compare-upstream", "consult-layer",
)  # fmt: skip
VALIDATOR_ALLOWED_OPS: tuple[str, ...] = ("check-env-promotion", "record-decision")
MAINTAINER_ALLOWED_OPS: tuple[str, ...] = (
    "scaffold-template", "manage-roster", "configure-git-policy", "delegate-to-child",
)  # fmt: skip
OWNER_RESTRICTED_OPS: tuple[str, ...] = (
    "init-fork", "scaffold-template", "register-subtree", "set-authority", "manage-roster",
    "configure-git-policy", "delegate-to-child", "release", "commit-layer", "push-layer",
)  # fmt: skip
_WORKSTATION_DEV_TARGETS: tuple[str, ...] = (
    "status", "setup-dev", "verify", "audit", "test", "test-unit",
    "test-imp", "test-e2e", "lint", "format", "workstation-sync", "docker-build",
)  # fmt: skip
_FULL_LAYER_TARGETS: tuple[str, ...] = (
    "status", "setup-dev", "task", "complete", "consult", "horizon", "sync", "upstream-diff",
    "diff", "authority", "roster", "env-gate", "decision", "promote", "delegate", "mcp-test",
)  # fmt: skip
LAYER_ROLE_MAKEFILE_TARGETS: dict[str, tuple[str, ...]] = {
    "workstation": _WORKSTATION_DEV_TARGETS,
    "corporate": tuple(t for t in _FULL_LAYER_TARGETS if t != "complete"),
    "domain-policy": _FULL_LAYER_TARGETS,
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
    "setup-dev": f"{_CLI_RUN} apply-project $(CURDIR) --template technical-base --include-defaults",
    "task": (
        f'{_CLI_RUN} start-task $(CURDIR) --task "$(TASK)" $(if $(TICKET),--ticket $(TICKET),)'
    ),
    "complete": f'{_CLI_RUN} complete-task {_PF} --task "$(TASK)"',
    "consult": f'{_CLI_RUN} consult-layer $(CURDIR) --layer $(LAYER) --query "$(QUERY)"',
    "horizon": f"{_CLI_RUN} inspect-horizon {_PF}",
    "sync": f"{_CLI_RUN} sync-layer {_PF} $(if $(STRATEGY),--strategy $(STRATEGY),)",
    "upstream-diff": f"{_CLI_RUN} compare-upstream {_PF}",
    "diff": f"{_CLI_RUN} diff-project {_PF}",
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
    "promote": (
        f"{_CLI_RUN} promote-from-project $(CURDIR) --source $(SOURCE) "
        "$(if $(TEMPLATE),--to-template $(TEMPLATE),) $(PR_FLAGS)"
    ),
    "delegate": (
        f'{_CLI_RUN} delegate-to-child $(CURDIR) --to-child $(CHILD) --task "$(TASK)" '
        "$(if $(TICKET),--ticket $(TICKET),) $(if $(PRIORITY),--priority $(PRIORITY),) "
        "$(if $(SURFACE),--surface $(SURFACE),) $(if $(SOURCE),--source $(SOURCE),) "
        "$(if $(CREATE_PR),--create-pr,)"
    ),
    "mcp-test": f"{_CLI_RUN} list-templates $(CURDIR)",
}
GENERIC_LAYER_TOKENS: frozenset[str] = frozenset({
    "root", "corp", "corporate", "dept", "department", "team", "squad", "layer", "base",
    "pack", "policy", "project", "enterprise", "acme", "demo", "test", "tech", "legal",
    "finance", "supply", "design", "brand", "marketing", "social", "growth", "safety",
    "human", "core", "technical", "business",
})  # fmt: skip
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
