"""Idempotency key support for safe request retries.

Prevents duplicate side-effects when clients retry API requests.
An idempotency key is stored on first execution; subsequent requests
with the same key return the cached response.

Components:
- :class:`IdempotencyStore` — protocol for persistence backends
- :class:`IdempotencyRecord` — stored execution result
- :class:`InMemoryIdempotencyStore` — test implementation
- :func:`idempotent` — decorator for FastAPI / service methods

Example:
    >>> from shared.idempotency import (
    ...     InMemoryIdempotencyStore, idempotent,
    ... )
    >>>
    >>> store = InMemoryIdempotencyStore()
    >>>
    >>> @idempotent(store=store)
    ... async def charge_payment(idempotency_key: str, amount: int):
    ...     return {"charged": amount}
"""

from __future__ import annotations

from shared.idempotency.base import (
    IdempotencyRecord,
    IdempotencyStore,
    InMemoryIdempotencyStore,
)
from shared.idempotency.decorator import idempotent

__all__ = [
    "IdempotencyRecord",
    "IdempotencyStore",
    "InMemoryIdempotencyStore",
    "idempotent",
]
