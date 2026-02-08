"""Web module for identity service.

Note: Admin web UI has been moved to identity-admin-service
for security isolation. This module only serves public OAuth web pages.
"""

from identity_service.api.web.routes import router

__all__ = ["router"]
