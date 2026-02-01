---
description: 'Cloud-native Python development guidelines following 12-factor principles, resilience patterns, and Kubernetes-ready practices'
applyTo: '**/*.py'
---

# Cloud-Native Python Development

Guidelines for building cloud-native Python microservices that are resilient, scalable, and Kubernetes-ready.

## The Twelve-Factor App

### 1. Codebase
- One codebase tracked in version control, many deploys
- Use monorepo or polyrepo consistently
- Tag releases, use semantic versioning

### 2. Dependencies
- Explicitly declare and isolate dependencies
- Use `pyproject.toml` with uv
- Pin exact versions for reproducibility (use `uv.lock`)

```toml
[project]
dependencies = [
    "fastapi==0.109.0",
    "pydantic==2.5.3",
    "sqlalchemy==2.0.25",
]
```

### 3. Config
- Store config in environment variables
- Never hardcode credentials or environment-specific values

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    redis_url: str
    secret_key: str
    debug: bool = False
    
    class Config:
        env_file = ".env"
```

### 4. Backing Services
- Treat backing services as attached resources
- Use dependency injection for service clients
- Support swapping services without code changes

```python
# Abstract interface
class ICacheService(ABC):
    @abstractmethod
    async def get(self, key: str) -> Optional[str]: ...
    @abstractmethod
    async def set(self, key: str, value: str, ttl: int) -> None: ...

# Redis implementation
class RedisCacheService(ICacheService):
    def __init__(self, redis_url: str):
        self._client = aioredis.from_url(redis_url)
```

### 5. Build, Release, Run
- Strictly separate build and run stages
- Use immutable releases with unique IDs
- Docker images should be immutable

### 6. Processes
- Execute the app as stateless processes
- Store session data in backing services (Redis)
- No sticky sessions

### 7. Port Binding
- Export services via port binding
- Self-contained with embedded server

```python
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
```

### 8. Concurrency
- Scale out via the process model
- Use async for I/O-bound operations
- Use workers for CPU-bound operations

### 9. Disposability
- Maximize robustness with fast startup and graceful shutdown
- Handle SIGTERM gracefully

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await startup_tasks()
    yield
    # Shutdown (graceful)
    await shutdown_tasks()
    await close_connections()

app = FastAPI(lifespan=lifespan)
```

### 10. Dev/Prod Parity
- Keep development, staging, and production similar
- Use Docker Compose for local development
- Same backing services in all environments

### 11. Logs
- Treat logs as event streams
- Write to stdout/stderr
- Use structured JSON logging

### 12. Admin Processes
- Run admin/management tasks as one-off processes
- Use CLI tools or management commands

## Resilience Patterns

### Circuit Breaker

```python
from enum import Enum
from datetime import datetime, timedelta
import asyncio

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery

class CircuitBreaker:
    """Circuit breaker pattern implementation."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_max_calls: int = 3,
    ):
        self._failure_threshold = failure_threshold
        self._recovery_timeout = timedelta(seconds=recovery_timeout)
        self._half_open_max_calls = half_open_max_calls
        
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: datetime | None = None
        self._half_open_calls = 0
        self._lock = asyncio.Lock()
    
    async def __aenter__(self):
        async with self._lock:
            if self._state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self._state = CircuitState.HALF_OPEN
                    self._half_open_calls = 0
                else:
                    raise CircuitOpenError("Circuit is open")
            
            if self._state == CircuitState.HALF_OPEN:
                if self._half_open_calls >= self._half_open_max_calls:
                    raise CircuitOpenError("Circuit half-open limit reached")
                self._half_open_calls += 1
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        async with self._lock:
            if exc_type is not None:
                self._record_failure()
            else:
                self._record_success()
        return False
    
    def _record_failure(self):
        self._failure_count += 1
        self._last_failure_time = datetime.now()
        
        if self._failure_count >= self._failure_threshold:
            self._state = CircuitState.OPEN
    
    def _record_success(self):
        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.CLOSED
        self._failure_count = 0
    
    def _should_attempt_reset(self) -> bool:
        if self._last_failure_time is None:
            return True
        return datetime.now() - self._last_failure_time >= self._recovery_timeout
```

### Retry with Exponential Backoff

```python
import asyncio
import random
from functools import wraps
from typing import Type, Tuple

def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
):
    """Decorator for retry with exponential backoff."""
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    
                    if attempt == max_retries:
                        raise
                    
                    # Calculate delay
                    delay = min(
                        base_delay * (exponential_base ** attempt),
                        max_delay
                    )
                    
                    # Add jitter
                    if jitter:
                        delay = delay * (0.5 + random.random())
                    
                    await asyncio.sleep(delay)
            
            raise last_exception
        
        return wrapper
    return decorator

# Usage
@retry_with_backoff(
    max_retries=3,
    retryable_exceptions=(ConnectionError, TimeoutError)
)
async def call_external_api(url: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(url, timeout=10.0)
        response.raise_for_status()
        return response.json()
```

### Bulkhead Pattern

```python
import asyncio
from contextlib import asynccontextmanager

class Bulkhead:
    """Bulkhead pattern to isolate failures."""
    
    def __init__(self, name: str, max_concurrent: int = 10):
        self._name = name
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._active = 0
    
    @asynccontextmanager
    async def acquire(self, timeout: float = None):
        """Acquire a slot in the bulkhead."""
        try:
            acquired = await asyncio.wait_for(
                self._semaphore.acquire(),
                timeout=timeout
            )
            self._active += 1
            yield
        except asyncio.TimeoutError:
            raise BulkheadFullError(f"Bulkhead {self._name} is full")
        finally:
            self._active -= 1
            self._semaphore.release()

# Usage
db_bulkhead = Bulkhead("database", max_concurrent=20)
external_api_bulkhead = Bulkhead("external_api", max_concurrent=5)

async def query_database():
    async with db_bulkhead.acquire(timeout=5.0):
        # Database operations isolated
        return await db.execute(query)
```

### Timeout Pattern

```python
import asyncio
from functools import wraps

def with_timeout(seconds: float):
    """Decorator to add timeout to async functions."""
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=seconds
                )
            except asyncio.TimeoutError:
                raise TimeoutError(
                    f"{func.__name__} timed out after {seconds}s"
                )
        return wrapper
    return decorator

# Usage
@with_timeout(10.0)
async def slow_operation():
    await external_service.call()
```

## Kubernetes-Ready Patterns

### Graceful Shutdown

```python
import signal
import asyncio
from typing import Set

class GracefulShutdown:
    """Handle graceful shutdown for Kubernetes."""
    
    def __init__(self):
        self._shutdown_event = asyncio.Event()
        self._active_requests: Set[asyncio.Task] = set()
    
    def setup_signal_handlers(self):
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(
                sig,
                lambda: asyncio.create_task(self._shutdown())
            )
    
    async def _shutdown(self):
        logger.info("shutdown_initiated")
        self._shutdown_event.set()
        
        # Wait for active requests
        if self._active_requests:
            logger.info(
                "waiting_for_requests",
                count=len(self._active_requests)
            )
            await asyncio.gather(*self._active_requests, return_exceptions=True)
        
        logger.info("shutdown_complete")
    
    def track_request(self, task: asyncio.Task):
        self._active_requests.add(task)
        task.add_done_callback(self._active_requests.discard)
    
    @property
    def is_shutting_down(self) -> bool:
        return self._shutdown_event.is_set()
```

### Pre-Stop Hook Support

```python
from fastapi import FastAPI
from contextlib import asynccontextmanager

shutdown_manager = GracefulShutdown()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    shutdown_manager.setup_signal_handlers()
    yield
    # Shutdown
    await shutdown_manager.wait_for_shutdown()

@app.get("/prestop")
async def prestop():
    """Kubernetes preStop hook endpoint."""
    # Give time for load balancer to remove pod
    await asyncio.sleep(5)
    return {"status": "ready_for_shutdown"}
```

### Resource Limits Awareness

```python
import os

def get_memory_limit() -> int:
    """Get memory limit from cgroup (Kubernetes)."""
    try:
        # cgroup v2
        with open("/sys/fs/cgroup/memory.max") as f:
            limit = f.read().strip()
            if limit == "max":
                return -1  # No limit
            return int(limit)
    except FileNotFoundError:
        try:
            # cgroup v1
            with open("/sys/fs/cgroup/memory/memory.limit_in_bytes") as f:
                return int(f.read().strip())
        except FileNotFoundError:
            return -1  # Not in container

def get_cpu_limit() -> float:
    """Get CPU limit from cgroup (Kubernetes)."""
    try:
        with open("/sys/fs/cgroup/cpu.max") as f:
            quota, period = f.read().strip().split()
            if quota == "max":
                return -1  # No limit
            return int(quota) / int(period)
    except FileNotFoundError:
        return -1  # Not in container

# Configure worker count based on limits
cpu_limit = get_cpu_limit()
worker_count = max(1, int(cpu_limit)) if cpu_limit > 0 else os.cpu_count()
```

## Configuration Management

### Environment-Based Configuration

```python
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Literal

class Settings(BaseSettings):
    # Environment
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = Field(default=False)
    
    # Service
    service_name: str = "my-service"
    service_version: str = "0.0.0"
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = Field(default=1, ge=1)
    
    # Database
    database_url: str
    database_pool_size: int = Field(default=5, ge=1)
    database_max_overflow: int = Field(default=10, ge=0)
    
    # Redis
    redis_url: str = "redis://localhost:6379"
    
    # Observability
    log_level: str = "INFO"
    otlp_endpoint: str = "http://localhost:4317"
    
    # Security
    secret_key: str
    access_token_expire_minutes: int = 30
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        
    @property
    def is_production(self) -> bool:
        return self.environment == "production"
    
    @property
    def is_development(self) -> bool:
        return self.environment == "development"
```

### Feature Flags Interface

```python
from abc import ABC, abstractmethod
from typing import Any, Optional

class IFeatureFlags(ABC):
    """Feature flags interface."""
    
    @abstractmethod
    async def is_enabled(
        self, 
        flag: str, 
        default: bool = False,
        context: Optional[dict] = None
    ) -> bool:
        """Check if a feature flag is enabled."""
        ...
    
    @abstractmethod
    async def get_value(
        self,
        flag: str,
        default: Any = None,
        context: Optional[dict] = None
    ) -> Any:
        """Get feature flag value."""
        ...

# Environment-based implementation
class EnvFeatureFlags(IFeatureFlags):
    def __init__(self, prefix: str = "FEATURE_"):
        self._prefix = prefix
    
    async def is_enabled(
        self,
        flag: str,
        default: bool = False,
        context: Optional[dict] = None
    ) -> bool:
        env_var = f"{self._prefix}{flag.upper()}"
        value = os.getenv(env_var)
        if value is None:
            return default
        return value.lower() in ("true", "1", "yes", "on")
```

## Container Best Practices

### Dockerfile

```dockerfile
# Build stage
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app

# Set uv environment variables
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project --no-dev

# Runtime stage
FROM python:3.12-slim-bookworm

WORKDIR /app

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy virtual environment from builder
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Copy application
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health/live')"

# Run
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### docker-compose.yml (Development)

```yaml
version: "3.8"

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/app
      - REDIS_URL=redis://redis:6379
      - SECRET_KEY=dev-secret-key
      - ENVIRONMENT=development
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - .:/app
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload

  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
      POSTGRES_DB: app
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user -d app"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5
```
