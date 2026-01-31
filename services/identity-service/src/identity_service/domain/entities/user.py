"""User domain entity - Aggregate root for user identity."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from shared.utils import now_utc

if TYPE_CHECKING:
    from identity_service.domain.value_objects import Email


@dataclass
class UserCredential:
    """User credential entity - manages password and MFA."""

    id: uuid.UUID = field(default_factory=uuid.uuid4)
    user_id: uuid.UUID | None = None
    password_hash: str = ""
    mfa_enabled: bool = False
    mfa_secret: str | None = None  # TOTP secret (encrypted)
    recovery_codes: list[str] = field(default_factory=list)
    last_password_change: datetime | None = None
    password_expires_at: datetime | None = None
    failed_login_attempts: int = 0
    locked_until: datetime | None = None
    created_at: datetime = field(default_factory=now_utc)
    updated_at: datetime = field(default_factory=now_utc)

    def is_locked(self) -> bool:
        """Check if account is currently locked."""
        if self.locked_until is None:
            return False
        return now_utc() < self.locked_until

    def increment_failed_attempts(self, max_attempts: int, lockout_duration: int) -> None:
        """Increment failed login attempts and lock if exceeded."""
        from datetime import timedelta

        self.failed_login_attempts += 1
        if self.failed_login_attempts >= max_attempts:
            self.locked_until = now_utc() + timedelta(seconds=lockout_duration)
        self.updated_at = now_utc()

    def reset_failed_attempts(self) -> None:
        """Reset failed login attempts after successful login."""
        self.failed_login_attempts = 0
        self.locked_until = None
        self.updated_at = now_utc()


@dataclass
class UserProfile:
    """User profile entity - stores user personal information."""

    id: uuid.UUID = field(default_factory=uuid.uuid4)
    user_id: uuid.UUID | None = None
    given_name: str | None = None
    family_name: str | None = None
    middle_name: str | None = None
    nickname: str | None = None
    preferred_username: str | None = None
    picture: str | None = None  # URL to profile picture
    website: str | None = None
    gender: str | None = None
    birthdate: str | None = None  # ISO 8601 date string
    zoneinfo: str | None = None  # Timezone
    locale: str | None = None  # BCP47 language tag
    phone_number: str | None = None
    phone_number_verified: bool = False
    address: dict | None = None  # OIDC address claim structure
    created_at: datetime = field(default_factory=now_utc)
    updated_at: datetime = field(default_factory=now_utc)

    @property
    def full_name(self) -> str | None:
        """Get full name from given and family name."""
        parts = [self.given_name, self.middle_name, self.family_name]
        name_parts = [p for p in parts if p]
        return " ".join(name_parts) if name_parts else None


@dataclass
class UserClaim:
    """Custom user claim entity."""

    id: uuid.UUID = field(default_factory=uuid.uuid4)
    user_id: uuid.UUID | None = None
    claim_type: str = ""
    claim_value: str = ""
    created_at: datetime = field(default_factory=now_utc)


@dataclass
class UserRole:
    """User role assignment entity."""

    id: uuid.UUID = field(default_factory=uuid.uuid4)
    user_id: uuid.UUID | None = None
    role_name: str = ""
    assigned_at: datetime = field(default_factory=now_utc)
    assigned_by: uuid.UUID | None = None
    expires_at: datetime | None = None

    def is_active(self) -> bool:
        """Check if role assignment is active."""
        if self.expires_at is None:
            return True
        return now_utc() < self.expires_at


@dataclass
class User:
    """User aggregate root - represents a user identity.

    This is the main entity for user identity management.
    It contains all related entities as part of the aggregate.
    """

    id: uuid.UUID = field(default_factory=uuid.uuid4)
    email: str = ""
    email_verified: bool = False
    username: str | None = None
    is_active: bool = True
    is_system: bool = False  # System/service accounts
    external_id: str | None = None  # For federated identity
    external_provider: str | None = None  # e.g., "google", "azure-ad"
    credential: UserCredential | None = None
    profile: UserProfile | None = None
    claims: list[UserClaim] = field(default_factory=list)
    roles: list[UserRole] = field(default_factory=list)
    created_at: datetime = field(default_factory=now_utc)
    updated_at: datetime = field(default_factory=now_utc)

    def __post_init__(self) -> None:
        """Initialize nested entities if not provided."""
        if self.credential is None:
            self.credential = UserCredential(user_id=self.id)
        else:
            self.credential.user_id = self.id

        if self.profile is None:
            self.profile = UserProfile(user_id=self.id)
        else:
            self.profile.user_id = self.id

    @property
    def subject_id(self) -> str:
        """Get subject identifier for tokens."""
        return str(self.id)

    def get_display_name(self) -> str:
        """Get user display name."""
        if self.profile and self.profile.full_name:
            return self.profile.full_name
        if self.username:
            return self.username
        return self.email.split("@")[0]

    def has_role(self, role_name: str) -> bool:
        """Check if user has a specific role."""
        return any(r.role_name == role_name and r.is_active() for r in self.roles)

    def add_role(self, role_name: str, assigned_by: uuid.UUID | None = None) -> None:
        """Add a role to the user."""
        if not self.has_role(role_name):
            self.roles.append(
                UserRole(user_id=self.id, role_name=role_name, assigned_by=assigned_by)
            )
            self.updated_at = now_utc()

    def remove_role(self, role_name: str) -> None:
        """Remove a role from the user."""
        self.roles = [r for r in self.roles if r.role_name != role_name]
        self.updated_at = now_utc()

    def add_claim(self, claim_type: str, claim_value: str) -> None:
        """Add a custom claim to the user."""
        self.claims.append(
            UserClaim(user_id=self.id, claim_type=claim_type, claim_value=claim_value)
        )
        self.updated_at = now_utc()

    def get_claims_dict(self) -> dict[str, str]:
        """Get all claims as a dictionary."""
        return {c.claim_type: c.claim_value for c in self.claims}

    def get_active_roles(self) -> list[str]:
        """Get list of active role names."""
        return [r.role_name for r in self.roles if r.is_active()]

    def can_login(self) -> tuple[bool, str | None]:
        """Check if user can login, returns (can_login, reason_if_not)."""
        if not self.is_active:
            return False, "Account is deactivated"
        if self.credential and self.credential.is_locked():
            return False, "Account is temporarily locked"
        return True, None

    def get_userinfo_claims(self, scopes: list[str]) -> dict:
        """Get OIDC userinfo claims based on requested scopes.

        Args:
            scopes: List of requested scopes (openid, profile, email, etc.)

        Returns:
            Dictionary of claims for the userinfo endpoint.
        """
        claims: dict = {"sub": self.subject_id}

        if "profile" in scopes and self.profile:
            profile_claims = {
                "name": self.profile.full_name,
                "given_name": self.profile.given_name,
                "family_name": self.profile.family_name,
                "middle_name": self.profile.middle_name,
                "nickname": self.profile.nickname,
                "preferred_username": self.profile.preferred_username or self.username,
                "picture": self.profile.picture,
                "website": self.profile.website,
                "gender": self.profile.gender,
                "birthdate": self.profile.birthdate,
                "zoneinfo": self.profile.zoneinfo,
                "locale": self.profile.locale,
                "updated_at": int(self.profile.updated_at.timestamp()),
            }
            claims.update({k: v for k, v in profile_claims.items() if v is not None})

        if "email" in scopes:
            claims["email"] = self.email
            claims["email_verified"] = self.email_verified

        if "phone" in scopes and self.profile:
            if self.profile.phone_number:
                claims["phone_number"] = self.profile.phone_number
                claims["phone_number_verified"] = self.profile.phone_number_verified

        if "address" in scopes and self.profile and self.profile.address:
            claims["address"] = self.profile.address

        # Add custom claims
        for claim in self.claims:
            claims[claim.claim_type] = claim.claim_value

        # Add roles if any
        if self.roles:
            claims["roles"] = self.get_active_roles()

        return claims
