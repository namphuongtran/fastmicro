"""Tests for shared.idempotency — idempotency key support."""

from __future__ import annotations

import pytest

from shared.idempotency import (
    IdempotencyRecord,
    IdempotencyStore,
    InMemoryIdempotencyStore,
    idempotent,
)
from shared.idempotency.base import IdempotencyStatus
from shared.idempotency.decorator import DuplicateRequestError


@pytest.mark.unit
class TestIdempotencyRecord:
    def test_defaults(self):
        r = IdempotencyRecord(key="abc")
        assert r.status == IdempotencyStatus.IN_PROGRESS
        assert r.response_code is None

    def test_completed_record(self):
        r = IdempotencyRecord(
            key="x",
            status=IdempotencyStatus.COMPLETED,
            response_code=201,
            response_body={"id": 1},
        )
        assert r.response_body == {"id": 1}


@pytest.mark.unit
class TestInMemoryIdempotencyStore:
    async def test_save_and_get(self):
        store = InMemoryIdempotencyStore()
        record = IdempotencyRecord(key="k1", status=IdempotencyStatus.COMPLETED)
        await store.save(record)

        retrieved = await store.get("k1")
        assert retrieved is not None
        assert retrieved.status == IdempotencyStatus.COMPLETED

    async def test_get_missing_returns_none(self):
        store = InMemoryIdempotencyStore()
        assert await store.get("nonexistent") is None

    async def test_delete(self):
        store = InMemoryIdempotencyStore()
        await store.save(IdempotencyRecord(key="d1"))
        await store.delete("d1")
        assert await store.get("d1") is None

    async def test_expired_record_returns_none(self):
        store = InMemoryIdempotencyStore(ttl_seconds=0)
        await store.save(IdempotencyRecord(key="exp"))
        # ttl=0 means it expires immediately
        assert await store.get("exp") is None

    async def test_clear(self):
        store = InMemoryIdempotencyStore()
        await store.save(IdempotencyRecord(key="a"))
        await store.save(IdempotencyRecord(key="b"))
        store.clear()
        assert await store.get("a") is None

    async def test_protocol_compliance(self):
        store = InMemoryIdempotencyStore()
        assert isinstance(store, IdempotencyStore)


@pytest.mark.unit
class TestIdempotentDecorator:
    async def test_first_call_executes(self):
        store = InMemoryIdempotencyStore()
        call_count = 0

        @idempotent(store=store)
        async def create_order(idempotency_key: str, amount: int):
            nonlocal call_count
            call_count += 1
            return {"order_id": "o1", "amount": amount}

        result = await create_order(idempotency_key="k1", amount=100)
        assert result == {"order_id": "o1", "amount": 100}
        assert call_count == 1

    async def test_second_call_returns_cached(self):
        store = InMemoryIdempotencyStore()
        call_count = 0

        @idempotent(store=store)
        async def create_order(idempotency_key: str, amount: int):
            nonlocal call_count
            call_count += 1
            return {"order_id": "o1", "amount": amount}

        await create_order(idempotency_key="k1", amount=100)
        result2 = await create_order(idempotency_key="k1", amount=200)

        # Should return original result, NOT re-execute
        assert result2 == {"order_id": "o1", "amount": 100}
        assert call_count == 1

    async def test_no_key_executes_normally(self):
        store = InMemoryIdempotencyStore()
        call_count = 0

        @idempotent(store=store)
        async def do_work(idempotency_key: str | None = None):
            nonlocal call_count
            call_count += 1
            return "done"

        await do_work()
        await do_work()
        assert call_count == 2  # No caching without key

    async def test_failed_execution_allows_retry(self):
        store = InMemoryIdempotencyStore()
        attempt = 0

        @idempotent(store=store)
        async def flaky(idempotency_key: str):
            nonlocal attempt
            attempt += 1
            if attempt == 1:
                raise ValueError("first try fails")
            return "ok"

        with pytest.raises(ValueError, match="first try fails"):
            await flaky(idempotency_key="retry-k")

        # Second call should retry because status is FAILED
        result = await flaky(idempotency_key="retry-k")
        assert result == "ok"

    async def test_duplicate_in_progress_raises(self):
        store = InMemoryIdempotencyStore()
        # Manually set an IN_PROGRESS record
        await store.save(IdempotencyRecord(key="busy", status=IdempotencyStatus.IN_PROGRESS))

        @idempotent(store=store)
        async def work(idempotency_key: str):
            return "done"

        with pytest.raises(DuplicateRequestError):
            await work(idempotency_key="busy")

    async def test_different_keys_execute_independently(self):
        store = InMemoryIdempotencyStore()
        call_count = 0

        @idempotent(store=store)
        async def process(idempotency_key: str, val: int):
            nonlocal call_count
            call_count += 1
            return val * 2

        r1 = await process(idempotency_key="a", val=5)
        r2 = await process(idempotency_key="b", val=10)
        assert r1 == 10
        assert r2 == 20
        assert call_count == 2
