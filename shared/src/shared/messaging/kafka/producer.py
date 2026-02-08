"""Kafka event producer using aiokafka.

High-throughput producer for ordered event streaming, primarily
used for the audit log pipeline and analytics event delivery.
"""

from __future__ import annotations

import logging
from typing import Any

from aiokafka import AIOKafkaProducer

from shared.ddd.events import DomainEvent
from shared.messaging.config import KafkaSettings
from shared.messaging.serialization import EventSerializer

logger = logging.getLogger(__name__)


class KafkaEventProducer:
    """Publishes domain events to Kafka topics using aiokafka.

    Designed for high-throughput, ordered event streams. Uses
    aggregate_id as the partition key to guarantee per-entity ordering.

    Attributes:
        settings: Kafka connection configuration.
        serializer: Event serializer for wire-format conversion.

    Example:
        >>> producer = KafkaEventProducer(settings, serializer)
        >>> async with producer:
        ...     await producer.publish(
        ...         audit_event,
        ...         routing_key="audit.events",
        ...     )
    """

    def __init__(
        self,
        settings: KafkaSettings,
        serializer: EventSerializer,
    ) -> None:
        """Initialize producer.

        Args:
            settings: Kafka connection settings.
            serializer: Event serializer instance.
        """
        self._settings = settings
        self._serializer = serializer
        self._producer: AIOKafkaProducer | None = None

    async def connect(self) -> None:
        """Start the Kafka producer.

        Initializes the aiokafka producer with compression,
        batching, and acknowledgement settings.
        """
        logger.info(
            "Connecting Kafka producer",
            extra={"bootstrap_servers": self._settings.bootstrap_servers},
        )

        kwargs: dict[str, Any] = {
            "bootstrap_servers": self._settings.bootstrap_servers,
            "client_id": self._settings.client_id,
            "acks": self._settings.acks,
            "compression_type": self._settings.compression_type,
            "max_batch_size": self._settings.max_batch_size,
            "linger_ms": self._settings.linger_ms,
        }

        # Add SASL config if specified
        if self._settings.sasl_mechanism:
            kwargs["security_protocol"] = self._settings.security_protocol
            kwargs["sasl_mechanism"] = self._settings.sasl_mechanism
            if self._settings.sasl_username:
                kwargs["sasl_plain_username"] = self._settings.sasl_username
            if self._settings.sasl_password:
                kwargs["sasl_plain_password"] = self._settings.sasl_password.get_secret_value()

        self._producer = AIOKafkaProducer(**kwargs)
        await self._producer.start()
        logger.info("Kafka producer started")

    async def disconnect(self) -> None:
        """Stop the Kafka producer, flushing pending messages."""
        if self._producer is not None:
            await self._producer.stop()
            self._producer = None
        logger.info("Kafka producer stopped")

    async def publish(
        self,
        event: DomainEvent,
        routing_key: str | None = None,
        *,
        headers: dict[str, str] | None = None,
    ) -> None:
        """Publish a domain event to a Kafka topic.

        Uses aggregate_id as partition key for per-entity ordering.

        Args:
            event: Domain event to publish.
            routing_key: Kafka topic name (required).
            headers: Optional message headers.

        Raises:
            RuntimeError: If producer is not connected.
            ValueError: If routing_key (topic) is not provided.
        """
        if self._producer is None:
            msg = "Producer not connected. Call connect() or use async with."
            raise RuntimeError(msg)

        if not routing_key:
            msg = "routing_key (Kafka topic) is required"
            raise ValueError(msg)

        correlation_id = event.metadata.get("correlation_id")
        body = self._serializer.serialize(event, correlation_id=correlation_id)

        # Use aggregate_id as partition key for ordering
        key = event.aggregate_id.encode("utf-8") if event.aggregate_id else None

        # Convert headers to Kafka format: list of (key, value_bytes) tuples
        kafka_headers: list[tuple[str, bytes]] | None = None
        if headers:
            kafka_headers = [(k, v.encode("utf-8")) for k, v in headers.items()]

        await self._producer.send_and_wait(
            topic=routing_key,
            value=body,
            key=key,
            headers=kafka_headers,
        )
        logger.debug(
            "Event published to Kafka",
            extra={
                "event_type": event.event_type,
                "event_id": event.event_id,
                "topic": routing_key,
            },
        )

    async def publish_batch(
        self,
        events: list[DomainEvent],
        routing_key: str | None = None,
    ) -> None:
        """Publish multiple events to a Kafka topic.

        Args:
            events: List of domain events.
            routing_key: Kafka topic name.
        """
        for event in events:
            await self.publish(event, routing_key=routing_key)

    async def __aenter__(self) -> KafkaEventProducer:
        """Async context manager entry — start producer."""
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Async context manager exit — stop producer."""
        await self.disconnect()
