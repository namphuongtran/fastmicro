"""FastAPI middleware components for microservices.

This module provides middleware for request context management,
including user identity and metadata. For correlation ID and logging,
use the RequestLoggingMiddleware from shared.observability.

Architecture:
    - Correlation ID management: shared.observability.structlog_config
    - Request logging: shared.observability.middleware.RequestLoggingMiddleware
    - User context (user_id, metadata): This module's RequestContextMiddleware

Example:
    >>> from fastapi import FastAPI
    >>> from shared.fastapi_utils.middleware import RequestContextMiddleware
    >>> from shared.observability import RequestLoggingMiddleware
    >>> 
    >>> app = FastAPI()
    >>> # Add RequestLoggingMiddleware first for correlation ID and logging
    >>> app.add_middleware(
    ...     RequestLoggingMiddleware,
    ...     service_name="my-service",
    ... )
    >>> # Then add RequestContextMiddleware for user context
    >>> app.add_middleware(RequestContextMiddleware)
"""

from __future__ import annotations

import uuid
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

# Import correlation ID functions from the single source of truth
from shared.observability.structlog_config import (
    get_correlation_id as _get_observability_correlation_id,
    set_correlation_id as _set_correlation_id,
    generate_correlation_id as _generate_correlation_id,
)


# Context variable for request-scoped data (user context, NOT correlation ID)
_request_context: ContextVar[RequestContext | None] = ContextVar(
    "request_context", default=None
)


@dataclass
class RequestContext:
    """Context data for the current request.
    
    Attributes:
        request_id: Unique identifier for this request.
        correlation_id: ID for tracking requests across services.
        user_id: Authenticated user ID (if available).
        metadata: Additional context metadata.
    """
    request_id: str
    correlation_id: str
    user_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


def get_request_context() -> RequestContext | None:
    """Get the current request context.
    
    Returns:
        The current RequestContext or None if not in a request.
        
    Example:
        >>> ctx = get_request_context()
        >>> if ctx:
        ...     print(f"Request ID: {ctx.request_id}")
    """
    return _request_context.get()


def get_correlation_id() -> str | None:
    """Get the current correlation ID.
    
    This function delegates to shared.observability.structlog_config which
    is the single source of truth for correlation ID management.
    
    Returns:
        The current correlation ID or None if not in a request.
        
    Example:
        >>> corr_id = get_correlation_id()
        >>> logger.info("Processing request", correlation_id=corr_id)
    """
    return _get_observability_correlation_id()


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Middleware that creates and manages request context.
    
    This middleware:
    - Generates a unique request ID for each request
    - Extracts or generates a correlation ID
    - Makes context available via get_request_context()
    - Adds correlation ID to response headers
    
    Example:
        >>> app = FastAPI()
        >>> app.add_middleware(RequestContextMiddleware)
    """

    def __init__(
        self,
        app: ASGIApp,
        correlation_header: str = "X-Correlation-ID",
        request_id_header: str = "X-Request-ID",
    ) -> None:
        """Initialize middleware.
        
        Args:
            app: The ASGI application.
            correlation_header: Header name for correlation ID.
            request_id_header: Header name for request ID.
        """
        super().__init__(app)
        self.correlation_header = correlation_header
        self.request_id_header = request_id_header

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Process the request and manage context.
        
        Args:
            request: The incoming request.
            call_next: The next handler in the chain.
            
        Returns:
            The response with added headers.
        """
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        
        # Get correlation ID from observability context (set by RequestLoggingMiddleware)
        # or extract from header / generate if not available
        correlation_id = _get_observability_correlation_id()
        if correlation_id is None:
            correlation_id = request.headers.get(
                self.correlation_header,
                _generate_correlation_id(),
            )
            # Set in observability context for structlog
            _set_correlation_id(correlation_id)
        
        # Create request context with user-level data
        context = RequestContext(
            request_id=request_id,
            correlation_id=correlation_id,
        )
        
        # Set request context (for user_id, metadata access)
        token_ctx = _request_context.set(context)
        
        try:
            # Process request
            response = await call_next(request)
            
            # Add headers to response
            response.headers[self.correlation_header] = correlation_id
            response.headers[self.request_id_header] = request_id
            
            return response
        finally:
            # Reset request context
            _request_context.reset(token_ctx)


__all__ = [
    "RequestContext",
    "RequestContextMiddleware",
    "get_request_context",
    "get_correlation_id",
]
