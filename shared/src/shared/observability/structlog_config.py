"""Structured logging configuration using structlog.

This module provides a standardized structlog configuration for all microservices.
It supports:
- JSON output in production (for log aggregation systems)
- Colored console output in development
- Correlation ID propagation via context variables
- OpenTelemetry trace ID integration
- Service-level context binding

Usage:
    from shared.observability import configure_structlog, get_structlog_logger, LoggingConfig
    
    configure_structlog(LoggingConfig(
        service_name="my-service",
        environment="production",
    ))
    
    logger = get_structlog_logger(__name__)
    logger.info("Application started", port=8000)

For FastAPI applications, use the lifespan pattern:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        configure_structlog(LoggingConfig(
            service_name=settings.app_name,
            environment=settings.environment,
        ))
        yield
"""

from __future__ import annotations

import logging
import sys
from contextvars import ContextVar
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

import structlog
from structlog.types import EventDict, Processor, WrappedLogger

# =============================================================================
# Context Variables for Request Context
# =============================================================================

_correlation_id_ctx: ContextVar[str | None] = ContextVar("correlation_id", default=None)
_service_name_ctx: ContextVar[str | None] = ContextVar("service_name", default=None)


def set_correlation_id(correlation_id: str) -> None:
    """Set the correlation ID for the current context.
    
    Args:
        correlation_id: The correlation ID to set.
    """
    _correlation_id_ctx.set(correlation_id)


def get_correlation_id() -> str | None:
    """Get the correlation ID for the current context.
    
    Returns:
        The current correlation ID or None if not set.
    """
    return _correlation_id_ctx.get()


def generate_correlation_id() -> str:
    """Generate a new correlation ID.
    
    Returns:
        A new UUID-based correlation ID.
    """
    return str(uuid4())


def clear_correlation_id() -> None:
    """Clear the correlation ID for the current context."""
    _correlation_id_ctx.set(None)


# =============================================================================
# Configuration
# =============================================================================

class Environment(str, Enum):
    """Application environment."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


@dataclass
class LoggingConfig:
    """Configuration for structured logging.
    
    Attributes:
        service_name: Name of the service (added to all log entries).
        environment: Environment name (development, staging, production, testing).
        log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        json_logs: Force JSON output. If None, auto-detects based on environment.
        add_caller_info: Include file, function, and line number in logs.
        add_timestamp: Include ISO 8601 timestamp in logs.
        utc_timestamps: Use UTC for timestamps (recommended for distributed systems).
        extra_processors: Additional custom processors to include.
    """
    service_name: str
    environment: str = "development"
    log_level: str = "INFO"
    json_logs: bool | None = None
    add_caller_info: bool = True
    add_timestamp: bool = True
    utc_timestamps: bool = True
    extra_processors: list[Processor] = field(default_factory=list)

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment.lower() in ("development", "dev", "local")

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() in ("production", "prod")

    @property
    def is_testing(self) -> bool:
        """Check if running in testing environment."""
        return self.environment.lower() in ("testing", "test")

    @property
    def should_use_json(self) -> bool:
        """Determine if JSON output should be used."""
        if self.json_logs is not None:
            return self.json_logs
        # Auto-detect: use JSON in production/staging, console in dev/test
        return not (self.is_development or self.is_testing)


# =============================================================================
# Custom Processors
# =============================================================================

def add_service_context(
    logger: WrappedLogger,
    method_name: str,
    event_dict: EventDict,
) -> EventDict:
    """Add service context to log events.
    
    Adds:
        - service: Service name from context
        - correlation_id: Correlation ID from context (if set)
    """
    # Add service name
    service_name = _service_name_ctx.get()
    if service_name:
        event_dict["service"] = service_name

    # Add correlation ID
    correlation_id = _correlation_id_ctx.get()
    if correlation_id:
        event_dict["correlation_id"] = correlation_id

    return event_dict


def add_opentelemetry_context(
    logger: WrappedLogger,
    method_name: str,
    event_dict: EventDict,
) -> EventDict:
    """Add OpenTelemetry trace context to log events.
    
    Adds trace_id and span_id if OpenTelemetry is configured and
    there's an active span.
    """
    try:
        from opentelemetry import trace

        span = trace.get_current_span()
        if span and span.is_recording():
            ctx = span.get_span_context()
            if ctx.is_valid:
                # Format as hex strings (standard for trace IDs)
                event_dict["trace_id"] = format(ctx.trace_id, "032x")
                event_dict["span_id"] = format(ctx.span_id, "016x")
    except ImportError:
        # OpenTelemetry not installed - skip silently
        pass
    except Exception:
        # Any other error - don't break logging
        pass

    return event_dict


def drop_color_message_key(
    logger: WrappedLogger,
    method_name: str,
    event_dict: EventDict,
) -> EventDict:
    """Drop the color_message key from event dict.
    
    This key is added by uvicorn/starlette and is not needed in JSON output.
    """
    event_dict.pop("color_message", None)
    return event_dict


# =============================================================================
# Configuration Functions
# =============================================================================

_configured: bool = False


def configure_structlog(config: LoggingConfig) -> None:
    """Configure structlog for the application.
    
    This should be called once at application startup, before any logging.
    
    Args:
        config: Logging configuration.
        
    Example:
        configure_structlog(LoggingConfig(
            service_name="my-service",
            environment="production",
            log_level="INFO",
        ))
    """
    global _configured

    # Set service name in context
    _service_name_ctx.set(config.service_name)

    # Build processor chain
    processors: list[Processor] = [
        # Merge context variables first
        structlog.contextvars.merge_contextvars,
        # Add custom context (service, correlation_id)
        add_service_context,
        # Add OpenTelemetry trace IDs
        add_opentelemetry_context,
        # Add log level
        structlog.processors.add_log_level,
    ]

    # Add timestamp
    if config.add_timestamp:
        processors.append(
            structlog.processors.TimeStamper(fmt="iso", utc=config.utc_timestamps)
        )

    # Add caller info (file, function, line)
    if config.add_caller_info and not config.is_production:
        processors.append(
            structlog.processors.CallsiteParameterAdder(
                parameters=[
                    structlog.processors.CallsiteParameter.FILENAME,
                    structlog.processors.CallsiteParameter.FUNC_NAME,
                    structlog.processors.CallsiteParameter.LINENO,
                ]
            )
        )

    # Add custom processors
    processors.extend(config.extra_processors)

    # Handle exceptions
    processors.append(structlog.processors.format_exc_info)

    # Drop uvicorn color_message key
    processors.append(drop_color_message_key)

    # Choose renderer based on environment
    if config.should_use_json:
        # Production: JSON output
        try:
            import orjson
            processors.append(
                structlog.processors.JSONRenderer(serializer=orjson.dumps)
            )
            logger_factory = structlog.BytesLoggerFactory()
        except ImportError:
            processors.append(structlog.processors.JSONRenderer())
            logger_factory = structlog.PrintLoggerFactory()
    else:
        # Development: Colored console output
        processors.append(
            structlog.dev.ConsoleRenderer(
                colors=True,
                exception_formatter=structlog.dev.plain_traceback,
            )
        )
        logger_factory = structlog.PrintLoggerFactory()

    # Get numeric log level
    numeric_level = getattr(logging, config.log_level.upper(), logging.INFO)

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        logger_factory=logger_factory,
        cache_logger_on_first_use=True,
    )

    # Also configure stdlib logging for third-party libraries
    _configure_stdlib_logging(config)

    _configured = True


def _configure_stdlib_logging(config: LoggingConfig) -> None:
    """Configure Python stdlib logging to work with structlog.
    
    This ensures logs from third-party libraries using stdlib logging
    are formatted consistently.
    """
    numeric_level = getattr(logging, config.log_level.upper(), logging.INFO)

    # Create a handler with structlog-compatible formatting
    if config.should_use_json:
        # JSON format for production
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(
            structlog.stdlib.ProcessorFormatter(
                processor=structlog.processors.JSONRenderer(),
                foreign_pre_chain=[
                    structlog.contextvars.merge_contextvars,
                    structlog.processors.add_log_level,
                    structlog.processors.TimeStamper(fmt="iso", utc=config.utc_timestamps),
                ],
            )
        )
    else:
        # Console format for development
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(
            structlog.stdlib.ProcessorFormatter(
                processor=structlog.dev.ConsoleRenderer(colors=True),
                foreign_pre_chain=[
                    structlog.contextvars.merge_contextvars,
                    structlog.processors.add_log_level,
                    structlog.processors.TimeStamper(fmt="iso", utc=config.utc_timestamps),
                ],
            )
        )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(numeric_level)

    # Reduce noise from common libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def configure_structlog_for_testing() -> None:
    """Configure structlog for testing.
    
    Uses ReturnLoggerFactory to allow capturing logs in tests.
    
    Example:
        def test_something(caplog):
            configure_structlog_for_testing()
            logger = get_structlog_logger("test")
            logger.info("test message")
            # Check logs...
    """
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            add_service_context,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.format_exc_info,
            structlog.dev.ConsoleRenderer(colors=False),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.DEBUG),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,  # Allow reconfiguration in tests
    )


def reset_structlog_configuration() -> None:
    """Reset structlog configuration.
    
    Useful for tests that need to reconfigure logging.
    """
    global _configured
    structlog.reset_defaults()
    _configured = False


# =============================================================================
# Logger Factory
# =============================================================================

def get_structlog_logger(
    name: str | None = None,
    **initial_context: Any,
) -> structlog.BoundLogger:
    """Get a structlog logger with optional initial context.
    
    Args:
        name: Logger name (typically __name__).
        **initial_context: Initial context to bind to the logger.
        
    Returns:
        A bound structlog logger.
        
    Example:
        logger = get_structlog_logger(__name__)
        logger.info("Starting up")
        
        # With initial context
        logger = get_structlog_logger(__name__, component="auth")
        logger.info("Processing request")  # Includes component="auth"
    """
    logger = structlog.get_logger(name)

    if initial_context:
        logger = logger.bind(**initial_context)

    return logger


def bind_contextvars(**context: Any) -> None:
    """Bind context variables that will be included in all subsequent logs.
    
    This is useful in middleware to add request-scoped context.
    
    Args:
        **context: Key-value pairs to bind to context.
        
    Example:
        # In middleware
        bind_contextvars(
            method=request.method,
            path=request.url.path,
            user_id=current_user.id,
        )
    """
    structlog.contextvars.bind_contextvars(**context)


def clear_contextvars() -> None:
    """Clear all bound context variables.
    
    Call this at the end of request handling to clean up.
    """
    structlog.contextvars.clear_contextvars()


def unbind_contextvars(*keys: str) -> None:
    """Remove specific context variables.
    
    Args:
        *keys: Keys to remove from context.
    """
    structlog.contextvars.unbind_contextvars(*keys)


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Configuration
    "Environment",
    "LoggingConfig",
    "configure_structlog",
    "configure_structlog_for_testing",
    "reset_structlog_configuration",
    # Context management
    "set_correlation_id",
    "get_correlation_id",
    "generate_correlation_id",
    "clear_correlation_id",
    "bind_contextvars",
    "clear_contextvars",
    "unbind_contextvars",
    # Logger
    "get_structlog_logger",
    # Processors (for advanced usage)
    "add_service_context",
    "add_opentelemetry_context",
    "drop_color_message_key",
]
