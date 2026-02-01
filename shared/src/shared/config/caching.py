"""Caching configuration settings.

This module provides caching settings with support for multiple
backends (Redis, Memcached, in-memory, database).
"""

from __future__ import annotations

from enum import Enum

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class CacheBackend(str, Enum):
    """Supported cache backends."""

    REDIS = "redis"
    MEMCACHED = "memcached"
    MEMORY = "memory"
    DATABASE = "database"
    NONE = "none"


class CacheStrategy(str, Enum):
    """Cache eviction strategies."""

    LRU = "lru"
    LFU = "lfu"
    FIFO = "fifo"
    TTL = "ttl"


class RedisCacheSettings(BaseSettings):
    """Redis cache backend settings.

    Attributes:
        host: Redis server host.
        port: Redis server port.
        db: Redis database number.
        password: Redis password.
        ssl: Enable SSL/TLS.
        prefix: Key prefix for namespacing.
        socket_timeout: Socket operation timeout.
    """

    model_config = SettingsConfigDict(
        env_prefix="CACHE_REDIS_",
        extra="ignore",
        case_sensitive=False,
    )

    host: str = Field(default="localhost", description="Redis host")
    port: int = Field(default=6379, ge=1, le=65535, description="Redis port")
    db: int = Field(default=0, ge=0, le=15, description="Redis database number")
    password: SecretStr | None = Field(default=None, description="Redis password")
    ssl: bool = Field(default=False, description="Enable SSL/TLS")
    prefix: str = Field(default="cache:", description="Key prefix")
    socket_timeout: float = Field(
        default=5.0,
        ge=0.1,
        description="Socket timeout in seconds",
    )


class MemcachedCacheSettings(BaseSettings):
    """Memcached cache backend settings.

    Attributes:
        hosts: Memcached server hosts.
        connect_timeout: Connection timeout.
        timeout: Operation timeout.
        no_delay: Disable Nagle's algorithm.
    """

    model_config = SettingsConfigDict(
        env_prefix="CACHE_MEMCACHED_",
        extra="ignore",
        case_sensitive=False,
    )

    hosts: list[str] = Field(
        default=["localhost:11211"],
        description="Memcached hosts",
    )
    connect_timeout: float = Field(
        default=5.0,
        ge=0.1,
        description="Connection timeout in seconds",
    )
    timeout: float = Field(
        default=1.0,
        ge=0.1,
        description="Operation timeout in seconds",
    )
    no_delay: bool = Field(
        default=True,
        description="Disable Nagle's algorithm",
    )


class MemoryCacheSettings(BaseSettings):
    """In-memory cache backend settings.

    Attributes:
        max_size: Maximum number of cached items.
        ttl: Default time-to-live in seconds.
    """

    model_config = SettingsConfigDict(
        env_prefix="CACHE_MEMORY_",
        extra="ignore",
        case_sensitive=False,
    )

    max_size: int = Field(
        default=1000,
        ge=1,
        description="Maximum cached items",
    )
    ttl: int = Field(
        default=300,
        ge=1,
        description="Default TTL in seconds",
    )


class DatabaseCacheSettings(BaseSettings):
    """Database cache backend settings.

    Attributes:
        table_name: Cache table name.
        cleanup_interval: Expired entries cleanup interval.
    """

    model_config = SettingsConfigDict(
        env_prefix="CACHE_DB_",
        extra="ignore",
        case_sensitive=False,
    )

    table_name: str = Field(default="cache_entries", description="Cache table name")
    cleanup_interval: int = Field(
        default=3600,
        ge=60,
        description="Cleanup interval in seconds",
    )


class CacheWarmingSettings(BaseSettings):
    """Cache warming configuration.

    Attributes:
        enabled: Enable cache warming on startup.
        batch_size: Number of items to warm in each batch.
        delay_between_batches: Delay between batches in seconds.
    """

    model_config = SettingsConfigDict(
        env_prefix="CACHE_WARMING_",
        extra="ignore",
        case_sensitive=False,
    )

    enabled: bool = Field(default=False, description="Enable cache warming")
    batch_size: int = Field(default=100, ge=1, description="Batch size")
    delay_between_batches: float = Field(
        default=0.1,
        ge=0,
        description="Delay between batches in seconds",
    )


class CacheClusterSettings(BaseSettings):
    """Cache cluster configuration.

    Attributes:
        enabled: Enable cluster mode.
        nodes: Cluster node addresses.
        read_from_replicas: Read from replica nodes.
    """

    model_config = SettingsConfigDict(
        env_prefix="CACHE_CLUSTER_",
        extra="ignore",
        case_sensitive=False,
    )

    enabled: bool = Field(default=False, description="Enable cluster mode")
    nodes: list[str] = Field(default=[], description="Cluster node addresses")
    read_from_replicas: bool = Field(
        default=True,
        description="Read from replica nodes",
    )


class CachingSettings(BaseSettings):
    """Comprehensive caching configuration.

    Provides configuration for multiple cache backends and
    caching behavior options.

    Attributes:
        enabled: Enable caching.
        backend: Cache backend type.
        default_ttl: Default TTL for cache entries.
        strategy: Cache eviction strategy.
        prefix: Global key prefix.
        redis: Redis backend settings.
        memcached: Memcached backend settings.
        memory: In-memory backend settings.
        database: Database backend settings.
        warming: Cache warming settings.
        cluster: Cluster settings.

    Example:
        >>> settings = CachingSettings()
        >>> print(settings.backend)
        CacheBackend.REDIS
    """

    model_config = SettingsConfigDict(
        env_prefix="CACHE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # General settings
    enabled: bool = Field(default=True, description="Enable caching")
    backend: CacheBackend = Field(
        default=CacheBackend.REDIS,
        description="Cache backend type",
    )
    default_ttl: int = Field(
        default=300,
        ge=1,
        description="Default TTL in seconds",
    )
    strategy: CacheStrategy = Field(
        default=CacheStrategy.LRU,
        description="Cache eviction strategy",
    )
    prefix: str = Field(default="", description="Global key prefix")

    # Backend configurations
    redis: RedisCacheSettings = Field(
        default_factory=RedisCacheSettings,
        description="Redis backend settings",
    )
    memcached: MemcachedCacheSettings = Field(
        default_factory=MemcachedCacheSettings,
        description="Memcached backend settings",
    )
    memory: MemoryCacheSettings = Field(
        default_factory=MemoryCacheSettings,
        description="In-memory backend settings",
    )
    database: DatabaseCacheSettings = Field(
        default_factory=DatabaseCacheSettings,
        description="Database backend settings",
    )

    # Advanced settings
    warming: CacheWarmingSettings = Field(
        default_factory=CacheWarmingSettings,
        description="Cache warming settings",
    )
    cluster: CacheClusterSettings = Field(
        default_factory=CacheClusterSettings,
        description="Cluster settings",
    )
