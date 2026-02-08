"""Messaging protocol definitions.

Defines structural typing protocols for event publishing and consuming,
allowing broker-agnostic service code.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, Protocol, runtime_checkable

from shared.ddd.events import DomainEvent


@runtime_checkable
class EventPublisher(Protocol):
    """Protocol for publishing domain events to a message broker.

    Implementations must support publishing single events and batches,
    as well as async context manager lifecycle (connect/disconnect).

    Example:
        >>> async with RabbitMQPublisher(settings) as publisher:
        ...     await publisher.publish(user_created_event, routing_key="user.created")
    """

    async def publish(
        self,
        event: DomainEvent,
        routing_key: str | None = None,
        *,
        headers: dict[str, str] | None = None,
    ) -> None:
        """Publish a single domain event.

        Args:
            event: The domain event to publish.
            routing_key: Broker-specific routing key (e.g. "user.created").
            headers: Optional message headers.
        """
        ...

    async def publish_batch(
        self,
        events: list[DomainEvent],
        routing_key: str | None = None,
    ) -> None:
        """Publish multiple domain events.

        Args:
            events: List of domain events to publish.
            routing_key: Common routing key for all events.
        """
        ...

    async def connect(self) -> None:
        """Establish connection to the message broker."""
        ...

    async def disconnect(self) -> None:
        """Close connection to the message broker."""
        ...


# Type alias for event handler callbacks
EventCallback = Callable[[DomainEvent, dict[str, Any]], Awaitable[None]]


@runtime_checkable
class EventConsumer(Protocol):
    """Protocol for consuming domain events from a message broker.

    Implementations must support subscribing to event types by routing key
    and running a consumption loop.

    Example:
        >>> async with RabbitMQConsumer(settings) as consumer:
        ...     await consumer.subscribe("user.created", handle_user_created)
        ...     await consumer.start()
    """

    async def subscribe(
        self,
        routing_key: str,
        callback: EventCallback,
        *,
        queue_name: str | None = None,
    ) -> None:
        """Subscribe to events matching a routing key pattern.

        Args:
            routing_key: Routing key pattern (supports wildcards for topic exchanges).
            callback: Async function called with (event, metadata) for each message.
            queue_name: Optional explicit queue name (auto-generated if omitted).
        """
        ...

    async def start(self) -> None:
        """Start consuming messages. Blocks until stopped."""
        ...

    async def stop(self) -> None:
        """Stop consuming messages gracefully."""
        ...

    async def connect(self) -> None:
        """Establish connection to the message broker."""
        ...

    async def disconnect(self) -> None:
        """Close connection to the message broker."""
        ...
