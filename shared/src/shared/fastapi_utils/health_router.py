"""FastAPI health check router factory.

Provides standardized health check endpoints for Kubernetes:
- /health - Basic health check
- /health/live - Liveness probe
- /health/ready - Readiness probe

Example:
    >>> from fastapi import FastAPI
    >>> from shared.fastapi_utils.health_router import create_health_router
    
    >>> app = FastAPI()
    >>> health_router = create_health_router(
    ...     service_name="my-service",
    ...     version="1.0.0",
    ... )
    >>> app.include_router(health_router)
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Response, status
from pydantic import BaseModel, Field

from shared.observability.health import (
    HealthCheckResult,
    HealthStatus,
    check_liveness,
    check_readiness,
    register_health_check,
)


class HealthResponse(BaseModel):
    """Basic health check response."""

    status: str = Field(description="Health status: healthy, unhealthy, or degraded")
    service: str = Field(description="Service name")
    version: str = Field(description="Service version")
    timestamp: datetime = Field(description="Current timestamp")


class LivenessResponse(BaseModel):
    """Liveness probe response."""

    status: str = Field(description="Liveness status")
    message: str | None = Field(default=None, description="Additional message")


class ReadinessResponse(BaseModel):
    """Readiness probe response."""

    status: str = Field(description="Overall readiness status")
    checks: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Individual health check results"
    )


class DetailedHealthResponse(BaseModel):
    """Detailed health response with all checks."""

    status: str = Field(description="Overall health status")
    service: str = Field(description="Service name")
    version: str = Field(description="Service version")
    timestamp: datetime = Field(description="Current timestamp")
    uptime_seconds: float | None = Field(default=None, description="Service uptime")
    checks: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Individual health check results"
    )


def create_health_router(
    *,
    service_name: str,
    version: str = "0.0.0",
    prefix: str = "/health",
    tags: list[str] | None = None,
    include_details: bool = True,
    startup_time: datetime | None = None,
) -> APIRouter:
    """Create a health check router with standardized endpoints.
    
    Creates a router with:
    - GET /health - Basic health check
    - GET /health/live - Kubernetes liveness probe
    - GET /health/ready - Kubernetes readiness probe
    
    Args:
        service_name: Name of the service
        version: Service version string
        prefix: URL prefix for health endpoints
        tags: OpenAPI tags for the router
        include_details: Include check details in /health endpoint
        startup_time: Service startup time for uptime calculation
        
    Returns:
        FastAPI router with health endpoints
        
    Example:
        >>> router = create_health_router(
        ...     service_name="user-service",
        ...     version="2.1.0",
        ...     startup_time=datetime.now(timezone.utc),
        ... )
        >>> app.include_router(router)
    """
    router = APIRouter(prefix=prefix, tags=tags or ["Health"])
    _startup_time = startup_time or datetime.now(UTC)

    @router.get(
        "",
        response_model=HealthResponse | DetailedHealthResponse,
        summary="Health Check",
        description="Basic health check endpoint",
    )
    async def health_check() -> HealthResponse | DetailedHealthResponse:
        """Basic health check endpoint.
        
        Returns service health status, name, and version.
        If include_details is True, also returns individual check results.
        """
        readiness = await check_readiness()
        now = datetime.now(UTC)

        if include_details:
            uptime = (now - _startup_time).total_seconds()
            return DetailedHealthResponse(
                status=readiness["status"],
                service=service_name,
                version=version,
                timestamp=now,
                uptime_seconds=uptime,
                checks=readiness.get("checks", []),
            )

        return HealthResponse(
            status=readiness["status"],
            service=service_name,
            version=version,
            timestamp=now,
        )

    @router.get(
        "/live",
        response_model=LivenessResponse,
        summary="Liveness Probe",
        description="Kubernetes liveness probe endpoint",
        responses={
            200: {"description": "Service is alive"},
            503: {"description": "Service is not alive"},
        },
    )
    async def liveness_probe(response: Response) -> LivenessResponse:
        """Kubernetes liveness probe.
        
        Returns 200 if the service is running.
        Kubernetes will restart the pod if this fails.
        """
        result = await check_liveness()

        if result.status != HealthStatus.HEALTHY:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

        return LivenessResponse(
            status=result.status.value,
            message=result.message,
        )

    @router.get(
        "/ready",
        response_model=ReadinessResponse,
        summary="Readiness Probe",
        description="Kubernetes readiness probe endpoint",
        responses={
            200: {"description": "Service is ready to receive traffic"},
            503: {"description": "Service is not ready"},
        },
    )
    async def readiness_probe(response: Response) -> ReadinessResponse:
        """Kubernetes readiness probe.
        
        Returns 200 if all critical dependencies are available.
        Kubernetes will stop routing traffic if this fails.
        """
        result = await check_readiness()

        if result["status"] != "healthy":
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

        return ReadinessResponse(
            status=result["status"],
            checks=result.get("checks", []),
        )

    return router


def create_database_health_check(
    name: str = "database",
    check_fn: Callable[[], Coroutine[Any, Any, bool]] | None = None,
    *,
    critical: bool = True,
    timeout_seconds: float = 5.0,
) -> None:
    """Create and register a database health check.
    
    Args:
        name: Health check name
        check_fn: Async function that returns True if healthy
        critical: Whether this is critical for readiness
        timeout_seconds: Timeout for the check
        
    Example:
        >>> async def check_db():
        ...     return await db_manager.health_check()
        >>> create_database_health_check(check_fn=check_db)
    """
    async def database_check() -> HealthCheckResult:
        if check_fn is None:
            return HealthCheckResult(
                name=name,
                status=HealthStatus.HEALTHY,
                message="No check configured",
            )

        try:
            is_healthy = await check_fn()
            return HealthCheckResult(
                name=name,
                status=HealthStatus.HEALTHY if is_healthy else HealthStatus.UNHEALTHY,
                message="Database connection OK" if is_healthy else "Database connection failed",
            )
        except Exception as e:
            return HealthCheckResult(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Database error: {e}",
            )

    register_health_check(
        name=name,
        check_fn=database_check,
        critical=critical,
        timeout_seconds=timeout_seconds,
    )


def create_cache_health_check(
    name: str = "cache",
    check_fn: Callable[[], Coroutine[Any, Any, bool]] | None = None,
    *,
    critical: bool = False,
    timeout_seconds: float = 3.0,
) -> None:
    """Create and register a cache health check.
    
    Args:
        name: Health check name
        check_fn: Async function that returns True if healthy
        critical: Whether this is critical for readiness
        timeout_seconds: Timeout for the check
        
    Example:
        >>> async def check_redis():
        ...     return await cache.health_check()
        >>> create_cache_health_check(check_fn=check_redis)
    """
    async def cache_check() -> HealthCheckResult:
        if check_fn is None:
            return HealthCheckResult(
                name=name,
                status=HealthStatus.HEALTHY,
                message="No check configured",
            )

        try:
            is_healthy = await check_fn()
            return HealthCheckResult(
                name=name,
                status=HealthStatus.HEALTHY if is_healthy else HealthStatus.DEGRADED,
                message="Cache connection OK" if is_healthy else "Cache connection failed",
            )
        except Exception as e:
            return HealthCheckResult(
                name=name,
                status=HealthStatus.DEGRADED,
                message=f"Cache error: {e}",
            )

    register_health_check(
        name=name,
        check_fn=cache_check,
        critical=critical,
        timeout_seconds=timeout_seconds,
    )


def create_external_service_health_check(
    name: str,
    check_fn: Callable[[], Coroutine[Any, Any, bool]],
    *,
    critical: bool = False,
    timeout_seconds: float = 10.0,
) -> None:
    """Create and register an external service health check.
    
    Args:
        name: Health check name
        check_fn: Async function that returns True if healthy
        critical: Whether this is critical for readiness
        timeout_seconds: Timeout for the check
        
    Example:
        >>> async def check_payment_service():
        ...     return await http_client.get("/health").is_ok()
        >>> create_external_service_health_check(
        ...     "payment-service",
        ...     check_payment_service,
        ...     critical=True,
        ... )
    """
    async def service_check() -> HealthCheckResult:
        try:
            is_healthy = await check_fn()
            return HealthCheckResult(
                name=name,
                status=HealthStatus.HEALTHY if is_healthy else HealthStatus.UNHEALTHY,
                message=f"{name} is available" if is_healthy else f"{name} is unavailable",
            )
        except Exception as e:
            return HealthCheckResult(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"{name} error: {e}",
            )

    register_health_check(
        name=name,
        check_fn=service_check,
        critical=critical,
        timeout_seconds=timeout_seconds,
    )
