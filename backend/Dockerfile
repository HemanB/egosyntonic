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
COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy source
COPY reasoning ./reasoning

# Install the project itself (without dev deps)
RUN uv sync --frozen --no-dev

# Cloud Run sets PORT
ENV PORT=8080
EXPOSE 8080

# Run as non-root
RUN useradd --create-home --shell /bin/bash app && chown -R app:app /app
USER app

CMD ["uv", "run", "uvicorn", "reasoning.main:app", "--host", "0.0.0.0", "--port", "8080", "--proxy-headers", "--forwarded-allow-ips", "*"]
