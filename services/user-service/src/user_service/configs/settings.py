"""User Service configuration settings."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class UserServiceSettings(BaseSettings):
    """User Service settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="USER_SERVICE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    service_name: str = Field(default="user-service", description="Service name")
    port: int = Field(default=8003, ge=1, le=65535, description="HTTP port")
    debug: bool = Field(default=False, description="Debug mode")
    log_level: str = Field(default="INFO", description="Log level")

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://admin:admin@localhost:5432/user_db",
        description="Async database URL",
    )
    db_pool_size: int = Field(default=10, ge=1, description="Connection pool size")
    db_max_overflow: int = Field(default=5, ge=0, description="Max overflow connections")

    # Redis
    redis_url: str = Field(
        default="redis://localhost:6379/2",
        description="Redis URL for caching",
    )

    # Messaging
    rabbitmq_url: str = Field(
        default="amqp://guest:guest@localhost:5672/",
        description="RabbitMQ connection URL",
    )

    # Observability
    otlp_endpoint: str = Field(
        default="http://localhost:4317",
        description="OpenTelemetry collector endpoint",
    )


@lru_cache(maxsize=1)
def get_settings() -> UserServiceSettings:
    """Get cached settings instance."""
    return UserServiceSettings()
