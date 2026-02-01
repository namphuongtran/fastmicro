import logging
from contextlib import asynccontextmanager
from multiprocessing import cpu_count, freeze_support

import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from .api.v1.auth_controller import router as auth_router
from .application.services.oauth_service import OAuthService
from .configs.settings import get_settings
from .infrastructure.middleware.compress_middleware import setup_compress_middleware
from .infrastructure.middleware.cors_middleware import setup_cors_middleware
from .infrastructure.middleware.session_middleware import setup_session_middleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings_manager = get_settings()
app_config = settings_manager.app

app_name = app_config.name
app_version = app_config.version
description = (
    app_config.description
    or """
This service acts as a central authentication gateway using standard OIDC (OpenID Connect) flows.
It allows seamless integration with external identity providers (IdPs) such as Keycloak, Auth0, Entra ID, and others.
The gateway handles user authentication, token exchange, and session management, making it easy to plug in different IdPs without changing your core application logic."""
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize OIDC service on startup
    try:
        oauth_service = OAuthService()
        await oauth_service.initialize()

        # Store in app state
        app.state.oauth_service = oauth_service
        logger.info("OAuth service initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize OAuth service: {e}")
        raise

    yield

    # Cleanup on shutdown
    logger.info("Shutting down application...")


# Create the main FastAPI application
app = FastAPI(title=app_name, version=app_version, description=description, lifespan=lifespan)

# Add middlewares and routers
setup_cors_middleware(app, settings_manager)
setup_compress_middleware(app)
setup_session_middleware(app, settings_manager)


@app.get("/", include_in_schema=False)
async def root():
    """The root function is a default entrypoint for the application.

    Returns:
        _type_: _description_
    """
    return JSONResponse({"service": app_name, "version": app_version})


# Include routers
app.include_router(auth_router, prefix="/v1")


def run_server(host="127.0.0.1", port=44381, workers=4, loop="asyncio", reload=False):
    """Start to run the server"""
    uvicorn.run(
        "src.federation_gateway.main:app",
        host=host,
        port=port,
        workers=workers,
        loop=loop,
        reload=reload,
    )


if __name__ == "__main__":
    freeze_support()  # Needed for pyinstaller for multiprocessing on WindowsOS
    num_workers = int(cpu_count() * 0.75)
    run_server(workers=num_workers)
