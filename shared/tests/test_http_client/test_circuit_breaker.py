"""Tests for shared.http_client.circuit_breaker module.

This module tests the circuit breaker pattern implementation.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shared.http_client.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
    CircuitOpenError,
)


class TestCircuitBreakerConfig:
    """Tests for CircuitBreakerConfig."""

    def test_create_config(self) -> None:
        """Should create circuit breaker config."""
        config = CircuitBreakerConfig(
            failure_threshold=5,
            recovery_timeout=30.0,
            half_open_max_calls=3,
        )
        
        assert config.failure_threshold == 5
        assert config.recovery_timeout == 30.0
        assert config.half_open_max_calls == 3

    def test_config_defaults(self) -> None:
        """Should have sensible defaults."""
        config = CircuitBreakerConfig()
        
        assert config.failure_threshold == 5
        assert config.recovery_timeout == 30.0
        assert config.half_open_max_calls == 1
        assert config.success_threshold == 2


class TestCircuitBreaker:
    """Tests for CircuitBreaker class."""

    @pytest.fixture
    def config(self) -> CircuitBreakerConfig:
        """Create test config."""
        return CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=0.1,  # Small for fast tests
            half_open_max_calls=2,
            success_threshold=2,
        )

    @pytest.fixture
    def breaker(self, config: CircuitBreakerConfig) -> CircuitBreaker:
        """Create test circuit breaker."""
        return CircuitBreaker("test-service", config)

    def test_create_breaker(self, config: CircuitBreakerConfig) -> None:
        """Should create circuit breaker."""
        breaker = CircuitBreaker("my-service", config)
        
        assert breaker.name == "my-service"
        assert breaker.state == CircuitState.CLOSED

    def test_initial_state_is_closed(self, breaker: CircuitBreaker) -> None:
        """Should start in closed state."""
        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_success_keeps_closed(self, breaker: CircuitBreaker) -> None:
        """Should stay closed on success."""
        async def success_call():
            return "success"
        
        result = await breaker.call(success_call)
        
        assert result == "success"
        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_failure_increments_count(
        self, breaker: CircuitBreaker
    ) -> None:
        """Should increment failure count."""
        async def failing_call():
            raise ValueError("error")
        
        with pytest.raises(ValueError):
            await breaker.call(failing_call)
        
        assert breaker.failure_count == 1
        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_opens_after_threshold(
        self, breaker: CircuitBreaker
    ) -> None:
        """Should open after failure threshold reached."""
        async def failing_call():
            raise ValueError("error")
        
        # Fail until threshold
        for _ in range(3):
            with pytest.raises(ValueError):
                await breaker.call(failing_call)
        
        assert breaker.state == CircuitState.OPEN
        assert breaker.failure_count == 3

    @pytest.mark.asyncio
    async def test_rejects_calls_when_open(
        self, breaker: CircuitBreaker
    ) -> None:
        """Should reject calls when open."""
        # Force open state
        breaker._state = CircuitState.OPEN
        breaker._opened_at = datetime.now(timezone.utc)
        
        async def any_call():
            return "should not reach"
        
        with pytest.raises(CircuitOpenError) as exc_info:
            await breaker.call(any_call)
        
        assert "test-service" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_transitions_to_half_open(
        self, breaker: CircuitBreaker
    ) -> None:
        """Should transition to half-open after recovery timeout."""
        async def failing_call():
            raise ValueError("error")
        
        async def success_call():
            return "success"
        
        # Open the circuit
        for _ in range(3):
            with pytest.raises(ValueError):
                await breaker.call(failing_call)
        
        assert breaker.state == CircuitState.OPEN
        
        # Wait for recovery timeout
        await asyncio.sleep(0.15)
        
        # Next call should be allowed (half-open)
        result = await breaker.call(success_call)
        
        assert breaker.state == CircuitState.HALF_OPEN
        assert result == "success"

    @pytest.mark.asyncio
    async def test_closes_after_success_in_half_open(
        self, breaker: CircuitBreaker
    ) -> None:
        """Should close after successes in half-open state."""
        async def success_call():
            return "success"
        
        # Set to half-open state manually
        breaker._state = CircuitState.HALF_OPEN
        breaker._half_open_successes = 0
        
        # Succeed twice (success_threshold = 2)
        await breaker.call(success_call)
        await breaker.call(success_call)
        
        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_reopens_on_failure_in_half_open(
        self, breaker: CircuitBreaker
    ) -> None:
        """Should reopen on failure in half-open state."""
        async def failing_call():
            raise ValueError("error")
        
        # Set to half-open state manually
        breaker._state = CircuitState.HALF_OPEN
        breaker._half_open_successes = 0
        
        with pytest.raises(ValueError):
            await breaker.call(failing_call)
        
        assert breaker.state == CircuitState.OPEN

    def test_reset(self, breaker: CircuitBreaker) -> None:
        """Should reset circuit breaker."""
        # Simulate some failures
        breaker._failure_count = 5
        breaker._state = CircuitState.OPEN
        
        breaker.reset()
        
        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0

    def test_get_stats(self, breaker: CircuitBreaker) -> None:
        """Should return circuit breaker stats."""
        stats = breaker.get_stats()
        
        assert "name" in stats
        assert "state" in stats
        assert "failure_count" in stats
        assert stats["name"] == "test-service"


class TestCircuitOpenError:
    """Tests for CircuitOpenError."""

    def test_create_error(self) -> None:
        """Should create circuit open error."""
        error = CircuitOpenError("my-service")
        
        assert "my-service" in str(error)
        assert error.service_name == "my-service"

    def test_error_with_retry_after(self) -> None:
        """Should include retry after hint."""
        error = CircuitOpenError("my-service", retry_after=30.0)
        
        assert error.retry_after == 30.0
