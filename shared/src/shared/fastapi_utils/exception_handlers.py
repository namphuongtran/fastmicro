"""FastAPI exception handlers for standardized error responses.

This module provides exception handlers that convert application
exceptions into consistent HTTP error responses.

Example:
    >>> from fastapi import FastAPI
    >>> from shared.fastapi_utils.exception_handlers import register_exception_handlers
    >>> app = FastAPI()
    >>> register_exception_handlers(app)
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from shared.exceptions import (
    BadRequestException,
    BaseServiceException,
    ConflictException,
    DatabaseException,
    ForbiddenException,
    NotFoundException,
    ServiceUnavailableException,
    UnauthorizedException,
    ValidationException,
)

logger = logging.getLogger(__name__)


def _create_error_response(
    status_code: int,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> JSONResponse:
    """Create standardized error response.

    Args:
        status_code: HTTP status code.
        code: Error code string.
        message: Human-readable error message.
        details: Additional error details.

    Returns:
        JSONResponse with error body.
    """
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": details or {},
            }
        },
    )


async def http_exception_handler(
    request: Request,
    exc: BaseServiceException,
) -> JSONResponse:
    """Handle HTTP exceptions from shared.exceptions.

    Args:
        request: The incoming request.
        exc: The exception that was raised.

    Returns:
        JSONResponse with error details.
    """
    # Map exception types to status codes and error codes
    status_code = getattr(exc, "status_code", 500)
    error_code = getattr(exc, "error_code", "INTERNAL_ERROR")

    # Extract details if available
    details = {}
    if hasattr(exc, "details") and exc.details:
        details = exc.details
    if hasattr(exc, "field"):
        details["field"] = exc.field
    if hasattr(exc, "resource_type"):
        details["resource_type"] = exc.resource_type
    if hasattr(exc, "resource_id"):
        details["resource_id"] = exc.resource_id

    logger.warning(
        "HTTP exception: %s",
        str(exc),
        extra={
            "status_code": status_code,
            "error_code": error_code,
            "path": request.url.path,
        },
    )

    return _create_error_response(
        status_code=status_code,
        code=error_code,
        message=str(exc),
        details=details,
    )


async def validation_exception_handler(
    request: Request,
    exc: ValidationException,
) -> JSONResponse:
    """Handle validation exceptions.

    Args:
        request: The incoming request.
        exc: The validation exception.

    Returns:
        JSONResponse with validation error details.
    """
    details = {
        "field": getattr(exc, "field", None),
        "value": getattr(exc, "value", None),
    }

    return _create_error_response(
        status_code=422,
        code="VALIDATION_ERROR",
        message=str(exc),
        details={k: v for k, v in details.items() if v is not None},
    )


async def generic_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Handle unhandled exceptions.

    Args:
        request: The incoming request.
        exc: The exception that was raised.

    Returns:
        JSONResponse with generic error.
    """
    logger.exception(
        "Unhandled exception: %s",
        str(exc),
        extra={"path": request.url.path},
    )

    return _create_error_response(
        status_code=500,
        code="INTERNAL_SERVER_ERROR",
        message="An internal error occurred",
        details={},
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers with the FastAPI app.

    This function registers handlers for:
    - NotFoundException (404)
    - ValidationException (422)
    - UnauthorizedException (401)
    - ForbiddenException (403)
    - ConflictException (409)
    - DatabaseException (503)
    - ServiceUnavailableException (503)
    - Generic Exception (500)

    Args:
        app: The FastAPI application.

    Example:
        >>> app = FastAPI()
        >>> register_exception_handlers(app)
    """
    # Register specific exception handlers
    app.add_exception_handler(NotFoundException, http_exception_handler)
    app.add_exception_handler(ValidationException, validation_exception_handler)
    app.add_exception_handler(UnauthorizedException, http_exception_handler)
    app.add_exception_handler(ForbiddenException, http_exception_handler)
    app.add_exception_handler(ConflictException, http_exception_handler)
    app.add_exception_handler(BadRequestException, http_exception_handler)
    app.add_exception_handler(DatabaseException, http_exception_handler)
    app.add_exception_handler(ServiceUnavailableException, http_exception_handler)

    # Generic handler for unhandled exceptions
    app.add_exception_handler(Exception, generic_exception_handler)


__all__ = [
    "generic_exception_handler",
    "http_exception_handler",
    "register_exception_handlers",
    "validation_exception_handler",
]
