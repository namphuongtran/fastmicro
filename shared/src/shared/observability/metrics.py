"""Prometheus-compatible metrics utilities for microservices.

This module provides metric types (Counter, Gauge, Histogram) and
a registry for managing application metrics.
"""

from __future__ import annotations

import functools
import time
import asyncio
from contextlib import contextmanager
from dataclasses import dataclass, field
from threading import Lock
from typing import Any, Callable, Generator, ParamSpec, TypeVar


@dataclass
class LabeledMetric:
    """A metric instance with specific label values."""
    
    _values: dict[str, float] = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock)

    def _get_key(self, labels: dict[str, str]) -> str:
        """Generate a key for the label combination."""
        return ",".join(f"{k}={v}" for k, v in sorted(labels.items()))


class Counter:
    """A counter metric that can only increase.
    
    Counters are used for counting events like requests, errors, etc.
    """

    def __init__(
        self,
        name: str,
        description: str,
        labels: list[str] | None = None,
    ) -> None:
        """Initialize a counter.
        
        Args:
            name: Metric name.
            description: Metric description.
            labels: Label names for this metric.
        """
        self.name = name
        self.description = description
        self._labels = labels or []
        self._values: dict[str, float] = {}
        self._lock = Lock()

    def _get_key(self, label_values: dict[str, str]) -> str:
        """Generate a key for label values."""
        if not label_values:
            return ""
        return ",".join(f"{k}={v}" for k, v in sorted(label_values.items()))

    def inc(self, amount: float = 1.0) -> None:
        """Increment the counter.
        
        Args:
            amount: Amount to increment (must be positive).
            
        Raises:
            ValueError: If amount is negative.
        """
        if amount < 0:
            raise ValueError("Counter cannot be decremented")
        
        with self._lock:
            key = self._get_key({})
            self._values[key] = self._values.get(key, 0) + amount

    def labels(self, **label_values: str) -> "_CounterChild":
        """Get a child counter with specific label values.
        
        Args:
            **label_values: Label values.
            
        Returns:
            Child counter instance.
        """
        return _CounterChild(self, label_values)


class _CounterChild:
    """A counter instance with specific label values."""

    def __init__(self, parent: Counter, label_values: dict[str, str]) -> None:
        self._parent = parent
        self._label_values = label_values

    def inc(self, amount: float = 1.0) -> None:
        """Increment the counter."""
        if amount < 0:
            raise ValueError("Counter cannot be decremented")
        
        with self._parent._lock:
            key = self._parent._get_key(self._label_values)
            self._parent._values[key] = self._parent._values.get(key, 0) + amount


class Gauge:
    """A gauge metric that can increase or decrease.
    
    Gauges are used for values that go up and down like
    temperature, memory usage, active connections, etc.
    """

    def __init__(
        self,
        name: str,
        description: str,
        labels: list[str] | None = None,
    ) -> None:
        """Initialize a gauge.
        
        Args:
            name: Metric name.
            description: Metric description.
            labels: Label names for this metric.
        """
        self.name = name
        self.description = description
        self._labels = labels or []
        self._values: dict[str, float] = {}
        self._lock = Lock()

    def _get_key(self, label_values: dict[str, str]) -> str:
        """Generate a key for label values."""
        if not label_values:
            return ""
        return ",".join(f"{k}={v}" for k, v in sorted(label_values.items()))

    def set(self, value: float) -> None:
        """Set the gauge value.
        
        Args:
            value: The value to set.
        """
        with self._lock:
            key = self._get_key({})
            self._values[key] = value

    def inc(self, amount: float = 1.0) -> None:
        """Increment the gauge.
        
        Args:
            amount: Amount to increment.
        """
        with self._lock:
            key = self._get_key({})
            self._values[key] = self._values.get(key, 0) + amount

    def dec(self, amount: float = 1.0) -> None:
        """Decrement the gauge.
        
        Args:
            amount: Amount to decrement.
        """
        with self._lock:
            key = self._get_key({})
            self._values[key] = self._values.get(key, 0) - amount

    def labels(self, **label_values: str) -> "_GaugeChild":
        """Get a child gauge with specific label values.
        
        Args:
            **label_values: Label values.
            
        Returns:
            Child gauge instance.
        """
        return _GaugeChild(self, label_values)

    @contextmanager
    def track_inprogress(self) -> Generator[None, None, None]:
        """Context manager to track in-progress operations.
        
        Increments gauge on entry, decrements on exit.
        
        Yields:
            None
        """
        self.inc()
        try:
            yield
        finally:
            self.dec()


class _GaugeChild:
    """A gauge instance with specific label values."""

    def __init__(self, parent: Gauge, label_values: dict[str, str]) -> None:
        self._parent = parent
        self._label_values = label_values

    def set(self, value: float) -> None:
        """Set the gauge value."""
        with self._parent._lock:
            key = self._parent._get_key(self._label_values)
            self._parent._values[key] = value

    def inc(self, amount: float = 1.0) -> None:
        """Increment the gauge."""
        with self._parent._lock:
            key = self._parent._get_key(self._label_values)
            self._parent._values[key] = self._parent._values.get(key, 0) + amount

    def dec(self, amount: float = 1.0) -> None:
        """Decrement the gauge."""
        with self._parent._lock:
            key = self._parent._get_key(self._label_values)
            self._parent._values[key] = self._parent._values.get(key, 0) - amount


# Default histogram buckets
DEFAULT_BUCKETS = (
    0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0
)


class Histogram:
    """A histogram metric for measuring distributions.
    
    Histograms are used for measuring things like request
    durations or response sizes.
    """

    def __init__(
        self,
        name: str,
        description: str,
        labels: list[str] | None = None,
        buckets: tuple[float, ...] | None = None,
    ) -> None:
        """Initialize a histogram.
        
        Args:
            name: Metric name.
            description: Metric description.
            labels: Label names for this metric.
            buckets: Bucket boundaries.
        """
        self.name = name
        self.description = description
        self._labels = labels or []
        self._buckets = buckets or DEFAULT_BUCKETS
        self._observations: dict[str, list[float]] = {}
        self._lock = Lock()

    def _get_key(self, label_values: dict[str, str]) -> str:
        """Generate a key for label values."""
        if not label_values:
            return ""
        return ",".join(f"{k}={v}" for k, v in sorted(label_values.items()))

    def observe(self, value: float) -> None:
        """Observe a value.
        
        Args:
            value: The value to observe.
        """
        with self._lock:
            key = self._get_key({})
            if key not in self._observations:
                self._observations[key] = []
            self._observations[key].append(value)

    def labels(self, **label_values: str) -> "_HistogramChild":
        """Get a child histogram with specific label values.
        
        Args:
            **label_values: Label values.
            
        Returns:
            Child histogram instance.
        """
        return _HistogramChild(self, label_values)

    @contextmanager
    def time(self) -> Generator[None, None, None]:
        """Context manager to time an operation.
        
        Yields:
            None
        """
        start = time.perf_counter()
        try:
            yield
        finally:
            duration = time.perf_counter() - start
            self.observe(duration)


class _HistogramChild:
    """A histogram instance with specific label values."""

    def __init__(self, parent: Histogram, label_values: dict[str, str]) -> None:
        self._parent = parent
        self._label_values = label_values

    def observe(self, value: float) -> None:
        """Observe a value."""
        with self._parent._lock:
            key = self._parent._get_key(self._label_values)
            if key not in self._parent._observations:
                self._parent._observations[key] = []
            self._parent._observations[key].append(value)


class MetricsRegistry:
    """Registry for managing application metrics."""

    def __init__(self) -> None:
        """Initialize the registry."""
        self._metrics: dict[str, Counter | Gauge | Histogram] = {}
        self._lock = Lock()
        self._namespace: str = ""
        self._enabled: bool = True

    def counter(
        self,
        name: str,
        description: str,
        labels: list[str] | None = None,
    ) -> Counter:
        """Create or get a counter.
        
        Args:
            name: Metric name.
            description: Metric description.
            labels: Label names.
            
        Returns:
            Counter instance.
        """
        full_name = f"{self._namespace}_{name}" if self._namespace else name
        
        with self._lock:
            if full_name in self._metrics:
                return self._metrics[full_name]  # type: ignore[return-value]
            
            counter = Counter(full_name, description, labels)
            self._metrics[full_name] = counter
            return counter

    def gauge(
        self,
        name: str,
        description: str,
        labels: list[str] | None = None,
    ) -> Gauge:
        """Create or get a gauge.
        
        Args:
            name: Metric name.
            description: Metric description.
            labels: Label names.
            
        Returns:
            Gauge instance.
        """
        full_name = f"{self._namespace}_{name}" if self._namespace else name
        
        with self._lock:
            if full_name in self._metrics:
                return self._metrics[full_name]  # type: ignore[return-value]
            
            gauge = Gauge(full_name, description, labels)
            self._metrics[full_name] = gauge
            return gauge

    def histogram(
        self,
        name: str,
        description: str,
        labels: list[str] | None = None,
        buckets: tuple[float, ...] | None = None,
    ) -> Histogram:
        """Create or get a histogram.
        
        Args:
            name: Metric name.
            description: Metric description.
            labels: Label names.
            buckets: Histogram buckets.
            
        Returns:
            Histogram instance.
        """
        full_name = f"{self._namespace}_{name}" if self._namespace else name
        
        with self._lock:
            if full_name in self._metrics:
                return self._metrics[full_name]  # type: ignore[return-value]
            
            histogram = Histogram(full_name, description, labels, buckets)
            self._metrics[full_name] = histogram
            return histogram

    def list_metrics(self) -> list[str]:
        """List all registered metric names.
        
        Returns:
            List of metric names.
        """
        with self._lock:
            return list(self._metrics.keys())


# Global registry singleton
_registry: MetricsRegistry | None = None
_registry_lock = Lock()


def get_metrics_registry() -> MetricsRegistry:
    """Get the global metrics registry.
    
    Returns:
        The global metrics registry instance.
    """
    global _registry
    
    with _registry_lock:
        if _registry is None:
            _registry = MetricsRegistry()
        return _registry


def configure_metrics(
    *,
    namespace: str = "",
    enabled: bool = True,
) -> None:
    """Configure metrics globally.
    
    Args:
        namespace: Prefix for all metric names.
        enabled: Whether metrics are enabled.
    """
    registry = get_metrics_registry()
    registry._namespace = namespace
    registry._enabled = enabled


P = ParamSpec("P")
T = TypeVar("T")


def timed(
    name: str,
    *,
    labels: dict[str, str] | None = None,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator to time function execution.
    
    Args:
        name: Metric name for the histogram.
        labels: Additional labels.
        
    Returns:
        Decorated function.
        
    Example:
        @timed("request_duration")
        def handle_request():
            ...
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        registry = get_metrics_registry()
        histogram = registry.histogram(
            name=f"{name}_seconds",
            description=f"Duration of {name} in seconds",
        )
        
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
                start = time.perf_counter()
                try:
                    return await func(*args, **kwargs)
                finally:
                    duration = time.perf_counter() - start
                    histogram.observe(duration)
            return async_wrapper  # type: ignore[return-value]
        else:
            @functools.wraps(func)
            def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
                start = time.perf_counter()
                try:
                    return func(*args, **kwargs)
                finally:
                    duration = time.perf_counter() - start
                    histogram.observe(duration)
            return sync_wrapper  # type: ignore[return-value]
    
    return decorator


__all__ = [
    "Counter",
    "Gauge",
    "Histogram",
    "MetricsRegistry",
    "get_metrics_registry",
    "configure_metrics",
    "timed",
]
