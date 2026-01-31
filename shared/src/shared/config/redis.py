"""Redis configuration settings.

This module provides Redis-specific settings with support
for standalone and cluster modes, SSL, and connection pooling.
"""

from __future__ import annotations

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class RedisSettings(BaseSettings):
    """Redis connection settings.

    Supports standalone Redis and Redis Cluster with SSL
    and connection pooling options.

    Attributes:
        host: Redis server host.
        port: Redis server port.
        db: Redis database number (0-15).
        username: Redis username (Redis 6+ ACL).
        password: Redis password.
        ssl: Enable SSL/TLS connection.
        max_connections: Maximum pool connections.
        socket_timeout: Socket operation timeout.
        socket_connect_timeout: Socket connection timeout.
        key_prefix: Prefix for all keys (namespacing).
        default_ttl: Default TTL for cache entries.
        cluster_mode: Enable Redis Cluster mode.

    Example:
        >>> settings = RedisSettings()
        >>> print(settings.url)
        redis://localhost:6379/0
    """

    model_config = SettingsConfigDict(
        env_prefix="REDIS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Connection settings
    host: str = Field(default="localhost", description="Redis host")
    port: int = Field(default=6379, ge=1, le=65535, description="Redis port")
    db: int = Field(default=0, ge=0, le=15, description="Redis database number")
    username: str | None = Field(
        default=None,
        description="Redis username (Redis 6+ ACL)",
    )
    password: SecretStr | None = Field(default=None, description="Redis password")

    # SSL/TLS
    ssl: bool = Field(default=False, description="Enable SSL/TLS")

    # Connection pool settings
    max_connections: int = Field(
        default=10,
        ge=1,
        description="Maximum pool connections",
    )
    socket_timeout: float = Field(
        default=5.0,
        ge=0.1,
        description="Socket operation timeout in seconds",
    )
    socket_connect_timeout: float = Field(
        default=5.0,
        ge=0.1,
        description="Socket connection timeout in seconds",
    )

    # Caching settings
    key_prefix: str = Field(
        default="",
        description="Prefix for all keys (namespacing)",
    )
    default_ttl: int | None = Field(
        default=None,
        ge=1,
        description="Default TTL for cache entries in seconds",
    )

    # Cluster mode
    cluster_mode: bool = Field(
        default=False,
        description="Enable Redis Cluster mode",
    )

    @property
    def url(self) -> str:
        """Generate Redis connection URL.

        Returns:
            Redis connection URL with all authentication details.
        """
        scheme = "rediss" if self.ssl else "redis"

        # Build authentication part
        auth = ""
        if self.username and self.password:
            auth = f"{self.username}:{self.password.get_secret_value()}@"
        elif self.password:
            auth = f":{self.password.get_secret_value()}@"

        return f"{scheme}://{auth}{self.host}:{self.port}/{self.db}"
