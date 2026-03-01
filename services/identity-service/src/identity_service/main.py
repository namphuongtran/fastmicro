"""Identity Service - FastAPI Application Entry Point."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from identity_service import __version__
from identity_service.api import auth_router, health_router, oauth_router
from identity_service.api.web import router as web_router
from identity_service.api.web import routes as web_routes
from identity_service.configs import get_settings

# Shared observability
from shared.fastapi_utils import RequestContextMiddleware, register_exception_handlers
from shared.observability import (
    LoggingConfig,
    RequestLoggingConfig,
    RequestLoggingMiddleware,
    TracingConfig,
    configure_structlog,
    configure_tracing,
    create_prometheus_asgi_app,
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
        service_name="identity-service",
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
    - RSA key initialization for JWT signing
    - Default OAuth2 client seeding
    """
    settings = get_settings()

    # Startup
    logger.info(
        "Starting Identity Service",
        version=__version__,
        environment=settings.app_env,
        issuer=settings.jwt_issuer,
    )

    # Initialize database connection pool
    from identity_service.infrastructure.database import dispose_db, init_db_manager

    db_manager = init_db_manager(
        database_url=settings.database_url.get_secret_value(),
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_pool_overflow,
        echo=settings.is_development,
    )
    logger.info("Database connection pool initialized")

    # Verify database connectivity
    if await db_manager.health_check():
        logger.info("Database health check passed")
    else:
        logger.warning("Database health check failed - service may not function correctly")

    # Register health checks (after DB is initialized)
    from identity_service.api.health import register_health_checks

    register_health_checks()
    logger.info("Health checks registered")

    # Initialize OpenTelemetry tracing
    if settings.otel_enabled:
        configure_tracing(
            TracingConfig(
                service_name=settings.otel_service_name,
                exporter_endpoint=settings.otel_exporter_endpoint,
            )
        )
        logger.info(
            "OpenTelemetry tracing configured",
            endpoint=settings.otel_exporter_endpoint,
        )

    # Initialize RSA keys
    from identity_service.infrastructure.security import get_key_manager

    key_manager = get_key_manager(
        settings.jwt_private_key_path,
        settings.jwt_public_key_path,
    )
    logger.info("RSA keys initialized", kid=key_manager.kid)

    # Seed default OAuth2 clients
    from identity_service.api.dependencies import get_client_repository
    from identity_service.infrastructure.database import get_db_manager

    try:
        from scripts.seed_clients import seed_default_clients

        async with get_db_manager().get_session() as session:
            client_repo = get_client_repository(session)
            await seed_default_clients(client_repo)
        logger.info("Default OAuth2 clients seeded")
    except Exception as e:
        logger.warning("Failed to seed default clients", error=str(e))

    yield

    # Shutdown
    logger.info("Shutting down Identity Service")
    await dispose_db()
    logger.info("Database connections disposed")


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

    # Request context middleware (correlation ID, request metadata)
    app.add_middleware(RequestContextMiddleware)

    # Request logging middleware (must be added after context middleware)
    app.add_middleware(
        RequestLoggingMiddleware,
        config=RequestLoggingConfig(
            exclude_paths=[
                "/health",
                "/healthz",
                "/ready",
                "/readyz",
                "/.well-known/openid-configuration",
                "/.well-known/jwks.json",
            ],
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

    # Register shared exception handlers (structured error responses)
    register_exception_handlers(app)

    # Prometheus metrics endpoint
    metrics_app = create_prometheus_asgi_app()
    app.mount("/metrics", metrics_app)

    # Include routers
    app.include_router(health_router)
    app.include_router(oauth_router)
    app.include_router(auth_router)
    app.include_router(web_router)

    # NOTE: Admin functionality has been moved to identity-admin-service
    # for security isolation. Admin API is no longer exposed from this service.

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
