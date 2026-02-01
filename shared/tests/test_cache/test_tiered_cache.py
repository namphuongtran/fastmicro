"""Tests for TieredCacheManager.

Comprehensive tests for the two-tier caching system.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from shared.cache.backends.memory import MemoryCache
from shared.cache.backends.null import NullCache
from shared.cache.manager import CacheConfig, TieredCacheManager, create_cache


class TestTieredCacheManagerBasic:
    """Test basic TieredCacheManager operations."""

    @pytest.fixture
    def l1_cache(self) -> MemoryCache:
        """Create L1 memory cache."""
        return MemoryCache(namespace="test", max_size=100)

    @pytest.fixture
    def l2_cache(self) -> MemoryCache:
        """Create L2 cache (using memory for testing)."""
        return MemoryCache(namespace="test", max_size=100)

    @pytest.fixture
    def manager(
        self, l1_cache: MemoryCache, l2_cache: MemoryCache
    ) -> TieredCacheManager:
        """Create tiered cache manager."""
        return TieredCacheManager(
            config=CacheConfig(),
            l1_cache=l1_cache,
            l2_cache=l2_cache,
        )

    @pytest.mark.asyncio
    async def test_set_writes_to_both_tiers(
        self, manager: TieredCacheManager, l1_cache: MemoryCache, l2_cache: MemoryCache
    ) -> None:
        """Test set writes to both L1 and L2."""
        await manager.set("key1", "value1")

        # Both tiers should have the value
        assert await l1_cache.get("key1") == "value1"
        assert await l2_cache.get("key1") == "value1"

    @pytest.mark.asyncio
    async def test_get_from_l1_first(
        self, manager: TieredCacheManager, l1_cache: MemoryCache
    ) -> None:
        """Test get checks L1 first."""
        await l1_cache.set("key1", "value1")

        result = await manager.get("key1")

        assert result == "value1"
        assert manager._l1_hits == 1
        assert manager._l2_hits == 0

    @pytest.mark.asyncio
    async def test_get_from_l2_on_l1_miss(
        self, manager: TieredCacheManager, l1_cache: MemoryCache, l2_cache: MemoryCache
    ) -> None:
        """Test get checks L2 on L1 miss."""
        # Only set in L2
        await l2_cache.set("key1", "value1")

        result = await manager.get("key1")

        assert result == "value1"
        assert manager._l1_hits == 0
        assert manager._l2_hits == 1

    @pytest.mark.asyncio
    async def test_l2_hit_backfills_l1(
        self, manager: TieredCacheManager, l1_cache: MemoryCache, l2_cache: MemoryCache
    ) -> None:
        """Test L2 hit backfills L1."""
        # Only set in L2
        await l2_cache.set("key1", "value1")

        # First get should hit L2 and backfill L1
        result1 = await manager.get("key1")
        assert result1 == "value1"

        # Now L1 should have it
        assert await l1_cache.get("key1") == "value1"

        # Reset stats and get again
        manager.reset_stats()
        result2 = await manager.get("key1")

        # Should now be an L1 hit
        assert result2 == "value1"
        assert manager._l1_hits == 1
        assert manager._l2_hits == 0

    @pytest.mark.asyncio
    async def test_delete_from_both_tiers(
        self, manager: TieredCacheManager, l1_cache: MemoryCache, l2_cache: MemoryCache
    ) -> None:
        """Test delete removes from both tiers."""
        await manager.set("key1", "value1")

        result = await manager.delete("key1")

        assert result is True
        assert await l1_cache.exists("key1") is False
        assert await l2_cache.exists("key1") is False

    @pytest.mark.asyncio
    async def test_exists_checks_both_tiers(
        self, manager: TieredCacheManager, l2_cache: MemoryCache
    ) -> None:
        """Test exists checks both tiers."""
        # Set only in L2
        await l2_cache.set("key1", "value1")

        assert await manager.exists("key1") is True
        assert await manager.exists("nonexistent") is False


class TestTieredCacheManagerBulk:
    """Test bulk operations."""

    @pytest.fixture
    def manager(self) -> TieredCacheManager:
        """Create tiered cache manager."""
        return TieredCacheManager(
            l1_cache=MemoryCache(namespace="test"),
            l2_cache=MemoryCache(namespace="test"),
        )

    @pytest.mark.asyncio
    async def test_get_many(self, manager: TieredCacheManager) -> None:
        """Test getting multiple values."""
        await manager.set("key1", "value1")
        await manager.set("key2", "value2")

        result = await manager.get_many(["key1", "key2", "key3"])

        assert result["key1"] == "value1"
        assert result["key2"] == "value2"
        assert result["key3"] is None

    @pytest.mark.asyncio
    async def test_set_many(self, manager: TieredCacheManager) -> None:
        """Test setting multiple values."""
        mapping = {"key1": "v1", "key2": "v2", "key3": "v3"}

        result = await manager.set_many(mapping)

        assert result is True
        assert await manager.get("key1") == "v1"
        assert await manager.get("key2") == "v2"
        assert await manager.get("key3") == "v3"

    @pytest.mark.asyncio
    async def test_delete_many(self, manager: TieredCacheManager) -> None:
        """Test deleting multiple values."""
        await manager.set_many({"key1": "v1", "key2": "v2", "key3": "v3"})

        count = await manager.delete_many(["key1", "key2"])

        assert count == 2
        assert await manager.exists("key1") is False
        assert await manager.exists("key2") is False
        assert await manager.exists("key3") is True


class TestTieredCacheManagerClear:
    """Test clear operation."""

    @pytest.mark.asyncio
    async def test_clear_both_tiers(self) -> None:
        """Test clearing both tiers."""
        l1 = MemoryCache(namespace="test")
        l2 = MemoryCache(namespace="test")
        manager = TieredCacheManager(l1_cache=l1, l2_cache=l2)

        await manager.set_many({"k1": "v1", "k2": "v2"})

        count = await manager.clear()

        # Count is sum of both tiers
        assert count >= 2
        assert await l1.exists("k1") is False
        assert await l2.exists("k1") is False


class TestTieredCacheManagerStats:
    """Test statistics collection."""

    @pytest.mark.asyncio
    async def test_stats(self) -> None:
        """Test comprehensive stats."""
        manager = TieredCacheManager(
            l1_cache=MemoryCache(namespace="test"),
            l2_cache=NullCache(namespace="test"),
        )

        # Generate some traffic
        await manager.set("key1", "value1")
        await manager.get("key1")  # L1 hit
        await manager.get("nonexistent")  # Miss

        stats = manager.stats()

        assert "tiered" in stats["backend"]
        assert "l1" in stats
        assert "l2" in stats
        assert stats["hits"]["l1"] == 1
        assert stats["misses"] == 1

    @pytest.mark.asyncio
    async def test_hit_rate_calculation(self) -> None:
        """Test hit rate is calculated correctly."""
        manager = TieredCacheManager(
            l1_cache=MemoryCache(namespace="test"),
            l2_cache=MemoryCache(namespace="test"),
        )

        await manager.set("key1", "value1")

        # 2 hits, 1 miss = 66.7% hit rate
        await manager.get("key1")  # Hit
        await manager.get("key1")  # Hit
        await manager.get("nonexistent")  # Miss

        stats = manager.stats()

        assert stats["hit_rate"] == pytest.approx(2/3, rel=0.01)


class TestTieredCacheManagerIncrement:
    """Test increment operation."""

    @pytest.mark.asyncio
    async def test_increment(self) -> None:
        """Test increment updates both tiers."""
        l1 = MemoryCache(namespace="test")
        l2 = MemoryCache(namespace="test")
        manager = TieredCacheManager(l1_cache=l1, l2_cache=l2)

        result = await manager.increment("counter")

        assert result == 1
        # L1 should be synchronized with L2 value
        assert await l1.get("counter") == 1


class TestTieredCacheManagerHealthCheck:
    """Test health check."""

    @pytest.mark.asyncio
    async def test_health_check(self) -> None:
        """Test health check returns status for both tiers."""
        manager = TieredCacheManager(
            l1_cache=MemoryCache(namespace="test"),
            l2_cache=NullCache(namespace="test"),
        )

        health = await manager.health_check()

        assert health["l1"] is True
        assert health["overall"] is True


class TestTieredCacheManagerContextManager:
    """Test context manager."""

    @pytest.mark.asyncio
    async def test_context_manager(self) -> None:
        """Test using manager as context manager."""
        config = CacheConfig()

        async with TieredCacheManager(config) as manager:
            await manager.set("key1", "value1")
            result = await manager.get("key1")
            assert result == "value1"


class TestCacheConfig:
    """Test CacheConfig."""

    def test_default_config(self) -> None:
        """Test default configuration."""
        config = CacheConfig()

        assert config.memory_enabled is True
        assert config.memory_max_size == 1000
        assert config.memory_default_ttl == 300
        assert config.redis_enabled is False

    def test_redis_config_from_settings(self) -> None:
        """Test building Redis config from settings."""
        config = CacheConfig(
            redis_enabled=True,
            redis_host="redis.example.com",
            redis_port=6380,
            redis_db=1,
            redis_password="secret",
        )

        redis_config = config.get_redis_config()

        assert redis_config.host == "redis.example.com"
        assert redis_config.port == 6380
        assert redis_config.db == 1
        assert redis_config.password == "secret"


class TestCreateCacheFactory:
    """Test create_cache factory function."""

    def test_create_memory_only_cache(self) -> None:
        """Test creating memory-only cache."""
        cache = create_cache(namespace="test")

        assert cache.l1.name == "memory"
        assert cache.l2.name == "null"  # Redis disabled

    def test_create_cache_with_custom_settings(self) -> None:
        """Test creating cache with custom settings."""
        cache = create_cache(
            memory_max_size=500,
            memory_ttl=120,
            namespace="custom",
        )

        stats = cache.l1.stats()
        assert stats["max_size"] == 500
        assert stats["default_ttl"] == 120
        assert stats["namespace"] == "custom"


class TestTieredCacheManagerL2Failure:
    """Test L2 failure handling."""

    @pytest.mark.asyncio
    async def test_l2_failure_on_set_continues(self) -> None:
        """Test that L2 failure doesn't fail the set operation."""
        l1 = MemoryCache(namespace="test")
        l2 = AsyncMock()
        l2.set = AsyncMock(side_effect=Exception("L2 error"))
        l2.name = "mock"
        l2.get = AsyncMock(return_value=None)

        manager = TieredCacheManager(l1_cache=l1, l2_cache=l2)

        # Should succeed even with L2 failure
        result = await manager.set("key1", "value1")

        assert result is True
        assert await l1.get("key1") == "value1"

    @pytest.mark.asyncio
    async def test_l2_failure_on_get_returns_none(self) -> None:
        """Test that L2 failure returns None gracefully."""
        l1 = MemoryCache(namespace="test")
        l2 = AsyncMock()
        l2.get = AsyncMock(side_effect=Exception("L2 error"))
        l2.name = "mock"

        manager = TieredCacheManager(l1_cache=l1, l2_cache=l2)

        # Should return None on L2 failure
        result = await manager.get("key1")

        assert result is None
