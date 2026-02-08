"""Worker Service — lightweight health API.

The worker processes tasks via ARQ, but exposes a minimal FastAPI
health endpoint for Kubernetes probes.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from shared.fastapi_utils import create_health_router, register_exception_handlers
from shared.observability import configure_structlog, configure_tracing, get_structlog_logger

from worker_service.configs.settings import get_settings

logger = get_structlog_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan."""
    settings = get_settings()
    configure_structlog(service_name=settings.service_name)
    configure_tracing(
        service_name=settings.service_name,
        endpoint=settings.otlp_endpoint,
    )
    logger.info("Worker health API starting", port=settings.port)
    yield
    logger.info("Worker health API shutting down")


def create_app() -> FastAPI:
    """Application factory — health endpoint only."""
    app = FastAPI(
        title="Worker Service",
        description="Background task processor — health endpoint",
        version="0.1.0",
        lifespan=lifespan,
        docs_url=None,
        openapi_url=None,
    )
    register_exception_handlers(app)
    app.include_router(create_health_router())
    return app
