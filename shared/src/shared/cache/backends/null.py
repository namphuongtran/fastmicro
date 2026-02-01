"""Null cache backend.

This module provides a no-operation cache for:
- Testing without real cache infrastructure
- Disabling cache via configuration
- Development environments

All operations succeed but don't actually cache anything.
"""

from __future__ import annotations

from typing import Any, TypeVar

from shared.cache.base import (
    AbstractCacheBackend,
    NullSerializer,
    Serializer,
)

V = TypeVar("V")


class NullCache(AbstractCacheBackend[V]):
    """No-operation cache backend.

    Implements the CacheBackend interface but doesn't store anything.
    Useful for testing, development, or disabling caching.

    Example:
        >>> cache = NullCache()
        >>> await cache.set("key", "value")  # Does nothing
        >>> await cache.get("key")  # Returns None
        None
    """

    def __init__(
        self,
        *,
        namespace: str = "",
        default_ttl: int = 0,
        serializer: Serializer[Any] | None = None,
    ) -> None:
        """Initialize null cache.

        Args:
            namespace: Key namespace prefix (ignored).
            default_ttl: Default TTL in seconds (ignored).
            serializer: Value serializer (ignored).
        """
        super().__init__(
            namespace=namespace,
            default_ttl=default_ttl,
            serializer=serializer or NullSerializer(),
        )
        self._get_count = 0
        self._set_count = 0
        self._delete_count = 0

    @property
    def name(self) -> str:
        """Return backend name."""
        return "null"

    async def get(self, key: str, default: V | None = None) -> V | None:
        """Get always returns default.

        Args:
            key: Cache key (ignored).
            default: Default value to return.

        Returns:
            Always returns default.
        """
        self._get_count += 1
        return default

    async def set(
        self,
        key: str,
        value: V,
        ttl: int | None = None,
    ) -> bool:
        """Set does nothing but returns success.

        Args:
            key: Cache key (ignored).
            value: Value to cache (ignored).
            ttl: Time-to-live (ignored).

        Returns:
            Always True.
        """
        self._set_count += 1
        return True

    async def delete(self, key: str) -> bool:
        """Delete does nothing but returns success.

        Args:
            key: Cache key (ignored).

        Returns:
            Always True.
        """
        self._delete_count += 1
        return True

    async def exists(self, key: str) -> bool:
        """Exists always returns False.

        Args:
            key: Cache key (ignored).

        Returns:
            Always False.
        """
        return False

    async def clear(self, namespace: str | None = None) -> int:
        """Clear does nothing.

        Args:
            namespace: Namespace prefix (ignored).

        Returns:
            Always 0.
        """
        return 0

    async def increment(self, key: str, delta: int = 1) -> int:
        """Increment returns delta (as if from 0).

        Args:
            key: Cache key (ignored).
            delta: Amount to increment.

        Returns:
            The delta value.
        """
        return delta

    async def get_many(self, keys: list[str]) -> dict[str, V | None]:
        """Get multiple values - all return None.

        Args:
            keys: List of cache keys.

        Returns:
            Dictionary with all values as None.
        """
        self._get_count += len(keys)
        return dict.fromkeys(keys)

    async def set_many(
        self,
        mapping: dict[str, V],
        ttl: int | None = None,
    ) -> bool:
        """Set multiple values - does nothing.

        Args:
            mapping: Dictionary of key-value pairs.
            ttl: Time-to-live (ignored).

        Returns:
            Always True.
        """
        self._set_count += len(mapping)
        return True

    async def delete_many(self, keys: list[str]) -> int:
        """Delete multiple keys - does nothing.

        Args:
            keys: List of cache keys.

        Returns:
            Always returns count of keys.
        """
        self._delete_count += len(keys)
        return len(keys)

    async def close(self) -> None:
        """Close does nothing."""
        pass

    def stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with operation counts.
        """
        return {
            "backend": self.name,
            "namespace": self._namespace,
            "get_calls": self._get_count,
            "set_calls": self._set_count,
            "delete_calls": self._delete_count,
        }

    def reset_stats(self) -> None:
        """Reset operation counters."""
        self._get_count = 0
        self._set_count = 0
        self._delete_count = 0

    async def __aenter__(self) -> NullCache[V]:
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        pass
