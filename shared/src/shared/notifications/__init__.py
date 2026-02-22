"""Notification abstraction for multi-channel delivery.

Provides a channel-agnostic notification interface so services can
send notifications without coupling to a specific transport.

Components:
- :class:`NotificationChannel` — protocol for delivery backends
- :class:`Notification` — payload dataclass
- :class:`NotificationService` — orchestrator with channel routing
- :class:`InMemoryNotificationChannel` — test implementation

Supported channel types: ``email``, ``sms``, ``push``, ``webhook``, ``slack``.

Example:
    >>> from shared.notifications import (
    ...     Notification, NotificationService, InMemoryNotificationChannel,
    ... )
    >>>
    >>> channel = InMemoryNotificationChannel()
    >>> svc = NotificationService()
    >>> svc.register_channel("email", channel)
    >>> await svc.send(Notification(
    ...     channel="email",
    ...     recipient="user@example.com",
    ...     subject="Welcome!",
    ...     body="Hello there.",
    ... ))
"""

from __future__ import annotations

from shared.notifications.base import (
    InMemoryNotificationChannel,
    Notification,
    NotificationChannel,
    NotificationPriority,
    NotificationResult,
    NotificationStatus,
)
from shared.notifications.service import NotificationService

__all__ = [
    "Notification",
    "NotificationChannel",
    "NotificationPriority",
    "NotificationResult",
    "NotificationService",
    "NotificationStatus",
    "InMemoryNotificationChannel",
]
