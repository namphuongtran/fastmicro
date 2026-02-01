"""Observability utilities for microservices.

This module provides comprehensive observability features including:
- Structured logging with structlog (recommended)
- Legacy JSON logging with correlation ID support
- Distributed tracing with OpenTelemetry-compatible spans
- Prometheus-compatible metrics (Counter, Gauge, Histogram)
- Health check utilities for Kubernetes probes

Recommended Usage (structlog):
    from shared.observability import configure_structlog, get_structlog_logger, LoggingConfig
    
    configure_structlog(LoggingConfig(
        service_name="my-service",
        environment="production",
    ))
    logger = get_structlog_logger(__name__)
    logger.info("Application started", port=8000)

Legacy Usage (stdlib logging):
    from shared.observability import configure_logging, get_logger
    
    configure_logging(level="INFO", json_format=True)
    logger = get_logger(__name__)
    logger.info("Application started")
"""

from __future__ import annotations

from shared.observability.health import (
    HealthCheck,
    HealthCheckResult,
    HealthStatus,
    check_liveness,
    check_readiness,
    create_health_check,
    get_health_status,
    register_health_check,
)

# Legacy logging (for backward compatibility)
from shared.observability.logging import (
    CorrelationIdFilter,
    JSONFormatter,
    configure_logging,
    get_logger,
    with_context,
)
from shared.observability.metrics import (
    Counter,
    Gauge,
    Histogram,
    MetricsRegistry,
    configure_metrics,
    get_metrics_registry,
    timed,
)
from shared.observability.middleware import (
    RequestLoggingConfig,
    RequestLoggingMiddleware,
    get_correlation_id_from_request,
)

# Structlog-based logging (recommended)
from shared.observability.structlog_config import (
    # Configuration
    Environment,
    LoggingConfig,
    add_opentelemetry_context,
    # Processors
    add_service_context,
    bind_contextvars,
    clear_contextvars,
    clear_correlation_id,
    configure_structlog,
    configure_structlog_for_testing,
    generate_correlation_id,
    get_correlation_id,
    # Logger
    get_structlog_logger,
    reset_structlog_configuration,
    # Context management
    set_correlation_id,
    unbind_contextvars,
)
from shared.observability.tracing import (
    Span,
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

__all__ = [
    # Structlog (recommended)
    "Environment",
    "LoggingConfig",
    "configure_structlog",
    "configure_structlog_for_testing",
    "reset_structlog_configuration",
    "get_structlog_logger",
    "bind_contextvars",
    "clear_contextvars",
    "unbind_contextvars",
    "add_service_context",
    "add_opentelemetry_context",
    # Context (shared between both)
    "set_correlation_id",
    "get_correlation_id",
    "generate_correlation_id",
    "clear_correlation_id",
    # Legacy logging (backward compatibility)
    "JSONFormatter",
    "CorrelationIdFilter",
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
    # Middleware
    "RequestLoggingConfig",
    "RequestLoggingMiddleware",
    "get_correlation_id_from_request",
]
