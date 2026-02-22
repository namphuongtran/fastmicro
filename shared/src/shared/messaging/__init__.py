"""Enterprise messaging module for event-driven microservices.

Provides abstractions and implementations for publishing and consuming
domain events over RabbitMQ (command/event bus) and Kafka (audit/analytics stream).

This module supports dual-broker architecture:
- **RabbitMQ**: Low-latency command and event delivery with topic exchanges
- **Kafka**: High-throughput ordered event streaming for audit and analytics

Example:
    >>> from shared.messaging import (
    ...     RabbitMQPublisher,
    ...     RabbitMQConsumer,
    ...     KafkaEventProducer,
    ...     KafkaEventConsumer,
    ...     EventEnvelope,
    ... )
"""

from __future__ import annotations

from shared.messaging.config import KafkaSettings, RabbitMQSettings
from shared.messaging.event_bridge import EventOutboxBridge
from shared.messaging.kafka import KafkaEventConsumer, KafkaEventProducer
from shared.messaging.rabbitmq import RabbitMQConsumer, RabbitMQPublisher
from shared.messaging.serialization import EventEnvelope, EventSerializer
from shared.messaging.types import EventCallback, EventConsumer, EventPublisher

__all__ = [
    # Configuration
    "RabbitMQSettings",
    "KafkaSettings",
    # Protocols
    "EventPublisher",
    "EventConsumer",
    "EventCallback",
    # Serialization
    "EventSerializer",
    "EventEnvelope",
    # Event Bridge
    "EventOutboxBridge",
    # RabbitMQ
    "RabbitMQPublisher",
    "RabbitMQConsumer",
    # Kafka
    "KafkaEventProducer",
    "KafkaEventConsumer",
]
