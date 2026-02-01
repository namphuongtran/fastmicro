"""
Unit tests for database exceptions.

Tests cover:
- Connection errors
- Query errors with SQL context
- Integrity constraint violations
- Transaction errors
- Timeout errors
- Wrapping of original exceptions
"""

from __future__ import annotations

from shared.exceptions.base import BaseServiceException, ErrorSeverity
from shared.exceptions.database import (
    ConnectionException,
    DatabaseException,
    IntegrityException,
    QueryException,
    TimeoutException,
    TransactionException,
)


class TestDatabaseExceptionBase:
    """Tests for base DatabaseException class."""

    def test_inherits_from_base(self) -> None:
        """DatabaseException inherits from BaseServiceException."""
        exc = DatabaseException(message="Database error")
        assert isinstance(exc, BaseServiceException)

    def test_default_error_code(self) -> None:
        """DatabaseException has default error code."""
        exc = DatabaseException(message="Database error")
        assert exc.error_code == "DATABASE_ERROR"

    def test_default_severity(self) -> None:
        """DatabaseException defaults to ERROR severity."""
        exc = DatabaseException(message="Database error")
        assert exc.severity == ErrorSeverity.ERROR

    def test_with_original_exception(self) -> None:
        """DatabaseException can wrap original exception."""
        original = Exception("Original DB error")
        exc = DatabaseException(
            message="Database operation failed",
            original_exception=original,
        )

        assert exc.original_exception is original
        assert exc.__cause__ is original

    def test_to_dict_includes_database_info(self) -> None:
        """to_dict() includes database-specific information."""
        exc = DatabaseException(
            message="Database error",
            details={"operation": "SELECT"},
        )

        result = exc.to_dict()
        assert result["details"]["operation"] == "SELECT"


class TestConnectionException:
    """Tests for database connection errors."""

    def test_default_values(self) -> None:
        """ConnectionException has correct defaults."""
        exc = ConnectionException()

        assert exc.error_code == "DB_CONNECTION_ERROR"
        assert exc.message == "Database connection failed"
        assert exc.severity == ErrorSeverity.CRITICAL

    def test_with_connection_details(self) -> None:
        """ConnectionException can include connection info."""
        exc = ConnectionException(
            message="Cannot connect to PostgreSQL",
            details={
                "host": "db.example.com",
                "port": 5432,
                "database": "myapp",
            },
        )

        assert exc.details["host"] == "db.example.com"
        assert exc.details["port"] == 5432

    def test_wraps_connection_error(self) -> None:
        """ConnectionException wraps underlying connection error."""
        original = ConnectionRefusedError("Connection refused")
        exc = ConnectionException(
            message="Database unavailable",
            original_exception=original,
        )

        assert exc.__cause__ is original


class TestQueryException:
    """Tests for query execution errors."""

    def test_default_values(self) -> None:
        """QueryException has correct defaults."""
        exc = QueryException()

        assert exc.error_code == "DB_QUERY_ERROR"
        assert "Query" in exc.message or "query" in exc.message.lower()

    def test_with_sql_context(self) -> None:
        """QueryException can include SQL context (sanitized)."""
        exc = QueryException(
            message="Query execution failed",
            details={
                "query_type": "SELECT",
                "table": "users",
                "error_position": 42,
            },
        )

        assert exc.details["query_type"] == "SELECT"
        assert exc.details["table"] == "users"

    def test_does_not_expose_full_query_by_default(self) -> None:
        """QueryException should not expose full SQL by default."""
        exc = QueryException(
            message="Syntax error",
            details={"query": "SELECT * FROM users WHERE id = 1"},
        )

        response = exc.to_dict(safe_mode=True)

        # In safe mode, raw query should not be exposed
        assert "SELECT" not in str(response.get("details", {}))


class TestIntegrityException:
    """Tests for integrity constraint violations."""

    def test_default_values(self) -> None:
        """IntegrityException has correct defaults."""
        exc = IntegrityException()

        assert exc.error_code == "DB_INTEGRITY_ERROR"
        assert exc.message == "Database integrity constraint violated"

    def test_unique_constraint_violation(self) -> None:
        """IntegrityException can represent unique constraint violation."""
        exc = IntegrityException.unique_violation(
            constraint_name="users_email_key",
            field="email",
            value="test@example.com",
        )

        assert exc.error_code == "DB_UNIQUE_VIOLATION"
        assert exc.details["constraint"] == "users_email_key"
        assert exc.details["field"] == "email"
        assert exc.details["violation_type"] == "unique"

    def test_foreign_key_violation(self) -> None:
        """IntegrityException can represent FK violation."""
        exc = IntegrityException.foreign_key_violation(
            constraint_name="orders_user_id_fkey",
            field="user_id",
            referenced_table="users",
        )

        assert exc.error_code == "DB_FK_VIOLATION"
        assert exc.details["constraint"] == "orders_user_id_fkey"
        assert exc.details["referenced_table"] == "users"
        assert exc.details["violation_type"] == "foreign_key"

    def test_not_null_violation(self) -> None:
        """IntegrityException can represent NOT NULL violation."""
        exc = IntegrityException.not_null_violation(
            field="username",
            table="users",
        )

        assert exc.error_code == "DB_NOT_NULL_VIOLATION"
        assert exc.details["field"] == "username"
        assert exc.details["violation_type"] == "not_null"

    def test_check_constraint_violation(self) -> None:
        """IntegrityException can represent CHECK constraint violation."""
        exc = IntegrityException.check_violation(
            constraint_name="users_age_check",
            field="age",
        )

        assert exc.error_code == "DB_CHECK_VIOLATION"
        assert exc.details["constraint"] == "users_age_check"
        assert exc.details["violation_type"] == "check"


class TestTransactionException:
    """Tests for transaction-related errors."""

    def test_default_values(self) -> None:
        """TransactionException has correct defaults."""
        exc = TransactionException()

        assert exc.error_code == "DB_TRANSACTION_ERROR"
        assert exc.severity == ErrorSeverity.ERROR

    def test_rollback_info(self) -> None:
        """TransactionException can include rollback status."""
        exc = TransactionException(
            message="Transaction failed",
            details={
                "rolled_back": True,
                "savepoint": "sp_1",
            },
        )

        assert exc.details["rolled_back"] is True
        assert exc.details["savepoint"] == "sp_1"

    def test_deadlock_detection(self) -> None:
        """TransactionException can indicate deadlock."""
        exc = TransactionException.deadlock_detected(
            table="orders",
            operation="UPDATE",
        )

        assert exc.error_code == "DB_DEADLOCK"
        assert exc.details["deadlock"] is True
        assert exc.details["table"] == "orders"

    def test_serialization_failure(self) -> None:
        """TransactionException can indicate serialization failure."""
        exc = TransactionException.serialization_failure()

        assert exc.error_code == "DB_SERIALIZATION_FAILURE"
        assert "serialization" in exc.message.lower() or "retry" in exc.message.lower()


class TestTimeoutException:
    """Tests for database timeout errors."""

    def test_default_values(self) -> None:
        """TimeoutException has correct defaults."""
        exc = TimeoutException()

        assert exc.error_code == "DB_TIMEOUT"
        assert "timed out" in exc.message.lower()

    def test_with_timeout_details(self) -> None:
        """TimeoutException can include timeout configuration."""
        exc = TimeoutException(
            message="Query timed out",
            details={
                "timeout_seconds": 30,
                "query_type": "SELECT",
                "table": "large_table",
            },
        )

        assert exc.details["timeout_seconds"] == 30
        assert exc.details["query_type"] == "SELECT"

    def test_connection_timeout(self) -> None:
        """TimeoutException for connection timeout."""
        exc = TimeoutException.connection_timeout(timeout_seconds=5)

        assert exc.error_code == "DB_CONNECTION_TIMEOUT"
        assert exc.details["timeout_seconds"] == 5
        assert exc.details["timeout_type"] == "connection"

    def test_query_timeout(self) -> None:
        """TimeoutException for query timeout."""
        exc = TimeoutException.query_timeout(timeout_seconds=30)

        assert exc.error_code == "DB_QUERY_TIMEOUT"
        assert exc.details["timeout_seconds"] == 30
        assert exc.details["timeout_type"] == "query"


class TestDatabaseExceptionFromSQLAlchemy:
    """Tests for converting SQLAlchemy exceptions to our exceptions."""

    def test_from_sqlalchemy_integrity_error(self) -> None:
        """DatabaseException.from_exception() handles IntegrityError pattern."""
        # Simulate SQLAlchemy IntegrityError message pattern
        original_msg = '(psycopg2.errors.UniqueViolation) duplicate key value violates unique constraint "users_email_key"'
        original = Exception(original_msg)

        exc = DatabaseException.from_exception(original)

        assert isinstance(exc, (DatabaseException, IntegrityException))
        assert exc.__cause__ is original

    def test_from_sqlalchemy_timeout_error(self) -> None:
        """DatabaseException.from_exception() handles timeout patterns."""
        original = TimeoutError("Connection timed out")

        exc = DatabaseException.from_exception(original)

        assert isinstance(exc, TimeoutException)
        assert exc.__cause__ is original
