# from fastapi import APIRouter, Depends, HTTPException, Query
# from fastapi.responses import JSONResponse
# from starlette.requests import Request as StarletteRequest
# import logging
# from typing import Optional
# from ...application.services.oauth_service import OAuthService
# from ...application.services.session_service import SessionService
# from ...infrastructure.middleware.auth_middleware import AuthMiddleware, security

# logger = logging.getLogger(__name__)

# router = APIRouter(prefix="/auth", tags=["authentication"])

# def get_oauth_service(request: StarletteRequest) -> OAuthService:
#     """Dependency to get OAuth service instance from app state"""
#     oauth_service = getattr(request.app.state, 'oauth_service', None)
    
#     if oauth_service is None:
#         raise HTTPException(
#             status_code=500, 
#             detail="OAuth service not initialized"
#         )
#     return oauth_service

# def get_auth_middleware(    
#     oauth_service: OAuthService = Depends(get_oauth_service)
# ) -> AuthMiddleware:
#     """Dependency to get AuthMiddleware instance"""
#     return AuthMiddleware(oidc_service=oauth_service)

# @router.get("/login")
# async def login(    
#     redirect_uri: Optional[str] = Query(None),
#     oauth_service: OAuthService = Depends(get_oauth_service)
# ):
#     """Initiate OIDC login flow"""
#     try:
#         logger.info("Initiating login flow")
#         result = await oauth_service.get_authorization_url(redirect_uri)
#         logger.info("Authorization URL generated successfully")
#         return result
#     except Exception as e:
#         logger.error(f"Login error: {e}")
#         raise HTTPException(status_code=500, detail=str(e))

# @router.get("/callback")
# async def callback(    
#     code: str,
#     state: str,
#     oauth_service: OAuthService = Depends(get_oauth_service)
# ):
#     """Handle OIDC callback"""
#     try:
#         logger.info("Processing OIDC callback")
#         tokens = await oauth_service.exchange_code_for_tokens(code, state)
#         logger.info("Token exchange completed successfully")
#         return tokens
#     except Exception as e:
#         logger.error(f"Callback error: {e}")
#         raise HTTPException(status_code=400, detail=str(e))

# @router.post("/refresh")
# async def refresh_access_token(    
#     refresh_token: str,
#     oauth_service: OAuthService = Depends(get_oauth_service)
# ):
#     """Refresh access token"""
#     try:
#         logger.info("Refreshing access token")
#         tokens = await oauth_service.refresh_token(refresh_token)
#         return tokens
#     except Exception as e:
#         logger.error(f"Token refresh error: {e}")
#         raise HTTPException(status_code=400, detail=str(e))

# @router.post("/logout")
# async def logout(    
#     oauth_service: OAuthService = Depends(get_oauth_service)
# ):
#     """Logout user and clear session"""
#     try:
#         logger.info("User logged out successfully")
#         return JSONResponse({
#             "success": True,
#             "message": "Logout successful"
#         })
#     except Exception as e:
#         logger.error(f"Error during logout: {str(e)}")
#         raise HTTPException(status_code=500, detail="Logout failed")

# @router.get("/user")
# async def get_current_user(    
#     user=Depends(get_auth_middleware)
# ):
#     """Get current authenticated user"""
#     if not user:
#         raise HTTPException(status_code=401, detail="Not authenticated")
    
#     try:
#         current_user = user.require_auth()
#         logger.info(f"Current user retrieved: {current_user.get('sub', 'unknown')}")
#         return current_user
#     except Exception as e:
#         logger.error(f"Error getting current user: {e}")
#         raise HTTPException(status_code=401, detail="Authentication required")

# @router.get("/health")
# async def auth_health(    
#     oauth_service: OAuthService = Depends(get_oauth_service)
# ):
#     """Check OAuth service health"""
#     try:
#         health = await oauth_service.health_check()
#         return health
#     except Exception as e:
#         return {"status": "unhealthy", "error": str(e)}

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse, JSONResponse
from starlette.requests import Request as StarletteRequest
from urllib.parse import urlencode, urlparse, parse_qs
from ...application.services.oauth_service import OAuthService
from ...infrastructure.middleware.auth_middleware import AuthMiddleware

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["authentication"])

def get_oauth_service(request: StarletteRequest) -> OAuthService:
    """Dependency to get OAuth service instance from app state"""
    oauth_service = getattr(request.app.state, 'oauth_service', None)
    
    if oauth_service is None:
        raise HTTPException(
            status_code=500, 
            detail="OAuth service not initialized"
        )
    return oauth_service

def get_auth_middleware(
    oauth_service: OAuthService = Depends(get_oauth_service)
) -> AuthMiddleware:
    """Dependency to get AuthMiddleware instance"""
    return AuthMiddleware(oidc_service=oauth_service)

@router.get("/login")
async def login(
    request: Request,
    redirect_uri: Optional[str] = Query(None, description="Where to redirect after successful login"),
    oauth_service: OAuthService = Depends(get_oauth_service)
):
    """
    Federation Gateway Login Endpoint
    
    Flow:
    1. Client calls /auth/login?redirect_uri=https://myapp.com/dashboard
    2. Gateway generates authorization URL for Keycloak
    3. Gateway redirects user to Keycloak login page
    4. User enters credentials on Keycloak
    5. Keycloak redirects back to /auth/callback with code
    6. Gateway exchanges code for tokens
    7. Gateway redirects user to original redirect_uri with tokens/session
    """
    try:
        logger.info(f"Federation login initiated. Target redirect: {redirect_uri}")
        
        # Store the final redirect URI in the callback URL as a parameter
        # This way we can redirect the user to their intended destination after auth
        callback_url = str(request.url_for("callback"))
        if redirect_uri:
            # Add the final redirect URI as a query parameter to the callback
            callback_url += f"?final_redirect={redirect_uri}"
        
        # Get authorization URL from OIDC provider (Keycloak)
        auth_response = await oauth_service.get_authorization_url(callback_url)
        
        logger.info(f"Redirecting user to Keycloak: {auth_response.authorization_url}")
        
        # REDIRECT user to Keycloak login page
        return RedirectResponse(
            url=auth_response.authorization_url,
            status_code=302
        )
        
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail=f"Authentication service error: {str(e)}")

@router.get("/callback")
async def callback(
    code: str,
    state: str,
    final_redirect: Optional[str] = Query(None, description="Final destination after auth"),
    oauth_service: OAuthService = Depends(get_oauth_service)
):
    """
    OIDC Callback Handler
    
    Flow:
    1. Keycloak redirects here with authorization code
    2. Exchange code for tokens
    3. Store tokens securely (session/cookie/header)
    4. Redirect user to their original destination
    """
    try:
        logger.info("Processing OIDC callback from Keycloak")
        
        # Exchange authorization code for tokens
        tokens = await oauth_service.exchange_code_for_tokens(code, state)
        logger.info("Token exchange completed successfully")
        
        # Get user info to verify authentication
        user_info = await oauth_service.get_user_info(tokens.access_token)
        logger.info(f"User authenticated: {user_info.email}")
        
        # Create response with redirect
        if final_redirect:
            # Redirect to the original application with tokens
            # Option 1: Pass tokens as URL fragments (for SPA)
            redirect_url = f"{final_redirect}#access_token={tokens.access_token}&id_token={tokens.id_token or ''}"
            
            # Option 2: Pass tokens as query parameters (less secure, for testing)
            # redirect_url = f"{final_redirect}?access_token={tokens.access_token}"
            
            # Option 3: Set secure cookies and redirect (most secure)
            response = RedirectResponse(url=final_redirect, status_code=302)
            
            # Set secure HTTP-only cookies
            response.set_cookie(
                key="access_token",
                value=tokens.access_token,
                httponly=True,
                secure=True,
                samesite="lax",
                max_age=tokens.expires_in
            )
            
            if tokens.id_token:
                response.set_cookie(
                    key="id_token",
                    value=tokens.id_token,
                    httponly=True,
                    secure=True,
                    samesite="lax",
                    max_age=tokens.expires_in
                )
            
            if tokens.refresh_token:
                response.set_cookie(
                    key="refresh_token",
                    value=tokens.refresh_token,
                    httponly=True,
                    secure=True,
                    samesite="lax",
                    max_age=86400 * 30  # 30 days
                )
            
            logger.info(f"Redirecting authenticated user to: {final_redirect}")
            return response
        else:
            # No final redirect specified, return success page or default redirect
            return JSONResponse({
                "success": True,
                "message": "Authentication successful",
                "user": {
                    "sub": user_info.sub,
                    "email": user_info.email,
                    "name": user_info.name
                }
            })
            
    except Exception as e:
        logger.error(f"Callback error: {e}")
        
        # If there's a final_redirect, redirect there with error
        if final_redirect:
            error_url = f"{final_redirect}?error=auth_failed&error_description={str(e)}"
            return RedirectResponse(url=error_url, status_code=302)
        
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/logout")
async def logout(
    redirect_uri: Optional[str] = Query(None, description="Where to redirect after logout"),
    oauth_service: OAuthService = Depends(get_oauth_service)
):
    """
    Federation Gateway Logout
    
    Clears local session and optionally redirects to Keycloak logout
    """
    try:
        # Clear cookies
        response = RedirectResponse(
            url=redirect_uri or "/", 
            status_code=302
        )
        
        # Clear authentication cookies
        response.delete_cookie("access_token")
        response.delete_cookie("id_token") 
        response.delete_cookie("refresh_token")
        
        # Optional: Redirect to Keycloak logout for complete SSO logout
        if hasattr(oauth_service, 'server_metadata') and oauth_service.server_metadata:
            end_session_endpoint = oauth_service.server_metadata.get('end_session_endpoint')
            if end_session_endpoint and redirect_uri:
                logout_url = f"{end_session_endpoint}?post_logout_redirect_uri={redirect_uri}"
                response = RedirectResponse(url=logout_url, status_code=302)
        
        logger.info("User logged out successfully")
        return response
        
    except Exception as e:
        logger.error(f"Error during logout: {str(e)}")
        raise HTTPException(status_code=500, detail="Logout failed")

@router.post("/refresh")
async def refresh_access_token(
    refresh_token: str,
    oauth_service: OAuthService = Depends(get_oauth_service)
):
    """Refresh access token (API endpoint)"""
    try:
        logger.info("Refreshing access token")
        tokens = await oauth_service.refresh_token(refresh_token)
        return tokens
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/user")
async def get_current_user(
    user=Depends(get_auth_middleware)
):
    """Get current authenticated user (API endpoint)"""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        current_user = user.require_auth()
        logger.info(f"Current user retrieved: {current_user.get('sub', 'unknown')}")
        return current_user
    except Exception as e:
        logger.error(f"Error getting current user: {e}")
        raise HTTPException(status_code=401, detail="Authentication required")

@router.get("/health")
async def auth_health(
    oauth_service: OAuthService = Depends(get_oauth_service)
):
    """Check OAuth service health"""
    try:
        health = await oauth_service.health_check()
        return health
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

# Middleware to protect routes (optional)
@router.get("/protected")
async def protected_route(
    user=Depends(get_auth_middleware)
):
    """Example protected route"""
    try:
        current_user = user.require_auth()
        return {
            "message": "Access granted to protected resource",
            "user": current_user
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail="Authentication required")