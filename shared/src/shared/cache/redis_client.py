"""Async Redis client for caching.

This module provides an async Redis client with support for:
- Basic operations (get, set, delete)
- Hash operations
- TTL management
- Health checks
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Self

import redis.asyncio as redis


class CacheError(Exception):
    """Base exception for cache errors."""

    pass


class RedisConnectionError(CacheError):
    """Error when Redis connection fails."""

    pass


@dataclass
class RedisConfig:
    """Configuration for Redis connection.

    Attributes:
        host: Redis host.
        port: Redis port.
        db: Redis database number.
        password: Redis password.
        ssl: Use SSL connection.
        socket_timeout: Socket timeout in seconds.
        decode_responses: Decode byte responses.
    """

    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: str | None = None
    ssl: bool = False
    socket_timeout: float = 5.0
    decode_responses: bool = False

    def build_url(self) -> str:
        """Build Redis connection URL.

        Returns:
            Redis connection URL string.
        """
        scheme = "rediss" if self.ssl else "redis"
        auth = f":{self.password}@" if self.password else ""
        return f"{scheme}://{auth}{self.host}:{self.port}/{self.db}"


class AsyncRedisClient:
    """Async Redis client for caching operations.

    Provides high-level caching operations with JSON serialization.

    Example:
        >>> config = RedisConfig(host="localhost", port=6379)
        >>> client = AsyncRedisClient(config)
        >>> await client.connect()
        >>> await client.set("user:1", {"name": "John"}, ttl=300)
        >>> user = await client.get("user:1")
    """

    def __init__(self, config: RedisConfig) -> None:
        """Initialize Redis client.

        Args:
            config: Redis configuration.
        """
        self._config = config
        self._redis: redis.Redis | None = None

    @property
    def config(self) -> RedisConfig:
        """Get Redis configuration."""
        return self._config

    async def connect(self) -> None:
        """Establish Redis connection."""
        try:
            self._redis = redis.Redis(
                host=self._config.host,
                port=self._config.port,
                db=self._config.db,
                password=self._config.password,
                ssl=self._config.ssl,
                socket_timeout=self._config.socket_timeout,
            )
        except Exception as e:
            raise RedisConnectionError(f"Failed to connect to Redis: {e}") from e

    async def close(self) -> None:
        """Close Redis connection."""
        if self._redis is not None:
            await self._redis.close()

    async def __aenter__(self) -> Self:
        """Enter async context."""
        await self.connect()
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Exit async context."""
        await self.close()

    def _ensure_connected(self) -> redis.Redis:
        """Ensure Redis is connected.

        Returns:
            Redis client instance.

        Raises:
            RedisConnectionError: If not connected.
        """
        if self._redis is None:
            raise RedisConnectionError("Redis client not connected")
        return self._redis

    def _serialize(self, value: Any) -> str:
        """Serialize value to JSON.

        Args:
            value: Value to serialize.

        Returns:
            JSON string.
        """
        return json.dumps(value)

    def _deserialize(self, value: bytes | str | None) -> Any:
        """Deserialize JSON value.

        Args:
            value: JSON bytes/string to deserialize.

        Returns:
            Deserialized Python object.
        """
        if value is None:
            return None
        if isinstance(value, bytes):
            value = value.decode("utf-8")
        return json.loads(value)

    # Basic operations

    async def get(self, key: str) -> Any:
        """Get value by key.

        Args:
            key: Cache key.

        Returns:
            Cached value or None if not found.
        """
        client = self._ensure_connected()
        value = await client.get(key)
        return self._deserialize(value)

    async def set(
        self,
        key: str,
        value: Any,
        *,
        ttl: int | None = None,
    ) -> bool:
        """Set value with optional TTL.

        Args:
            key: Cache key.
            value: Value to cache.
            ttl: Time to live in seconds.

        Returns:
            True if set successfully.
        """
        client = self._ensure_connected()
        serialized = self._serialize(value)
        result = await client.set(key, serialized, ex=ttl)
        return bool(result)

    async def delete(self, key: str) -> bool:
        """Delete value by key.

        Args:
            key: Cache key.

        Returns:
            True if key was deleted.
        """
        client = self._ensure_connected()
        result = await client.delete(key)
        return result > 0

    async def exists(self, key: str) -> bool:
        """Check if key exists.

        Args:
            key: Cache key.

        Returns:
            True if key exists.
        """
        client = self._ensure_connected()
        result = await client.exists(key)
        return result > 0

    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration on key.

        Args:
            key: Cache key.
            seconds: Time to live in seconds.

        Returns:
            True if expiration was set.
        """
        client = self._ensure_connected()
        result = await client.expire(key, seconds)
        return bool(result)

    async def ttl(self, key: str) -> int:
        """Get time to live for key.

        Args:
            key: Cache key.

        Returns:
            TTL in seconds, -1 if no expiry, -2 if key doesn't exist.
        """
        client = self._ensure_connected()
        return await client.ttl(key)

    # Counter operations

    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment value by amount.

        Args:
            key: Cache key.
            amount: Amount to increment.

        Returns:
            New value after increment.
        """
        client = self._ensure_connected()
        return await client.incr(key, amount)

    async def decrement(self, key: str, amount: int = 1) -> int:
        """Decrement value by amount.

        Args:
            key: Cache key.
            amount: Amount to decrement.

        Returns:
            New value after decrement.
        """
        client = self._ensure_connected()
        return await client.decr(key, amount)

    # Hash operations

    async def hset(self, name: str, key: str, value: Any) -> int:
        """Set hash field value.

        Args:
            name: Hash name.
            key: Field key.
            value: Field value.

        Returns:
            1 if field is new, 0 if updated.
        """
        client = self._ensure_connected()
        serialized = self._serialize(value)
        return await client.hset(name, key, serialized)

    async def hget(self, name: str, key: str) -> Any:
        """Get hash field value.

        Args:
            name: Hash name.
            key: Field key.

        Returns:
            Field value or None.
        """
        client = self._ensure_connected()
        value = await client.hget(name, key)
        return self._deserialize(value)

    async def hgetall(self, name: str) -> dict[str, Any]:
        """Get all hash fields.

        Args:
            name: Hash name.

        Returns:
            Dictionary of field values.
        """
        client = self._ensure_connected()
        raw = await client.hgetall(name)
        return {
            k.decode("utf-8") if isinstance(k, bytes) else k: self._deserialize(v)
            for k, v in raw.items()
        }

    async def hdel(self, name: str, key: str) -> int:
        """Delete hash field.

        Args:
            name: Hash name.
            key: Field key.

        Returns:
            Number of fields deleted.
        """
        client = self._ensure_connected()
        return await client.hdel(name, key)

    # Health check

    async def health_check(self) -> bool:
        """Check Redis connectivity.

        Returns:
            True if Redis is reachable.
        """
        try:
            client = self._ensure_connected()
            result = await client.ping()
            return bool(result)
        except Exception:
            return False
