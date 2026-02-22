"""Core notification types and in-memory channel implementation."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol, runtime_checkable
from uuid import uuid4


class NotificationStatus(str, enum.Enum):
    """Delivery status of a notification."""

    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    BOUNCED = "bounced"


class NotificationPriority(str, enum.Enum):
    """Priority level for notifications."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class Notification:
    """Notification payload.

    Attributes:
        notification_id: Unique identifier.
        channel: Target channel name (e.g. ``email``, ``sms``).
        recipient: Destination address (email, phone, URL, etc.).
        subject: Notification subject / title.
        body: Notification body / content.
        template_id: Optional template identifier for server-side rendering.
        template_vars: Variables to inject into the template.
        priority: Delivery priority.
        metadata: Arbitrary key-value context.
        correlation_id: Distributed trace correlation.
        created_at: When the notification was created.
    """

    channel: str
    recipient: str
    subject: str = ""
    body: str = ""
    notification_id: str = field(default_factory=lambda: str(uuid4()))
    template_id: str | None = None
    template_vars: dict[str, Any] = field(default_factory=dict)
    priority: NotificationPriority = NotificationPriority.NORMAL
    metadata: dict[str, Any] = field(default_factory=dict)
    correlation_id: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class NotificationResult:
    """Outcome of a send attempt.

    Attributes:
        notification_id: Original notification ID.
        status: Delivery status.
        provider_id: Identifier returned by the delivery provider.
        error: Error message on failure.
        sent_at: When the notification was dispatched.
    """

    notification_id: str
    status: NotificationStatus
    provider_id: str | None = None
    error: str | None = None
    sent_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@runtime_checkable
class NotificationChannel(Protocol):
    """Protocol for notification delivery backends.

    Each channel handles a single transport (email, SMS, etc.).
    """

    async def send(self, notification: Notification) -> NotificationResult:
        """Deliver a notification and return the result."""
        ...

    async def send_batch(self, notifications: list[Notification]) -> list[NotificationResult]:
        """Deliver multiple notifications in a batch."""
        ...


class InMemoryNotificationChannel:
    """In-memory notification channel for testing.

    Stores all sent notifications in a list for assertions.
    Optionally simulates failures.

    Example:
        >>> channel = InMemoryNotificationChannel()
        >>> result = await channel.send(Notification(
        ...     channel="email",
        ...     recipient="test@example.com",
        ...     subject="Test",
        ...     body="Hello",
        ... ))
        >>> assert result.status == NotificationStatus.SENT
        >>> assert len(channel.sent) == 1
    """

    def __init__(self, *, fail: bool = False) -> None:
        self.sent: list[Notification] = []
        self.results: list[NotificationResult] = []
        self._fail = fail

    async def send(self, notification: Notification) -> NotificationResult:
        """Record the notification and return a result."""
        self.sent.append(notification)
        if self._fail:
            result = NotificationResult(
                notification_id=notification.notification_id,
                status=NotificationStatus.FAILED,
                error="Simulated failure",
            )
        else:
            result = NotificationResult(
                notification_id=notification.notification_id,
                status=NotificationStatus.SENT,
                provider_id=f"mem-{notification.notification_id}",
            )
        self.results.append(result)
        return result

    async def send_batch(self, notifications: list[Notification]) -> list[NotificationResult]:
        """Send multiple notifications sequentially."""
        return [await self.send(n) for n in notifications]

    def clear(self) -> None:
        """Remove all recorded notifications."""
        self.sent.clear()
        self.results.clear()
