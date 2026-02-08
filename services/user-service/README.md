# User Service

User management microservice — profiles, preferences, and tenant management.

## Architecture

Clean Architecture (ADR-001):

```
src/user_service/
├── api/              # FastAPI routers, dependencies
├── application/      # DTOs, application services
├── configs/          # Pydantic Settings
├── domain/           # Entities, value objects, repository interfaces
│   ├── entities/     # User aggregate root + domain events
│   └── repositories/ # Abstract repository port
└── infrastructure/   # SQLAlchemy models, concrete repos
    ├── database/     # ORM models, session management
    └── repositories/ # PostgreSQL implementation
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST   | `/api/v1/users` | Create user |
| GET    | `/api/v1/users/{id}` | Get user by ID |
| PATCH  | `/api/v1/users/{id}` | Update user profile |
| POST   | `/api/v1/users/{id}/deactivate` | Deactivate user |
| DELETE | `/api/v1/users/{id}` | Delete user |
| GET    | `/api/v1/users` | List users (paginated) |
| GET    | `/health/live` | Liveness probe |
| GET    | `/health/ready` | Readiness probe |

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `USER_SERVICE_SERVICE_NAME` | `user-service` | Service name |
| `USER_SERVICE_PORT` | `8003` | HTTP port |
| `USER_SERVICE_DATABASE_URL` | `postgresql+asyncpg://...` | PostgreSQL connection |
| `USER_SERVICE_REDIS_URL` | `redis://localhost:6379/2` | Redis connection |
| `USER_SERVICE_RABBITMQ_URL` | `amqp://guest:guest@localhost/` | RabbitMQ connection |
| `USER_SERVICE_OTLP_ENDPOINT` | `http://localhost:4317` | OTLP collector |

## Running

```bash
# Development
cd services/user-service
uv run uvicorn user_service.main:app --reload --port 8003 --factory

# Docker
docker compose up user-service
```
