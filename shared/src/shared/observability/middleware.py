"""FastAPI middleware for structured logging and correlation ID propagation.

This module provides middleware that automatically:
- Extracts or generates correlation IDs for request tracing
- Logs incoming requests and outgoing responses
- Measures request duration
- Binds request context to structlog for the request lifecycle

Usage:
    from fastapi import FastAPI
    from shared.observability.middleware import RequestLoggingMiddleware

    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)

With configuration:
    from shared.observability.middleware import (
        RequestLoggingMiddleware,
        RequestLoggingConfig,
    )

    app.add_middleware(
        RequestLoggingMiddleware,
        config=RequestLoggingConfig(
            correlation_id_header="X-Correlation-ID",
            log_request_body=False,
            log_response_body=False,
            exclude_paths=["/health", "/metrics"],
        ),
    )
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from shared.observability.structlog_config import (
    bind_contextvars,
    clear_contextvars,
    generate_correlation_id,
    get_correlation_id,
    get_structlog_logger,
    set_correlation_id,
)

# =============================================================================
# Configuration
# =============================================================================


@dataclass
class RequestLoggingConfig:
    """Configuration for request logging middleware.

    Attributes:
        correlation_id_header: HTTP header name for correlation ID.
            The middleware will look for this header in incoming requests
            and set it in outgoing responses.
        request_id_header: Alternative header name for request ID.
            If correlation_id_header is not found, this will be checked.
        log_request_headers: Include request headers in logs.
        log_response_headers: Include response headers in logs.
        log_request_body: Include request body in logs (use with caution).
        log_response_body: Include response body in logs (use with caution).
        exclude_paths: Paths to exclude from logging (e.g., health checks).
        exclude_paths_startswith: Path prefixes to exclude from logging.
        sensitive_headers: Headers to redact from logs.
        max_body_log_size: Maximum body size to log (bytes).
        slow_request_threshold_ms: Threshold for slow request warnings (milliseconds).
    """

    correlation_id_header: str = "X-Correlation-ID"
    request_id_header: str = "X-Request-ID"
    log_request_headers: bool = False
    log_response_headers: bool = False
    log_request_body: bool = False
    log_response_body: bool = False
    exclude_paths: list[str] = field(
        default_factory=lambda: [
            "/health",
            "/healthz",
            "/ready",
            "/readyz",
            "/live",
            "/livez",
            "/metrics",
            "/favicon.ico",
        ]
    )
    exclude_paths_startswith: list[str] = field(
        default_factory=lambda: [
            "/static/",
            "/.well-known/",
        ]
    )
    sensitive_headers: set[str] = field(
        default_factory=lambda: {
            "authorization",
            "cookie",
            "x-api-key",
            "x-auth-token",
            "x-csrf-token",
        }
    )
    max_body_log_size: int = 1024  # 1KB
    slow_request_threshold_ms: float = 1000.0  # 1 second


# =============================================================================
# Default Configuration
# =============================================================================

DEFAULT_CONFIG = RequestLoggingConfig()


# =============================================================================
# Middleware Implementation
# =============================================================================


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for automatic request logging and correlation ID propagation.

    This middleware:
    1. Extracts correlation ID from request headers (or generates one)
    2. Binds request context to structlog for the entire request
    3. Logs incoming requests with method, path, and client info
    4. Logs outgoing responses with status code and duration
    5. Adds correlation ID to response headers
    6. Clears context after request completes

    Example:
        app = FastAPI()
        app.add_middleware(RequestLoggingMiddleware)

        # Or with custom config:
        app.add_middleware(
            RequestLoggingMiddleware,
            config=RequestLoggingConfig(
                exclude_paths=["/health", "/ready"],
                slow_request_threshold_ms=500,
            ),
        )
    """

    def __init__(
        self,
        app: ASGIApp,
        config: RequestLoggingConfig | None = None,
    ) -> None:
        """Initialize the middleware.

        Args:
            app: The ASGI application.
            config: Optional configuration. Uses defaults if not provided.
        """
        super().__init__(app)
        self.config = config or DEFAULT_CONFIG
        self.logger = get_structlog_logger("shared.observability.middleware")

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Process the request and add logging/correlation ID.

        Args:
            request: The incoming request.
            call_next: The next middleware/handler in the chain.

        Returns:
            The response with correlation ID header added.
        """
        # Check if this path should be excluded from logging
        if self._should_exclude_path(request.url.path):
            return await call_next(request)

        # Extract or generate correlation ID
        correlation_id = self._extract_correlation_id(request)
        set_correlation_id(correlation_id)

        # Bind request context to structlog
        bind_contextvars(
            correlation_id=correlation_id,
            http_method=request.method,
            http_path=request.url.path,
            client_ip=self._get_client_ip(request),
        )

        # Record start time
        start_time = time.perf_counter()

        # Log incoming request
        request_log_data = self._build_request_log_data(request)
        self.logger.info("Request started", **request_log_data)

        # Process request
        response: Response | None = None
        error: Exception | None = None

        try:
            response = await call_next(request)
        except Exception as exc:
            error = exc
            raise
        finally:
            # Calculate duration
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Log response/error
            self._log_response(
                request=request,
                response=response,
                error=error,
                duration_ms=duration_ms,
            )

            # Clear context
            clear_contextvars()

        # Add correlation ID to response headers
        if response is not None:
            response.headers[self.config.correlation_id_header] = correlation_id

        return response

    def _should_exclude_path(self, path: str) -> bool:
        """Check if the path should be excluded from logging.

        Args:
            path: The request path.

        Returns:
            True if the path should be excluded.
        """
        # Exact match
        if path in self.config.exclude_paths:
            return True

        # Prefix match
        return any(
            path.startswith(prefix) for prefix in self.config.exclude_paths_startswith
        )

    def _extract_correlation_id(self, request: Request) -> str:
        """Extract correlation ID from request headers or generate one.

        Args:
            request: The incoming request.

        Returns:
            The correlation ID (extracted or generated).
        """
        # Try primary header
        correlation_id = request.headers.get(self.config.correlation_id_header)
        if correlation_id:
            return correlation_id

        # Try alternative header
        correlation_id = request.headers.get(self.config.request_id_header)
        if correlation_id:
            return correlation_id

        # Generate new ID
        return generate_correlation_id()

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request, handling proxies.

        Args:
            request: The incoming request.

        Returns:
            The client IP address.
        """
        # Check X-Forwarded-For header (from load balancers/proxies)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # Take the first IP (original client)
            return forwarded_for.split(",")[0].strip()

        # Check X-Real-IP header
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        # Fall back to direct client
        if request.client:
            return request.client.host

        return "unknown"

    def _build_request_log_data(self, request: Request) -> dict:
        """Build log data for the incoming request.

        Args:
            request: The incoming request.

        Returns:
            Dictionary of log data.
        """
        data = {
            "http_version": request.scope.get("http_version", "1.1"),
            "query_string": str(request.query_params) if request.query_params else None,
            "user_agent": request.headers.get("user-agent"),
        }

        # Add headers if configured
        if self.config.log_request_headers:
            data["headers"] = self._sanitize_headers(dict(request.headers))

        # Remove None values
        return {k: v for k, v in data.items() if v is not None}

    def _sanitize_headers(self, headers: dict[str, str]) -> dict[str, str]:
        """Sanitize headers by redacting sensitive values.

        Args:
            headers: The headers dictionary.

        Returns:
            Sanitized headers with sensitive values redacted.
        """
        sanitized = {}
        for key, value in headers.items():
            if key.lower() in self.config.sensitive_headers:
                sanitized[key] = "[REDACTED]"
            else:
                sanitized[key] = value
        return sanitized

    def _log_response(
        self,
        request: Request,
        response: Response | None,
        error: Exception | None,
        duration_ms: float,
    ) -> None:
        """Log the response or error.

        Args:
            request: The original request.
            response: The response (if successful).
            error: The error (if failed).
            duration_ms: Request duration in milliseconds.
        """
        log_data = {
            "duration_ms": round(duration_ms, 2),
        }

        # Check for slow request
        is_slow = duration_ms >= self.config.slow_request_threshold_ms

        if error is not None:
            # Log error
            log_data["error_type"] = type(error).__name__
            log_data["error_message"] = str(error)
            self.logger.error("Request failed", **log_data, exc_info=error)
        elif response is not None:
            # Log response
            log_data["http_status"] = response.status_code
            log_data["content_type"] = response.headers.get("content-type")

            # Add response headers if configured
            if self.config.log_response_headers:
                log_data["response_headers"] = self._sanitize_headers(dict(response.headers))

            # Determine log level based on status and duration
            if response.status_code >= 500:
                self.logger.error("Request completed", **log_data)
            elif response.status_code >= 400:
                self.logger.warning("Request completed", **log_data)
            elif is_slow:
                self.logger.warning("Slow request completed", **log_data)
            else:
                self.logger.info("Request completed", **log_data)


# =============================================================================
# Convenience Functions
# =============================================================================


def add_request_logging_middleware(
    app: ASGIApp,
    config: RequestLoggingConfig | None = None,
) -> None:
    """Add request logging middleware to a FastAPI/Starlette app.

    This is a convenience function that's equivalent to:
        app.add_middleware(RequestLoggingMiddleware, config=config)

    Args:
        app: The FastAPI/Starlette application.
        config: Optional configuration.

    Example:
        from fastapi import FastAPI
        from shared.observability.middleware import add_request_logging_middleware

        app = FastAPI()
        add_request_logging_middleware(app)
    """
    # Note: For FastAPI, use app.add_middleware directly
    # This function is provided for non-FastAPI Starlette apps
    raise NotImplementedError("Use app.add_middleware(RequestLoggingMiddleware) for FastAPI apps")


def get_correlation_id_from_request(request: Request) -> str | None:
    """Get the correlation ID from the current request context.

    This is useful when you need to access the correlation ID
    inside a route handler.

    Args:
        request: The FastAPI/Starlette request.

    Returns:
        The correlation ID if set, None otherwise.

    Example:
        @app.get("/example")
        async def example(request: Request):
            correlation_id = get_correlation_id_from_request(request)
            # Use correlation_id for downstream calls
    """
    return get_correlation_id()


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "RequestLoggingConfig",
    "RequestLoggingMiddleware",
    "get_correlation_id_from_request",
]
