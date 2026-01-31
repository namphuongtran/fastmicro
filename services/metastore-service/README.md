# Metastore Service

Metadata management service for storing and managing application metadata, configurations, and feature flags. Built with Domain-Driven Design (DDD) principles and Clean Architecture.

## Overview

The Metastore Service provides centralized metadata management for the microservices architecture. It handles application configurations, feature flags, tenant settings, and dynamic configurations with full versioning support.

## Features

- **Metadata Storage**: Store and retrieve arbitrary key-value metadata with namespacing and tagging
- **Feature Flags**: Dynamic feature flag management with targeting rules, rollout percentages, and environment/tenant overrides
- **Configuration Management**: Centralized typed configuration for services with JSON schema validation
- **Multi-tenant Support**: Tenant-isolated configurations and metadata
- **Version Control**: Full version history with rollback capability for all changes
- **Caching**: Redis-based caching layer for hot metadata and feature flags
- **Secret Management**: SecretReference pattern for secure credential handling with vault integration

## Architecture

The service follows Clean Architecture with DDD principles:

```
src/metastore_service/
├── api/                    # API layer (FastAPI routers)
│   ├── routes/             # Endpoint definitions
│   └── dependencies.py     # Dependency injection
├── application/            # Application layer
│   ├── dtos/               # Data transfer objects (Pydantic)
│   └── services/           # Business logic services
├── domain/                 # Domain layer (pure Python)
│   ├── entities/           # Aggregate roots and entities
│   ├── repositories/       # Repository interfaces (ABCs)
│   └── value_objects.py    # Value objects (immutable)
├── infrastructure/         # Infrastructure layer
│   ├── cache/              # Redis caching implementation
│   ├── database/           # SQLAlchemy models and sessions
│   └── repositories/       # Repository implementations
└── configs/                # Application settings
```

## Domain Model

### Aggregates

1. **MetadataEntry** - Generic key-value metadata with versioning
   - Supports JSON, YAML, TEXT, and BINARY content types
   - Namespace-based organization
   - Tag-based categorization
   - Optional encryption support

2. **FeatureFlag** - Feature flag with advanced targeting
   - Targeting rules (attribute-based evaluation)
   - Rollout percentages (consistent hashing)
   - Tenant overrides
   - Environment overrides
   - Expiration support

3. **Configuration** - Service configuration with schema validation
   - Environment-specific configs (dev/staging/production)
   - JSON schema validation
   - Secret references for sensitive values
   - Activation/deactivation support
   - Effective date ranges

## Getting Started

### Prerequisites

- Python 3.12+
- PostgreSQL 14+
- Redis 7+

### Installation

```bash
cd services/metastore-service
poetry install

# Set up environment variables
cp .env.example .env

# Run database migrations
poetry run alembic upgrade head

# Start the service
poetry run uvicorn metastore_service.main:app --reload --port 8002
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://postgres:postgres@localhost:5432/metastore_db` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/1` |
| `APP_ENV` | Environment (development/staging/production) | `development` |
| `APP_PORT` | HTTP port | `8002` |
| `LOG_LEVEL` | Logging level | `INFO` |

## API Endpoints

### Health Checks

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Basic health check |
| GET | `/health/live` | Kubernetes liveness probe |
| GET | `/health/ready` | Kubernetes readiness probe |

### Metadata API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/metadata` | Create metadata entry |
| GET | `/api/v1/metadata` | List metadata entries |
| GET | `/api/v1/metadata/{id}` | Get metadata by ID |
| GET | `/api/v1/metadata/key/{key}` | Get metadata by key |
| PUT | `/api/v1/metadata/{id}` | Update metadata |
| DELETE | `/api/v1/metadata/{id}` | Delete metadata |
| GET | `/api/v1/metadata/{id}/versions` | Get version history |
| POST | `/api/v1/metadata/{id}/rollback/{version}` | Rollback to version |

### Feature Flags API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/feature-flags` | Create feature flag |
| GET | `/api/v1/feature-flags` | List feature flags |
| GET | `/api/v1/feature-flags/{id}` | Get flag by ID |
| GET | `/api/v1/feature-flags/name/{name}` | Get flag by name |
| PUT | `/api/v1/feature-flags/{id}` | Update feature flag |
| DELETE | `/api/v1/feature-flags/{id}` | Delete feature flag |
| POST | `/api/v1/feature-flags/evaluate` | Evaluate single flag |
| POST | `/api/v1/feature-flags/evaluate/bulk` | Evaluate multiple flags |
| POST | `/api/v1/feature-flags/{id}/enable` | Enable flag |
| POST | `/api/v1/feature-flags/{id}/disable` | Disable flag |
| POST | `/api/v1/feature-flags/{id}/rollout` | Set rollout percentage |

### Configuration API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/configurations` | Create configuration |
| GET | `/api/v1/configurations/{id}` | Get configuration by ID |
| GET | `/api/v1/configurations/service/{service_id}` | List by service |
| GET | `/api/v1/configurations/effective/{service_id}` | Get effective config |
| PUT | `/api/v1/configurations/{id}` | Update configuration |
| DELETE | `/api/v1/configurations/{id}` | Delete configuration |
| POST | `/api/v1/configurations/{id}/activate` | Activate config |
| POST | `/api/v1/configurations/{id}/deactivate` | Deactivate config |
| GET | `/api/v1/configurations/{id}/versions` | Get version history |
| POST | `/api/v1/configurations/{id}/rollback/{version}` | Rollback to version |

## Examples

### Create a Metadata Entry

```bash
curl -X POST http://localhost:8002/api/v1/metadata \
  -H "Content-Type: application/json" \
  -d '{
    "key": "app.database.pool_size",
    "namespace": "production",
    "value": 10,
    "content_type": "json",
    "tags": ["database", "performance"],
    "description": "Database connection pool size"
  }'
```

### Create a Feature Flag

```bash
curl -X POST http://localhost:8002/api/v1/feature-flags \
  -H "Content-Type: application/json" \
  -d '{
    "name": "new-checkout-flow",
    "description": "Enable new checkout experience",
    "enabled": true,
    "default_value": false,
    "rollout_percentage": 25,
    "tags": ["checkout", "experiment"]
  }'
```

### Evaluate Feature Flag

```bash
curl -X POST http://localhost:8002/api/v1/feature-flags/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "name": "new-checkout-flow",
    "context": {"user_id": "user-123", "country": "US"},
    "tenant_id": "premium-tenant",
    "environment": "production"
  }'
```

### Create Service Configuration

```bash
curl -X POST http://localhost:8002/api/v1/configurations \
  -H "Content-Type: application/json" \
  -d '{
    "service_id": "order-service",
    "name": "database",
    "environment": "production",
    "values": {
      "host": "db.example.com",
      "port": 5432,
      "pool_size": 20,
      "ssl_enabled": true
    },
    "description": "Database configuration for order service"
  }'
```

## Testing

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=metastore_service --cov-report=html

# Run specific test file
poetry run pytest tests/unit/domain/test_entities.py -v
```

## Development

### Code Quality

```bash
# Format code
poetry run ruff format src tests

# Lint code
poetry run ruff check src tests --fix

# Type checking
poetry run mypy src
```

### Database Migrations

```bash
# Generate migration
poetry run alembic revision --autogenerate -m "Description"

# Apply migrations
poetry run alembic upgrade head

# Rollback
poetry run alembic downgrade -1
```

## License

MIT License
