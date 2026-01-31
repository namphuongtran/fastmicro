"""
Base exception classes for the shared library.

This module provides the foundational exception hierarchy for all services,
supporting correlation IDs for distributed tracing, structured serialization,
and exception chaining for root cause analysis.

Example:
    >>> from shared.exceptions.base import BaseServiceException, ErrorSeverity
    >>> exc = BaseServiceException(
    ...     message="Operation failed",
    ...     error_code="OP_FAILED",
    ...     correlation_id="trace-123",
    ... )
    >>> exc.to_dict()
    {'type': 'BaseServiceException', 'message': 'Operation failed', ...}
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from functools import total_ordering
from typing import TYPE_CHECKING, Any, Self

if TYPE_CHECKING:
    from collections.abc import Mapping

__all__ = [
    "BaseServiceException",
    "ErrorSeverity",
]


@total_ordering
class ErrorSeverity(Enum):
    """
    Severity levels for exceptions, ordered from least to most severe.

    Used for logging, alerting, and monitoring integration.

    Example:
        >>> ErrorSeverity.WARNING < ErrorSeverity.ERROR
        True
    """

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

    def __lt__(self, other: object) -> bool:
        """Compare severity levels."""
        if not isinstance(other, ErrorSeverity):
            return NotImplemented
        order = [self.DEBUG, self.INFO, self.WARNING, self.ERROR, self.CRITICAL]
        return order.index(self) < order.index(other)

    def __eq__(self, other: object) -> bool:
        """Check equality with another severity."""
        if not isinstance(other, ErrorSeverity):
            return NotImplemented
        return self.value == other.value

    def __hash__(self) -> int:
        """Make ErrorSeverity hashable."""
        return hash(self.value)


class BaseServiceException(Exception):
    """
    Base exception class for all service exceptions.

    Provides:
    - Structured error information (code, message, details)
    - Correlation ID for distributed tracing
    - Automatic timestamp
    - Serialization to dict/JSON format
    - Exception chaining support

    Attributes:
        message: Human-readable error description.
        error_code: Unique error identifier (e.g., "AUTH_001").
        details: Additional context as key-value pairs.
        correlation_id: Distributed tracing ID for request tracking.
        timestamp: When the exception occurred (UTC).
        severity: Error severity level for logging/alerting.

    Example:
        >>> try:
        ...     raise BaseServiceException(
        ...         message="User not found",
        ...         error_code="USER_404",
        ...         details={"user_id": "123"},
        ...     )
        ... except BaseServiceException as e:
        ...     print(e.to_dict())
    """

    def __init__(
        self,
        message: str = "An error occurred",
        *,
        error_code: str = "INTERNAL_ERROR",
        details: dict[str, Any] | None = None,
        correlation_id: str | None = None,
        timestamp: datetime | None = None,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
    ) -> None:
        """
        Initialize the exception.

        Args:
            message: Human-readable error description.
            error_code: Unique error identifier.
            details: Additional error context.
            correlation_id: Distributed tracing ID.
            timestamp: When the error occurred (defaults to now).
            severity: Error severity level.
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.correlation_id = correlation_id
        self.timestamp = timestamp or datetime.now(UTC)
        self.severity = severity

    def __str__(self) -> str:
        """Return the error message."""
        return self.message

    def __repr__(self) -> str:
        """Return detailed representation for debugging."""
        return (
            f"{self.__class__.__name__}("
            f"message={self.message!r}, "
            f"error_code={self.error_code!r}, "
            f"correlation_id={self.correlation_id!r})"
        )

    def to_dict(
        self,
        *,
        exclude_none: bool = True,
        include_cause: bool = True,
    ) -> dict[str, Any]:
        """
        Serialize exception to a dictionary.

        Args:
            exclude_none: If True, omit fields with None values.
            include_cause: If True, include chained exception info.

        Returns:
            Dictionary representation suitable for JSON serialization.

        Example:
            >>> exc = BaseServiceException(message="Error", error_code="E001")
            >>> exc.to_dict()
            {'type': 'BaseServiceException', 'message': 'Error', ...}
        """
        result: dict[str, Any] = {
            "type": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code,
            "details": self.details,
            "severity": self.severity.value,
            "timestamp": self.timestamp.isoformat(),
        }

        if exclude_none:
            if self.correlation_id is not None:
                result["correlation_id"] = self.correlation_id
        else:
            result["correlation_id"] = self.correlation_id

        # Include cause information if present
        if include_cause and self.__cause__ is not None:
            result["cause"] = {
                "type": type(self.__cause__).__name__,
                "message": str(self.__cause__),
            }

        return result

    def with_correlation_id(self, correlation_id: str) -> Self:
        """
        Create a new exception instance with the given correlation ID.

        This is useful for adding tracing information without mutating
        the original exception.

        Args:
            correlation_id: The trace/correlation ID to attach.

        Returns:
            A new exception instance with the correlation ID set.

        Example:
            >>> exc = BaseServiceException(message="Error")
            >>> traced = exc.with_correlation_id("trace-123")
            >>> traced.correlation_id
            'trace-123'
        """
        new_exc = self.__class__(
            message=self.message,
            error_code=self.error_code,
            details=self.details.copy(),
            correlation_id=correlation_id,
            timestamp=self.timestamp,
            severity=self.severity,
        )
        if self.__cause__:
            new_exc.__cause__ = self.__cause__
        return new_exc
