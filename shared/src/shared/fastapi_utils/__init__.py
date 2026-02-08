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
from shared.fastapi_utils.dependencies import (
    ServiceContextDep,
    get_service_context,
)
from shared.fastapi_utils.health_router import (
    DetailedHealthResponse,
    HealthResponse,
    LivenessResponse,
    ReadinessResponse,
    create_cache_health_check,
    create_database_health_check,
    create_external_service_health_check,
    create_health_router,
)
from shared.fastapi_utils.lifespan import (
    LifespanManager,
    create_lifespan,
    register_shutdown_handler,
    register_startup_handler,
)
from shared.fastapi_utils.middleware import (
    RequestContext,
    RequestContextMiddleware,
    get_correlation_id,
    get_request_context,
)

__all__ = [
    # Middleware
    "RequestContext",
    "RequestContextMiddleware",
    "get_request_context",
    "get_correlation_id",
    # Dependencies
    "get_service_context",
    "ServiceContextDep",
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
    # Health router
    "create_health_router",
    "create_database_health_check",
    "create_cache_health_check",
    "create_external_service_health_check",
    "HealthResponse",
    "LivenessResponse",
    "ReadinessResponse",
    "DetailedHealthResponse",
]
