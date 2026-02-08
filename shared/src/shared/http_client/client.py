"""HTTP service client with retry and resilience features.

This module provides an async HTTP client for microservice communication:
- ServiceClient: Main HTTP client with retry support
- ServiceClientConfig: Configuration for the client
- ServiceResponse: Standardized response wrapper
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Self
from uuid import uuid4

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)


class HTTPClientError(Exception):
    """Base exception for HTTP client errors.

    Attributes:
        message: Error description.
        status_code: HTTP status code (if applicable).
        response_data: Response data (if applicable).
    """

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_data: dict[str, Any] | None = None,
    ) -> None:
        """Initialize HTTP client error.

        Args:
            message: Error description.
            status_code: HTTP status code.
            response_data: Response data from server.
        """
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class ServiceUnavailableError(HTTPClientError):
    """Error when service is unavailable after retries."""

    def __init__(self, message: str = "Service unavailable") -> None:
        """Initialize service unavailable error.

        Args:
            message: Error description.
        """
        super().__init__(message, status_code=503)


@dataclass
class ServiceClientConfig:
    """Configuration for service client.

    Attributes:
        base_url: Base URL for the service.
        timeout: Request timeout in seconds.
        max_retries: Maximum retry attempts.
        retry_backoff: Initial backoff delay in seconds.
        retry_backoff_max: Maximum backoff delay in seconds.
        headers: Default headers to include in all requests.
        auto_correlation_id: Auto-generate correlation ID if not provided.
        correlation_id_header: Header name for correlation ID.
    """

    base_url: str
    timeout: float = 30.0
    max_retries: int = 3
    retry_backoff: float = 1.0
    retry_backoff_max: float = 60.0
    headers: dict[str, str] = field(default_factory=dict)
    auto_correlation_id: bool = False
    correlation_id_header: str = "X-Correlation-ID"
    # Circuit Breaker settings
    circuit_breaker_enabled: bool = True
    cb_failure_threshold: int = 5
    cb_recovery_timeout: float = 30.0


@dataclass
class ServiceResponse:
    """Standardized service response wrapper.

    Attributes:
        status_code: HTTP status code.
        data: Response data (parsed JSON or raw).
        headers: Response headers.
    """

    status_code: int
    data: Any
    headers: dict[str, str]

    @property
    def is_success(self) -> bool:
        """Check if response indicates success (2xx)."""
        return 200 <= self.status_code < 300

    @property
    def is_client_error(self) -> bool:
        """Check if response indicates client error (4xx)."""
        return 400 <= self.status_code < 500

    @property
    def is_server_error(self) -> bool:
        """Check if response indicates server error (5xx)."""
        return 500 <= self.status_code < 600


class ServiceClient:
    """Async HTTP client for microservice communication.

    Features:
    - Automatic retries with exponential backoff
    - Correlation ID propagation
    - Configurable timeouts
    - Response normalization

    Example:
        >>> config = ServiceClientConfig(base_url="https://api.example.com")
        >>> async with ServiceClient(config) as client:
        ...     response = await client.get("/users/1")
        ...     if response.is_success:
        ...         user = response.data
    """

    def __init__(self, config: ServiceClientConfig) -> None:
        """Initialize service client.

        Args:
            config: Client configuration.
        """
        self._config = config
        self._client = httpx.AsyncClient(
            base_url=config.base_url,
            timeout=config.timeout,
            headers=config.headers,
        )
        # Initialize circuit breaker if enabled
        from shared.http_client.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
        
        self._circuit_breaker: CircuitBreaker | None = None
        if config.circuit_breaker_enabled:
            # Create a simple name from the base url if explicit name not provided
            # ideally config would have a service_name field
            name = config.base_url.replace("https://", "").replace("http://", "").split("/")[0]
            self._circuit_breaker = CircuitBreaker(
                name=name,
                config=CircuitBreakerConfig(
                    failure_threshold=config.cb_failure_threshold,
                    recovery_timeout=config.cb_recovery_timeout,
                )
            )

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()

    async def get(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        correlation_id: str | None = None,
    ) -> ServiceResponse:
        """Make GET request.

        Args:
            path: Request path.
            params: Query parameters.
            headers: Additional headers.
            correlation_id: Correlation ID for tracing.

        Returns:
            ServiceResponse with status, data, and headers.
        """
        return await self._request(
            "GET",
            path,
            params=params,
            headers=headers,
            correlation_id=correlation_id,
        )

    async def post(
        self,
        path: str,
        *,
        json: Any | None = None,
        data: Any | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        correlation_id: str | None = None,
    ) -> ServiceResponse:
        """Make POST request.

        Args:
            path: Request path.
            json: JSON body data.
            data: Form data.
            params: Query parameters.
            headers: Additional headers.
            correlation_id: Correlation ID for tracing.

        Returns:
            ServiceResponse with status, data, and headers.
        """
        return await self._request(
            "POST",
            path,
            json=json,
            data=data,
            params=params,
            headers=headers,
            correlation_id=correlation_id,
        )

    async def put(
        self,
        path: str,
        *,
        json: Any | None = None,
        data: Any | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        correlation_id: str | None = None,
    ) -> ServiceResponse:
        """Make PUT request.

        Args:
            path: Request path.
            json: JSON body data.
            data: Form data.
            params: Query parameters.
            headers: Additional headers.
            correlation_id: Correlation ID for tracing.

        Returns:
            ServiceResponse with status, data, and headers.
        """
        return await self._request(
            "PUT",
            path,
            json=json,
            data=data,
            params=params,
            headers=headers,
            correlation_id=correlation_id,
        )

    async def patch(
        self,
        path: str,
        *,
        json: Any | None = None,
        data: Any | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        correlation_id: str | None = None,
    ) -> ServiceResponse:
        """Make PATCH request.

        Args:
            path: Request path.
            json: JSON body data.
            data: Form data.
            params: Query parameters.
            headers: Additional headers.
            correlation_id: Correlation ID for tracing.

        Returns:
            ServiceResponse with status, data, and headers.
        """
        return await self._request(
            "PATCH",
            path,
            json=json,
            data=data,
            params=params,
            headers=headers,
            correlation_id=correlation_id,
        )

    async def delete(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        correlation_id: str | None = None,
    ) -> ServiceResponse:
        """Make DELETE request.

        Args:
            path: Request path.
            params: Query parameters.
            headers: Additional headers.
            correlation_id: Correlation ID for tracing.

        Returns:
            ServiceResponse with status, data, and headers.
        """
        return await self._request(
            "DELETE",
            path,
            params=params,
            headers=headers,
            correlation_id=correlation_id,
        )

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: Any | None = None,
        data: Any | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        correlation_id: str | None = None,
    ) -> ServiceResponse:
        """Make HTTP request with retry logic and circuit breaker.

        Args:
            method: HTTP method.
            path: Request path.
            json: JSON body data.
            data: Form data.
            params: Query parameters.
            headers: Additional headers.
            correlation_id: Correlation ID for tracing.

        Returns:
            ServiceResponse with status, data, and headers.

        Raises:
            ServiceUnavailableError: When max retries exceeded or circuit open.
            HTTPClientError: For other client errors.
        """
        # Prepare headers
        request_headers = dict(headers or {})

        # Add correlation ID
        if correlation_id:
            request_headers[self._config.correlation_id_header] = correlation_id
        elif self._config.auto_correlation_id:
            request_headers[self._config.correlation_id_header] = str(uuid4())

        async def make_request() -> ServiceResponse:
            response = await self._client.request(
                method,
                path,
                json=json,
                data=data,
                params=params,
                headers=request_headers,
            )

            # Raise HTTPStatusError for 5xx to trigger retries/circuit breaker
            # We explicitly want to retry on server errors
            if response.status_code >= 500:
                raise httpx.HTTPStatusError(
                    f"Server error: {response.status_code}",
                    request=response.request,
                    response=response,
                )
            
            return self._parse_response(response)

        # 1. Wrap with Circuit Breaker (Fail Fast)
        # If the circuit is OPEN, this will raise CircuitOpenError immediately.
        # We generally do NOT want to retry CircuitOpenError, as we want to save the system.
        try:
            if self._circuit_breaker:
                from shared.http_client.circuit_breaker import CircuitOpenError
                
                async def cb_wrapper():
                    # 2. Wrap with Retries (Try Again)
                    # We retry network errors and 5xx errors INSIDE the circuit breaker.
                    # This means if retries fail, it counts as a failure for the circuit.
                    async for attempt in AsyncRetrying(
                        stop=stop_after_attempt(self._config.max_retries),
                        wait=wait_exponential(
                            multiplier=self._config.retry_backoff,
                            max=self._config.retry_backoff_max,
                        ),
                        retry=retry_if_exception_type(
                            (
                                httpx.TimeoutException,
                                httpx.ConnectError,
                                httpx.ReadTimeout,
                                httpx.WriteTimeout,
                                httpx.HTTPStatusError, # Retries on 5xx
                            )
                        ),
                        reraise=True,
                    ):
                        with attempt:
                            return await make_request()
                
                try:
                    return await self._circuit_breaker.call(cb_wrapper)
                except CircuitOpenError as e:
                    # Map to our standard exception
                    raise ServiceUnavailableError(f"Circuit open for {self._config.base_url}: {e}") from e
                    
            else:
                # No circuit breaker, just standard retries
                async for attempt in AsyncRetrying(
                    stop=stop_after_attempt(self._config.max_retries),
                    wait=wait_exponential(
                        multiplier=self._config.retry_backoff,
                        max=self._config.retry_backoff_max,
                    ),
                    retry=retry_if_exception_type(
                        (
                            httpx.TimeoutException,
                            httpx.ConnectError,
                            httpx.ReadTimeout,
                            httpx.WriteTimeout,
                            httpx.HTTPStatusError,
                        )
                    ),
                    reraise=True,
                ):
                    with attempt:
                        return await make_request()

        except (httpx.TimeoutException, httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout) as e:
            raise ServiceUnavailableError(f"Max retries exceeded for {method} {path}: {e}") from e
        except httpx.HTTPStatusError as e:
            # If we exhausted retries on 5xx, we parse the error response
            return self._parse_response(e.response)
        
        # Should not be reached
        raise ServiceUnavailableError("Unknown error occurred")

    def _parse_response(self, response: httpx.Response) -> ServiceResponse:
        """Parse HTTP response into ServiceResponse.

        Args:
            response: httpx response object.

        Returns:
            Standardized ServiceResponse.
        """
        # Try to parse JSON, fall back to raw content
        try:
            data = response.json() if response.content else {}
        except Exception:
            data = response.text if response.content else ""

        return ServiceResponse(
            status_code=response.status_code,
            data=data,
            headers=dict(response.headers),
        )
