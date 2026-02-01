# Audit Service

Enterprise audit logging service for tracking system events, user actions, and compliance records.

## Overview

The Audit Service provides centralized audit logging capabilities for the microservices architecture. It captures and stores audit events from all services, enabling compliance reporting, security analysis, and operational insights.

## Features

- **Event Logging**: Capture audit events from all microservices
- **Compliance Support**: GDPR, SOC2, and HIPAA compliance tracking
- **Search & Query**: Full-text search and filtering capabilities
- **Retention Policies**: Configurable data retention and archival
- **Real-time Streaming**: WebSocket support for live audit feeds
- **Export Capabilities**: CSV, JSON, and PDF export formats

## Architecture

This service follows **Clean Architecture** principles:

```
src/audit_service/
├── api/                    # HTTP/gRPC interface layer
│   └── v1/                 # API version 1
│       ├── audit_controller.py
│       └── health_controller.py
├── application/            # Use cases and business logic
│   ├── services/           # Application services
│   │   └── audit_service.py
│   └── dtos/               # Data Transfer Objects
├── domain/                 # Core business entities
│   ├── entities/           # Domain models
│   │   └── audit_event.py
│   ├── repositories/       # Repository interfaces
│   │   └── audit_repository.py
│   └── value_objects/      # Value objects
├── infrastructure/         # External concerns
│   ├── persistence/        # Database implementations
│   │   └── sqlalchemy_audit_repository.py
│   ├── middleware/         # HTTP middleware
│   └── messaging/          # Event bus integration
├── configs/                # Configuration
│   └── settings.py
└── main.py                 # Application entry point
```

## Technology Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL (via SQLAlchemy async)
- **Caching**: Redis (via shared library)
- **Observability**: OpenTelemetry, Prometheus
- **Messaging**: RabbitMQ (for event consumption)

## Getting Started

### Prerequisites

- Python 3.12+
- uv (Python package manager)
- Docker & Docker Compose

### Local Development

```bash
# Navigate to service directory
cd services/audit-service

# Install dependencies
uv sync

# Run database migrations
uv run alembic upgrade head

# Start the service
uv run uvicorn audit_service.main:app --reload --port 8001
```

### Docker Development

```bash
# From project root
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up audit-service
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src/audit_service --cov-report=html

# Run specific test file
uv run pytest tests/unit/test_audit_service.py -v
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/ready` | Readiness check |
| GET | `/metrics` | Prometheus metrics |
| POST | `/api/v1/audit/events` | Create audit event |
| GET | `/api/v1/audit/events` | List audit events |
| GET | `/api/v1/audit/events/{id}` | Get audit event by ID |
| GET | `/api/v1/audit/events/search` | Search audit events |
| GET | `/api/v1/audit/events/export` | Export audit events |

## Configuration

Configuration is managed via environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_ENV` | Environment (development/staging/production) | development |
| `APP_PORT` | Service port | 8001 |
| `DATABASE_URL` | PostgreSQL connection string | - |
| `REDIS_URL` | Redis connection string | - |
| `RABBITMQ_URL` | RabbitMQ connection string | - |
| `LOG_LEVEL` | Logging level | INFO |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OpenTelemetry collector endpoint | - |

## Integration with Shared Library

This service leverages the shared library for common functionality:

```python
from shared.exceptions import HTTPException, ValidationError
from shared.config import BaseSettings
from shared.observability import get_logger, setup_tracing
from shared.cache import TieredCacheManager
from shared.dbs import AsyncSessionFactory
from shared.auth import require_auth, get_current_user
```

## License

MIT License - see [LICENSE](../../LICENSE) for details.
