"""Event serialization and deserialization.

Handles conversion between DomainEvent instances and wire-format
bytes for message broker transport, with schema versioning support.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from shared.ddd.events import DomainEvent


@dataclass(frozen=True)
class EventEnvelope:
    """Wire-format envelope wrapping a domain event for transport.

    Provides metadata for routing, deduplication, and schema evolution.

    Attributes:
        message_id: Unique message identifier for deduplication.
        event_type: Fully qualified event type name (e.g. "UserCreated").
        event_version: Schema version for backward-compatible evolution.
        source: Originating service name.
        correlation_id: Request correlation ID for distributed tracing.
        causation_id: ID of the event that caused this event.
        timestamp: ISO 8601 timestamp of envelope creation.
        payload: Serialized event data dictionary.
    """

    message_id: str = field(default_factory=lambda: str(uuid4()))
    event_type: str = ""
    event_version: int = 1
    source: str = ""
    correlation_id: str | None = None
    causation_id: str | None = None
    timestamp: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
    )
    payload: dict[str, Any] = field(default_factory=dict)


class EventSerializer:
    """Serializes and deserializes domain events for message broker transport.

    Wraps DomainEvent instances in EventEnvelope for wire transport,
    adding metadata for tracing, deduplication, and schema versioning.

    Attributes:
        source: Name of the originating service.
        event_registry: Mapping of event_type names to DomainEvent subclasses.

    Example:
        >>> serializer = EventSerializer(source="identity-service")
        >>> serializer.register_event(UserCreated)
        >>> payload = serializer.serialize(user_created_event)
        >>> event = serializer.deserialize(payload)
    """

    def __init__(self, source: str) -> None:
        """Initialize serializer.

        Args:
            source: Name of the originating service for envelope metadata.
        """
        self.source = source
        self._event_registry: dict[str, type[DomainEvent]] = {}

    def register_event(self, event_class: type[DomainEvent]) -> None:
        """Register a DomainEvent subclass for deserialization.

        Args:
            event_class: The event class to register.
        """
        self._event_registry[event_class.__name__] = event_class

    def serialize(
        self,
        event: DomainEvent,
        *,
        correlation_id: str | None = None,
        causation_id: str | None = None,
        event_version: int = 1,
    ) -> bytes:
        """Serialize a domain event to JSON bytes.

        Creates an EventEnvelope wrapping the event data and encodes
        it as UTF-8 JSON bytes for broker transport.

        Args:
            event: The domain event to serialize.
            correlation_id: Optional correlation ID for tracing.
            causation_id: Optional causation ID for event chain tracking.
            event_version: Schema version number.

        Returns:
            UTF-8 encoded JSON bytes.
        """
        envelope = EventEnvelope(
            message_id=event.event_id,
            event_type=event.event_type,
            event_version=event_version,
            source=self.source,
            correlation_id=correlation_id or event.metadata.get("correlation_id"),
            causation_id=causation_id,
            payload=event.to_dict(),
        )
        return self._envelope_to_bytes(envelope)

    def deserialize(self, data: bytes) -> tuple[DomainEvent | None, EventEnvelope]:
        """Deserialize JSON bytes back to a domain event.

        Attempts to reconstruct a typed DomainEvent if the event_type
        is registered; otherwise returns None with the raw envelope.

        Args:
            data: UTF-8 encoded JSON bytes from the broker.

        Returns:
            Tuple of (DomainEvent or None, EventEnvelope).
            Event is None if the event_type is not registered.
        """
        raw = json.loads(data.decode("utf-8"))
        envelope = EventEnvelope(
            message_id=raw.get("message_id", ""),
            event_type=raw.get("event_type", ""),
            event_version=raw.get("event_version", 1),
            source=raw.get("source", ""),
            correlation_id=raw.get("correlation_id"),
            causation_id=raw.get("causation_id"),
            timestamp=raw.get("timestamp", ""),
            payload=raw.get("payload", {}),
        )

        event_class = self._event_registry.get(envelope.event_type)
        if event_class is None:
            return None, envelope

        return self._reconstruct_event(event_class, envelope), envelope

    def _reconstruct_event(
        self,
        event_class: type[DomainEvent],
        envelope: EventEnvelope,
    ) -> DomainEvent:
        """Reconstruct a typed DomainEvent from envelope payload.

        Args:
            event_class: Target DomainEvent subclass.
            envelope: The deserialized envelope.

        Returns:
            Reconstructed DomainEvent instance.
        """
        payload = envelope.payload
        data = payload.get("data", {})

        # Merge base fields + event-specific data
        base_fields = {
            "event_id": payload.get("event_id", envelope.message_id),
            "aggregate_id": payload.get("aggregate_id"),
            "aggregate_type": payload.get("aggregate_type"),
            "metadata": payload.get("metadata", {}),
        }
        return event_class(**base_fields, **data)

    @staticmethod
    def _envelope_to_bytes(envelope: EventEnvelope) -> bytes:
        """Convert envelope to JSON bytes.

        Args:
            envelope: The envelope to serialize.

        Returns:
            UTF-8 JSON bytes.
        """
        data = {
            "message_id": envelope.message_id,
            "event_type": envelope.event_type,
            "event_version": envelope.event_version,
            "source": envelope.source,
            "correlation_id": envelope.correlation_id,
            "causation_id": envelope.causation_id,
            "timestamp": envelope.timestamp,
            "payload": envelope.payload,
        }
        return json.dumps(data, default=str).encode("utf-8")
