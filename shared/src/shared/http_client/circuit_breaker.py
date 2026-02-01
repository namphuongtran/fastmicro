"""Circuit breaker pattern implementation.

This module provides a circuit breaker for resilient service calls:
- CircuitBreaker: Main circuit breaker implementation
- CircuitBreakerConfig: Configuration options
- CircuitState: Circuit states (CLOSED, OPEN, HALF_OPEN)
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from collections.abc import Awaitable

T = TypeVar("T")


class CircuitState(str, Enum):
    """Circuit breaker states.

    CLOSED: Normal operation, requests pass through.
    OPEN: Failures exceeded threshold, requests are rejected.
    HALF_OPEN: Testing recovery, limited requests allowed.
    """

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpenError(Exception):
    """Error raised when circuit is open.

    Attributes:
        service_name: Name of the service.
        retry_after: Suggested retry time in seconds.
    """

    def __init__(
        self,
        service_name: str,
        retry_after: float | None = None,
    ) -> None:
        """Initialize circuit open error.

        Args:
            service_name: Name of the service.
            retry_after: Suggested retry time in seconds.
        """
        message = f"Circuit breaker open for service: {service_name}"
        if retry_after:
            message += f" (retry after {retry_after}s)"
        super().__init__(message)
        self.service_name = service_name
        self.retry_after = retry_after


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker.

    Attributes:
        failure_threshold: Number of failures before opening circuit.
        recovery_timeout: Seconds to wait before trying recovery.
        half_open_max_calls: Max calls allowed in half-open state.
        success_threshold: Successes needed to close circuit.
        excluded_exceptions: Exceptions that don't count as failures.
    """

    failure_threshold: int = 5
    recovery_timeout: float = 30.0
    half_open_max_calls: int = 1
    success_threshold: int = 2
    excluded_exceptions: tuple[type[Exception], ...] = ()


class CircuitBreaker:
    """Circuit breaker for resilient service calls.

    Implements the circuit breaker pattern to prevent cascading failures:

    1. CLOSED state: Normal operation, failures are counted
    2. OPEN state: After threshold failures, requests are rejected
    3. HALF_OPEN state: After recovery timeout, limited requests are allowed

    Example:
        >>> breaker = CircuitBreaker("user-service", CircuitBreakerConfig())
        >>> async def fetch_user():
        ...     return await http_client.get("/users/1")
        ...
        >>> try:
        ...     result = await breaker.call(fetch_user)
        ... except CircuitOpenError:
        ...     # Service is unavailable, use fallback
        ...     pass
    """

    def __init__(
        self,
        name: str,
        config: CircuitBreakerConfig | None = None,
    ) -> None:
        """Initialize circuit breaker.

        Args:
            name: Service name for identification.
            config: Circuit breaker configuration.
        """
        self._name = name
        self._config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._half_open_successes = 0
        self._opened_at: datetime | None = None
        self._lock = asyncio.Lock()

    @property
    def name(self) -> str:
        """Get circuit breaker name."""
        return self._name

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        return self._state

    @property
    def failure_count(self) -> int:
        """Get current failure count."""
        return self._failure_count

    async def call(
        self,
        func: Callable[[], Awaitable[T]],
    ) -> T:
        """Execute function through circuit breaker.

        Args:
            func: Async function to execute.

        Returns:
            Result of the function.

        Raises:
            CircuitOpenError: If circuit is open.
            Exception: Original exception from the function.
        """
        async with self._lock:
            await self._check_state()

        try:
            result = await func()
            await self._on_success()
            return result
        except Exception as e:
            if not isinstance(e, self._config.excluded_exceptions):
                await self._on_failure()
            raise

    async def _check_state(self) -> None:
        """Check and potentially transition state."""
        if self._state == CircuitState.OPEN:
            if self._should_attempt_recovery():
                self._state = CircuitState.HALF_OPEN
                self._half_open_successes = 0
            else:
                retry_after = self._get_retry_after()
                raise CircuitOpenError(self._name, retry_after)

    def _should_attempt_recovery(self) -> bool:
        """Check if recovery should be attempted."""
        if self._opened_at is None:
            return False

        elapsed = (datetime.now(UTC) - self._opened_at).total_seconds()
        return elapsed >= self._config.recovery_timeout

    def _get_retry_after(self) -> float | None:
        """Calculate retry after time."""
        if self._opened_at is None:
            return None

        elapsed = (datetime.now(UTC) - self._opened_at).total_seconds()
        remaining = self._config.recovery_timeout - elapsed
        return max(0, remaining)

    async def _on_success(self) -> None:
        """Handle successful call."""
        async with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._half_open_successes += 1
                if self._half_open_successes >= self._config.success_threshold:
                    self._close()
            else:
                # Reset failure count on success in closed state
                self._success_count += 1

    async def _on_failure(self) -> None:
        """Handle failed call."""
        async with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._open()
            elif self._state == CircuitState.CLOSED:
                self._failure_count += 1
                if self._failure_count >= self._config.failure_threshold:
                    self._open()

    def _open(self) -> None:
        """Open the circuit."""
        self._state = CircuitState.OPEN
        self._opened_at = datetime.now(UTC)

    def _close(self) -> None:
        """Close the circuit."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._half_open_successes = 0
        self._opened_at = None

    def reset(self) -> None:
        """Reset circuit breaker to initial state."""
        self._close()

    def get_stats(self) -> dict[str, Any]:
        """Get circuit breaker statistics.

        Returns:
            Dictionary with current stats.
        """
        return {
            "name": self._name,
            "state": self._state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "opened_at": self._opened_at.isoformat() if self._opened_at else None,
        }
