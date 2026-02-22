"""Shared extensions package.

This package provides reusable decorators, middleware patterns,
and dependency injection utilities for microservices.
"""

from __future__ import annotations

from shared.extensions.container_protocol import ContainerProtocol
from shared.extensions.decorators import (
    cache,
    deprecated,
    log_calls,
    rate_limit,
    retry,
    singleton,
    timeout,
    validate_args,
)
from shared.extensions.dependency_injection import (
    Container,
    Depends,
    Scope,
    get_container,
    inject,
    register,
    resolve,
)
from shared.extensions.dishka_adapter import (
    DishkaContainerAdapter,
    DishkaFastAPIMiddleware,
    create_dishka_fastapi_middleware,
    dishka_dependency,
    is_dishka_available,
)
from shared.extensions.transactional import transactional

__all__ = [
    # Decorators
    "retry",
    "cache",
    "rate_limit",
    "timeout",
    "deprecated",
    "log_calls",
    "validate_args",
    "singleton",
    "transactional",
    # Dependency Injection
    "Container",
    "ContainerProtocol",
    "Scope",
    "Depends",
    "inject",
    "get_container",
    "register",
    "resolve",
    # Dishka DI Adapter
    "is_dishka_available",
    "DishkaContainerAdapter",
    "DishkaFastAPIMiddleware",
    "create_dishka_fastapi_middleware",
    "dishka_dependency",
]
