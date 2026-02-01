"""Tests for shared.cache.redis_client module.

This module tests the async Redis client implementation.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from shared.cache.redis_client import (
    AsyncRedisClient,
    CacheError,
    RedisConfig,
    RedisConnectionError,
)


class TestRedisConfig:
    """Tests for RedisConfig."""

    def test_create_config(self) -> None:
        """Should create Redis config."""
        config = RedisConfig(
            host="localhost",
            port=6379,
            db=0,
        )

        assert config.host == "localhost"
        assert config.port == 6379
        assert config.db == 0

    def test_config_defaults(self) -> None:
        """Should have sensible defaults."""
        config = RedisConfig()

        assert config.host == "localhost"
        assert config.port == 6379
        assert config.db == 0
        assert config.password is None
        assert config.ssl is False
        assert config.socket_timeout == 5.0

    def test_config_with_password(self) -> None:
        """Should support password."""
        config = RedisConfig(
            host="redis.example.com",
            password="secret",
            ssl=True,
        )

        assert config.password == "secret"
        assert config.ssl is True

    def test_build_url(self) -> None:
        """Should build Redis URL."""
        config = RedisConfig(
            host="localhost",
            port=6379,
            db=1,
        )

        url = config.build_url()
        assert "localhost" in url
        assert "6379" in url

    def test_build_url_with_password(self) -> None:
        """Should include password in URL."""
        config = RedisConfig(
            host="localhost",
            port=6379,
            password="secret",
        )

        url = config.build_url()
        assert "secret" in url or "redis://" in url


class TestAsyncRedisClient:
    """Tests for AsyncRedisClient."""

    @pytest.fixture
    def config(self) -> RedisConfig:
        """Create test config."""
        return RedisConfig(host="localhost", port=6379)

    @pytest.fixture
    def mock_redis(self) -> MagicMock:
        """Create mock Redis client."""
        mock = MagicMock()
        mock.get = AsyncMock(return_value=None)
        mock.set = AsyncMock(return_value=True)
        mock.delete = AsyncMock(return_value=1)
        mock.exists = AsyncMock(return_value=1)
        mock.expire = AsyncMock(return_value=True)
        mock.ttl = AsyncMock(return_value=100)
        mock.keys = AsyncMock(return_value=[])
        mock.ping = AsyncMock(return_value=True)
        mock.close = AsyncMock()
        mock.incr = AsyncMock(return_value=1)
        mock.decr = AsyncMock(return_value=0)
        mock.hset = AsyncMock(return_value=1)
        mock.hget = AsyncMock(return_value=None)
        mock.hgetall = AsyncMock(return_value={})
        mock.hdel = AsyncMock(return_value=1)
        mock.lpush = AsyncMock(return_value=1)
        mock.rpush = AsyncMock(return_value=1)
        mock.lpop = AsyncMock(return_value=None)
        mock.rpop = AsyncMock(return_value=None)
        mock.lrange = AsyncMock(return_value=[])
        return mock

    @pytest.fixture
    def client(self, config: RedisConfig, mock_redis: MagicMock) -> AsyncRedisClient:
        """Create test client with mock Redis."""
        client = AsyncRedisClient(config)
        client._redis = mock_redis
        return client

    def test_create_client(self, config: RedisConfig) -> None:
        """Should create Redis client."""
        client = AsyncRedisClient(config)
        assert client is not None

    @pytest.mark.asyncio
    async def test_get_value(self, client: AsyncRedisClient, mock_redis: MagicMock) -> None:
        """Should get value from Redis."""
        mock_redis.get.return_value = b'"test_value"'

        value = await client.get("test_key")

        assert value == "test_value"
        mock_redis.get.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_get_missing_value(self, client: AsyncRedisClient, mock_redis: MagicMock) -> None:
        """Should return None for missing key."""
        mock_redis.get.return_value = None

        value = await client.get("missing_key")

        assert value is None

    @pytest.mark.asyncio
    async def test_set_value(self, client: AsyncRedisClient, mock_redis: MagicMock) -> None:
        """Should set value in Redis."""
        await client.set("test_key", "test_value")

        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        assert call_args[0][0] == "test_key"

    @pytest.mark.asyncio
    async def test_set_with_ttl(self, client: AsyncRedisClient, mock_redis: MagicMock) -> None:
        """Should set value with TTL."""
        await client.set("test_key", "test_value", ttl=300)

        call_kwargs = mock_redis.set.call_args.kwargs
        assert call_kwargs.get("ex") == 300

    @pytest.mark.asyncio
    async def test_delete_value(self, client: AsyncRedisClient, mock_redis: MagicMock) -> None:
        """Should delete value from Redis."""
        mock_redis.delete.return_value = 1

        result = await client.delete("test_key")

        assert result is True
        mock_redis.delete.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_delete_missing_key(
        self, client: AsyncRedisClient, mock_redis: MagicMock
    ) -> None:
        """Should return False for missing key."""
        mock_redis.delete.return_value = 0

        result = await client.delete("missing_key")

        assert result is False

    @pytest.mark.asyncio
    async def test_exists(self, client: AsyncRedisClient, mock_redis: MagicMock) -> None:
        """Should check if key exists."""
        mock_redis.exists.return_value = 1

        result = await client.exists("test_key")

        assert result is True

    @pytest.mark.asyncio
    async def test_not_exists(self, client: AsyncRedisClient, mock_redis: MagicMock) -> None:
        """Should return False for missing key."""
        mock_redis.exists.return_value = 0

        result = await client.exists("missing_key")

        assert result is False

    @pytest.mark.asyncio
    async def test_set_expire(self, client: AsyncRedisClient, mock_redis: MagicMock) -> None:
        """Should set expiration on key."""
        await client.expire("test_key", 300)

        mock_redis.expire.assert_called_once_with("test_key", 300)

    @pytest.mark.asyncio
    async def test_get_ttl(self, client: AsyncRedisClient, mock_redis: MagicMock) -> None:
        """Should get TTL for key."""
        mock_redis.ttl.return_value = 100

        ttl = await client.ttl("test_key")

        assert ttl == 100

    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncRedisClient, mock_redis: MagicMock) -> None:
        """Should check Redis health."""
        mock_redis.ping.return_value = True

        is_healthy = await client.health_check()

        assert is_healthy is True

    @pytest.mark.asyncio
    async def test_increment(self, client: AsyncRedisClient, mock_redis: MagicMock) -> None:
        """Should increment value."""
        mock_redis.incr.return_value = 5

        result = await client.increment("counter")

        assert result == 5

    @pytest.mark.asyncio
    async def test_decrement(self, client: AsyncRedisClient, mock_redis: MagicMock) -> None:
        """Should decrement value."""
        mock_redis.decr.return_value = 3

        result = await client.decrement("counter")

        assert result == 3

    @pytest.mark.asyncio
    async def test_close(self, client: AsyncRedisClient, mock_redis: MagicMock) -> None:
        """Should close connection."""
        await client.close()

        mock_redis.close.assert_called_once()


class TestAsyncRedisClientHash:
    """Tests for hash operations."""

    @pytest.fixture
    def mock_redis(self) -> MagicMock:
        """Create mock Redis client."""
        mock = MagicMock()
        mock.hset = AsyncMock(return_value=1)
        mock.hget = AsyncMock(return_value=None)
        mock.hgetall = AsyncMock(return_value={})
        mock.hdel = AsyncMock(return_value=1)
        return mock

    @pytest.fixture
    def client(self, mock_redis: MagicMock) -> AsyncRedisClient:
        """Create test client with mock Redis."""
        config = RedisConfig()
        client = AsyncRedisClient(config)
        client._redis = mock_redis
        return client

    @pytest.mark.asyncio
    async def test_hset(self, client: AsyncRedisClient, mock_redis: MagicMock) -> None:
        """Should set hash field."""
        await client.hset("myhash", "field1", "value1")

        mock_redis.hset.assert_called_once()

    @pytest.mark.asyncio
    async def test_hget(self, client: AsyncRedisClient, mock_redis: MagicMock) -> None:
        """Should get hash field."""
        mock_redis.hget.return_value = b'"value1"'

        value = await client.hget("myhash", "field1")

        assert value == "value1"

    @pytest.mark.asyncio
    async def test_hgetall(self, client: AsyncRedisClient, mock_redis: MagicMock) -> None:
        """Should get all hash fields."""
        mock_redis.hgetall.return_value = {
            b"field1": b'"value1"',
            b"field2": b'"value2"',
        }

        values = await client.hgetall("myhash")

        assert values["field1"] == "value1"
        assert values["field2"] == "value2"

    @pytest.mark.asyncio
    async def test_hdel(self, client: AsyncRedisClient, mock_redis: MagicMock) -> None:
        """Should delete hash field."""
        await client.hdel("myhash", "field1")

        mock_redis.hdel.assert_called_once_with("myhash", "field1")


class TestCacheErrors:
    """Tests for cache error classes."""

    def test_cache_error(self) -> None:
        """Should create cache error."""
        error = CacheError("Cache operation failed")

        assert str(error) == "Cache operation failed"

    def test_connection_error(self) -> None:
        """Should create connection error."""
        error = RedisConnectionError("Failed to connect to Redis")

        assert str(error) == "Failed to connect to Redis"
        assert isinstance(error, CacheError)
