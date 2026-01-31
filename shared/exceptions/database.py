"""
Database exception classes for wrapping database-related errors.

This module provides a hierarchy of database exceptions that wrap
underlying database driver errors and provide consistent error handling
across different database backends.

Example:
    >>> from shared.exceptions.database import IntegrityException
    >>> raise IntegrityException.unique_violation(
    ...     constraint_name="users_email_key",
    ...     field="email",
    ...     value="test@example.com"
    ... )
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, ClassVar, Self

from shared.exceptions.base import BaseServiceException, ErrorSeverity

if TYPE_CHECKING:
    pass

__all__ = [
    "DatabaseException",
    "ConnectionException",
    "QueryException",
    "IntegrityException",
    "TransactionException",
    "TimeoutException",
]


class DatabaseException(BaseServiceException):
    """
    Base exception for all database-related errors.

    Provides common functionality for wrapping database driver exceptions
    and converting them to structured error information.

    Attributes:
        original_exception: The underlying database exception, if any.

    Example:
        >>> try:
        ...     # database operation
        ... except Exception as e:
        ...     raise DatabaseException(
        ...         message="Database operation failed",
        ...         original_exception=e
        ...     ) from e
    """

    def __init__(
        self,
        message: str = "Database error occurred",
        *,
        error_code: str = "DATABASE_ERROR",
        details: dict[str, Any] | None = None,
        correlation_id: str | None = None,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        original_exception: BaseException | None = None,
    ) -> None:
        """
        Initialize database exception.

        Args:
            message: Human-readable error description.
            error_code: Unique error identifier.
            details: Additional error context.
            correlation_id: Distributed tracing ID.
            severity: Error severity level.
            original_exception: The underlying database exception.
        """
        super().__init__(
            message=message,
            error_code=error_code,
            details=details,
            correlation_id=correlation_id,
            severity=severity,
        )
        self.original_exception = original_exception
        if original_exception is not None:
            self.__cause__ = original_exception

    def to_dict(
        self,
        *,
        exclude_none: bool = True,
        include_cause: bool = True,
        safe_mode: bool = False,
    ) -> dict[str, Any]:
        """
        Serialize exception to dictionary.

        Args:
            exclude_none: If True, omit fields with None values.
            include_cause: If True, include chained exception info.
            safe_mode: If True, sanitize sensitive information like queries.

        Returns:
            Dictionary representation suitable for JSON serialization.
        """
        result = super().to_dict(exclude_none=exclude_none, include_cause=include_cause)

        if safe_mode:
            # Remove potentially sensitive information
            sanitized_details = {}
            sensitive_keys = {"query", "sql", "connection_string", "password"}
            for key, value in self.details.items():
                if key.lower() not in sensitive_keys:
                    sanitized_details[key] = value
            result["details"] = sanitized_details

        return result

    @classmethod
    def from_exception(cls, exc: BaseException) -> DatabaseException:
        """
        Create appropriate DatabaseException from an underlying exception.

        Analyzes the exception message to determine the most specific
        exception type to return.

        Args:
            exc: The original exception to wrap.

        Returns:
            Appropriate DatabaseException subclass instance.

        Example:
            >>> try:
            ...     # database operation
            ... except Exception as e:
            ...     raise DatabaseException.from_exception(e)
        """
        exc_str = str(exc).lower()

        # Check for timeout patterns
        if any(word in exc_str for word in ("timeout", "timed out")):
            return TimeoutException(
                message=str(exc),
                original_exception=exc,
            )

        # Check for connection patterns
        if any(word in exc_str for word in ("connection", "connect", "refused")):
            return ConnectionException(
                message=str(exc),
                original_exception=exc,
            )

        # Check for integrity patterns
        if any(
            word in exc_str
            for word in ("unique", "duplicate", "foreign key", "constraint", "integrity")
        ):
            return IntegrityException(
                message=str(exc),
                original_exception=exc,
            )

        # Default to base DatabaseException
        return cls(
            message=str(exc),
            original_exception=exc,
        )


class ConnectionException(DatabaseException):
    """
    Exception for database connection failures.

    Use for:
    - Connection refused
    - Authentication failures
    - Network errors
    - Connection pool exhaustion

    Example:
        >>> raise ConnectionException(
        ...     message="Cannot connect to PostgreSQL",
        ...     details={"host": "db.example.com", "port": 5432}
        ... )
    """

    def __init__(
        self,
        message: str = "Database connection failed",
        *,
        error_code: str = "DB_CONNECTION_ERROR",
        details: dict[str, Any] | None = None,
        correlation_id: str | None = None,
        original_exception: BaseException | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code=error_code,
            details=details,
            correlation_id=correlation_id,
            severity=ErrorSeverity.CRITICAL,
            original_exception=original_exception,
        )


class QueryException(DatabaseException):
    """
    Exception for query execution failures.

    Use for:
    - Syntax errors
    - Invalid table/column references
    - Query execution errors

    Example:
        >>> raise QueryException(
        ...     message="Syntax error in query",
        ...     details={"query_type": "SELECT", "table": "users"}
        ... )
    """

    def __init__(
        self,
        message: str = "Query execution failed",
        *,
        error_code: str = "DB_QUERY_ERROR",
        details: dict[str, Any] | None = None,
        correlation_id: str | None = None,
        original_exception: BaseException | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code=error_code,
            details=details,
            correlation_id=correlation_id,
            severity=ErrorSeverity.ERROR,
            original_exception=original_exception,
        )


class IntegrityException(DatabaseException):
    """
    Exception for database integrity constraint violations.

    Use for:
    - Unique constraint violations
    - Foreign key violations
    - NOT NULL violations
    - CHECK constraint violations

    Example:
        >>> raise IntegrityException.unique_violation(
        ...     constraint_name="users_email_key",
        ...     field="email",
        ...     value="test@example.com"
        ... )
    """

    def __init__(
        self,
        message: str = "Database integrity constraint violated",
        *,
        error_code: str = "DB_INTEGRITY_ERROR",
        details: dict[str, Any] | None = None,
        correlation_id: str | None = None,
        original_exception: BaseException | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code=error_code,
            details=details,
            correlation_id=correlation_id,
            severity=ErrorSeverity.ERROR,
            original_exception=original_exception,
        )

    @classmethod
    def unique_violation(
        cls,
        constraint_name: str,
        field: str,
        value: Any | None = None,
        *,
        correlation_id: str | None = None,
    ) -> Self:
        """
        Create exception for unique constraint violation.

        Args:
            constraint_name: Name of the violated constraint.
            field: Field that caused the violation.
            value: The duplicate value (optional).
            correlation_id: Optional trace ID.

        Returns:
            Configured IntegrityException instance.
        """
        details: dict[str, Any] = {
            "constraint": constraint_name,
            "field": field,
            "violation_type": "unique",
        }
        if value is not None:
            details["value"] = value

        return cls(
            message=f"Duplicate value for field '{field}'",
            error_code="DB_UNIQUE_VIOLATION",
            details=details,
            correlation_id=correlation_id,
        )

    @classmethod
    def foreign_key_violation(
        cls,
        constraint_name: str,
        field: str,
        referenced_table: str,
        *,
        correlation_id: str | None = None,
    ) -> Self:
        """
        Create exception for foreign key violation.

        Args:
            constraint_name: Name of the violated constraint.
            field: Field that caused the violation.
            referenced_table: Table that the FK references.
            correlation_id: Optional trace ID.

        Returns:
            Configured IntegrityException instance.
        """
        return cls(
            message=f"Foreign key violation on field '{field}'",
            error_code="DB_FK_VIOLATION",
            details={
                "constraint": constraint_name,
                "field": field,
                "referenced_table": referenced_table,
                "violation_type": "foreign_key",
            },
            correlation_id=correlation_id,
        )

    @classmethod
    def not_null_violation(
        cls,
        field: str,
        table: str,
        *,
        correlation_id: str | None = None,
    ) -> Self:
        """
        Create exception for NOT NULL violation.

        Args:
            field: Field that requires a value.
            table: Table containing the field.
            correlation_id: Optional trace ID.

        Returns:
            Configured IntegrityException instance.
        """
        return cls(
            message=f"Field '{field}' cannot be null",
            error_code="DB_NOT_NULL_VIOLATION",
            details={
                "field": field,
                "table": table,
                "violation_type": "not_null",
            },
            correlation_id=correlation_id,
        )

    @classmethod
    def check_violation(
        cls,
        constraint_name: str,
        field: str,
        *,
        correlation_id: str | None = None,
    ) -> Self:
        """
        Create exception for CHECK constraint violation.

        Args:
            constraint_name: Name of the violated constraint.
            field: Field that failed the check.
            correlation_id: Optional trace ID.

        Returns:
            Configured IntegrityException instance.
        """
        return cls(
            message=f"Check constraint violated on field '{field}'",
            error_code="DB_CHECK_VIOLATION",
            details={
                "constraint": constraint_name,
                "field": field,
                "violation_type": "check",
            },
            correlation_id=correlation_id,
        )


class TransactionException(DatabaseException):
    """
    Exception for transaction-related errors.

    Use for:
    - Transaction rollback
    - Deadlock detection
    - Serialization failures
    - Savepoint errors

    Example:
        >>> raise TransactionException.deadlock_detected(
        ...     table="orders",
        ...     operation="UPDATE"
        ... )
    """

    def __init__(
        self,
        message: str = "Transaction error occurred",
        *,
        error_code: str = "DB_TRANSACTION_ERROR",
        details: dict[str, Any] | None = None,
        correlation_id: str | None = None,
        original_exception: BaseException | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code=error_code,
            details=details,
            correlation_id=correlation_id,
            severity=ErrorSeverity.ERROR,
            original_exception=original_exception,
        )

    @classmethod
    def deadlock_detected(
        cls,
        table: str,
        operation: str,
        *,
        correlation_id: str | None = None,
    ) -> Self:
        """
        Create exception for deadlock detection.

        Args:
            table: Table involved in the deadlock.
            operation: Operation that caused the deadlock.
            correlation_id: Optional trace ID.

        Returns:
            Configured TransactionException instance.
        """
        return cls(
            message=f"Deadlock detected during {operation} on table '{table}'",
            error_code="DB_DEADLOCK",
            details={
                "deadlock": True,
                "table": table,
                "operation": operation,
            },
            correlation_id=correlation_id,
        )

    @classmethod
    def serialization_failure(
        cls,
        *,
        correlation_id: str | None = None,
    ) -> Self:
        """
        Create exception for serialization failure.

        Returns:
            Configured TransactionException instance.
        """
        return cls(
            message="Transaction serialization failure. Please retry the operation.",
            error_code="DB_SERIALIZATION_FAILURE",
            details={"serialization_failure": True},
            correlation_id=correlation_id,
        )


class TimeoutException(DatabaseException):
    """
    Exception for database timeout errors.

    Use for:
    - Connection timeouts
    - Query timeouts
    - Lock wait timeouts

    Example:
        >>> raise TimeoutException.query_timeout(timeout_seconds=30)
    """

    def __init__(
        self,
        message: str = "Database operation timed out",
        *,
        error_code: str = "DB_TIMEOUT",
        details: dict[str, Any] | None = None,
        correlation_id: str | None = None,
        original_exception: BaseException | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code=error_code,
            details=details,
            correlation_id=correlation_id,
            severity=ErrorSeverity.ERROR,
            original_exception=original_exception,
        )

    @classmethod
    def connection_timeout(
        cls,
        timeout_seconds: int,
        *,
        correlation_id: str | None = None,
    ) -> Self:
        """
        Create exception for connection timeout.

        Args:
            timeout_seconds: Configured timeout value.
            correlation_id: Optional trace ID.

        Returns:
            Configured TimeoutException instance.
        """
        return cls(
            message=f"Database connection timed out after {timeout_seconds} seconds",
            error_code="DB_CONNECTION_TIMEOUT",
            details={
                "timeout_seconds": timeout_seconds,
                "timeout_type": "connection",
            },
            correlation_id=correlation_id,
        )

    @classmethod
    def query_timeout(
        cls,
        timeout_seconds: int,
        *,
        correlation_id: str | None = None,
    ) -> Self:
        """
        Create exception for query timeout.

        Args:
            timeout_seconds: Configured timeout value.
            correlation_id: Optional trace ID.

        Returns:
            Configured TimeoutException instance.
        """
        return cls(
            message=f"Query execution timed out after {timeout_seconds} seconds",
            error_code="DB_QUERY_TIMEOUT",
            details={
                "timeout_seconds": timeout_seconds,
                "timeout_type": "query",
            },
            correlation_id=correlation_id,
        )
