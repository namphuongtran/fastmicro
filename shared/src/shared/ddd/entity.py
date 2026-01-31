"""Base entity classes for Domain-Driven Design.

This module provides the foundational entity classes:
- Entity: Base class with identity
- AggregateRoot: Entity that serves as an aggregate boundary
- EntityId: Typed ID wrapper for entities
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Generic, TypeVar
from uuid import uuid4

if TYPE_CHECKING:
    from shared.ddd.events import DomainEvent

T = TypeVar("T")


@dataclass(frozen=True)
class EntityId(Generic[T]):
    """Typed entity identifier.
    
    Wraps raw IDs to provide type safety and domain meaning.
    
    Example:
        >>> UserId = EntityId[str]
        >>> user_id = UserId("user-123")
        >>> user_id.value
        'user-123'
    """
    
    value: T
    
    def __str__(self) -> str:
        return str(self.value)
    
    def __hash__(self) -> int:
        return hash(self.value)
    
    def __eq__(self, other: object) -> bool:
        if isinstance(other, EntityId):
            return self.value == other.value
        return self.value == other
    
    @classmethod
    def generate(cls) -> EntityId[str]:
        """Generate a new UUID-based entity ID.
        
        Returns:
            New EntityId with UUID value.
        """
        return cls(str(uuid4()))


class Entity(ABC):
    """Base class for domain entities.
    
    An entity is an object defined primarily by its identity,
    rather than its attributes. Two entities with the same ID
    are considered the same entity.
    
    Attributes:
        _id: The entity's unique identifier
        _created_at: When the entity was created
        _updated_at: When the entity was last updated
    
    Example:
        >>> class User(Entity):
        ...     def __init__(self, id: str, name: str):
        ...         super().__init__(id)
        ...         self._name = name
        ...
        ...     @property
        ...     def name(self) -> str:
        ...         return self._name
    """
    
    __slots__ = ("_id", "_created_at", "_updated_at")
    
    def __init__(
        self,
        id: str | None = None,
        *,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        """Initialize entity.
        
        Args:
            id: Entity identifier. Generated if not provided.
            created_at: Creation timestamp. Defaults to now.
            updated_at: Update timestamp. Defaults to None.
        """
        self._id = id or str(uuid4())
        self._created_at = created_at or datetime.now(timezone.utc)
        self._updated_at = updated_at
    
    @property
    def id(self) -> str:
        """Get the entity's unique identifier."""
        return self._id
    
    @property
    def created_at(self) -> datetime:
        """Get the creation timestamp."""
        return self._created_at
    
    @property
    def updated_at(self) -> datetime | None:
        """Get the last update timestamp."""
        return self._updated_at
    
    def mark_updated(self) -> None:
        """Mark the entity as updated with current timestamp."""
        self._updated_at = datetime.now(timezone.utc)
    
    def __eq__(self, other: object) -> bool:
        """Two entities are equal if they have the same ID."""
        if not isinstance(other, Entity):
            return False
        return self._id == other._id
    
    def __hash__(self) -> int:
        """Hash based on entity ID."""
        return hash(self._id)
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self._id!r})"


class AggregateRoot(Entity):
    """Base class for aggregate roots.
    
    An aggregate root is an entity that serves as the entry point
    to an aggregate - a cluster of domain objects treated as a single unit.
    
    Aggregate roots:
    - Own domain events that occur within the aggregate
    - Enforce invariants across the aggregate
    - Are the only entities directly loadable from repositories
    
    Example:
        >>> class Order(AggregateRoot):
        ...     def __init__(self, id: str, customer_id: str):
        ...         super().__init__(id)
        ...         self._customer_id = customer_id
        ...         self._items: list[OrderItem] = []
        ...
        ...     def add_item(self, product_id: str, quantity: int) -> None:
        ...         item = OrderItem(product_id, quantity)
        ...         self._items.append(item)
        ...         self.add_event(OrderItemAdded(self.id, product_id, quantity))
    """
    
    __slots__ = ("_domain_events", "_version")
    
    def __init__(
        self,
        id: str | None = None,
        *,
        version: int = 0,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        """Initialize aggregate root.
        
        Args:
            id: Entity identifier.
            version: Optimistic concurrency version.
            created_at: Creation timestamp.
            updated_at: Update timestamp.
        """
        super().__init__(id, created_at=created_at, updated_at=updated_at)
        self._domain_events: list[DomainEvent] = []
        self._version = version
    
    @property
    def version(self) -> int:
        """Get optimistic concurrency version."""
        return self._version
    
    def increment_version(self) -> None:
        """Increment version for optimistic concurrency."""
        self._version += 1
    
    @property
    def domain_events(self) -> list[DomainEvent]:
        """Get pending domain events."""
        return list(self._domain_events)
    
    def add_event(self, event: DomainEvent) -> None:
        """Add a domain event.
        
        Args:
            event: Domain event to add.
        """
        self._domain_events.append(event)
    
    def clear_events(self) -> list[DomainEvent]:
        """Clear and return pending domain events.
        
        Returns:
            List of cleared events.
        """
        events = list(self._domain_events)
        self._domain_events.clear()
        return events
    
    def has_pending_events(self) -> bool:
        """Check if there are pending domain events.
        
        Returns:
            True if there are pending events.
        """
        return len(self._domain_events) > 0


@dataclass
class Specification(ABC, Generic[T]):
    """Specification pattern for business rules.
    
    Encapsulates business logic for filtering or validating entities.
    
    Example:
        >>> @dataclass
        ... class ActiveUserSpec(Specification[User]):
        ...     def is_satisfied_by(self, user: User) -> bool:
        ...         return user.is_active and not user.is_deleted
    """
    
    @abstractmethod
    def is_satisfied_by(self, entity: T) -> bool:
        """Check if entity satisfies the specification.
        
        Args:
            entity: Entity to check.
            
        Returns:
            True if specification is satisfied.
        """
        ...
    
    def and_(self, other: Specification[T]) -> AndSpecification[T]:
        """Combine with AND logic."""
        return AndSpecification(self, other)
    
    def or_(self, other: Specification[T]) -> OrSpecification[T]:
        """Combine with OR logic."""
        return OrSpecification(self, other)
    
    def not_(self) -> NotSpecification[T]:
        """Negate specification."""
        return NotSpecification(self)


@dataclass
class AndSpecification(Specification[T]):
    """AND combination of specifications."""
    
    left: Specification[T]
    right: Specification[T]
    
    def is_satisfied_by(self, entity: T) -> bool:
        return self.left.is_satisfied_by(entity) and self.right.is_satisfied_by(entity)


@dataclass
class OrSpecification(Specification[T]):
    """OR combination of specifications."""
    
    left: Specification[T]
    right: Specification[T]
    
    def is_satisfied_by(self, entity: T) -> bool:
        return self.left.is_satisfied_by(entity) or self.right.is_satisfied_by(entity)


@dataclass
class NotSpecification(Specification[T]):
    """NOT negation of specification."""
    
    spec: Specification[T]
    
    def is_satisfied_by(self, entity: T) -> bool:
        return not self.spec.is_satisfied_by(entity)
