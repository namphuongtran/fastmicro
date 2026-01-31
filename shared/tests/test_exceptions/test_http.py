"""
Unit tests for HTTP exceptions.

Tests cover:
- Status code mapping for each HTTP exception type
- Default messages and error codes
- Custom message support
- Response format generation
- Headers support
"""

from __future__ import annotations

from typing import Any

import pytest

from shared.exceptions.base import BaseServiceException, ErrorSeverity
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


class TestHTTPExceptionBase:
    """Tests for base HTTPException class."""

    def test_http_exception_inherits_from_base(self) -> None:
        """HTTPException inherits from BaseServiceException."""
        exc = HTTPException(
            status_code=500,
            message="Server error",
        )
        assert isinstance(exc, BaseServiceException)

    def test_http_exception_requires_status_code(self) -> None:
        """HTTPException requires a status code."""
        exc = HTTPException(status_code=400, message="Bad request")
        assert exc.status_code == 400

    def test_http_exception_with_headers(self) -> None:
        """HTTPException can include response headers."""
        headers = {"X-RateLimit-Remaining": "0", "Retry-After": "60"}
        exc = HTTPException(
            status_code=429,
            message="Rate limited",
            headers=headers,
        )
        assert exc.headers == headers

    def test_to_response_format(self) -> None:
        """to_response() returns API-friendly format."""
        exc = HTTPException(
            status_code=400,
            message="Invalid input",
            error_code="INVALID_INPUT",
            details={"field": "email"},
            correlation_id="req-123",
        )

        response = exc.to_response()

        assert response["status_code"] == 400
        assert response["body"]["error"]["message"] == "Invalid input"
        assert response["body"]["error"]["code"] == "INVALID_INPUT"
        assert response["body"]["error"]["details"] == {"field": "email"}
        assert response["body"]["error"]["correlation_id"] == "req-123"

    def test_to_response_includes_headers(self) -> None:
        """to_response() includes headers when present."""
        exc = HTTPException(
            status_code=429,
            message="Too many requests",
            headers={"Retry-After": "60"},
        )

        response = exc.to_response()

        assert response["headers"] == {"Retry-After": "60"}


class TestBadRequestException:
    """Tests for 400 Bad Request exception."""

    def test_default_values(self) -> None:
        """BadRequestException has correct defaults."""
        exc = BadRequestException()

        assert exc.status_code == 400
        assert exc.error_code == "BAD_REQUEST"
        assert exc.message == "Bad request"

    def test_custom_message(self) -> None:
        """BadRequestException accepts custom message."""
        exc = BadRequestException(message="Invalid JSON body")

        assert exc.message == "Invalid JSON body"
        assert exc.status_code == 400

    def test_with_details(self) -> None:
        """BadRequestException can include details."""
        exc = BadRequestException(
            message="Missing required field",
            details={"field": "username"},
        )

        assert exc.details == {"field": "username"}


class TestUnauthorizedException:
    """Tests for 401 Unauthorized exception."""

    def test_default_values(self) -> None:
        """UnauthorizedException has correct defaults."""
        exc = UnauthorizedException()

        assert exc.status_code == 401
        assert exc.error_code == "UNAUTHORIZED"
        assert exc.message == "Authentication required"

    def test_with_custom_message(self) -> None:
        """UnauthorizedException accepts custom message."""
        exc = UnauthorizedException(message="Token expired")

        assert exc.message == "Token expired"

    def test_with_www_authenticate_header(self) -> None:
        """UnauthorizedException can include WWW-Authenticate header."""
        exc = UnauthorizedException(
            message="Invalid token",
            headers={"WWW-Authenticate": 'Bearer realm="api"'},
        )

        assert exc.headers["WWW-Authenticate"] == 'Bearer realm="api"'


class TestForbiddenException:
    """Tests for 403 Forbidden exception."""

    def test_default_values(self) -> None:
        """ForbiddenException has correct defaults."""
        exc = ForbiddenException()

        assert exc.status_code == 403
        assert exc.error_code == "FORBIDDEN"
        assert exc.message == "Access denied"

    def test_with_resource_details(self) -> None:
        """ForbiddenException can include resource information."""
        exc = ForbiddenException(
            message="Insufficient permissions",
            details={
                "resource": "users",
                "action": "delete",
                "required_role": "admin",
            },
        )

        assert exc.details["resource"] == "users"
        assert exc.details["required_role"] == "admin"


class TestNotFoundException:
    """Tests for 404 Not Found exception."""

    def test_default_values(self) -> None:
        """NotFoundException has correct defaults."""
        exc = NotFoundException()

        assert exc.status_code == 404
        assert exc.error_code == "NOT_FOUND"
        assert exc.message == "Resource not found"

    def test_with_resource_type_and_id(self) -> None:
        """NotFoundException can specify resource details."""
        exc = NotFoundException(
            message="User not found",
            details={"resource_type": "User", "resource_id": "123"},
        )

        assert exc.details["resource_type"] == "User"
        assert exc.details["resource_id"] == "123"

    @staticmethod
    def for_resource(resource_type: str, resource_id: str) -> NotFoundException:
        """Factory method creates NotFoundException for a specific resource."""
        return NotFoundException.for_resource(resource_type, resource_id)

    def test_for_resource_factory_method(self) -> None:
        """for_resource() creates properly configured exception."""
        exc = NotFoundException.for_resource("User", "user-123")

        assert exc.message == "User with id 'user-123' not found"
        assert exc.details["resource_type"] == "User"
        assert exc.details["resource_id"] == "user-123"


class TestMethodNotAllowedException:
    """Tests for 405 Method Not Allowed exception."""

    def test_default_values(self) -> None:
        """MethodNotAllowedException has correct defaults."""
        exc = MethodNotAllowedException()

        assert exc.status_code == 405
        assert exc.error_code == "METHOD_NOT_ALLOWED"

    def test_with_allowed_methods(self) -> None:
        """MethodNotAllowedException can specify allowed methods."""
        exc = MethodNotAllowedException(
            message="POST not allowed",
            headers={"Allow": "GET, HEAD"},
        )

        assert exc.headers["Allow"] == "GET, HEAD"


class TestConflictException:
    """Tests for 409 Conflict exception."""

    def test_default_values(self) -> None:
        """ConflictException has correct defaults."""
        exc = ConflictException()

        assert exc.status_code == 409
        assert exc.error_code == "CONFLICT"
        assert exc.message == "Resource conflict"

    def test_for_duplicate_resource(self) -> None:
        """ConflictException can indicate duplicate resource."""
        exc = ConflictException(
            message="Email already exists",
            details={"field": "email", "value": "test@example.com"},
        )

        assert exc.details["field"] == "email"


class TestUnprocessableEntityException:
    """Tests for 422 Unprocessable Entity exception."""

    def test_default_values(self) -> None:
        """UnprocessableEntityException has correct defaults."""
        exc = UnprocessableEntityException()

        assert exc.status_code == 422
        assert exc.error_code == "UNPROCESSABLE_ENTITY"

    def test_with_validation_errors(self) -> None:
        """UnprocessableEntityException can include validation errors."""
        exc = UnprocessableEntityException(
            message="Validation failed",
            details={
                "errors": [
                    {"loc": ["body", "email"], "msg": "invalid email format"},
                ]
            },
        )

        assert len(exc.details["errors"]) == 1


class TestRateLimitException:
    """Tests for 429 Too Many Requests exception."""

    def test_default_values(self) -> None:
        """RateLimitException has correct defaults."""
        exc = RateLimitException()

        assert exc.status_code == 429
        assert exc.error_code == "RATE_LIMITED"
        assert exc.message == "Too many requests"

    def test_with_retry_after(self) -> None:
        """RateLimitException includes Retry-After header."""
        exc = RateLimitException(
            message="Rate limit exceeded",
            retry_after=60,
        )

        assert exc.headers["Retry-After"] == "60"
        assert exc.details["retry_after_seconds"] == 60


class TestInternalServerException:
    """Tests for 500 Internal Server Error exception."""

    def test_default_values(self) -> None:
        """InternalServerException has correct defaults."""
        exc = InternalServerException()

        assert exc.status_code == 500
        assert exc.error_code == "INTERNAL_ERROR"
        assert exc.message == "Internal server error"
        assert exc.severity == ErrorSeverity.ERROR

    def test_hides_internal_details_in_response(self) -> None:
        """InternalServerException hides sensitive details in response."""
        exc = InternalServerException(
            message="Database connection failed",
            details={"connection_string": "postgresql://..."},
        )

        response = exc.to_response()

        # Internal details should not leak to response
        assert "connection_string" not in str(response["body"])


class TestBadGatewayException:
    """Tests for 502 Bad Gateway exception."""

    def test_default_values(self) -> None:
        """BadGatewayException has correct defaults."""
        exc = BadGatewayException()

        assert exc.status_code == 502
        assert exc.error_code == "BAD_GATEWAY"

    def test_with_upstream_service(self) -> None:
        """BadGatewayException can specify upstream service."""
        exc = BadGatewayException(
            message="Upstream service unavailable",
            details={"upstream_service": "payment-service"},
        )

        assert exc.details["upstream_service"] == "payment-service"


class TestServiceUnavailableException:
    """Tests for 503 Service Unavailable exception."""

    def test_default_values(self) -> None:
        """ServiceUnavailableException has correct defaults."""
        exc = ServiceUnavailableException()

        assert exc.status_code == 503
        assert exc.error_code == "SERVICE_UNAVAILABLE"

    def test_with_maintenance_window(self) -> None:
        """ServiceUnavailableException can specify maintenance details."""
        exc = ServiceUnavailableException(
            message="Service under maintenance",
            headers={"Retry-After": "3600"},
            details={"reason": "scheduled_maintenance"},
        )

        assert exc.headers["Retry-After"] == "3600"
        assert exc.details["reason"] == "scheduled_maintenance"


class TestGatewayTimeoutException:
    """Tests for 504 Gateway Timeout exception."""

    def test_default_values(self) -> None:
        """GatewayTimeoutException has correct defaults."""
        exc = GatewayTimeoutException()

        assert exc.status_code == 504
        assert exc.error_code == "GATEWAY_TIMEOUT"
        assert exc.message == "Gateway timeout"

    def test_with_timeout_details(self) -> None:
        """GatewayTimeoutException can include timeout information."""
        exc = GatewayTimeoutException(
            message="Upstream request timed out",
            details={"timeout_seconds": 30, "upstream": "inventory-service"},
        )

        assert exc.details["timeout_seconds"] == 30


class TestHTTPExceptionStatusCodeMapping:
    """Tests verifying correct status code mapping for all exception types."""

    @pytest.mark.parametrize(
        "exception_class,expected_status",
        [
            (BadRequestException, 400),
            (UnauthorizedException, 401),
            (ForbiddenException, 403),
            (NotFoundException, 404),
            (MethodNotAllowedException, 405),
            (ConflictException, 409),
            (UnprocessableEntityException, 422),
            (RateLimitException, 429),
            (InternalServerException, 500),
            (BadGatewayException, 502),
            (ServiceUnavailableException, 503),
            (GatewayTimeoutException, 504),
        ],
    )
    def test_status_code_mapping(
        self, exception_class: type[HTTPException], expected_status: int
    ) -> None:
        """Each exception class maps to the correct HTTP status code."""
        exc = exception_class()
        assert exc.status_code == expected_status
