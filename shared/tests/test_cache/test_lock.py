"""Tests for shared.cache.lock module.

This module tests distributed locking.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from shared.cache.lock import (
    DistributedLock,
    LockAcquisitionError,
    LockConfig,
    LockReleaseError,
)
from shared.cache.redis_client import AsyncRedisClient


class TestLockConfig:
    """Tests for LockConfig."""

    def test_create_config(self) -> None:
        """Should create lock config."""
        config = LockConfig(
            name="my-lock",
            timeout=30.0,
            blocking=True,
            blocking_timeout=10.0,
        )

        assert config.name == "my-lock"
        assert config.timeout == 30.0
        assert config.blocking is True
        assert config.blocking_timeout == 10.0

    def test_config_defaults(self) -> None:
        """Should have sensible defaults."""
        config = LockConfig(name="test-lock")

        assert config.timeout == 30.0
        assert config.blocking is True
        assert config.blocking_timeout == 10.0


class TestDistributedLock:
    """Tests for DistributedLock."""

    @pytest.fixture
    def mock_redis(self) -> MagicMock:
        """Create mock Redis client."""
        mock = MagicMock(spec=AsyncRedisClient)
        mock._redis = MagicMock()
        mock._redis.set = AsyncMock(return_value=True)
        mock._redis.get = AsyncMock(return_value=None)
        mock._redis.delete = AsyncMock(return_value=1)
        mock._redis.expire = AsyncMock(return_value=True)
        return mock

    @pytest.fixture
    def config(self) -> LockConfig:
        """Create test config."""
        return LockConfig(
            name="test-lock",
            timeout=10.0,
            blocking=False,
        )

    @pytest.fixture
    def lock(self, mock_redis: MagicMock, config: LockConfig) -> DistributedLock:
        """Create test lock."""
        return DistributedLock(mock_redis, config)

    def test_create_lock(self, mock_redis: MagicMock, config: LockConfig) -> None:
        """Should create distributed lock."""
        lock = DistributedLock(mock_redis, config)

        assert lock is not None
        assert lock.name == "test-lock"

    @pytest.mark.asyncio
    async def test_acquire_lock(self, lock: DistributedLock, mock_redis: MagicMock) -> None:
        """Should acquire lock."""
        mock_redis._redis.set.return_value = True

        acquired = await lock.acquire()

        assert acquired is True

    @pytest.mark.asyncio
    async def test_acquire_lock_failure(self, lock: DistributedLock, mock_redis: MagicMock) -> None:
        """Should handle lock acquisition failure."""
        mock_redis._redis.set.return_value = False

        acquired = await lock.acquire()

        assert acquired is False

    @pytest.mark.asyncio
    async def test_release_lock(self, lock: DistributedLock, mock_redis: MagicMock) -> None:
        """Should release lock."""
        # Simulate owning the lock
        lock._token = "test-token"
        mock_redis._redis.get.return_value = b"test-token"

        await lock.release()

        mock_redis._redis.delete.assert_called()

    @pytest.mark.asyncio
    async def test_context_manager(self, mock_redis: MagicMock, config: LockConfig) -> None:
        """Should work as context manager."""
        mock_redis._redis.set.return_value = True
        mock_redis._redis.get.return_value = None

        lock = DistributedLock(mock_redis, config)

        async with lock:
            # Lock should be acquired
            assert lock._token is not None

    @pytest.mark.asyncio
    async def test_lock_extend(self, lock: DistributedLock, mock_redis: MagicMock) -> None:
        """Should extend lock timeout."""
        lock._token = "test-token"
        mock_redis._redis.get.return_value = b"test-token"

        result = await lock.extend(30)

        assert result is True
        mock_redis._redis.expire.assert_called()

    @pytest.mark.asyncio
    async def test_is_locked(self, lock: DistributedLock, mock_redis: MagicMock) -> None:
        """Should check if resource is locked."""
        mock_redis._redis.get.return_value = b"some-token"

        is_locked = await lock.is_locked()

        assert is_locked is True

    @pytest.mark.asyncio
    async def test_is_not_locked(self, lock: DistributedLock, mock_redis: MagicMock) -> None:
        """Should return False when not locked."""
        mock_redis._redis.get.return_value = None

        is_locked = await lock.is_locked()

        assert is_locked is False


class TestLockErrors:
    """Tests for lock error classes."""

    def test_lock_acquisition_error(self) -> None:
        """Should create lock acquisition error."""
        error = LockAcquisitionError("Failed to acquire lock")

        assert str(error) == "Failed to acquire lock"

    def test_lock_release_error(self) -> None:
        """Should create lock release error."""
        error = LockReleaseError("Failed to release lock")

        assert str(error) == "Failed to release lock"
