"""Utility decorators for microservices.

This module provides common decorators for retry logic, caching,
rate limiting, timeouts, deprecation warnings, logging, and more.
"""

from __future__ import annotations

import asyncio
import builtins
import functools
import hashlib
import logging
import threading
import time
import warnings
from collections import OrderedDict
from collections.abc import Callable
from typing import (
    Any,
    ParamSpec,
    TypeVar,
)

P = ParamSpec("P")
T = TypeVar("T")

logger = logging.getLogger(__name__)


class RetryError(Exception):
    """Raised when all retry attempts fail."""

    def __init__(
        self,
        message: str,
        attempts: int,
        last_exception: Exception | None = None,
    ) -> None:
        super().__init__(message)
        self.attempts = attempts
        self.last_exception = last_exception


class RateLimitExceededError(Exception):
    """Raised when rate limit is exceeded."""

    def __init__(self, message: str = "Rate limit exceeded") -> None:
        super().__init__(message)


class OperationTimeoutError(Exception):
    """Raised when operation times out."""

    def __init__(self, message: str = "Operation timed out") -> None:
        super().__init__(message)


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    exceptions: tuple[type[Exception], ...] | None = None,
    exponential_backoff: bool = False,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Retry a function on failure.

    Args:
        max_attempts: Maximum number of retry attempts.
        delay: Delay between retries in seconds.
        exceptions: Tuple of exception types to catch. If None, catches all.
        exponential_backoff: If True, delay doubles after each attempt.

    Returns:
        Decorated function with retry logic.

    Example:
        >>> @retry(max_attempts=3, delay=1.0)
        ... def unstable_operation():
        ...     # May fail sometimes
        ...     pass
    """
    catch_exceptions = exceptions or (Exception,)

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            last_exception: Exception | None = None
            current_delay = delay

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except catch_exceptions as e:
                    last_exception = e
                    if attempt < max_attempts:
                        time.sleep(current_delay)
                        if exponential_backoff:
                            current_delay *= 2

            raise RetryError(
                f"Failed after {max_attempts} attempts",
                attempts=max_attempts,
                last_exception=last_exception,
            )

        @functools.wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            last_exception: Exception | None = None
            current_delay = delay

            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)  # type: ignore[misc]
                except catch_exceptions as e:
                    last_exception = e
                    if attempt < max_attempts:
                        await asyncio.sleep(current_delay)
                        if exponential_backoff:
                            current_delay *= 2

            raise RetryError(
                f"Failed after {max_attempts} attempts",
                attempts=max_attempts,
                last_exception=last_exception,
            )

        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore[return-value]
        return sync_wrapper

    return decorator


def cache(
    ttl: float | None = None,
    max_size: int = 128,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Cache function results.

    Args:
        ttl: Time-to-live for cached entries in seconds. None means no expiry.
        max_size: Maximum number of cached entries.

    Returns:
        Decorated function with caching.

    Example:
        >>> @cache(ttl=60.0, max_size=100)
        ... def expensive_computation(x: int) -> int:
        ...     return x ** 2
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        # Cache storage: key -> (value, expiry_time)
        cache_store: OrderedDict[str, tuple[T, float | None]] = OrderedDict()
        lock = threading.Lock()

        def _make_key(*args: Any, **kwargs: Any) -> str:
            """Create a hashable cache key from arguments."""
            key_parts = [repr(arg) for arg in args]
            key_parts.extend(f"{k}={v!r}" for k, v in sorted(kwargs.items()))
            key_str = ",".join(key_parts)
            return hashlib.md5(key_str.encode()).hexdigest()

        def _is_expired(expiry: float | None) -> bool:
            """Check if cache entry is expired."""
            if expiry is None:
                return False
            return time.time() > expiry

        def _evict_if_needed() -> None:
            """Evict oldest entries if max_size exceeded."""
            while len(cache_store) >= max_size:
                cache_store.popitem(last=False)

        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            key = _make_key(*args, **kwargs)

            with lock:
                if key in cache_store:
                    value, expiry = cache_store[key]
                    if not _is_expired(expiry):
                        # Move to end (most recently used)
                        cache_store.move_to_end(key)
                        return value
                    # Expired, remove it
                    del cache_store[key]

                # Compute new value
                result = func(*args, **kwargs)

                # Evict old entries if needed
                _evict_if_needed()

                # Store with expiry
                expiry_time = (time.time() + ttl) if ttl else None
                cache_store[key] = (result, expiry_time)

                return result

        # Expose cache control methods
        wrapper.cache_clear = lambda: cache_store.clear()  # type: ignore[attr-defined]
        wrapper.cache_info = lambda: {  # type: ignore[attr-defined]
            "size": len(cache_store),
            "max_size": max_size,
        }

        return wrapper

    return decorator


def rate_limit(
    max_calls: int,
    period: float,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Rate limit function calls.

    Args:
        max_calls: Maximum number of calls allowed.
        period: Time period in seconds.

    Returns:
        Decorated function with rate limiting.

    Raises:
        RateLimitExceededError: When rate limit is exceeded.

    Example:
        >>> @rate_limit(max_calls=10, period=60.0)
        ... def api_call():
        ...     pass
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        call_times: list[float] = []
        lock = threading.Lock()

        def _clean_old_calls() -> None:
            """Remove calls outside the current period."""
            cutoff = time.time() - period
            while call_times and call_times[0] < cutoff:
                call_times.pop(0)

        @functools.wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            with lock:
                _clean_old_calls()
                if len(call_times) >= max_calls:
                    raise RateLimitExceededError(
                        f"Rate limit exceeded: {max_calls} calls per {period}s"
                    )
                call_times.append(time.time())
            return func(*args, **kwargs)

        @functools.wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            with lock:
                _clean_old_calls()
                if len(call_times) >= max_calls:
                    raise RateLimitExceededError(
                        f"Rate limit exceeded: {max_calls} calls per {period}s"
                    )
                call_times.append(time.time())
            return await func(*args, **kwargs)  # type: ignore[misc]

        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore[return-value]
        return sync_wrapper

    return decorator


def timeout(seconds: float) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Add timeout to function execution.

    Args:
        seconds: Maximum execution time in seconds.

    Returns:
        Decorated function with timeout.

    Raises:
        OperationTimeoutError: When execution exceeds timeout.

    Example:
        >>> @timeout(5.0)
        ... def slow_operation():
        ...     time.sleep(10)
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(func, *args, **kwargs)
                try:
                    return future.result(timeout=seconds)
                except concurrent.futures.TimeoutError:
                    raise OperationTimeoutError(
                        f"Operation timed out after {seconds} seconds"
                    ) from None

        @functools.wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            try:
                return await asyncio.wait_for(
                    func(*args, **kwargs),  # type: ignore[arg-type]
                    timeout=seconds,
                )
            except builtins.TimeoutError:
                raise OperationTimeoutError(
                    f"Operation timed out after {seconds} seconds"
                ) from None

        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore[return-value]
        return sync_wrapper

    return decorator


def deprecated(
    reason: str = "",
    version: str | None = None,
    alternative: str | None = None,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Mark a function as deprecated.

    Args:
        reason: Reason for deprecation.
        version: Version when deprecated.
        alternative: Suggested alternative.

    Returns:
        Decorated function that warns on use.

    Example:
        >>> @deprecated(reason="Use new_func instead", version="2.0")
        ... def old_func():
        ...     pass
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            message_parts = [f"{func.__name__} is deprecated"]
            if version:
                message_parts.append(f" since version {version}")
            if reason:
                message_parts.append(f": {reason}")
            if alternative:
                message_parts.append(f". Use {alternative} instead")

            warnings.warn(
                "".join(message_parts),
                DeprecationWarning,
                stacklevel=2,
            )
            return func(*args, **kwargs)

        return wrapper

    return decorator


def log_calls(
    level: int = logging.DEBUG,
    include_args: bool = True,
    include_result: bool = False,
    logger_name: str | None = None,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Log function calls.

    Args:
        level: Logging level.
        include_args: Whether to log arguments.
        include_result: Whether to log return value.
        logger_name: Name of logger to use.

    Returns:
        Decorated function with call logging.

    Example:
        >>> @log_calls(level=logging.INFO)
        ... def important_operation(x: int) -> int:
        ...     return x * 2
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        func_logger = logging.getLogger(logger_name or func.__module__)

        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            if include_args:
                args_repr = [repr(a) for a in args]
                kwargs_repr = [f"{k}={v!r}" for k, v in kwargs.items()]
                signature = ", ".join(args_repr + kwargs_repr)
                func_logger.log(level, "Calling %s(%s)", func.__name__, signature)
            else:
                func_logger.log(level, "Calling %s", func.__name__)

            result = func(*args, **kwargs)

            if include_result:
                func_logger.log(level, "%s returned %r", func.__name__, result)
            else:
                func_logger.log(level, "%s completed", func.__name__)

            return result

        return wrapper

    return decorator


def validate_args(
    **validators: Callable[[Any], bool],
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Validate function arguments.

    Args:
        **validators: Mapping of argument names to validator functions.

    Returns:
        Decorated function with argument validation.

    Raises:
        ValueError: When validation fails.

    Example:
        >>> @validate_args(x=lambda x: x > 0, name=lambda n: len(n) > 0)
        ... def create_user(x: int, name: str) -> dict:
        ...     return {"id": x, "name": name}
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        import inspect

        sig = inspect.signature(func)
        param_names = list(sig.parameters.keys())

        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            # Build dict of all arguments
            bound_args: dict[str, Any] = {}
            for i, arg in enumerate(args):
                if i < len(param_names):
                    bound_args[param_names[i]] = arg
            bound_args.update(kwargs)

            # Validate each argument
            for arg_name, validator in validators.items():
                if arg_name in bound_args:
                    value = bound_args[arg_name]
                    if not validator(value):
                        raise ValueError(f"Validation failed for argument '{arg_name}'")

            return func(*args, **kwargs)

        return wrapper

    return decorator


def singleton(cls: type[T]) -> type[T]:
    """Make a class a singleton.

    Args:
        cls: Class to make singleton.

    Returns:
        Singleton class.

    Example:
        >>> @singleton
        ... class AppConfig:
        ...     def __init__(self):
        ...         self.debug = False
    """
    instances: dict[type, Any] = {}
    lock = threading.Lock()

    @functools.wraps(cls, updated=[])
    class SingletonWrapper(cls):  # type: ignore[valid-type, misc]
        def __new__(cls_inner: type, *args: Any, **kwargs: Any) -> T:
            if cls not in instances:
                with lock:
                    if cls not in instances:
                        instances[cls] = super().__new__(cls_inner)
            return instances[cls]

    return SingletonWrapper
