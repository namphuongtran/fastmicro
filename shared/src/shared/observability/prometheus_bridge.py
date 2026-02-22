"""Prometheus metrics bridge for production-grade metrics export.

This module bridges the custom in-memory metrics (Counter, Gauge, Histogram)
to the real ``prometheus_client`` library so that metrics can be scraped by
Prometheus in production.  For tests and local development the default
in-memory backend remains zero-dependency.

Two backends are provided:

* **InMemoryMetricsBackend** (default) – lightweight, no external deps.
* **PrometheusMetricsBackend** – delegates to ``prometheus_client``.

Usage::

    from shared.observability.prometheus_bridge import (
        MetricsBackend,
        PrometheusMetricsBackend,
        InMemoryMetricsBackend,
        create_metrics_backend,
    )

    # Auto-detect (uses prometheus_client if installed)
    backend = create_metrics_backend(namespace="myservice")

    counter = backend.counter("requests_total", "Total requests", ["method"])
    counter.labels(method="GET").inc()

    # ASGI app for /metrics endpoint
    from prometheus_client import make_asgi_app
    metrics_app = make_asgi_app()
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from collections.abc import Generator
from contextlib import contextmanager
from threading import Lock
from typing import Protocol, runtime_checkable


# ---------------------------------------------------------------------------
# Abstract metric types (backend-agnostic)
# ---------------------------------------------------------------------------


@runtime_checkable
class CounterLike(Protocol):
    """Protocol for a counter metric."""

    def inc(self, amount: float = 1.0) -> None: ...


@runtime_checkable
class LabeledCounterLike(Protocol):
    """Protocol for a labeled counter metric."""

    def labels(self, **label_values: str) -> CounterLike: ...
    def inc(self, amount: float = 1.0) -> None: ...


@runtime_checkable
class GaugeLike(Protocol):
    """Protocol for a gauge metric."""

    def set(self, value: float) -> None: ...
    def inc(self, amount: float = 1.0) -> None: ...
    def dec(self, amount: float = 1.0) -> None: ...


@runtime_checkable
class LabeledGaugeLike(Protocol):
    """Protocol for a labeled gauge metric."""

    def labels(self, **label_values: str) -> GaugeLike: ...
    def set(self, value: float) -> None: ...
    def inc(self, amount: float = 1.0) -> None: ...
    def dec(self, amount: float = 1.0) -> None: ...


@runtime_checkable
class HistogramLike(Protocol):
    """Protocol for a histogram metric."""

    def observe(self, value: float) -> None: ...


@runtime_checkable
class LabeledHistogramLike(Protocol):
    """Protocol for a labeled histogram metric."""

    def labels(self, **label_values: str) -> HistogramLike: ...
    def observe(self, value: float) -> None: ...


# ---------------------------------------------------------------------------
# Abstract backend
# ---------------------------------------------------------------------------


class MetricsBackend(ABC):
    """Abstract metrics backend.

    Implementations provide factory methods for creating
    counter / gauge / histogram metrics.
    """

    @abstractmethod
    def counter(
        self,
        name: str,
        description: str,
        labels: list[str] | None = None,
    ) -> LabeledCounterLike:
        """Create or retrieve a counter metric."""

    @abstractmethod
    def gauge(
        self,
        name: str,
        description: str,
        labels: list[str] | None = None,
    ) -> LabeledGaugeLike:
        """Create or retrieve a gauge metric."""

    @abstractmethod
    def histogram(
        self,
        name: str,
        description: str,
        labels: list[str] | None = None,
        buckets: tuple[float, ...] | None = None,
    ) -> LabeledHistogramLike:
        """Create or retrieve a histogram metric."""

    @abstractmethod
    def list_metrics(self) -> list[str]:
        """Return all registered metric names."""


# ---------------------------------------------------------------------------
# In-memory backend (reuses existing custom metrics)
# ---------------------------------------------------------------------------


class InMemoryMetricsBackend(MetricsBackend):
    """In-memory metrics backend using custom implementations.

    This is the zero-dependency default, suitable for testing and
    environments where Prometheus scraping is not available.
    """

    def __init__(self, *, namespace: str = "") -> None:
        from shared.observability.metrics import MetricsRegistry

        self._registry = MetricsRegistry()
        if namespace:
            self._registry._namespace = namespace

    @property
    def registry(self) -> object:
        """Underlying :class:`MetricsRegistry` instance."""
        return self._registry

    def counter(
        self,
        name: str,
        description: str,
        labels: list[str] | None = None,
    ) -> LabeledCounterLike:
        return self._registry.counter(name, description, labels)  # type: ignore[return-value]

    def gauge(
        self,
        name: str,
        description: str,
        labels: list[str] | None = None,
    ) -> LabeledGaugeLike:
        return self._registry.gauge(name, description, labels)  # type: ignore[return-value]

    def histogram(
        self,
        name: str,
        description: str,
        labels: list[str] | None = None,
        buckets: tuple[float, ...] | None = None,
    ) -> LabeledHistogramLike:
        return self._registry.histogram(name, description, labels, buckets)  # type: ignore[return-value]

    def list_metrics(self) -> list[str]:
        return self._registry.list_metrics()


# ---------------------------------------------------------------------------
# Real Prometheus backend
# ---------------------------------------------------------------------------

# Default buckets matching prometheus_client defaults
_DEFAULT_PROMETHEUS_BUCKETS = (
    0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5,
    0.75, 1.0, 2.5, 5.0, 7.5, 10.0, float("inf"),
)


class PrometheusMetricsBackend(MetricsBackend):
    """Production metrics backend backed by ``prometheus_client``.

    Metrics are automatically registered in the default Prometheus
    ``CollectorRegistry`` and can be scraped at the standard ``/metrics``
    endpoint.

    Raises:
        ImportError: If ``prometheus_client`` is not installed.
    """

    def __init__(self, *, namespace: str = "") -> None:
        try:
            import prometheus_client  # noqa: F401
        except ImportError as exc:
            raise ImportError(
                "prometheus_client is required for PrometheusMetricsBackend. "
                "Install it with: pip install shared[observability]"
            ) from exc

        self._namespace = namespace
        self._metrics: dict[str, object] = {}
        self._lock = Lock()

    def _full_name(self, name: str) -> str:
        return f"{self._namespace}_{name}" if self._namespace else name

    def counter(
        self,
        name: str,
        description: str,
        labels: list[str] | None = None,
    ) -> LabeledCounterLike:
        import prometheus_client

        full_name = self._full_name(name)
        with self._lock:
            if full_name not in self._metrics:
                self._metrics[full_name] = prometheus_client.Counter(
                    full_name,
                    description,
                    labelnames=labels or [],
                )
            return self._metrics[full_name]  # type: ignore[return-value]

    def gauge(
        self,
        name: str,
        description: str,
        labels: list[str] | None = None,
    ) -> LabeledGaugeLike:
        import prometheus_client

        full_name = self._full_name(name)
        with self._lock:
            if full_name not in self._metrics:
                self._metrics[full_name] = prometheus_client.Gauge(
                    full_name,
                    description,
                    labelnames=labels or [],
                )
            return self._metrics[full_name]  # type: ignore[return-value]

    def histogram(
        self,
        name: str,
        description: str,
        labels: list[str] | None = None,
        buckets: tuple[float, ...] | None = None,
    ) -> LabeledHistogramLike:
        import prometheus_client

        full_name = self._full_name(name)
        with self._lock:
            if full_name not in self._metrics:
                self._metrics[full_name] = prometheus_client.Histogram(
                    full_name,
                    description,
                    labelnames=labels or [],
                    buckets=buckets or _DEFAULT_PROMETHEUS_BUCKETS,
                )
            return self._metrics[full_name]  # type: ignore[return-value]

    def list_metrics(self) -> list[str]:
        with self._lock:
            return list(self._metrics.keys())


# ---------------------------------------------------------------------------
# Factory helper
# ---------------------------------------------------------------------------

_active_backend: MetricsBackend | None = None
_backend_lock = Lock()


def create_metrics_backend(
    *,
    namespace: str = "",
    backend: str = "auto",
) -> MetricsBackend:
    """Create a metrics backend.

    Args:
        namespace: Prefix for all metric names.
        backend: ``"auto"`` (try prometheus_client first), ``"prometheus"``,
            or ``"memory"``.

    Returns:
        A :class:`MetricsBackend` instance.

    Raises:
        ImportError: If ``backend="prometheus"`` and the library is missing.
        ValueError: If *backend* is not recognised.
    """
    if backend == "auto":
        try:
            return PrometheusMetricsBackend(namespace=namespace)
        except ImportError:
            return InMemoryMetricsBackend(namespace=namespace)
    elif backend == "prometheus":
        return PrometheusMetricsBackend(namespace=namespace)
    elif backend == "memory":
        return InMemoryMetricsBackend(namespace=namespace)
    else:
        raise ValueError(f"Unknown metrics backend: {backend!r}")


def get_metrics_backend() -> MetricsBackend:
    """Get or lazily create the global metrics backend.

    On first call the backend is auto-detected (Prometheus if available,
    otherwise in-memory).

    Returns:
        The active :class:`MetricsBackend`.
    """
    global _active_backend

    with _backend_lock:
        if _active_backend is None:
            _active_backend = create_metrics_backend()
        return _active_backend


def set_metrics_backend(backend: MetricsBackend) -> None:
    """Override the global metrics backend.

    Call this during application startup to explicitly choose a backend.

    Args:
        backend: The backend to use.
    """
    global _active_backend

    with _backend_lock:
        _active_backend = backend


def reset_metrics_backend() -> None:
    """Reset the global backend (useful in tests)."""
    global _active_backend

    with _backend_lock:
        _active_backend = None


# ---------------------------------------------------------------------------
# Convenience: ASGI metrics app factory
# ---------------------------------------------------------------------------


def create_prometheus_asgi_app() -> object:
    """Create an ASGI app that exposes ``/metrics`` for Prometheus scraping.

    Returns:
        An ASGI application from ``prometheus_client``.

    Raises:
        ImportError: If ``prometheus_client`` is not installed.

    Example (mount onto FastAPI)::

        from fastapi import FastAPI
        from shared.observability.prometheus_bridge import create_prometheus_asgi_app

        app = FastAPI()
        app.mount("/metrics", create_prometheus_asgi_app())
    """
    from prometheus_client import make_asgi_app

    return make_asgi_app()


__all__ = [
    "CounterLike",
    "GaugeLike",
    "HistogramLike",
    "InMemoryMetricsBackend",
    "LabeledCounterLike",
    "LabeledGaugeLike",
    "LabeledHistogramLike",
    "MetricsBackend",
    "PrometheusMetricsBackend",
    "create_metrics_backend",
    "create_prometheus_asgi_app",
    "get_metrics_backend",
    "reset_metrics_backend",
    "set_metrics_backend",
]
