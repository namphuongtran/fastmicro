"""Worker service configuration."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings


class WorkerServiceSettings(BaseSettings):
    """Worker service configuration from environment."""

    model_config = {"env_prefix": "WORKER_SERVICE_"}

    service_name: str = "worker-service"
    port: int = 8005
    debug: bool = False

    # Redis (ARQ queue backend)
    redis_url: str = "redis://localhost:6379/4"

    # Database (for tasks that need DB access)
    database_url: str = (
        "postgresql+asyncpg://fastmicro:fastmicro@localhost:5432/fastmicro_workers"
    )

    # RabbitMQ (for consuming events that trigger tasks)
    rabbitmq_url: str = "amqp://guest:guest@localhost/"

    # ARQ settings
    arq_max_jobs: int = 10
    arq_job_timeout_seconds: int = 300
    arq_keep_result_seconds: int = 3600
    arq_retry_jobs: bool = True
    arq_max_tries: int = 3

    # Observability
    otlp_endpoint: str = "http://localhost:4317"


@lru_cache
def get_settings() -> WorkerServiceSettings:
    """Cached settings singleton."""
    return WorkerServiceSettings()
