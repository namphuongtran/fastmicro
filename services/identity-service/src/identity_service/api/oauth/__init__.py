"""OAuth2 API routes package."""

from fastapi import APIRouter

from identity_service.api.oauth.authorize import router as authorize_router
from identity_service.api.oauth.discovery import router as discovery_router
from identity_service.api.oauth.introspection import router as introspection_router
from identity_service.api.oauth.token import router as token_router
from identity_service.api.oauth.userinfo import router as userinfo_router

# Create combined router
oauth_router = APIRouter()

# Include all OAuth2/OIDC routes
oauth_router.include_router(discovery_router)
oauth_router.include_router(authorize_router)
oauth_router.include_router(token_router)
oauth_router.include_router(introspection_router)
oauth_router.include_router(userinfo_router)

__all__ = ["oauth_router"]
