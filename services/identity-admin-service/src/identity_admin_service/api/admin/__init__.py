"""Admin API routes for identity service management.

Provides administrative endpoints for:
- OAuth2 client management
- User management
- System configuration
"""

from identity_admin_service.api.admin.clients import router as clients_router
from identity_admin_service.api.admin.users import router as users_router

__all__ = [
    "clients_router",
    "users_router",
]
