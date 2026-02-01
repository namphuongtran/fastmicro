from fastapi import FastAPI
import secrets
from starlette.middleware.sessions import SessionMiddleware
import logging
from federation_gateway.configs.settings import FederationGatewaySettings

logger = logging.getLogger(__name__)

def setup_session_middleware(app: FastAPI, settings: FederationGatewaySettings):
    """
    Setup session middleware for FastAPI application.
    
    Args:
        app: FastAPI application instance
        settings: Gateway settings with session configuration
    """
    crypto_config = settings.security.crypto
    session_config = settings.security.session
    
    # Get secret key from crypto settings or generate one
    secret_key = (
        crypto_config.secret_key.get_secret_value()
        if crypto_config.secret_key
        else secrets.token_hex(32)
    )
    
    # Add Session middleware to FastAPI
    app.add_middleware(
        SessionMiddleware,
        secret_key=secret_key,
        max_age=session_config.max_age,
        same_site=session_config.cookie.same_site.value if hasattr(session_config, 'cookie') else "lax",
        session_cookie=session_config.cookie_name,
        https_only=session_config.cookie.secure if hasattr(session_config, 'cookie') else False,
    )
    
    logger.info(f"Session middleware configured with cookie name: {session_config.cookie_name}")