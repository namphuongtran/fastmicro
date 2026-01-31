# =============================================================================
# Multi-stage Dockerfile for identity-service
# Enterprise Identity Provider - OAuth 2.0 / OpenID Connect Server
# =============================================================================

# Stage 1: Builder with uv
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies first (better layer caching)
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=services/identity-service/pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=services/identity-service/uv.lock,target=uv.lock \
    --mount=type=bind,source=shared/,target=/shared/ \
    uv sync --locked --no-install-project --no-dev

# Copy source and install project
COPY services/identity-service/src/ ./src/
COPY services/identity-service/templates/ ./templates/
COPY services/identity-service/static/ ./static/
COPY shared/ /shared/
COPY services/identity-service/pyproject.toml services/identity-service/uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

# -----------------------------------------------------------------------------
# Stage 2: Runtime
FROM python:3.12-slim-bookworm AS runtime

LABEL maintainer="Nam Tran <nam.tranphuong@outlook.com>" \
      description="Identity Service - OAuth 2.0 / OpenID Connect Provider" \
      version="0.1.0"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    PATH="/app/.venv/bin:$PATH" \
    APP_ENV=production \
    APP_PORT=8000

RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl libpq5 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy virtual environment and application from builder
COPY --from=builder --chown=appuser:appgroup /app/.venv /app/.venv
COPY --from=builder --chown=appuser:appgroup /app/src ./src/
COPY --from=builder --chown=appuser:appgroup /app/templates ./templates/
COPY --from=builder --chown=appuser:appgroup /app/static ./static/
COPY --from=builder --chown=appuser:appgroup /shared /shared

# Create directory for RSA keys
RUN mkdir -p /app/keys && chown -R appuser:appgroup /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "identity_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
