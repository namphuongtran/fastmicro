"""Value objects for Domain-Driven Design.

Value objects are immutable objects defined by their attributes rather
than identity. Two value objects with the same attributes are equal.

This module provides:
- ValueObject: Base class for custom value objects
- Common value objects: Email, Money, Percentage, etc.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Generic, TypeVar

T = TypeVar("T")


class ValueObject(ABC):
    """Base class for value objects.
    
    Value objects are immutable and compared by their attributes.
    Subclasses should:
    - Be dataclasses with frozen=True
    - Implement validate() for business rules
    - Not have an identity field
    
    Example:
        >>> @dataclass(frozen=True)
        ... class Price(ValueObject):
        ...     amount: Decimal
        ...     currency: str
        ...
        ...     def validate(self) -> None:
        ...         if self.amount < 0:
        ...             raise ValueError("Price cannot be negative")
        ...         if len(self.currency) != 3:
        ...             raise ValueError("Currency must be 3 characters")
    """
    
    def __post_init__(self) -> None:
        """Validate after initialization."""
        self.validate()
    
    @abstractmethod
    def validate(self) -> None:
        """Validate the value object.
        
        Raises:
            ValueError: If validation fails.
        """
        ...


@dataclass(frozen=True)
class NonEmptyString(ValueObject):
    """A non-empty string value object.
    
    Example:
        >>> name = NonEmptyString("John")
        >>> name.value
        'John'
    """
    
    value: str
    min_length: int = 1
    max_length: int = 1000
    
    def validate(self) -> None:
        if not self.value or not self.value.strip():
            raise ValueError("Value cannot be empty")
        if len(self.value) < self.min_length:
            raise ValueError(f"Value must be at least {self.min_length} characters")
        if len(self.value) > self.max_length:
            raise ValueError(f"Value must be at most {self.max_length} characters")
    
    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class Email(ValueObject):
    """Email address value object with validation.
    
    Example:
        >>> email = Email("user@example.com")
        >>> email.local_part
        'user'
        >>> email.domain
        'example.com'
    """
    
    value: str
    
    # RFC 5322 simplified pattern
    _EMAIL_PATTERN = re.compile(
        r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    )
    
    def validate(self) -> None:
        if not self.value:
            raise ValueError("Email cannot be empty")
        if not self._EMAIL_PATTERN.match(self.value):
            raise ValueError(f"Invalid email format: {self.value}")
        if len(self.value) > 254:
            raise ValueError("Email too long (max 254 characters)")
    
    @property
    def local_part(self) -> str:
        """Get the local part (before @)."""
        return self.value.split("@")[0]
    
    @property
    def domain(self) -> str:
        """Get the domain part (after @)."""
        return self.value.split("@")[1]
    
    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class PhoneNumber(ValueObject):
    """Phone number value object with validation.
    
    Stores phone in E.164 format (e.g., +14155552671).
    
    Example:
        >>> phone = PhoneNumber("+14155552671")
        >>> phone.country_code
        '1'
    """
    
    value: str
    
    # E.164 format: + followed by 1-15 digits
    _PHONE_PATTERN = re.compile(r"^\+[1-9]\d{1,14}$")
    
    def validate(self) -> None:
        if not self.value:
            raise ValueError("Phone number cannot be empty")
        
        # Remove spaces and dashes for validation
        normalized = self.value.replace(" ", "").replace("-", "")
        
        if not self._PHONE_PATTERN.match(normalized):
            raise ValueError(f"Invalid phone number format: {self.value}")
    
    @property
    def country_code(self) -> str:
        """Extract country code (digits after + before first space)."""
        # Simplified: assume first 1-3 digits are country code
        digits = "".join(c for c in self.value if c.isdigit())
        return digits[:1] if len(digits) <= 11 else digits[:2] if len(digits) <= 12 else digits[:3]
    
    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class Money(ValueObject):
    """Monetary value with currency.
    
    Uses Decimal for precision. Supports basic arithmetic.
    
    Example:
        >>> price = Money(Decimal("99.99"), "USD")
        >>> discount = Money(Decimal("10.00"), "USD")
        >>> final = price - discount
        >>> final.amount
        Decimal('89.99')
    """
    
    amount: Decimal
    currency: str
    
    def validate(self) -> None:
        if not isinstance(self.amount, Decimal):
            raise ValueError("Amount must be a Decimal")
        if len(self.currency) != 3:
            raise ValueError("Currency must be 3-letter ISO code")
        if not self.currency.isupper():
            raise ValueError("Currency must be uppercase")
    
    def __add__(self, other: Money) -> Money:
        if not isinstance(other, Money):
            raise TypeError(f"Cannot add Money and {type(other)}")
        if self.currency != other.currency:
            raise ValueError(f"Cannot add different currencies: {self.currency} and {other.currency}")
        return Money(self.amount + other.amount, self.currency)
    
    def __sub__(self, other: Money) -> Money:
        if not isinstance(other, Money):
            raise TypeError(f"Cannot subtract {type(other)} from Money")
        if self.currency != other.currency:
            raise ValueError(f"Cannot subtract different currencies: {self.currency} and {other.currency}")
        return Money(self.amount - other.amount, self.currency)
    
    def __mul__(self, factor: int | float | Decimal) -> Money:
        return Money(self.amount * Decimal(str(factor)), self.currency)
    
    def __neg__(self) -> Money:
        return Money(-self.amount, self.currency)
    
    def __abs__(self) -> Money:
        return Money(abs(self.amount), self.currency)
    
    def __lt__(self, other: Money) -> bool:
        self._ensure_same_currency(other)
        return self.amount < other.amount
    
    def __le__(self, other: Money) -> bool:
        self._ensure_same_currency(other)
        return self.amount <= other.amount
    
    def __gt__(self, other: Money) -> bool:
        self._ensure_same_currency(other)
        return self.amount > other.amount
    
    def __ge__(self, other: Money) -> bool:
        self._ensure_same_currency(other)
        return self.amount >= other.amount
    
    def _ensure_same_currency(self, other: Money) -> None:
        if self.currency != other.currency:
            raise ValueError(f"Cannot compare different currencies: {self.currency} and {other.currency}")
    
    @property
    def is_positive(self) -> bool:
        return self.amount > 0
    
    @property
    def is_negative(self) -> bool:
        return self.amount < 0
    
    @property
    def is_zero(self) -> bool:
        return self.amount == 0
    
    def round_to(self, places: int = 2) -> Money:
        """Round to specified decimal places."""
        return Money(round(self.amount, places), self.currency)
    
    def __str__(self) -> str:
        return f"{self.currency} {self.amount:.2f}"
    
    @classmethod
    def zero(cls, currency: str) -> Money:
        """Create zero amount in given currency."""
        return cls(Decimal("0"), currency)


@dataclass(frozen=True)
class Percentage(ValueObject):
    """Percentage value object (0-100 or 0-1 scale).
    
    Internally stores as decimal (0-1), displays as percentage (0-100).
    
    Example:
        >>> rate = Percentage(0.15)  # 15%
        >>> rate.as_percentage
        15.0
        >>> rate.apply_to(Decimal("100"))
        Decimal('15.00')
    """
    
    value: Decimal | float
    
    def validate(self) -> None:
        val = float(self.value)
        if val < 0 or val > 1:
            raise ValueError(f"Percentage must be between 0 and 1, got {val}")
    
    @property
    def as_decimal(self) -> Decimal:
        """Get as decimal (0-1)."""
        return Decimal(str(self.value))
    
    @property
    def as_percentage(self) -> float:
        """Get as percentage (0-100)."""
        return float(self.value) * 100
    
    def apply_to(self, amount: Decimal) -> Decimal:
        """Apply percentage to an amount.
        
        Args:
            amount: Amount to apply percentage to.
            
        Returns:
            Resulting amount.
        """
        return amount * self.as_decimal
    
    def __str__(self) -> str:
        return f"{self.as_percentage:.1f}%"
    
    @classmethod
    def from_percentage(cls, value: float) -> Percentage:
        """Create from percentage value (0-100)."""
        return cls(value / 100)


@dataclass(frozen=True)
class PositiveInt(ValueObject):
    """Positive integer value object.
    
    Example:
        >>> quantity = PositiveInt(5)
        >>> quantity.value
        5
    """
    
    value: int
    
    def validate(self) -> None:
        if not isinstance(self.value, int):
            raise ValueError("Value must be an integer")
        if self.value <= 0:
            raise ValueError(f"Value must be positive, got {self.value}")
    
    def __int__(self) -> int:
        return self.value
    
    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class PositiveDecimal(ValueObject):
    """Positive decimal value object.
    
    Example:
        >>> weight = PositiveDecimal(Decimal("2.5"))
        >>> weight.value
        Decimal('2.5')
    """
    
    value: Decimal
    
    def validate(self) -> None:
        if self.value <= 0:
            raise ValueError(f"Value must be positive, got {self.value}")
    
    def __float__(self) -> float:
        return float(self.value)
    
    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class DateRange(ValueObject):
    """Date range value object.
    
    Represents a period between two dates (inclusive).
    
    Example:
        >>> period = DateRange(date(2024, 1, 1), date(2024, 12, 31))
        >>> period.days
        366
        >>> date(2024, 6, 15) in period
        True
    """
    
    start: date
    end: date
    
    def validate(self) -> None:
        if self.start > self.end:
            raise ValueError(f"Start date {self.start} must be before or equal to end date {self.end}")
    
    @property
    def days(self) -> int:
        """Number of days in range (inclusive)."""
        return (self.end - self.start).days + 1
    
    def contains(self, d: date) -> bool:
        """Check if date is within range."""
        return self.start <= d <= self.end
    
    def __contains__(self, d: date) -> bool:
        return self.contains(d)
    
    def overlaps(self, other: DateRange) -> bool:
        """Check if this range overlaps with another."""
        return self.start <= other.end and other.start <= self.end
    
    def __str__(self) -> str:
        return f"{self.start} to {self.end}"


@dataclass(frozen=True)
class Address(ValueObject):
    """Physical address value object.
    
    Example:
        >>> addr = Address(
        ...     street="123 Main St",
        ...     city="San Francisco",
        ...     state="CA",
        ...     postal_code="94102",
        ...     country="US"
        ... )
    """
    
    street: str
    city: str
    state: str | None
    postal_code: str
    country: str
    street2: str | None = None
    
    def validate(self) -> None:
        if not self.street or not self.street.strip():
            raise ValueError("Street is required")
        if not self.city or not self.city.strip():
            raise ValueError("City is required")
        if not self.postal_code or not self.postal_code.strip():
            raise ValueError("Postal code is required")
        if not self.country or len(self.country) != 2:
            raise ValueError("Country must be 2-letter ISO code")
    
    @property
    def full_address(self) -> str:
        """Get formatted full address."""
        parts = [self.street]
        if self.street2:
            parts.append(self.street2)
        parts.append(f"{self.city}, {self.state or ''} {self.postal_code}".strip())
        parts.append(self.country)
        return "\n".join(parts)
    
    def __str__(self) -> str:
        return f"{self.street}, {self.city}, {self.country}"
