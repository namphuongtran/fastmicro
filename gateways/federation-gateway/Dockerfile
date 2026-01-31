# =============================================================================
# Multi-stage Dockerfile for federation-gateway
# =============================================================================

# Stage 1: Builder with uv
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy libs to maintain the correct relative path structure
COPY libs/ /app/libs/

# Install dependencies first (better layer caching)
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=gateways/federation-gateway/pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=gateways/federation-gateway/uv.lock,target=uv.lock \
    uv sync --locked --no-install-project --no-dev

# Copy source and install project
COPY gateways/federation-gateway/src/ ./src/
COPY gateways/federation-gateway/pyproject.toml gateways/federation-gateway/uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

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
    APP_ENV=production

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl libpq5 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create non-root user
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

# Copy virtual environment and application from builder
COPY --from=builder --chown=appuser:appgroup /app/.venv /app/.venv
COPY --from=builder --chown=appuser:appgroup /app/src ./src/
COPY --from=builder --chown=appuser:appgroup /app/libs /app/libs

USER appuser

EXPOSE 44381

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:44381/health || exit 1

CMD ["uvicorn", "federation_gateway.main:app", "--host", "0.0.0.0", "--port", "44381"]
