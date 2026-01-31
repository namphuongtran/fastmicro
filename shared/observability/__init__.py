"""Observability utilities for microservices.

This module provides comprehensive observability features including:
- Structured JSON logging with correlation ID support
- Distributed tracing with OpenTelemetry-compatible spans
- Prometheus-compatible metrics (Counter, Gauge, Histogram)
- Health check utilities for Kubernetes probes
"""

from __future__ import annotations

from shared.observability.logging import (
    JSONFormatter,
    CorrelationIdFilter,
    set_correlation_id,
    get_correlation_id,
    generate_correlation_id,
    with_context,
    get_logger,
    configure_logging,
)

from shared.observability.tracing import (
    SpanKind,
    TracingConfig,
    Span,
    configure_tracing,
    get_current_span,
    get_trace_id,
    create_span,
    inject_context,
    extract_context,
    traced,
)

from shared.observability.metrics import (
    Counter,
    Gauge,
    Histogram,
    MetricsRegistry,
    get_metrics_registry,
    configure_metrics,
    timed,
)

from shared.observability.health import (
    HealthStatus,
    HealthCheckResult,
    HealthCheck,
    register_health_check,
    create_health_check,
    check_liveness,
    check_readiness,
    get_health_status,
)


__all__ = [
    # Logging
    "JSONFormatter",
    "CorrelationIdFilter",
    "set_correlation_id",
    "get_correlation_id",
    "generate_correlation_id",
    "with_context",
    "get_logger",
    "configure_logging",
    # Tracing
    "SpanKind",
    "TracingConfig",
    "Span",
    "configure_tracing",
    "get_current_span",
    "get_trace_id",
    "create_span",
    "inject_context",
    "extract_context",
    "traced",
    # Metrics
    "Counter",
    "Gauge",
    "Histogram",
    "MetricsRegistry",
    "get_metrics_registry",
    "configure_metrics",
    "timed",
    # Health
    "HealthStatus",
    "HealthCheckResult",
    "HealthCheck",
    "register_health_check",
    "create_health_check",
    "check_liveness",
    "check_readiness",
    "get_health_status",
]
