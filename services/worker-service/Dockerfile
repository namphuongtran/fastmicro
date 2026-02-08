# =============================================================================
# Multi-stage Dockerfile for worker-service
# Background task processing via ARQ + health API
# =============================================================================

# Stage 1: Builder with uv
FROM python:3.12-slim-bookworm AS builder

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY shared /app/shared
COPY services/worker-service /app/services/worker-service

WORKDIR /app/services/worker-service

ENV UV_PROJECT_ENVIRONMENT=/app/.venv
RUN uv sync --frozen --no-dev --no-editable

# -----------------------------------------------------------------------------
# Stage 2: Runtime
FROM python:3.12-slim-bookworm AS runtime

LABEL maintainer="FastMicro Team" \
      description="Worker Service - async background task processing" \
      version="0.1.0"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    PATH="/app/.venv/bin:$PATH" \
    APP_ENV=production

RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl libpq5 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder --chown=appuser:appgroup /app/.venv /app/.venv
COPY --from=builder --chown=appuser:appgroup /app/services/worker-service/src ./src/

RUN chown -R appuser:appgroup /app
USER appuser

# ARQ worker has no HTTP server; health is monitored via Redis connection
# For Kubernetes, use a sidecar or exec-based liveness probe
CMD ["arq", "worker_service.worker.WorkerSettings"]
