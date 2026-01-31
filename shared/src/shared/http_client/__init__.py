"""HTTP client utilities for microservice communication.

This module provides resilient HTTP client utilities:
- ServiceClient: Async HTTP client with retry support
- CircuitBreaker: Circuit breaker for resilience
- ServiceResponse: Standardized response wrapper

Example:
    >>> from shared.http_client import (
    ...     ServiceClient,
    ...     ServiceClientConfig,
    ...     CircuitBreaker,
    ...     CircuitBreakerConfig,
    ... )
    ...
    >>> config = ServiceClientConfig(base_url="https://api.example.com")
    >>> async with ServiceClient(config) as client:
    ...     response = await client.get("/users/1")
    ...     print(response.data)
"""

from shared.http_client.client import (
    ServiceClient,
    ServiceClientConfig,
    ServiceResponse,
    HTTPClientError,
    ServiceUnavailableError,
)
from shared.http_client.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
    CircuitOpenError,
)

__all__ = [
    # Client
    "ServiceClient",
    "ServiceClientConfig",
    "ServiceResponse",
    # Errors
    "HTTPClientError",
    "ServiceUnavailableError",
    "CircuitOpenError",
    # Circuit Breaker
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitState",
]
