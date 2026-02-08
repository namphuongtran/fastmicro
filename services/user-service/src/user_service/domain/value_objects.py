"""User domain value objects."""

from __future__ import annotations

from dataclasses import dataclass

from shared.ddd import ValueObject


@dataclass(frozen=True)
class UserEmail(ValueObject):
    """Email value object with validation."""

    value: str

    def validate(self) -> None:
        """Validate email format."""
        if "@" not in self.value or "." not in self.value.split("@")[-1]:
            msg = f"Invalid email format: {self.value}"
            raise ValueError(msg)


@dataclass(frozen=True)
class UserPreference(ValueObject):
    """Key-value preference pair."""

    key: str
    value: str

    def validate(self) -> None:
        """Validate preference key is non-empty."""
        if not self.key.strip():
            msg = "Preference key cannot be empty"
            raise ValueError(msg)
