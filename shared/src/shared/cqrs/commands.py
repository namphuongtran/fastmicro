"""Command types and command bus.

A *command* represents an intent to change system state.  Each command
type has exactly one handler.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

from shared.cqrs.bus import MessageBus

R = TypeVar("R")  # Return / result type
C = TypeVar("C", bound="Command[Any]")


@dataclass(frozen=True)
class Command(Generic[R]):
    """Base class for all commands.

    Commands are **immutable** data carriers that describe an intent
    to mutate system state.  The generic parameter ``R`` is the
    expected return type of the handler.

    Attributes:
        metadata: Optional dict for carrying cross-cutting context
            (correlation ID, tenant ID, user context, etc.).

    Example::

        @dataclass(frozen=True)
        class CreateOrder(Command[str]):
            customer_id: str
            items: list[str]
    """

    metadata: dict[str, Any] = field(
        default_factory=dict, compare=False, repr=False, kw_only=True,
    )


class CommandHandler(ABC, Generic[C, R]):
    """Handler for a specific command type.

    Subclass and implement :meth:`handle` to process the command.

    Example::

        class CreateOrderHandler(CommandHandler[CreateOrder, str]):
            async def handle(self, command: CreateOrder) -> str:
                order_id = await self._repo.create(command)
                return order_id
    """

    @abstractmethod
    async def handle(self, command: C) -> R:
        """Execute the command and return a result.

        Args:
            command: The command to process.

        Returns:
            The result of the command execution.
        """
        ...


class CommandBus(MessageBus[Command[Any], CommandHandler[Any, Any]]):
    """Dispatches commands to their registered handlers.

    Each command type may have at most **one** handler.
    Uses copy-on-write for thread-safe lock-free reads on the hot path.

    Example::

        bus = CommandBus()
        bus.register(CreateOrder, CreateOrderHandler())
        order_id = await bus.dispatch(CreateOrder(customer_id="c1", items=["x"]))
    """

    _label: str = "command"
