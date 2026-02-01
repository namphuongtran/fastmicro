"""Two-tier caching system for microservices.

This module provides enterprise-ready caching utilities with:
- Two-tier caching: L1 (memory) + L2 (Redis)
- Multiple backends: Memory, Redis, Null
- Cache decorators: @cached, @cache_aside, @invalidate_cache
- Distributed locking via Redis

Architecture:
    - L1 (Memory): ~1μs latency, per-process, cachetools TTLCache
    - L2 (Redis): ~1-5ms latency, shared, optional

Example:
    >>> from shared.cache import (
    ...     TieredCacheManager,
    ...     CacheConfig,
    ...     create_cache,
    ...     cached,
    ... )
    ...
    >>> # Simple: Memory only
    >>> cache = create_cache(namespace="myapp")
    >>>
    >>> # Full: Memory + Redis
    >>> config = CacheConfig(
    ...     redis_enabled=True,
    ...     redis_url="redis://localhost:6379/0"
    ... )
    >>> cache = TieredCacheManager(config)
    >>> await cache.connect()
    >>>
    >>> # Using decorators
    >>> @cached(cache, ttl=300)
    ... async def get_user(user_id: int) -> dict:
    ...     return await db.fetch_user(user_id)

Legacy Support:
    AsyncRedisClient and RedisConfig from redis_client module
    are still available for backward compatibility.
"""

# Core abstractions
# Backends
from shared.cache.backends import (
    MemoryCache,
    NullCache,
    RedisCache,
)
from shared.cache.backends.redis import RedisConfig as RedisCacheConfig
from shared.cache.base import (
    AbstractCacheBackend,
    CacheBackend,
    CacheConnectionError,
    CacheError,
    CacheSerializationError,
    JsonSerializer,
    NullSerializer,
    PickleSerializer,
    Serializer,
)

# Decorators
from shared.cache.decorators import (
    build_cache_key,
    cache_aside,
    cached,
    cached_method,
    invalidate_cache,
)

# Lock
from shared.cache.lock import (
    DistributedLock,
    LockAcquisitionError,
    LockConfig,
    LockReleaseError,
)

# Manager
from shared.cache.manager import (
    CacheConfig,
    TieredCacheManager,
    create_cache,
)

# Legacy support - keep for backward compatibility
from shared.cache.redis_client import (
    AsyncRedisClient,
    RedisConfig,
)
from shared.cache.redis_client import (
    CacheError as LegacyCacheError,
)
from shared.cache.redis_client import (
    ConnectionError as LegacyConnectionError,
)

__all__ = [
    # Core Protocol
    "CacheBackend",
    "AbstractCacheBackend",
    "Serializer",
    "NullSerializer",
    "JsonSerializer",
    "PickleSerializer",
    # Backends
    "MemoryCache",
    "RedisCache",
    "NullCache",
    "RedisCacheConfig",
    # Manager
    "TieredCacheManager",
    "CacheConfig",
    "create_cache",
    # Decorators
    "cached",
    "cache_aside",
    "invalidate_cache",
    "cached_method",
    "build_cache_key",
    # Lock
    "DistributedLock",
    "LockConfig",
    # Errors
    "CacheError",
    "CacheConnectionError",
    "CacheSerializationError",
    "LockAcquisitionError",
    "LockReleaseError",
    # Legacy (backward compatibility)
    "AsyncRedisClient",
    "RedisConfig",
]
