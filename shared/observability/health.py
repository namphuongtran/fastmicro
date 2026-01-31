"""Health check utilities for microservices.

This module provides health check functionality for Kubernetes
liveness and readiness probes.
"""

from __future__ import annotations

import asyncio
import functools
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Coroutine


class HealthStatus(Enum):
    """Health check status values."""
    
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    
    name: str
    status: HealthStatus
    message: str | None = None
    details: dict[str, Any] = field(default_factory=dict)
    duration_ms: float | None = None

    @property
    def is_healthy(self) -> bool:
        """Check if the result indicates healthy status.
        
        Returns:
            True if status is HEALTHY.
        """
        return self.status == HealthStatus.HEALTHY

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary.
        
        Returns:
            Dictionary representation.
        """
        result: dict[str, Any] = {
            "name": self.name,
            "status": self.status.value,
        }
        
        if self.message:
            result["message"] = self.message
        
        if self.details:
            result["details"] = self.details
        
        if self.duration_ms is not None:
            result["duration_ms"] = self.duration_ms
        
        return result


# Type alias for health check functions
HealthCheckFn = Callable[[], Coroutine[Any, Any, HealthCheckResult]]


@dataclass
class HealthCheck:
    """A registered health check."""
    
    name: str
    check_fn: HealthCheckFn
    timeout_seconds: float = 10.0
    critical: bool = False

    async def run(self) -> HealthCheckResult:
        """Run the health check.
        
        Returns:
            Health check result.
        """
        start = time.perf_counter()
        
        try:
            result = await asyncio.wait_for(
                self.check_fn(),
                timeout=self.timeout_seconds,
            )
            result.duration_ms = (time.perf_counter() - start) * 1000
            return result
        
        except asyncio.TimeoutError:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check timed out after {self.timeout_seconds}s",
                duration_ms=(time.perf_counter() - start) * 1000,
            )
        
        except Exception as e:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=str(e),
                duration_ms=(time.perf_counter() - start) * 1000,
            )


# Global registry of health checks
_health_checks: dict[str, HealthCheck] = {}


def register_health_check(
    name: str,
    check_fn: HealthCheckFn,
    *,
    critical: bool = False,
    timeout_seconds: float = 10.0,
) -> None:
    """Register a health check.
    
    Args:
        name: Health check name.
        check_fn: Async function that returns HealthCheckResult.
        critical: Whether this check is critical for readiness.
        timeout_seconds: Timeout for the check.
    """
    _health_checks[name] = HealthCheck(
        name=name,
        check_fn=check_fn,
        timeout_seconds=timeout_seconds,
        critical=critical,
    )


def create_health_check(
    name: str,
    *,
    critical: bool = False,
    timeout_seconds: float = 10.0,
) -> Callable[[HealthCheckFn], HealthCheckFn]:
    """Decorator to create a health check.
    
    Args:
        name: Health check name.
        critical: Whether this check is critical for readiness.
        timeout_seconds: Timeout for the check.
        
    Returns:
        Decorator function.
        
    Example:
        @create_health_check("database", critical=True)
        async def check_database() -> HealthCheckResult:
            ...
    """
    def decorator(func: HealthCheckFn) -> HealthCheckFn:
        register_health_check(
            name=name,
            check_fn=func,
            critical=critical,
            timeout_seconds=timeout_seconds,
        )
        return func
    
    return decorator


async def check_liveness() -> HealthCheckResult:
    """Check if the application is alive.
    
    Liveness probes indicate if the application is running.
    A simple check that always returns healthy if the app is responsive.
    
    Returns:
        Health check result.
    """
    return HealthCheckResult(
        name="liveness",
        status=HealthStatus.HEALTHY,
        message="Application is running",
    )


async def check_readiness() -> dict[str, Any]:
    """Check if the application is ready to serve traffic.
    
    Readiness probes check that all dependencies are available.
    
    Returns:
        Dictionary with overall status and individual check results.
    """
    results: list[HealthCheckResult] = []
    
    # Run all registered checks
    for name, check in _health_checks.items():
        result = await check.run()
        results.append(result)
    
    # Determine overall status
    has_unhealthy_critical = any(
        result.status == HealthStatus.UNHEALTHY
        and _health_checks.get(result.name, HealthCheck(name="", check_fn=check_liveness)).critical
        for result in results
    )
    
    has_unhealthy = any(
        result.status == HealthStatus.UNHEALTHY
        for result in results
    )
    
    has_degraded = any(
        result.status == HealthStatus.DEGRADED
        for result in results
    )
    
    if has_unhealthy_critical or (has_unhealthy and not results):
        overall_status = "unhealthy"
    elif has_unhealthy or has_degraded:
        overall_status = "degraded"
    else:
        overall_status = "healthy"
    
    return {
        "status": overall_status,
        "checks": [r.to_dict() for r in results],
    }


async def get_health_status() -> dict[str, Any]:
    """Get overall health status.
    
    Returns:
        Dictionary with status and all check results.
    """
    return await check_readiness()


__all__ = [
    "HealthStatus",
    "HealthCheckResult",
    "HealthCheck",
    "register_health_check",
    "create_health_check",
    "check_liveness",
    "check_readiness",
    "get_health_status",
]
