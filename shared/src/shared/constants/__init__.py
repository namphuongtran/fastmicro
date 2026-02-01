"""
Shared constants for enterprise Python microservices.

This module provides common constants, enums, and validation patterns
used across all services.

Usage:
    >>> from shared.constants import HTTPStatus, Environment, Patterns
    >>> if HTTPStatus.is_success(response.status_code):
    ...     print("Success!")
    >>> if Environment.current().is_production:
    ...     print("Running in production")
    >>> if Patterns.is_valid_email(email):
    ...     print("Valid email")
"""

from shared.constants.environments import Environment
from shared.constants.http_status import HTTPStatus
from shared.constants.patterns import Patterns

__all__ = [
    "Environment",
    "HTTPStatus",
    "Patterns",
]
