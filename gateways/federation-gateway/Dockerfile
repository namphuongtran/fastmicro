# =============================================================================
# Multi-stage Dockerfile for federation-gateway
# =============================================================================

# Stage 1: Builder with uv
FROM python:3.12-slim-bookworm AS builder

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy shared library first (maintains relative path structure)
COPY shared /app/shared

# Copy gateway files
COPY gateways/federation-gateway /app/gateways/federation-gateway

WORKDIR /app/gateways/federation-gateway

# Install dependencies (frozen allows minor lock differences)
RUN uv sync --frozen --no-dev

# -----------------------------------------------------------------------------
# Stage 2: Runtime
FROM python:3.12-slim-bookworm AS runtime

LABEL maintainer="Nam Tran <nam.tranphuong@outlook.com>" \
      description="Federation Gateway - API Gateway for microservices" \
      version="0.1.0"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    PATH="/app/.venv/bin:$PATH" \
    APP_ENV=production \
    APP_PORT=8000

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl libpq5 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create non-root user
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

# Copy virtual environment and application from builder
COPY --from=builder --chown=appuser:appgroup /app/gateways/federation-gateway/.venv /app/.venv
COPY --from=builder --chown=appuser:appgroup /app/gateways/federation-gateway/src ./src/

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "federation_gateway.main:app", "--host", "0.0.0.0", "--port", "8000"]
