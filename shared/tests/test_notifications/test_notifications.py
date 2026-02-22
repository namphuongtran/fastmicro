"""Tests for shared.notifications — notification abstraction."""

from __future__ import annotations

import pytest

from shared.notifications import (
    InMemoryNotificationChannel,
    Notification,
    NotificationChannel,
    NotificationPriority,
    NotificationService,
    NotificationStatus,
)


@pytest.mark.unit
class TestNotification:
    def test_create_notification(self):
        n = Notification(
            channel="email",
            recipient="user@example.com",
            subject="Hello",
            body="World",
        )
        assert n.channel == "email"
        assert n.recipient == "user@example.com"
        assert n.notification_id  # UUID generated
        assert n.priority == NotificationPriority.NORMAL

    def test_template_notification(self):
        n = Notification(
            channel="email",
            recipient="u@x.com",
            template_id="welcome-email",
            template_vars={"name": "Alice"},
        )
        assert n.template_id == "welcome-email"
        assert n.template_vars["name"] == "Alice"


@pytest.mark.unit
class TestInMemoryNotificationChannel:
    async def test_send_success(self):
        ch = InMemoryNotificationChannel()
        n = Notification(channel="test", recipient="a@b.com", subject="Hi")
        result = await ch.send(n)
        assert result.status == NotificationStatus.SENT
        assert len(ch.sent) == 1

    async def test_send_failure(self):
        ch = InMemoryNotificationChannel(fail=True)
        n = Notification(channel="test", recipient="a@b.com")
        result = await ch.send(n)
        assert result.status == NotificationStatus.FAILED
        assert result.error == "Simulated failure"

    async def test_send_batch(self):
        ch = InMemoryNotificationChannel()
        items = [Notification(channel="test", recipient=f"u{i}@x.com") for i in range(5)]
        results = await ch.send_batch(items)
        assert len(results) == 5
        assert all(r.status == NotificationStatus.SENT for r in results)

    async def test_clear(self):
        ch = InMemoryNotificationChannel()
        await ch.send(Notification(channel="t", recipient="a@b.com"))
        ch.clear()
        assert len(ch.sent) == 0

    async def test_protocol_compliance(self):
        ch = InMemoryNotificationChannel()
        assert isinstance(ch, NotificationChannel)


@pytest.mark.unit
class TestNotificationService:
    async def test_send_via_registered_channel(self):
        ch = InMemoryNotificationChannel()
        svc = NotificationService()
        svc.register_channel("email", ch)

        result = await svc.send(Notification(channel="email", recipient="u@x.com", subject="Hi"))
        assert result.status == NotificationStatus.SENT
        assert len(ch.sent) == 1

    async def test_send_unknown_channel(self):
        svc = NotificationService()
        result = await svc.send(Notification(channel="sms", recipient="+123"))
        assert result.status == NotificationStatus.FAILED
        assert "Unknown channel" in (result.error or "")

    async def test_default_metadata_injection(self):
        ch = InMemoryNotificationChannel()
        svc = NotificationService(default_metadata={"env": "test"})
        svc.register_channel("email", ch)

        await svc.send(
            Notification(
                channel="email",
                recipient="u@x.com",
                metadata={"custom": "value"},
            )
        )
        # The channel should receive merged metadata
        assert ch.sent[0].metadata == {"env": "test", "custom": "value"}

    async def test_send_batch(self):
        ch = InMemoryNotificationChannel()
        svc = NotificationService()
        svc.register_channel("email", ch)

        items = [Notification(channel="email", recipient=f"u{i}@x.com") for i in range(3)]
        results = await svc.send_batch(items)
        assert len(results) == 3

    async def test_broadcast(self):
        email_ch = InMemoryNotificationChannel()
        sms_ch = InMemoryNotificationChannel()
        svc = NotificationService()
        svc.register_channel("email", email_ch)
        svc.register_channel("sms", sms_ch)

        results = await svc.broadcast(
            channels=["email", "sms"],
            recipient="user@x.com",
            subject="Alert",
            body="System alert",
        )
        assert len(results) == 2
        assert len(email_ch.sent) == 1
        assert len(sms_ch.sent) == 1

    async def test_channel_exception_handled(self):
        """If a channel raises, the service returns FAILED instead of propagating."""

        class BrokenChannel:
            async def send(self, notification):
                raise ConnectionError("connection lost")

            async def send_batch(self, notifications):
                return [await self.send(n) for n in notifications]

        svc = NotificationService()
        svc.register_channel("broken", BrokenChannel())
        result = await svc.send(Notification(channel="broken", recipient="x"))
        assert result.status == NotificationStatus.FAILED
        assert "connection lost" in (result.error or "")
