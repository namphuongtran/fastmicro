"""Tests for the Prometheus metrics bridge."""

from __future__ import annotations

import pytest

from shared.observability.prometheus_bridge import (
    InMemoryMetricsBackend,
    MetricsBackend,
    PrometheusMetricsBackend,
    create_metrics_backend,
    get_metrics_backend,
    reset_metrics_backend,
    set_metrics_backend,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_global_backend():
    """Reset global backend between tests."""
    reset_metrics_backend()
    yield
    reset_metrics_backend()


@pytest.fixture()
def memory_backend() -> InMemoryMetricsBackend:
    return InMemoryMetricsBackend(namespace="test")


@pytest.fixture()
def prom_backend() -> PrometheusMetricsBackend:
    """Prometheus backend – uses a fresh CollectorRegistry per test."""
    import prometheus_client

    # Use an isolated registry so tests don't interfere with each other
    registry = prometheus_client.CollectorRegistry()
    backend = _PrometheusBackendIsolated(namespace="test", registry=registry)
    return backend


class _PrometheusBackendIsolated(PrometheusMetricsBackend):
    """Test helper: Prometheus backend with isolated registry."""

    def __init__(self, *, namespace: str = "", registry: object = None) -> None:
        super().__init__(namespace=namespace)
        self._isolated_registry = registry

    def counter(self, name, description, labels=None):
        import prometheus_client

        full_name = self._full_name(name)
        with self._lock:
            if full_name not in self._metrics:
                self._metrics[full_name] = prometheus_client.Counter(
                    full_name,
                    description,
                    labelnames=labels or [],
                    registry=self._isolated_registry,
                )
            return self._metrics[full_name]

    def gauge(self, name, description, labels=None):
        import prometheus_client

        full_name = self._full_name(name)
        with self._lock:
            if full_name not in self._metrics:
                self._metrics[full_name] = prometheus_client.Gauge(
                    full_name,
                    description,
                    labelnames=labels or [],
                    registry=self._isolated_registry,
                )
            return self._metrics[full_name]

    def histogram(self, name, description, labels=None, buckets=None):
        import prometheus_client

        full_name = self._full_name(name)
        with self._lock:
            if full_name not in self._metrics:
                self._metrics[full_name] = prometheus_client.Histogram(
                    full_name,
                    description,
                    labelnames=labels or [],
                    buckets=buckets or (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, float("inf")),
                    registry=self._isolated_registry,
                )
            return self._metrics[full_name]


# ====================================================================
# InMemoryMetricsBackend
# ====================================================================


class TestInMemoryMetricsBackend:
    """Tests for InMemoryMetricsBackend."""

    def test_counter_inc(self, memory_backend: InMemoryMetricsBackend):
        counter = memory_backend.counter("requests_total", "Total requests")
        counter.inc()
        counter.inc(5)
        assert "test_requests_total" in memory_backend.list_metrics()

    def test_counter_labels(self, memory_backend: InMemoryMetricsBackend):
        counter = memory_backend.counter("http_requests", "HTTP", ["method"])
        counter.labels(method="GET").inc()
        counter.labels(method="POST").inc(2)
        assert "test_http_requests" in memory_backend.list_metrics()

    def test_gauge_set(self, memory_backend: InMemoryMetricsBackend):
        gauge = memory_backend.gauge("temperature", "Temp")
        gauge.set(42.0)
        assert "test_temperature" in memory_backend.list_metrics()

    def test_gauge_inc_dec(self, memory_backend: InMemoryMetricsBackend):
        gauge = memory_backend.gauge("connections", "Active connections")
        gauge.inc()
        gauge.inc(3)
        gauge.dec()
        assert "test_connections" in memory_backend.list_metrics()

    def test_gauge_labels(self, memory_backend: InMemoryMetricsBackend):
        gauge = memory_backend.gauge("pool_size", "Pool", ["name"])
        gauge.labels(name="db").set(10)
        assert "test_pool_size" in memory_backend.list_metrics()

    def test_histogram_observe(self, memory_backend: InMemoryMetricsBackend):
        hist = memory_backend.histogram("latency", "Request latency")
        hist.observe(0.5)
        hist.observe(1.2)
        assert "test_latency" in memory_backend.list_metrics()

    def test_histogram_labels(self, memory_backend: InMemoryMetricsBackend):
        hist = memory_backend.histogram("resp_size", "Response size", ["endpoint"])
        hist.labels(endpoint="/api").observe(1024)
        assert "test_resp_size" in memory_backend.list_metrics()

    def test_list_metrics_empty(self):
        backend = InMemoryMetricsBackend()
        assert backend.list_metrics() == []

    def test_namespace_applied(self, memory_backend: InMemoryMetricsBackend):
        memory_backend.counter("foo", "foo counter")
        assert "test_foo" in memory_backend.list_metrics()

    def test_counter_reuse(self, memory_backend: InMemoryMetricsBackend):
        c1 = memory_backend.counter("dup", "dup counter")
        c2 = memory_backend.counter("dup", "dup counter")
        assert c1 is c2

    def test_is_metrics_backend(self, memory_backend: InMemoryMetricsBackend):
        assert isinstance(memory_backend, MetricsBackend)


# ====================================================================
# PrometheusMetricsBackend
# ====================================================================


class TestPrometheusMetricsBackend:
    """Tests for PrometheusMetricsBackend (requires prometheus_client)."""

    def test_counter_inc(self, prom_backend):
        counter = prom_backend.counter("prom_requests", "Total")
        counter.inc()
        counter.inc(5)
        # prometheus_client Counter._value is accessible
        assert counter._value.get() == 6.0

    def test_counter_labels(self, prom_backend):
        counter = prom_backend.counter("prom_http", "HTTP", ["method"])
        counter.labels(method="GET").inc()
        counter.labels(method="POST").inc(2)
        assert counter.labels(method="GET")._value.get() == 1.0
        assert counter.labels(method="POST")._value.get() == 2.0

    def test_gauge_set(self, prom_backend):
        gauge = prom_backend.gauge("prom_temp", "Temp")
        gauge.set(42.0)
        assert gauge._value.get() == 42.0

    def test_gauge_inc_dec(self, prom_backend):
        gauge = prom_backend.gauge("prom_conn", "Connections")
        gauge.inc()
        gauge.inc(3)
        gauge.dec()
        assert gauge._value.get() == 3.0

    def test_gauge_labels(self, prom_backend):
        gauge = prom_backend.gauge("prom_pool", "Pool", ["name"])
        gauge.labels(name="db").set(10)
        assert gauge.labels(name="db")._value.get() == 10.0

    def test_histogram_observe(self, prom_backend):
        hist = prom_backend.histogram("prom_latency", "Latency")
        hist.observe(0.5)
        hist.observe(1.2)
        # _sum is cumulative
        assert hist._sum.get() == pytest.approx(1.7, abs=0.01)

    def test_histogram_labels(self, prom_backend):
        hist = prom_backend.histogram("prom_resp", "Response", ["path"])
        hist.labels(path="/api").observe(1024)
        assert hist.labels(path="/api")._sum.get() == pytest.approx(1024.0)

    def test_list_metrics(self, prom_backend):
        prom_backend.counter("prom_a", "a")
        prom_backend.gauge("prom_b", "b")
        names = prom_backend.list_metrics()
        assert "test_prom_a" in names
        assert "test_prom_b" in names

    def test_metric_reuse(self, prom_backend):
        c1 = prom_backend.counter("same", "same")
        c2 = prom_backend.counter("same", "same")
        assert c1 is c2

    def test_is_metrics_backend(self, prom_backend):
        assert isinstance(prom_backend, MetricsBackend)


# ====================================================================
# Factory / globals
# ====================================================================


class TestFactory:
    """Tests for create_metrics_backend and global management."""

    def test_create_auto(self):
        backend = create_metrics_backend(backend="auto")
        # Should succeed either way – prometheus_client is installed in dev
        assert isinstance(backend, MetricsBackend)

    def test_create_memory(self):
        backend = create_metrics_backend(backend="memory")
        assert isinstance(backend, InMemoryMetricsBackend)

    def test_create_prometheus(self):
        backend = create_metrics_backend(backend="prometheus")
        assert isinstance(backend, PrometheusMetricsBackend)

    def test_create_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown metrics backend"):
            create_metrics_backend(backend="unknown")

    def test_get_metrics_backend_creates_default(self):
        backend = get_metrics_backend()
        assert isinstance(backend, MetricsBackend)

    def test_set_metrics_backend(self):
        custom = InMemoryMetricsBackend(namespace="custom")
        set_metrics_backend(custom)
        assert get_metrics_backend() is custom

    def test_reset_metrics_backend(self):
        set_metrics_backend(InMemoryMetricsBackend())
        reset_metrics_backend()
        # Next call creates a new one
        b = get_metrics_backend()
        assert isinstance(b, MetricsBackend)

    def test_namespace_passed(self):
        backend = create_metrics_backend(namespace="svc", backend="memory")
        backend.counter("cnt", "counter")
        assert "svc_cnt" in backend.list_metrics()
