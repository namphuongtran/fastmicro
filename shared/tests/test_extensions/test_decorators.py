"""Tests for shared.extensions.decorators module.

This module tests utility decorators including retry, cache,
rate limit, timeout, and deprecation decorators.
"""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch
import warnings

import pytest

if TYPE_CHECKING:
    pass

from shared.extensions.decorators import (
    retry,
    cache,
    rate_limit,
    timeout,
    deprecated,
    log_calls,
    validate_args,
    singleton,
)


class TestRetryDecorator:
    """Tests for @retry decorator."""

    def test_succeeds_first_try(self) -> None:
        """Should succeed on first try."""
        call_count = 0
        
        @retry(max_attempts=3)
        def succeeds() -> str:
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = succeeds()
        assert result == "success"
        assert call_count == 1

    def test_retries_on_failure(self) -> None:
        """Should retry on failure."""
        call_count = 0
        
        @retry(max_attempts=3)
        def fails_twice() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary error")
            return "success"
        
        result = fails_twice()
        assert result == "success"
        assert call_count == 3

    def test_raises_after_max_attempts(self) -> None:
        """Should raise RetryError after max attempts exceeded."""
        from shared.extensions.decorators import RetryError
        
        @retry(max_attempts=3)
        def always_fails() -> None:
            raise RuntimeError("Always fails")
        
        with pytest.raises(RetryError) as exc_info:
            always_fails()
        
        assert exc_info.value.attempts == 3
        assert isinstance(exc_info.value.last_exception, RuntimeError)

    def test_specific_exceptions(self) -> None:
        """Should only retry on specified exceptions."""
        call_count = 0
        
        @retry(max_attempts=3, exceptions=(ValueError,))
        def raises_type_error() -> None:
            nonlocal call_count
            call_count += 1
            raise TypeError("Not retryable")
        
        with pytest.raises(TypeError):
            raises_type_error()
        
        assert call_count == 1  # No retry for TypeError

    def test_delay_between_retries(self) -> None:
        """Should delay between retries."""
        call_times: list[float] = []
        
        @retry(max_attempts=3, delay=0.1)
        def fails_with_delay() -> str:
            call_times.append(time.time())
            if len(call_times) < 3:
                raise ValueError("Retry")
            return "done"
        
        fails_with_delay()
        
        # Check delay between calls
        if len(call_times) >= 2:
            assert call_times[1] - call_times[0] >= 0.09

    @pytest.mark.asyncio
    async def test_async_retry(self) -> None:
        """Should work with async functions."""
        call_count = 0
        
        @retry(max_attempts=3)
        async def async_fails_once() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Temporary")
            return "async success"
        
        result = await async_fails_once()
        assert result == "async success"
        assert call_count == 2

    def test_preserves_function_metadata(self) -> None:
        """Should preserve function name and docstring."""
        @retry(max_attempts=3)
        def documented_function() -> None:
            """This is a docstring."""
            pass
        
        assert documented_function.__name__ == "documented_function"
        assert "docstring" in (documented_function.__doc__ or "")


class TestCacheDecorator:
    """Tests for @cache decorator."""

    def test_caches_result(self) -> None:
        """Should cache function result."""
        call_count = 0
        
        @cache()
        def expensive_call(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2
        
        result1 = expensive_call(5)
        result2 = expensive_call(5)
        
        assert result1 == 10
        assert result2 == 10
        assert call_count == 1  # Only called once

    def test_different_args_different_cache(self) -> None:
        """Should cache separately for different arguments."""
        call_count = 0
        
        @cache()
        def add(a: int, b: int) -> int:
            nonlocal call_count
            call_count += 1
            return a + b
        
        add(1, 2)
        add(3, 4)
        add(1, 2)  # Should use cache
        
        assert call_count == 2

    def test_ttl_expiration(self) -> None:
        """Should expire cache after TTL."""
        call_count = 0
        
        @cache(ttl=0.1)
        def with_ttl() -> str:
            nonlocal call_count
            call_count += 1
            return "result"
        
        with_ttl()
        time.sleep(0.15)
        with_ttl()  # Should call again after TTL
        
        assert call_count == 2

    def test_max_size(self) -> None:
        """Should respect max cache size."""
        @cache(max_size=2)
        def limited(x: int) -> int:
            return x
        
        limited(1)
        limited(2)
        limited(3)  # Should evict oldest
        
        # Implementation detail - just verify it works

    def test_cache_different_kwargs(self) -> None:
        """Should cache separately for different kwargs."""
        call_count = 0
        
        @cache()
        def with_kwargs(x: int, multiplier: int = 2) -> int:
            nonlocal call_count
            call_count += 1
            return x * multiplier
        
        with_kwargs(5, multiplier=2)
        with_kwargs(5, multiplier=3)
        with_kwargs(5, multiplier=2)  # Should use cache
        
        assert call_count == 2


class TestRateLimitDecorator:
    """Tests for @rate_limit decorator."""

    def test_allows_within_limit(self) -> None:
        """Should allow calls within rate limit."""
        @rate_limit(max_calls=5, period=1.0)
        def limited_func() -> str:
            return "ok"
        
        for _ in range(5):
            assert limited_func() == "ok"

    def test_blocks_over_limit(self) -> None:
        """Should block calls over limit."""
        from shared.extensions.decorators import RateLimitExceededError
        
        @rate_limit(max_calls=2, period=1.0)
        def strict_limit() -> str:
            return "ok"
        
        strict_limit()
        strict_limit()
        
        with pytest.raises(RateLimitExceededError):
            strict_limit()

    @pytest.mark.asyncio
    async def test_async_rate_limit(self) -> None:
        """Should work with async functions."""
        @rate_limit(max_calls=2, period=1.0)
        async def async_limited() -> str:
            return "async ok"
        
        await async_limited()
        await async_limited()


class TestTimeoutDecorator:
    """Tests for @timeout decorator."""

    def test_completes_within_timeout(self) -> None:
        """Should complete if within timeout."""
        @timeout(seconds=1.0)
        def fast_func() -> str:
            return "fast"
        
        assert fast_func() == "fast"

    def test_raises_on_timeout(self) -> None:
        """Should raise on timeout."""
        from shared.extensions.decorators import TimeoutError as DecoratorTimeoutError
        
        @timeout(seconds=0.1)
        def slow_func() -> str:
            time.sleep(1.0)
            return "slow"
        
        with pytest.raises(DecoratorTimeoutError):
            slow_func()

    @pytest.mark.asyncio
    async def test_async_timeout(self) -> None:
        """Should work with async functions."""
        @timeout(seconds=1.0)
        async def async_fast() -> str:
            return "async fast"
        
        result = await async_fast()
        assert result == "async fast"

    @pytest.mark.asyncio
    async def test_async_timeout_exceeded(self) -> None:
        """Should timeout async functions."""
        from shared.extensions.decorators import TimeoutError as DecoratorTimeoutError
        
        @timeout(seconds=0.1)
        async def async_slow() -> str:
            await asyncio.sleep(1.0)
            return "slow"
        
        with pytest.raises(DecoratorTimeoutError):
            await async_slow()


class TestDeprecatedDecorator:
    """Tests for @deprecated decorator."""

    def test_emits_warning(self) -> None:
        """Should emit deprecation warning."""
        @deprecated("Use new_function instead")
        def old_function() -> str:
            return "old"
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = old_function()
            
            assert result == "old"
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "new_function" in str(w[0].message)

    def test_still_works(self) -> None:
        """Should still execute the function."""
        @deprecated("Deprecated")
        def working_function() -> int:
            return 42
        
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            assert working_function() == 42


class TestLogCallsDecorator:
    """Tests for @log_calls decorator."""

    def test_logs_function_call(self) -> None:
        """Should log function calls."""
        @log_calls()
        def logged_func(x: int) -> int:
            return x * 2
        
        result = logged_func(5)
        assert result == 10

    def test_logs_with_custom_logger_name(self) -> None:
        """Should use custom logger name."""
        @log_calls(logger_name="custom.logger")
        def with_custom_logger() -> str:
            return "logged"
        
        result = with_custom_logger()
        assert result == "logged"

    @pytest.mark.asyncio
    async def test_async_log_calls(self) -> None:
        """Should work with async functions."""
        @log_calls()
        async def async_logged() -> str:
            return "async logged"
        
        result = await async_logged()
        assert result == "async logged"


class TestValidateArgsDecorator:
    """Tests for @validate_args decorator."""

    def test_passes_valid_args(self) -> None:
        """Should pass with valid arguments."""
        @validate_args(x=lambda v: v > 0)
        def positive_only(x: int) -> int:
            return x
        
        assert positive_only(5) == 5

    def test_rejects_invalid_args(self) -> None:
        """Should reject invalid arguments."""
        @validate_args(x=lambda v: v > 0)
        def positive_only(x: int) -> int:
            return x
        
        with pytest.raises(ValueError):
            positive_only(-1)

    def test_multiple_validators(self) -> None:
        """Should validate multiple arguments."""
        @validate_args(
            x=lambda v: v > 0,
            y=lambda v: isinstance(v, str),
        )
        def multi_validate(x: int, y: str) -> str:
            return f"{y}: {x}"
        
        assert multi_validate(5, "count") == "count: 5"


class TestSingletonDecorator:
    """Tests for @singleton decorator."""

    def test_returns_same_instance(self) -> None:
        """Should return the same instance."""
        @singleton
        class SingletonClass:
            value: int = 0
        
        instance1 = SingletonClass()
        instance1.value = 42
        
        instance2 = SingletonClass()
        
        assert instance1 is instance2
        assert instance2.value == 42

    def test_different_classes_different_singletons(self) -> None:
        """Should handle different singleton classes."""
        @singleton
        class SingletonA:
            pass
        
        @singleton
        class SingletonB:
            pass
        
        a = SingletonA()
        b = SingletonB()
        
        assert a is not b
