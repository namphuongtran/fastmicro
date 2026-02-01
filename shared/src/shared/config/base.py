"""Base configuration settings.

This module provides the base settings class and utilities
for all microservice configurations.
"""

from __future__ import annotations

import threading
from typing import Any, TypeVar

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

T = TypeVar("T", bound=BaseSettings)

# Global settings cache
_settings_cache: dict[type, Any] = {}
_cache_lock = threading.Lock()


class SettingsError(Exception):
    """Raised when settings configuration is invalid.

    Attributes:
        field: The field that caused the error, if applicable.
    """

    def __init__(self, message: str, field: str | None = None) -> None:
        self.field = field
        if field:
            message = f"{field}: {message}"
        super().__init__(message)


class BaseServiceSettings(BaseSettings):
    """Base settings for all microservices.

    This class provides common configuration options shared across
    all services. Extend this class to add service-specific settings.

    Attributes:
        app_name: Name of the application/service.
        app_version: Version of the application.
        debug: Enable debug mode.
        environment: Current environment (development, staging, production).
        host: Server host address.
        port: Server port number.
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        cors_origins: Allowed CORS origins.
        allowed_hosts: Allowed host headers.

    Example:
        >>> class MyServiceSettings(BaseServiceSettings):
        ...     database_url: str
        ...     api_key: SecretStr
        ...
        >>> settings = MyServiceSettings()
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Application settings
    app_name: str = Field(default="microservice", description="Application name")
    app_version: str = Field(default="0.1.0", description="Application version")
    debug: bool = Field(default=False, description="Enable debug mode")
    environment: str = Field(
        default="development",
        description="Environment (development, staging, production, testing)",
    )

    # Server settings
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, ge=1, le=65535, description="Server port")

    # Logging
    log_level: str = Field(
        default="INFO",
        description="Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )

    # Security
    cors_origins: list[str] = Field(
        default=["*"],
        description="Allowed CORS origins",
    )
    allowed_hosts: list[str] = Field(
        default=["*"],
        description="Allowed host headers",
    )

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment.lower() == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"

    @property
    def is_staging(self) -> bool:
        """Check if running in staging environment."""
        return self.environment.lower() == "staging"

    @property
    def is_testing(self) -> bool:
        """Check if running in testing environment."""
        return self.environment.lower() == "testing"


def get_settings(settings_class: type[T]) -> T:
    """Get cached settings instance.

    This function caches settings instances by class type to avoid
    re-parsing environment variables on every access.

    Args:
        settings_class: The settings class to instantiate.

    Returns:
        Cached instance of the settings class.

    Example:
        >>> settings = get_settings(BaseServiceSettings)
        >>> print(settings.app_name)
    """
    with _cache_lock:
        if settings_class not in _settings_cache:
            _settings_cache[settings_class] = settings_class()
        return _settings_cache[settings_class]


def clear_settings_cache() -> None:
    """Clear the settings cache.

    Call this function when you need to reload settings,
    for example after modifying environment variables in tests.
    """
    with _cache_lock:
        _settings_cache.clear()
