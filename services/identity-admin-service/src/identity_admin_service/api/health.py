"""Health check endpoints for Identity Admin Service."""

from fastapi import APIRouter

from identity_admin_service import __version__
from identity_admin_service.configs import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    """Basic health check endpoint.

    Returns:
        Service health status with version info.
    """
    settings = get_settings()
    return {
        "status": "healthy",
        "service": "identity-admin-service",
        "version": __version__,
        "environment": settings.app_env,
    }


@router.get("/healthz")
async def healthz() -> dict:
    """Kubernetes liveness probe endpoint.

    Returns:
        Simple status for liveness check.
    """
    return {"status": "ok"}


@router.get("/readyz")
async def readyz() -> dict:
    """Kubernetes readiness probe endpoint.

    Returns:
        Readiness status including dependencies.
    """
    # TODO: Add actual dependency checks (database, identity-service)
    return {"status": "ready"}
