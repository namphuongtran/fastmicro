# =============================================================================
# Multi-stage Dockerfile for notification-service
# Event-driven notification delivery (email, SMS, push, webhook)
# =============================================================================

# Stage 1: Builder with uv
FROM python:3.12-slim-bookworm AS builder

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY shared /app/shared
COPY services/notification-service /app/services/notification-service

WORKDIR /app/services/notification-service

ENV UV_PROJECT_ENVIRONMENT=/app/.venv
RUN uv sync --frozen --no-dev --no-editable

# -----------------------------------------------------------------------------
# Stage 2: Runtime
FROM python:3.12-slim-bookworm AS runtime

LABEL maintainer="FastMicro Team" \
      description="Notification Service - event-driven notification delivery" \
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
    curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder --chown=appuser:appgroup /app/.venv /app/.venv
COPY --from=builder --chown=appuser:appgroup /app/services/notification-service/src ./src/

RUN chown -R appuser:appgroup /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/live || exit 1

CMD ["uvicorn", "notification_service.main:create_app", "--host", "0.0.0.0", "--port", "8000", "--factory"]
