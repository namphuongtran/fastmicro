"""
Unit tests for BaseServiceException.

Tests cover:
- Exception creation with default and custom parameters
- Serialization to dict format
- Correlation ID propagation
- Exception chaining
- Timestamp auto-generation
"""

from __future__ import annotations

from datetime import UTC, datetime

from shared.exceptions.base import BaseServiceException, ErrorSeverity


class TestBaseServiceExceptionCreation:
    """Tests for BaseServiceException instantiation."""

    def test_creation_with_message_only(self) -> None:
        """Exception can be created with just a message."""
        exc = BaseServiceException(message="Something went wrong")

        assert str(exc) == "Something went wrong"
        assert exc.message == "Something went wrong"
        assert exc.error_code == "INTERNAL_ERROR"  # default
        assert exc.details == {}
        assert exc.correlation_id is None
        assert exc.severity == ErrorSeverity.ERROR

    def test_creation_with_all_parameters(self) -> None:
        """Exception accepts all parameters."""
        details = {"user_id": "123", "action": "delete"}
        exc = BaseServiceException(
            message="Resource not found",
            error_code="RES_NOT_FOUND",
            details=details,
            correlation_id="trace-abc-123",
            severity=ErrorSeverity.WARNING,
        )

        assert exc.message == "Resource not found"
        assert exc.error_code == "RES_NOT_FOUND"
        assert exc.details == details
        assert exc.correlation_id == "trace-abc-123"
        assert exc.severity == ErrorSeverity.WARNING

    def test_timestamp_auto_generated(self) -> None:
        """Timestamp is automatically set on creation."""
        before = datetime.now(UTC)
        exc = BaseServiceException(message="Test")
        after = datetime.now(UTC)

        assert exc.timestamp is not None
        assert before <= exc.timestamp <= after

    def test_timestamp_can_be_provided(self) -> None:
        """Timestamp can be explicitly provided."""
        custom_time = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)
        exc = BaseServiceException(message="Test", timestamp=custom_time)

        assert exc.timestamp == custom_time


class TestBaseServiceExceptionSerialization:
    """Tests for exception serialization."""

    def test_to_dict_contains_all_fields(self) -> None:
        """to_dict() returns all exception fields."""
        exc = BaseServiceException(
            message="Test error",
            error_code="TEST_001",
            details={"key": "value"},
            correlation_id="corr-123",
        )

        result = exc.to_dict()

        assert result["message"] == "Test error"
        assert result["error_code"] == "TEST_001"
        assert result["details"] == {"key": "value"}
        assert result["correlation_id"] == "corr-123"
        assert result["severity"] == "error"
        assert "timestamp" in result
        assert result["type"] == "BaseServiceException"

    def test_to_dict_excludes_none_correlation_id_by_default(self) -> None:
        """to_dict() can exclude None values."""
        exc = BaseServiceException(message="Test")

        result = exc.to_dict(exclude_none=True)

        assert "correlation_id" not in result

    def test_to_dict_includes_none_when_requested(self) -> None:
        """to_dict() includes None values when exclude_none=False."""
        exc = BaseServiceException(message="Test")

        result = exc.to_dict(exclude_none=False)

        assert "correlation_id" in result
        assert result["correlation_id"] is None

    def test_to_dict_timestamp_is_iso_format(self) -> None:
        """Timestamp is serialized as ISO 8601 string."""
        exc = BaseServiceException(message="Test")

        result = exc.to_dict()

        # Should be parseable ISO format
        parsed = datetime.fromisoformat(result["timestamp"])
        assert parsed == exc.timestamp


class TestBaseServiceExceptionChaining:
    """Tests for exception chaining support."""

    def test_exception_chaining_with_cause(self) -> None:
        """Exception can chain to original cause."""
        original = ValueError("Original error")

        try:
            try:
                raise original
            except ValueError as e:
                raise BaseServiceException(
                    message="Wrapped error",
                    error_code="WRAP_001",
                ) from e
        except BaseServiceException as exc:
            assert exc.__cause__ is original
            assert exc.message == "Wrapped error"

    def test_to_dict_includes_cause_when_present(self) -> None:
        """to_dict() includes cause information when exception is chained."""
        original = ValueError("Original error")

        try:
            raise BaseServiceException(message="Wrapped") from original
        except BaseServiceException as exc:
            result = exc.to_dict()

            assert "cause" in result
            assert result["cause"]["type"] == "ValueError"
            assert result["cause"]["message"] == "Original error"


class TestBaseServiceExceptionCorrelationId:
    """Tests for correlation ID handling."""

    def test_correlation_id_propagation(self) -> None:
        """Correlation ID can be set and retrieved."""
        exc = BaseServiceException(
            message="Test",
            correlation_id="trace-xyz-789",
        )

        assert exc.correlation_id == "trace-xyz-789"

    def test_with_correlation_id_creates_new_instance(self) -> None:
        """with_correlation_id() creates a new exception with the ID."""
        original = BaseServiceException(message="Test", error_code="TEST_001")
        new_exc = original.with_correlation_id("new-trace-id")

        assert new_exc is not original
        assert new_exc.correlation_id == "new-trace-id"
        assert new_exc.message == original.message
        assert new_exc.error_code == original.error_code
        assert original.correlation_id is None  # Original unchanged


class TestErrorSeverity:
    """Tests for ErrorSeverity enum."""

    def test_severity_values(self) -> None:
        """ErrorSeverity has expected values."""
        assert ErrorSeverity.DEBUG.value == "debug"
        assert ErrorSeverity.INFO.value == "info"
        assert ErrorSeverity.WARNING.value == "warning"
        assert ErrorSeverity.ERROR.value == "error"
        assert ErrorSeverity.CRITICAL.value == "critical"

    def test_severity_comparison(self) -> None:
        """Severities can be compared by level."""
        assert ErrorSeverity.DEBUG < ErrorSeverity.INFO
        assert ErrorSeverity.INFO < ErrorSeverity.WARNING
        assert ErrorSeverity.WARNING < ErrorSeverity.ERROR
        assert ErrorSeverity.ERROR < ErrorSeverity.CRITICAL
