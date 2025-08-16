from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from ...application.services.oauth_service import OAuthService

security = HTTPBearer(auto_error=False)

class AuthMiddleware:
    def __init__(self, oidc_service: OAuthService):
        self.oidc_service = oidc_service
    
    async def get_current_user(self, credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
        """Get current authenticated user"""
        if not credentials:
            return None
        
        try:
            user_info = await self.oidc_service.get_user_info(credentials.credentials)
            return user_info
        except Exception:
            return None
    
    async def require_auth(self, credentials: HTTPAuthorizationCredentials = Depends(security)):
        """Require authentication"""
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        try:
            user = await self.oidc_service.get_user_info(credentials.credentials)
            return user
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )