"""Structured logging utilities for microservices.

This module provides JSON-formatted logging with correlation ID support,
context management, and easy configuration for production environments.
"""

from __future__ import annotations

import json
import logging
import sys
import contextvars
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Generator


# Context variables for correlation ID and extra context
_correlation_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "correlation_id", default=None
)
_log_context: contextvars.ContextVar[dict[str, Any]] = contextvars.ContextVar(
    "log_context", default={}
)


def set_correlation_id(correlation_id: str) -> None:
    """Set the correlation ID for the current context.
    
    Args:
        correlation_id: The correlation ID to set.
    """
    _correlation_id.set(correlation_id)


def get_correlation_id() -> str | None:
    """Get the correlation ID for the current context.
    
    Returns:
        The current correlation ID or None if not set.
    """
    return _correlation_id.get()


def generate_correlation_id() -> str:
    """Generate a new correlation ID.
    
    Returns:
        A new UUID-based correlation ID.
    """
    return str(uuid.uuid4())


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging.
    
    Outputs log records as JSON objects with consistent fields
    for easy parsing by log aggregation systems.
    """

    def __init__(
        self,
        *,
        include_timestamp: bool = True,
        timestamp_format: str | None = None,
        extra_fields: dict[str, Any] | None = None,
    ) -> None:
        """Initialize the JSON formatter.
        
        Args:
            include_timestamp: Whether to include timestamp in output.
            timestamp_format: Custom timestamp format (ISO 8601 by default).
            extra_fields: Additional fields to include in every log entry.
        """
        super().__init__()
        self.include_timestamp = include_timestamp
        self.timestamp_format = timestamp_format
        self.extra_fields = extra_fields or {}

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record as JSON.
        
        Args:
            record: The log record to format.
            
        Returns:
            JSON-formatted log string.
        """
        # Build base log entry
        log_entry: dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add timestamp
        if self.include_timestamp:
            if self.timestamp_format:
                log_entry["timestamp"] = datetime.fromtimestamp(
                    record.created, tz=timezone.utc
                ).strftime(self.timestamp_format)
            else:
                log_entry["timestamp"] = datetime.fromtimestamp(
                    record.created, tz=timezone.utc
                ).isoformat()

        # Add correlation ID if present
        correlation_id = get_correlation_id()
        if correlation_id:
            log_entry["correlation_id"] = correlation_id

        # Add context from context var
        context = _log_context.get()
        if context:
            log_entry.update(context)

        # Add exception info
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Add extra fields from formatter config
        log_entry.update(self.extra_fields)

        # Add extra fields from record
        for key, value in record.__dict__.items():
            if key not in (
                "name", "msg", "args", "created", "filename", "funcName",
                "levelname", "levelno", "lineno", "module", "msecs",
                "pathname", "process", "processName", "relativeCreated",
                "stack_info", "exc_info", "exc_text", "thread", "threadName",
                "message", "taskName",
            ):
                log_entry[key] = value

        return json.dumps(log_entry, default=str)


class CorrelationIdFilter(logging.Filter):
    """Logging filter that adds correlation ID to log records.
    
    This filter ensures every log record has a correlation_id attribute,
    generating one if not already present in the context.
    """

    def __init__(self, *, auto_generate: bool = True) -> None:
        """Initialize the filter.
        
        Args:
            auto_generate: Whether to auto-generate correlation ID if missing.
        """
        super().__init__()
        self.auto_generate = auto_generate

    def filter(self, record: logging.LogRecord) -> bool:
        """Add correlation ID to the log record.
        
        Args:
            record: The log record to filter.
            
        Returns:
            Always True (we're adding data, not filtering).
        """
        correlation_id = get_correlation_id()
        
        if correlation_id is None and self.auto_generate:
            correlation_id = generate_correlation_id()
            set_correlation_id(correlation_id)
        
        record.correlation_id = correlation_id  # type: ignore[attr-defined]
        return True


@contextmanager
def with_context(**kwargs: Any) -> Generator[None, None, None]:
    """Context manager to add fields to log context.
    
    Args:
        **kwargs: Key-value pairs to add to log context.
        
    Yields:
        None
        
    Example:
        with with_context(user_id="123", request_id="abc"):
            logger.info("Processing request")  # Includes user_id and request_id
    """
    current_context = _log_context.get().copy()
    new_context = {**current_context, **kwargs}
    token = _log_context.set(new_context)
    try:
        yield
    finally:
        _log_context.reset(token)


# Logger cache
_loggers: dict[str, logging.Logger] = {}


def get_logger(name: str | None = None) -> logging.Logger:
    """Get a logger instance with caching.
    
    Args:
        name: Logger name. If None, returns root logger.
        
    Returns:
        Configured logger instance.
    """
    if name is None:
        return logging.getLogger()
    
    if name not in _loggers:
        _loggers[name] = logging.getLogger(name)
    
    return _loggers[name]


def configure_logging(
    *,
    level: str | int = logging.INFO,
    json_format: bool = True,
    include_correlation_id: bool = True,
    extra_fields: dict[str, Any] | None = None,
    stream: Any = None,
) -> None:
    """Configure logging for the application.
    
    Args:
        level: Logging level (e.g., "INFO", "DEBUG", logging.INFO).
        json_format: Whether to use JSON formatting.
        include_correlation_id: Whether to include correlation ID filter.
        extra_fields: Additional fields for JSON formatter.
        stream: Output stream (defaults to sys.stderr).
    """
    # Convert string level to int
    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create handler
    handler = logging.StreamHandler(stream or sys.stderr)
    handler.setLevel(level)

    # Set formatter
    if json_format:
        formatter = JSONFormatter(extra_fields=extra_fields)
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
    
    handler.setFormatter(formatter)

    # Add correlation ID filter
    if include_correlation_id:
        handler.addFilter(CorrelationIdFilter())

    root_logger.addHandler(handler)


__all__ = [
    "JSONFormatter",
    "CorrelationIdFilter",
    "set_correlation_id",
    "get_correlation_id",
    "generate_correlation_id",
    "with_context",
    "get_logger",
    "configure_logging",
]
