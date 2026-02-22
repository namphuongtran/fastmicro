"""Core idempotency types and in-memory store."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol, runtime_checkable


class IdempotencyStatus(str, enum.Enum):
    """Processing status of an idempotency key."""

    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class IdempotencyRecord:
    """Stored result for an idempotency key.

    Attributes:
        key: The idempotency key value.
        status: Processing status.
        response_code: HTTP status code of the original response.
        response_body: Serialized response body.
        created_at: When the key was first seen.
        expires_at: When the key should be auto-purged.
    """

    key: str
    status: IdempotencyStatus = IdempotencyStatus.IN_PROGRESS
    response_code: int | None = None
    response_body: Any = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime | None = None


@runtime_checkable
class IdempotencyStore(Protocol):
    """Protocol for idempotency key persistence.

    Implementations may use Redis, PostgreSQL, DynamoDB, etc.
    """

    async def get(self, key: str) -> IdempotencyRecord | None:
        """Retrieve a record by key, or ``None`` if not found / expired."""
        ...

    async def save(self, record: IdempotencyRecord) -> None:
        """Persist a new or updated record."""
        ...

    async def delete(self, key: str) -> None:
        """Remove a record."""
        ...


class InMemoryIdempotencyStore:
    """In-memory idempotency store for testing.

    Automatically skips expired records on read.

    Example:
        >>> store = InMemoryIdempotencyStore(ttl_seconds=3600)
        >>> await store.save(IdempotencyRecord(key="abc", status=IdempotencyStatus.COMPLETED))
        >>> record = await store.get("abc")
        >>> assert record is not None
    """

    def __init__(self, *, ttl_seconds: int = 86400) -> None:
        self._records: dict[str, IdempotencyRecord] = {}
        self.ttl_seconds = ttl_seconds

    async def get(self, key: str) -> IdempotencyRecord | None:
        record = self._records.get(key)
        if record is None:
            return None
        if record.expires_at and datetime.now(UTC) > record.expires_at:
            del self._records[key]
            return None
        return record

    async def save(self, record: IdempotencyRecord) -> None:
        if record.expires_at is None:
            record = IdempotencyRecord(
                key=record.key,
                status=record.status,
                response_code=record.response_code,
                response_body=record.response_body,
                created_at=record.created_at,
                expires_at=datetime.now(UTC) + timedelta(seconds=self.ttl_seconds),
            )
        self._records[record.key] = record

    async def delete(self, key: str) -> None:
        self._records.pop(key, None)

    def clear(self) -> None:
        self._records.clear()
