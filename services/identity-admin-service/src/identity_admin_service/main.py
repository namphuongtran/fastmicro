"""Identity Admin Service - FastAPI Application Entry Point."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from identity_admin_service import __version__
from identity_admin_service.api import clients_router, health_router, users_router
from identity_admin_service.api.web import admin_router
from identity_admin_service.api.web import routes as admin_web_routes
from identity_admin_service.configs import get_settings
from identity_admin_service.middleware import IPWhitelistMiddleware

# Shared observability
from shared.observability import (
    LoggingConfig,
    RequestLoggingConfig,
    RequestLoggingMiddleware,
    configure_structlog,
    get_structlog_logger,
)

# Paths for templates and static files
BASE_DIR = Path(__file__).resolve().parent.parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

# Configure structured logging using shared library
settings = get_settings()
configure_structlog(
    LoggingConfig(
        service_name="identity-admin-service",
        environment=settings.app_env,
        log_level=settings.log_level,
    )
)

logger = get_structlog_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler.

    Handles startup and shutdown events including:
    - Database connection pool initialization
    - Template configuration
    """
    settings = get_settings()

    # Startup
    logger.info(
        "Starting Identity Admin Service",
        version=__version__,
        environment=settings.app_env,
        port=settings.app_port,
        identity_service_url=settings.identity_service_url,
    )

    # Security warning for production
    if settings.is_production and settings.allowed_admin_ips == "*":
        logger.warning(
            "Production deployment with unrestricted IP access",
            recommendation="Configure ALLOWED_ADMIN_IPS for production",
        )

    if settings.is_production and not settings.admin_require_mfa:
        logger.warning(
            "Production deployment without MFA requirement",
            recommendation="Enable ADMIN_REQUIRE_MFA for production",
        )

    yield

    # Shutdown
    logger.info("Shutting down Identity Admin Service")


def create_app() -> FastAPI:
    """Create and configure FastAPI application.

    Returns:
        Configured FastAPI application instance.
    """
    settings = get_settings()

    app = FastAPI(
        title="Identity Admin Service",
        description="Internal administration service for Identity Provider management",
        version=__version__,
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
        openapi_url="/openapi.json" if settings.is_development else None,
        lifespan=lifespan,
    )

    # Mount static files
    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    # Configure templates
    if TEMPLATES_DIR.exists():
        templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
        admin_web_routes.templates = templates

    # IP Whitelist middleware (first to reject unauthorized IPs early)
    if settings.allowed_admin_ips != "*":
        app.add_middleware(
            IPWhitelistMiddleware,
            allowed_ips=settings.allowed_ip_list,
        )

    # Request logging middleware
    app.add_middleware(
        RequestLoggingMiddleware,
        config=RequestLoggingConfig(
            exclude_paths=[
                "/health",
                "/healthz",
                "/ready",
                "/readyz",
            ],
            slow_request_threshold_ms=500.0,
        ),
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Correlation-ID", "X-Request-ID"],
    )

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handle uncaught exceptions."""
        logger.error(
            "Unhandled exception in admin service",
            path=request.url.path,
            method=request.method,
            error=str(exc),
            exc_info=True,
        )

        return JSONResponse(
            status_code=500,
            content={
                "error": "server_error",
                "error_description": "An internal error occurred",
            },
        )

    # Include routers
    app.include_router(health_router)

    # Admin API routers
    app.include_router(clients_router)
    app.include_router(users_router)

    # Admin Web UI
    app.include_router(admin_router)

    return app


# Application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "identity_admin_service.main:app",
        host="0.0.0.0",
        port=settings.app_port,
        reload=settings.is_development,
    )
