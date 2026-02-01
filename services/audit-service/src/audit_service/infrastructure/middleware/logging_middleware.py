"""
Logging middleware for request/response logging.

Provides structured logging for all HTTP requests with timing information.
"""

import time
from collections.abc import Callable
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Import shared library logger
try:
    from shared.observability import get_logger
except ImportError:
    import structlog

    get_logger = structlog.get_logger

logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for structured request/response logging.

    Logs request start, completion, and timing for observability.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Response],
    ) -> Response:
        """
        Process the request with logging.

        Args:
            request: Incoming HTTP request.
            call_next: Next middleware/handler in the chain.

        Returns:
            Response: HTTP response.
        """
        # Skip logging for health checks to reduce noise
        if request.url.path in ("/health", "/ready", "/metrics"):
            return await call_next(request)

        # Extract request context
        request_id = getattr(request.state, "request_id", "unknown")
        correlation_id = getattr(request.state, "correlation_id", "unknown")

        # Build log context
        log_context: dict[str, Any] = {
            "request_id": request_id,
            "correlation_id": correlation_id,
            "method": request.method,
            "path": request.url.path,
            "query": str(request.query_params) if request.query_params else None,
            "client_ip": self._get_client_ip(request),
            "user_agent": request.headers.get("user-agent"),
        }

        # Log request start
        logger.info("Request started", **log_context)

        # Time the request
        start_time = time.perf_counter()

        try:
            response = await call_next(request)

            # Calculate duration
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Log request completion
            logger.info(
                "Request completed",
                **log_context,
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2),
            )

            return response

        except Exception as exc:
            # Calculate duration
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Log request error
            logger.error(
                "Request failed",
                **log_context,
                error=str(exc),
                error_type=type(exc).__name__,
                duration_ms=round(duration_ms, 2),
            )

            raise

    def _get_client_ip(self, request: Request) -> str:
        """
        Extract client IP from request, handling proxies.

        Args:
            request: HTTP request.

        Returns:
            str: Client IP address.
        """
        # Check X-Forwarded-For header (for proxied requests)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # Take the first IP in the chain
            return forwarded_for.split(",")[0].strip()

        # Check X-Real-IP header
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        # Fall back to direct client IP
        if request.client:
            return request.client.host

        return "unknown"
