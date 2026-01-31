# =============================================================================
# Multi-stage Dockerfile for audit-service
# =============================================================================
# Stage 1: Builder - Install dependencies and build the application
# Stage 2: Runtime - Minimal image for production
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Builder
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies for building
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry==1.8.5

# Set working directory
WORKDIR /app

# Copy dependency files first (for better layer caching)
COPY services/audit-service/pyproject.toml services/audit-service/poetry.lock* ./
COPY shared/ /shared/

# Configure Poetry to not create virtual environment (we're in container)
RUN poetry config virtualenvs.create false

# Install dependencies (production only)
RUN poetry install --no-interaction --no-ansi --only main --no-root

# Copy application source
COPY services/audit-service/src/ ./src/

# Install the application
RUN poetry install --no-interaction --no-ansi --only main

# -----------------------------------------------------------------------------
# Stage 2: Runtime
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

# Labels for container metadata
LABEL maintainer="Nam Tran <nam.tranphuong@outlook.com>" \
      description="Audit Service - Event logging and compliance tracking" \
      version="0.1.0"

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
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

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --from=builder /app/src ./src/

# Copy shared library
COPY --from=builder /shared /shared

# Change ownership to non-root user
RUN chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Expose the application port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "audit_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
