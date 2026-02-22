"""Domain Event → Outbox Bridge.

Connects the DDD aggregate-root event mechanism to the transactional
outbox pattern so that domain events are persisted inside the same
database transaction as the business operation.

Workflow
~~~~~~~~
1.  Service performs business logic (adds / updates aggregates).
2.  Before ``uow.commit()``, call ``EventOutboxBridge.collect(aggregate)``
    to drain all pending domain events from the aggregate.
3.  The bridge creates an ``OutboxEntry`` for each event and flushes it
    within the current session.
4.  ``uow.commit()`` commits **both** the business data and the outbox
    rows atomically.
5.  A background ``OutboxRelay`` later picks them up and publishes to
    the message broker.

This approach eliminates the dual-write problem between the database
and the broker.

Example::

    async with SqlAlchemyUnitOfWork(db_manager) as uow:
        user_repo = uow.get_repository("users", UserRepository)
        user = User(name="Alice")
        user.add_event(UserCreated(user_id=user.id))
        await user_repo.add(user)

        bridge = EventOutboxBridge(uow.session, source="identity-service")
        await bridge.collect(user)          # drains events → outbox rows
        await uow.commit()
"""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from shared.ddd.entity import AggregateRoot
from shared.ddd.events import DomainEvent, EventDispatcher
from shared.messaging.outbox import OutboxEntry, OutboxRepository

logger = logging.getLogger(__name__)


class EventOutboxBridge:
    """Bridges domain events from aggregates into the transactional outbox.

    Parameters
    ----------
    session:
        The active ``AsyncSession`` (same session as the business
        transaction — ensures atomicity).
    source:
        Originating service name written into every outbox entry
        (e.g. ``"identity-service"``).
    correlation_id:
        Optional request-scoped correlation ID for distributed tracing.
    dispatcher:
        Optional in-memory ``EventDispatcher`` for local side-effects
        (e.g. updating read projections synchronously before commit).
    """

    def __init__(
        self,
        session: AsyncSession,
        *,
        source: str = "",
        correlation_id: str | None = None,
        dispatcher: EventDispatcher | None = None,
    ) -> None:
        self._outbox_repo = OutboxRepository(session)
        self._source = source
        self._correlation_id = correlation_id
        self._dispatcher = dispatcher
        self._collected: list[DomainEvent] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def collect(self, aggregate: AggregateRoot) -> list[DomainEvent]:
        """Drain pending events from an aggregate into the outbox.

        Calls ``aggregate.clear_events()`` so each event is captured
        exactly once.

        Parameters
        ----------
        aggregate:
            The aggregate root whose events should be persisted.

        Returns
        -------
        list[DomainEvent]
            The events that were collected (useful for logging / assertions).
        """
        events = aggregate.clear_events()
        for event in events:
            await self._persist_event(event, aggregate)
        self._collected.extend(events)
        return events

    async def collect_many(self, aggregates: list[AggregateRoot]) -> list[DomainEvent]:
        """Drain pending events from multiple aggregates.

        Parameters
        ----------
        aggregates:
            List of aggregate roots to collect events from.

        Returns
        -------
        list[DomainEvent]
            All events collected across the aggregates.
        """
        all_events: list[DomainEvent] = []
        for aggregate in aggregates:
            events = await self.collect(aggregate)
            all_events.extend(events)
        return all_events

    async def publish_event(
        self,
        event: DomainEvent,
        *,
        aggregate_id: str | None = None,
        aggregate_type: str | None = None,
    ) -> None:
        """Persist an ad-hoc domain event to the outbox.

        Use when the event does not originate from an ``AggregateRoot``
        (e.g. system events, saga compensation).

        Parameters
        ----------
        event:
            The domain event to store.
        aggregate_id:
            Optional aggregate ID to associate with the event.
        aggregate_type:
            Optional aggregate type name.
        """
        if aggregate_id is not None:
            event.aggregate_id = aggregate_id
        if aggregate_type is not None:
            event.aggregate_type = aggregate_type

        await self._persist_event(event)
        self._collected.append(event)

    async def dispatch_collected(self) -> None:
        """Dispatch all collected events through the in-memory dispatcher.

        Call this **after** ``uow.commit()`` so that local side-effects
        (projections, cache invalidation) fire only when the transaction
        has succeeded.

        If no dispatcher was provided at construction time this is a
        no-op.
        """
        if self._dispatcher is None:
            return
        for event in self._collected:
            await self._dispatcher.dispatch(event)
        logger.debug(
            "Dispatched %d events via in-memory dispatcher",
            len(self._collected),
        )

    @property
    def collected_events(self) -> list[DomainEvent]:
        """Return all events collected so far (read-only copy)."""
        return list(self._collected)

    def clear(self) -> None:
        """Reset the collected-events buffer."""
        self._collected.clear()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    async def _persist_event(
        self,
        event: DomainEvent,
        aggregate: AggregateRoot | None = None,
    ) -> None:
        """Create an ``OutboxEntry`` and flush it within the session."""
        # Enrich event metadata
        if self._correlation_id:
            event.metadata.setdefault("correlation_id", self._correlation_id)

        if aggregate is not None:
            event.aggregate_id = event.aggregate_id or aggregate.id
            event.aggregate_type = event.aggregate_type or type(aggregate).__name__

        entry = OutboxEntry.from_domain_event(
            event,
            source=self._source,
        )
        await self._outbox_repo.add(entry)

        logger.debug(
            "Persisted domain event to outbox",
            extra={
                "event_id": event.event_id,
                "event_type": event.event_type,
                "aggregate_id": event.aggregate_id,
            },
        )


__all__ = [
    "EventOutboxBridge",
]
