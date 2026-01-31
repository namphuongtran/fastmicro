"""In-memory cache backend using cachetools.

This module provides L1 (local) caching with:
- TTL-based expiration
- LRU eviction when max size reached
- Thread-safe operations via asyncio.Lock
- Zero network latency (~1μs access time)

Best used as the first tier in a tiered cache setup.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Generic, TypeVar

from cachetools import TTLCache

from shared.cache.base import (
    AbstractCacheBackend,
    CacheError,
    NullSerializer,
    Serializer,
)

V = TypeVar("V")


class MemoryCache(AbstractCacheBackend[V]):
    """In-memory cache backend using cachetools TTLCache.
    
    Provides fast local caching with TTL expiration and LRU eviction.
    Thread-safe for use in async contexts.
    
    Features:
        - Configurable max size (items)
        - TTL-based expiration
        - LRU eviction when full
        - Thread-safe via asyncio.Lock
        - ~1μs access time
    
    Example:
        >>> cache = MemoryCache(max_size=1000, default_ttl=300)
        >>> await cache.set("user:123", {"name": "John"})
        >>> await cache.get("user:123")
        {'name': 'John'}
    
    Note:
        This cache is per-process. Each worker process has its own
        independent cache instance. Use Redis for shared state.
    """

    def __init__(
        self,
        *,
        max_size: int = 1000,
        default_ttl: int = 300,
        namespace: str = "",
    ) -> None:
        """Initialize memory cache.
        
        Args:
            max_size: Maximum number of items in cache.
            default_ttl: Default TTL in seconds.
            namespace: Optional key namespace prefix.
        """
        # Memory cache uses NullSerializer - stores Python objects directly
        super().__init__(
            namespace=namespace,
            default_ttl=default_ttl,
            serializer=NullSerializer(),
        )
        self._max_size = max_size
        self._cache: TTLCache[str, Any] = TTLCache(maxsize=max_size, ttl=default_ttl)
        self._lock = asyncio.Lock()
        # Track custom TTLs (cachetools TTLCache has single global TTL)
        self._ttls: dict[str, float] = {}  # key -> expiry timestamp

    @property
    def name(self) -> str:
        """Return backend name."""
        return "memory"

    @property
    def size(self) -> int:
        """Return current cache size."""
        return len(self._cache)

    @property
    def max_size(self) -> int:
        """Return maximum cache size."""
        return self._max_size

    async def get(self, key: str, default: V | None = None) -> V | None:
        """Get a value from the cache.
        
        Args:
            key: Cache key.
            default: Default value if key not found.
            
        Returns:
            Cached value or default.
        """
        full_key = self.build_key(key)
        
        async with self._lock:
            # Check custom TTL expiry
            if full_key in self._ttls:
                if time.time() > self._ttls[full_key]:
                    # Expired - clean up
                    self._cache.pop(full_key, None)
                    del self._ttls[full_key]
                    return default
            
            try:
                return self._cache[full_key]
            except KeyError:
                return default

    async def set(
        self,
        key: str,
        value: V,
        ttl: int | None = None,
    ) -> bool:
        """Set a value in the cache.
        
        Args:
            key: Cache key.
            value: Value to cache.
            ttl: Time-to-live in seconds (None = use default).
            
        Returns:
            True if successful.
        """
        full_key = self.build_key(key)
        effective_ttl = self._get_ttl(ttl)
        
        async with self._lock:
            self._cache[full_key] = value
            
            # Track custom TTL if different from default
            if effective_ttl and effective_ttl != self._default_ttl:
                self._ttls[full_key] = time.time() + effective_ttl
            elif full_key in self._ttls:
                # Remove custom TTL if using default
                del self._ttls[full_key]
        
        return True

    async def delete(self, key: str) -> bool:
        """Delete a key from the cache.
        
        Args:
            key: Cache key to delete.
            
        Returns:
            True if key was deleted, False if not found.
        """
        full_key = self.build_key(key)
        
        async with self._lock:
            existed = full_key in self._cache
            self._cache.pop(full_key, None)
            self._ttls.pop(full_key, None)
            return existed

    async def exists(self, key: str) -> bool:
        """Check if a key exists in the cache.
        
        Args:
            key: Cache key.
            
        Returns:
            True if key exists and not expired.
        """
        full_key = self.build_key(key)
        
        async with self._lock:
            # Check custom TTL expiry
            if full_key in self._ttls:
                if time.time() > self._ttls[full_key]:
                    self._cache.pop(full_key, None)
                    del self._ttls[full_key]
                    return False
            
            return full_key in self._cache

    async def clear(self, namespace: str | None = None) -> int:
        """Clear cache entries.
        
        Args:
            namespace: Optional namespace prefix to clear.
                      If None, clears entire cache.
            
        Returns:
            Number of keys cleared.
        """
        async with self._lock:
            if namespace is None:
                count = len(self._cache)
                self._cache.clear()
                self._ttls.clear()
                return count
            
            # Clear only keys matching namespace
            prefix = f"{namespace}:"
            keys_to_delete = [k for k in self._cache if k.startswith(prefix)]
            
            for key in keys_to_delete:
                self._cache.pop(key, None)
                self._ttls.pop(key, None)
            
            return len(keys_to_delete)

    async def increment(self, key: str, delta: int = 1) -> int:
        """Increment a numeric value.
        
        Args:
            key: Cache key.
            delta: Amount to increment (can be negative).
            
        Returns:
            New value after increment.
            
        Raises:
            CacheError: If value is not numeric.
        """
        full_key = self.build_key(key)
        
        async with self._lock:
            current = self._cache.get(full_key, 0)
            
            if not isinstance(current, (int, float)):
                raise CacheError(
                    f"Cannot increment non-numeric value: {type(current).__name__}",
                    details={"key": key, "value_type": type(current).__name__},
                )
            
            new_value = int(current) + delta
            self._cache[full_key] = new_value
            return new_value

    async def get_many(self, keys: list[str]) -> dict[str, V | None]:
        """Get multiple values at once.
        
        Args:
            keys: List of cache keys.
            
        Returns:
            Dictionary mapping keys to values (None if not found).
        """
        result: dict[str, V | None] = {}
        
        async with self._lock:
            now = time.time()
            for key in keys:
                full_key = self.build_key(key)
                
                # Check expiry
                if full_key in self._ttls and now > self._ttls[full_key]:
                    self._cache.pop(full_key, None)
                    del self._ttls[full_key]
                    result[key] = None
                else:
                    result[key] = self._cache.get(full_key)
        
        return result

    async def set_many(
        self,
        mapping: dict[str, V],
        ttl: int | None = None,
    ) -> bool:
        """Set multiple values at once.
        
        Args:
            mapping: Dictionary of key-value pairs.
            ttl: Time-to-live in seconds.
            
        Returns:
            True if all successful.
        """
        effective_ttl = self._get_ttl(ttl)
        expiry = time.time() + effective_ttl if effective_ttl else None
        
        async with self._lock:
            for key, value in mapping.items():
                full_key = self.build_key(key)
                self._cache[full_key] = value
                
                if expiry and effective_ttl != self._default_ttl:
                    self._ttls[full_key] = expiry
                elif full_key in self._ttls:
                    del self._ttls[full_key]
        
        return True

    async def delete_many(self, keys: list[str]) -> int:
        """Delete multiple keys at once.
        
        Args:
            keys: List of cache keys to delete.
            
        Returns:
            Number of keys deleted.
        """
        count = 0
        
        async with self._lock:
            for key in keys:
                full_key = self.build_key(key)
                if full_key in self._cache:
                    self._cache.pop(full_key, None)
                    self._ttls.pop(full_key, None)
                    count += 1
        
        return count

    def stats(self) -> dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Dictionary with cache stats.
        """
        return {
            "backend": self.name,
            "size": len(self._cache),
            "max_size": self._max_size,
            "default_ttl": self._default_ttl,
            "namespace": self._namespace,
            "custom_ttl_keys": len(self._ttls),
        }

    async def close(self) -> None:
        """Clear cache on close."""
        async with self._lock:
            self._cache.clear()
            self._ttls.clear()
