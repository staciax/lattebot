ARG PYTHON_VERSION=3.13

FROM ghcr.io/astral-sh/uv:bookworm-slim AS builder
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Configure the Python directory so it is consistent
ENV UV_PYTHON_INSTALL_DIR /python

# Only use the managed Python version
ENV UV_PYTHON_PREFERENCE=only-managed

# Required for installing Dependencies 
RUN apt-get update && apt-get install -y --no-install-recommends \
		build-essential \
        git \
        ca-certificates \ 
    &&  rm -rf /var/lib/apt/lists/*

# Install Python before the project for caching
RUN uv python install ${PYTHON_VERSION}

WORKDIR /app

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev --no-editable

ADD . /app

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable

FROM debian:bookworm-slim

WORKDIR /app

# Copy the Python version
COPY --from=builder --chown=python:python /python /python
# SSL certificates are required for HTTPS requests
COPY --from=builder --chown=python:python /etc/ssl/certs /etc/ssl/certs 
# For pygit2
COPY --from=builder --chown=python:python /usr/bin/git /usr/bin/git

COPY --from=builder --chown=app:app /app /app

ENV PATH="/app/.venv/bin:$PATH"
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt

CMD ["python", "launcher.py"]

# https://docs.astral.sh/uv/guides/integration/docker
# https://github.com/astral-sh/uv-docker-example