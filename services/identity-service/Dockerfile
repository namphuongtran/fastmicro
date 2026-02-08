# =============================================================================
# Multi-stage Dockerfile for identity-service
# Enterprise Identity Provider - OAuth 2.0 / OpenID Connect Server
# =============================================================================

# Stage 1: Builder with uv
FROM python:3.12-slim-bookworm AS builder

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy shared library first (maintains relative path structure)
COPY shared /app/shared

# Copy service files
COPY services/identity-service /app/services/identity-service

WORKDIR /app/services/identity-service

# Install into /app/.venv so shebangs are correct after COPY to runtime stage
ENV UV_PROJECT_ENVIRONMENT=/app/.venv
RUN uv sync --frozen --no-dev --no-editable

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
COPY --from=builder --chown=appuser:appgroup /app/services/identity-service/src ./src/
COPY --from=builder --chown=appuser:appgroup /app/services/identity-service/templates ./templates/
COPY --from=builder --chown=appuser:appgroup /app/services/identity-service/static ./static/

# Create directory for RSA keys
RUN mkdir -p /app/keys && chown -R appuser:appgroup /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "identity_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
