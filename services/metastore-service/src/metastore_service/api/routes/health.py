"""Health check endpoints using shared library router.

Uses the standardized health router from the shared library for
Kubernetes-compatible liveness and readiness probes.
"""

from __future__ import annotations

from datetime import datetime, timezone

from shared.fastapi_utils.health_router import create_health_router

from metastore_service.configs.settings import get_settings

settings = get_settings()

# Create health router using shared library factory
router = create_health_router(
    service_name=settings.app_name,
    version=settings.app_version,
    prefix="/health",
    tags=["Health"],
    include_details=True,
    startup_time=datetime.now(timezone.utc),
)
