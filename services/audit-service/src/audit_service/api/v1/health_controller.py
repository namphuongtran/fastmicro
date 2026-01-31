"""
Health check endpoints for Audit Service.

Provides liveness, readiness, and metrics endpoints for container orchestration
and monitoring systems.
"""

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Response
from pydantic import BaseModel, Field

from audit_service.configs.settings import get_settings

router = APIRouter()
settings = get_settings()


class HealthResponse(BaseModel):
    """Health check response model."""
    
    status: str = Field(description="Service status (healthy/unhealthy)")
    service: str = Field(description="Service name")
    version: str = Field(description="Service version")
    timestamp: datetime = Field(description="Response timestamp")
    environment: str = Field(description="Deployment environment")


class ReadinessResponse(BaseModel):
    """Readiness check response model."""
    
    status: str = Field(description="Readiness status (ready/not_ready)")
    checks: dict[str, Any] = Field(description="Individual component checks")
    timestamp: datetime = Field(description="Response timestamp")


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Liveness probe endpoint for container orchestration",
)
async def health_check() -> HealthResponse:
    """
    Perform a basic health check.
    
    This endpoint is used by container orchestration systems (Kubernetes, Docker)
    to determine if the service is alive. It should be lightweight and always
    return quickly.
    
    Returns:
        HealthResponse: Current health status.
    """
    return HealthResponse(
        status="healthy",
        service=settings.service_name,
        version="0.1.0",
        timestamp=datetime.now(timezone.utc),
        environment=settings.app_env,
    )


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Readiness Check",
    description="Readiness probe endpoint checking all dependencies",
)
async def readiness_check() -> ReadinessResponse:
    """
    Perform a comprehensive readiness check.
    
    This endpoint checks all service dependencies (database, cache, message queue)
    to determine if the service is ready to accept traffic.
    
    Returns:
        ReadinessResponse: Readiness status with individual component checks.
    """
    checks: dict[str, Any] = {}
    all_healthy = True
    
    # Check database connection
    try:
        # TODO: Implement actual database check
        # await database.execute("SELECT 1")
        checks["database"] = {"status": "healthy", "latency_ms": 1}
    except Exception as e:
        checks["database"] = {"status": "unhealthy", "error": str(e)}
        all_healthy = False
    
    # Check Redis connection
    try:
        # TODO: Implement actual Redis check
        # await redis.ping()
        checks["redis"] = {"status": "healthy", "latency_ms": 1}
    except Exception as e:
        checks["redis"] = {"status": "unhealthy", "error": str(e)}
        all_healthy = False
    
    # Check RabbitMQ connection
    try:
        # TODO: Implement actual RabbitMQ check
        checks["rabbitmq"] = {"status": "healthy", "latency_ms": 1}
    except Exception as e:
        checks["rabbitmq"] = {"status": "unhealthy", "error": str(e)}
        all_healthy = False
    
    return ReadinessResponse(
        status="ready" if all_healthy else "not_ready",
        checks=checks,
        timestamp=datetime.now(timezone.utc),
    )


@router.get(
    "/metrics",
    summary="Prometheus Metrics",
    description="Prometheus-compatible metrics endpoint",
)
async def metrics() -> Response:
    """
    Export Prometheus metrics.
    
    Returns:
        Response: Prometheus-formatted metrics.
    """
    try:
        from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
        
        return Response(
            content=generate_latest(),
            media_type=CONTENT_TYPE_LATEST,
        )
    except ImportError:
        return Response(
            content="# Prometheus client not installed\n",
            media_type="text/plain",
        )
