"""API routes package."""

from metastore_service.api.routes.configuration import router as configuration_router
from metastore_service.api.routes.feature_flags import router as feature_flag_router
from metastore_service.api.routes.health import router as health_router
from metastore_service.api.routes.metadata import router as metadata_router

__all__ = [
    "health_router",
    "metadata_router",
    "feature_flag_router",
    "configuration_router",
]
