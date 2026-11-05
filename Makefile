.PHONY: help status task complete consult horizon sync diff promote delegate decision venv install install-dev install-runtime setup-dev reset-dev publish-oss workstation-setup workstation-sync workstation-status test test-unit test-imp test-e2e test-cov test-all lint format typecheck verify audit layer-list layer-pull-all docker-build docker-self-test docker-mcp clean

export PYTHONDONTWRITEBYTECODE := 1

PYTHON ?= python3
VENV_DIR ?= venv
VENV_BIN := $(VENV_DIR)/bin
DOCKER_IMAGE ?= dotfiles-ubuntu-mcp
DOCKER_TAG ?= $(shell tr -d '[:space:]' < VERSION)
GIT_COMMIT ?= $(shell git rev-parse --short HEAD 2>/dev/null || echo unknown)

help:
	@echo "dotfiles-ubuntu development & verification targets:"
	@echo "  make install            Create ./venv and install requirements-dev.txt (chains -r requirements.txt)"
	@echo "  make setup-dev          Clean .agents/ residue and materialize clean software-engineering dev environment"
	@echo "  make reset-dev          Alias for make setup-dev (purge local fork test residue & restore dev baseline)"
	@echo "  make publish-oss        Export clean tracker-free Open-Source release to upstream"
	@echo "  make workstation-setup  Configure local workstation runtime (private/readonly mode, human-base, boot auto-sync)"
	@echo "  make workstation-sync   Sync workstation runtime (origin -> upstream OSS -> clean committed local dev) and re-stow"
	@echo "  make workstation-status Show local workstation configuration and runtime status JSON"
	@echo "  make status             Show consolidated workspace status digest (./scripts/layer-config.sh status)"
	@echo "  make task               Claim a task in WORKTASK.md and emit feature branch (TASK=\"<query>\")"
	@echo "  make complete           Mark task [x] in WORKTASK.md (TASK=\"<query>\")"
	@echo "  make consult            Run zero-residue read-only consultation (LAYER=<id> QUERY=\"<text>\")"
	@echo "  make horizon            Inspect 1-hop upstream/downstream horizon radar"
	@echo "  make sync               Synchronize layer templates and mounted subtrees"
	@echo "  make diff               Compare workspace .agents/ against governing layers"
	@echo "  make promote            Promote workspace asset upward (SOURCE=<rel-path>)"
	@echo "  make delegate           Delegate 1-hop directive into layers/<child>/ (CHILD=<id> TASK=\"<text>\")"
	@echo "  make decision           Record governance decision (ITEM=\"<ref>\" DEC=approve|reject REASON=\"<text>\")"
	@echo "  make install-runtime    Create ./venv and install only runtime base requirements.txt"
	@echo "  make test             Run all unit, implementation, and end-to-end tests"
	@echo "  make test-unit        Run unit tests (tests/unit/)"
	@echo "  make test-imp         Run implementation tests (tests/imp/)"
	@echo "  make test-e2e         Run end-to-end chained MCP & hook lifecycle tests (tests/e2e/)"
	@echo "  make test-cov         Run full test suite with 100% branch coverage gate"
	@echo "  make lint             Run ruff check and mypy --strict"
	@echo "  make format           Auto-format Python files with ruff format & ruff check --fix"
	@echo "  make verify           Run full repository & CI verification suite (./scripts/verify-repo.sh)"
	@echo "  make audit            Run read-only system & symlink drift audit (./audit.sh)"
	@echo "  make layer-list       List mounted git subtree context layers (./scripts/layer-subtree.sh list)"
	@echo "  make layer-pull-all   Pull latest changes across all mounted layers/* subtrees"
	@echo "  make docker-build     Build the hermetic Ubuntu 26.04 MCP container image ($(DOCKER_IMAGE):$(DOCKER_TAG))"
	@echo "  make docker-self-test Run in-container MCP self-test (--read-only --network=none)"
	@echo "  make docker-mcp       Start interactive stdio MCP server inside hardened container"
	@echo "  make clean            Remove caches, coverage artifacts, and runtime logs"

$(VENV_BIN)/pytest:
	$(PYTHON) -m venv $(VENV_DIR)
	$(VENV_BIN)/pip install --upgrade pip -q
	$(VENV_BIN)/pip install -r requirements-dev.txt -q

venv install install-dev: $(VENV_BIN)/pytest

setup-dev reset-dev: $(VENV_BIN)/pytest
	rm -rf $(CURDIR)/.agents/rules $(CURDIR)/.agents/skills $(CURDIR)/.agents/assets $(CURDIR)/.agents/proposals $(CURDIR)/WORKVALI.md
	./scripts/layer-config.sh apply-project $(CURDIR) --template software-engineering

publish-oss:
	./scripts/workstation-sync.sh --publish-oss $(if $(RELEASE_VERSION),--release-version $(RELEASE_VERSION),$(if $(CREATE_PR),--create-pr,--dry-run))

workstation-setup:
	./scripts/workstation-sync.sh --setup

workstation-sync:
	./scripts/workstation-sync.sh --sync

workstation-status:
	./scripts/workstation-sync.sh --status

status:
	./scripts/layer-config.sh status $(CURDIR)

task:
	./scripts/layer-config.sh start-task $(CURDIR) --task "$(TASK)" $(if $(TICKET),--ticket $(TICKET),)

complete:
	./scripts/layer-config.sh complete-task $(CURDIR) $(if $(PARENT_SYNC),--parent-dir $(PARENT_DIR),) --task "$(TASK)" $(if $(DELIVERABLE),--deliverable "$(DELIVERABLE)",) $(if $(SUMMARY),--summary "$(SUMMARY)",) $(if $(CREATE_PR),--create-pr,)

consult:
	./scripts/layer-config.sh consult-layer $(CURDIR) --layer $(LAYER) --query "$(QUERY)" $(if $(PATH_TARGET),--path $(PATH_TARGET),) $(if $(TIER),--tier $(TIER),)

horizon:
	./scripts/layer-config.sh inspect-horizon $(CURDIR)

sync:
	./scripts/layer-config.sh sync-layer $(CURDIR) $(if $(STRATEGY),--strategy $(STRATEGY),)

diff:
	./scripts/layer-config.sh diff-project $(CURDIR)

promote:
	./scripts/layer-config.sh promote-from-project $(CURDIR) --source $(SOURCE) $(if $(TARGET_REPO),--upstream-dir $(TARGET_REPO),) $(if $(LAYER),--to-layer $(LAYER),) $(if $(TEMPLATE),--to-template $(TEMPLATE),) $(PR_FLAGS)

delegate:
	./scripts/layer-config.sh delegate-to-child $(CURDIR) --to-child $(CHILD) --task "$(TASK)" $(if $(TICKET),--ticket $(TICKET),) $(if $(PRIORITY),--priority $(PRIORITY),) $(if $(SURFACE),--surface $(SURFACE),) $(if $(SOURCE),--source $(SOURCE),) $(if $(CREATE_PR),--create-pr,)

decision:
	./scripts/layer-config.sh record-decision $(CURDIR) --item "$(ITEM)" --decision $(DEC) --reason "$(REASON)"

install-runtime:
	$(PYTHON) -m venv $(VENV_DIR)
	$(VENV_BIN)/pip install --upgrade pip -q
	$(VENV_BIN)/pip install -r requirements.txt -q

test: $(VENV_BIN)/pytest
	$(VENV_BIN)/pytest tests/unit/ tests/imp/ tests/e2e/

test-unit: $(VENV_BIN)/pytest
	$(VENV_BIN)/pytest tests/unit/

test-imp: $(VENV_BIN)/pytest
	$(VENV_BIN)/pytest tests/imp/

test-e2e: $(VENV_BIN)/pytest
	$(VENV_BIN)/pytest tests/e2e/

test-cov test-all: $(VENV_BIN)/pytest
	$(VENV_BIN)/pytest tests/unit/ tests/imp/ tests/e2e/ --cov --cov-report=term-missing --cov-branch --no-cov-on-fail

lint: $(VENV_BIN)/pytest
	$(VENV_BIN)/ruff check antigravity/.gemini/config/scripts/ scripts/ tests/
	$(VENV_BIN)/mypy antigravity/.gemini/config/scripts/ scripts/ tests/

typecheck: $(VENV_BIN)/pytest
	$(VENV_BIN)/mypy antigravity/.gemini/config/scripts/ scripts/ tests/

format: $(VENV_BIN)/pytest
	$(VENV_BIN)/ruff format antigravity/.gemini/config/scripts/ scripts/ tests/
	$(VENV_BIN)/ruff check --fix antigravity/.gemini/config/scripts/ scripts/ tests/

verify:
	./scripts/verify-repo.sh

audit:
	./audit.sh

layer-list:
	./scripts/layer-subtree.sh list

layer-pull-all:
	./scripts/layer-subtree.sh pull-all

docker-build:
	docker build --build-arg GIT_COMMIT=$(GIT_COMMIT) -t $(DOCKER_IMAGE):$(DOCKER_TAG) -t $(DOCKER_IMAGE):latest .

docker-self-test:
	docker run --rm --read-only --network=none --cap-drop=ALL $(DOCKER_IMAGE):latest --self-test --no-log

docker-mcp:
	docker run -i --rm --read-only --network=none --cap-drop=ALL $(DOCKER_IMAGE):latest --no-log

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov logs
	find . -path "./$(VENV_DIR)" -prune -o -type d -name "__pycache__" -prune -exec rm -rf {} +
