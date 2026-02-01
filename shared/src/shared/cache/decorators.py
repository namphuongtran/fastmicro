"""Cache decorators for easy caching.

This module provides decorators for caching function results:
- @cached: Simple caching with TTL
- @cache_aside: Cache-aside pattern
- @invalidate_cache: Cache invalidation on update
- @cached_property: Caching for instance methods

All decorators work with any CacheBackend implementation.
"""

from __future__ import annotations

import functools
import hashlib
import inspect
import json
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, ParamSpec, TypeVar

if TYPE_CHECKING:
    from collections.abc import Awaitable

from shared.cache.base import CacheBackend

P = ParamSpec("P")
T = TypeVar("T")


def build_cache_key(
    func: Callable[..., Any],
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    *,
    prefix: str | None = None,
    skip_self: bool = True,
) -> str:
    """Build cache key from function and arguments.
    
    Creates a deterministic cache key based on:
    - Function module and qualified name
    - Positional and keyword arguments (JSON-serialized)
    
    Args:
        func: The function being cached.
        args: Positional arguments.
        kwargs: Keyword arguments.
        prefix: Optional key prefix.
        skip_self: Skip first argument if it's 'self' or 'cls'.
        
    Returns:
        Cache key string (hashed if > 200 chars).
        
    Example:
        >>> def get_user(user_id: int) -> dict:
        ...     pass
        >>> build_cache_key(get_user, (123,), {})
        'module:get_user:123'
    """
    key_parts: list[str] = []

    # Add prefix if provided
    if prefix:
        key_parts.append(prefix)

    # Add function identity
    key_parts.append(func.__module__)
    key_parts.append(func.__qualname__)

    # Determine if we should skip first argument (self/cls)
    args_to_use = args
    if skip_self and args:
        sig = inspect.signature(func)
        params = list(sig.parameters.keys())
        if params and params[0] in ("self", "cls"):
            args_to_use = args[1:]

    # Add args to key
    for arg in args_to_use:
        try:
            key_parts.append(json.dumps(arg, sort_keys=True, default=str))
        except (TypeError, ValueError):
            key_parts.append(str(arg))

    # Add kwargs to key (sorted for consistency)
    for k, v in sorted(kwargs.items()):
        try:
            key_parts.append(f"{k}={json.dumps(v, sort_keys=True, default=str)}")
        except (TypeError, ValueError):
            key_parts.append(f"{k}={v}")

    key_string = ":".join(key_parts)

    # Hash if too long (Redis key limit and readability)
    if len(key_string) > 200:
        hash_suffix = hashlib.sha256(key_string.encode()).hexdigest()[:16]
        short_prefix = key_string[:100]
        return f"{short_prefix}:{hash_suffix}"

    return key_string


def cached(
    cache: CacheBackend[Any],
    *,
    ttl: int | None = None,
    prefix: str | None = None,
    key_builder: Callable[..., str] | None = None,
    skip_self: bool = True,
) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:
    """Decorator for caching async function results.
    
    Implements cache-aside pattern:
    1. Check cache for existing value
    2. If found, return cached value
    3. If not found, call function
    4. Cache result and return
    
    Args:
        cache: Any CacheBackend implementation (memory, redis, tiered).
        ttl: Cache TTL in seconds (uses backend default if None).
        prefix: Key prefix for namespacing.
        key_builder: Custom function to build cache key.
        skip_self: Skip 'self'/'cls' argument in key building.
        
    Returns:
        Decorated function.
        
    Example:
        >>> from shared.cache import TieredCacheManager, CacheConfig
        >>> cache = TieredCacheManager(CacheConfig())
        >>> 
        >>> @cached(cache, ttl=300, prefix="users")
        ... async def get_user(user_id: int) -> dict:
        ...     return await db.fetch_user(user_id)
        >>>
        >>> # With custom key builder
        >>> @cached(cache, key_builder=lambda id: f"user:{id}")
        ... async def get_user_v2(user_id: int) -> dict:
        ...     return await db.fetch_user(user_id)
    """
    def decorator(
        func: Callable[P, Awaitable[T]]
    ) -> Callable[P, Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            # Build cache key
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
                if prefix:
                    cache_key = f"{prefix}:{cache_key}"
            else:
                cache_key = build_cache_key(
                    func, args, kwargs,
                    prefix=prefix,
                    skip_self=skip_self,
                )

            # Try to get from cache
            cached_value = await cache.get(cache_key)
            if cached_value is not None:
                return cached_value  # type: ignore

            # Call function and cache result
            result = await func(*args, **kwargs)

            # Don't cache None results
            if result is not None:
                await cache.set(cache_key, result, ttl=ttl)

            return result

        # Add utility methods to wrapper
        wrapper.cache = cache  # type: ignore
        wrapper.build_key = lambda *a, **kw: (  # type: ignore
            key_builder(*a, **kw) if key_builder
            else build_cache_key(func, a, kw, prefix=prefix, skip_self=skip_self)
        )

        return wrapper

    return decorator


def cache_aside(
    cache: CacheBackend[Any],
    *,
    ttl: int | None = None,
    prefix: str | None = None,
    key_builder: Callable[..., str] | None = None,
    skip_self: bool = True,
) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:
    """Decorator implementing cache-aside pattern.
    
    Alias for @cached - explicitly named for pattern clarity.
    
    The cache-aside pattern (also known as lazy loading):
    - Application checks cache before calling data source
    - Application populates cache on cache miss
    - Application is responsible for cache management
    
    Args:
        cache: Any CacheBackend implementation.
        ttl: Cache TTL in seconds.
        prefix: Key prefix for namespacing.
        key_builder: Custom function to build cache key.
        skip_self: Skip 'self'/'cls' argument in key building.
        
    Returns:
        Decorated function.
        
    Example:
        >>> @cache_aside(cache, ttl=600, prefix="products")
        ... async def get_product(product_id: str) -> dict:
        ...     return await catalog_service.fetch(product_id)
    """
    return cached(
        cache,
        ttl=ttl,
        prefix=prefix,
        key_builder=key_builder,
        skip_self=skip_self,
    )


def invalidate_cache(
    cache: CacheBackend[Any],
    *,
    keys: list[str] | None = None,
    prefix: str | None = None,
    key_builder: Callable[..., str] | None = None,
    before: bool = False,
) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:
    """Decorator for invalidating cache on data mutation.
    
    Automatically invalidates cache entries when data changes.
    Useful for write operations (create, update, delete).
    
    Args:
        cache: Any CacheBackend implementation.
        keys: Static list of keys to invalidate.
        prefix: Key prefix to add to built keys.
        key_builder: Function to build key from arguments.
        before: If True, invalidate before function execution.
        
    Returns:
        Decorated function.
        
    Example:
        >>> @invalidate_cache(cache, key_builder=lambda id, data: f"user:{id}")
        ... async def update_user(user_id: int, data: dict) -> dict:
        ...     return await db.update_user(user_id, data)
        >>>
        >>> # Invalidate multiple keys
        >>> @invalidate_cache(cache, keys=["users:list", "users:count"])
        ... async def create_user(data: dict) -> dict:
        ...     return await db.create_user(data)
        >>>
        >>> # Invalidate before execution (for deletes)
        >>> @invalidate_cache(cache, key_builder=lambda id: f"user:{id}", before=True)
        ... async def delete_user(user_id: int) -> bool:
        ...     return await db.delete_user(user_id)
    """
    def decorator(
        func: Callable[P, Awaitable[T]]
    ) -> Callable[P, Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            async def do_invalidate() -> None:
                """Perform cache invalidation."""
                # Invalidate static keys
                if keys:
                    for key in keys:
                        full_key = f"{prefix}:{key}" if prefix else key
                        await cache.delete(full_key)

                # Invalidate dynamic key
                if key_builder:
                    key = key_builder(*args, **kwargs)
                    full_key = f"{prefix}:{key}" if prefix else key
                    await cache.delete(full_key)

            if before:
                await do_invalidate()

            # Execute the function
            result = await func(*args, **kwargs)

            if not before:
                await do_invalidate()

            return result

        return wrapper

    return decorator


def cached_method(
    cache: CacheBackend[Any],
    *,
    ttl: int | None = None,
    prefix: str | None = None,
    key_builder: Callable[..., str] | None = None,
    include_instance_id: bool = True,
) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:
    """Decorator for caching instance method results.
    
    Similar to @cached but designed for class instance methods.
    Can optionally include instance identity in cache key.
    
    Args:
        cache: Any CacheBackend implementation.
        ttl: Cache TTL in seconds.
        prefix: Key prefix for namespacing.
        key_builder: Custom function to build cache key.
        include_instance_id: Include id(self) in cache key.
        
    Returns:
        Decorated method.
        
    Example:
        >>> class UserService:
        ...     @cached_method(cache, ttl=300, prefix="user_service")
        ...     async def get_user(self, user_id: int) -> dict:
        ...         return await self.db.fetch_user(user_id)
    """
    def decorator(
        func: Callable[P, Awaitable[T]]
    ) -> Callable[P, Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            # Build cache key
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            elif include_instance_id and args:
                # Include instance id for per-instance caching
                instance_id = id(args[0])
                base_key = build_cache_key(
                    func, args[1:], kwargs,
                    prefix=None,
                    skip_self=False,
                )
                cache_key = f"{instance_id}:{base_key}"
            else:
                cache_key = build_cache_key(
                    func, args, kwargs,
                    prefix=None,
                    skip_self=True,
                )

            # Add prefix
            if prefix:
                cache_key = f"{prefix}:{cache_key}"

            # Try to get from cache
            cached_value = await cache.get(cache_key)
            if cached_value is not None:
                return cached_value  # type: ignore

            # Call method and cache result
            result = await func(*args, **kwargs)

            if result is not None:
                await cache.set(cache_key, result, ttl=ttl)

            return result

        return wrapper

    return decorator


# Backward compatibility aliases
_build_default_key = build_cache_key
