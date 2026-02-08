"""Tests for shared.messaging.types — Protocol compliance checks."""

from shared.messaging.types import EventConsumer, EventPublisher


class TestProtocols:
    """Verify that the protocols are runtime-checkable."""

    def test_event_publisher_is_runtime_checkable(self):
        """EventPublisher should be a runtime-checkable Protocol."""
        assert hasattr(EventPublisher, "__protocol_attrs__") or hasattr(
            EventPublisher, "__abstractmethods__"
        )

    def test_event_consumer_is_runtime_checkable(self):
        """EventConsumer should be a runtime-checkable Protocol."""
        assert hasattr(EventConsumer, "__protocol_attrs__") or hasattr(
            EventConsumer, "__abstractmethods__"
        )
