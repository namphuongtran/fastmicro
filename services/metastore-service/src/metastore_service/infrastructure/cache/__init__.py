"""Cache infrastructure package.

Uses the shared library's TieredCacheManager for two-tier caching:
- L1: In-memory cache (fast, per-process)
- L2: Redis cache (distributed, shared across instances)
"""

from shared.cache import CacheConfig, TieredCacheManager
from shared.cache.base import CacheBackend

__all__ = [
    "CacheConfig",
    "TieredCacheManager",
    "CacheBackend",
]
