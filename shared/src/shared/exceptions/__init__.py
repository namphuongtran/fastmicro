"""
Shared exception classes for enterprise Python microservices.

This module provides a comprehensive exception hierarchy for handling
errors consistently across all services. The exceptions are designed for:

- Distributed tracing with correlation ID support
- HTTP API responses with proper status codes
- Database error handling with driver-agnostic abstractions
- Pydantic-compatible validation errors
- Structured logging and monitoring integration

Usage:
    >>> from shared.exceptions import NotFoundException, ValidationException
    >>> raise NotFoundException.for_resource("User", "user-123")

Exception Hierarchy:
    BaseServiceException
    ├── HTTPException
    │   ├── BadRequestException (400)
    │   ├── UnauthorizedException (401)
    │   ├── ForbiddenException (403)
    │   ├── NotFoundException (404)
    │   ├── MethodNotAllowedException (405)
    │   ├── ConflictException (409)
    │   ├── UnprocessableEntityException (422)
    │   │   └── ValidationException
    │   ├── RateLimitException (429)
    │   ├── InternalServerException (500)
    │   ├── BadGatewayException (502)
    │   ├── ServiceUnavailableException (503)
    │   └── GatewayTimeoutException (504)
    └── DatabaseException
        ├── ConnectionException
        ├── QueryException
        ├── IntegrityException
        ├── TransactionException
        └── TimeoutException
"""

from shared.exceptions.base import BaseServiceException, ErrorSeverity
from shared.exceptions.database import (
    ConnectionException,
    DatabaseException,
    IntegrityException,
    QueryException,
    TimeoutException,
    TransactionException,
)
from shared.exceptions.http import (
    BadGatewayException,
    BadRequestException,
    ConflictException,
    ForbiddenException,
    GatewayTimeoutException,
    HTTPException,
    InternalServerException,
    MethodNotAllowedException,
    NotFoundException,
    RateLimitException,
    ServiceUnavailableException,
    UnauthorizedException,
    UnprocessableEntityException,
)
from shared.exceptions.validation import FieldError, ValidationException

__all__ = [
    # Base
    "BaseServiceException",
    "ErrorSeverity",
    # HTTP (4xx)
    "HTTPException",
    "BadRequestException",
    "UnauthorizedException",
    "ForbiddenException",
    "NotFoundException",
    "MethodNotAllowedException",
    "ConflictException",
    "UnprocessableEntityException",
    "RateLimitException",
    # HTTP (5xx)
    "InternalServerException",
    "BadGatewayException",
    "ServiceUnavailableException",
    "GatewayTimeoutException",
    # Validation
    "FieldError",
    "ValidationException",
    # Database
    "DatabaseException",
    "ConnectionException",
    "QueryException",
    "IntegrityException",
    "TransactionException",
    "TimeoutException",
]
