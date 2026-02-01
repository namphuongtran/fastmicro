"""
Request ID middleware for distributed tracing.

Ensures every request has a unique identifier for tracing across services.
"""

import uuid
from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

REQUEST_ID_HEADER = "X-Request-ID"
CORRELATION_ID_HEADER = "X-Correlation-ID"


class RequestIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add request ID to all requests.

    If X-Request-ID header is present, uses it; otherwise generates a new UUID.
    Also propagates X-Correlation-ID if present.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Response],
    ) -> Response:
        """
        Process the request and add request ID.

        Args:
            request: Incoming HTTP request.
            call_next: Next middleware/handler in the chain.

        Returns:
            Response: HTTP response with request ID header.
        """
        # Get or generate request ID
        request_id = request.headers.get(REQUEST_ID_HEADER)
        if not request_id:
            request_id = str(uuid.uuid4())

        # Get or propagate correlation ID
        correlation_id = request.headers.get(CORRELATION_ID_HEADER, request_id)

        # Store in request state for access in handlers
        request.state.request_id = request_id
        request.state.correlation_id = correlation_id

        # Process request
        response = await call_next(request)

        # Add headers to response
        response.headers[REQUEST_ID_HEADER] = request_id
        response.headers[CORRELATION_ID_HEADER] = correlation_id

        return response
