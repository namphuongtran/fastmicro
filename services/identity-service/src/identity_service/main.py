"""Identity Service - FastAPI Application Entry Point."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from identity_service import __version__
from identity_service.api import health_router, oauth_router
from identity_service.api.web import router as web_router
from identity_service.api.web import routes as web_routes
from identity_service.configs import get_settings

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
configure_structlog(LoggingConfig(
    service_name="identity-service",
    environment=settings.app_env,
    log_level=settings.log_level,
))

logger = get_structlog_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler.

    Handles startup and shutdown events.
    """
    settings = get_settings()

    # Startup
    logger.info(
        "Starting Identity Service",
        version=__version__,
        environment=settings.app_env,
        issuer=settings.jwt_issuer,
    )

    # Initialize RSA keys
    from identity_service.infrastructure.security import get_key_manager

    key_manager = get_key_manager(
        settings.jwt_private_key_path,
        settings.jwt_public_key_path,
    )
    logger.info("RSA keys initialized", kid=key_manager.kid)

    yield

    # Shutdown
    logger.info("Shutting down Identity Service")


def create_app() -> FastAPI:
    """Create and configure FastAPI application.

    Returns:
        Configured FastAPI application instance.
    """
    settings = get_settings()

    app = FastAPI(
        title="Identity Service",
        description="Enterprise Identity Provider - OAuth 2.0 / OpenID Connect Server",
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
        web_routes.templates = templates

    # Request logging middleware (must be added first to wrap other middleware)
    app.add_middleware(
        RequestLoggingMiddleware,
        config=RequestLoggingConfig(
            exclude_paths=["/health", "/healthz", "/ready", "/readyz", "/.well-known/openid-configuration", "/.well-known/jwks.json"],
            slow_request_threshold_ms=500.0,
        ),
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Correlation-ID", "X-Request-ID"],
    )

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handle uncaught exceptions."""
        logger.error(
            "Unhandled exception",
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
    app.include_router(oauth_router)
    app.include_router(web_router)

    return app


# Application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "identity_service.main:app",
        host="0.0.0.0",
        port=settings.app_port,
        reload=settings.is_development,
    )
