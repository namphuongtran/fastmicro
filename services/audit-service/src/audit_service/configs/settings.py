"""
Configuration settings for Audit Service.

Uses Pydantic Settings for configuration management with support for
environment variables and .env files.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings with environment variable support.

    All settings can be overridden via environment variables.
    Environment variables should be prefixed with the service name
    or use the exact field name.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application Settings
    service_name: str = Field(default="audit-service", description="Service name for observability")
    app_env: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Application environment",
    )
    app_port: int = Field(default=8001, ge=1, le=65535, description="Application port")
    app_host: str = Field(default="0.0.0.0", description="Application host")
    debug: bool = Field(default=False, description="Debug mode")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level",
    )

    # CORS Settings
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        description="Allowed CORS origins",
    )

    # Database Settings
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/audit_db",
        description="PostgreSQL connection string",
    )
    database_pool_size: int = Field(default=5, ge=1, le=100, description="Database pool size")
    database_max_overflow: int = Field(
        default=10, ge=0, le=100, description="Database max overflow"
    )
    database_pool_timeout: int = Field(
        default=30, ge=1, description="Database pool timeout in seconds"
    )

    # Redis Settings
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection string",
    )
    redis_prefix: str = Field(default="audit:", description="Redis key prefix")

    # RabbitMQ Settings
    rabbitmq_url: str = Field(
        default="amqp://guest:guest@localhost:5672/",
        description="RabbitMQ connection string",
    )
    rabbitmq_exchange: str = Field(default="audit_events", description="RabbitMQ exchange name")
    rabbitmq_queue: str = Field(default="audit_queue", description="RabbitMQ queue name")

    # OpenTelemetry Settings
    otel_enabled: bool = Field(default=True, description="Enable OpenTelemetry")
    otel_exporter_endpoint: str = Field(
        default="http://localhost:4317",
        description="OTLP exporter endpoint",
    )
    otel_service_namespace: str = Field(default="fastmicro", description="Service namespace")

    # Audit Settings
    audit_retention_days: int = Field(
        default=365,
        ge=30,
        description="Audit log retention in days",
    )
    audit_batch_size: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Batch size for bulk operations",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        """Parse CORS origins from comma-separated string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.app_env == "development"


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Uses LRU cache to ensure settings are only loaded once.

    Returns:
        Settings: Application settings instance.
    """
    return Settings()
