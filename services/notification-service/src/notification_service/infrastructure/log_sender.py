"""Log-based notification sender for development."""

from __future__ import annotations

import structlog

from notification_service.domain.models import (
    NotificationChannel,
    NotificationRequest,
    NotificationSender,
)

logger = structlog.get_logger()


class LogSender(NotificationSender):
    """Sends notifications to the structured log (dev/test only)."""

    @property
    def channel(self) -> NotificationChannel:
        return NotificationChannel.EMAIL

    async def send(self, request: NotificationRequest) -> bool:
        """Log the notification instead of sending."""
        logger.info(
            "notification_logged",
            channel=request.channel,
            recipient=request.recipient,
            subject=request.subject,
            event_type=request.event_type,
        )
        return True
