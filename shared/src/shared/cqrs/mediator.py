"""Mediator — unified dispatcher for commands and queries.

The Mediator combines a :class:`CommandBus` and :class:`QueryBus`
behind a single ``send()`` method, and threads a pipeline of
:class:`PipelineBehavior` instances around every dispatch.

It also supports 1:N domain event publishing via :meth:`publish`,
bridging CQRS with DDD domain events.

Example::

    mediator = Mediator()
    mediator.add_behavior(LoggingBehavior())
    mediator.register_command_handler(CreateUser, CreateUserHandler())
    mediator.register_query_handler(GetUserById, GetUserByIdHandler())

    user_id = await mediator.send(CreateUser(email="a@b.com", name="Alice"))
    user    = await mediator.send(GetUserById(user_id=user_id))

    # Publish domain events (1:N handlers)
    mediator.register_event_handler(OrderPlaced, SendConfirmationEmail())
    mediator.register_event_handler(OrderPlaced, UpdateInventory())
    await mediator.publish(OrderPlaced(order_id="123"))
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, TypeVar, overload

from shared.cqrs.commands import Command, CommandBus, CommandHandler
from shared.cqrs.pipeline import PipelineBehavior
from shared.cqrs.queries import Query, QueryBus, QueryHandler
from shared.ddd.events import DomainEvent, DomainEventHandler

R = TypeVar("R")
C = TypeVar("C", bound=Command[Any])
Q = TypeVar("Q", bound=Query[Any])
E = TypeVar("E", bound=DomainEvent)


class Mediator:
    """Unified dispatcher with middleware pipeline and event publishing.

    The mediator owns a :class:`CommandBus` and a :class:`QueryBus`,
    wraps every dispatch in registered :class:`PipelineBehavior`
    instances, and supports 1:N :class:`DomainEvent` publishing.

    Args:
        behaviors: Optional initial list of pipeline behaviors.
    """

    def __init__(
        self,
        behaviors: list[PipelineBehavior] | None = None,
    ) -> None:
        self._command_bus = CommandBus()
        self._query_bus = QueryBus()
        self._behaviors: list[PipelineBehavior] = list(behaviors or [])
        self._pipeline_version: int = 0
        self._event_handlers: dict[type[DomainEvent], list[DomainEventHandler[Any]]] = {}

    # ------------------------------------------------------------------
    # Pipeline behaviors
    # ------------------------------------------------------------------

    def add_behavior(self, behavior: PipelineBehavior) -> None:
        """Append a behavior to the pipeline.

        Behaviors are executed in the order they were added, with the
        first behavior being the outermost wrapper.

        Args:
            behavior: The behavior to add.
        """
        self._behaviors.append(behavior)
        self._pipeline_version += 1

    # ------------------------------------------------------------------
    # Handler registration
    # ------------------------------------------------------------------

    def register_command_handler(
        self,
        command_type: type[C],
        handler: CommandHandler[C, Any],
    ) -> None:
        """Register a handler for a command type.

        Args:
            command_type: The command class.
            handler: The handler instance.

        Raises:
            ValueError: If a handler is already registered.
        """
        self._command_bus.register(command_type, handler)

    def register_query_handler(
        self,
        query_type: type[Q],
        handler: QueryHandler[Q, Any],
    ) -> None:
        """Register a handler for a query type.

        Args:
            query_type: The query class.
            handler: The handler instance.

        Raises:
            ValueError: If a handler is already registered.
        """
        self._query_bus.register(query_type, handler)

    def register_event_handler(
        self,
        event_type: type[E],
        handler: DomainEventHandler[E],
    ) -> None:
        """Register a handler for a domain event type (1:N).

        Multiple handlers can be registered for the same event type.

        Args:
            event_type: The domain event class.
            handler: The handler instance.
        """
        self._event_handlers.setdefault(event_type, []).append(handler)

    # ------------------------------------------------------------------
    # Dispatch (commands / queries)
    # ------------------------------------------------------------------

    @overload
    async def send(self, request: Command[R]) -> R: ...
    @overload
    async def send(self, request: Query[R]) -> R: ...

    async def send(self, request: Command[R] | Query[R]) -> R:
        """Dispatch a command or query through the pipeline.

        The request is routed to either the :class:`CommandBus` or
        :class:`QueryBus` depending on its type, after passing
        through all registered pipeline behaviors that apply.

        Args:
            request: A :class:`Command` or :class:`Query` instance.

        Returns:
            The result from the handler.

        Raises:
            KeyError: If no handler is registered.
            TypeError: If *request* is neither a Command nor a Query.
        """
        if isinstance(request, Command):
            inner: Callable[[Any], Awaitable[Any]] = self._command_bus.dispatch
        elif isinstance(request, Query):
            inner = self._query_bus.dispatch
        else:
            raise TypeError(f"Expected Command or Query, got {type(request).__name__}")

        # Build the pipeline from the inside out, filtering by applies_to.
        handler = inner
        for behavior in reversed(self._behaviors):
            if behavior.applies_to(request):
                handler = _wrap(behavior, handler)

        return await handler(request)

    # ------------------------------------------------------------------
    # Publish (domain events — 1:N)
    # ------------------------------------------------------------------

    async def publish(self, event: DomainEvent) -> None:
        """Publish a domain event to all registered handlers.

        All handlers for the event type are called sequentially.

        Args:
            event: The domain event to publish.
        """
        handlers = self._event_handlers.get(type(event), [])
        for handler in handlers:
            await handler.handle(event)

    # ------------------------------------------------------------------
    # Introspection / management
    # ------------------------------------------------------------------

    @property
    def command_bus(self) -> CommandBus:
        """Access the underlying command bus."""
        return self._command_bus

    @property
    def query_bus(self) -> QueryBus:
        """Access the underlying query bus."""
        return self._query_bus

    def clear(self) -> None:
        """Remove all handlers, event handlers, and behaviors."""
        self._command_bus.clear()
        self._query_bus.clear()
        self._behaviors.clear()
        self._event_handlers.clear()
        self._pipeline_version = 0


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------


def _wrap(
    behavior: PipelineBehavior,
    next_: Callable[[Any], Awaitable[Any]],
) -> Callable[[Any], Awaitable[Any]]:
    """Create a closure that threads *next_* through *behavior*."""

    async def _pipeline(request: Any) -> Any:
        return await behavior.handle(request, next_)

    return _pipeline
