# Domain-Driven Design Module

This module provides foundational building blocks for implementing Domain-Driven Design (DDD) patterns in Python microservices.

## Overview

```
shared/ddd/
├── __init__.py          # Module exports
├── entity.py            # Entity, AggregateRoot, Specification
├── value_objects.py     # ValueObject base class and common types
└── events.py            # DomainEvent, EventDispatcher
```

## Key Concepts

### Entities

Entities are objects defined primarily by their identity rather than attributes.

```python
from shared.ddd import Entity, AggregateRoot

class User(Entity):
    def __init__(self, id: str, email: str, name: str):
        super().__init__(id)
        self._email = email
        self._name = name
    
    @property
    def email(self) -> str:
        return self._email

# Two entities with the same ID are equal
user1 = User("123", "john@example.com", "John")
user2 = User("123", "different@example.com", "Different")
assert user1 == user2  # True - same ID
```

### Aggregate Roots

Aggregate roots are entities that serve as entry points to aggregates and own domain events.

```python
from shared.ddd import AggregateRoot, DomainEvent
from dataclasses import dataclass

@dataclass
class OrderPlaced(DomainEvent):
    order_id: str
    customer_id: str
    total: Decimal

class Order(AggregateRoot):
    def __init__(self, id: str, customer_id: str):
        super().__init__(id)
        self._customer_id = customer_id
        self._items: list[OrderItem] = []
        self._status = "draft"
    
    def place(self) -> None:
        if not self._items:
            raise ValueError("Cannot place empty order")
        self._status = "placed"
        self.add_event(OrderPlaced(
            order_id=self.id,
            customer_id=self._customer_id,
            total=self._calculate_total(),
        ))
```

### Value Objects

Value objects are immutable and defined by their attributes.

```python
from shared.ddd import Email, Money, Percentage
from decimal import Decimal

# Built-in value objects
email = Email("user@example.com")
price = Money(Decimal("99.99"), "USD")
discount = Percentage(0.15)  # 15%

# Value objects are immutable and validated
try:
    invalid_email = Email("not-an-email")
except ValueError as e:
    print(e)  # Invalid email format

# Custom value objects
from shared.ddd import ValueObject
from dataclasses import dataclass

@dataclass(frozen=True)
class SKU(ValueObject):
    value: str
    
    def validate(self) -> None:
        if not self.value or len(self.value) < 6:
            raise ValueError("SKU must be at least 6 characters")
```

### Domain Events

Events represent something that happened in the domain.

```python
from shared.ddd import DomainEvent, EventDispatcher
from dataclasses import dataclass

@dataclass
class UserRegistered(DomainEvent):
    user_id: str
    email: str

# Create dispatcher
dispatcher = EventDispatcher()

# Register handler (decorator style)
@dispatcher.subscribe(UserRegistered)
async def send_welcome_email(event: UserRegistered):
    print(f"Sending welcome email to {event.email}")

# Dispatch events
await dispatcher.dispatch(UserRegistered(
    user_id="123",
    email="user@example.com",
    aggregate_id="123",
    aggregate_type="User",
))
```

## Available Value Objects

| Type | Description | Example |
|------|-------------|---------|
| `Email` | Validated email address | `Email("user@example.com")` |
| `PhoneNumber` | E.164 format phone | `PhoneNumber("+14155552671")` |
| `Money` | Currency + amount | `Money(Decimal("10.00"), "USD")` |
| `Percentage` | 0-1 decimal | `Percentage(0.15)` |
| `NonEmptyString` | Non-blank string | `NonEmptyString("Hello")` |
| `PositiveInt` | Integer > 0 | `PositiveInt(5)` |
| `PositiveDecimal` | Decimal > 0 | `PositiveDecimal(Decimal("2.5"))` |
| `DateRange` | Start/end dates | `DateRange(date(2024,1,1), date(2024,12,31))` |
| `Address` | Physical address | `Address(street="...", city="...", ...)` |

## Specification Pattern

Encapsulate business rules for filtering or validating entities:

```python
from shared.ddd.entity import Specification
from dataclasses import dataclass

@dataclass
class ActiveUserSpec(Specification[User]):
    def is_satisfied_by(self, user: User) -> bool:
        return user.is_active and not user.is_deleted

@dataclass
class PremiumUserSpec(Specification[User]):
    def is_satisfied_by(self, user: User) -> bool:
        return user.subscription_tier == "premium"

# Combine specifications
active_premium = ActiveUserSpec().and_(PremiumUserSpec())
active_or_premium = ActiveUserSpec().or_(PremiumUserSpec())
not_active = ActiveUserSpec().not_()
```

## Integration with Services

Use DDD patterns with the application service layer:

```python
from shared.ddd import AggregateRoot, DomainEvent, EventDispatcher
from shared.application import CRUDService

class UserService(CRUDService[User, str]):
    def __init__(
        self,
        repository: UserRepository,
        event_dispatcher: EventDispatcher,
    ):
        super().__init__()
        self._repository = repository
        self._dispatcher = event_dispatcher
    
    async def create(self, data: CreateUserDTO) -> User:
        user = User(email=data.email, name=data.name)
        await self._repository.add(user)
        
        # Dispatch domain events
        await self._dispatcher.dispatch_all(user.clear_events())
        
        return user
```

## Best Practices

1. **Keep aggregates small** - Only include entities that must be consistent together
2. **Reference other aggregates by ID** - Don't hold direct references
3. **Domain events for cross-aggregate communication** - Avoid direct coupling
4. **Value objects for validation** - Encapsulate validation in the type itself
5. **Immutable where possible** - Use `frozen=True` for dataclasses
6. **Rich domain models** - Put business logic in entities, not services
