from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from starlette.responses import Response
from starlette.requests import Request
from authlib.integrations.starlette_client import OAuthError
import json
import logging
from typing import Dict, Any

from ...application.services.oauth_service import OAuthService
from ...application.services.session_service import SessionService
from ...configs.settings import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])

def get_oauth_service() -> OAuthService:
    """Dependency to get OAuth service instance"""
    return OAuthService()

def get_session_service() -> SessionService:
    """Dependency to get Session service instance"""
    return SessionService()

@router.get("/")
async def auth_status(
    request: Request,
    session_service: SessionService = Depends(get_session_service)
):
    """
    Get current authentication status
    Returns user info if authenticated, otherwise login prompt
    """
    try:
        user = await session_service.get_user(request)
        if user:
            return JSONResponse({
                "authenticated": True,
                "user": user,
                "message": "User is authenticated"
            })
        
        return JSONResponse({
            "authenticated": False,
            "login_url": "/v1/auth/login",
            "message": "User not authenticated"
        })
    except Exception as e:
        logger.error(f"Error checking auth status: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/login")
async def login(
    request: Request,
    oauth_service: OAuthService = Depends(get_oauth_service)
):
    """
    Initiate OAuth login flow
    Redirects user to identity provider login page
    """
    try:
        redirect_uri = request.url_for('auth_callback')
        print(f"Redirect URI: {redirect_uri}")
        return await oauth_service.authorize_redirect(request, redirect_uri)
    except Exception as e:
        logger.error(f"Error initiating login: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to initiate login")

@router.get("/callback")
async def auth_callback(
    request: Request,
    oauth_service: OAuthService = Depends(get_oauth_service),
    session_service: SessionService = Depends(get_session_service)
):
    """
    Handle OAuth callback from identity provider
    Exchange authorization code for tokens and create user session
    """
    try:
        # Exchange authorization code for access token
        token = await oauth_service.authorize_access_token(request)
        
        # Extract user information from token
        user_info = oauth_service.get_user_info(token)
        
        if user_info:
            # Create user session
            await session_service.create_session(request, user_info)
            logger.info(f"User authenticated successfully: {user_info.get('email', 'unknown')}")
            
            # Redirect to success page or return JSON response
            return JSONResponse({
                "success": True,
                "message": "Authentication successful",
                "user": user_info
            })
        else:
            logger.warning("No user info received from OAuth provider")
            raise HTTPException(status_code=400, detail="Authentication failed - no user info")
            
    except OAuthError as error:
        logger.error(f"OAuth error during callback: {error.error}")
        return JSONResponse(
            status_code=400,
            content={"error": error.error, "description": getattr(error, 'description', 'OAuth authentication failed')}
        )
    except Exception as e:
        logger.error(f"Unexpected error during auth callback: {str(e)}")
        raise HTTPException(status_code=500, detail="Authentication callback failed")

@router.post("/logout")
async def logout(
    request: Request,
    session_service: SessionService = Depends(get_session_service)
):
    """
    Logout user and clear session
    """
    try:
        await session_service.clear_session(request)
        logger.info("User logged out successfully")
        
        return JSONResponse({
            "success": True,
            "message": "Logout successful"
        })
    except Exception as e:
        logger.error(f"Error during logout: {str(e)}")
        raise HTTPException(status_code=500, detail="Logout failed")

@router.get("/user")
async def get_current_user(
    request: Request,
    session_service: SessionService = Depends(get_session_service)
):
    """
    Get current authenticated user information
    """
    try:
        user = await session_service.get_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        return JSONResponse({
            "user": user,
            "message": "User information retrieved successfully"
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving user info: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve user information")

@router.get("/refresh")
async def refresh_token(
    request: Request,
    oauth_service: OAuthService = Depends(get_oauth_service),
    session_service: SessionService = Depends(get_session_service)
):
    """
    Refresh access token if refresh token is available
    """
    try:
        # Get current session
        user_session = await session_service.get_session_data(request)
        if not user_session:
            raise HTTPException(status_code=401, detail="No active session")
        
        # Attempt to refresh token
        new_token = await oauth_service.refresh_access_token(user_session.get('refresh_token'))
        
        if new_token:
            # Update session with new token info
            await session_service.update_session(request, new_token)
            
            return JSONResponse({
                "success": True,
                "message": "Token refreshed successfully"
            })
        else:
            # Clear invalid session
            await session_service.clear_session(request)
            raise HTTPException(status_code=401, detail="Token refresh failed")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refreshing token: {str(e)}")
        raise HTTPException(status_code=500, detail="Token refresh failed")