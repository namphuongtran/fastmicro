"""Health check endpoints."""

from datetime import UTC, datetime

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    service: str
    version: str
    timestamp: str


class ReadinessResponse(BaseModel):
    """Readiness check response."""

    status: str
    checks: dict[str, str]


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Basic health check endpoint.

    Returns:
        Service health status.
    """
    from identity_service import __version__

    return HealthResponse(
        status="healthy",
        service="identity-service",
        version=__version__,
        timestamp=datetime.now(UTC).isoformat(),
    )


@router.get("/ready", response_model=ReadinessResponse)
async def readiness_check() -> ReadinessResponse:
    """Readiness check with dependency status.

    Returns:
        Readiness status with dependency checks.
    """
    checks = {
        "database": "healthy",  # TODO: Add actual DB check
        "redis": "healthy",  # TODO: Add actual Redis check
        "keys": "healthy",  # TODO: Add key availability check
    }

    # Determine overall status
    all_healthy = all(v == "healthy" for v in checks.values())

    return ReadinessResponse(
        status="ready" if all_healthy else "not_ready",
        checks=checks,
    )


@router.get("/live")
async def liveness_check() -> dict:
    """Kubernetes liveness probe.

    Returns:
        Simple OK response.
    """
    return {"status": "alive"}
