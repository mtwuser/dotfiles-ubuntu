.PHONY: help venv install install-dev install-runtime test test-unit test-imp test-e2e test-cov test-all lint format typecheck verify audit layer-list layer-pull-all docker-build docker-self-test docker-mcp clean

export PYTHONDONTWRITEBYTECODE := 1

PYTHON ?= python3
VENV_DIR ?= venv
VENV_BIN := $(VENV_DIR)/bin
DOCKER_IMAGE ?= dotfiles-ubuntu-mcp
DOCKER_TAG ?= $(shell tr -d '[:space:]' < VERSION)
GIT_COMMIT ?= $(shell git rev-parse --short HEAD 2>/dev/null || echo unknown)

help:
	@echo "dotfiles-ubuntu development & verification targets:"
	@echo "  make install          Create ./venv and install requirements-dev.txt (chains -r requirements.txt)"
	@echo "  make install-runtime  Create ./venv and install only runtime base requirements.txt"
	@echo "  make test             Run all unit, implementation, and end-to-end tests"
	@echo "  make test-unit        Run unit tests (tests/unit/)"
	@echo "  make test-imp         Run implementation/integration tests (tests/imp/)"
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
