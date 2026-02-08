"""RabbitMQ event publisher using aio-pika.

Publishes domain events to a RabbitMQ topic exchange with
automatic reconnection, structured logging, and DLX support.
"""

from __future__ import annotations

import logging
from typing import Any

import aio_pika
from aio_pika import ExchangeType, Message
from aio_pika.abc import (
    AbstractChannel,
    AbstractExchange,
    AbstractRobustConnection,
)

from shared.ddd.events import DomainEvent
from shared.messaging.config import RabbitMQSettings
from shared.messaging.serialization import EventSerializer

logger = logging.getLogger(__name__)


class RabbitMQPublisher:
    """Publishes domain events to RabbitMQ via a topic exchange.

    Uses aio-pika's robust connection for automatic reconnection.
    Events are serialized into JSON envelopes with metadata for
    tracing and deduplication.

    Attributes:
        settings: RabbitMQ connection and exchange configuration.
        serializer: Event serializer for wire-format conversion.

    Example:
        >>> settings = RabbitMQSettings()
        >>> serializer = EventSerializer(source="identity-service")
        >>> async with RabbitMQPublisher(settings, serializer) as publisher:
        ...     await publisher.publish(
        ...         UserCreated(user_id="123"),
        ...         routing_key="user.created",
        ...     )
    """

    def __init__(
        self,
        settings: RabbitMQSettings,
        serializer: EventSerializer,
    ) -> None:
        """Initialize publisher.

        Args:
            settings: RabbitMQ connection settings.
            serializer: Event serializer instance.
        """
        self._settings = settings
        self._serializer = serializer
        self._connection: AbstractRobustConnection | None = None
        self._channel: AbstractChannel | None = None
        self._exchange: AbstractExchange | None = None

    async def connect(self) -> None:
        """Establish connection to RabbitMQ and declare the topic exchange.

        Creates a robust connection with auto-reconnect, opens a channel,
        and declares the domain events topic exchange and its dead letter exchange.
        """
        logger.info(
            "Connecting to RabbitMQ",
            extra={"host": self._settings.host, "port": self._settings.port},
        )
        self._connection = await aio_pika.connect_robust(
            self._settings.url,
            timeout=self._settings.connection_timeout,
            heartbeat=self._settings.heartbeat,
        )
        self._channel = await self._connection.channel()

        # Declare dead letter exchange
        await self._channel.declare_exchange(
            self._settings.dead_letter_exchange,
            ExchangeType.TOPIC,
            durable=True,
        )

        # Declare main topic exchange
        self._exchange = await self._channel.declare_exchange(
            self._settings.exchange_name,
            ExchangeType.TOPIC,
            durable=True,
        )
        logger.info(
            "RabbitMQ publisher connected",
            extra={"exchange": self._settings.exchange_name},
        )

    async def disconnect(self) -> None:
        """Close the RabbitMQ connection and channel."""
        if self._channel and not self._channel.is_closed:
            await self._channel.close()
        if self._connection and not self._connection.is_closed:
            await self._connection.close()
        logger.info("RabbitMQ publisher disconnected")

    async def publish(
        self,
        event: DomainEvent,
        routing_key: str | None = None,
        *,
        headers: dict[str, str] | None = None,
    ) -> None:
        """Publish a single domain event to the exchange.

        Args:
            event: Domain event to publish.
            routing_key: Topic routing key (defaults to event_type in snake_case).
            headers: Optional AMQP message headers.

        Raises:
            RuntimeError: If publisher is not connected.
        """
        if self._exchange is None:
            msg = "Publisher not connected. Call connect() or use async with."
            raise RuntimeError(msg)

        key = routing_key or self._default_routing_key(event)
        correlation_id = event.metadata.get("correlation_id")
        body = self._serializer.serialize(event, correlation_id=correlation_id)

        message = Message(
            body=body,
            content_type="application/json",
            message_id=event.event_id,
            headers=headers or {},
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        )

        await self._exchange.publish(message, routing_key=key)
        logger.debug(
            "Event published",
            extra={
                "event_type": event.event_type,
                "event_id": event.event_id,
                "routing_key": key,
            },
        )

    async def publish_batch(
        self,
        events: list[DomainEvent],
        routing_key: str | None = None,
    ) -> None:
        """Publish multiple domain events.

        Args:
            events: List of domain events to publish.
            routing_key: Common routing key (per-event default if None).
        """
        for event in events:
            await self.publish(event, routing_key=routing_key)

    @staticmethod
    def _default_routing_key(event: DomainEvent) -> str:
        """Derive a default routing key from the event type.

        Converts PascalCase event type to dot-separated lowercase.
        E.g. "UserCreated" -> "user.created".

        Args:
            event: The domain event.

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

    async def __aenter__(self) -> RabbitMQPublisher:
        """Async context manager entry — connect."""
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Async context manager exit — disconnect."""
        await self.disconnect()
