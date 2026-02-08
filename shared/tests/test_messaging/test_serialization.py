"""Tests for shared.messaging.serialization — EventEnvelope and EventSerializer."""

from __future__ import annotations

import json
from dataclasses import dataclass

import pytest

from shared.ddd.events import DomainEvent
from shared.messaging.serialization import EventEnvelope, EventSerializer

# ---- test fixtures ----

@dataclass
class OrderPlaced(DomainEvent):
    """Test domain event."""

    order_id: str = ""
    total: float = 0.0


@dataclass
class PaymentReceived(DomainEvent):
    """Another test domain event (unregistered)."""

    payment_id: str = ""


# ---- EventEnvelope tests ----

class TestEventEnvelope:
    """Tests for EventEnvelope data class."""

    def test_defaults(self):
        """Test envelope generates default values."""
        envelope = EventEnvelope()
        assert envelope.message_id  # non-empty UUID
        assert envelope.timestamp  # non-empty ISO timestamp
        assert envelope.event_type == ""
        assert envelope.event_version == 1
        assert envelope.payload == {}

    def test_frozen(self):
        """Test envelope is immutable."""
        envelope = EventEnvelope(event_type="OrderPlaced")
        with pytest.raises(AttributeError):
            envelope.event_type = "Changed"  # type: ignore[misc]


# ---- EventSerializer tests ----

class TestEventSerializer:
    """Tests for EventSerializer round-trip serialization."""

    @pytest.fixture
    def serializer(self) -> EventSerializer:
        """Create a serializer with OrderPlaced registered."""
        s = EventSerializer(source="order-service")
        s.register_event(OrderPlaced)
        return s

    def test_serialize_returns_bytes(self, serializer: EventSerializer):
        """Serialize should return UTF-8 JSON bytes."""
        event = OrderPlaced(
            order_id="ord-123",
            total=99.99,
            aggregate_id="ord-123",
            aggregate_type="Order",
        )
        data = serializer.serialize(event)
        assert isinstance(data, bytes)

        parsed = json.loads(data)
        assert parsed["event_type"] == "OrderPlaced"
        assert parsed["source"] == "order-service"
        assert parsed["payload"]["aggregate_id"] == "ord-123"

    def test_serialize_includes_correlation_id(self, serializer: EventSerializer):
        """Correlation ID should appear in the envelope."""
        event = OrderPlaced(order_id="ord-1")
        data = serializer.serialize(event, correlation_id="req-abc")

        parsed = json.loads(data)
        assert parsed["correlation_id"] == "req-abc"

    def test_round_trip_registered_event(self, serializer: EventSerializer):
        """Serialize → deserialize should reconstruct the typed event."""
        event = OrderPlaced(
            order_id="ord-456",
            total=49.99,
            aggregate_id="ord-456",
            aggregate_type="Order",
        )
        data = serializer.serialize(event, correlation_id="corr-1")

        reconstructed, envelope = serializer.deserialize(data)

        assert reconstructed is not None
        assert isinstance(reconstructed, OrderPlaced)
        assert reconstructed.order_id == "ord-456"
        assert reconstructed.total == 49.99
        assert reconstructed.aggregate_id == "ord-456"
        assert envelope.event_type == "OrderPlaced"
        assert envelope.source == "order-service"

    def test_deserialize_unregistered_event_returns_none(
        self, serializer: EventSerializer
    ):
        """Unregistered event type should return None event with envelope."""
        event = PaymentReceived(payment_id="pay-1")
        # Serialize via a fresh serializer that knows PaymentReceived
        other_serializer = EventSerializer(source="payment-service")
        other_serializer.register_event(PaymentReceived)
        data = other_serializer.serialize(event)

        # Deserialize with the original serializer that doesn't know PaymentReceived
        reconstructed, envelope = serializer.deserialize(data)

        assert reconstructed is None
        assert envelope.event_type == "PaymentReceived"
        assert envelope.source == "payment-service"

    def test_deserialize_preserves_message_id(self, serializer: EventSerializer):
        """Message ID should survive round-trip."""
        event = OrderPlaced(order_id="ord-1")
        data = serializer.serialize(event)

        _, envelope = serializer.deserialize(data)
        assert envelope.message_id == event.event_id

    def test_register_multiple_events(self):
        """Multiple event types can be registered and deserialized."""
        s = EventSerializer(source="test")
        s.register_event(OrderPlaced)
        s.register_event(PaymentReceived)

        e1 = OrderPlaced(order_id="o1")
        e2 = PaymentReceived(payment_id="p1")

        r1, _ = s.deserialize(s.serialize(e1))
        r2, _ = s.deserialize(s.serialize(e2))

        assert isinstance(r1, OrderPlaced)
        assert isinstance(r2, PaymentReceived)
        assert r1.order_id == "o1"
        assert r2.payment_id == "p1"
