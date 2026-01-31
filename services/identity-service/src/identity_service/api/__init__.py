"""API layer package."""

from identity_service.api.health import router as health_router
from identity_service.api.oauth import oauth_router

__all__ = ["health_router", "oauth_router"]
