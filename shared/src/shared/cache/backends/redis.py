"""Redis cache backend.

This module provides L2 (distributed) caching with:
- Cluster-wide shared state
- Persistence (optional)
- Pub/sub for cache invalidation
- JSON serialization by default

Best used as the second tier in a tiered cache setup.
"""

from __future__ import annotations

from typing import Any, TypeVar

from pydantic import BaseModel

from shared.cache.base import (
    AbstractCacheBackend,
    CacheConnectionError,
    CacheError,
    JsonSerializer,
    Serializer,
)

V = TypeVar("V")


class RedisConfig(BaseModel):
    """Redis connection configuration.

    Supports both URL-based and parameter-based configuration.

    Example:
        >>> # URL-based
        >>> config = RedisConfig(url="redis://localhost:6379/0")
        >>>
        >>> # Parameter-based
        >>> config = RedisConfig(host="localhost", port=6379, db=0)
    """

    url: str | None = None
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: str | None = None
    username: str | None = None
    ssl: bool = False
    socket_timeout: float = 5.0
    socket_connect_timeout: float = 5.0
    max_connections: int = 10
    decode_responses: bool = False  # We handle decoding ourselves

    def build_url(self) -> str:
        """Build Redis URL from parameters.

        Returns:
            Redis connection URL.
        """
        if self.url:
            return self.url

        scheme = "rediss" if self.ssl else "redis"
        auth = ""
        if self.username and self.password:
            auth = f"{self.username}:{self.password}@"
        elif self.password:
            auth = f":{self.password}@"

        return f"{scheme}://{auth}{self.host}:{self.port}/{self.db}"


class RedisCache(AbstractCacheBackend[V]):
    """Redis cache backend for distributed caching.

    Provides cluster-wide shared caching with optional persistence.
    Uses JSON serialization by default for debuggability.

    Features:
        - Distributed/shared state
        - TTL-based expiration
        - Atomic operations (increment, etc.)
        - Connection pooling
        - ~1-5ms access time

    Example:
        >>> config = RedisConfig(host="localhost", port=6379)
        >>> cache = RedisCache(config, namespace="myapp")
        >>> await cache.connect()
        >>> await cache.set("user:123", {"name": "John"}, ttl=3600)
        >>> await cache.get("user:123")
        {'name': 'John'}
        >>> await cache.close()

    Note:
        Call connect() before use, or use as async context manager.
    """

    def __init__(
        self,
        config: RedisConfig | None = None,
        *,
        namespace: str = "",
        default_ttl: int = 3600,
        serializer: Serializer[Any] | None = None,
    ) -> None:
        """Initialize Redis cache.

        Args:
            config: Redis connection configuration.
            namespace: Key namespace prefix.
            default_ttl: Default TTL in seconds.
            serializer: Value serializer (default: JsonSerializer).
        """
        super().__init__(
            namespace=namespace,
            default_ttl=default_ttl,
            serializer=serializer or JsonSerializer(),
        )
        self._config = config or RedisConfig()
        self._client: Any = None  # redis.asyncio.Redis
        self._connected = False

    @property
    def name(self) -> str:
        """Return backend name."""
        return "redis"

    @property
    def is_connected(self) -> bool:
        """Check if connected to Redis."""
        return self._connected and self._client is not None

    async def connect(self) -> None:
        """Connect to Redis.

        Raises:
            CacheConnectionError: If connection fails.
        """
        if self._connected:
            return

        try:
            import redis.asyncio as redis

            self._client = redis.from_url(
                self._config.build_url(),
                socket_timeout=self._config.socket_timeout,
                socket_connect_timeout=self._config.socket_connect_timeout,
                max_connections=self._config.max_connections,
                decode_responses=False,  # We handle decoding
            )

            # Test connection
            await self._client.ping()
            self._connected = True

        except ImportError as e:
            raise CacheConnectionError(
                "Redis library not installed. Install with: pip install redis",
                details={"error": str(e)},
            ) from e
        except Exception as e:
            raise CacheConnectionError(
                f"Failed to connect to Redis: {e}",
                details={"url": self._config.build_url()},
            ) from e

    async def _ensure_connected(self) -> None:
        """Ensure connection is established."""
        if not self._connected:
            await self.connect()

    async def get(self, key: str, default: V | None = None) -> V | None:
        """Get a value from Redis.

        Args:
            key: Cache key.
            default: Default value if key not found.

        Returns:
            Cached value or default.
        """
        await self._ensure_connected()
        full_key = self.build_key(key)

        try:
            data = await self._client.get(full_key)
            if data is None:
                return default
            return self._serializer.deserialize(data)
        except Exception:
            # Log but don't fail - return default
            return default

    async def set(
        self,
        key: str,
        value: V,
        ttl: int | None = None,
    ) -> bool:
        """Set a value in Redis.

        Args:
            key: Cache key.
            value: Value to cache.
            ttl: Time-to-live in seconds.

        Returns:
            True if successful.
        """
        await self._ensure_connected()
        full_key = self.build_key(key)
        effective_ttl = self._get_ttl(ttl)

        try:
            data = self._serializer.serialize(value)
            if effective_ttl:
                await self._client.setex(full_key, effective_ttl, data)
            else:
                await self._client.set(full_key, data)
            return True
        except Exception as e:
            raise CacheError(
                f"Failed to set key: {e}",
                details={"key": key},
            ) from e

    async def delete(self, key: str) -> bool:
        """Delete a key from Redis.

        Args:
            key: Cache key to delete.

        Returns:
            True if key was deleted, False if not found.
        """
        await self._ensure_connected()
        full_key = self.build_key(key)

        try:
            result = await self._client.delete(full_key)
            return result > 0
        except Exception as e:
            raise CacheError(
                f"Failed to delete key: {e}",
                details={"key": key},
            ) from e

    async def exists(self, key: str) -> bool:
        """Check if a key exists in Redis.

        Args:
            key: Cache key.

        Returns:
            True if key exists.
        """
        await self._ensure_connected()
        full_key = self.build_key(key)

        try:
            return await self._client.exists(full_key) > 0
        except Exception:
            return False

    async def clear(self, namespace: str | None = None) -> int:
        """Clear cache entries.

        Args:
            namespace: Namespace prefix to clear.
                      If None, clears current namespace.

        Returns:
            Number of keys cleared.
        """
        await self._ensure_connected()

        # Determine pattern to match
        ns = namespace if namespace is not None else self._namespace
        pattern = f"{ns}:*" if ns else "*"

        try:
            # Use SCAN for large datasets to avoid blocking
            count = 0
            cursor = 0
            while True:
                cursor, keys = await self._client.scan(
                    cursor=cursor,
                    match=pattern,
                    count=100,
                )
                if keys:
                    count += await self._client.delete(*keys)
                if cursor == 0:
                    break
            return count
        except Exception as e:
            raise CacheError(
                f"Failed to clear cache: {e}",
                details={"pattern": pattern},
            ) from e

    async def increment(self, key: str, delta: int = 1) -> int:
        """Increment a numeric value atomically.

        Args:
            key: Cache key.
            delta: Amount to increment (can be negative).

        Returns:
            New value after increment.
        """
        await self._ensure_connected()
        full_key = self.build_key(key)

        try:
            if delta >= 0:
                return await self._client.incrby(full_key, delta)
            else:
                return await self._client.decrby(full_key, abs(delta))
        except Exception as e:
            raise CacheError(
                f"Failed to increment key: {e}",
                details={"key": key, "delta": delta},
            ) from e

    async def expire(self, key: str, ttl: int) -> bool:
        """Set TTL on an existing key.

        Args:
            key: Cache key.
            ttl: Time-to-live in seconds.

        Returns:
            True if TTL was set, False if key doesn't exist.
        """
        await self._ensure_connected()
        full_key = self.build_key(key)

        try:
            return await self._client.expire(full_key, ttl)
        except Exception as e:
            raise CacheError(
                f"Failed to set expiry: {e}",
                details={"key": key, "ttl": ttl},
            ) from e

    async def ttl(self, key: str) -> int:
        """Get TTL of a key.

        Args:
            key: Cache key.

        Returns:
            TTL in seconds, -1 if no TTL, -2 if key doesn't exist.
        """
        await self._ensure_connected()
        full_key = self.build_key(key)

        try:
            return await self._client.ttl(full_key)
        except Exception:
            return -2

    async def get_many(self, keys: list[str]) -> dict[str, V | None]:
        """Get multiple values at once using MGET.

        Args:
            keys: List of cache keys.

        Returns:
            Dictionary mapping keys to values (None if not found).
        """
        await self._ensure_connected()

        if not keys:
            return {}

        full_keys = [self.build_key(k) for k in keys]

        try:
            values = await self._client.mget(full_keys)
            result: dict[str, V | None] = {}

            for key, value in zip(keys, values, strict=True):
                if value is None:
                    result[key] = None
                else:
                    try:
                        result[key] = self._serializer.deserialize(value)
                    except Exception:
                        result[key] = None

            return result
        except Exception:
            return dict.fromkeys(keys)

    async def set_many(
        self,
        mapping: dict[str, V],
        ttl: int | None = None,
    ) -> bool:
        """Set multiple values at once using pipeline.

        Args:
            mapping: Dictionary of key-value pairs.
            ttl: Time-to-live in seconds.

        Returns:
            True if all successful.
        """
        await self._ensure_connected()

        if not mapping:
            return True

        effective_ttl = self._get_ttl(ttl)

        try:
            pipe = self._client.pipeline()

            for key, value in mapping.items():
                full_key = self.build_key(key)
                data = self._serializer.serialize(value)

                if effective_ttl:
                    pipe.setex(full_key, effective_ttl, data)
                else:
                    pipe.set(full_key, data)

            await pipe.execute()
            return True
        except Exception as e:
            raise CacheError(
                f"Failed to set multiple keys: {e}",
                details={"key_count": len(mapping)},
            ) from e

    async def delete_many(self, keys: list[str]) -> int:
        """Delete multiple keys at once.

        Args:
            keys: List of cache keys to delete.

        Returns:
            Number of keys deleted.
        """
        await self._ensure_connected()

        if not keys:
            return 0

        full_keys = [self.build_key(k) for k in keys]

        try:
            return await self._client.delete(*full_keys)
        except Exception as e:
            raise CacheError(
                f"Failed to delete multiple keys: {e}",
                details={"key_count": len(keys)},
            ) from e

    async def health_check(self) -> bool:
        """Check Redis connection health.

        Returns:
            True if healthy.
        """
        try:
            await self._ensure_connected()
            await self._client.ping()
            return True
        except Exception:
            return False

    def stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache stats.
        """
        return {
            "backend": self.name,
            "connected": self._connected,
            "namespace": self._namespace,
            "default_ttl": self._default_ttl,
            "url": self._config.build_url().split("@")[-1],  # Hide credentials
        }

    async def close(self) -> None:
        """Close Redis connection."""
        if self._client:
            try:
                await self._client.close()
            except Exception:
                pass
            finally:
                self._client = None
                self._connected = False

    async def __aenter__(self) -> RedisCache[V]:
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()
