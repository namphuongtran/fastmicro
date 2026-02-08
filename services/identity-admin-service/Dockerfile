FROM python:3.12-slim AS builder

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy shared library first
COPY shared /app/shared

# Copy service
COPY services/identity-admin-service /app/services/identity-admin-service

WORKDIR /app/services/identity-admin-service

# Install into /app/.venv so shebangs are correct after COPY to runtime stage
ENV UV_PROJECT_ENVIRONMENT=/app/.venv
RUN uv sync --frozen --no-dev --no-editable

# Production image
FROM python:3.12-slim

WORKDIR /app

# Create non-root user
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

# Install curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl && rm -rf /var/lib/apt/lists/*

# Copy installed packages and application
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/services/identity-admin-service/src /app/src
COPY --from=builder /app/services/identity-admin-service/templates /app/templates
COPY --from=builder /app/services/identity-admin-service/static /app/static

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src"
ENV PYTHONUNBUFFERED=1
ENV APP_ENV=production
ENV APP_PORT=8000

# Change ownership to non-root user
RUN chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000

# Health check - use port 8000 (internal container port)
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "-m", "uvicorn", "identity_admin_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
