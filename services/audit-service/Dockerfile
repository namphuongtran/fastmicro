# =============================================================================
# Multi-stage Dockerfile for audit-service
# =============================================================================
# Stage 1: Builder - Install dependencies with uv
# Stage 2: Runtime - Minimal image for production
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Builder with uv
# -----------------------------------------------------------------------------
FROM python:3.12-slim-bookworm AS builder

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy shared library first (maintains relative path structure)
COPY shared /app/shared

# Copy service files
COPY services/audit-service /app/services/audit-service

WORKDIR /app/services/audit-service

# Install into /app/.venv so shebangs are correct after COPY to runtime stage
ENV UV_PROJECT_ENVIRONMENT=/app/.venv
RUN uv sync --frozen --no-dev --no-editable

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
COPY --from=builder --chown=appuser:appgroup /app/services/audit-service/src ./src/

# Switch to non-root user
USER appuser

# Expose the application port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "audit_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
