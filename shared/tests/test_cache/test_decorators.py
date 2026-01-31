"""Tests for shared.cache.decorators module.

This module tests cache decorators.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shared.cache.decorators import cached, cache_aside, invalidate_cache
from shared.cache.redis_client import AsyncRedisClient, RedisConfig


class TestCachedDecorator:
    """Tests for @cached decorator."""

    @pytest.fixture
    def mock_redis_client(self) -> MagicMock:
        """Create mock Redis client."""
        mock = MagicMock(spec=AsyncRedisClient)
        mock.get = AsyncMock(return_value=None)
        mock.set = AsyncMock()
        return mock

    @pytest.mark.asyncio
    async def test_caches_result(
        self, mock_redis_client: MagicMock
    ) -> None:
        """Should cache function result."""
        call_count = 0
        
        @cached(mock_redis_client, ttl=300)
        async def get_data(item_id: int) -> dict:
            nonlocal call_count
            call_count += 1
            return {"id": item_id, "name": "test"}
        
        # First call - cache miss
        result = await get_data(1)
        
        assert result == {"id": 1, "name": "test"}
        assert call_count == 1
        mock_redis_client.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_cached_result(
        self, mock_redis_client: MagicMock
    ) -> None:
        """Should return cached result on hit."""
        mock_redis_client.get.return_value = {"id": 1, "name": "cached"}
        call_count = 0
        
        @cached(mock_redis_client)
        async def get_data(item_id: int) -> dict:
            nonlocal call_count
            call_count += 1
            return {"id": item_id, "name": "fresh"}
        
        result = await get_data(1)
        
        assert result == {"id": 1, "name": "cached"}
        assert call_count == 0  # Function not called

    @pytest.mark.asyncio
    async def test_custom_key_builder(
        self, mock_redis_client: MagicMock
    ) -> None:
        """Should use custom key builder."""
        @cached(
            mock_redis_client,
            key_builder=lambda *args, **kwargs: f"custom:{args[0]}",
        )
        async def get_data(item_id: int) -> dict:
            return {"id": item_id}
        
        await get_data(42)
        
        call_args = mock_redis_client.get.call_args
        assert call_args[0][0] == "custom:42"

    @pytest.mark.asyncio
    async def test_prefix(
        self, mock_redis_client: MagicMock
    ) -> None:
        """Should add prefix to cache key."""
        @cached(mock_redis_client, prefix="myservice")
        async def get_data(item_id: int) -> dict:
            return {"id": item_id}
        
        await get_data(1)
        
        call_args = mock_redis_client.get.call_args
        key = call_args[0][0]
        assert key.startswith("myservice:")


class TestCacheAsideDecorator:
    """Tests for @cache_aside decorator."""

    @pytest.fixture
    def mock_redis_client(self) -> MagicMock:
        """Create mock Redis client."""
        mock = MagicMock(spec=AsyncRedisClient)
        mock.get = AsyncMock(return_value=None)
        mock.set = AsyncMock()
        return mock

    @pytest.mark.asyncio
    async def test_cache_aside_miss(
        self, mock_redis_client: MagicMock
    ) -> None:
        """Should fetch and cache on miss."""
        @cache_aside(mock_redis_client)
        async def get_user(user_id: int) -> dict:
            return {"id": user_id, "name": "John"}
        
        result = await get_user(1)
        
        assert result == {"id": 1, "name": "John"}
        mock_redis_client.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_aside_hit(
        self, mock_redis_client: MagicMock
    ) -> None:
        """Should return cached value on hit."""
        mock_redis_client.get.return_value = {"id": 1, "name": "Cached"}
        
        @cache_aside(mock_redis_client)
        async def get_user(user_id: int) -> dict:
            return {"id": user_id, "name": "Fresh"}
        
        result = await get_user(1)
        
        assert result == {"id": 1, "name": "Cached"}
        mock_redis_client.set.assert_not_called()


class TestInvalidateCacheDecorator:
    """Tests for @invalidate_cache decorator."""

    @pytest.fixture
    def mock_redis_client(self) -> MagicMock:
        """Create mock Redis client."""
        mock = MagicMock(spec=AsyncRedisClient)
        mock.delete = AsyncMock(return_value=True)
        return mock

    @pytest.mark.asyncio
    async def test_invalidates_after_call(
        self, mock_redis_client: MagicMock
    ) -> None:
        """Should invalidate cache after function call."""
        @invalidate_cache(
            mock_redis_client,
            key_builder=lambda user_id, name: f"user:{user_id}",
        )
        async def update_user(user_id: int, name: str) -> dict:
            return {"id": user_id, "name": name}
        
        result = await update_user(1, "Updated")
        
        assert result == {"id": 1, "name": "Updated"}
        mock_redis_client.delete.assert_called_once_with("user:1")

    @pytest.mark.asyncio
    async def test_invalidates_multiple_keys(
        self, mock_redis_client: MagicMock
    ) -> None:
        """Should invalidate multiple cache keys."""
        @invalidate_cache(
            mock_redis_client,
            keys=["user:1", "users:list"],
        )
        async def delete_user(user_id: int) -> bool:
            return True
        
        await delete_user(1)
        
        assert mock_redis_client.delete.call_count == 2
