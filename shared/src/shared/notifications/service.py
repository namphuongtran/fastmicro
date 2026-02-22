"""Notification orchestrator with channel routing.

:class:`NotificationService` maintains a registry of
:class:`NotificationChannel` implementations keyed by channel name
and routes each :class:`Notification` to the appropriate backend.
"""

from __future__ import annotations

import logging
from typing import Any

from shared.notifications.base import (
    Notification,
    NotificationChannel,
    NotificationResult,
    NotificationStatus,
)

logger = logging.getLogger(__name__)


class NotificationService:
    """Routes notifications to registered channels.

    Attributes:
        channels: Mapping of channel name → backend.
        default_metadata: Metadata injected into every notification.

    Example:
        >>> svc = NotificationService(default_metadata={"env": "production"})
        >>> svc.register_channel("email", SmtpChannel())
        >>> svc.register_channel("sms", TwilioChannel())
        >>>
        >>> await svc.send(Notification(channel="email", ...))
        >>> await svc.send(Notification(channel="sms", ...))
    """

    def __init__(
        self,
        *,
        default_metadata: dict[str, Any] | None = None,
    ) -> None:
        self.channels: dict[str, NotificationChannel] = {}
        self.default_metadata = default_metadata or {}

    def register_channel(self, name: str, channel: NotificationChannel) -> None:
        """Register a delivery channel.

        Args:
            name: Channel key (must match ``Notification.channel``).
            channel: Backend that implements :class:`NotificationChannel`.
        """
        self.channels[name] = channel

    async def send(self, notification: Notification) -> NotificationResult:
        """Send a single notification via the matching channel.

        Args:
            notification: The notification payload.

        Returns:
            Delivery result.
        """
        channel = self.channels.get(notification.channel)
        if channel is None:
            logger.error("No channel registered for '%s'", notification.channel)
            return NotificationResult(
                notification_id=notification.notification_id,
                status=NotificationStatus.FAILED,
                error=f"Unknown channel: {notification.channel}",
            )

        # Inject default metadata
        if self.default_metadata:
            merged = {**self.default_metadata, **notification.metadata}
            # Notification is a dataclass — create a new one with merged metadata
            notification = Notification(
                notification_id=notification.notification_id,
                channel=notification.channel,
                recipient=notification.recipient,
                subject=notification.subject,
                body=notification.body,
                template_id=notification.template_id,
                template_vars=notification.template_vars,
                priority=notification.priority,
                metadata=merged,
                correlation_id=notification.correlation_id,
                created_at=notification.created_at,
            )

        try:
            return await channel.send(notification)
        except Exception as exc:
            logger.exception(
                "Failed to send notification %s via %s",
                notification.notification_id,
                notification.channel,
            )
            return NotificationResult(
                notification_id=notification.notification_id,
                status=NotificationStatus.FAILED,
                error=str(exc),
            )

    async def send_batch(
        self,
        notifications: list[Notification],
    ) -> list[NotificationResult]:
        """Send multiple notifications, each routed to its channel.

        Args:
            notifications: List of notification payloads.

        Returns:
            List of delivery results (same order as input).
        """
        return [await self.send(n) for n in notifications]

    async def broadcast(
        self,
        *,
        channels: list[str],
        recipient: str,
        subject: str,
        body: str,
        **kwargs: Any,
    ) -> list[NotificationResult]:
        """Send the same message across multiple channels.

        Args:
            channels: Channel names to send through.
            recipient: Destination address.
            subject: Message subject.
            body: Message body.
            **kwargs: Extra fields forwarded to :class:`Notification`.

        Returns:
            List of results, one per channel.
        """
        results: list[NotificationResult] = []
        for ch in channels:
            n = Notification(
                channel=ch,
                recipient=recipient,
                subject=subject,
                body=body,
                **kwargs,
            )
            results.append(await self.send(n))
        return results
