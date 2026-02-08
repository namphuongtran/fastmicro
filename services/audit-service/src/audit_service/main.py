"""
Audit Service - FastAPI Application Entry Point.

This module initializes and configures the FastAPI application with all
necessary middleware, routers, and lifecycle hooks.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from audit_service.api.v1 import audit_controller, health_controller
from audit_service.configs.settings import get_settings
from shared.fastapi_utils.exception_handlers import register_exception_handlers
from shared.fastapi_utils.middleware import RequestContextMiddleware
from shared.observability import (
    LoggingConfig,
    RequestLoggingMiddleware,
    TracingConfig,
    configure_structlog,
    get_structlog_logger,
)
from shared.observability.tracing import configure_tracing


settings = get_settings()
configure_structlog(LoggingConfig(
    service_name=settings.service_name,
    environment=settings.app_env,
    log_level=settings.log_level,
))
logger = get_structlog_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    logger.info(
        "Starting Audit Service",
        version=app.version,
        environment=settings.app_env,
    )

    if settings.otel_enabled:
        configure_tracing(TracingConfig(
            service_name=settings.service_name,
        ))
        logger.info("OpenTelemetry tracing initialized")

    yield

    logger.info("Shutting down Audit Service")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Audit Service",
        description="Enterprise audit logging service for tracking system events, user actions, and compliance records",
        version="0.1.0",
        docs_url="/docs" if settings.app_env != "production" else None,
        redoc_url="/redoc" if settings.app_env != "production" else None,
        openapi_url="/openapi.json" if settings.app_env != "production" else None,
        lifespan=lifespan,
    )

    configure_middleware(app)
    register_exception_handlers(app)
    configure_routers(app)

    return app


def configure_middleware(app: FastAPI) -> None:
    """Configure application middleware stack."""
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(RequestLoggingMiddleware)


def configure_routers(app: FastAPI) -> None:
    """Configure API routers."""
    app.include_router(
        health_controller.router,
        tags=["Health"],
    )
    app.include_router(
        audit_controller.router,
        prefix="/api/v1/audit",
        tags=["Audit Events"],
    )


# Create the application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "audit_service.main:app",
        host="0.0.0.0",
        port=settings.app_port,
        reload=settings.app_env == "development",
        log_level=settings.log_level.lower(),
    )
