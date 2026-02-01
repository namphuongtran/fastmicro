"""Shared extensions package.

This package provides reusable decorators, middleware patterns,
and dependency injection utilities for microservices.
"""

from __future__ import annotations

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
    # Dependency Injection
    "Container",
    "Scope",
    "Depends",
    "inject",
    "get_container",
    "register",
    "resolve",
]
