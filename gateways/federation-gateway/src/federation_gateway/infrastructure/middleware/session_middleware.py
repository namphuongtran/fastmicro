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
    crypto_config = settings_manager.security.crypto
    session_config = settings_manager.security.session
    
    # Add Session middleware to FastAPI
    app.add_middleware(
        SessionMiddleware,
        secret_key=crypto_config.secret_key or secrets.token_hex(32),
        max_age=session_config.timeout,
        same_site=session_config.same_site_cookies,
        session_cookie=session_config.cookie_name,
        https_only=session_config.https_only,
    )
    
    logger.info(f"Session middleware configured with key: {crypto_config.secret_key}")
    logger.info(f"Session middleware configured with name: {session_config.cookie_name}")