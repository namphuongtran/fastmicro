"""Generic message bus with copy-on-write dispatch.

This module provides a reusable :class:`MessageBus` base that handles
handler registration and dispatch with thread-safe copy-on-write
semantics.  :class:`~shared.cqrs.commands.CommandBus` and
:class:`~shared.cqrs.queries.QueryBus` are thin type-safe wrappers.
"""

from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

M = TypeVar("M")  # Message (Command, Query, …)
H = TypeVar("H")  # Handler type


class MessageHandler(ABC, Generic[M]):
    """Protocol-level base for all message handlers."""

    @abstractmethod
    async def handle(self, message: M) -> Any:
        """Process *message* and return a result."""
        ...


class MessageBus(Generic[M, H]):
    """Generic copy-on-write message bus.

    Provides thread-safe registration and lock-free dispatch.
    Subclasses should specialise the type parameters for type safety.

    Type Parameters:
        M: The base message type (e.g. ``Command``, ``Query``).
        H: The handler type (e.g. ``CommandHandler``, ``QueryHandler``).
    """

    _label: str = "message"  # Override for nicer error messages

    def __init__(self) -> None:
        self._handlers: dict[type[M], H] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Registration (copy-on-write)
    # ------------------------------------------------------------------

    def register(self, message_type: type[M], handler: H) -> None:
        """Register *handler* for *message_type*.

        Raises:
            ValueError: If a handler is already registered.
        """
        with self._lock:
            if message_type in self._handlers:
                raise ValueError(f"A handler is already registered for {message_type.__name__}")
            new = dict(self._handlers)
            new[message_type] = handler
            self._handlers = new

    def unregister(self, message_type: type[M]) -> None:
        """Remove the handler for *message_type*.

        Raises:
            KeyError: If no handler is registered.
        """
        with self._lock:
            if message_type not in self._handlers:
                raise KeyError(f"No handler registered for {message_type.__name__}")
            new = dict(self._handlers)
            del new[message_type]
            self._handlers = new

    # ------------------------------------------------------------------
    # Dispatch (lock-free snapshot read)
    # ------------------------------------------------------------------

    async def dispatch(self, message: M) -> Any:
        """Send *message* to its registered handler.

        Raises:
            KeyError: If no handler is registered.
        """
        handler = self._handlers.get(type(message))
        if handler is None:
            raise KeyError(f"No handler registered for {type(message).__name__}")
        return await handler.handle(message)  # type: ignore[union-attr]

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def has_handler(self, message_type: type[M]) -> bool:
        """Check whether a handler is registered."""
        return message_type in self._handlers

    def clear(self) -> None:
        """Remove all handler registrations."""
        with self._lock:
            self._handlers = {}
