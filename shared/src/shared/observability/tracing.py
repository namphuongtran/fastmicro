"""Distributed tracing utilities for microservices.

This module provides OpenTelemetry-compatible tracing utilities including
span creation, context propagation, and the @traced decorator.
"""

from __future__ import annotations

import asyncio
import contextvars
import functools
import time
import uuid
from collections.abc import Callable, Generator
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, ParamSpec, TypeVar


class SpanKind(Enum):
    """Span kind indicating the role in a trace."""

    INTERNAL = "internal"
    SERVER = "server"
    CLIENT = "client"
    PRODUCER = "producer"
    CONSUMER = "consumer"


@dataclass
class TracingConfig:
    """Configuration for tracing."""

    service_name: str = "unknown-service"
    enabled: bool = True
    sample_rate: float = 1.0
    exporter_endpoint: str | None = None
    extra_attributes: dict[str, Any] = field(default_factory=dict)


@dataclass
class Span:
    """Represents a tracing span."""

    name: str
    trace_id: str
    span_id: str
    parent_span_id: str | None = None
    kind: SpanKind = SpanKind.INTERNAL
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None
    attributes: dict[str, Any] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)
    status: str = "OK"
    exception: BaseException | None = None

    def set_attribute(self, key: str, value: Any) -> None:
        """Set an attribute on the span.

        Args:
            key: Attribute key.
            value: Attribute value.
        """
        self.attributes[key] = value

    def add_event(self, name: str, attributes: dict[str, Any] | None = None) -> None:
        """Add an event to the span.

        Args:
            name: Event name.
            attributes: Event attributes.
        """
        self.events.append(
            {
                "name": name,
                "timestamp": time.time(),
                "attributes": attributes or {},
            }
        )

    def record_exception(self, exception: BaseException) -> None:
        """Record an exception on the span.

        Args:
            exception: The exception to record.
        """
        self.exception = exception
        self.status = "ERROR"
        self.add_event(
            "exception",
            {
                "exception.type": type(exception).__name__,
                "exception.message": str(exception),
            },
        )

    def end(self) -> None:
        """End the span."""
        self.end_time = time.time()


# Context variables for tracing
_current_span: contextvars.ContextVar[Span | None] = contextvars.ContextVar(
    "current_span", default=None
)
_trace_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("trace_id", default=None)

# Global tracing configuration
_tracing_config: TracingConfig = TracingConfig()


def configure_tracing(config: TracingConfig) -> None:
    """Configure tracing globally.

    Args:
        config: Tracing configuration.
    """
    global _tracing_config
    _tracing_config = config


def get_current_span() -> Span | None:
    """Get the current span from context.

    Returns:
        The current span or None if no span is active.
    """
    return _current_span.get()


def get_trace_id() -> str | None:
    """Get the current trace ID from context.

    Returns:
        The current trace ID or None if no trace is active.
    """
    return _trace_id.get()


def _generate_id() -> str:
    """Generate a unique ID for spans/traces."""
    return uuid.uuid4().hex[:16]


@contextmanager
def create_span(
    name: str,
    *,
    kind: SpanKind = SpanKind.INTERNAL,
    attributes: dict[str, Any] | None = None,
) -> Generator[Span, None, None]:
    """Create a new span as a context manager.

    Args:
        name: Span name.
        kind: Span kind.
        attributes: Initial span attributes.

    Yields:
        The created span.

    Example:
        with create_span("process_order", kind=SpanKind.SERVER) as span:
            span.set_attribute("order_id", "12345")
            # Do work
    """
    if not _tracing_config.enabled:
        # Return a no-op span when tracing is disabled
        yield Span(name=name, trace_id="", span_id="")
        return

    # Get or create trace ID
    trace_id = _trace_id.get()
    if trace_id is None:
        trace_id = _generate_id()
        _trace_id.set(trace_id)

    # Get parent span
    parent_span = _current_span.get()
    parent_span_id = parent_span.span_id if parent_span else None

    # Create new span
    span = Span(
        name=name,
        trace_id=trace_id,
        span_id=_generate_id(),
        parent_span_id=parent_span_id,
        kind=kind,
        attributes=attributes or {},
    )

    # Set as current span
    token = _current_span.set(span)

    try:
        yield span
    except BaseException as e:
        span.record_exception(e)
        raise
    finally:
        span.end()
        _current_span.reset(token)


def inject_context(carrier: dict[str, str]) -> None:
    """Inject trace context into a carrier (e.g., HTTP headers).

    Args:
        carrier: Dictionary to inject context into.
    """
    trace_id = get_trace_id()
    span = get_current_span()

    if trace_id:
        carrier["traceparent"] = f"00-{trace_id}-{span.span_id if span else '0' * 16}-01"


def extract_context(carrier: dict[str, str]) -> dict[str, str | None]:
    """Extract trace context from a carrier (e.g., HTTP headers).

    Args:
        carrier: Dictionary containing trace context.

    Returns:
        Extracted context with trace_id and parent_span_id.
    """
    traceparent = carrier.get("traceparent", "")

    if traceparent:
        parts = traceparent.split("-")
        if len(parts) >= 3:
            return {
                "trace_id": parts[1],
                "parent_span_id": parts[2],
            }

    return {"trace_id": None, "parent_span_id": None}


P = ParamSpec("P")
T = TypeVar("T")


def traced(
    name: str | None = None,
    *,
    kind: SpanKind = SpanKind.INTERNAL,
    attributes: dict[str, Any] | None = None,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator to trace a function.

    Args:
        name: Span name (defaults to function name).
        kind: Span kind.
        attributes: Initial span attributes.

    Returns:
        Decorated function.

    Example:
        @traced("process_payment", kind=SpanKind.CLIENT)
        async def process_payment(order_id: str) -> bool:
            ...
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        span_name = name or func.__name__

        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
                with create_span(span_name, kind=kind, attributes=attributes):
                    try:
                        return await func(*args, **kwargs)
                    except BaseException:
                        raise

            return async_wrapper  # type: ignore[return-value]
        else:

            @functools.wraps(func)
            def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
                with create_span(span_name, kind=kind, attributes=attributes):
                    try:
                        return func(*args, **kwargs)
                    except BaseException:
                        raise

            return sync_wrapper  # type: ignore[return-value]

    return decorator


__all__ = [
    "Span",
    "SpanKind",
    "TracingConfig",
    "configure_tracing",
    "create_span",
    "extract_context",
    "get_current_span",
    "get_trace_id",
    "inject_context",
    "traced",
]
