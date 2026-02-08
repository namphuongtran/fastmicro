"""Event consumer — subscribes to domain events and dispatches notifications."""

from __future__ import annotations

from typing import Any

import structlog
from shared.ddd import DomainEvent

from notification_service.domain.models import (
    NotificationChannel,
    NotificationRequest,
    NotificationSender,
)

logger = structlog.get_logger()


class NotificationDispatcher:
    """Receives domain events and dispatches notifications via registered senders."""

    def __init__(self) -> None:
        self._senders: dict[NotificationChannel, NotificationSender] = {}

    def register_sender(self, sender: NotificationSender) -> None:
        """Register a sender for a channel."""
        self._senders[sender.channel] = sender

    async def handle_event(self, event: DomainEvent, metadata: dict[str, Any]) -> None:
        """Handle a domain event by dispatching appropriate notifications.

        This is the callback wired into the RabbitMQ consumer.

        Args:
            event: Deserialized domain event.
            metadata: Envelope metadata (correlation_id, source, etc.).
        """
        event_type = type(event).__name__
        logger.info("notification_event_received", event_type=event_type)

        requests = self._build_requests(event, metadata)
        for req in requests:
            sender = self._senders.get(req.channel)
            if sender is None:
                logger.warning(
                    "no_sender_for_channel",
                    channel=req.channel,
                    event_type=event_type,
                )
                continue
            try:
                await sender.send(req)
                logger.info(
                    "notification_sent",
                    channel=req.channel,
                    recipient=req.recipient,
                    event_type=event_type,
                )
            except Exception:
                logger.exception(
                    "notification_send_failed",
                    channel=req.channel,
                    recipient=req.recipient,
                    event_type=event_type,
                )

    def _build_requests(
        self,
        event: DomainEvent,
        metadata: dict[str, Any],
    ) -> list[NotificationRequest]:
        """Build notification requests from a domain event.

        Override or extend with routing rules, template rendering, and
        recipient resolution.

        Returns:
            List of NotificationRequest objects.
        """
        # Placeholder: concrete routing rules will map event types to
        # channel/recipient/template combinations.
        _ = event, metadata
        return []
