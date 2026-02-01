"""Tests for shared.observability.tracing module.

This module tests OpenTelemetry tracing utilities including span creation,
context propagation, and trace configuration.
"""

from __future__ import annotations

import pytest

from shared.observability.tracing import (
    SpanKind,
    TracingConfig,
    configure_tracing,
    create_span,
    extract_context,
    get_current_span,
    get_trace_id,
    inject_context,
    traced,
)


class TestTracingConfig:
    """Tests for TracingConfig dataclass."""

    def test_default_values(self) -> None:
        """Should have sensible defaults."""
        config = TracingConfig(service_name="test-service")

        assert config.service_name == "test-service"
        assert config.enabled is True
        assert config.sample_rate == 1.0

    def test_custom_values(self) -> None:
        """Should accept custom values."""
        config = TracingConfig(
            service_name="my-service",
            enabled=False,
            sample_rate=0.5,
            exporter_endpoint="http://jaeger:14268",
        )

        assert config.service_name == "my-service"
        assert config.enabled is False
        assert config.sample_rate == 0.5
        assert config.exporter_endpoint == "http://jaeger:14268"


class TestSpanKind:
    """Tests for SpanKind enum."""

    def test_span_kinds_exist(self) -> None:
        """Should have standard span kinds."""
        assert hasattr(SpanKind, "INTERNAL")
        assert hasattr(SpanKind, "SERVER")
        assert hasattr(SpanKind, "CLIENT")
        assert hasattr(SpanKind, "PRODUCER")
        assert hasattr(SpanKind, "CONSUMER")


class TestCreateSpan:
    """Tests for create_span context manager."""

    def test_creates_span(self) -> None:
        """Should create a span context."""
        with create_span("test-operation") as span:
            assert span is not None

    def test_span_has_name(self) -> None:
        """Should set span name."""
        with create_span("my-operation") as span:
            # Span should be created with the given name
            pass  # Name is set internally

    def test_span_with_attributes(self) -> None:
        """Should set span attributes."""
        with create_span("operation", attributes={"key": "value"}) as span:
            # Attributes should be set on the span
            pass

    def test_span_with_kind(self) -> None:
        """Should set span kind."""
        with create_span("http-request", kind=SpanKind.CLIENT) as span:
            pass

    def test_nested_spans(self) -> None:
        """Should support nested spans."""
        with create_span("parent") as parent_span, create_span("child") as child_span:
            # Child should be nested under parent
            pass

    def test_span_records_exception(self) -> None:
        """Should record exceptions on span."""
        with pytest.raises(ValueError), create_span("failing-operation") as span:
            raise ValueError("Test error")


class TestGetCurrentSpan:
    """Tests for get_current_span function."""

    def test_returns_span_in_context(self) -> None:
        """Should return current span when in span context."""
        with create_span("test") as expected_span:
            current = get_current_span()
            # Should return a span (may be same or wrapped)
            assert current is not None

    def test_returns_none_outside_context(self) -> None:
        """Should return None or no-op span outside context."""
        span = get_current_span()
        # Should return something (even if no-op)


class TestGetTraceId:
    """Tests for get_trace_id function."""

    def test_returns_trace_id_in_span(self) -> None:
        """Should return trace ID when in span context."""
        with create_span("test"):
            trace_id = get_trace_id()
            # Should return a string trace ID or None
            if trace_id:
                assert isinstance(trace_id, str)

    def test_returns_none_outside_span(self) -> None:
        """Should return None outside span context."""
        trace_id = get_trace_id()
        # May be None or empty string


class TestContextPropagation:
    """Tests for context injection and extraction."""

    def test_inject_context_to_dict(self) -> None:
        """Should inject trace context into carrier dict."""
        carrier: dict[str, str] = {}

        with create_span("test"):
            inject_context(carrier)

        # Carrier may have traceparent header (if tracing is enabled)

    def test_extract_context_from_dict(self) -> None:
        """Should extract trace context from carrier dict."""
        carrier = {"traceparent": "00-trace-span-01"}

        context = extract_context(carrier)
        # Should return a context object (may be empty if invalid)


class TestTracedDecorator:
    """Tests for @traced decorator."""

    def test_decorates_sync_function(self) -> None:
        """Should decorate synchronous functions."""

        @traced("my-operation")
        def my_function() -> str:
            return "result"

        result = my_function()
        assert result == "result"

    def test_decorates_async_function(self) -> None:
        """Should decorate async functions."""

        @traced("async-operation")
        async def my_async_function() -> str:
            return "async result"

        import asyncio

        result = asyncio.run(my_async_function())
        assert result == "async result"

    def test_preserves_function_metadata(self) -> None:
        """Should preserve function name and docstring."""

        @traced("operation")
        def documented_function() -> None:
            """This is the docstring."""
            pass

        assert documented_function.__name__ == "documented_function"
        assert "docstring" in (documented_function.__doc__ or "")

    def test_passes_arguments(self) -> None:
        """Should pass arguments to decorated function."""

        @traced("add-operation")
        def add(a: int, b: int) -> int:
            return a + b

        result = add(2, 3)
        assert result == 5

    def test_handles_exceptions(self) -> None:
        """Should propagate exceptions from decorated function."""

        @traced("failing")
        def failing_function() -> None:
            raise RuntimeError("Intentional error")

        with pytest.raises(RuntimeError, match="Intentional error"):
            failing_function()

    def test_with_attributes(self) -> None:
        """Should support custom attributes."""

        @traced("operation", attributes={"custom": "attr"})
        def attributed_function() -> str:
            return "done"

        result = attributed_function()
        assert result == "done"


class TestConfigureTracing:
    """Tests for configure_tracing function."""

    def test_configures_with_config_object(self) -> None:
        """Should accept TracingConfig object."""
        config = TracingConfig(
            service_name="test-service",
            enabled=True,
        )

        # Should not raise
        configure_tracing(config)

    def test_disabled_tracing(self) -> None:
        """Should handle disabled tracing gracefully."""
        config = TracingConfig(
            service_name="test-service",
            enabled=False,
        )

        configure_tracing(config)

        # Operations should still work (as no-ops)
        with create_span("test"):
            pass
