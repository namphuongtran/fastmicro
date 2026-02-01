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

from shared.config.app import AppSettings, PaginationSettings
from shared.config.auth import AuthSettings
from shared.config.base import (
    BaseServiceSettings,
    SettingsError,
    clear_settings_cache,
    get_settings,
)
from shared.config.caching import (
    CacheBackend,
    CacheClusterSettings,
    CacheStrategy,
    CacheWarmingSettings,
    CachingSettings,
    DatabaseCacheSettings,
    MemcachedCacheSettings,
    MemoryCacheSettings,
    RedisCacheSettings,
)
from shared.config.database import DatabaseSettings, DatabaseType
from shared.config.logging import (
    ConsoleLoggingSettings,
    ElasticsearchLoggingSettings,
    FileLoggingSettings,
    LogFormat,
    LoggingSettings,
    LogLevel,
    OpenTelemetrySettings,
    RequestLoggingSettings,
    SentrySettings,
)
from shared.config.redis import RedisSettings
from shared.config.security import (
    CookieSettings,
    CORSSettings,
    CryptoSettings,
    RateLimitSettings,
    SameSitePolicy,
    SecurityHeadersSettings,
    SecuritySettings,
    SessionSettings,
    TLSSettings,
)

__all__ = [
    # Base
    "BaseServiceSettings",
    "SettingsError",
    "get_settings",
    "clear_settings_cache",
    # App
    "AppSettings",
    "PaginationSettings",
    # Auth
    "AuthSettings",
    # Caching
    "CachingSettings",
    "CacheBackend",
    "CacheStrategy",
    "RedisCacheSettings",
    "MemcachedCacheSettings",
    "MemoryCacheSettings",
    "DatabaseCacheSettings",
    "CacheWarmingSettings",
    "CacheClusterSettings",
    # Database
    "DatabaseSettings",
    "DatabaseType",
    # Logging
    "LoggingSettings",
    "LogFormat",
    "LogLevel",
    "ConsoleLoggingSettings",
    "FileLoggingSettings",
    "SentrySettings",
    "OpenTelemetrySettings",
    "ElasticsearchLoggingSettings",
    "RequestLoggingSettings",
    # Redis
    "RedisSettings",
    # Security
    "SecuritySettings",
    "CORSSettings",
    "RateLimitSettings",
    "SecurityHeadersSettings",
    "CookieSettings",
    "SessionSettings",
    "CryptoSettings",
    "TLSSettings",
    "SameSitePolicy",
]
