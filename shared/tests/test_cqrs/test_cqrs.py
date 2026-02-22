"""Tests for the CQRS / Mediator module."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock

import pytest

from shared.cqrs import (
    Command,
    CommandBus,
    CommandHandler,
    LoggingBehavior,
    Mediator,
    PipelineBehavior,
    Query,
    QueryBus,
    QueryHandler,
    TimingBehavior,
    ValidationBehavior,
)
from shared.ddd.events import DomainEvent, DomainEventHandler

# ======================================================================
# Fixtures — sample commands, queries, and handlers
# ======================================================================


@dataclass(frozen=True)
class CreateItem(Command[str]):
    name: str


@dataclass(frozen=True)
class DeleteItem(Command[bool]):
    item_id: str


@dataclass(frozen=True)
class GetItem(Query[dict[str, Any] | None]):
    item_id: str


@dataclass(frozen=True)
class ListItems(Query[list[str]]):
    pass


@dataclass(frozen=True)
class ValidatedCommand(Command[str]):
    value: str

    def validate(self) -> None:
        if not self.value:
            raise ValueError("value must not be empty")


class CreateItemHandler(CommandHandler[CreateItem, str]):
    async def handle(self, command: CreateItem) -> str:
        return f"item-{command.name}"


class DeleteItemHandler(CommandHandler[DeleteItem, bool]):
    async def handle(self, command: DeleteItem) -> bool:
        return True


class GetItemHandler(QueryHandler[GetItem, dict[str, Any] | None]):
    async def handle(self, query: GetItem) -> dict[str, Any] | None:
        if query.item_id == "missing":
            return None
        return {"id": query.item_id, "name": "test"}


class ListItemsHandler(QueryHandler[ListItems, list[str]]):
    async def handle(self, query: ListItems) -> list[str]:
        return ["a", "b", "c"]


class ValidatedCommandHandler(CommandHandler[ValidatedCommand, str]):
    async def handle(self, command: ValidatedCommand) -> str:
        return command.value.upper()


class FailingHandler(CommandHandler[CreateItem, str]):
    async def handle(self, command: CreateItem) -> str:
        raise RuntimeError("boom")


# ======================================================================
# TestCommandBus
# ======================================================================


class TestCommandBus:
    def test_register_and_dispatch(self) -> None:
        bus = CommandBus()
        bus.register(CreateItem, CreateItemHandler())
        assert bus.has_handler(CreateItem)

    async def test_dispatch_returns_result(self) -> None:
        bus = CommandBus()
        bus.register(CreateItem, CreateItemHandler())
        result = await bus.dispatch(CreateItem(name="widget"))
        assert result == "item-widget"

    def test_register_duplicate_raises(self) -> None:
        bus = CommandBus()
        bus.register(CreateItem, CreateItemHandler())
        with pytest.raises(ValueError, match="already registered"):
            bus.register(CreateItem, CreateItemHandler())

    async def test_dispatch_unregistered_raises(self) -> None:
        bus = CommandBus()
        with pytest.raises(KeyError, match="No handler registered"):
            await bus.dispatch(CreateItem(name="x"))

    def test_unregister(self) -> None:
        bus = CommandBus()
        bus.register(CreateItem, CreateItemHandler())
        bus.unregister(CreateItem)
        assert not bus.has_handler(CreateItem)

    def test_unregister_missing_raises(self) -> None:
        bus = CommandBus()
        with pytest.raises(KeyError, match="No handler registered"):
            bus.unregister(CreateItem)

    def test_clear(self) -> None:
        bus = CommandBus()
        bus.register(CreateItem, CreateItemHandler())
        bus.register(DeleteItem, DeleteItemHandler())
        bus.clear()
        assert not bus.has_handler(CreateItem)
        assert not bus.has_handler(DeleteItem)

    def test_has_handler_false(self) -> None:
        bus = CommandBus()
        assert not bus.has_handler(CreateItem)


# ======================================================================
# TestQueryBus
# ======================================================================


class TestQueryBus:
    def test_register_and_has_handler(self) -> None:
        bus = QueryBus()
        bus.register(GetItem, GetItemHandler())
        assert bus.has_handler(GetItem)

    async def test_dispatch_returns_result(self) -> None:
        bus = QueryBus()
        bus.register(GetItem, GetItemHandler())
        result = await bus.dispatch(GetItem(item_id="123"))
        assert result == {"id": "123", "name": "test"}

    async def test_dispatch_none_result(self) -> None:
        bus = QueryBus()
        bus.register(GetItem, GetItemHandler())
        result = await bus.dispatch(GetItem(item_id="missing"))
        assert result is None

    def test_register_duplicate_raises(self) -> None:
        bus = QueryBus()
        bus.register(GetItem, GetItemHandler())
        with pytest.raises(ValueError, match="already registered"):
            bus.register(GetItem, GetItemHandler())

    async def test_dispatch_unregistered_raises(self) -> None:
        bus = QueryBus()
        with pytest.raises(KeyError, match="No handler registered"):
            await bus.dispatch(GetItem(item_id="x"))

    def test_unregister(self) -> None:
        bus = QueryBus()
        bus.register(GetItem, GetItemHandler())
        bus.unregister(GetItem)
        assert not bus.has_handler(GetItem)

    def test_unregister_missing_raises(self) -> None:
        bus = QueryBus()
        with pytest.raises(KeyError, match="No handler registered"):
            bus.unregister(GetItem)

    def test_clear(self) -> None:
        bus = QueryBus()
        bus.register(GetItem, GetItemHandler())
        bus.register(ListItems, ListItemsHandler())
        bus.clear()
        assert not bus.has_handler(GetItem)
        assert not bus.has_handler(ListItems)


# ======================================================================
# TestMediator — dispatch
# ======================================================================


class TestMediatorDispatch:
    async def test_send_command(self) -> None:
        m = Mediator()
        m.register_command_handler(CreateItem, CreateItemHandler())
        result = await m.send(CreateItem(name="foo"))
        assert result == "item-foo"

    async def test_send_query(self) -> None:
        m = Mediator()
        m.register_query_handler(GetItem, GetItemHandler())
        result = await m.send(GetItem(item_id="42"))
        assert result == {"id": "42", "name": "test"}

    async def test_send_query_list(self) -> None:
        m = Mediator()
        m.register_query_handler(ListItems, ListItemsHandler())
        result = await m.send(ListItems())
        assert result == ["a", "b", "c"]

    async def test_send_unknown_type_raises(self) -> None:
        m = Mediator()
        with pytest.raises(TypeError, match="Expected Command or Query"):
            await m.send("not a command")  # type: ignore[arg-type]

    async def test_send_unregistered_command_raises(self) -> None:
        m = Mediator()
        with pytest.raises(KeyError):
            await m.send(CreateItem(name="x"))

    async def test_send_unregistered_query_raises(self) -> None:
        m = Mediator()
        with pytest.raises(KeyError):
            await m.send(GetItem(item_id="x"))


# ======================================================================
# TestMediator — properties
# ======================================================================


class TestMediatorProperties:
    def test_command_bus_property(self) -> None:
        m = Mediator()
        assert isinstance(m.command_bus, CommandBus)

    def test_query_bus_property(self) -> None:
        m = Mediator()
        assert isinstance(m.query_bus, QueryBus)

    def test_clear(self) -> None:
        m = Mediator()
        m.register_command_handler(CreateItem, CreateItemHandler())
        m.register_query_handler(GetItem, GetItemHandler())
        m.add_behavior(LoggingBehavior())
        m.clear()
        assert not m.command_bus.has_handler(CreateItem)
        assert not m.query_bus.has_handler(GetItem)


# ======================================================================
# TestMediator — pipeline behaviors
# ======================================================================


class TestPipelineBehaviors:
    async def test_logging_behavior_success(self, caplog: pytest.LogCaptureFixture) -> None:
        m = Mediator(behaviors=[LoggingBehavior(log_level=logging.INFO)])
        m.register_command_handler(CreateItem, CreateItemHandler())
        with caplog.at_level(logging.INFO, logger="shared.cqrs.pipeline"):
            result = await m.send(CreateItem(name="bar"))
        assert result == "item-bar"
        assert "Dispatching CreateItem" in caplog.text
        assert "Completed CreateItem" in caplog.text

    async def test_logging_behavior_error(self, caplog: pytest.LogCaptureFixture) -> None:
        m = Mediator(behaviors=[LoggingBehavior()])
        m.register_command_handler(CreateItem, FailingHandler())
        with (
            caplog.at_level(logging.DEBUG, logger="shared.cqrs.pipeline"),
            pytest.raises(RuntimeError, match="boom"),
        ):
            await m.send(CreateItem(name="x"))
        assert "Failed CreateItem" in caplog.text

    async def test_timing_behavior_fast(self, caplog: pytest.LogCaptureFixture) -> None:
        m = Mediator(behaviors=[TimingBehavior(slow_threshold_ms=5000)])
        m.register_command_handler(CreateItem, CreateItemHandler())
        with caplog.at_level(logging.DEBUG, logger="shared.cqrs.pipeline"):
            result = await m.send(CreateItem(name="fast"))
        assert result == "item-fast"
        assert "completed in" in caplog.text

    async def test_timing_behavior_slow(self, caplog: pytest.LogCaptureFixture) -> None:
        m = Mediator(behaviors=[TimingBehavior(slow_threshold_ms=0)])
        m.register_command_handler(CreateItem, CreateItemHandler())
        with caplog.at_level(logging.WARNING, logger="shared.cqrs.pipeline"):
            await m.send(CreateItem(name="slow"))
        assert "Slow CreateItem" in caplog.text

    async def test_validation_behavior_passes(self) -> None:
        m = Mediator(behaviors=[ValidationBehavior()])
        m.register_command_handler(ValidatedCommand, ValidatedCommandHandler())
        result = await m.send(ValidatedCommand(value="hello"))
        assert result == "HELLO"

    async def test_validation_behavior_fails(self) -> None:
        m = Mediator(behaviors=[ValidationBehavior()])
        m.register_command_handler(ValidatedCommand, ValidatedCommandHandler())
        with pytest.raises(ValueError, match="value must not be empty"):
            await m.send(ValidatedCommand(value=""))

    async def test_validation_skipped_without_method(self) -> None:
        """Commands without validate() just pass through."""
        m = Mediator(behaviors=[ValidationBehavior()])
        m.register_command_handler(CreateItem, CreateItemHandler())
        result = await m.send(CreateItem(name="ok"))
        assert result == "item-ok"

    async def test_multiple_behaviors_order(self) -> None:
        """Behaviors execute in registration order (outermost first)."""
        call_order: list[str] = []

        class BehaviorA(PipelineBehavior):
            async def handle(self, request: Any, next_: Any) -> Any:
                call_order.append("A-before")
                result = await next_(request)
                call_order.append("A-after")
                return result

        class BehaviorB(PipelineBehavior):
            async def handle(self, request: Any, next_: Any) -> Any:
                call_order.append("B-before")
                result = await next_(request)
                call_order.append("B-after")
                return result

        m = Mediator(behaviors=[BehaviorA(), BehaviorB()])
        m.register_command_handler(CreateItem, CreateItemHandler())
        await m.send(CreateItem(name="x"))

        assert call_order == ["A-before", "B-before", "B-after", "A-after"]

    async def test_behavior_can_modify_result(self) -> None:
        class UppercaseBehavior(PipelineBehavior):
            async def handle(self, request: Any, next_: Any) -> Any:
                result = await next_(request)
                return result.upper() if isinstance(result, str) else result

        m = Mediator(behaviors=[UppercaseBehavior()])
        m.register_command_handler(CreateItem, CreateItemHandler())
        result = await m.send(CreateItem(name="test"))
        assert result == "ITEM-TEST"

    async def test_behaviors_with_queries(self) -> None:
        """Behaviors also wrap query dispatch."""
        calls: list[str] = []

        class TrackingBehavior(PipelineBehavior):
            async def handle(self, request: Any, next_: Any) -> Any:
                calls.append(type(request).__name__)
                return await next_(request)

        m = Mediator(behaviors=[TrackingBehavior()])
        m.register_query_handler(ListItems, ListItemsHandler())
        result = await m.send(ListItems())
        assert result == ["a", "b", "c"]
        assert calls == ["ListItems"]

    async def test_constructor_behaviors(self) -> None:
        """Behaviors passed in constructor work the same way."""
        mock = AsyncMock(side_effect=lambda req, nxt: nxt(req))

        class MockBehavior(PipelineBehavior):
            async def handle(self, request: Any, next_: Any) -> Any:
                return await mock(request, next_)

        m = Mediator(behaviors=[MockBehavior()])
        m.register_command_handler(CreateItem, CreateItemHandler())
        await m.send(CreateItem(name="z"))
        mock.assert_called_once()


# ======================================================================
# TestCommand / TestQuery immutability
# ======================================================================


class TestImmutability:
    def test_command_frozen(self) -> None:
        cmd = CreateItem(name="x")
        with pytest.raises(AttributeError):
            cmd.name = "y"  # type: ignore[misc]

    def test_query_frozen(self) -> None:
        q = GetItem(item_id="1")
        with pytest.raises(AttributeError):
            q.item_id = "2"  # type: ignore[misc]


# ======================================================================
# TestCommand / TestQuery metadata
# ======================================================================


class TestMetadata:
    def test_command_metadata_default_empty(self) -> None:
        cmd = CreateItem(name="x")
        assert cmd.metadata == {}

    def test_command_metadata_kwonly(self) -> None:
        cmd = CreateItem(name="x", metadata={"trace_id": "abc"})
        assert cmd.metadata == {"trace_id": "abc"}

    def test_query_metadata_default_empty(self) -> None:
        q = GetItem(item_id="1")
        assert q.metadata == {}

    def test_query_metadata_kwonly(self) -> None:
        q = GetItem(item_id="1", metadata={"user": "bob"})
        assert q.metadata == {"user": "bob"}

    def test_metadata_not_in_comparison(self) -> None:
        """Metadata is excluded from equality."""
        a = CreateItem(name="x", metadata={"a": 1})
        b = CreateItem(name="x", metadata={"b": 2})
        assert a == b


# ======================================================================
# TestConcurrentBus — copy-on-write safety
# ======================================================================


class TestConcurrentBus:
    async def test_concurrent_register_and_dispatch(self) -> None:
        """Register and dispatch concurrently without errors."""
        bus = CommandBus()
        bus.register(CreateItem, CreateItemHandler())
        dispatching = True
        errors: list[Exception] = []

        async def dispatch_loop() -> None:
            while dispatching:
                try:
                    await bus.dispatch(CreateItem(name="x"))
                except Exception as exc:
                    errors.append(exc)
                await asyncio.sleep(0)

        async def register_unregister_loop() -> None:
            for _ in range(50):
                bus.register(DeleteItem, DeleteItemHandler())
                bus.unregister(DeleteItem)
                await asyncio.sleep(0)

        task = asyncio.create_task(dispatch_loop())
        await register_unregister_loop()
        dispatching = False
        await task
        assert errors == []


# ======================================================================
# TestShortCircuitBehavior
# ======================================================================


class TestShortCircuitBehavior:
    async def test_behavior_that_skips_next(self) -> None:
        """A behavior that doesn't call next_ short-circuits the pipeline."""

        class BlockingBehavior(PipelineBehavior):
            async def handle(self, request: Any, next_: Any) -> Any:
                return "blocked"

        m = Mediator(behaviors=[BlockingBehavior()])
        m.register_command_handler(CreateItem, CreateItemHandler())
        result = await m.send(CreateItem(name="test"))
        assert result == "blocked"


# ======================================================================
# TestAsyncValidation
# ======================================================================


class TestAsyncValidation:
    async def test_async_validate_passes(self) -> None:
        """ValidationBehavior supports async validate() methods."""

        @dataclass(frozen=True)
        class AsyncValidCmd(Command[str]):
            value: str

            async def validate(self) -> None:
                if not self.value:
                    raise ValueError("empty")

        class AsyncValidHandler(CommandHandler["AsyncValidCmd", str]):
            async def handle(self, command: AsyncValidCmd) -> str:
                return command.value

        m = Mediator(behaviors=[ValidationBehavior()])
        m.register_command_handler(AsyncValidCmd, AsyncValidHandler())
        result = await m.send(AsyncValidCmd(value="ok"))
        assert result == "ok"

    async def test_async_validate_fails(self) -> None:
        @dataclass(frozen=True)
        class AsyncValidCmd2(Command[str]):
            value: str

            async def validate(self) -> None:
                if not self.value:
                    raise ValueError("must not be empty")

        class AsyncValidHandler2(CommandHandler["AsyncValidCmd2", str]):
            async def handle(self, command: AsyncValidCmd2) -> str:
                return command.value

        m = Mediator(behaviors=[ValidationBehavior()])
        m.register_command_handler(AsyncValidCmd2, AsyncValidHandler2())
        with pytest.raises(ValueError, match="must not be empty"):
            await m.send(AsyncValidCmd2(value=""))


# ======================================================================
# TestPerTypeBehaviorFiltering
# ======================================================================


class TestPerTypeBehaviorFiltering:
    async def test_applies_to_filters_behavior(self) -> None:
        """Behavior with applies_to only runs for matching requests."""
        calls: list[str] = []

        class CommandOnlyBehavior(PipelineBehavior):
            def applies_to(self, request: Any) -> bool:
                return isinstance(request, Command)

            async def handle(self, request: Any, next_: Any) -> Any:
                calls.append("command-behavior")
                return await next_(request)

        m = Mediator(behaviors=[CommandOnlyBehavior()])
        m.register_command_handler(CreateItem, CreateItemHandler())
        m.register_query_handler(ListItems, ListItemsHandler())

        await m.send(CreateItem(name="cmd"))
        assert calls == ["command-behavior"]

        calls.clear()
        await m.send(ListItems())
        assert calls == []  # behavior skipped for queries

    async def test_default_applies_to_all(self) -> None:
        """Default applies_to returns True for everything."""

        class DefaultBehavior(PipelineBehavior):
            async def handle(self, request: Any, next_: Any) -> Any:
                return await next_(request)

        b = DefaultBehavior()
        assert b.applies_to(CreateItem(name="x")) is True
        assert b.applies_to(ListItems()) is True
        assert b.applies_to("anything") is True


# ======================================================================
# TestMediatorEventPublishing
# ======================================================================


class TestMediatorEventPublishing:
    async def test_publish_domain_event(self) -> None:
        @dataclass
        class OrderPlaced(DomainEvent):
            order_id: str = ""

        class OrderPlacedHandler(DomainEventHandler[OrderPlaced]):
            def __init__(self) -> None:
                self.events: list[OrderPlaced] = []

            async def handle(self, event: OrderPlaced) -> None:
                self.events.append(event)

        m = Mediator()
        handler = OrderPlacedHandler()
        m.register_event_handler(OrderPlaced, handler)

        event = OrderPlaced(order_id="123")
        await m.publish(event)
        assert len(handler.events) == 1
        assert handler.events[0].order_id == "123"

    async def test_publish_multiple_handlers(self) -> None:
        @dataclass
        class ItemCreated(DomainEvent):
            item_name: str = ""

        results: list[str] = []

        class HandlerA(DomainEventHandler[ItemCreated]):
            async def handle(self, event: ItemCreated) -> None:
                results.append(f"A-{event.item_name}")

        class HandlerB(DomainEventHandler[ItemCreated]):
            async def handle(self, event: ItemCreated) -> None:
                results.append(f"B-{event.item_name}")

        m = Mediator()
        m.register_event_handler(ItemCreated, HandlerA())
        m.register_event_handler(ItemCreated, HandlerB())

        await m.publish(ItemCreated(item_name="widget"))
        assert results == ["A-widget", "B-widget"]

    async def test_publish_no_handlers(self) -> None:
        """Publishing an event with no handlers is a no-op."""
        m = Mediator()
        await m.publish(DomainEvent())  # should not raise

    async def test_clear_removes_event_handlers(self) -> None:
        @dataclass
        class SomeEvent(DomainEvent):
            pass

        class SomeHandler(DomainEventHandler[SomeEvent]):
            async def handle(self, event: SomeEvent) -> None:
                pass

        m = Mediator()
        m.register_event_handler(SomeEvent, SomeHandler())
        m.clear()
        # After clear, no error and no handlers invoked
        await m.publish(SomeEvent())
