"""User Service — FastAPI application entry point.

Registers middleware, exception handlers, health checks, and API routers.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from starlette.requests import Request

from shared.application.base_service import ConflictError, NotFoundError, ServiceError
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

from user_service.api.routes import router as api_router
from user_service.configs.settings import get_settings

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
        "User Service starting",
        service_name=settings.service_name,
        port=settings.port,
    )
    yield
    logger.info("User Service shutting down")


def create_app() -> FastAPI:
    """Application factory."""
    settings = get_settings()

    app = FastAPI(
        title="User Service",
        description="User management — profiles, preferences, tenant management",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/api/v1/docs",
        openapi_url="/api/v1/openapi.json",
    )

    # Middleware (order matters: outermost first)
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(RequestLoggingMiddleware)

    # Exception handlers
    register_exception_handlers(app)

    # Map application-layer errors to HTTP responses
    @app.exception_handler(NotFoundError)
    async def _not_found_handler(_request: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(ConflictError)
    async def _conflict_handler(_request: Request, exc: ConflictError) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.exception_handler(ServiceError)
    async def _service_error_handler(_request: Request, exc: ServiceError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    # Health checks
    app.include_router(create_health_router(service_name=settings.service_name))

    # API routes
    app.include_router(api_router, prefix="/api/v1")

    return app
app = create_app()
