"""Distributed locking with Redis.

This module provides distributed locking functionality:
- DistributedLock: Redis-based distributed lock
- LockConfig: Lock configuration
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Self

if TYPE_CHECKING:
    from shared.cache.redis_client import AsyncRedisClient


class LockAcquisitionError(Exception):
    """Error when lock acquisition fails."""

    pass


class LockReleaseError(Exception):
    """Error when lock release fails."""

    pass


@dataclass
class LockConfig:
    """Configuration for distributed lock.
    
    Attributes:
        name: Lock name/identifier.
        timeout: Lock timeout in seconds.
        blocking: Whether to block waiting for lock.
        blocking_timeout: Max time to wait for lock.
        retry_interval: Interval between retry attempts.
    """

    name: str
    timeout: float = 30.0
    blocking: bool = True
    blocking_timeout: float = 10.0
    retry_interval: float = 0.1


class DistributedLock:
    """Redis-based distributed lock.
    
    Provides mutual exclusion across distributed processes.
    
    Example:
        >>> config = LockConfig(name="resource-lock", timeout=30)
        >>> lock = DistributedLock(redis_client, config)
        >>> async with lock:
        ...     # Protected critical section
        ...     await process_resource()
    """

    def __init__(
        self,
        client: AsyncRedisClient,
        config: LockConfig,
    ) -> None:
        """Initialize distributed lock.
        
        Args:
            client: Redis client instance.
            config: Lock configuration.
        """
        self._client = client
        self._config = config
        self._token: str | None = None
        self._key = f"lock:{config.name}"

    @property
    def name(self) -> str:
        """Get lock name."""
        return self._config.name

    async def acquire(self) -> bool:
        """Acquire the lock.
        
        Returns:
            True if lock was acquired.
        """
        self._token = str(uuid.uuid4())
        redis = self._client._redis
        
        if redis is None:
            return False
        
        if self._config.blocking:
            return await self._acquire_blocking(redis)
        else:
            return await self._acquire_non_blocking(redis)

    async def _acquire_non_blocking(self, redis: Any) -> bool:
        """Try to acquire lock without blocking.
        
        Args:
            redis: Redis client.
            
        Returns:
            True if acquired.
        """
        result = await redis.set(
            self._key,
            self._token,
            nx=True,
            ex=int(self._config.timeout),
        )
        return bool(result)

    async def _acquire_blocking(self, redis: Any) -> bool:
        """Acquire lock with blocking and retries.
        
        Args:
            redis: Redis client.
            
        Returns:
            True if acquired within timeout.
        """
        deadline = asyncio.get_event_loop().time() + self._config.blocking_timeout
        
        while asyncio.get_event_loop().time() < deadline:
            result = await redis.set(
                self._key,
                self._token,
                nx=True,
                ex=int(self._config.timeout),
            )
            if result:
                return True
            
            await asyncio.sleep(self._config.retry_interval)
        
        return False

    async def release(self) -> None:
        """Release the lock.
        
        Raises:
            LockReleaseError: If lock cannot be released.
        """
        if self._token is None:
            return
        
        redis = self._client._redis
        if redis is None:
            return
        
        # Only delete if we own the lock
        current_token = await redis.get(self._key)
        if current_token:
            token_str = current_token.decode() if isinstance(current_token, bytes) else current_token
            if token_str == self._token:
                await redis.delete(self._key)
        
        self._token = None

    async def extend(self, additional_time: int) -> bool:
        """Extend lock timeout.
        
        Args:
            additional_time: Additional time in seconds.
            
        Returns:
            True if extended successfully.
        """
        if self._token is None:
            return False
        
        redis = self._client._redis
        if redis is None:
            return False
        
        # Verify we own the lock
        current_token = await redis.get(self._key)
        if current_token:
            token_str = current_token.decode() if isinstance(current_token, bytes) else current_token
            if token_str == self._token:
                await redis.expire(self._key, additional_time)
                return True
        
        return False

    async def is_locked(self) -> bool:
        """Check if resource is locked.
        
        Returns:
            True if resource is locked (by anyone).
        """
        redis = self._client._redis
        if redis is None:
            return False
        
        value = await redis.get(self._key)
        return value is not None

    async def __aenter__(self) -> Self:
        """Enter async context, acquiring lock."""
        acquired = await self.acquire()
        if not acquired:
            raise LockAcquisitionError(
                f"Failed to acquire lock: {self._config.name}"
            )
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Exit async context, releasing lock."""
        await self.release()
