# =============================================================================
# Multi-stage Dockerfile for metastore-service
# =============================================================================

FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl && rm -rf /var/lib/apt/lists/*

RUN pip install poetry==1.8.5

WORKDIR /app

COPY services/metastore-service/pyproject.toml services/metastore-service/poetry.lock* ./
COPY shared/ /shared/

RUN poetry config virtualenvs.create false
RUN poetry install --no-interaction --no-ansi --only main --no-root

COPY services/metastore-service/src/ ./src/
RUN poetry install --no-interaction --no-ansi --only main

# -----------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

LABEL maintainer="Nam Tran <nam.tranphuong@outlook.com>" \
      description="Metastore Service - Metadata and configuration management" \
      version="0.1.0"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    APP_ENV=production \
    APP_PORT=8000

RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app/src ./src/
COPY --from=builder /shared /shared

RUN chown -R appuser:appgroup /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "metastore_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
