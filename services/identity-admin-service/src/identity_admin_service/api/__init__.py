"""API layer package for Identity Admin Service."""

from identity_admin_service.api.admin.clients import router as clients_router
from identity_admin_service.api.admin.users import router as users_router
from identity_admin_service.api.health import router as health_router

__all__ = ["health_router", "clients_router", "users_router"]
