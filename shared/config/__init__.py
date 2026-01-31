"""Configuration management package.

This package provides Pydantic-settings based configuration
for microservices with environment variable support.

Example:
    >>> from shared.config import BaseServiceSettings, DatabaseSettings
    >>> from shared.config import get_settings, clear_settings_cache
    >>> 
    >>> class MySettings(BaseServiceSettings):
    ...     custom_setting: str = "default"
    >>> 
    >>> settings = get_settings(MySettings)
"""

from __future__ import annotations

from shared.config.base import (
    BaseServiceSettings,
    SettingsError,
    get_settings,
    clear_settings_cache,
)
from shared.config.database import DatabaseSettings, DatabaseType
from shared.config.redis import RedisSettings
from shared.config.auth import AuthSettings

__all__ = [
    # Base
    "BaseServiceSettings",
    "SettingsError",
    "get_settings",
    "clear_settings_cache",
    # Database
    "DatabaseSettings",
    "DatabaseType",
    # Redis
    "RedisSettings",
    # Auth
    "AuthSettings",
]
