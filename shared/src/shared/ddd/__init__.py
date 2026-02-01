"""Domain-Driven Design building blocks.

This module provides foundational DDD patterns:
- **Entities**: Base classes for domain entities with identity
- **Value Objects**: Immutable objects defined by their attributes
- **Aggregates**: Entity clusters with a root
- **Domain Events**: Events for cross-aggregate communication

Example:
    >>> from shared.ddd import Entity, ValueObject, AggregateRoot, DomainEvent
    
    # Define a value object
    >>> @dataclass(frozen=True)
    ... class Email(ValueObject):
    ...     value: str
    ...     def validate(self) -> None:
    ...         if "@" not in self.value:
    ...             raise ValueError("Invalid email")
    
    # Define an entity
    >>> class User(AggregateRoot):
    ...     def __init__(self, id: str, email: Email):
    ...         super().__init__(id)
    ...         self._email = email
"""

from shared.ddd.entity import (
    AggregateRoot,
    Entity,
    EntityId,
)
from shared.ddd.events import (
    DomainEvent,
    DomainEventHandler,
    EventDispatcher,
)
from shared.ddd.value_objects import (
    Address,
    DateRange,
    Email,
    Money,
    NonEmptyString,
    Percentage,
    PhoneNumber,
    PositiveDecimal,
    PositiveInt,
    ValueObject,
)

__all__ = [
    # Entities
    "Entity",
    "AggregateRoot",
    "EntityId",
    # Value Objects
    "ValueObject",
    "Email",
    "PhoneNumber",
    "Money",
    "Percentage",
    "NonEmptyString",
    "PositiveInt",
    "PositiveDecimal",
    "DateRange",
    "Address",
    # Events
    "DomainEvent",
    "DomainEventHandler",
    "EventDispatcher",
]
