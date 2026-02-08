"""API layer package.

Note: Admin API (clients, users) has been moved to identity-admin-service
for security isolation. This service now serves only public IdP endpoints.
"""

from identity_service.api.auth import auth_router
from identity_service.api.health import router as health_router
from identity_service.api.oauth import oauth_router

__all__ = ["auth_router", "health_router", "oauth_router"]
