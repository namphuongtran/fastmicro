"""Application settings using pydantic-settings.

This module provides centralized configuration using the shared library's
DatabaseConfig and CacheConfig patterns for seamless integration with
AsyncDatabaseManager and TieredCacheManager.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

from shared.cache import CacheConfig
from shared.sqlalchemy_async import DatabaseConfig


class Settings(BaseSettings):
    """Application settings with environment variable binding.
    
    Settings are loaded from environment variables with optional .env file support.
    The class provides factory methods for creating shared library config objects.
    
    Example:
        >>> settings = get_settings()
        >>> db_config = settings.get_database_config()
        >>> cache_config = settings.get_cache_config()
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application settings
    app_name: str = "metastore-service"
    app_version: str = "0.1.0"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    log_level: str = "INFO"

    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1

    # Database settings
    database_driver: str = "postgresql+asyncpg"
    database_host: str = "localhost"
    database_port: int = 5432
    database_user: str = "postgres"
    database_password: str = ""
    database_name: str = "metastore"
    database_pool_size: int = 5
    database_max_overflow: int = 10
    database_pool_timeout: int = 30
    database_pool_recycle: int = 3600
    database_echo: bool = False

    # Redis/Cache settings
    redis_enabled: bool = True
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str | None = None
    redis_max_connections: int = 10

    # Cache TTL settings
    cache_memory_ttl: int = 300  # 5 minutes
    cache_redis_ttl: int = 3600  # 1 hour
    cache_memory_max_size: int = 1000

    # CORS settings
    cors_origins: list[str] = ["*"]
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = ["*"]
    cors_allow_headers: list[str] = ["*"]

    @property
    def database_url(self) -> str:
        """Build async database URL from components."""
        return (
            f"{self.database_driver}://"
            f"{self.database_user}:{self.database_password}@"
            f"{self.database_host}:{self.database_port}/"
            f"{self.database_name}"
        )

    @property
    def redis_url(self) -> str:
        """Build Redis URL from components."""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    def get_database_config(self) -> DatabaseConfig:
        """Create DatabaseConfig for AsyncDatabaseManager.
        
        Returns:
            DatabaseConfig instance configured from settings.
            
        Example:
            >>> settings = get_settings()
            >>> config = settings.get_database_config()
            >>> db = AsyncDatabaseManager(config)
        """
        return DatabaseConfig(
            url=self.database_url,
            pool_size=self.database_pool_size,
            max_overflow=self.database_max_overflow,
            pool_timeout=self.database_pool_timeout,
            pool_recycle=self.database_pool_recycle,
            echo=self.database_echo,
        )

    def get_cache_config(self) -> CacheConfig:
        """Create CacheConfig for TieredCacheManager.
        
        Returns:
            CacheConfig instance configured from settings.
            
        Example:
            >>> settings = get_settings()
            >>> config = settings.get_cache_config()
            >>> cache = await TieredCacheManager.create(config)
        """
        return CacheConfig(
            memory_enabled=True,
            memory_max_size=self.cache_memory_max_size,
            memory_default_ttl=self.cache_memory_ttl,
            redis_enabled=self.redis_enabled,
            redis_url=self.redis_url if self.redis_enabled else None,
            redis_host=self.redis_host,
            redis_port=self.redis_port,
            redis_db=self.redis_db,
            redis_password=self.redis_password,
            redis_default_ttl=self.cache_redis_ttl,
            redis_max_connections=self.redis_max_connections,
            namespace=self.app_name,
        )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.
    
    Uses LRU cache to ensure settings are loaded only once.
    
    Returns:
        Singleton Settings instance.
    """
    return Settings()

