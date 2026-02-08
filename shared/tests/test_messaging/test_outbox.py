"""Tests for shared.messaging.outbox — OutboxEntry, OutboxRepository, OutboxRelay."""

from __future__ import annotations

import json
from dataclasses import dataclass
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from shared.ddd.events import DomainEvent
from shared.messaging.outbox import OutboxBase, OutboxEntry, OutboxRelay, OutboxRepository
from shared.messaging.serialization import EventSerializer

# ---- test fixtures ----

@dataclass
class ItemCreated(DomainEvent):
    """Test domain event."""

    item_id: str = ""
    name: str = ""


@pytest.fixture
async def engine():
    """Create an in-memory SQLite async engine for testing."""
    eng = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with eng.begin() as conn:
        await conn.run_sync(OutboxBase.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest.fixture
async def session(engine) -> AsyncSession:
    """Create a test session."""
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as sess:
        yield sess


# ---- OutboxEntry.from_domain_event ----

class TestOutboxEntryCreation:
    """Tests for OutboxEntry.from_domain_event."""

    def test_from_domain_event_basic(self):
        """from_domain_event should populate all fields from the event."""
        event = ItemCreated(
            item_id="item-1",
            name="Widget",
            aggregate_id="item-1",
            aggregate_type="Item",
        )
        entry = OutboxEntry.from_domain_event(event, source="item-service")

        assert entry.event_id == event.event_id
        assert entry.event_type == "ItemCreated"
        assert entry.aggregate_id == "item-1"
        assert entry.aggregate_type == "Item"
        assert entry.source == "item-service"
        # Column default is applied on flush, so before flush it may be None
        assert entry.published in (False, None)
        assert entry.retry_count in (0, None)

    def test_from_domain_event_custom_routing_key(self):
        """Custom routing key should override derived key."""
        event = ItemCreated(item_id="item-2")
        entry = OutboxEntry.from_domain_event(
            event, routing_key="custom.routing.key"
        )
        assert entry.routing_key == "custom.routing.key"

    def test_from_domain_event_payload_is_valid_json(self):
        """Payload should be valid JSON containing the event data."""
        event = ItemCreated(item_id="item-3", name="Gadget")
        entry = OutboxEntry.from_domain_event(event)
        payload = json.loads(entry.payload)
        assert payload["event_type"] == "ItemCreated"
        assert "data" in payload
        assert payload["data"]["item_id"] == "item-3"


# ---- OutboxRepository ----

class TestOutboxRepository:
    """Tests for OutboxRepository CRUD operations."""

    @pytest.mark.asyncio
    async def test_add_and_get_pending(self, session: AsyncSession):
        """Added entries should appear in get_pending results."""
        repo = OutboxRepository(session)
        event = ItemCreated(item_id="item-10")
        entry = OutboxEntry.from_domain_event(event, source="test")

        await repo.add(entry)
        await session.commit()

        pending = await repo.get_pending(batch_size=10)
        assert len(pending) == 1
        assert pending[0].event_id == event.event_id

    @pytest.mark.asyncio
    async def test_mark_published(self, session: AsyncSession):
        """mark_published should set published=True and published_at."""
        repo = OutboxRepository(session)
        event = ItemCreated(item_id="item-11")
        entry = OutboxEntry.from_domain_event(event, source="test")

        await repo.add(entry)
        await session.commit()

        pending = await repo.get_pending()
        assert len(pending) == 1

        await repo.mark_published(pending[0].id)
        await session.commit()

        remaining = await repo.get_pending()
        assert len(remaining) == 0

    @pytest.mark.asyncio
    async def test_mark_failed_increments_retry(self, session: AsyncSession):
        """mark_failed should increment retry_count and record error."""
        repo = OutboxRepository(session)
        event = ItemCreated(item_id="item-12")
        entry = OutboxEntry.from_domain_event(event, source="test")

        await repo.add(entry)
        await session.commit()

        pending = await repo.get_pending()
        await repo.mark_failed(pending[0].id, error="Connection refused")
        await session.commit()

        pending_again = await repo.get_pending()
        assert len(pending_again) == 1
        assert pending_again[0].retry_count == 1
        assert pending_again[0].error == "Connection refused"

    @pytest.mark.asyncio
    async def test_get_pending_skips_exceeded_retries(self, session: AsyncSession):
        """Entries exceeding max_retries should not appear in get_pending."""
        repo = OutboxRepository(session)
        event = ItemCreated(item_id="item-13")
        entry = OutboxEntry.from_domain_event(event, source="test")

        await repo.add(entry)
        await session.commit()

        # Exhaust retries
        for _ in range(6):
            pending = await repo.get_pending(max_retries=5)
            if pending:
                await repo.mark_failed(pending[0].id, error="fail")
                await session.commit()

        remaining = await repo.get_pending(max_retries=5)
        assert len(remaining) == 0


# ---- OutboxRelay ----

class TestOutboxRelay:
    """Tests for OutboxRelay processing loop."""

    @pytest.mark.asyncio
    async def test_process_pending_publishes_and_marks(self, session: AsyncSession):
        """Relay should publish each entry and mark it as published."""
        repo = OutboxRepository(session)
        publisher = AsyncMock()
        publisher.publish = AsyncMock()
        serializer = EventSerializer(source="test")

        # Create 2 outbox entries
        for i in range(2):
            event = ItemCreated(item_id=f"item-{i}")
            entry = OutboxEntry.from_domain_event(event, source="test")
            await repo.add(entry)
        await session.commit()

        relay = OutboxRelay(repo, publisher, serializer)
        count = await relay.process_pending(batch_size=10)

        assert count == 2
        assert publisher.publish.call_count == 2

        remaining = await repo.get_pending()
        assert len(remaining) == 0

    @pytest.mark.asyncio
    async def test_process_pending_handles_publish_failure(
        self, session: AsyncSession
    ):
        """Relay should mark entries as failed when publishing raises."""
        repo = OutboxRepository(session)
        publisher = AsyncMock()
        publisher.publish = AsyncMock(side_effect=ConnectionError("broker down"))
        serializer = EventSerializer(source="test")

        event = ItemCreated(item_id="item-fail")
        entry = OutboxEntry.from_domain_event(event, source="test")
        await repo.add(entry)
        await session.commit()

        relay = OutboxRelay(repo, publisher, serializer)
        count = await relay.process_pending(batch_size=10)

        assert count == 0
        pending = await repo.get_pending()
        assert len(pending) == 1
        assert pending[0].retry_count == 1
