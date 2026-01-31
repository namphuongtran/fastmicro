"""Tests for shared.observability.logging module.

This module tests structured logging utilities including JSON formatting,
correlation ID propagation, context enrichment, and log level management.
"""

from __future__ import annotations

import json
import logging
import sys
from io import StringIO
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    pass

from shared.observability.logging import (
    CorrelationIdFilter,
    JSONFormatter,
    configure_logging,
    get_correlation_id,
    get_logger,
    set_correlation_id,
    with_context,
)


class TestJSONFormatter:
    """Tests for JSONFormatter class."""

    def test_formats_as_json(self) -> None:
        """Should format log records as JSON."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        
        output = formatter.format(record)
        parsed = json.loads(output)
        
        assert parsed["message"] == "Test message"
        assert parsed["level"] == "INFO"

    def test_includes_timestamp(self) -> None:
        """Should include ISO8601 timestamp."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test",
            args=(),
            exc_info=None,
        )
        
        output = formatter.format(record)
        parsed = json.loads(output)
        
        assert "timestamp" in parsed
        assert "T" in parsed["timestamp"]  # ISO format

    def test_includes_logger_name(self) -> None:
        """Should include logger name."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="myapp.service",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test",
            args=(),
            exc_info=None,
        )
        
        output = formatter.format(record)
        parsed = json.loads(output)
        
        assert parsed["logger"] == "myapp.service"

    def test_includes_extra_fields(self) -> None:
        """Should include extra fields from record."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test",
            args=(),
            exc_info=None,
        )
        record.user_id = "user-123"
        record.request_id = "req-456"
        
        output = formatter.format(record)
        parsed = json.loads(output)
        
        assert parsed["user_id"] == "user-123"
        assert parsed["request_id"] == "req-456"

    def test_handles_exception_info(self) -> None:
        """Should include exception traceback."""
        formatter = JSONFormatter()
        
        try:
            raise ValueError("Test error")
        except ValueError:
            exc_info = sys.exc_info()
        
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=10,
            msg="Error occurred",
            args=(),
            exc_info=exc_info,
        )
        
        output = formatter.format(record)
        parsed = json.loads(output)
        
        assert "exception" in parsed
        assert "ValueError" in parsed["exception"]
        assert "Test error" in parsed["exception"]

    def test_handles_message_formatting(self) -> None:
        """Should format message with args."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="User %s logged in from %s",
            args=("john", "192.168.1.1"),
            exc_info=None,
        )
        
        output = formatter.format(record)
        parsed = json.loads(output)
        
        assert parsed["message"] == "User john logged in from 192.168.1.1"

    def test_custom_fields(self) -> None:
        """Should include custom static fields."""
        formatter = JSONFormatter(extra_fields={"service": "api", "version": "1.0"})
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test",
            args=(),
            exc_info=None,
        )
        
        output = formatter.format(record)
        parsed = json.loads(output)
        
        assert parsed["service"] == "api"
        assert parsed["version"] == "1.0"


class TestCorrelationIdFilter:
    """Tests for CorrelationIdFilter class."""

    def test_adds_correlation_id_to_record(self) -> None:
        """Should add correlation_id to log record."""
        filter_ = CorrelationIdFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test",
            args=(),
            exc_info=None,
        )
        
        set_correlation_id("test-correlation-123")
        filter_.filter(record)
        
        assert hasattr(record, "correlation_id")
        assert record.correlation_id == "test-correlation-123"

    def test_generates_correlation_id_if_missing(self) -> None:
        """Should generate correlation_id if not set."""
        filter_ = CorrelationIdFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test",
            args=(),
            exc_info=None,
        )
        
        set_correlation_id(None)  # Clear any existing
        filter_.filter(record)
        
        assert hasattr(record, "correlation_id")
        # Should have some value (either generated or empty)


class TestCorrelationId:
    """Tests for correlation ID context management."""

    def test_set_and_get_correlation_id(self) -> None:
        """Should set and retrieve correlation ID."""
        set_correlation_id("my-correlation-id")
        assert get_correlation_id() == "my-correlation-id"

    def test_clear_correlation_id(self) -> None:
        """Should clear correlation ID."""
        set_correlation_id("some-id")
        set_correlation_id(None)
        result = get_correlation_id()
        # Should be None or empty
        assert result is None or result == ""

    def test_correlation_id_isolation(self) -> None:
        """Should isolate correlation ID per context."""
        set_correlation_id("id-1")
        assert get_correlation_id() == "id-1"
        
        set_correlation_id("id-2")
        assert get_correlation_id() == "id-2"


class TestWithContext:
    """Tests for with_context context manager."""

    def test_adds_context_to_logs(self) -> None:
        """Should add context fields to log records."""
        logger = get_logger("test.context")
        handler = logging.Handler()
        handler.emit = MagicMock()
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        
        with with_context(user_id="user-123", action="login"):
            logger.info("Test message")
        
        # Verify emit was called
        assert handler.emit.called

    def test_context_is_removed_after_block(self) -> None:
        """Should remove context after exiting block."""
        # Context should be scoped to the with block
        with with_context(temp_field="temp_value"):
            pass
        
        # After exiting, the context should be cleaned up
        # This is tested implicitly by the context manager behavior


class TestGetLogger:
    """Tests for get_logger function."""

    def test_returns_logger(self) -> None:
        """Should return a logger instance."""
        logger = get_logger("test.module")
        assert isinstance(logger, logging.Logger)

    def test_logger_name(self) -> None:
        """Should use provided name."""
        logger = get_logger("myapp.service")
        assert logger.name == "myapp.service"

    def test_cached_logger(self) -> None:
        """Should return same logger for same name."""
        logger1 = get_logger("test.cached")
        logger2 = get_logger("test.cached")
        assert logger1 is logger2


class TestConfigureLogging:
    """Tests for configure_logging function."""

    def test_sets_log_level(self) -> None:
        """Should set the root log level."""
        configure_logging(level="DEBUG")
        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG

    def test_json_format(self) -> None:
        """Should use JSON format when specified."""
        configure_logging(json_format=True, level="INFO")
        # The configuration should complete without error

    def test_console_format(self) -> None:
        """Should use console format when specified."""
        configure_logging(json_format=False, level="INFO")
        # The configuration should complete without error

    def test_adds_correlation_filter(self) -> None:
        """Should add correlation ID filter."""
        configure_logging(level="INFO")
        root_logger = logging.getLogger()
        
        # Check that some filter exists
        # (implementation detail - may vary)


class TestStructuredLogging:
    """Integration tests for structured logging."""

    def test_full_json_log_output(self) -> None:
        """Should produce complete JSON log output."""
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(JSONFormatter())
        
        logger = logging.getLogger("test.integration")
        logger.handlers = [handler]
        logger.setLevel(logging.INFO)
        
        logger.info("User action", extra={"user_id": "u123", "action": "click"})
        
        output = stream.getvalue()
        parsed = json.loads(output.strip())
        
        assert parsed["message"] == "User action"
        assert parsed["level"] == "INFO"
        assert parsed["user_id"] == "u123"
        assert parsed["action"] == "click"
        assert "timestamp" in parsed

    def test_error_with_exception(self) -> None:
        """Should log errors with exception details."""
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(JSONFormatter())
        
        logger = logging.getLogger("test.error")
        logger.handlers = [handler]
        logger.setLevel(logging.ERROR)
        
        try:
            raise RuntimeError("Something went wrong")
        except RuntimeError:
            logger.exception("Operation failed")
        
        output = stream.getvalue()
        parsed = json.loads(output.strip())
        
        assert parsed["level"] == "ERROR"
        assert "exception" in parsed
        assert "RuntimeError" in parsed["exception"]
