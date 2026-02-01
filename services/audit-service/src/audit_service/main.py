"""
Audit Service - FastAPI Application Entry Point.

This module initializes and configures the FastAPI application with all
necessary middleware, routers, and lifecycle hooks.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from audit_service.api.v1 import audit_controller, health_controller
from audit_service.configs.settings import get_settings
from audit_service.infrastructure.middleware import (
    LoggingMiddleware,
    RequestIdMiddleware,
)

# Import shared library components
try:
    from shared.exceptions import HTTPException as SharedHTTPException
    from shared.observability import get_logger, setup_tracing
except ImportError:
    # Fallback for standalone development
    import structlog
    get_logger = structlog.get_logger

    def setup_tracing(_: object) -> None:  # noqa: E731
        pass

    SharedHTTPException = Exception


settings = get_settings()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.
    
    Handles startup and shutdown events for the application.
    """
    # Startup
    logger.info(
        "Starting Audit Service",
        version=app.version,
        environment=settings.app_env,
    )

    # Initialize OpenTelemetry tracing
    if settings.otel_enabled:
        setup_tracing(settings.service_name)
        logger.info("OpenTelemetry tracing initialized")

    # Initialize database connections
    # await init_database()

    # Initialize cache
    # await init_cache()

    yield

    # Shutdown
    logger.info("Shutting down Audit Service")

    # Cleanup resources
    # await close_database()
    # await close_cache()


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        FastAPI: Configured FastAPI application instance.
    """
    app = FastAPI(
        title="Audit Service",
        description="Enterprise audit logging service for tracking system events, user actions, and compliance records",
        version="0.1.0",
        docs_url="/docs" if settings.app_env != "production" else None,
        redoc_url="/redoc" if settings.app_env != "production" else None,
        openapi_url="/openapi.json" if settings.app_env != "production" else None,
        lifespan=lifespan,
    )

    # Configure middleware (order matters - first added is outermost)
    configure_middleware(app)

    # Configure exception handlers
    configure_exception_handlers(app)

    # Include routers
    configure_routers(app)

    return app


def configure_middleware(app: FastAPI) -> None:
    """Configure application middleware stack."""

    # GZip compression for responses
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request ID middleware (for tracing)
    app.add_middleware(RequestIdMiddleware)

    # Logging middleware
    app.add_middleware(LoggingMiddleware)


def configure_exception_handlers(app: FastAPI) -> None:
    """Configure global exception handlers."""

    @app.exception_handler(SharedHTTPException)
    async def shared_http_exception_handler(
        request: Request, exc: SharedHTTPException
    ) -> JSONResponse:
        """Handle shared library HTTP exceptions."""
        return JSONResponse(
            status_code=getattr(exc, "status_code", 500),
            content={
                "error": getattr(exc, "error_code", "INTERNAL_ERROR"),
                "message": str(exc),
                "details": getattr(exc, "details", None),
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """Handle unhandled exceptions."""
        logger.exception(
            "Unhandled exception",
            path=request.url.path,
            method=request.method,
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
            },
        )


def configure_routers(app: FastAPI) -> None:
    """Configure API routers."""

    # Health check endpoints (no prefix)
    app.include_router(
        health_controller.router,
        tags=["Health"],
    )

    # Audit API v1
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
