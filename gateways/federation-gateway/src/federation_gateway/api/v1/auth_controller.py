"""
Authentication API controller
"""

import logging
from fastapi import APIRouter, Request, HTTPException, Depends, Query
from fastapi.responses import RedirectResponse
from authlib.integrations.starlette_client import OAuthError
from settings.settings_manager import SettingsManager
from src.federation_gateway.application.services.token_service import TokenService
from src.federation_gateway.application.services.auth_service import AuthService
from src.federation_gateway.domain.entities.token_validation_response import TokenValidationResponse
from src.federation_gateway.domain.entities.user_info import UserInfo
from src.federation_gateway.configs.settings import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])


# Dependency injection
def get_token_service(settings: SettingsManager = Depends(get_settings)) -> TokenService:
    """Get token service dependency."""
    return TokenService(settings)


def get_auth_service(
    settings: SettingsManager = Depends(get_settings),
    token_service: TokenService = Depends(get_token_service)
) -> AuthService:
    """Get authentication service dependency."""
    return AuthService(settings, token_service)


@router.get("/login")
async def login(
    request: Request,
    redirect_uri: str = Query(..., description="URI to redirect after successful authentication")
):
    """Initiate OIDC login flow."""
    
    # Store the original redirect URI in session
    request.session["redirect_uri"] = redirect_uri
    
    # Get OAuth client from app state
    oauth = request.app.state.oauth
    client = oauth.create_client("oidc")
    
    # Generate callback URL
    callback_url = str(request.url_for("auth_callback"))
    
    try:
        # Redirect to IdP for authentication
        return await client.authorize_redirect(request, callback_url)
    except Exception as e:
        logger.error(f"Error initiating login: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to initiate login")


@router.get("/callback")
async def callback(
    request: Request,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Handle OIDC callback from IdP."""
    
    # Get the original redirect URI from session
    redirect_uri = request.session.get("redirect_uri")
    if not redirect_uri:
        raise HTTPException(status_code=400, detail="Missing redirect URI in session")
    
    # Get OAuth client from app state
    oauth = request.app.state.oauth
    client = oauth.create_client("oidc")
    
    try:
        # Exchange authorization code for tokens
        token = await client.authorize_access_token(request)
        
        # Handle authentication through service
        auth_result = await auth_service.handle_successful_auth(token)
        
        # Clean up session
        request.session.pop("redirect_uri", None)
        
        if not auth_result.success:
            # Authentication failed
            error_url = f"{redirect_uri}?error={auth_result.error}&error_description={auth_result.error_description}"
            return RedirectResponse(url=error_url)
        
        # Redirect back to the original application with token
        redirect_url = f"{redirect_uri}?token={auth_result.access_token}&token_type=Bearer"
        return RedirectResponse(url=redirect_url)
        
    except OAuthError as e:
        logger.error(f"OAuth error during callback: {str(e)}")
        error_url = f"{redirect_uri}?error=oauth_error&error_description={str(e)}"
        return RedirectResponse(url=error_url)
    except Exception as e:
        logger.error(f"Unexpected error during callback: {str(e)}")
        error_url = f"{redirect_uri}?error=server_error&error_description=Authentication failed"
        return RedirectResponse(url=error_url)


@router.get("/userinfo", response_model=UserInfo)
async def get_userinfo(
    request: Request,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Get user information from JWT token."""
    
    # Get user info through service
    auth_header = request.headers.get("Authorization")
    payload = auth_service.validate_token_and_get_user_info(auth_header)
    
    # Return user info
    return UserInfo(
        sub=payload.get("sub"),
        email=payload.get("email"),
        name=payload.get("name"),
        preferred_username=payload.get("preferred_username"),
        given_name=payload.get("given_name"),
        family_name=payload.get("family_name"),
        picture=payload.get("picture")
    )


@router.post("/logout")
async def logout(
    request: Request,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Logout endpoint."""
    
    # Process logout through service
    auth_header = request.headers.get("Authorization")
    success = auth_service.logout_user(auth_header)
    
    if not success:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return {"message": "Logged out successfully"}


@router.get("/validate", response_model=TokenValidationResponse)
async def validate_token(
    request: Request,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Validate JWT token."""
    
    # Validate token through service
    auth_header = request.headers.get("Authorization")
    payload = auth_service.validate_token_and_get_user_info(auth_header)
    
    return TokenValidationResponse(
        valid=True,
        sub=payload.get("sub"),
        exp=payload.get("exp"),
        iat=payload.get("iat")
    )
