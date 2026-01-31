"""FastAPI middleware components for microservices.

This module provides middleware for request context management,
correlation ID tracking, and other cross-cutting concerns.

Example:
    >>> from fastapi import FastAPI
    >>> from shared.fastapi_utils.middleware import RequestContextMiddleware
    >>> app = FastAPI()
    >>> app.add_middleware(RequestContextMiddleware)
"""

from __future__ import annotations

import uuid
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp


# Context variables for request-scoped data
_request_context: ContextVar[RequestContext | None] = ContextVar(
    "request_context", default=None
)
_correlation_id: ContextVar[str | None] = ContextVar(
    "correlation_id", default=None
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
    
    Returns:
        The current correlation ID or None if not in a request.
        
    Example:
        >>> corr_id = get_correlation_id()
        >>> logger.info("Processing request", correlation_id=corr_id)
    """
    return _correlation_id.get()


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
        # Generate or extract IDs
        request_id = str(uuid.uuid4())
        correlation_id = request.headers.get(
            self.correlation_header,
            str(uuid.uuid4()),
        )
        
        # Create request context
        context = RequestContext(
            request_id=request_id,
            correlation_id=correlation_id,
        )
        
        # Set context variables
        token_ctx = _request_context.set(context)
        token_corr = _correlation_id.set(correlation_id)
        
        try:
            # Process request
            response = await call_next(request)
            
            # Add headers to response
            response.headers[self.correlation_header] = correlation_id
            response.headers[self.request_id_header] = request_id
            
            return response
        finally:
            # Reset context variables
            _request_context.reset(token_ctx)
            _correlation_id.reset(token_corr)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Simple middleware for correlation ID tracking.
    
    A lighter-weight alternative to RequestContextMiddleware
    when you only need correlation ID tracking.
    
    Example:
        >>> app = FastAPI()
        >>> app.add_middleware(CorrelationIdMiddleware)
    """

    def __init__(
        self,
        app: ASGIApp,
        header_name: str = "X-Correlation-ID",
    ) -> None:
        """Initialize middleware.
        
        Args:
            app: The ASGI application.
            header_name: Header name for correlation ID.
        """
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Process the request and track correlation ID.
        
        Args:
            request: The incoming request.
            call_next: The next handler in the chain.
            
        Returns:
            The response with correlation ID header.
        """
        # Extract or generate correlation ID
        correlation_id = request.headers.get(
            self.header_name,
            str(uuid.uuid4()),
        )
        
        # Set context variable
        token = _correlation_id.set(correlation_id)
        
        try:
            response = await call_next(request)
            response.headers[self.header_name] = correlation_id
            return response
        finally:
            _correlation_id.reset(token)


__all__ = [
    "RequestContext",
    "RequestContextMiddleware",
    "CorrelationIdMiddleware",
    "get_request_context",
    "get_correlation_id",
]
