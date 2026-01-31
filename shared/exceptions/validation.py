"""
Validation exception classes compatible with Pydantic validation errors.

This module provides structured validation exceptions that integrate
seamlessly with FastAPI's error handling and produce Pydantic-compatible
error responses.

Example:
    >>> from shared.exceptions.validation import ValidationException, FieldError
    >>> errors = [
    ...     FieldError(loc=("body", "email"), msg="Invalid email", type="value_error.email")
    ... ]
    >>> raise ValidationException(errors=errors)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Self

from shared.exceptions.http import UnprocessableEntityException

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = [
    "FieldError",
    "ValidationException",
]


@dataclass(frozen=True, slots=True)
class FieldError:
    """
    Represents a single field validation error.

    This class matches the Pydantic ValidationError format for seamless
    integration with FastAPI's error handling.

    Attributes:
        loc: Location of the error as a tuple (e.g., ("body", "email")).
        msg: Human-readable error message.
        type: Error type identifier (e.g., "value_error.email").
        ctx: Additional context for the error (optional).

    Example:
        >>> error = FieldError(
        ...     loc=("body", "email"),
        ...     msg="value is not a valid email address",
        ...     type="value_error.email"
        ... )
        >>> error.to_dict()
        {'loc': ['body', 'email'], 'msg': 'value is not a valid email address', ...}
    """

    loc: tuple[str | int, ...]
    msg: str
    type: str
    ctx: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to Pydantic-compatible dictionary format.

        Returns:
            Dictionary matching Pydantic's error format.
        """
        result: dict[str, Any] = {
            "loc": list(self.loc),  # Convert tuple to list for JSON
            "msg": self.msg,
            "type": self.type,
        }
        if self.ctx is not None:
            result["ctx"] = self.ctx
        return result


class ValidationException(UnprocessableEntityException):
    """
    Exception for validation errors with detailed field information.

    Inherits from UnprocessableEntityException (422) and provides
    structured error information compatible with Pydantic's validation
    error format.

    Attributes:
        errors: List of FieldError objects describing each validation failure.

    Example:
        >>> errors = [
        ...     FieldError(loc=("body", "email"), msg="Invalid email", type="value_error"),
        ...     FieldError(loc=("body", "age"), msg="Must be positive", type="value_error"),
        ... ]
        >>> raise ValidationException(errors=errors)
    """

    def __init__(
        self,
        errors: Sequence[FieldError],
        *,
        message: str = "Validation failed",
        error_code: str = "VALIDATION_ERROR",
        correlation_id: str | None = None,
    ) -> None:
        """
        Initialize validation exception.

        Args:
            errors: List of field validation errors.
            message: Human-readable summary message.
            error_code: Unique error identifier.
            correlation_id: Distributed tracing ID.
        """
        self.errors = list(errors)

        # Build details with serialized errors
        details: dict[str, Any] = {
            "errors": [e.to_dict() for e in self.errors],
        }

        super().__init__(
            message=message,
            error_code=error_code,
            details=details,
            correlation_id=correlation_id,
        )

    def to_response(self) -> dict[str, Any]:
        """
        Generate API response with validation errors.

        Returns:
            Response dictionary with structured error information.
        """
        body: dict[str, Any] = {
            "error": {
                "code": self.error_code,
                "message": self.message,
                "details": {
                    "errors": [e.to_dict() for e in self.errors],
                },
            }
        }

        if self.correlation_id:
            body["error"]["correlation_id"] = self.correlation_id

        return {
            "status_code": self.status_code,
            "body": body,
        }

    @classmethod
    def from_errors(
        cls,
        error_dicts: Sequence[dict[str, Any]],
        *,
        message: str = "Validation failed",
        correlation_id: str | None = None,
    ) -> Self:
        """
        Create ValidationException from a list of error dictionaries.

        This is useful for converting Pydantic validation errors or
        similar formats.

        Args:
            error_dicts: List of error dictionaries with loc, msg, type keys.
            message: Human-readable summary message.
            correlation_id: Distributed tracing ID.

        Returns:
            Configured ValidationException instance.

        Example:
            >>> errors = [
            ...     {"loc": ("body", "email"), "msg": "Invalid", "type": "error"}
            ... ]
            >>> exc = ValidationException.from_errors(errors)
        """
        field_errors = [
            FieldError(
                loc=tuple(e.get("loc", ())),
                msg=e.get("msg", "Validation error"),
                type=e.get("type", "value_error"),
                ctx=e.get("ctx"),
            )
            for e in error_dicts
        ]
        return cls(
            errors=field_errors,
            message=message,
            correlation_id=correlation_id,
        )

    @classmethod
    def for_field(
        cls,
        field: str,
        message: str,
        error_type: str,
        *,
        location: str = "body",
        ctx: dict[str, Any] | None = None,
        correlation_id: str | None = None,
    ) -> Self:
        """
        Create ValidationException for a single field error.

        Args:
            field: Field name that failed validation.
            message: Error message.
            error_type: Error type identifier.
            location: Location prefix (default: "body").
            ctx: Additional error context.
            correlation_id: Distributed tracing ID.

        Returns:
            Configured ValidationException instance.

        Example:
            >>> exc = ValidationException.for_field(
            ...     field="email",
            ...     message="Invalid email format",
            ...     error_type="value_error.email"
            ... )
        """
        error = FieldError(
            loc=(location, field),
            msg=message,
            type=error_type,
            ctx=ctx,
        )
        return cls(
            errors=[error],
            message=f"Validation failed for field '{field}'",
            correlation_id=correlation_id,
        )

    @classmethod
    def for_missing_field(
        cls,
        field: str,
        *,
        location: str = "body",
        correlation_id: str | None = None,
    ) -> Self:
        """
        Create ValidationException for a missing required field.

        Args:
            field: Name of the missing field.
            location: Location prefix (default: "body").
            correlation_id: Distributed tracing ID.

        Returns:
            Configured ValidationException instance.

        Example:
            >>> exc = ValidationException.for_missing_field("username")
        """
        error = FieldError(
            loc=(location, field),
            msg=f"Field '{field}' is required",
            type="value_error.missing",
        )
        return cls(
            errors=[error],
            message=f"Missing required field: {field}",
            correlation_id=correlation_id,
        )

    @classmethod
    def for_invalid_type(
        cls,
        field: str,
        expected_type: str,
        actual_value: Any,
        *,
        location: str = "body",
        correlation_id: str | None = None,
    ) -> Self:
        """
        Create ValidationException for a type mismatch.

        Args:
            field: Field name with wrong type.
            expected_type: Expected type name.
            actual_value: The value that was provided.
            location: Location prefix (default: "body").
            correlation_id: Distributed tracing ID.

        Returns:
            Configured ValidationException instance.

        Example:
            >>> exc = ValidationException.for_invalid_type(
            ...     field="age",
            ...     expected_type="integer",
            ...     actual_value="not_a_number"
            ... )
        """
        actual_type = type(actual_value).__name__
        error = FieldError(
            loc=(location, field),
            msg=f"Expected {expected_type}, got {actual_type}",
            type="type_error",
            ctx={
                "expected_type": expected_type,
                "actual_type": actual_type,
            },
        )
        return cls(
            errors=[error],
            message=f"Invalid type for field '{field}'",
            correlation_id=correlation_id,
        )
