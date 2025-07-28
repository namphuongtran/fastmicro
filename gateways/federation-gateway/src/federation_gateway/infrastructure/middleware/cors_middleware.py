from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
from settings.settings_manager import SettingsManager

logger = logging.getLogger(__name__)

def setup_cors_middleware(app: FastAPI, settings_manager: SettingsManager):
    """
    Setup CORS middleware using security settings.
    
    Args:
        app: FastAPI application instance
        settings_manager: Settings manager with CORS configuration
    """
    cors_config = settings_manager.security.cors
    
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