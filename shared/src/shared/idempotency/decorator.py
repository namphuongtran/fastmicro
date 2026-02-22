"""Idempotency decorator for async service methods / FastAPI endpoints.

The ``@idempotent`` decorator intercepts calls, checks for an existing
:class:`IdempotencyRecord`, and either returns the cached result or
executes the function and stores the outcome.

Usage:
    >>> @idempotent(store=my_store, key_param="idempotency_key")
    ... async def create_payment(idempotency_key: str, amount: int):
    ...     return {"status": "charged", "amount": amount}
"""

from __future__ import annotations

import functools
import logging
from collections.abc import Callable, Coroutine
from typing import Any, ParamSpec, TypeVar

from shared.idempotency.base import (
    IdempotencyRecord,
    IdempotencyStatus,
    IdempotencyStore,
)

P = ParamSpec("P")
R = TypeVar("R")

logger = logging.getLogger(__name__)


class DuplicateRequestError(Exception):
    """Raised when a request with the same key is already in flight."""

    def __init__(self, key: str) -> None:
        self.key = key
        super().__init__(f"Request with idempotency key '{key}' is already being processed")


def idempotent(
    *,
    store: IdempotencyStore,
    key_param: str = "idempotency_key",
    response_code: int = 200,
) -> Callable[
    [Callable[P, Coroutine[Any, Any, R]]],
    Callable[P, Coroutine[Any, Any, R]],
]:
    """Decorator that adds idempotency to an async function.

    The decorated function **must** accept a keyword argument named
    ``key_param`` (default ``"idempotency_key"``).  When a matching
    record is found in the store the cached result is returned
    immediately without re-executing the function.

    Args:
        store: The :class:`IdempotencyStore` backend to use.
        key_param: Name of the function parameter holding the key.
        response_code: HTTP status code to store on success.

    Returns:
        Decorated async function.
    """

    def decorator(
        fn: Callable[P, Coroutine[Any, Any, R]],
    ) -> Callable[P, Coroutine[Any, Any, R]]:
        @functools.wraps(fn)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            key: str | None = kwargs.get(key_param)  # type: ignore[arg-type]
            if key is None:
                # No idempotency key provided — execute normally
                return await fn(*args, **kwargs)

            # Check for existing record
            existing = await store.get(key)
            if existing is not None:
                if existing.status == IdempotencyStatus.IN_PROGRESS:
                    raise DuplicateRequestError(key)
                if existing.status == IdempotencyStatus.COMPLETED:
                    logger.debug("Idempotency hit for key=%s", key)
                    return existing.response_body  # type: ignore[return-value]
                # FAILED — allow retry by falling through

            # Lock the key
            record = IdempotencyRecord(
                key=key,
                status=IdempotencyStatus.IN_PROGRESS,
            )
            await store.save(record)

            try:
                result = await fn(*args, **kwargs)
                record = IdempotencyRecord(
                    key=key,
                    status=IdempotencyStatus.COMPLETED,
                    response_code=response_code,
                    response_body=result,
                )
                await store.save(record)
                return result

            except Exception:
                record = IdempotencyRecord(
                    key=key,
                    status=IdempotencyStatus.FAILED,
                    response_body=None,
                )
                await store.save(record)
                raise

        return wrapper

    return decorator
