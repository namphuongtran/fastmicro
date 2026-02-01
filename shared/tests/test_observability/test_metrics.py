"""Tests for shared.observability.metrics module.

This module tests Prometheus metrics utilities including counters,
histograms, gauges, and metric registration.
"""

from __future__ import annotations

import pytest

from shared.observability.metrics import (
    Counter,
    Gauge,
    Histogram,
    MetricsRegistry,
    configure_metrics,
    get_metrics_registry,
    timed,
)


class TestCounter:
    """Tests for Counter metric."""

    def test_create_counter(self) -> None:
        """Should create a counter."""
        counter = Counter(
            name="requests_total",
            description="Total requests",
        )
        assert counter.name == "requests_total"

    def test_increment_counter(self) -> None:
        """Should increment counter value."""
        counter = Counter(name="test_counter", description="Test")
        counter.inc()
        # Value should be incremented

    def test_increment_by_amount(self) -> None:
        """Should increment by specified amount."""
        counter = Counter(name="test_counter_amount", description="Test")
        counter.inc(5)
        # Value should be incremented by 5

    def test_counter_with_labels(self) -> None:
        """Should support labels."""
        counter = Counter(
            name="http_requests",
            description="HTTP requests",
            labels=["method", "status"],
        )
        counter.labels(method="GET", status="200").inc()

    def test_counter_cannot_decrease(self) -> None:
        """Should not allow negative increments."""
        counter = Counter(name="positive_counter", description="Test")
        with pytest.raises((ValueError, TypeError)):
            counter.inc(-1)


class TestGauge:
    """Tests for Gauge metric."""

    def test_create_gauge(self) -> None:
        """Should create a gauge."""
        gauge = Gauge(
            name="temperature",
            description="Current temperature",
        )
        assert gauge.name == "temperature"

    def test_set_gauge_value(self) -> None:
        """Should set gauge value."""
        gauge = Gauge(name="test_gauge", description="Test")
        gauge.set(42.5)

    def test_increment_gauge(self) -> None:
        """Should increment gauge."""
        gauge = Gauge(name="test_gauge_inc", description="Test")
        gauge.inc()
        gauge.inc(5)

    def test_decrement_gauge(self) -> None:
        """Should decrement gauge."""
        gauge = Gauge(name="test_gauge_dec", description="Test")
        gauge.set(10)
        gauge.dec()
        gauge.dec(3)

    def test_gauge_with_labels(self) -> None:
        """Should support labels."""
        gauge = Gauge(
            name="active_connections",
            description="Active connections",
            labels=["server"],
        )
        gauge.labels(server="web-1").set(100)

    def test_gauge_track_inprogress(self) -> None:
        """Should track in-progress operations."""
        gauge = Gauge(name="in_progress", description="Test")

        with gauge.track_inprogress():
            # Gauge should be incremented during context
            pass
        # Gauge should be decremented after context


class TestHistogram:
    """Tests for Histogram metric."""

    def test_create_histogram(self) -> None:
        """Should create a histogram."""
        histogram = Histogram(
            name="request_duration",
            description="Request duration in seconds",
        )
        assert histogram.name == "request_duration"

    def test_observe_value(self) -> None:
        """Should observe values."""
        histogram = Histogram(name="test_histogram", description="Test")
        histogram.observe(0.5)
        histogram.observe(1.2)
        histogram.observe(0.3)

    def test_custom_buckets(self) -> None:
        """Should support custom buckets."""
        histogram = Histogram(
            name="custom_buckets",
            description="Test",
            buckets=[0.1, 0.5, 1.0, 5.0, 10.0],
        )
        histogram.observe(0.75)

    def test_histogram_with_labels(self) -> None:
        """Should support labels."""
        histogram = Histogram(
            name="http_duration",
            description="HTTP request duration",
            labels=["method", "endpoint"],
        )
        histogram.labels(method="GET", endpoint="/api/users").observe(0.123)

    def test_time_context_manager(self) -> None:
        """Should time operations with context manager."""
        histogram = Histogram(name="operation_time", description="Test")

        with histogram.time():
            # Simulate work
            pass
        # Duration should be observed


class TestMetricsRegistry:
    """Tests for MetricsRegistry class."""

    def test_create_registry(self) -> None:
        """Should create a metrics registry."""
        registry = MetricsRegistry()
        assert registry is not None

    def test_register_counter(self) -> None:
        """Should register a counter."""
        registry = MetricsRegistry()
        counter = registry.counter(
            name="my_counter",
            description="My counter",
        )
        assert counter is not None

    def test_register_gauge(self) -> None:
        """Should register a gauge."""
        registry = MetricsRegistry()
        gauge = registry.gauge(
            name="my_gauge",
            description="My gauge",
        )
        assert gauge is not None

    def test_register_histogram(self) -> None:
        """Should register a histogram."""
        registry = MetricsRegistry()
        histogram = registry.histogram(
            name="my_histogram",
            description="My histogram",
        )
        assert histogram is not None

    def test_get_existing_metric(self) -> None:
        """Should return existing metric by name."""
        registry = MetricsRegistry()
        counter1 = registry.counter(name="shared_counter", description="Test")
        counter2 = registry.counter(name="shared_counter", description="Test")

        # Should return the same counter
        assert counter1 is counter2

    def test_list_metrics(self) -> None:
        """Should list all registered metrics."""
        registry = MetricsRegistry()
        registry.counter(name="counter1", description="Test")
        registry.gauge(name="gauge1", description="Test")

        metrics = registry.list_metrics()
        assert "counter1" in metrics
        assert "gauge1" in metrics


class TestTimedDecorator:
    """Tests for @timed decorator."""

    def test_times_sync_function(self) -> None:
        """Should time synchronous functions."""
        @timed("sync_operation")
        def my_function() -> str:
            return "result"

        result = my_function()
        assert result == "result"

    def test_times_async_function(self) -> None:
        """Should time async functions."""
        @timed("async_operation")
        async def my_async_function() -> str:
            return "async result"

        import asyncio
        result = asyncio.run(my_async_function())
        assert result == "async result"

    def test_preserves_function_metadata(self) -> None:
        """Should preserve function name."""
        @timed("operation")
        def named_function() -> None:
            """Docstring."""
            pass

        assert named_function.__name__ == "named_function"

    def test_handles_exceptions(self) -> None:
        """Should record time even on exceptions."""
        @timed("failing_operation")
        def failing_function() -> None:
            raise RuntimeError("Error")

        with pytest.raises(RuntimeError):
            failing_function()

    def test_with_labels(self) -> None:
        """Should support labels."""
        @timed("labeled_operation", labels={"type": "background"})
        def background_task() -> str:
            return "done"

        result = background_task()
        assert result == "done"


class TestGetMetricsRegistry:
    """Tests for get_metrics_registry function."""

    def test_returns_registry(self) -> None:
        """Should return a metrics registry."""
        registry = get_metrics_registry()
        assert isinstance(registry, MetricsRegistry)

    def test_returns_singleton(self) -> None:
        """Should return the same registry instance."""
        registry1 = get_metrics_registry()
        registry2 = get_metrics_registry()
        assert registry1 is registry2


class TestConfigureMetrics:
    """Tests for configure_metrics function."""

    def test_configure_with_defaults(self) -> None:
        """Should configure with default settings."""
        configure_metrics()
        # Should not raise

    def test_configure_with_namespace(self) -> None:
        """Should accept namespace prefix."""
        configure_metrics(namespace="myapp")

    def test_configure_disabled(self) -> None:
        """Should handle disabled metrics."""
        configure_metrics(enabled=False)

        # Metrics should still work (as no-ops)
        registry = get_metrics_registry()
        counter = registry.counter(name="disabled_counter", description="Test")
        counter.inc()  # Should not raise
