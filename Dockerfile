ARG PYTHON_VERSION=3.13
FROM ghcr.io/astral-sh/uv:python${PYTHON_VERSION}-bookworm-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
		build-essential \
        git \
    &&  rm -rf /var/lib/apt/lists/*

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

# Change the working directory to the `app` directory
WORKDIR /app

# Install the project's dependencies using the lockfile and settings
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev --no-editable --no-group dev

# Copy the project into the intermediate image
ADD . /app

# Sync the project 
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable --no-group dev

FROM python:${PYTHON_VERSION}-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY --from=builder --chown=app:app /app /app
# COPY --from=builder /usr/bin/git /usr/bin/git

ENV PATH="/app/.venv/bin:$PATH"

CMD ["python", "launcher.py"]

# https://docs.astral.sh/uv/guides/integration/docker
# https://github.com/astral-sh/uv-docker-example