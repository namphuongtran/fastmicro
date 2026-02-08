"""User aggregate root — core domain entity.

The User aggregate encapsulates user profile data, preferences,
and raises domain events for cross-service communication.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from shared.ddd import AggregateRoot, DomainEvent


@dataclass
class UserCreated(DomainEvent):
    """Raised when a new user profile is created."""

    user_id: str = ""
    email: str = ""
    display_name: str = ""
    tenant_id: str | None = None


@dataclass
class UserUpdated(DomainEvent):
    """Raised when a user profile is updated."""

    user_id: str = ""
    changed_fields: list[str] = field(default_factory=list)


@dataclass
class UserDeactivated(DomainEvent):
    """Raised when a user is deactivated."""

    user_id: str = ""
    reason: str = ""


class User(AggregateRoot):
    """User aggregate root.

    Manages user profile, preferences, and tenant association.
    Raises domain events for cross-service integration.

    Attributes:
        email: User's email address.
        display_name: User's display name.
        first_name: Given name.
        last_name: Family name.
        tenant_id: Associated tenant identifier.
        is_active: Whether the user account is active.
        preferences: User preference key-value store.
        created_at: Account creation timestamp.
        updated_at: Last update timestamp.
    """

    __slots__ = (
        "_email",
        "_display_name",
        "_first_name",
        "_last_name",
        "_tenant_id",
        "_is_active",
        "_preferences",
        "_created_at",
        "_updated_at",
    )

    def __init__(
        self,
        id: str,
        email: str,
        display_name: str,
        *,
        first_name: str = "",
        last_name: str = "",
        tenant_id: str | None = None,
        is_active: bool = True,
        preferences: dict[str, Any] | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        """Initialize User aggregate.

        Args:
            id: Unique user identifier.
            email: User email address.
            display_name: Display name.
            first_name: Given name.
            last_name: Family name.
            tenant_id: Tenant identifier.
            is_active: Account active flag.
            preferences: User preferences.
            created_at: Creation timestamp.
            updated_at: Update timestamp.
        """
        super().__init__(id)
        self._email = email
        self._display_name = display_name
        self._first_name = first_name
        self._last_name = last_name
        self._tenant_id = tenant_id
        self._is_active = is_active
        self._preferences = preferences or {}
        self._created_at = created_at or datetime.now(UTC)
        self._updated_at = updated_at

    # --- Properties ---

    @property
    def email(self) -> str:
        return self._email

    @property
    def display_name(self) -> str:
        return self._display_name

    @property
    def first_name(self) -> str:
        return self._first_name

    @property
    def last_name(self) -> str:
        return self._last_name

    @property
    def tenant_id(self) -> str | None:
        return self._tenant_id

    @property
    def is_active(self) -> bool:
        return self._is_active

    @property
    def preferences(self) -> dict[str, Any]:
        return dict(self._preferences)

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime | None:
        return self._updated_at

    # --- Commands ---

    @classmethod
    def create(
        cls,
        id: str,
        email: str,
        display_name: str,
        *,
        first_name: str = "",
        last_name: str = "",
        tenant_id: str | None = None,
    ) -> User:
        """Factory method — create a new user and raise UserCreated event.

        Args:
            id: Unique user identifier.
            email: User email.
            display_name: Display name.
            first_name: Given name.
            last_name: Family name.
            tenant_id: Tenant identifier.

        Returns:
            New User aggregate with UserCreated domain event.
        """
        user = cls(
            id=id,
            email=email,
            display_name=display_name,
            first_name=first_name,
            last_name=last_name,
            tenant_id=tenant_id,
        )
        user.add_event(
            UserCreated(
                user_id=id,
                email=email,
                display_name=display_name,
                tenant_id=tenant_id,
                aggregate_id=id,
                aggregate_type="User",
            )
        )
        return user

    def update_profile(
        self,
        *,
        display_name: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> None:
        """Update user profile fields.

        Args:
            display_name: New display name.
            first_name: New given name.
            last_name: New family name.
        """
        changed: list[str] = []
        if display_name is not None and display_name != self._display_name:
            self._display_name = display_name
            changed.append("display_name")
        if first_name is not None and first_name != self._first_name:
            self._first_name = first_name
            changed.append("first_name")
        if last_name is not None and last_name != self._last_name:
            self._last_name = last_name
            changed.append("last_name")

        if changed:
            self._updated_at = datetime.now(UTC)
            self.add_event(
                UserUpdated(
                    user_id=self.id,
                    changed_fields=changed,
                    aggregate_id=self.id,
                    aggregate_type="User",
                )
            )

    def deactivate(self, reason: str = "") -> None:
        """Deactivate the user account.

        Args:
            reason: Reason for deactivation.
        """
        self._is_active = False
        self._updated_at = datetime.now(UTC)
        self.add_event(
            UserDeactivated(
                user_id=self.id,
                reason=reason,
                aggregate_id=self.id,
                aggregate_type="User",
            )
        )

    def set_preference(self, key: str, value: Any) -> None:
        """Set a user preference.

        Args:
            key: Preference key.
            value: Preference value.
        """
        self._preferences[key] = value
        self._updated_at = datetime.now(UTC)
