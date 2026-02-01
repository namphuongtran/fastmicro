import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from federation_gateway.configs.settings import FederationGatewaySettings

logger = logging.getLogger(__name__)

def setup_cors_middleware(app: FastAPI, settings: FederationGatewaySettings):
    """
    Setup CORS middleware using security settings.
    
    Args:
        app: FastAPI application instance
        settings: Gateway settings with CORS configuration
    """
    cors_config = settings.security.cors

    if not cors_config.enabled:
        logger.info("CORS is disabled")
        return

    # Add CORS middleware to FastAPI
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_config.allow_origins,
        allow_credentials=cors_config.allow_credentials,
        allow_methods=cors_config.allow_methods,
        allow_headers=cors_config.allow_headers,
        expose_headers=cors_config.expose_headers,
        max_age=cors_config.max_age,
    )

    logger.info(f"CORS middleware configured with origins: {cors_config.allow_origins}")
