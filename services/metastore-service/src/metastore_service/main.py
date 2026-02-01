"""Metastore Service - FastAPI Application Entry Point."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from metastore_service.api.dependencies import set_cache, set_database_manager
from metastore_service.api.routes import (
    configuration_router,
    feature_flag_router,
    health_router,
    metadata_router,
)
from metastore_service.configs.settings import get_settings
from shared.cache import TieredCacheManager
from shared.observability import (
    LoggingConfig,
    RequestLoggingConfig,
    RequestLoggingMiddleware,
    configure_structlog,
    get_structlog_logger,
)
from shared.observability.health import register_health_check

# Use shared library managers
from shared.sqlalchemy_async import AsyncDatabaseManager

settings = get_settings()

# Configure structured logging using shared library
configure_structlog(
    LoggingConfig(
        service_name="metastore-service",
        environment=settings.environment,
        log_level=getattr(settings, "log_level", "INFO"),
    )
)

logger = get_structlog_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager.

    Initializes and cleans up:
    - Database connection pool (AsyncDatabaseManager)
    - Cache manager (TieredCacheManager with L1/L2)
    - Health check registrations
    """
    logger.info(
        "Starting Metastore Service",
        version=settings.app_version,
        environment=settings.environment,
    )

    # Initialize database manager with shared library
    db_config = settings.get_database_config()
    db_manager = AsyncDatabaseManager(db_config)
    set_database_manager(db_manager)
    logger.info("Database connection pool initialized")

    # Register database health check
    async def db_health_check() -> bool:
        return await db_manager.health_check()

    register_health_check("database", db_health_check)

    # Initialize tiered cache manager
    cache: TieredCacheManager | None = None
    if settings.redis_enabled:
        try:
            cache_config = settings.get_cache_config()
            cache = await TieredCacheManager.create(cache_config)
            set_cache(cache)
            logger.info("Tiered cache initialized (L1: memory, L2: Redis)")

            # Register cache health check
            async def cache_health_check() -> bool:
                return await cache.health_check() if cache else False

            register_health_check("cache", cache_health_check)
        except Exception as e:
            logger.warning(
                "Failed to connect to Redis, continuing without L2 cache",
                error=str(e),
            )

    yield

    # Cleanup
    if cache:
        await cache.close()
        logger.info("Cache manager closed")

    await db_manager.dispose()
    logger.info("Database connection pool closed")

    logger.info("Shutting down Metastore Service")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Metastore Service",
        description="Metadata management service for configurations and feature flags",
        version=settings.app_version,
        docs_url="/docs" if settings.environment != "production" else None,
        redoc_url="/redoc" if settings.environment != "production" else None,
        lifespan=lifespan,
    )

    # Request logging middleware (must be added first to wrap other middleware)
    app.add_middleware(
        RequestLoggingMiddleware,
        config=RequestLoggingConfig(
            slow_request_threshold_ms=500.0,
        ),
    )

    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=[*settings.cors_allow_headers, "X-Correlation-ID"],
    )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception", extra={"path": request.url.path})
        return JSONResponse(status_code=500, content={"error": "INTERNAL_ERROR"})

    # Include routers
    app.include_router(health_router, tags=["Health"])
    app.include_router(metadata_router, prefix="/api/v1", tags=["Metadata"])
    app.include_router(feature_flag_router, prefix="/api/v1", tags=["Feature Flags"])
    app.include_router(configuration_router, prefix="/api/v1", tags=["Configurations"])

    return app


app = create_app()
