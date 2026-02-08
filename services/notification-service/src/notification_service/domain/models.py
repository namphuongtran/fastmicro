"""Notification channel abstraction and types."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class NotificationChannel(StrEnum):
    """Supported notification delivery channels."""

    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    WEBHOOK = "webhook"
    IN_APP = "in_app"


class NotificationStatus(StrEnum):
    """Notification delivery status."""

    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class NotificationRequest:
    """A notification to be delivered.

    Attributes:
        channel: Delivery channel.
        recipient: Target address (email, phone, device token, URL).
        subject: Notification subject / title.
        body: Notification body (plain text or HTML).
        metadata: Additional data for template rendering.
        event_type: Originating domain event type.
        correlation_id: Request correlation ID for tracing.
    """

    channel: NotificationChannel
    recipient: str
    subject: str
    body: str
    metadata: dict[str, Any] = field(default_factory=dict)
    event_type: str = ""
    correlation_id: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class NotificationSender(ABC):
    """Abstract notification sender (port)."""

    @property
    @abstractmethod
    def channel(self) -> NotificationChannel:
        """Channel this sender handles."""
        ...

    @abstractmethod
    async def send(self, request: NotificationRequest) -> bool:
        """Send a notification.

        Args:
            request: The notification to deliver.

        Returns:
            True if sent successfully.
        """
        ...
