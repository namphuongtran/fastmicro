"""RabbitMQ event consumer using aio-pika.

Consumes domain events from RabbitMQ queues with automatic reconnection,
dead letter handling, and structured logging.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import aio_pika
from aio_pika import ExchangeType
from aio_pika.abc import (
    AbstractChannel,
    AbstractExchange,
    AbstractIncomingMessage,
    AbstractQueue,
    AbstractRobustConnection,
)

from shared.messaging.config import RabbitMQSettings
from shared.messaging.serialization import EventSerializer
from shared.messaging.types import EventCallback

logger = logging.getLogger(__name__)


class RabbitMQConsumer:
    """Consumes domain events from RabbitMQ queues.

    Supports subscribing to multiple routing keys on a topic exchange,
    with automatic dead-letter handling and graceful shutdown.

    Attributes:
        settings: RabbitMQ connection configuration.
        serializer: Event serializer for deserialization.

    Example:
        >>> consumer = RabbitMQConsumer(settings, serializer)
        >>> await consumer.connect()
        >>> await consumer.subscribe("user.created", handle_user_created)
        >>> await consumer.subscribe("order.*", handle_order_events)
        >>> await consumer.start()  # Blocks until stop() is called
    """

    def __init__(
        self,
        settings: RabbitMQSettings,
        serializer: EventSerializer,
        *,
        service_name: str = "unknown",
    ) -> None:
        """Initialize consumer.

        Args:
            settings: RabbitMQ connection settings.
            serializer: Event serializer for deserialization.
            service_name: Name of consuming service (used for queue naming).
        """
        self._settings = settings
        self._serializer = serializer
        self._service_name = service_name
        self._connection: AbstractRobustConnection | None = None
        self._channel: AbstractChannel | None = None
        self._exchange: AbstractExchange | None = None
        self._queues: list[AbstractQueue] = []
        self._subscriptions: list[tuple[str, EventCallback, str | None]] = []
        self._stop_event = asyncio.Event()

    async def connect(self) -> None:
        """Establish connection to RabbitMQ.

        Creates a robust connection, opens a channel with prefetch control,
        and declares the topic exchange.
        """
        logger.info(
            "Consumer connecting to RabbitMQ",
            extra={"host": self._settings.host, "service": self._service_name},
        )
        self._connection = await aio_pika.connect_robust(
            self._settings.url,
            timeout=self._settings.connection_timeout,
            heartbeat=self._settings.heartbeat,
        )
        self._channel = await self._connection.channel()
        await self._channel.set_qos(prefetch_count=self._settings.prefetch_count)

        # Declare dead letter exchange
        dlx = await self._channel.declare_exchange(
            self._settings.dead_letter_exchange,
            ExchangeType.TOPIC,
            durable=True,
        )

        # Declare main exchange
        self._exchange = await self._channel.declare_exchange(
            self._settings.exchange_name,
            ExchangeType.TOPIC,
            durable=True,
        )
        # Store DLX reference for queue declaration
        self._dlx = dlx
        logger.info("RabbitMQ consumer connected")

    async def disconnect(self) -> None:
        """Close the RabbitMQ connection."""
        if self._channel and not self._channel.is_closed:
            await self._channel.close()
        if self._connection and not self._connection.is_closed:
            await self._connection.close()
        self._queues.clear()
        logger.info("RabbitMQ consumer disconnected")

    async def subscribe(
        self,
        routing_key: str,
        callback: EventCallback,
        *,
        queue_name: str | None = None,
    ) -> None:
        """Subscribe to events matching a routing key pattern.

        Declares a durable queue with dead-letter support, binds it to
        the exchange with the given routing key, and registers the callback.

        Args:
            routing_key: Routing key pattern (e.g. "user.created", "order.*").
            callback: Async function(event, metadata) called for each message.
            queue_name: Explicit queue name. Defaults to "{service}.{routing_key}".
        """
        if self._channel is None or self._exchange is None:
            msg = "Consumer not connected. Call connect() first."
            raise RuntimeError(msg)

        name = queue_name or f"{self._service_name}.{routing_key}"

        # Declare durable queue with DLX
        queue = await self._channel.declare_queue(
            name,
            durable=True,
            arguments={
                "x-dead-letter-exchange": self._settings.dead_letter_exchange,
                "x-dead-letter-routing-key": f"dlq.{routing_key}",
            },
        )
        await queue.bind(self._exchange, routing_key=routing_key)

        # Declare DLQ and bind
        dlq = await self._channel.declare_queue(f"{name}.dlq", durable=True)
        await dlq.bind(self._dlx, routing_key=f"dlq.{routing_key}")

        # Register consumer callback
        await queue.consume(self._make_message_handler(callback))
        self._queues.append(queue)

        logger.info(
            "Subscribed to events",
            extra={"routing_key": routing_key, "queue": name},
        )

    def _make_message_handler(
        self,
        callback: EventCallback,
    ) -> Any:
        """Create an aio-pika message handler wrapping the user callback.

        Args:
            callback: User-provided async event handler.

        Returns:
            Async function compatible with aio-pika queue.consume().
        """

        async def handler(message: AbstractIncomingMessage) -> None:
            async with message.process(requeue=False):
                try:
                    event, envelope = self._serializer.deserialize(message.body)
                    metadata = {
                        "message_id": envelope.message_id,
                        "source": envelope.source,
                        "correlation_id": envelope.correlation_id,
                        "timestamp": envelope.timestamp,
                        "routing_key": message.routing_key,
                    }
                    if event is not None:
                        await callback(event, metadata)
                    else:
                        logger.warning(
                            "Unknown event type, skipping",
                            extra={
                                "event_type": envelope.event_type,
                                "message_id": envelope.message_id,
                            },
                        )
                except Exception:
                    logger.exception(
                        "Error processing message",
                        extra={"message_id": str(message.message_id)},
                    )
                    # Message will be nacked and sent to DLQ
                    raise

        return handler

    async def start(self) -> None:
        """Start consuming messages. Blocks until stop() is called."""
        logger.info("Consumer started, waiting for messages...")
        await self._stop_event.wait()

    async def stop(self) -> None:
        """Signal the consumer to stop."""
        self._stop_event.set()
        logger.info("Consumer stop requested")

    async def __aenter__(self) -> RabbitMQConsumer:
        """Async context manager entry — connect."""
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Async context manager exit — stop and disconnect."""
        await self.stop()
        await self.disconnect()
