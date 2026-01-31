"""Metastore Service - FastAPI Application Entry Point."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from metastore_service.api.v1 import health_controller, metadata_controller
from metastore_service.configs.settings import get_settings

try:
    from shared.observability import get_logger
except ImportError:
    import structlog
    get_logger = structlog.get_logger

settings = get_settings()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    logger.info("Starting Metastore Service", version=app.version, environment=settings.app_env)
    yield
    logger.info("Shutting down Metastore Service")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Metastore Service",
        description="Metadata management service for configurations and feature flags",
        version="0.1.0",
        docs_url="/docs" if settings.app_env != "production" else None,
        redoc_url="/redoc" if settings.app_env != "production" else None,
        lifespan=lifespan,
    )
    
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception", path=request.url.path)
        return JSONResponse(status_code=500, content={"error": "INTERNAL_ERROR"})
    
    app.include_router(health_controller.router, tags=["Health"])
    app.include_router(metadata_controller.router, prefix="/api/v1/metadata", tags=["Metadata"])
    
    return app


app = create_app()
