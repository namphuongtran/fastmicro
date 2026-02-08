"""Unit tests for notification-service domain models and dispatcher."""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import AsyncMock

import pytest
from shared.ddd import DomainEvent

from notification_service.domain.models import (
    NotificationChannel,
    NotificationRequest,
    NotificationSender,
    NotificationStatus,
)
from notification_service.application.dispatcher import NotificationDispatcher
from notification_service.infrastructure.log_sender import LogSender


# ---- domain model tests ----

class TestNotificationChannel:
    """Tests for NotificationChannel enum."""

    def test_all_channels_defined(self):
        assert NotificationChannel.EMAIL == "email"
        assert NotificationChannel.SMS == "sms"
        assert NotificationChannel.PUSH == "push"
        assert NotificationChannel.WEBHOOK == "webhook"
        assert NotificationChannel.IN_APP == "in_app"


class TestNotificationStatus:
    """Tests for NotificationStatus enum."""

    def test_all_statuses_defined(self):
        assert NotificationStatus.PENDING == "pending"
        assert NotificationStatus.SENT == "sent"
        assert NotificationStatus.DELIVERED == "delivered"
        assert NotificationStatus.FAILED == "failed"
        assert NotificationStatus.RETRYING == "retrying"


class TestNotificationRequest:
    """Tests for NotificationRequest dataclass."""

    def test_basic_creation(self):
        req = NotificationRequest(
            channel=NotificationChannel.EMAIL,
            recipient="user@example.com",
            subject="Hello",
            body="World",
        )
        assert req.channel == NotificationChannel.EMAIL
        assert req.recipient == "user@example.com"
        assert req.metadata == {}
        assert req.created_at is not None

    def test_metadata_defaults_to_empty(self):
        req = NotificationRequest(
            channel=NotificationChannel.SMS,
            recipient="+1234",
            subject="",
            body="Hi",
        )
        assert req.metadata == {}


# ---- LogSender tests ----

class TestLogSender:
    """Tests for the LogSender (dev/test sender)."""

    def test_channel_is_email(self):
        sender = LogSender()
        assert sender.channel == NotificationChannel.EMAIL

    @pytest.mark.asyncio
    async def test_send_returns_true(self):
        sender = LogSender()
        req = NotificationRequest(
            channel=NotificationChannel.EMAIL,
            recipient="dev@test.com",
            subject="Test",
            body="Body",
        )
        result = await sender.send(req)
        assert result is True


# ---- NotificationDispatcher tests ----

@dataclass
class _TestEvent(DomainEvent):
    """Dummy domain event for dispatcher tests."""

    detail: str = ""


class TestNotificationDispatcher:
    """Tests for NotificationDispatcher."""

    def test_register_sender(self):
        dispatcher = NotificationDispatcher()
        sender = LogSender()
        dispatcher.register_sender(sender)
        assert NotificationChannel.EMAIL in dispatcher._senders

    @pytest.mark.asyncio
    async def test_handle_event_calls_sender(self):
        """When _build_requests returns items, the sender should be called."""
        dispatcher = NotificationDispatcher()
        mock_sender = AsyncMock(spec=NotificationSender)
        mock_sender.channel = NotificationChannel.EMAIL
        mock_sender.send = AsyncMock(return_value=True)
        dispatcher.register_sender(mock_sender)

        # Override _build_requests to return a concrete notification
        req = NotificationRequest(
            channel=NotificationChannel.EMAIL,
            recipient="test@test.com",
            subject="Hi",
            body="Hello",
        )
        dispatcher._build_requests = lambda event, meta: [req]

        event = _TestEvent(detail="test")
        await dispatcher.handle_event(event, metadata={})
        mock_sender.send.assert_awaited_once_with(req)

    @pytest.mark.asyncio
    async def test_handle_event_no_sender_for_channel(self):
        """Events routed to unregistered channels should log warning but not crash."""
        dispatcher = NotificationDispatcher()
        req = NotificationRequest(
            channel=NotificationChannel.WEBHOOK,
            recipient="https://hook.example.com",
            subject="",
            body="{}",
        )
        dispatcher._build_requests = lambda event, meta: [req]

        event = _TestEvent(detail="test")
        # Should not raise
        await dispatcher.handle_event(event, metadata={})

    @pytest.mark.asyncio
    async def test_handle_event_sender_failure_does_not_propagate(self):
        """If sender.send raises, dispatcher should catch and log."""
        dispatcher = NotificationDispatcher()
        failing_sender = AsyncMock(spec=NotificationSender)
        failing_sender.channel = NotificationChannel.EMAIL
        failing_sender.send = AsyncMock(side_effect=ConnectionError("SMTP down"))
        dispatcher.register_sender(failing_sender)

        req = NotificationRequest(
            channel=NotificationChannel.EMAIL,
            recipient="fail@test.com",
            subject="Boom",
            body="Error",
        )
        dispatcher._build_requests = lambda event, meta: [req]

        event = _TestEvent(detail="test")
        # Should not raise
        await dispatcher.handle_event(event, metadata={})

    @pytest.mark.asyncio
    async def test_default_build_requests_returns_empty(self):
        """The default _build_requests should return an empty list."""
        dispatcher = NotificationDispatcher()
        event = _TestEvent(detail="no-routing")
        requests = dispatcher._build_requests(event, {})
        assert requests == []
