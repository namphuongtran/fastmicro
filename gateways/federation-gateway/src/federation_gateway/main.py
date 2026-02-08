"""Federation Gateway - Central OIDC Authentication Gateway.

This service acts as a central authentication gateway using standard OIDC
(OpenID Connect) flows. It handles user authentication, token exchange, and
session management with external identity providers.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from .api.v1.auth_controller import router as auth_router
from .application.services.oauth_service import OAuthService
from .configs.settings import get_settings
from .infrastructure.middleware.compress_middleware import setup_compress_middleware
from .infrastructure.middleware.cors_middleware import setup_cors_middleware
from .infrastructure.middleware.session_middleware import setup_session_middleware
from shared.fastapi_utils.exception_handlers import register_exception_handlers
from shared.fastapi_utils.health_router import create_health_router
from shared.fastapi_utils.middleware import RequestContextMiddleware
from shared.observability import (
    LoggingConfig,
    RequestLoggingMiddleware,
    configure_structlog,
    get_structlog_logger,
)

settings_manager = get_settings()

configure_structlog(LoggingConfig(
    service_name="federation-gateway",
    environment="development",
    log_level="DEBUG",
))
logger = get_structlog_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: initialize OIDC service on startup."""
    try:
        oauth_service = OAuthService()
        await oauth_service.initialize()
        app.state.oauth_service = oauth_service
        logger.info("OAuth service initialized successfully")
    except Exception:
        logger.warning(
            "Failed to initialize OAuth service — "
            "OIDC endpoints will be unavailable until provider is reachable",
            exc_info=True,
        )
        app.state.oauth_service = None

    yield

    logger.info("Shutting down federation-gateway")


app = FastAPI(
    title="Federation Gateway",
    version="0.1.0",
    description=(
        "Central authentication gateway using standard OIDC (OpenID Connect) flows. "
        "Supports seamless integration with external IdPs such as Keycloak, Auth0, and Entra ID."
    ),
    lifespan=lifespan,
)

# Middleware stack (order: last added = outermost)
setup_cors_middleware(app, settings_manager)
setup_compress_middleware(app)
setup_session_middleware(app, settings_manager)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(RequestLoggingMiddleware)

# Exception handlers
register_exception_handlers(app)

# Health checks
health_router = create_health_router(
    service_name="federation-gateway",
    version="0.1.0",
)
app.include_router(health_router)


@app.get("/", include_in_schema=False)
async def root() -> JSONResponse:
    """Root endpoint returning service metadata."""
    return JSONResponse({"service": "federation-gateway", "version": "0.1.0"})


# API routers
app.include_router(auth_router, prefix="/api/v1")
