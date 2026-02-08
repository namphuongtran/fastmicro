"""Transactional Outbox pattern for reliable event publishing.

Implements the Transactional Outbox pattern to guarantee at-least-once
delivery of domain events. Events are written to an outbox table within
the same database transaction as the business operation, then a background
relay process publishes them to the message broker.

This eliminates the dual-write problem between the database and broker.

Architecture:
    1. Service writes entity + outbox entry in one transaction
    2. OutboxRelay polls outbox table for unpublished entries
    3. Relay publishes each entry to the broker and marks it as published
    4. Failed entries are retried with exponential backoff

Example:
    >>> from shared.messaging.outbox import OutboxEntry, OutboxRepository
    >>>
    >>> # Within a Unit of Work transaction:
    >>> outbox_repo = OutboxRepository(session)
    >>> entry = OutboxEntry.from_domain_event(event, source="identity-service")
    >>> await outbox_repo.add(entry)
    >>>
    >>> # In a background task:
    >>> relay = OutboxRelay(outbox_repo, publisher)
    >>> await relay.process_pending(batch_size=50)
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Integer, String, Text, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from shared.ddd.events import DomainEvent
from shared.messaging.serialization import EventSerializer
from shared.messaging.types import EventPublisher

logger = logging.getLogger(__name__)


class OutboxBase(DeclarativeBase):
    """Declarative base for outbox tables.

    Services should use this base class for the outbox table model,
    or integrate OutboxEntry into their existing declarative base.
    """


class OutboxEntry(OutboxBase):
    """Outbox table entry representing a domain event to be published.

    Attributes:
        id: Auto-incrementing primary key.
        event_id: Unique event identifier (for deduplication).
        event_type: Event class name (e.g. "UserCreated").
        aggregate_id: ID of the aggregate that raised the event.
        aggregate_type: Aggregate class name.
        routing_key: Broker routing key (e.g. "user.created").
        payload: JSON-serialized event data.
        source: Originating service name.
        correlation_id: Request correlation ID.
        created_at: When the outbox entry was created.
        published: Whether the entry has been published.
        published_at: When the entry was published.
        retry_count: Number of publish attempts.
        error: Last publish error message.
    """

    __tablename__ = "outbox"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=False, index=True,
    )
    event_type: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    aggregate_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    aggregate_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    routing_key: Mapped[str] = mapped_column(String(255), nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    correlation_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    @classmethod
    def from_domain_event(
        cls,
        event: DomainEvent,
        *,
        source: str = "",
        routing_key: str | None = None,
    ) -> OutboxEntry:
        """Create an outbox entry from a domain event.

        Args:
            event: The domain event to store.
            source: Name of the originating service.
            routing_key: Optional explicit routing key.

        Returns:
            New OutboxEntry ready to be added to a session.
        """
        key = routing_key or _derive_routing_key(event)
        return cls(
            event_id=event.event_id,
            event_type=event.event_type,
            aggregate_id=event.aggregate_id,
            aggregate_type=event.aggregate_type,
            routing_key=key,
            payload=json.dumps(event.to_dict(), default=str),
            source=source,
            correlation_id=event.metadata.get("correlation_id"),
        )


class OutboxRepository:
    """Repository for managing outbox entries within a database session.

    Used within the same Unit of Work transaction as the business
    operation to guarantee atomicity.

    Attributes:
        session: Async SQLAlchemy session.

    Example:
        >>> async with uow:
        ...     await user_repo.add(user)
        ...     await outbox_repo.add(OutboxEntry.from_domain_event(event))
        ...     await uow.commit()
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository.

        Args:
            session: Async SQLAlchemy session (same as the business transaction).
        """
        self._session = session

    async def add(self, entry: OutboxEntry) -> None:
        """Add an outbox entry to the session.

        Args:
            entry: Outbox entry to persist.
        """
        self._session.add(entry)
        await self._session.flush()

    async def get_pending(
        self,
        batch_size: int = 50,
        max_retries: int = 5,
    ) -> list[OutboxEntry]:
        """Fetch unpublished outbox entries for relay processing.

        Args:
            batch_size: Maximum number of entries to return.
            max_retries: Skip entries exceeding this retry count.

        Returns:
            List of pending outbox entries ordered by creation time.
        """
        stmt = (
            select(OutboxEntry)
            .where(
                OutboxEntry.published.is_(False),
                OutboxEntry.retry_count < max_retries,
            )
            .order_by(OutboxEntry.created_at)
            .limit(batch_size)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def mark_published(self, entry_id: int) -> None:
        """Mark an outbox entry as successfully published.

        Args:
            entry_id: Primary key of the entry.
        """
        stmt = (
            update(OutboxEntry)
            .where(OutboxEntry.id == entry_id)
            .values(
                published=True,
                published_at=datetime.now(UTC),
            )
        )
        await self._session.execute(stmt)

    async def mark_failed(self, entry_id: int, error: str) -> None:
        """Record a publish failure and increment retry count.

        Args:
            entry_id: Primary key of the entry.
            error: Error description.
        """
        stmt = (
            update(OutboxEntry)
            .where(OutboxEntry.id == entry_id)
            .values(
                retry_count=OutboxEntry.retry_count + 1,
                error=error,
            )
        )
        await self._session.execute(stmt)


class OutboxRelay:
    """Background process that relays outbox entries to a message broker.

    Polls the outbox table for unpublished entries, publishes them
    to the configured broker, and marks them as published.

    Attributes:
        outbox_repo: Repository for accessing outbox entries.
        publisher: Event publisher (RabbitMQ or Kafka).
        serializer: Event serializer for reconstructing wire format.

    Example:
        >>> relay = OutboxRelay(outbox_repo, publisher, serializer)
        >>> await relay.process_pending(batch_size=100)
    """

    def __init__(
        self,
        outbox_repo: OutboxRepository,
        publisher: EventPublisher,
        serializer: EventSerializer,
    ) -> None:
        """Initialize relay.

        Args:
            outbox_repo: Repository for outbox entries.
            publisher: Event publisher for sending to broker.
            serializer: Event serializer.
        """
        self._outbox_repo = outbox_repo
        self._publisher = publisher
        self._serializer = serializer

    async def process_pending(
        self,
        batch_size: int = 50,
        max_retries: int = 5,
    ) -> int:
        """Process a batch of pending outbox entries.

        Fetches unpublished entries, publishes each to the broker,
        and marks them as published or failed.

        Args:
            batch_size: Maximum entries to process in one batch.
            max_retries: Skip entries exceeding this retry count.

        Returns:
            Number of successfully published entries.
        """
        entries = await self._outbox_repo.get_pending(
            batch_size=batch_size,
            max_retries=max_retries,
        )

        if not entries:
            return 0

        published_count = 0

        for entry in entries:
            try:
                # Reconstruct a minimal DomainEvent for publishing
                payload = json.loads(entry.payload)
                event = _reconstruct_minimal_event(payload, entry)

                await self._publisher.publish(
                    event,
                    routing_key=entry.routing_key,
                    headers={
                        "x-source": entry.source,
                        "x-correlation-id": entry.correlation_id or "",
                    },
                )

                await self._outbox_repo.mark_published(entry.id)
                published_count += 1

                logger.debug(
                    "Outbox entry published",
                    extra={
                        "event_id": entry.event_id,
                        "event_type": entry.event_type,
                        "routing_key": entry.routing_key,
                    },
                )

            except Exception as exc:
                logger.warning(
                    "Failed to publish outbox entry",
                    extra={
                        "event_id": entry.event_id,
                        "event_type": entry.event_type,
                        "retry_count": entry.retry_count,
                        "error": str(exc),
                    },
                )
                await self._outbox_repo.mark_failed(entry.id, str(exc))

        logger.info(
            "Outbox relay batch completed",
            extra={
                "total": len(entries),
                "published": published_count,
                "failed": len(entries) - published_count,
            },
        )

        return published_count


def _derive_routing_key(event: DomainEvent) -> str:
    """Derive a routing key from event type name.

    Converts PascalCase to dot-separated lowercase.
    E.g. "UserCreated" -> "user.created".

    Args:
        event: Domain event.

    Returns:
        Dot-separated lowercase routing key.
    """
    name = event.event_type
    parts: list[str] = []
    current: list[str] = []
    for char in name:
        if char.isupper() and current:
            parts.append("".join(current).lower())
            current = [char]
        else:
            current.append(char)
    if current:
        parts.append("".join(current).lower())
    return ".".join(parts)


def _reconstruct_minimal_event(
    payload: dict[str, Any],
    entry: OutboxEntry,
) -> DomainEvent:
    """Reconstruct a minimal DomainEvent from outbox entry payload.

    This creates a base DomainEvent with enough data for the
    serializer to produce a valid broker message.

    Args:
        payload: Parsed JSON payload from the outbox entry.
        entry: The outbox entry.

    Returns:
        Minimal DomainEvent for publishing.
    """

    class _OutboxEvent(DomainEvent):
        """Transient event class for outbox relay publishing."""

        _event_type_name: str = ""

        @property
        def event_type(self) -> str:
            return self._event_type_name

        def to_dict(self) -> dict[str, Any]:
            return payload

    event = _OutboxEvent(
        event_id=entry.event_id,
        aggregate_id=entry.aggregate_id,
        aggregate_type=entry.aggregate_type,
        metadata={"correlation_id": entry.correlation_id} if entry.correlation_id else {},
    )
    event._event_type_name = entry.event_type
    return event
