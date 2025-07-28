from fastapi import FastAPI
import secrets
from starlette.middleware.sessions import SessionMiddleware
import logging
from settings.settings_manager import SettingsManager

logger = logging.getLogger(__name__)

def setup_session_middleware(app: FastAPI, settings_manager: SettingsManager):
    """
    Setup session middleware for FastAPI application.
    
    Args:
        app: FastAPI application instance
        settings_manager: Settings manager with session configuration
    """
    session_config = settings_manager.security.crypto
    
    # Add Session middleware to FastAPI
    app.add_middleware(
        SessionMiddleware,
        secret_key=session_config.secret_key or secrets.token_hex(32)
    )
    
    logger.info(f"Session middleware configured with name: {session_config.secret_key}")