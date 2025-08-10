from authlib.integrations.starlette_client import OAuth
from starlette.requests import Request
from starlette.responses import Response
from typing import Dict, Any, Optional
import logging

from ...configs.settings import get_settings

logger = logging.getLogger(__name__)

class OAuthService:
    """Service for handling OAuth operations"""
    
    def __init__(self):
        self.settings = get_settings()
        self.oauth = OAuth()
        self._register_client()
    
    def _register_client(self):
        """Register OAuth client with the configured identity provider"""
        self.oauth.register(
            name="oidc",
            client_id=self.settings.auth.oidc.client_id,
            client_secret=self.settings.auth.oidc.client_secret,
            server_metadata_url=f"{self.settings.auth.oidc.issuer_url}/.well-known/openid-configuration",
            client_kwargs={
                "scope": " ".join(self.settings.auth.oidc.scopes)
            }
        )
        logger.info(f"OAuth client registered for issuer: {self.settings.auth.oidc.issuer_url}")
    
    async def authorize_redirect(self, request: Request, redirect_uri: str) -> Response:
        """Redirect user to OAuth provider for authentication"""
        return await self.oauth.oidc.authorize_redirect(request, redirect_uri)
    
    async def authorize_access_token(self, request: Request) -> Dict[str, Any]:
        """Exchange authorization code for access token"""
        return await self.oauth.oidc.authorize_access_token(request)
    
    def get_user_info(self, token: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract user information from token"""
        user_info = token.get('userinfo')
        if user_info:
            return dict(user_info)
        return None
    
    async def refresh_access_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """Refresh access token using refresh token"""
        try:
            # Implementation depends on your OAuth provider
            # This is a placeholder - implement based on your provider's refresh flow
            logger.warning("Token refresh not implemented yet")
            return None
        except Exception as e:
            logger.error(f"Token refresh failed: {str(e)}")
            return None