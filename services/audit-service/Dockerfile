# =============================================================================
# Multi-stage Dockerfile for audit-service
# =============================================================================
# Stage 1: Builder - Install dependencies with uv
# Stage 2: Runtime - Minimal image for production
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Builder with uv
# -----------------------------------------------------------------------------
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

# Set environment variables
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

# Install system dependencies for building
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install dependencies first (better layer caching)
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=services/audit-service/pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=services/audit-service/uv.lock,target=uv.lock \
    --mount=type=bind,source=shared/,target=/shared/ \
    uv sync --locked --no-install-project --no-dev

# Copy source and install project
COPY services/audit-service/src/ ./src/
COPY shared/ /shared/
COPY services/audit-service/pyproject.toml services/audit-service/uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

# -----------------------------------------------------------------------------
# Stage 2: Runtime
# -----------------------------------------------------------------------------
FROM python:3.12-slim-bookworm AS runtime

# Labels for container metadata
LABEL maintainer="Nam Tran <nam.tranphuong@outlook.com>" \
      description="Audit Service - Event logging and compliance tracking" \
      version="0.1.0"

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    PATH="/app/.venv/bin:$PATH" \
    APP_ENV=production \
    APP_PORT=8000

# Create non-root user for security
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Set working directory
WORKDIR /app

# Copy virtual environment and application from builder
COPY --from=builder --chown=appuser:appgroup /app/.venv /app/.venv
COPY --from=builder --chown=appuser:appgroup /app/src ./src/
COPY --from=builder --chown=appuser:appgroup /shared /shared

# Switch to non-root user
USER appuser

# Expose the application port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "audit_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
