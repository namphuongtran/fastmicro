"""Tiered cache manager.

This module provides a two-tier caching system:
- L1: In-memory cache (fast, per-process)
- L2: Redis cache (distributed, shared)

The manager automatically handles cache hierarchy:
- GET: L1 → L2 (with L1 backfill on L2 hit)
- SET: L1 + L2 (write-through)
- DELETE: L1 + L2 (invalidate both)
"""

from __future__ import annotations

import asyncio
from typing import Any, TypeVar

from pydantic import BaseModel, Field

from shared.cache.backends.memory import MemoryCache
from shared.cache.backends.null import NullCache
from shared.cache.backends.redis import RedisCache, RedisConfig
from shared.cache.base import CacheBackend

V = TypeVar("V")


class CacheConfig(BaseModel):
    """Cache tier configuration.
    
    Configures the two-tier cache system. Memory cache (L1) is
    always enabled, Redis cache (L2) is optional.
    
    Example:
        >>> # Memory only
        >>> config = CacheConfig()
        >>>
        >>> # Memory + Redis
        >>> config = CacheConfig(
        ...     redis_enabled=True,
        ...     redis_url="redis://localhost:6379/0"
        ... )
    """

    # L1 Memory cache settings
    memory_enabled: bool = True
    memory_max_size: int = Field(default=1000, ge=0)
    memory_default_ttl: int = Field(default=300, ge=0)

    # L2 Redis cache settings
    redis_enabled: bool = False
    redis_url: str | None = None
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str | None = None
    redis_default_ttl: int = Field(default=3600, ge=0)
    redis_max_connections: int = Field(default=10, ge=1)

    # General settings
    namespace: str = ""
    key_prefix: str = ""

    def get_redis_config(self) -> RedisConfig:
        """Build RedisConfig from settings."""
        return RedisConfig(
            url=self.redis_url,
            host=self.redis_host,
            port=self.redis_port,
            db=self.redis_db,
            password=self.redis_password,
            max_connections=self.redis_max_connections,
        )


class TieredCacheManager(CacheBackend[V]):
    """Two-tier cache manager orchestrating L1 (memory) and L2 (Redis).
    
    Implements a hierarchical caching strategy:
    
    Read Flow (GET):
        1. Check L1 (memory) - ~1μs latency
        2. If miss, check L2 (Redis) - ~1-5ms latency
        3. If L2 hit, backfill L1 for future requests
        4. Return value or default
    
    Write Flow (SET):
        1. Write to L1 (memory) - always
        2. Write to L2 (Redis) - if enabled (write-through)
    
    Delete Flow (DELETE):
        1. Delete from L1 (memory) - always
        2. Delete from L2 (Redis) - if enabled
    
    Example:
        >>> config = CacheConfig(
        ...     redis_enabled=True,
        ...     redis_url="redis://localhost:6379/0"
        ... )
        >>> cache = TieredCacheManager(config)
        >>> await cache.connect()
        >>>
        >>> # Fast writes to both tiers
        >>> await cache.set("user:123", {"name": "John"})
        >>>
        >>> # Fast reads from L1
        >>> await cache.get("user:123")
        {'name': 'John'}
    
    Note:
        Call connect() before use, or use as async context manager.
    """

    def __init__(
        self,
        config: CacheConfig | None = None,
        *,
        l1_cache: CacheBackend[V] | None = None,
        l2_cache: CacheBackend[V] | None = None,
    ) -> None:
        """Initialize tiered cache manager.
        
        Args:
            config: Cache configuration.
            l1_cache: Custom L1 backend (for testing).
            l2_cache: Custom L2 backend (for testing).
        """
        self._config = config or CacheConfig()

        # Initialize L1 (memory) cache
        if l1_cache is not None:
            self._l1 = l1_cache
        elif self._config.memory_enabled:
            self._l1 = MemoryCache(
                namespace=self._config.namespace,
                max_size=self._config.memory_max_size,
                default_ttl=self._config.memory_default_ttl,
            )
        else:
            self._l1 = NullCache(namespace=self._config.namespace)

        # Initialize L2 (Redis) cache
        if l2_cache is not None:
            self._l2 = l2_cache
        elif self._config.redis_enabled:
            self._l2 = RedisCache(
                config=self._config.get_redis_config(),
                namespace=self._config.namespace,
                default_ttl=self._config.redis_default_ttl,
            )
        else:
            self._l2 = NullCache(namespace=self._config.namespace)

        self._connected = False
        self._l1_hits = 0
        self._l2_hits = 0
        self._misses = 0

    @property
    def name(self) -> str:
        """Return backend name."""
        return f"tiered({self._l1.name}+{self._l2.name})"

    @property
    def l1(self) -> CacheBackend[V]:
        """Get L1 (memory) cache backend."""
        return self._l1

    @property
    def l2(self) -> CacheBackend[V]:
        """Get L2 (Redis) cache backend."""
        return self._l2

    async def connect(self) -> None:
        """Connect to cache backends.
        
        Connects to Redis if enabled. Memory cache doesn't need connection.
        """
        if self._connected:
            return

        # Connect L2 (Redis) if it has connect method
        if hasattr(self._l2, "connect"):
            await self._l2.connect()

        self._connected = True

    async def get(self, key: str, default: V | None = None) -> V | None:
        """Get value with tiered lookup.
        
        Lookup order: L1 (memory) → L2 (Redis)
        On L2 hit, backfills L1 for faster subsequent access.
        
        Args:
            key: Cache key.
            default: Default value if not found.
            
        Returns:
            Cached value or default.
        """
        # Try L1 first (fast path ~1μs)
        try:
            value = await self._l1.get(key)
            if value is not None:
                self._l1_hits += 1
                return value
        except Exception:
            pass  # L1 failure, continue to L2

        # Try L2 (slower path ~1-5ms)
        try:
            value = await self._l2.get(key)
            if value is not None:
                self._l2_hits += 1
                # Backfill L1 for future requests (best effort)
                try:
                    await self._l1.set(key, value)
                except Exception:
                    pass
                return value
        except Exception:
            pass  # L2 failure, return default

        self._misses += 1
        return default

    async def set(
        self,
        key: str,
        value: V,
        ttl: int | None = None,
    ) -> bool:
        """Set value in both tiers (write-through).
        
        Writes to both L1 and L2 for consistency.
        
        Args:
            key: Cache key.
            value: Value to cache.
            ttl: Time-to-live in seconds.
            
        Returns:
            True if successful.
        """
        # Write to both tiers concurrently
        results = await asyncio.gather(
            self._l1.set(key, value, ttl),
            self._l2.set(key, value, ttl),
            return_exceptions=True,
        )

        # L1 must succeed, L2 failures are tolerated
        l1_success = results[0] is True
        return l1_success

    async def delete(self, key: str) -> bool:
        """Delete from both tiers.
        
        Args:
            key: Cache key to delete.
            
        Returns:
            True if deleted from at least one tier.
        """
        results = await asyncio.gather(
            self._l1.delete(key),
            self._l2.delete(key),
            return_exceptions=True,
        )

        # Return True if deleted from either tier
        l1_deleted = results[0] is True
        l2_deleted = results[1] is True
        return l1_deleted or l2_deleted

    async def exists(self, key: str) -> bool:
        """Check if key exists in either tier.
        
        Args:
            key: Cache key.
            
        Returns:
            True if key exists in L1 or L2.
        """
        # Check L1 first (fast)
        if await self._l1.exists(key):
            return True

        # Check L2
        return await self._l2.exists(key)

    async def clear(self, namespace: str | None = None) -> int:
        """Clear both cache tiers.
        
        Args:
            namespace: Namespace prefix to clear.
            
        Returns:
            Total number of keys cleared.
        """
        results = await asyncio.gather(
            self._l1.clear(namespace),
            self._l2.clear(namespace),
            return_exceptions=True,
        )

        l1_count = results[0] if isinstance(results[0], int) else 0
        l2_count = results[1] if isinstance(results[1], int) else 0

        return l1_count + l2_count

    async def increment(self, key: str, delta: int = 1) -> int:
        """Increment value in both tiers.
        
        Note: This operation may have race conditions between tiers.
        For strict atomic increments, use Redis directly.
        
        Args:
            key: Cache key.
            delta: Amount to increment.
            
        Returns:
            New value after increment.
        """
        # Increment in L2 first (authoritative if enabled)
        l2_value = await self._l2.increment(key, delta)

        # Update L1 to match
        await self._l1.set(key, l2_value)

        return l2_value

    async def get_many(self, keys: list[str]) -> dict[str, V | None]:
        """Get multiple values with tiered lookup.
        
        Args:
            keys: List of cache keys.
            
        Returns:
            Dictionary mapping keys to values.
        """
        if not keys:
            return {}

        # Get all from L1
        l1_results = await self._l1.get_many(keys)

        # Find keys missing from L1
        missing_keys = [k for k, v in l1_results.items() if v is None]

        if missing_keys:
            # Get missing from L2
            l2_results = await self._l2.get_many(missing_keys)

            # Backfill L1 with L2 hits
            backfill = {k: v for k, v in l2_results.items() if v is not None}
            if backfill:
                await self._l1.set_many(backfill)

            # Merge results
            l1_results.update(l2_results)

        return l1_results

    async def set_many(
        self,
        mapping: dict[str, V],
        ttl: int | None = None,
    ) -> bool:
        """Set multiple values in both tiers.
        
        Args:
            mapping: Dictionary of key-value pairs.
            ttl: Time-to-live in seconds.
            
        Returns:
            True if successful.
        """
        if not mapping:
            return True

        results = await asyncio.gather(
            self._l1.set_many(mapping, ttl),
            self._l2.set_many(mapping, ttl),
            return_exceptions=True,
        )

        return results[0] is True

    async def delete_many(self, keys: list[str]) -> int:
        """Delete multiple keys from both tiers.
        
        Args:
            keys: List of cache keys.
            
        Returns:
            Number of keys deleted.
        """
        if not keys:
            return 0

        results = await asyncio.gather(
            self._l1.delete_many(keys),
            self._l2.delete_many(keys),
            return_exceptions=True,
        )

        # Return max of both (they should be similar)
        l1_count = results[0] if isinstance(results[0], int) else 0
        l2_count = results[1] if isinstance(results[1], int) else 0

        return max(l1_count, l2_count)

    async def health_check(self) -> dict[str, bool]:
        """Check health of both cache tiers.
        
        Returns:
            Dictionary with health status of each tier.
        """
        l1_healthy = True  # Memory cache is always healthy
        l2_healthy = True

        if hasattr(self._l2, "health_check"):
            l2_healthy = await self._l2.health_check()

        return {
            "l1": l1_healthy,
            "l2": l2_healthy,
            "overall": l1_healthy,  # System works with just L1
        }

    def stats(self) -> dict[str, Any]:
        """Get comprehensive cache statistics.
        
        Returns:
            Dictionary with stats for both tiers.
        """
        total_requests = self._l1_hits + self._l2_hits + self._misses

        l1_stats = self._l1.stats() if hasattr(self._l1, "stats") else {}
        l2_stats = self._l2.stats() if hasattr(self._l2, "stats") else {}

        return {
            "backend": self.name,
            "connected": self._connected,
            "l1": l1_stats,
            "l2": l2_stats,
            "hits": {
                "l1": self._l1_hits,
                "l2": self._l2_hits,
                "total": self._l1_hits + self._l2_hits,
            },
            "misses": self._misses,
            "hit_rate": (
                (self._l1_hits + self._l2_hits) / total_requests
                if total_requests > 0
                else 0.0
            ),
            "l1_hit_rate": (
                self._l1_hits / total_requests
                if total_requests > 0
                else 0.0
            ),
        }

    def reset_stats(self) -> None:
        """Reset hit/miss counters."""
        self._l1_hits = 0
        self._l2_hits = 0
        self._misses = 0

        if hasattr(self._l1, "reset_stats"):
            self._l1.reset_stats()
        if hasattr(self._l2, "reset_stats"):
            self._l2.reset_stats()

    async def close(self) -> None:
        """Close all cache connections."""
        await asyncio.gather(
            self._l1.close(),
            self._l2.close(),
            return_exceptions=True,
        )
        self._connected = False

    async def __aenter__(self) -> TieredCacheManager[V]:
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()


# Convenience factory function
def create_cache(
    *,
    memory_enabled: bool = True,
    memory_max_size: int = 1000,
    memory_ttl: int = 300,
    redis_enabled: bool = False,
    redis_url: str | None = None,
    redis_host: str = "localhost",
    redis_port: int = 6379,
    redis_ttl: int = 3600,
    namespace: str = "",
) -> TieredCacheManager[Any]:
    """Create a tiered cache manager with common settings.
    
    Args:
        memory_enabled: Enable L1 memory cache.
        memory_max_size: Max items in memory cache.
        memory_ttl: Default TTL for memory cache.
        redis_enabled: Enable L2 Redis cache.
        redis_url: Redis connection URL.
        redis_host: Redis host (if URL not provided).
        redis_port: Redis port.
        redis_ttl: Default TTL for Redis cache.
        namespace: Key namespace prefix.
        
    Returns:
        Configured TieredCacheManager instance.
        
    Example:
        >>> # Memory only
        >>> cache = create_cache()
        >>>
        >>> # Memory + Redis
        >>> cache = create_cache(
        ...     redis_enabled=True,
        ...     redis_url="redis://localhost:6379/0",
        ...     namespace="myapp"
        ... )
    """
    config = CacheConfig(
        memory_enabled=memory_enabled,
        memory_max_size=memory_max_size,
        memory_default_ttl=memory_ttl,
        redis_enabled=redis_enabled,
        redis_url=redis_url,
        redis_host=redis_host,
        redis_port=redis_port,
        redis_default_ttl=redis_ttl,
        namespace=namespace,
    )
    return TieredCacheManager(config)
