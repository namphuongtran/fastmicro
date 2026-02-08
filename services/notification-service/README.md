# Notification Service

Event-driven notification delivery service. Consumes domain events from RabbitMQ and dispatches notifications through configured channels (email, SMS, push, webhook).

## Architecture

```
src/notification_service/
├── application/      # Event dispatching logic
├── configs/          # Pydantic Settings
├── domain/           # Channel abstractions, notification models
└── infrastructure/   # Concrete channel senders (SMTP, webhook, etc.)
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET    | `/health/live` | Liveness probe |
| GET    | `/health/ready` | Readiness probe |

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `NOTIFICATION_SERVICE_SERVICE_NAME` | `notification-service` | Service name |
| `NOTIFICATION_SERVICE_PORT` | `8004` | HTTP port |
| `NOTIFICATION_SERVICE_RABBITMQ_URL` | `amqp://guest:guest@localhost/` | RabbitMQ |
| `NOTIFICATION_SERVICE_REDIS_URL` | `redis://localhost:6379/3` | Redis |
| `NOTIFICATION_SERVICE_SMTP_HOST` | `localhost` | SMTP server |
| `NOTIFICATION_SERVICE_OTLP_ENDPOINT` | `http://localhost:4317` | OTLP collector |
