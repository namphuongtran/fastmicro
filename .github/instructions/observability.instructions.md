---
description: 'Observability standards for Python microservices including structured logging, OpenTelemetry tracing, Prometheus metrics, and health checks'
applyTo: '**/*.py'
---

# Observability Standards

Comprehensive observability guidelines for enterprise Python microservices in the fastmicro project.

## The Three Pillars of Observability

```
┌─────────────────────────────────────────────────────────────────┐
│                      OBSERVABILITY                               │
├─────────────────────┬─────────────────────┬─────────────────────┤
│       LOGS          │       TRACES        │       METRICS       │
│   What happened?    │   Where happened?   │   How much/often?   │
│   (Events)          │   (Request flow)    │   (Aggregations)    │
└─────────────────────┴─────────────────────┴─────────────────────┘
```

## Structured Logging

### Configuration

```python
import structlog
from structlog.stdlib import ProcessorStack

def configure_logging(
    service_name: str,
    log_level: str = "INFO",
    json_output: bool = True,
) -> None:
    """Configure structured logging for the service."""
    
    processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]
    
    if json_output:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
```

### Logging Standards

```python
import structlog
from typing import Any

logger = structlog.get_logger()

# REQUIRED: Always include these fields
logger.info(
    "event_description",           # What happened (snake_case)
    service="user-service",        # Service name
    correlation_id="uuid-here",    # Request correlation ID
    user_id=123,                   # User context (if applicable)
)

# GOOD: Structured event logging
logger.info(
    "user_created",
    user_id=user.id,
    email=user.email,
    duration_ms=elapsed_time,
)

# GOOD: Error logging with context
logger.error(
    "database_connection_failed",
    host=db_host,
    port=db_port,
    error=str(e),
    retry_attempt=attempt,
    exc_info=True,
)

# BAD: Unstructured logging
logger.info(f"User {user.id} was created")  # Don't do this!
```

### Log Levels

| Level | Use Case |
|-------|----------|
| DEBUG | Detailed debugging information (not in production) |
| INFO | Significant events (request received, task completed) |
| WARNING | Unexpected but handled situations |
| ERROR | Errors that need attention but service continues |
| CRITICAL | Service cannot continue, immediate action required |

### Correlation ID Middleware

```python
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import structlog
import uuid

class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Add correlation ID to all requests."""
    
    HEADER_NAME = "X-Correlation-ID"
    
    async def dispatch(self, request: Request, call_next):
        correlation_id = request.headers.get(
            self.HEADER_NAME, 
            str(uuid.uuid4())
        )
        
        # Bind to structlog context
        structlog.contextvars.bind_contextvars(
            correlation_id=correlation_id
        )
        
        response = await call_next(request)
        response.headers[self.HEADER_NAME] = correlation_id
        
        # Clear context after request
        structlog.contextvars.unbind_contextvars("correlation_id")
        
        return response
```

## OpenTelemetry Tracing

### Setup

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME

def configure_tracing(
    service_name: str,
    otlp_endpoint: str = "http://localhost:4317",
) -> None:
    """Configure OpenTelemetry tracing."""
    
    resource = Resource(attributes={
        SERVICE_NAME: service_name
    })
    
    provider = TracerProvider(resource=resource)
    
    exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
    processor = BatchSpanProcessor(exporter)
    provider.add_span_processor(processor)
    
    trace.set_tracer_provider(provider)
```

### Tracing Patterns

```python
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

tracer = trace.get_tracer(__name__)

# Basic span
async def get_user(user_id: int) -> User:
    with tracer.start_as_current_span("get_user") as span:
        span.set_attribute("user.id", user_id)
        
        user = await repository.get(user_id)
        
        if user is None:
            span.set_status(Status(StatusCode.ERROR, "User not found"))
            raise NotFoundError(f"User {user_id} not found")
        
        return user

# Span with events
async def process_order(order: Order) -> None:
    with tracer.start_as_current_span("process_order") as span:
        span.set_attribute("order.id", order.id)
        span.set_attribute("order.total", order.total)
        
        span.add_event("validation_started")
        await validate_order(order)
        span.add_event("validation_completed")
        
        span.add_event("payment_started")
        await process_payment(order)
        span.add_event("payment_completed")

# Decorator for automatic tracing
def traced(name: str = None):
    """Decorator to add tracing to functions."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            span_name = name or func.__name__
            with tracer.start_as_current_span(span_name):
                return await func(*args, **kwargs)
        return wrapper
    return decorator
```

### Context Propagation

```python
from opentelemetry.propagate import inject, extract
from opentelemetry.propagators.b3 import B3MultiFormat
import httpx

# Propagate context in outgoing requests
async def call_external_service(url: str, data: dict) -> dict:
    headers = {}
    inject(headers)  # Inject trace context
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=data, headers=headers)
        return response.json()

# Extract context from incoming requests (middleware)
def extract_trace_context(request: Request):
    context = extract(request.headers)
    return context
```

## Prometheus Metrics

### Setup

```python
from prometheus_client import Counter, Histogram, Gauge, Info
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response

# Define metrics
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"]
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

ACTIVE_CONNECTIONS = Gauge(
    "active_connections",
    "Number of active connections"
)

SERVICE_INFO = Info(
    "service",
    "Service information"
)
```

### Metrics Middleware

```python
import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

class MetricsMiddleware(BaseHTTPMiddleware):
    """Collect HTTP metrics for all requests."""
    
    async def dispatch(self, request: Request, call_next):
        method = request.method
        endpoint = request.url.path
        
        ACTIVE_CONNECTIONS.inc()
        start_time = time.perf_counter()
        
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            status_code = 500
            raise
        finally:
            duration = time.perf_counter() - start_time
            
            REQUEST_COUNT.labels(
                method=method,
                endpoint=endpoint,
                status_code=status_code
            ).inc()
            
            REQUEST_LATENCY.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)
            
            ACTIVE_CONNECTIONS.dec()
        
        return response
```

### Custom Business Metrics

```python
# Define domain-specific metrics
ORDERS_PROCESSED = Counter(
    "orders_processed_total",
    "Total orders processed",
    ["status", "payment_method"]
)

ORDER_VALUE = Histogram(
    "order_value_dollars",
    "Order value distribution",
    buckets=[10, 25, 50, 100, 250, 500, 1000, 2500, 5000]
)

# Use in business logic
async def complete_order(order: Order) -> None:
    await process_order(order)
    
    ORDERS_PROCESSED.labels(
        status="completed",
        payment_method=order.payment_method
    ).inc()
    
    ORDER_VALUE.observe(order.total)
```

### Metrics Endpoint

```python
from fastapi import APIRouter
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

router = APIRouter()

@router.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )
```

## Health Checks

### Health Check Types

```python
from enum import Enum
from pydantic import BaseModel
from typing import Dict, Optional

class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"

class ComponentHealth(BaseModel):
    status: HealthStatus
    latency_ms: Optional[float] = None
    message: Optional[str] = None

class HealthResponse(BaseModel):
    status: HealthStatus
    version: str
    components: Dict[str, ComponentHealth]
```

### Health Check Implementation

```python
from fastapi import APIRouter
import asyncio
import time

router = APIRouter()

async def check_database() -> ComponentHealth:
    """Check database connectivity."""
    start = time.perf_counter()
    try:
        async with get_db_session() as session:
            await session.execute(text("SELECT 1"))
        latency = (time.perf_counter() - start) * 1000
        return ComponentHealth(status=HealthStatus.HEALTHY, latency_ms=latency)
    except Exception as e:
        return ComponentHealth(
            status=HealthStatus.UNHEALTHY, 
            message=str(e)
        )

async def check_redis() -> ComponentHealth:
    """Check Redis connectivity."""
    start = time.perf_counter()
    try:
        await redis_client.ping()
        latency = (time.perf_counter() - start) * 1000
        return ComponentHealth(status=HealthStatus.HEALTHY, latency_ms=latency)
    except Exception as e:
        return ComponentHealth(
            status=HealthStatus.UNHEALTHY,
            message=str(e)
        )

@router.get("/health/live")
async def liveness():
    """Kubernetes liveness probe - is the service running?"""
    return {"status": "alive"}

@router.get("/health/ready")
async def readiness() -> HealthResponse:
    """Kubernetes readiness probe - can the service handle traffic?"""
    db_health, redis_health = await asyncio.gather(
        check_database(),
        check_redis(),
    )
    
    components = {
        "database": db_health,
        "redis": redis_health,
    }
    
    # Determine overall status
    if all(c.status == HealthStatus.HEALTHY for c in components.values()):
        overall = HealthStatus.HEALTHY
    elif any(c.status == HealthStatus.UNHEALTHY for c in components.values()):
        overall = HealthStatus.UNHEALTHY
    else:
        overall = HealthStatus.DEGRADED
    
    return HealthResponse(
        status=overall,
        version=settings.version,
        components=components,
    )
```

## Integration Example

### FastAPI Application Setup

```python
from fastapi import FastAPI
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    configure_logging(service_name="user-service")
    configure_tracing(service_name="user-service")
    SERVICE_INFO.info({
        "version": settings.version,
        "environment": settings.environment,
    })
    
    yield
    
    # Shutdown
    # Cleanup resources

app = FastAPI(lifespan=lifespan)

# Add middleware
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(MetricsMiddleware)

# Add routes
app.include_router(health_router, prefix="/health", tags=["health"])
app.include_router(metrics_router, tags=["metrics"])
```

## Naming Conventions

### Metrics

```
# Format: <namespace>_<subsystem>_<name>_<unit>

# Counters (total suffix)
http_requests_total
orders_processed_total
errors_total

# Histograms/Summaries (unit suffix)
http_request_duration_seconds
order_processing_duration_seconds

# Gauges (no special suffix)
active_connections
queue_depth
memory_usage_bytes
```

### Spans

```
# Format: <verb>_<noun> or <service>.<operation>

# Good
get_user
create_order
validate_payment
user-service.authenticate

# Bad
UserService
doStuff
process
```

### Log Events

```
# Format: <noun>_<past_tense_verb>

# Good
user_created
order_processed
payment_failed
connection_established

# Bad
Creating user
ProcessOrder
error!!
```
