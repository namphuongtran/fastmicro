"""Custom middleware for Identity Admin Service."""

from collections.abc import Callable
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from shared.observability import get_structlog_logger

logger = get_structlog_logger(__name__)


class IPWhitelistMiddleware(BaseHTTPMiddleware):
    """Middleware to restrict access to whitelisted IP addresses.

    This provides an additional layer of security for the admin service
    by rejecting requests from unauthorized IP addresses.
    """

    def __init__(self, app: Any, allowed_ips: list[str]) -> None:
        """Initialize the middleware.

        Args:
            app: The ASGI application.
            allowed_ips: List of allowed IP addresses. Use ["*"] to allow all.
        """
        super().__init__(app)
        self.allowed_ips = set(allowed_ips)
        self.allow_all = "*" in self.allowed_ips

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Response]
    ) -> Response:
        """Process the request and check IP whitelist.

        Args:
            request: The incoming request.
            call_next: The next middleware/handler in the chain.

        Returns:
            Response from the next handler or 403 if IP not allowed.
        """
        if self.allow_all:
            return await call_next(request)

        # Get client IP (consider X-Forwarded-For for proxied requests)
        client_ip = self._get_client_ip(request)

        if client_ip not in self.allowed_ips:
            logger.warning(
                "Unauthorized IP access attempt",
                client_ip=client_ip,
                path=request.url.path,
                method=request.method,
            )
            return JSONResponse(
                status_code=403,
                content={
                    "error": "access_denied",
                    "error_description": "Access denied from this IP address",
                },
            )

        return await call_next(request)

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request.

        Handles X-Forwarded-For header for reverse proxy scenarios.

        Args:
            request: The incoming request.

        Returns:
            The client IP address.
        """
        # Check X-Forwarded-For header (set by reverse proxies)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP in the chain (original client)
            return forwarded_for.split(",")[0].strip()

        # Fall back to direct client IP
        if request.client:
            return request.client.host

        return "unknown"
