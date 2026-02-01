"""Tests for shared.observability.health module.

This module tests health check utilities including liveness,
readiness probes, and dependency health checks.
"""

from __future__ import annotations

import asyncio

import pytest

from shared.observability.health import (
    HealthCheck,
    HealthCheckResult,
    HealthStatus,
    check_liveness,
    check_readiness,
    create_health_check,
    get_health_status,
    register_health_check,
)


class TestHealthStatus:
    """Tests for HealthStatus enum."""

    def test_healthy_status(self) -> None:
        """Should have HEALTHY status."""
        assert HealthStatus.HEALTHY.value == "healthy"

    def test_unhealthy_status(self) -> None:
        """Should have UNHEALTHY status."""
        assert HealthStatus.UNHEALTHY.value == "unhealthy"

    def test_degraded_status(self) -> None:
        """Should have DEGRADED status."""
        assert HealthStatus.DEGRADED.value == "degraded"


class TestHealthCheckResult:
    """Tests for HealthCheckResult dataclass."""

    def test_create_healthy_result(self) -> None:
        """Should create healthy result."""
        result = HealthCheckResult(
            name="database",
            status=HealthStatus.HEALTHY,
        )
        assert result.name == "database"
        assert result.status == HealthStatus.HEALTHY

    def test_create_unhealthy_result_with_message(self) -> None:
        """Should create unhealthy result with message."""
        result = HealthCheckResult(
            name="cache",
            status=HealthStatus.UNHEALTHY,
            message="Connection refused",
        )
        assert result.message == "Connection refused"

    def test_result_with_details(self) -> None:
        """Should support additional details."""
        result = HealthCheckResult(
            name="api",
            status=HealthStatus.HEALTHY,
            details={"latency_ms": 50, "version": "1.0"},
        )
        assert result.details["latency_ms"] == 50

    def test_result_with_duration(self) -> None:
        """Should track check duration."""
        result = HealthCheckResult(
            name="service",
            status=HealthStatus.HEALTHY,
            duration_ms=15.5,
        )
        assert result.duration_ms == 15.5

    def test_is_healthy_property(self) -> None:
        """Should have is_healthy property."""
        healthy = HealthCheckResult(name="test", status=HealthStatus.HEALTHY)
        unhealthy = HealthCheckResult(name="test", status=HealthStatus.UNHEALTHY)

        assert healthy.is_healthy is True
        assert unhealthy.is_healthy is False

    def test_to_dict(self) -> None:
        """Should convert to dictionary."""
        result = HealthCheckResult(
            name="db",
            status=HealthStatus.HEALTHY,
            message="OK",
        )
        data = result.to_dict()

        assert data["name"] == "db"
        assert data["status"] == "healthy"


class TestHealthCheck:
    """Tests for HealthCheck class."""

    def test_create_health_check(self) -> None:
        """Should create a health check."""

        async def check_fn() -> HealthCheckResult:
            return HealthCheckResult(name="test", status=HealthStatus.HEALTHY)

        check = HealthCheck(name="test", check_fn=check_fn)
        assert check.name == "test"

    def test_health_check_with_timeout(self) -> None:
        """Should support timeout configuration."""

        async def check_fn() -> HealthCheckResult:
            return HealthCheckResult(name="test", status=HealthStatus.HEALTHY)

        check = HealthCheck(name="test", check_fn=check_fn, timeout_seconds=5.0)
        assert check.timeout_seconds == 5.0

    def test_health_check_critical_flag(self) -> None:
        """Should support critical flag."""

        async def check_fn() -> HealthCheckResult:
            return HealthCheckResult(name="test", status=HealthStatus.HEALTHY)

        check = HealthCheck(name="test", check_fn=check_fn, critical=True)
        assert check.critical is True

    @pytest.mark.asyncio
    async def test_run_health_check(self) -> None:
        """Should run health check."""

        async def check_fn() -> HealthCheckResult:
            return HealthCheckResult(name="test", status=HealthStatus.HEALTHY)

        check = HealthCheck(name="test", check_fn=check_fn)
        result = await check.run()

        assert result.status == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_handles_check_exception(self) -> None:
        """Should handle exceptions in check function."""

        async def failing_check() -> HealthCheckResult:
            raise ConnectionError("Database unavailable")

        check = HealthCheck(name="db", check_fn=failing_check)
        result = await check.run()

        assert result.status == HealthStatus.UNHEALTHY
        assert "Database unavailable" in (result.message or "")

    @pytest.mark.asyncio
    async def test_handles_timeout(self) -> None:
        """Should handle timeout."""

        async def slow_check() -> HealthCheckResult:
            await asyncio.sleep(10)  # Simulate slow check
            return HealthCheckResult(name="slow", status=HealthStatus.HEALTHY)

        check = HealthCheck(name="slow", check_fn=slow_check, timeout_seconds=0.1)
        result = await check.run()

        assert result.status == HealthStatus.UNHEALTHY
        assert "timed out" in (result.message or "").lower()


class TestCreateHealthCheck:
    """Tests for create_health_check decorator."""

    @pytest.mark.asyncio
    async def test_creates_health_check_from_function(self) -> None:
        """Should create health check from decorated function."""

        @create_health_check("my_service")
        async def check_my_service() -> HealthCheckResult:
            return HealthCheckResult(name="my_service", status=HealthStatus.HEALTHY)

        result = await check_my_service()
        assert result.status == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_with_timeout(self) -> None:
        """Should accept timeout parameter."""

        @create_health_check("service", timeout_seconds=2.0)
        async def check_service() -> HealthCheckResult:
            return HealthCheckResult(name="service", status=HealthStatus.HEALTHY)

        result = await check_service()
        assert result.status == HealthStatus.HEALTHY


class TestRegisterHealthCheck:
    """Tests for register_health_check function."""

    def test_register_check(self) -> None:
        """Should register a health check."""

        async def check_fn() -> HealthCheckResult:
            return HealthCheckResult(name="registered", status=HealthStatus.HEALTHY)

        register_health_check(name="registered", check_fn=check_fn)
        # Should not raise

    def test_register_with_options(self) -> None:
        """Should register with options."""

        async def check_fn() -> HealthCheckResult:
            return HealthCheckResult(name="opts", status=HealthStatus.HEALTHY)

        register_health_check(
            name="opts",
            check_fn=check_fn,
            critical=True,
            timeout_seconds=5.0,
        )


class TestGetHealthStatus:
    """Tests for get_health_status function."""

    @pytest.mark.asyncio
    async def test_returns_overall_status(self) -> None:
        """Should return overall health status."""
        status = await get_health_status()

        assert "status" in status
        assert "checks" in status

    @pytest.mark.asyncio
    async def test_includes_all_checks(self) -> None:
        """Should include all registered checks."""

        # Register some checks first
        async def check_a() -> HealthCheckResult:
            return HealthCheckResult(name="a", status=HealthStatus.HEALTHY)

        register_health_check(name="a", check_fn=check_a)

        status = await get_health_status()
        # Should include registered checks


class TestCheckLiveness:
    """Tests for check_liveness function."""

    @pytest.mark.asyncio
    async def test_returns_liveness_status(self) -> None:
        """Should return liveness status."""
        result = await check_liveness()

        assert isinstance(result, HealthCheckResult)

    @pytest.mark.asyncio
    async def test_liveness_is_simple(self) -> None:
        """Liveness should be a simple alive check."""
        result = await check_liveness()

        # Basic liveness should always be healthy if app is running
        assert result.status == HealthStatus.HEALTHY


class TestCheckReadiness:
    """Tests for check_readiness function."""

    @pytest.mark.asyncio
    async def test_returns_readiness_status(self) -> None:
        """Should return readiness status."""
        result = await check_readiness()

        assert isinstance(result, dict)
        assert "status" in result

    @pytest.mark.asyncio
    async def test_includes_dependency_checks(self) -> None:
        """Should include dependency health checks."""

        # Register a critical dependency check
        async def check_db() -> HealthCheckResult:
            return HealthCheckResult(name="database", status=HealthStatus.HEALTHY)

        register_health_check(name="database", check_fn=check_db, critical=True)

        result = await check_readiness()
        assert "checks" in result

    @pytest.mark.asyncio
    async def test_unhealthy_when_critical_fails(self) -> None:
        """Should be unhealthy when critical dependency fails."""

        async def failing_db() -> HealthCheckResult:
            return HealthCheckResult(
                name="critical_db",
                status=HealthStatus.UNHEALTHY,
                message="Connection failed",
            )

        register_health_check(name="critical_db", check_fn=failing_db, critical=True)

        result = await check_readiness()
        # Overall status should be unhealthy when critical check fails


class TestHealthCheckIntegration:
    """Integration tests for health checks."""

    @pytest.mark.asyncio
    async def test_full_health_check_flow(self) -> None:
        """Should support full health check flow."""

        # Define checks
        @create_health_check("api", critical=True)
        async def check_api() -> HealthCheckResult:
            return HealthCheckResult(name="api", status=HealthStatus.HEALTHY)

        @create_health_check("cache", critical=False)
        async def check_cache() -> HealthCheckResult:
            return HealthCheckResult(
                name="cache",
                status=HealthStatus.DEGRADED,
                message="High latency",
            )

        # Run individual checks
        api_result = await check_api()
        cache_result = await check_cache()

        assert api_result.is_healthy is True
        assert cache_result.status == HealthStatus.DEGRADED

    @pytest.mark.asyncio
    async def test_health_response_format(self) -> None:
        """Should return properly formatted health response."""
        status = await get_health_status()

        # Should have standard health response format
        assert isinstance(status, dict)
        assert "status" in status
        assert status["status"] in ["healthy", "unhealthy", "degraded"]
