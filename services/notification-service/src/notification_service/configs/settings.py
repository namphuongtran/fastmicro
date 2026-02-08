"""Notification service configuration."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings


class NotificationServiceSettings(BaseSettings):
    """Notification service configuration from environment."""

    model_config = {"env_prefix": "NOTIFICATION_SERVICE_"}

    service_name: str = "notification-service"
    port: int = 8004
    debug: bool = False
    log_level: str = "INFO"

    # RabbitMQ
    rabbitmq_url: str = "amqp://guest:guest@localhost/"

    # Redis (for deduplication / rate limiting)
    redis_url: str = "redis://localhost:6379/3"

    # SMTP
    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_email: str = "noreply@example.com"
    smtp_use_tls: bool = True

    # Webhook
    webhook_timeout_seconds: int = 10
    webhook_max_retries: int = 3

    # Observability
    otlp_endpoint: str = "http://localhost:4317"


@lru_cache
def get_settings() -> NotificationServiceSettings:
    """Cached settings singleton."""
    return NotificationServiceSettings()
