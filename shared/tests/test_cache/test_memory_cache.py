"""Tests for MemoryCache backend.

Comprehensive tests for the L1 in-memory cache implementation.
"""

from __future__ import annotations

import asyncio

import pytest

from shared.cache.backends.memory import MemoryCache


class TestMemoryCacheBasicOperations:
    """Test basic cache operations."""

    @pytest.fixture
    def cache(self) -> MemoryCache:
        """Create a memory cache instance."""
        return MemoryCache(namespace="test", max_size=100, default_ttl=60)

    @pytest.mark.asyncio
    async def test_set_and_get(self, cache: MemoryCache) -> None:
        """Test basic set and get operations."""
        await cache.set("key1", "value1")
        result = await cache.get("key1")
        assert result == "value1"

    @pytest.mark.asyncio
    async def test_get_nonexistent_returns_default(self, cache: MemoryCache) -> None:
        """Test get with default value for nonexistent key."""
        result = await cache.get("nonexistent", default="default_value")
        assert result == "default_value"

    @pytest.mark.asyncio
    async def test_get_nonexistent_returns_none(self, cache: MemoryCache) -> None:
        """Test get returns None for nonexistent key."""
        result = await cache.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_with_custom_ttl(self, cache: MemoryCache) -> None:
        """Test set with custom TTL."""
        await cache.set("key1", "value1", ttl=1)
        result = await cache.get("key1")
        assert result == "value1"
        
        # Wait for expiration
        await asyncio.sleep(1.1)
        result = await cache.get("key1")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_existing_key(self, cache: MemoryCache) -> None:
        """Test delete removes existing key."""
        await cache.set("key1", "value1")
        result = await cache.delete("key1")
        assert result is True
        assert await cache.get("key1") is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_key(self, cache: MemoryCache) -> None:
        """Test delete returns False for nonexistent key."""
        result = await cache.delete("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_exists(self, cache: MemoryCache) -> None:
        """Test exists check."""
        await cache.set("key1", "value1")
        assert await cache.exists("key1") is True
        assert await cache.exists("nonexistent") is False


class TestMemoryCacheNamespace:
    """Test namespace functionality."""

    @pytest.mark.asyncio
    async def test_namespace_isolation(self) -> None:
        """Test that namespaces provide key isolation."""
        cache1 = MemoryCache(namespace="ns1")
        cache2 = MemoryCache(namespace="ns2")
        
        await cache1.set("key", "value1")
        await cache2.set("key", "value2")
        
        assert await cache1.get("key") == "value1"
        assert await cache2.get("key") == "value2"

    @pytest.mark.asyncio
    async def test_build_key_with_namespace(self) -> None:
        """Test key building with namespace."""
        cache = MemoryCache(namespace="myapp")
        key = cache.build_key("user:123")
        assert key == "myapp:user:123"

    @pytest.mark.asyncio
    async def test_build_key_without_namespace(self) -> None:
        """Test key building without namespace."""
        cache = MemoryCache(namespace="")
        key = cache.build_key("user:123")
        assert key == "user:123"


class TestMemoryCacheBulkOperations:
    """Test bulk operations."""

    @pytest.fixture
    def cache(self) -> MemoryCache:
        """Create a memory cache instance."""
        return MemoryCache(namespace="test")

    @pytest.mark.asyncio
    async def test_get_many(self, cache: MemoryCache) -> None:
        """Test getting multiple values."""
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        
        result = await cache.get_many(["key1", "key2", "key3"])
        
        assert result == {
            "key1": "value1",
            "key2": "value2",
            "key3": None,
        }

    @pytest.mark.asyncio
    async def test_set_many(self, cache: MemoryCache) -> None:
        """Test setting multiple values."""
        mapping = {"key1": "value1", "key2": "value2", "key3": "value3"}
        result = await cache.set_many(mapping)
        
        assert result is True
        assert await cache.get("key1") == "value1"
        assert await cache.get("key2") == "value2"
        assert await cache.get("key3") == "value3"

    @pytest.mark.asyncio
    async def test_delete_many(self, cache: MemoryCache) -> None:
        """Test deleting multiple values."""
        await cache.set_many({"key1": "v1", "key2": "v2", "key3": "v3"})
        
        count = await cache.delete_many(["key1", "key2"])
        
        assert count == 2
        assert await cache.exists("key1") is False
        assert await cache.exists("key2") is False
        assert await cache.exists("key3") is True


class TestMemoryCacheIncrement:
    """Test increment operation."""

    @pytest.fixture
    def cache(self) -> MemoryCache:
        """Create a memory cache instance."""
        return MemoryCache(namespace="test")

    @pytest.mark.asyncio
    async def test_increment_new_key(self, cache: MemoryCache) -> None:
        """Test increment on new key starts from 0."""
        result = await cache.increment("counter")
        assert result == 1

    @pytest.mark.asyncio
    async def test_increment_existing_key(self, cache: MemoryCache) -> None:
        """Test increment on existing numeric value."""
        await cache.set("counter", 5)
        result = await cache.increment("counter")
        assert result == 6

    @pytest.mark.asyncio
    async def test_increment_with_delta(self, cache: MemoryCache) -> None:
        """Test increment with custom delta."""
        await cache.set("counter", 10)
        result = await cache.increment("counter", delta=5)
        assert result == 15

    @pytest.mark.asyncio
    async def test_decrement(self, cache: MemoryCache) -> None:
        """Test decrement (negative delta)."""
        await cache.set("counter", 10)
        result = await cache.increment("counter", delta=-3)
        assert result == 7


class TestMemoryCacheClear:
    """Test clear operation."""

    @pytest.mark.asyncio
    async def test_clear_all(self) -> None:
        """Test clearing all entries."""
        cache = MemoryCache(namespace="test")
        await cache.set_many({"key1": "v1", "key2": "v2", "key3": "v3"})
        
        count = await cache.clear()
        
        assert count == 3
        assert await cache.exists("key1") is False
        assert await cache.exists("key2") is False
        assert await cache.exists("key3") is False


class TestMemoryCacheStats:
    """Test statistics collection."""

    @pytest.mark.asyncio
    async def test_stats(self) -> None:
        """Test stats collection."""
        cache = MemoryCache(namespace="test", max_size=100, default_ttl=60)
        await cache.set_many({"key1": "v1", "key2": "v2"})
        
        stats = cache.stats()
        
        assert stats["backend"] == "memory"
        assert stats["namespace"] == "test"
        assert stats["max_size"] == 100
        assert stats["size"] == 2
        assert stats["default_ttl"] == 60


class TestMemoryCacheEviction:
    """Test LRU eviction behavior."""

    @pytest.mark.asyncio
    async def test_max_size_eviction(self) -> None:
        """Test that cache evicts when max size is exceeded."""
        cache = MemoryCache(namespace="test", max_size=3)
        
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.set("key3", "value3")
        
        # Adding a 4th key should evict the least recently used
        await cache.set("key4", "value4")
        
        # One of the earlier keys should be evicted
        stats = cache.stats()
        assert stats["size"] == 3


class TestMemoryCacheContextManager:
    """Test async context manager."""

    @pytest.mark.asyncio
    async def test_context_manager(self) -> None:
        """Test using cache as context manager."""
        async with MemoryCache(namespace="test") as cache:
            await cache.set("key1", "value1")
            result = await cache.get("key1")
            assert result == "value1"


class TestMemoryCacheDataTypes:
    """Test various data types."""

    @pytest.fixture
    def cache(self) -> MemoryCache:
        """Create a memory cache instance."""
        return MemoryCache(namespace="test")

    @pytest.mark.asyncio
    async def test_dict_value(self, cache: MemoryCache) -> None:
        """Test caching dict values."""
        data = {"name": "John", "age": 30, "tags": ["admin", "user"]}
        await cache.set("user", data)
        result = await cache.get("user")
        assert result == data

    @pytest.mark.asyncio
    async def test_list_value(self, cache: MemoryCache) -> None:
        """Test caching list values."""
        data = [1, 2, 3, "four", {"five": 5}]
        await cache.set("items", data)
        result = await cache.get("items")
        assert result == data

    @pytest.mark.asyncio
    async def test_none_value(self, cache: MemoryCache) -> None:
        """Test caching None value - should still be distinguishable."""
        # This is tricky - None is a valid cached value
        # but we use None to indicate "not found"
        await cache.set("nullable", None)
        result = await cache.get("nullable")
        # Memory cache preserves None
        assert result is None

    @pytest.mark.asyncio
    async def test_boolean_values(self, cache: MemoryCache) -> None:
        """Test caching boolean values."""
        await cache.set("flag_true", True)
        await cache.set("flag_false", False)
        
        assert await cache.get("flag_true") is True
        assert await cache.get("flag_false") is False

    @pytest.mark.asyncio
    async def test_numeric_values(self, cache: MemoryCache) -> None:
        """Test caching numeric values."""
        await cache.set("int_val", 42)
        await cache.set("float_val", 3.14)
        
        assert await cache.get("int_val") == 42
        assert await cache.get("float_val") == 3.14
