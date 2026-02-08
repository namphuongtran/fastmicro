# Worker Service

Background task processing service using [ARQ](https://arq-docs.helpmanual.io/) (async Redis queue).

## Architecture

```
src/worker_service/
├── configs/     # Pydantic Settings
├── main.py      # Health API (for K8s probes)
├── worker.py    # ARQ worker entry point + settings
└── tasks/       # Task function definitions
    ├── outbox_relay.py   # Transactional outbox polling
    └── cleanup.py        # Expired session cleanup
```

## Running

```bash
# ARQ worker (task processing)
cd services/worker-service
arq worker_service.worker.WorkerSettings

# Health API (for K8s liveness/readiness)
uv run uvicorn worker_service.main:create_app --port 8005 --factory
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `WORKER_SERVICE_REDIS_URL` | `redis://localhost:6379/4` | ARQ queue backend |
| `WORKER_SERVICE_DATABASE_URL` | `postgresql+asyncpg://...` | PostgreSQL |
| `WORKER_SERVICE_RABBITMQ_URL` | `amqp://guest:guest@localhost/` | RabbitMQ |
| `WORKER_SERVICE_ARQ_MAX_JOBS` | `10` | Concurrent job limit |
| `WORKER_SERVICE_ARQ_JOB_TIMEOUT_SECONDS` | `300` | Job timeout |
| `WORKER_SERVICE_OTLP_ENDPOINT` | `http://localhost:4317` | OTLP collector |

## Tasks

| Task | Schedule | Description |
|------|----------|-------------|
| `process_outbox` | Every 15 min | Polls outbox table, publishes events |
| `cleanup_expired_sessions` | Daily 3 AM | Removes stale data |
