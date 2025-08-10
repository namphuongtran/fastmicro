from starlette.requests import Request
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class SessionService:
    """Service for handling user sessions"""
    
    async def get_user(self, request: Request) -> Optional[Dict[str, Any]]:
        """Get user information from session"""
        return request.session.get('user')
    
    async def get_session_data(self, request: Request) -> Optional[Dict[str, Any]]:
        """Get full session data"""
        return dict(request.session) if request.session else None
    
    async def create_session(self, request: Request, user_info: Dict[str, Any]) -> None:
        """Create user session with user information"""
        request.session['user'] = user_info
        # You can also store additional session data like tokens, preferences, etc.
        logger.info(f"Session created for user: {user_info.get('email', 'unknown')}")
    
    async def update_session(self, request: Request, token_data: Dict[str, Any]) -> None:
        """Update session with new token data"""
        if 'user' in request.session:
            # Update token information while preserving user data
            request.session.update(token_data)
            logger.info("Session updated with new token data")
    
    async def clear_session(self, request: Request) -> None:
        """Clear user session"""
        user_email = request.session.get('user', {}).get('email', 'unknown')
        request.session.clear()
        logger.info(f"Session cleared for user: {user_email}")