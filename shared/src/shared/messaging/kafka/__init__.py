"""Kafka messaging implementations.

Provides producer and consumer implementations using aiokafka
for high-throughput ordered event streaming (audit, analytics).
"""

from __future__ import annotations

from shared.messaging.kafka.consumer import KafkaEventConsumer
from shared.messaging.kafka.producer import KafkaEventProducer

__all__ = [
    "KafkaEventProducer",
    "KafkaEventConsumer",
]
