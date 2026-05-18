# Build context: repo ROOT (not backend/). This is so we can include
# shared/vocabularies and shared/schemas, which the backend reads at runtime.
#
# Build command (from repo root):
#   docker build -f backend/Dockerfile -t egosyntonic-reasoning .

# syntax=docker/dockerfile:1.7
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# uv for fast, lockfile-based installs
COPY --from=ghcr.io/astral-sh/uv:0.5.4 /uv /usr/local/bin/uv

WORKDIR /app

# Install deps first for better layer caching
COPY backend/pyproject.toml backend/uv.lock* ./
RUN uv sync --frozen --no-dev --no-install-project 2>/dev/null \
    || uv sync --no-dev --no-install-project

# Copy backend source
COPY backend/reasoning ./reasoning

# Copy shared/ — the backend resolves vocabularies relative to ../../shared
# from reasoning/. In Docker we recreate the same layout.
COPY shared /shared

# Install the project itself
RUN uv sync --no-dev 2>/dev/null || true

# Cloud Run sets PORT
ENV PORT=8080
EXPOSE 8080

# Run as non-root
RUN useradd --create-home --shell /bin/bash app && chown -R app:app /app /shared
USER app

CMD ["uv", "run", "uvicorn", "reasoning.main:app", "--host", "0.0.0.0", "--port", "8080", "--proxy-headers", "--forwarded-allow-ips", "*"]
