"""Tests for shared.audit — audit trail module."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from shared.audit import (
    AuditAction,
    AuditEvent,
    AuditLogger,
    AuditQuery,
    InMemoryAuditLogger,
    audit_log,
)


@pytest.mark.unit
class TestAuditEvent:
    def test_create_event(self):
        evt = AuditEvent(
            action=AuditAction.CREATE,
            actor_id="user-1",
            resource_type="Order",
            resource_id="order-42",
        )
        assert evt.action == AuditAction.CREATE
        assert evt.actor_id == "user-1"
        assert evt.resource_type == "Order"
        assert evt.event_id  # UUID generated

    def test_frozen(self):
        evt = AuditEvent(
            action=AuditAction.READ,
            actor_id="u",
            resource_type="X",
        )
        with pytest.raises(AttributeError):
            evt.actor_id = "v"  # type: ignore[misc]

    def test_to_dict(self):
        evt = AuditEvent(
            action=AuditAction.DELETE,
            actor_id="admin",
            resource_type="User",
            resource_id="u-1",
            description="Removed inactive user",
        )
        d = evt.to_dict()
        assert d["action"] == "delete"
        assert d["actor_id"] == "admin"
        assert d["resource_type"] == "User"
        assert "occurred_at" in d

    def test_custom_action_string(self):
        evt = AuditEvent(
            action="custom_action",
            actor_id="svc",
            resource_type="Widget",
        )
        assert evt.action == "custom_action"


@pytest.mark.unit
class TestInMemoryAuditLogger:
    async def test_log_and_query(self):
        logger = InMemoryAuditLogger()
        evt = AuditEvent(
            action=AuditAction.CREATE,
            actor_id="u1",
            resource_type="Order",
            resource_id="o1",
        )
        await logger.log(evt)
        assert len(logger.events) == 1

        results = await logger.query(AuditQuery(actor_id="u1"))
        assert len(results) == 1
        assert results[0].resource_id == "o1"

    async def test_log_many(self):
        logger = InMemoryAuditLogger()
        events = [
            AuditEvent(action=AuditAction.CREATE, actor_id="u1", resource_type="A"),
            AuditEvent(action=AuditAction.UPDATE, actor_id="u2", resource_type="B"),
        ]
        await logger.log_many(events)
        assert len(logger.events) == 2

    async def test_query_by_resource_type(self):
        logger = InMemoryAuditLogger()
        await logger.log(AuditEvent(action=AuditAction.CREATE, actor_id="u", resource_type="X"))
        await logger.log(AuditEvent(action=AuditAction.CREATE, actor_id="u", resource_type="Y"))

        results = await logger.query(AuditQuery(resource_type="X"))
        assert len(results) == 1

    async def test_query_by_action(self):
        logger = InMemoryAuditLogger()
        await logger.log(AuditEvent(action=AuditAction.CREATE, actor_id="u", resource_type="A"))
        await logger.log(AuditEvent(action=AuditAction.DELETE, actor_id="u", resource_type="A"))

        results = await logger.query(AuditQuery(action=AuditAction.DELETE))
        assert len(results) == 1
        assert results[0].action == AuditAction.DELETE

    async def test_query_by_date_range(self):
        logger = InMemoryAuditLogger()
        now = datetime.now(UTC)
        old = AuditEvent(
            action=AuditAction.CREATE,
            actor_id="u",
            resource_type="A",
            occurred_at=now - timedelta(days=10),
        )
        recent = AuditEvent(
            action=AuditAction.UPDATE,
            actor_id="u",
            resource_type="A",
            occurred_at=now,
        )
        await logger.log_many([old, recent])

        results = await logger.query(AuditQuery(from_date=now - timedelta(days=1)))
        assert len(results) == 1

    async def test_query_limit_offset(self):
        logger = InMemoryAuditLogger()
        for i in range(10):
            await logger.log(
                AuditEvent(action=AuditAction.READ, actor_id="u", resource_type="A")
            )
        results = await logger.query(AuditQuery(limit=3, offset=0))
        assert len(results) == 3

        results2 = await logger.query(AuditQuery(limit=3, offset=8))
        assert len(results2) == 2

    async def test_clear(self):
        logger = InMemoryAuditLogger()
        await logger.log(AuditEvent(action=AuditAction.CREATE, actor_id="u", resource_type="A"))
        logger.clear()
        assert len(logger.events) == 0

    async def test_protocol_compliance(self):
        logger = InMemoryAuditLogger()
        assert isinstance(logger, AuditLogger)


@pytest.mark.unit
class TestAuditLogDecorator:
    async def test_basic_audit_logging(self):
        audit_logger = InMemoryAuditLogger()

        class MyService:
            def __init__(self):
                self._audit = audit_logger

            @audit_log(action=AuditAction.CREATE, resource_type="Widget")
            async def create_widget(self, name: str):
                return {"id": "w-1", "name": name}

        svc = MyService()
        result = await svc.create_widget("gadget")
        assert result == {"id": "w-1", "name": "gadget"}
        assert len(audit_logger.events) == 1
        assert audit_logger.events[0].resource_type == "Widget"

    async def test_no_audit_logger_still_works(self):
        """When _audit is missing, the function still executes."""

        class NoAudit:
            @audit_log(action=AuditAction.READ, resource_type="X")
            async def read(self):
                return 42

        svc = NoAudit()
        result = await svc.read()
        assert result == 42

    async def test_custom_resource_id_extractor(self):
        audit_logger = InMemoryAuditLogger()

        class Svc:
            _audit = audit_logger

            @audit_log(
                action=AuditAction.CREATE,
                resource_type="Item",
                get_resource_id=lambda result: result["id"],
            )
            async def create(self):
                return {"id": "item-99"}

        await Svc().create()
        assert audit_logger.events[0].resource_id == "item-99"
