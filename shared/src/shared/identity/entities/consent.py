"""Consent domain entity - User consent for client access."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime

from shared.utils import now_utc


@dataclass
class ConsentScope:
    """Individual scope within a consent."""

    id: uuid.UUID = field(default_factory=uuid.uuid4)
    consent_id: uuid.UUID | None = None
    scope: str = ""
    granted_at: datetime = field(default_factory=now_utc)


@dataclass
class Consent:
    """User consent aggregate - records user consent for client access.

    Tracks which scopes a user has granted to which clients.
    """

    id: uuid.UUID = field(default_factory=uuid.uuid4)
    user_id: uuid.UUID | None = None
    client_id: str = ""  # OAuth2 client_id string
    scopes: list[ConsentScope] = field(default_factory=list)
    remember: bool = False  # Whether to skip consent prompt in future
    created_at: datetime = field(default_factory=now_utc)
    updated_at: datetime = field(default_factory=now_utc)
    expires_at: datetime | None = None

    def is_valid(self) -> bool:
        """Check if consent is still valid."""
        if self.expires_at is None:
            return True
        return now_utc() < self.expires_at

    def get_granted_scopes(self) -> list[str]:
        """Get list of granted scope strings."""
        return [s.scope for s in self.scopes]

    def has_scope(self, scope: str) -> bool:
        """Check if a specific scope is granted."""
        return scope in self.get_granted_scopes()

    def covers_scopes(self, requested_scopes: list[str]) -> bool:
        """Check if consent covers all requested scopes.

        Args:
            requested_scopes: List of scopes to check

        Returns:
            True if all requested scopes are granted.
        """
        granted = set(self.get_granted_scopes())
        return all(scope in granted for scope in requested_scopes)

    def add_scope(self, scope: str) -> None:
        """Add a scope to the consent."""
        if not self.has_scope(scope):
            self.scopes.append(ConsentScope(consent_id=self.id, scope=scope))
            self.updated_at = now_utc()

    def remove_scope(self, scope: str) -> None:
        """Remove a scope from the consent."""
        self.scopes = [s for s in self.scopes if s.scope != scope]
        self.updated_at = now_utc()

    def update_scopes(self, scopes: list[str]) -> None:
        """Update the granted scopes.

        Args:
            scopes: New list of scopes to grant
        """
        # Keep track of which scopes to add/remove
        current_scopes = set(self.get_granted_scopes())
        new_scopes = set(scopes)

        # Remove scopes that are no longer granted
        for scope in current_scopes - new_scopes:
            self.remove_scope(scope)

        # Add new scopes
        for scope in new_scopes - current_scopes:
            self.add_scope(scope)


@dataclass
class Session:
    """User session entity - tracks authenticated sessions.

    Stored in Redis for fast lookup.
    """

    id: uuid.UUID = field(default_factory=uuid.uuid4)
    user_id: uuid.UUID | None = None
    client_id: str | None = None  # Which client initiated session
    ip_address: str | None = None
    user_agent: str | None = None
    created_at: datetime = field(default_factory=now_utc)
    last_activity: datetime = field(default_factory=now_utc)
    expires_at: datetime | None = None
    is_active: bool = True

    def is_valid(self) -> bool:
        """Check if session is still valid."""
        if not self.is_active:
            return False
        return not (self.expires_at and now_utc() > self.expires_at)

    def update_activity(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = now_utc()

    def terminate(self) -> None:
        """Terminate the session."""
        self.is_active = False

    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id) if self.user_id else None,
            "client_id": self.client_id,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_active": self.is_active,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Session:
        """Create from dictionary."""
        return cls(
            id=uuid.UUID(data["id"]),
            user_id=uuid.UUID(data["user_id"]) if data.get("user_id") else None,
            client_id=data.get("client_id"),
            ip_address=data.get("ip_address"),
            user_agent=data.get("user_agent"),
            created_at=datetime.fromisoformat(data["created_at"]),
            last_activity=datetime.fromisoformat(data["last_activity"]),
            expires_at=datetime.fromisoformat(data["expires_at"])
            if data.get("expires_at")
            else None,
            is_active=data.get("is_active", True),
        )
