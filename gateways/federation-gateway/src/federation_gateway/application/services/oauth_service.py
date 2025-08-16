from authlib.integrations.httpx_client import AsyncOAuth2Client
from authlib.integrations.base_client import OAuthError
from authlib.oidc.discovery import get_well_known_url
import httpx
import secrets
import time
from typing import Dict, Any
import logging
from ...domain.entities.user_info import UserInfo
from ...domain.entities.token_response import TokenResponse
from ...domain.entities.auth_response import AuthResponse
from ...configs.settings import get_settings

logger = logging.getLogger(__name__)

class OAuthService:
    """OIDC Service for single provider configuration"""
    
    def __init__(self):
        self.settings = get_settings()
        self.client: AsyncOAuth2Client = None
        self.server_metadata: Dict[str, Any] = {}
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self._setup_client()

    def _is_local_development(self) -> bool:
        """Check if running in local development environment"""
        issuer_url = self.settings.auth.oidc.issuer_url.lower()
        local_indicators = [
            'localhost',
            '127.0.0.1',
            '.local',
            ':44381',
            ':8443',
            'auth.local.ags.com'  # Your specific local domain
        ]
        return any(indicator in issuer_url for indicator in local_indicators)
    
    def _get_ssl_context(self):
        """Get appropriate SSL context for environment"""
        if self._is_local_development():
            logger.warning("Running in local development mode - SSL verification disabled")
            return False
        return True
    
    def _setup_client(self):
        """Setup OAuth client with configured provider"""
        self.client = AsyncOAuth2Client(
            client_id=self.settings.auth.oidc.client_id,
            client_secret=self.settings.auth.oidc.client_secret,
            scope=self.settings.auth.oidc.scopes
        )
        logger.info("OIDC client configured")
    
    async def initialize(self):
        """Initialize OIDC provider metadata"""
        try:
            # Create HTTP client with timeout and error handling
            timeout = httpx.Timeout(30.0, connect=10.0)
            # Method 1: Using authlib's get_well_known_url helper
            discovery_url = get_well_known_url(self.settings.auth.oidc.issuer_url, external=True)
            # SSL configuration for local development
            ssl_verify = self._get_ssl_context()
            async with httpx.AsyncClient(timeout=timeout, verify=ssl_verify) as http_client:
                logger.debug(f"Making request to: {discovery_url}")
                response = await http_client.get(discovery_url)
                logger.info(f"Response status: {response.status_code}")
                logger.debug(f"Response headers: {dict(response.headers)}")
                response.raise_for_status()
                self.server_metadata = response.json()
            
            # Update client with server metadata
            self.client.server_metadata = self.server_metadata
            
            logger.info("OIDC provider metadata initialized")
            logger.debug(f"Available endpoints: {list(self.server_metadata.keys())}")
            
        except Exception as e:
            logger.error(f"Failed to initialize OIDC provider: {e}")
            raise
    
    async def get_authorization_url(self, redirect_uri: str = None) -> AuthResponse:
        """Get authorization URL"""
        if not self.server_metadata:
            raise Exception("OIDC service not initialized. Call initialize() first.")
            
        if not redirect_uri:
            redirect_uri = self.settings.auth.oidc.redirect_uri
            
        state = secrets.token_urlsafe(32)
        
        self.sessions[state] = {
            "redirect_uri": redirect_uri,
            "timestamp": time.time()
        }
        
        # Use the authorization_endpoint from discovered metadata
        auth_endpoint = self.server_metadata.get('authorization_endpoint')
        if not auth_endpoint:
            raise Exception("Authorization endpoint not found in provider metadata")
        
        auth_url, _ = self.client.create_authorization_url(
            auth_endpoint,
            redirect_uri=redirect_uri,
            state=state
        )
        
        logger.info("Authorization URL generated")
        return AuthResponse(authorization_url=auth_url, state=state)
    
    async def exchange_code_for_tokens(self, code: str, state: str) -> TokenResponse:
        """Exchange authorization code for tokens"""
        if not self.server_metadata:
            raise Exception("OIDC service not initialized")
            
        if state not in self.sessions:
            raise Exception("Invalid state parameter")
        
        session = self.sessions[state]
        
        # Check session expiration (optional - add timeout as needed)
        if time.time() - session["timestamp"] > 600:  # 10 minutes timeout
            del self.sessions[state]
            raise Exception("Session expired")
        
        try:
            token_endpoint = self.server_metadata.get('token_endpoint')
            if not token_endpoint:
                raise Exception("Token endpoint not found in provider metadata")
            
            token = await self.client.fetch_token(
                token_endpoint,
                code=code,
                redirect_uri=session["redirect_uri"]
            )
            
            del self.sessions[state]
            
            logger.info("Tokens exchanged successfully")
            return TokenResponse(
                access_token=token['access_token'],
                id_token=token.get('id_token'),
                refresh_token=token.get('refresh_token'),
                expires_in=token.get('expires_in', 3600)
            )
            
        except OAuthError as e:
            logger.error(f"Token exchange failed: {e}")
            raise Exception(f"Token exchange failed: {str(e)}")
    
    async def get_user_info(self, access_token: str) -> UserInfo:
        """Get user information using access token"""
        if not self.server_metadata:
            raise Exception("OIDC service not initialized")
            
        userinfo_endpoint = self.server_metadata.get('userinfo_endpoint')
        
        if not userinfo_endpoint:
            raise Exception("Userinfo endpoint not available")
        
        try:
            async with httpx.AsyncClient() as http_client:
                response = await http_client.get(
                    userinfo_endpoint,
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                response.raise_for_status()
                data = response.json()
            
            logger.info("User info retrieved successfully")
            return UserInfo(
                sub=data.get('sub'),
                name=data.get('name'),
                email=data.get('email'),
                preferred_username=data.get('preferred_username'),
                roles=data.get('roles', [])
            )
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise Exception("Invalid or expired token")
            logger.error(f"Userinfo request failed: {e}")
            raise Exception("Failed to get user info")
    
    async def refresh_token(self, refresh_token: str) -> TokenResponse:
        """Refresh access token"""
        if not self.server_metadata:
            raise Exception("OIDC service not initialized")
            
        try:
            token_endpoint = self.server_metadata.get('token_endpoint')
            if not token_endpoint:
                raise Exception("Token endpoint not found in provider metadata")
                
            token = await self.client.refresh_token(
                token_endpoint,
                refresh_token=refresh_token
            )
            
            logger.info("Token refreshed successfully")
            return TokenResponse(
                access_token=token['access_token'],
                id_token=token.get('id_token'),
                refresh_token=token.get('refresh_token', refresh_token),
                expires_in=token.get('expires_in', 3600)
            )
            
        except OAuthError as e:
            logger.error(f"Token refresh failed: {e}")
            raise Exception(f"Token refresh failed: {str(e)}")