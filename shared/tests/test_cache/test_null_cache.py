"""Tests for NullCache backend.

Tests for the no-operation cache implementation.
"""

from __future__ import annotations

import pytest

from shared.cache.backends.null import NullCache


class TestNullCacheOperations:
    """Test NullCache operations."""

    @pytest.fixture
    def cache(self) -> NullCache:
        """Create a null cache instance."""
        return NullCache(namespace="test")

    @pytest.mark.asyncio
    async def test_get_returns_default(self, cache: NullCache) -> None:
        """Test get always returns default."""
        result = await cache.get("key")
        assert result is None
        
        result = await cache.get("key", default="default")
        assert result == "default"

    @pytest.mark.asyncio
    async def test_set_returns_true(self, cache: NullCache) -> None:
        """Test set always succeeds."""
        result = await cache.set("key", "value")
        assert result is True
        
        # But value is not stored
        assert await cache.get("key") is None

    @pytest.mark.asyncio
    async def test_delete_returns_true(self, cache: NullCache) -> None:
        """Test delete always succeeds."""
        result = await cache.delete("key")
        assert result is True

    @pytest.mark.asyncio
    async def test_exists_returns_false(self, cache: NullCache) -> None:
        """Test exists always returns False."""
        await cache.set("key", "value")
        assert await cache.exists("key") is False

    @pytest.mark.asyncio
    async def test_clear_returns_zero(self, cache: NullCache) -> None:
        """Test clear returns 0."""
        result = await cache.clear()
        assert result == 0

    @pytest.mark.asyncio
    async def test_increment_returns_delta(self, cache: NullCache) -> None:
        """Test increment returns delta (as if from 0)."""
        result = await cache.increment("counter")
        assert result == 1
        
        result = await cache.increment("counter", delta=5)
        assert result == 5


class TestNullCacheBulkOperations:
    """Test bulk operations."""

    @pytest.fixture
    def cache(self) -> NullCache:
        """Create a null cache instance."""
        return NullCache()

    @pytest.mark.asyncio
    async def test_get_many_returns_none(self, cache: NullCache) -> None:
        """Test get_many returns None for all keys."""
        result = await cache.get_many(["key1", "key2", "key3"])
        assert result == {"key1": None, "key2": None, "key3": None}

    @pytest.mark.asyncio
    async def test_set_many_returns_true(self, cache: NullCache) -> None:
        """Test set_many always succeeds."""
        result = await cache.set_many({"key1": "v1", "key2": "v2"})
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_many_returns_count(self, cache: NullCache) -> None:
        """Test delete_many returns key count."""
        result = await cache.delete_many(["key1", "key2", "key3"])
        assert result == 3


class TestNullCacheStats:
    """Test statistics tracking."""

    @pytest.mark.asyncio
    async def test_stats_tracks_operations(self) -> None:
        """Test stats tracks operation counts."""
        cache = NullCache()
        
        await cache.get("k1")
        await cache.get("k2")
        await cache.set("k1", "v1")
        await cache.delete("k1")
        
        stats = cache.stats()
        
        assert stats["backend"] == "null"
        assert stats["get_calls"] == 2
        assert stats["set_calls"] == 1
        assert stats["delete_calls"] == 1

    @pytest.mark.asyncio
    async def test_reset_stats(self) -> None:
        """Test resetting statistics."""
        cache = NullCache()
        
        await cache.get("k1")
        await cache.set("k1", "v1")
        
        cache.reset_stats()
        stats = cache.stats()
        
        assert stats["get_calls"] == 0
        assert stats["set_calls"] == 0
        assert stats["delete_calls"] == 0


class TestNullCacheContextManager:
    """Test context manager."""

    @pytest.mark.asyncio
    async def test_context_manager(self) -> None:
        """Test using NullCache as context manager."""
        async with NullCache() as cache:
            result = await cache.set("key", "value")
            assert result is True
            assert await cache.get("key") is None


class TestNullCacheName:
    """Test backend name."""

    def test_name(self) -> None:
        """Test backend name property."""
        cache = NullCache()
        assert cache.name == "null"
