"""Logging configuration settings.

This module provides comprehensive logging settings with support
for multiple outputs (console, file, Sentry, OpenTelemetry, Elasticsearch).
"""

from __future__ import annotations

from enum import Enum

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LogFormat(str, Enum):
    """Supported log formats."""

    JSON = "json"
    TEXT = "text"
    STRUCTURED = "structured"


class LogLevel(str, Enum):
    """Standard log levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ConsoleLoggingSettings(BaseSettings):
    """Console logging output settings.

    Attributes:
        enabled: Enable console logging.
        format: Log output format.
        colorize: Enable colorized output.
    """

    model_config = SettingsConfigDict(
        env_prefix="LOG_CONSOLE_",
        extra="ignore",
        case_sensitive=False,
    )

    enabled: bool = Field(default=True, description="Enable console logging")
    format: LogFormat = Field(default=LogFormat.TEXT, description="Log output format")
    colorize: bool = Field(default=True, description="Enable colorized output")


class FileLoggingSettings(BaseSettings):
    """File logging output settings.

    Attributes:
        enabled: Enable file logging.
        path: Log file path.
        format: Log output format.
        max_size_mb: Maximum file size before rotation.
        backup_count: Number of backup files to keep.
        rotation: Enable log rotation.
    """

    model_config = SettingsConfigDict(
        env_prefix="LOG_FILE_",
        extra="ignore",
        case_sensitive=False,
    )

    enabled: bool = Field(default=False, description="Enable file logging")
    path: str = Field(default="logs/app.log", description="Log file path")
    format: LogFormat = Field(default=LogFormat.JSON, description="Log output format")
    max_size_mb: int = Field(
        default=10,
        ge=1,
        description="Maximum file size in MB before rotation",
    )
    backup_count: int = Field(
        default=5,
        ge=0,
        description="Number of backup files to keep",
    )
    rotation: bool = Field(default=True, description="Enable log rotation")


class SentrySettings(BaseSettings):
    """Sentry error tracking settings.

    Attributes:
        enabled: Enable Sentry integration.
        dsn: Sentry DSN.
        environment: Environment name for Sentry.
        traces_sample_rate: Tracing sample rate (0.0-1.0).
        profiles_sample_rate: Profiling sample rate (0.0-1.0).
        send_default_pii: Include PII in error reports.
    """

    model_config = SettingsConfigDict(
        env_prefix="SENTRY_",
        extra="ignore",
        case_sensitive=False,
    )

    enabled: bool = Field(default=False, description="Enable Sentry integration")
    dsn: SecretStr | None = Field(default=None, description="Sentry DSN")
    environment: str = Field(
        default="development",
        description="Environment name",
    )
    traces_sample_rate: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Tracing sample rate",
    )
    profiles_sample_rate: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Profiling sample rate",
    )
    send_default_pii: bool = Field(
        default=False,
        description="Include PII in error reports",
    )


class OpenTelemetrySettings(BaseSettings):
    """OpenTelemetry observability settings.

    Attributes:
        enabled: Enable OpenTelemetry integration.
        service_name: Service name for traces.
        endpoint: OTLP exporter endpoint.
        insecure: Use insecure connection.
        traces_enabled: Enable distributed tracing.
        metrics_enabled: Enable metrics collection.
        logs_enabled: Enable log export.
    """

    model_config = SettingsConfigDict(
        env_prefix="OTEL_",
        extra="ignore",
        case_sensitive=False,
    )

    enabled: bool = Field(default=False, description="Enable OpenTelemetry")
    service_name: str = Field(
        default="microservice",
        description="Service name for traces",
    )
    endpoint: str = Field(
        default="http://localhost:4317",
        description="OTLP exporter endpoint",
    )
    insecure: bool = Field(default=True, description="Use insecure connection")
    traces_enabled: bool = Field(default=True, description="Enable distributed tracing")
    metrics_enabled: bool = Field(default=True, description="Enable metrics collection")
    logs_enabled: bool = Field(default=True, description="Enable log export")


class ElasticsearchLoggingSettings(BaseSettings):
    """Elasticsearch logging output settings.

    Attributes:
        enabled: Enable Elasticsearch logging.
        hosts: Elasticsearch hosts.
        index_prefix: Index name prefix.
        username: Elasticsearch username.
        password: Elasticsearch password.
        ssl_verify: Verify SSL certificates.
    """

    model_config = SettingsConfigDict(
        env_prefix="LOG_ES_",
        extra="ignore",
        case_sensitive=False,
    )

    enabled: bool = Field(default=False, description="Enable Elasticsearch logging")
    hosts: list[str] = Field(
        default=["http://localhost:9200"],
        description="Elasticsearch hosts",
    )
    index_prefix: str = Field(
        default="logs",
        description="Index name prefix",
    )
    username: str | None = Field(default=None, description="Elasticsearch username")
    password: SecretStr | None = Field(
        default=None,
        description="Elasticsearch password",
    )
    ssl_verify: bool = Field(default=True, description="Verify SSL certificates")


class RequestLoggingSettings(BaseSettings):
    """HTTP request/response logging settings.

    Attributes:
        enabled: Enable request logging.
        log_request_headers: Log request headers.
        log_request_body: Log request body.
        log_response_headers: Log response headers.
        log_response_body: Log response body.
        exclude_paths: Paths to exclude from logging.
        mask_headers: Headers to mask in logs.
    """

    model_config = SettingsConfigDict(
        env_prefix="LOG_REQUEST_",
        extra="ignore",
        case_sensitive=False,
    )

    enabled: bool = Field(default=True, description="Enable request logging")
    log_request_headers: bool = Field(default=False, description="Log request headers")
    log_request_body: bool = Field(default=False, description="Log request body")
    log_response_headers: bool = Field(
        default=False,
        description="Log response headers",
    )
    log_response_body: bool = Field(default=False, description="Log response body")
    exclude_paths: list[str] = Field(
        default=["/health", "/healthz", "/ready", "/metrics"],
        description="Paths to exclude from logging",
    )
    mask_headers: list[str] = Field(
        default=["Authorization", "X-API-Key", "Cookie"],
        description="Headers to mask in logs",
    )


class LoggingSettings(BaseSettings):
    """Comprehensive logging configuration.

    Aggregates all logging-related settings into a single
    configuration object.

    Attributes:
        level: Global log level.
        format: Default log format.
        console: Console output settings.
        file: File output settings.
        sentry: Sentry error tracking settings.
        otel: OpenTelemetry settings.
        elasticsearch: Elasticsearch output settings.
        request: HTTP request logging settings.

    Example:
        >>> settings = LoggingSettings()
        >>> print(settings.level)
        INFO
    """

    model_config = SettingsConfigDict(
        env_prefix="LOG_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Global settings
    level: LogLevel = Field(default=LogLevel.INFO, description="Global log level")
    format: LogFormat = Field(default=LogFormat.TEXT, description="Default log format")

    # Output configurations
    console: ConsoleLoggingSettings = Field(
        default_factory=ConsoleLoggingSettings,
        description="Console output settings",
    )
    file: FileLoggingSettings = Field(
        default_factory=FileLoggingSettings,
        description="File output settings",
    )
    sentry: SentrySettings = Field(
        default_factory=SentrySettings,
        description="Sentry error tracking",
    )
    otel: OpenTelemetrySettings = Field(
        default_factory=OpenTelemetrySettings,
        description="OpenTelemetry settings",
    )
    elasticsearch: ElasticsearchLoggingSettings = Field(
        default_factory=ElasticsearchLoggingSettings,
        description="Elasticsearch output",
    )
    request: RequestLoggingSettings = Field(
        default_factory=RequestLoggingSettings,
        description="Request logging settings",
    )

    @field_validator("level", mode="before")
    @classmethod
    def validate_level(cls, v: str | LogLevel) -> LogLevel:
        """Convert string to LogLevel enum."""
        if isinstance(v, str):
            return LogLevel(v.upper())
        return v
