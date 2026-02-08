"""Kafka event consumer using aiokafka.

Consumes ordered event streams from Kafka topics, primarily
used for audit log processing and analytics pipelines.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from aiokafka import AIOKafkaConsumer

from shared.messaging.config import KafkaSettings
from shared.messaging.serialization import EventSerializer
from shared.messaging.types import EventCallback

logger = logging.getLogger(__name__)


class KafkaEventConsumer:
    """Consumes domain events from Kafka topics using aiokafka.

    Supports subscribing to multiple topics with a single consumer group.
    Messages are deserialized and dispatched to registered callbacks.

    Attributes:
        settings: Kafka connection configuration.
        serializer: Event serializer for deserialization.

    Example:
        >>> consumer = KafkaEventConsumer(settings, serializer)
        >>> await consumer.subscribe("audit.events", handle_audit)
        >>> async with consumer:
        ...     await consumer.start()
    """

    def __init__(
        self,
        settings: KafkaSettings,
        serializer: EventSerializer,
        *,
        group_id: str | None = None,
    ) -> None:
        """Initialize consumer.

        Args:
            settings: Kafka connection settings.
            serializer: Event serializer for deserialization.
            group_id: Consumer group ID. Defaults to settings.group_id.
        """
        self._settings = settings
        self._serializer = serializer
        self._group_id = group_id or settings.group_id
        self._consumer: AIOKafkaConsumer | None = None
        self._subscriptions: dict[str, EventCallback] = {}
        self._running = False

    async def subscribe(
        self,
        routing_key: str,
        callback: EventCallback,
        *,
        queue_name: str | None = None,
    ) -> None:
        """Register a callback for a Kafka topic.

        Must be called before connect()/start().

        Args:
            routing_key: Kafka topic name.
            callback: Async function(event, metadata) for each message.
            queue_name: Ignored (exists for protocol compatibility).
        """
        self._subscriptions[routing_key] = callback
        logger.info("Subscribed to Kafka topic", extra={"topic": routing_key})

    async def connect(self) -> None:
        """Create and start the Kafka consumer.

        Subscribes to all registered topics and starts polling.
        """
        if not self._subscriptions:
            msg = "No subscriptions registered. Call subscribe() before connect()."
            raise RuntimeError(msg)

        topics = list(self._subscriptions.keys())
        logger.info(
            "Connecting Kafka consumer",
            extra={
                "topics": topics,
                "group_id": self._group_id,
                "bootstrap_servers": self._settings.bootstrap_servers,
            },
        )

        kwargs: dict[str, Any] = {
            "bootstrap_servers": self._settings.bootstrap_servers,
            "group_id": self._group_id,
            "client_id": f"{self._settings.client_id}-consumer",
            "auto_offset_reset": "earliest",
            "enable_auto_commit": False,
        }

        # Add SASL config if specified
        if self._settings.sasl_mechanism:
            kwargs["security_protocol"] = self._settings.security_protocol
            kwargs["sasl_mechanism"] = self._settings.sasl_mechanism
            if self._settings.sasl_username:
                kwargs["sasl_plain_username"] = self._settings.sasl_username
            if self._settings.sasl_password:
                kwargs["sasl_plain_password"] = self._settings.sasl_password.get_secret_value()

        self._consumer = AIOKafkaConsumer(*topics, **kwargs)
        await self._consumer.start()
        logger.info("Kafka consumer started")

    async def disconnect(self) -> None:
        """Stop the Kafka consumer."""
        self._running = False
        if self._consumer is not None:
            await self._consumer.stop()
            self._consumer = None
        logger.info("Kafka consumer stopped")

    async def start(self) -> None:
        """Start consuming messages. Blocks until stop() is called.

        Polls messages from subscribed topics, deserializes them,
        and dispatches to registered callbacks. Commits offsets
        after successful processing.
        """
        if self._consumer is None:
            msg = "Consumer not connected. Call connect() first."
            raise RuntimeError(msg)

        self._running = True
        logger.info("Kafka consumer polling started")

        try:
            async for msg in self._consumer:
                if not self._running:
                    break

                try:
                    event, envelope = self._serializer.deserialize(msg.value)
                    metadata: dict[str, Any] = {
                        "message_id": envelope.message_id,
                        "source": envelope.source,
                        "correlation_id": envelope.correlation_id,
                        "timestamp": envelope.timestamp,
                        "topic": msg.topic,
                        "partition": msg.partition,
                        "offset": msg.offset,
                    }

                    callback = self._subscriptions.get(msg.topic)
                    if callback and event is not None:
                        await callback(event, metadata)
                    elif event is None:
                        logger.warning(
                            "Unknown event type from Kafka",
                            extra={
                                "event_type": envelope.event_type,
                                "topic": msg.topic,
                            },
                        )

                    # Commit offset after successful processing
                    await self._consumer.commit()

                except Exception:
                    logger.exception(
                        "Error processing Kafka message",
                        extra={
                            "topic": msg.topic,
                            "partition": msg.partition,
                            "offset": msg.offset,
                        },
                    )
                    # Continue processing next message; failed messages
                    # should be handled by a DLQ topic via error handler
                    await self._consumer.commit()

        except asyncio.CancelledError:
            logger.info("Kafka consumer cancelled")

    async def stop(self) -> None:
        """Signal the consumer to stop polling."""
        self._running = False
        logger.info("Kafka consumer stop requested")

    async def __aenter__(self) -> KafkaEventConsumer:
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
