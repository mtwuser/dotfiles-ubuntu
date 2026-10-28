# syntax=docker/dockerfile:1
# ==============================================================================
# dotfiles-ubuntu — Contextual MCP Server & Multi-Layer Governance Image
# ==============================================================================
# Supports two primary container architectures:
#   1. Standalone Hermetic MCP Hub (stdio via 'docker run -i --rm'):
#        docker run -i --rm --read-only --network=none dotfiles-ubuntu-mcp:latest
#   2. Multi-Stage Sidecar Layer Injection into Microservice Images:
#        COPY --from=dotfiles-ubuntu-mcp:latest /opt/dotfiles-ubuntu /opt/dotfiles-ubuntu
# ==============================================================================

FROM ubuntu:26.04

LABEL org.opencontainers.image.title="dotfiles-ubuntu-mcp" \
      org.opencontainers.image.description="Declarative Ubuntu 26.04 LTS & Google Antigravity 2.0 Contextual MCP Server" \
      org.opencontainers.image.source="https://github.com/mtwuser/dotfiles-ubuntu" \
      org.opencontainers.image.licenses="MIT"

ARG DEBIAN_FRONTEND=noninteractive
ARG INSTALL_RUNTIME_DEPS="false"

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        git \
        python3 \
    && if [ "$INSTALL_RUNTIME_DEPS" = "true" ]; then \
        apt-get install -y --no-install-recommends python3-pip python3-venv; \
    fi \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/dotfiles-ubuntu
COPY . /opt/dotfiles-ubuntu/

ARG GIT_COMMIT="unknown"
ARG LAYER_ID=""
ARG LAYER_ROLE=""
ARG MCP_ENV=""

RUN mkdir -p /opt/dotfiles-ubuntu/logs \
    && chmod +x /opt/dotfiles-ubuntu/bootstrap.sh \
                /opt/dotfiles-ubuntu/backup.sh \
                /opt/dotfiles-ubuntu/audit.sh \
                /opt/dotfiles-ubuntu/scripts/*.sh \
                /opt/dotfiles-ubuntu/scripts/*.py \
                /opt/dotfiles-ubuntu/antigravity/.gemini/config/scripts/*.py \
    && if [ "$INSTALL_RUNTIME_DEPS" = "true" ]; then \
        python3 -m venv /opt/dotfiles-venv && \
        /opt/dotfiles-venv/bin/pip install --no-cache-dir -r /opt/dotfiles-ubuntu/requirements.txt && \
        if [ -n "$MCP_ENV" ] && [ -f "/opt/dotfiles-ubuntu/requirements-${MCP_ENV}.txt" ]; then \
            /opt/dotfiles-venv/bin/pip install --no-cache-dir -r "/opt/dotfiles-ubuntu/requirements-${MCP_ENV}.txt"; \
        fi; \
    fi \
    && chown -R ubuntu:ubuntu /opt/dotfiles-ubuntu/logs

ENV PATH="/opt/dotfiles-venv/bin:${PATH}" \
    DOTFILES_REPO_DIR="/opt/dotfiles-ubuntu" \
    DOTFILES_MCP_LOG_DIR="/opt/dotfiles-ubuntu/logs" \
    DOTFILES_GIT_COMMIT="${GIT_COMMIT}" \
    DOTFILES_LAYER_ID="${LAYER_ID}" \
    DOTFILES_LAYER_ROLE="${LAYER_ROLE}" \
    PYTHONDONTWRITEBYTECODE="1" \
    PYTHONUNBUFFERED="1"

# Build-time verification gate: ensure MCP server and subtree orchestrator pass self-tests
RUN python3 /opt/dotfiles-ubuntu/scripts/dotfiles_mcp_server.py --self-test --no-log >/dev/null \
    && /opt/dotfiles-ubuntu/scripts/layer-subtree.sh list >/dev/null

USER ubuntu

ENTRYPOINT ["python3", "/opt/dotfiles-ubuntu/scripts/dotfiles_mcp_server.py"]
