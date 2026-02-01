"""
HTTP exception classes mapped to standard HTTP status codes.

This module provides exceptions that map directly to HTTP response codes,
making it easy to translate service errors into appropriate API responses.

Example:
    >>> from shared.exceptions.http import NotFoundException
    >>> raise NotFoundException.for_resource("User", "user-123")
"""

from __future__ import annotations

from typing import Any, ClassVar, Self

from shared.exceptions.base import BaseServiceException, ErrorSeverity

__all__ = [
    "BadGatewayException",
    "BadRequestException",
    "ConflictException",
    "ForbiddenException",
    "GatewayTimeoutException",
    "HTTPException",
    "InternalServerException",
    "MethodNotAllowedException",
    "NotFoundException",
    "RateLimitException",
    "ServiceUnavailableException",
    "UnauthorizedException",
    "UnprocessableEntityException",
]


class HTTPException(BaseServiceException):
    """
    Base HTTP exception with status code support.

    All HTTP exceptions inherit from this class and map to specific
    HTTP status codes for API responses.

    Attributes:
        status_code: HTTP status code (e.g., 400, 404, 500).
        headers: Optional HTTP headers to include in response.

    Example:
        >>> exc = HTTPException(status_code=400, message="Invalid request")
        >>> exc.to_response()
        {'status_code': 400, 'body': {...}, 'headers': {}}
    """

    status_code: ClassVar[int] = 500

    def __init__(
        self,
        status_code: int | None = None,
        message: str = "An error occurred",
        *,
        error_code: str = "HTTP_ERROR",
        details: dict[str, Any] | None = None,
        correlation_id: str | None = None,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        headers: dict[str, str] | None = None,
    ) -> None:
        """
        Initialize HTTP exception.

        Args:
            status_code: HTTP status code (uses class default if not provided).
            message: Human-readable error description.
            error_code: Unique error identifier.
            details: Additional error context.
            correlation_id: Distributed tracing ID.
            severity: Error severity level.
            headers: HTTP headers to include in response.
        """
        super().__init__(
            message=message,
            error_code=error_code,
            details=details,
            correlation_id=correlation_id,
            severity=severity,
        )
        if status_code is not None:
            self.status_code = status_code
        self.headers = headers or {}

    def to_response(self) -> dict[str, Any]:
        """
        Generate API response format.

        Returns:
            Dictionary with status_code, body, and headers suitable
            for returning from an API endpoint.

        Example:
            >>> exc = BadRequestException(message="Invalid input")
            >>> response = exc.to_response()
            >>> response['status_code']
            400
        """
        body: dict[str, Any] = {
            "error": {
                "code": self.error_code,
                "message": self.message,
            }
        }

        if self.details:
            body["error"]["details"] = self.details

        if self.correlation_id:
            body["error"]["correlation_id"] = self.correlation_id

        response: dict[str, Any] = {
            "status_code": self.status_code,
            "body": body,
        }

        if self.headers:
            response["headers"] = self.headers

        return response


# =============================================================================
# 4xx Client Errors
# =============================================================================


class BadRequestException(HTTPException):
    """
    400 Bad Request - The request was malformed or invalid.

    Use for:
    - Malformed JSON/XML
    - Missing required parameters
    - Invalid request format

    Example:
        >>> raise BadRequestException(message="Invalid JSON body")
    """

    status_code: ClassVar[int] = 400

    def __init__(
        self,
        message: str = "Bad request",
        *,
        error_code: str = "BAD_REQUEST",
        details: dict[str, Any] | None = None,
        correlation_id: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code=error_code,
            details=details,
            correlation_id=correlation_id,
            severity=ErrorSeverity.WARNING,
            headers=headers,
        )


class UnauthorizedException(HTTPException):
    """
    401 Unauthorized - Authentication is required or has failed.

    Use for:
    - Missing authentication credentials
    - Invalid or expired tokens
    - Failed authentication attempts

    Example:
        >>> raise UnauthorizedException(message="Token expired")
    """

    status_code: ClassVar[int] = 401

    def __init__(
        self,
        message: str = "Authentication required",
        *,
        error_code: str = "UNAUTHORIZED",
        details: dict[str, Any] | None = None,
        correlation_id: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code=error_code,
            details=details,
            correlation_id=correlation_id,
            severity=ErrorSeverity.WARNING,
            headers=headers,
        )


class ForbiddenException(HTTPException):
    """
    403 Forbidden - The user lacks permission to access the resource.

    Use for:
    - Insufficient permissions
    - Access denied to specific resources
    - Role-based access control violations

    Example:
        >>> raise ForbiddenException(
        ...     message="Insufficient permissions",
        ...     details={"required_role": "admin"}
        ... )
    """

    status_code: ClassVar[int] = 403

    def __init__(
        self,
        message: str = "Access denied",
        *,
        error_code: str = "FORBIDDEN",
        details: dict[str, Any] | None = None,
        correlation_id: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code=error_code,
            details=details,
            correlation_id=correlation_id,
            severity=ErrorSeverity.WARNING,
            headers=headers,
        )


class NotFoundException(HTTPException):
    """
    404 Not Found - The requested resource does not exist.

    Use for:
    - Resource not found by ID
    - Endpoint not found
    - File not found

    Example:
        >>> raise NotFoundException.for_resource("User", "user-123")
    """

    status_code: ClassVar[int] = 404

    def __init__(
        self,
        message: str = "Resource not found",
        *,
        error_code: str = "NOT_FOUND",
        details: dict[str, Any] | None = None,
        correlation_id: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code=error_code,
            details=details,
            correlation_id=correlation_id,
            severity=ErrorSeverity.WARNING,
            headers=headers,
        )

    @classmethod
    def for_resource(
        cls,
        resource_type: str,
        resource_id: str,
        *,
        correlation_id: str | None = None,
    ) -> Self:
        """
        Create a NotFoundException for a specific resource.

        Args:
            resource_type: Type of resource (e.g., "User", "Order").
            resource_id: Identifier of the missing resource.
            correlation_id: Optional trace ID.

        Returns:
            Configured NotFoundException instance.

        Example:
            >>> exc = NotFoundException.for_resource("User", "123")
            >>> exc.message
            "User with id '123' not found"
        """
        return cls(
            message=f"{resource_type} with id '{resource_id}' not found",
            error_code="NOT_FOUND",
            details={
                "resource_type": resource_type,
                "resource_id": resource_id,
            },
            correlation_id=correlation_id,
        )


class MethodNotAllowedException(HTTPException):
    """
    405 Method Not Allowed - HTTP method not supported for this endpoint.

    Use the Allow header to indicate which methods are supported.

    Example:
        >>> raise MethodNotAllowedException(
        ...     message="POST not allowed",
        ...     headers={"Allow": "GET, HEAD"}
        ... )
    """

    status_code: ClassVar[int] = 405

    def __init__(
        self,
        message: str = "Method not allowed",
        *,
        error_code: str = "METHOD_NOT_ALLOWED",
        details: dict[str, Any] | None = None,
        correlation_id: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code=error_code,
            details=details,
            correlation_id=correlation_id,
            severity=ErrorSeverity.WARNING,
            headers=headers,
        )


class ConflictException(HTTPException):
    """
    409 Conflict - The request conflicts with current resource state.

    Use for:
    - Duplicate resources
    - Concurrent modification conflicts
    - State machine violations

    Example:
        >>> raise ConflictException(
        ...     message="Email already exists",
        ...     details={"field": "email"}
        ... )
    """

    status_code: ClassVar[int] = 409

    def __init__(
        self,
        message: str = "Resource conflict",
        *,
        error_code: str = "CONFLICT",
        details: dict[str, Any] | None = None,
        correlation_id: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code=error_code,
            details=details,
            correlation_id=correlation_id,
            severity=ErrorSeverity.WARNING,
            headers=headers,
        )


class UnprocessableEntityException(HTTPException):
    """
    422 Unprocessable Entity - Request is well-formed but semantically invalid.

    This is the base class for validation errors. For detailed field-level
    validation errors, use ValidationException from shared.exceptions.validation.

    Example:
        >>> raise UnprocessableEntityException(message="Validation failed")
    """

    status_code: ClassVar[int] = 422

    def __init__(
        self,
        message: str = "Unprocessable entity",
        *,
        error_code: str = "UNPROCESSABLE_ENTITY",
        details: dict[str, Any] | None = None,
        correlation_id: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code=error_code,
            details=details,
            correlation_id=correlation_id,
            severity=ErrorSeverity.WARNING,
            headers=headers,
        )


class RateLimitException(HTTPException):
    """
    429 Too Many Requests - Rate limit exceeded.

    Includes Retry-After header to indicate when the client can retry.

    Example:
        >>> raise RateLimitException(retry_after=60)
    """

    status_code: ClassVar[int] = 429

    def __init__(
        self,
        message: str = "Too many requests",
        *,
        error_code: str = "RATE_LIMITED",
        retry_after: int | None = None,
        details: dict[str, Any] | None = None,
        correlation_id: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        _headers = headers or {}
        _details = details or {}

        if retry_after is not None:
            _headers["Retry-After"] = str(retry_after)
            _details["retry_after_seconds"] = retry_after

        super().__init__(
            message=message,
            error_code=error_code,
            details=_details,
            correlation_id=correlation_id,
            severity=ErrorSeverity.WARNING,
            headers=_headers,
        )


# =============================================================================
# 5xx Server Errors
# =============================================================================


class InternalServerException(HTTPException):
    """
    500 Internal Server Error - An unexpected error occurred.

    Internal details are hidden from API responses to prevent information leakage.

    Example:
        >>> raise InternalServerException(message="Database error")
    """

    status_code: ClassVar[int] = 500

    def __init__(
        self,
        message: str = "Internal server error",
        *,
        error_code: str = "INTERNAL_ERROR",
        details: dict[str, Any] | None = None,
        correlation_id: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code=error_code,
            details=details,
            correlation_id=correlation_id,
            severity=ErrorSeverity.ERROR,
            headers=headers,
        )

    def to_response(self) -> dict[str, Any]:
        """
        Generate API response, hiding internal details.

        Internal server errors should not leak sensitive information
        to clients. Only the error code and a generic message are returned.
        """
        body: dict[str, Any] = {
            "error": {
                "code": self.error_code,
                "message": "An internal error occurred. Please try again later.",
            }
        }

        if self.correlation_id:
            body["error"]["correlation_id"] = self.correlation_id

        return {
            "status_code": self.status_code,
            "body": body,
        }


class BadGatewayException(HTTPException):
    """
    502 Bad Gateway - Upstream service returned an invalid response.

    Use for:
    - Upstream service errors
    - Invalid responses from dependencies
    - Proxy errors

    Example:
        >>> raise BadGatewayException(
        ...     details={"upstream_service": "payment-service"}
        ... )
    """

    status_code: ClassVar[int] = 502

    def __init__(
        self,
        message: str = "Bad gateway",
        *,
        error_code: str = "BAD_GATEWAY",
        details: dict[str, Any] | None = None,
        correlation_id: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code=error_code,
            details=details,
            correlation_id=correlation_id,
            severity=ErrorSeverity.ERROR,
            headers=headers,
        )


class ServiceUnavailableException(HTTPException):
    """
    503 Service Unavailable - Service is temporarily unavailable.

    Use for:
    - Planned maintenance
    - Temporary overload
    - Circuit breaker open state

    Example:
        >>> raise ServiceUnavailableException(
        ...     message="Service under maintenance",
        ...     headers={"Retry-After": "3600"}
        ... )
    """

    status_code: ClassVar[int] = 503

    def __init__(
        self,
        message: str = "Service unavailable",
        *,
        error_code: str = "SERVICE_UNAVAILABLE",
        details: dict[str, Any] | None = None,
        correlation_id: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code=error_code,
            details=details,
            correlation_id=correlation_id,
            severity=ErrorSeverity.ERROR,
            headers=headers,
        )


class GatewayTimeoutException(HTTPException):
    """
    504 Gateway Timeout - Upstream service did not respond in time.

    Use for:
    - Upstream request timeouts
    - Slow dependency services
    - Network timeouts

    Example:
        >>> raise GatewayTimeoutException(
        ...     details={"timeout_seconds": 30, "upstream": "inventory-service"}
        ... )
    """

    status_code: ClassVar[int] = 504

    def __init__(
        self,
        message: str = "Gateway timeout",
        *,
        error_code: str = "GATEWAY_TIMEOUT",
        details: dict[str, Any] | None = None,
        correlation_id: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code=error_code,
            details=details,
            correlation_id=correlation_id,
            severity=ErrorSeverity.ERROR,
            headers=headers,
        )
