"""Notification Service — FastAPI application entry point.

Combines a lightweight health/admin API with a RabbitMQ event consumer
that dispatches notifications through configured channels.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from shared.fastapi_utils import (
    RequestContextMiddleware,
    create_health_router,
    register_exception_handlers,
)
from shared.observability import (
    RequestLoggingMiddleware,
    configure_structlog,
    configure_tracing,
    get_structlog_logger,
)
from shared.observability.structlog_config import LoggingConfig
from shared.observability.tracing import TracingConfig

from notification_service.configs.settings import get_settings

logger = get_structlog_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: startup and shutdown hooks."""
    settings = get_settings()
    configure_structlog(LoggingConfig(
        service_name=settings.service_name,
        log_level=settings.log_level,
    ))
    configure_tracing(TracingConfig(
        service_name=settings.service_name,
        exporter_endpoint=settings.otlp_endpoint,
    ))
    logger.info(
        "Notification Service starting",
        service_name=settings.service_name,
        port=settings.port,
    )
    # TODO: start RabbitMQ consumer in background task
    yield
    # TODO: stop RabbitMQ consumer gracefully
    logger.info("Notification Service shutting down")


def create_app() -> FastAPI:
    """Application factory."""
    settings = get_settings()

    app = FastAPI(
        title="Notification Service",
        description="Event-driven notification delivery (email, SMS, push, webhook)",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/api/v1/docs",
        openapi_url="/api/v1/openapi.json",
    )

    # Middleware
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(RequestLoggingMiddleware)

    # Exception handlers
    register_exception_handlers(app)

    # Health checks
    app.include_router(create_health_router(service_name=settings.service_name))

    return app
