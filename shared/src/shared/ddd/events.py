"""Domain events for Domain-Driven Design.

Domain events represent something that happened in the domain that
domain experts care about. They enable loose coupling between aggregates.

This module provides:
- DomainEvent: Base class for domain events
- DomainEventHandler: Interface for event handlers
- EventDispatcher: In-memory event dispatcher
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Generic, TypeVar
from uuid import uuid4

T = TypeVar("T", bound="DomainEvent")


@dataclass
class DomainEvent:
    """Base class for domain events.
    
    Domain events capture something that happened in the domain.
    They are immutable records of past occurrences.
    
    Attributes:
        event_id: Unique event identifier
        occurred_at: When the event occurred
        aggregate_id: ID of the aggregate that raised the event
        aggregate_type: Type name of the aggregate
        metadata: Additional event metadata
    
    Example:
        >>> @dataclass
        ... class OrderPlaced(DomainEvent):
        ...     order_id: str
        ...     customer_id: str
        ...     total_amount: Decimal
    """

    event_id: str = field(default_factory=lambda: str(uuid4()))
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    aggregate_id: str | None = None
    aggregate_type: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def event_type(self) -> str:
        """Get the event type name."""
        return self.__class__.__name__

    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary.
        
        Returns:
            Dictionary representation of the event.
        """
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "occurred_at": self.occurred_at.isoformat(),
            "aggregate_id": self.aggregate_id,
            "aggregate_type": self.aggregate_type,
            "metadata": self.metadata,
            "data": self._get_event_data(),
        }

    def _get_event_data(self) -> dict[str, Any]:
        """Get event-specific data.
        
        Override in subclasses to include custom data.
        
        Returns:
            Dictionary with event data.
        """
        # Get all fields except base DomainEvent fields
        base_fields = {"event_id", "occurred_at", "aggregate_id", "aggregate_type", "metadata"}
        return {
            k: v for k, v in self.__dict__.items()
            if k not in base_fields and not k.startswith("_")
        }


class DomainEventHandler(ABC, Generic[T]):
    """Abstract handler for domain events.
    
    Implement this interface to handle specific event types.
    
    Example:
        >>> class OrderPlacedHandler(DomainEventHandler[OrderPlaced]):
        ...     async def handle(self, event: OrderPlaced) -> None:
        ...         # Send confirmation email
        ...         await email_service.send_order_confirmation(event.order_id)
    """

    @abstractmethod
    async def handle(self, event: T) -> None:
        """Handle the domain event.
        
        Args:
            event: The domain event to handle.
        """
        ...


# Type alias for event handler functions
EventHandlerFn = Callable[[DomainEvent], Coroutine[Any, Any, None]]


class EventDispatcher:
    """In-memory domain event dispatcher.
    
    Dispatches events to registered handlers. Supports both
    class-based handlers and function handlers.
    
    Example:
        >>> dispatcher = EventDispatcher()
        
        >>> # Register function handler
        >>> @dispatcher.subscribe(OrderPlaced)
        ... async def on_order_placed(event: OrderPlaced):
        ...     print(f"Order {event.order_id} placed!")
        
        >>> # Register class handler
        >>> dispatcher.register(OrderPlaced, order_placed_handler)
        
        >>> # Dispatch event
        >>> await dispatcher.dispatch(OrderPlaced(order_id="123", ...))
    """

    def __init__(self) -> None:
        """Initialize event dispatcher."""
        self._handlers: dict[type[DomainEvent], list[EventHandlerFn]] = {}
        self._class_handlers: dict[type[DomainEvent], list[DomainEventHandler]] = {}

    def register(
        self,
        event_type: type[T],
        handler: DomainEventHandler[T] | EventHandlerFn,
    ) -> None:
        """Register a handler for an event type.
        
        Args:
            event_type: The event type to handle.
            handler: Handler instance or async function.
        """
        if isinstance(handler, DomainEventHandler):
            if event_type not in self._class_handlers:
                self._class_handlers[event_type] = []
            self._class_handlers[event_type].append(handler)
        else:
            if event_type not in self._handlers:
                self._handlers[event_type] = []
            self._handlers[event_type].append(handler)

    def subscribe(
        self, event_type: type[T]
    ) -> Callable[[EventHandlerFn], EventHandlerFn]:
        """Decorator to subscribe a function to an event type.
        
        Args:
            event_type: The event type to subscribe to.
            
        Returns:
            Decorator function.
            
        Example:
            >>> @dispatcher.subscribe(OrderPlaced)
            ... async def handle_order(event: OrderPlaced):
            ...     ...
        """
        def decorator(func: EventHandlerFn) -> EventHandlerFn:
            self.register(event_type, func)
            return func
        return decorator

    async def dispatch(self, event: DomainEvent) -> None:
        """Dispatch an event to all registered handlers.
        
        Args:
            event: The event to dispatch.
        """
        event_type = type(event)

        # Call function handlers
        for handler in self._handlers.get(event_type, []):
            await handler(event)

        # Call class handlers
        for handler in self._class_handlers.get(event_type, []):
            await handler.handle(event)

    async def dispatch_all(self, events: list[DomainEvent]) -> None:
        """Dispatch multiple events.
        
        Args:
            events: List of events to dispatch.
        """
        for event in events:
            await self.dispatch(event)

    def clear(self) -> None:
        """Clear all registered handlers."""
        self._handlers.clear()
        self._class_handlers.clear()

    def has_handlers(self, event_type: type[DomainEvent]) -> bool:
        """Check if event type has registered handlers.
        
        Args:
            event_type: Event type to check.
            
        Returns:
            True if handlers are registered.
        """
        return (
            event_type in self._handlers or
            event_type in self._class_handlers
        )


# Global event dispatcher (optional singleton)
_global_dispatcher: EventDispatcher | None = None


def get_event_dispatcher() -> EventDispatcher:
    """Get or create the global event dispatcher.
    
    Returns:
        Global EventDispatcher instance.
    """
    global _global_dispatcher
    if _global_dispatcher is None:
        _global_dispatcher = EventDispatcher()
    return _global_dispatcher


def reset_event_dispatcher() -> None:
    """Reset the global event dispatcher."""
    global _global_dispatcher
    _global_dispatcher = None
