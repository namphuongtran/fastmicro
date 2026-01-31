"""FastAPI integration utilities for microservices.

This module provides FastAPI-specific utilities including:

- **Middleware**: Request context and correlation ID tracking
- **Exception Handlers**: Standardized error responses
- **Lifespan**: Application lifecycle management

Example:
    >>> from fastapi import FastAPI
    >>> from shared.fastapi import (
    ...     RequestContextMiddleware,
    ...     register_exception_handlers,
    ...     LifespanManager,
    ...     create_lifespan,
    ... )
    
    # Create lifespan manager
    >>> manager = LifespanManager()
    >>> @manager.on_startup
    ... async def init_services():
    ...     await database.connect()
    
    # Create app
    >>> app = FastAPI(lifespan=create_lifespan(manager))
    
    # Add middleware
    >>> app.add_middleware(RequestContextMiddleware)
    
    # Register exception handlers
    >>> register_exception_handlers(app)
"""

from shared.fastapi_utils.exception_handlers import (
    generic_exception_handler,
    http_exception_handler,
    register_exception_handlers,
    validation_exception_handler,
)
from shared.fastapi_utils.lifespan import (
    LifespanManager,
    create_lifespan,
    register_shutdown_handler,
    register_startup_handler,
)
from shared.fastapi_utils.middleware import (
    CorrelationIdMiddleware,
    RequestContext,
    RequestContextMiddleware,
    get_correlation_id,
    get_request_context,
)

__all__ = [
    # Middleware
    "RequestContext",
    "RequestContextMiddleware",
    "CorrelationIdMiddleware",
    "get_request_context",
    "get_correlation_id",
    # Exception handlers
    "register_exception_handlers",
    "http_exception_handler",
    "validation_exception_handler",
    "generic_exception_handler",
    # Lifespan
    "LifespanManager",
    "create_lifespan",
    "register_startup_handler",
    "register_shutdown_handler",
]
