# Shared Library

Enterprise shared library for Python microservices - providing exceptions, constants, utilities, observability, resilience, authentication, and database patterns.

## Installation

### Local Development (Editable)

```bash
pip install -e ".[dev]"
```

### With Optional Dependencies

```bash
# All optional dependencies
pip install -e ".[all]"

# Specific groups
pip install -e ".[observability]"
pip install -e ".[database]"
pip install -e ".[auth]"
pip install -e ".[grpc]"
```

## Quick Start

### Exceptions

```python
from shared.exceptions import NotFoundException, ValidationException, FieldError

# HTTP exception with resource details
raise NotFoundException.for_resource("User", "user-123")

# Validation errors
errors = [
    FieldError(loc=("body", "email"), msg="Invalid email", type="value_error.email")
]
raise ValidationException(errors=errors)
```

### Constants

```python
from shared.constants import HTTPStatus, Environment

if status == HTTPStatus.OK:
    print("Success!")

if Environment.current() == Environment.PRODUCTION:
    print("Running in production")
```

### Utilities

```python
from shared.utils import utc_now, serialize_datetime

now = utc_now()
iso_string = serialize_datetime(now)
```

## Module Overview

| Module | Description |
|--------|-------------|
| `exceptions` | Exception hierarchy with HTTP mapping, database errors, validation |
| `constants` | HTTP status codes, environments, regex patterns |
| `utils` | Date/time, serialization, validation utilities |
| `auth` | JWT, password hashing, OAuth2/OIDC, RBAC |
| `dbs` | Repository pattern, Unit of Work, async sessions |
| `observability` | Structured logging, OpenTelemetry tracing, Prometheus metrics |
| `resilience` | Circuit breaker, retry, bulkhead patterns |
| `proto` | Protocol Buffers and gRPC support |
| `messaging` | Event-driven messaging (Kafka, RabbitMQ) |
| `caching` | Redis and in-memory caching with decorators |

## Development

```bash
# Run tests
pytest

# Run tests with coverage
pytest --cov=shared --cov-report=html

# Type checking
mypy shared

# Linting
ruff check shared
```

## License

MIT
