# ADR-003: Observability Stack Selection

## Status
Accepted

## Date
2025-01

## Context
We need a comprehensive observability solution covering:
- **Metrics**: System and application performance metrics
- **Logging**: Centralized, structured log aggregation
- **Tracing**: Distributed tracing across microservices

## Decision
We will adopt the following observability stack:

| Concern | Tool | Reason |
|---------|------|--------|
| Metrics | **Prometheus** + **Grafana** | Industry standard, extensive ecosystem |
| Logging | **Seq** | Structured logging, .NET/Python friendly |
| Tracing | **Jaeger** | OpenTelemetry compatible, excellent UI |

### Integration Points

#### Python Services
```python
# Metrics
from prometheus_client import Counter, Histogram

# Tracing
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# Logging
import structlog
```

#### Instrumentation Strategy
1. **Auto-instrumentation** via OpenTelemetry for HTTP/database
2. **Custom metrics** for business KPIs
3. **Correlation IDs** propagated via middleware

### Dashboard Strategy
- Service Overview dashboard (latency, errors, throughput)
- Per-service detailed dashboards
- Infrastructure dashboards (Redis, Postgres, MongoDB)

## Consequences

### Positive
- Full observability coverage
- Open-source, no vendor lock-in
- Excellent tooling and documentation
- OpenTelemetry future-proofs tracing

### Negative
- Multiple tools to maintain
- Storage requirements for metrics/logs/traces
- Learning curve for Prometheus query language (PromQL)

## Alternatives Considered

1. **Datadog**: Excellent but expensive, vendor lock-in
2. **ELK Stack**: Complex to operate at scale
3. **Grafana Loki**: Considered for logging, Seq chosen for better .NET/Python integration
