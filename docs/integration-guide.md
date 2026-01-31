# Shared Library Integration Guide

This guide explains how to integrate the shared library into your microservice.

## Prerequisites

- Python 3.12+
- Poetry 2.x installed

## Quick Start

### 1. Add Shared Library Dependency

In your service's `pyproject.toml`:

```toml
[tool.poetry.group.local.dependencies]
shared = { path = "../../shared", develop = true }
```

### 2. Install Dependencies

```bash
cd services/your-service
poetry install
```

### 3. Import and Use

```python
# Authentication
from shared.auth import JWTValidator, get_current_user

# Database utilities
from shared.dbs import DatabaseManager, get_session

# Exceptions
from shared.exceptions import NotFoundError, ValidationError

# Logging
from shared.observability import get_logger, setup_logging

# HTTP client
from shared.http import AsyncHTTPClient

# Constants
from shared.constants import HTTPStatus
```

## Module Reference

### `shared.auth`
Authentication and authorization utilities.

```python
from shared.auth import JWTValidator, get_current_user, require_permission

# Validate JWT tokens
validator = JWTValidator(settings.keycloak_url)
user = await validator.validate(token)

# Use as FastAPI dependency
@router.get("/protected")
async def protected_route(user: User = Depends(get_current_user)):
    return {"user": user.email}
```

### `shared.dbs`
Database connection management.

```python
from shared.dbs import AsyncSessionManager, get_async_session

# Configure database
session_manager = AsyncSessionManager(settings.database_url)

# Use in routes
@router.get("/items")
async def get_items(db: AsyncSession = Depends(get_async_session)):
    return await db.execute(select(Item))
```

### `shared.exceptions`
Standard exception hierarchy.

```python
from shared.exceptions import (
    AppException,
    NotFoundError,
    ValidationError,
    UnauthorizedError,
    ForbiddenError,
)

# Raise exceptions
raise NotFoundError(f"Item {item_id} not found")

# Register handlers in FastAPI
from shared.exceptions import register_exception_handlers
register_exception_handlers(app)
```

### `shared.observability`
Logging, metrics, and tracing.

```python
from shared.observability import (
    get_logger,
    setup_logging,
    MetricsMiddleware,
    TracingMiddleware,
)

# Configure logging
setup_logging(level="INFO", format="json")
logger = get_logger(__name__)

# Add middleware
app.add_middleware(MetricsMiddleware)
app.add_middleware(TracingMiddleware)
```

### `shared.http`
HTTP client with resilience patterns.

```python
from shared.http import AsyncHTTPClient, RetryConfig

client = AsyncHTTPClient(
    base_url="https://api.example.com",
    retry_config=RetryConfig(max_retries=3, backoff_factor=0.5),
)

response = await client.get("/users")
```

## Best Practices

### 1. Use Dependency Injection
```python
# Good: Use Depends() for shared utilities
@router.get("/")
async def handler(logger = Depends(get_logger)):
    logger.info("Processing request")

# Avoid: Direct instantiation in handlers
```

### 2. Configure at Startup
```python
# In main.py lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(level=settings.log_level)
    await database.connect()
    yield
    await database.disconnect()
```

### 3. Handle Exceptions Consistently
```python
# Register once in main.py
from shared.exceptions import register_exception_handlers
register_exception_handlers(app)
```

## Troubleshooting

### Import Errors
If you get import errors, ensure:
1. Poetry virtual environment is activated
2. Shared library is installed: `poetry install`
3. Python path includes shared: `PYTHONPATH=/app/shared`

### Version Conflicts
If dependencies conflict:
1. Check shared library versions in `shared/pyproject.toml`
2. Update your service to compatible versions
3. Run `poetry update` to resolve

## See Also

- [Architecture Overview](./architecture.md)
- [ADR-002: Shared Library Strategy](./adr/0002-shared-library.md)
