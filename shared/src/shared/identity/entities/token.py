"""Token domain entities - Authorization codes and tokens."""

from __future__ import annotations

import secrets
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from shared.identity.value_objects import TokenType
from shared.utils import now_utc


@dataclass
class AuthorizationCode:
    """Authorization code entity - used in authorization code flow.

    Short-lived code exchanged for tokens. Stored in Redis.
    """

    id: uuid.UUID = field(default_factory=uuid.uuid4)
    code: str = field(default_factory=lambda: secrets.token_urlsafe(32))
    client_id: str = ""
    user_id: uuid.UUID | None = None
    redirect_uri: str = ""
    scope: str = ""
    nonce: str | None = None  # Required for OIDC
    state: str | None = None
    code_challenge: str | None = None  # PKCE
    code_challenge_method: str | None = None  # "S256" or "plain"
    created_at: datetime = field(default_factory=now_utc)
    expires_at: datetime | None = None
    is_used: bool = False

    def __post_init__(self) -> None:
        """Set default expiration if not provided."""
        if self.expires_at is None:
            # Authorization codes expire in 10 minutes
            self.expires_at = now_utc() + timedelta(minutes=10)

    def is_expired(self) -> bool:
        """Check if code has expired."""
        if self.expires_at is None:
            return False
        return now_utc() > self.expires_at

    def is_valid(self) -> bool:
        """Check if code is still valid (not expired and not used)."""
        return not self.is_expired() and not self.is_used

    def mark_as_used(self) -> None:
        """Mark code as used (can only be used once)."""
        self.is_used = True

    def verify_pkce(self, code_verifier: str) -> bool:
        """Verify PKCE code verifier against stored challenge.

        Args:
            code_verifier: The code verifier from token request

        Returns:
            True if verification passes.
        """
        if not self.code_challenge:
            # PKCE not required for this request
            return True

        if self.code_challenge_method == "plain":
            return code_verifier == self.code_challenge

        if self.code_challenge_method == "S256":
            import base64
            import hashlib

            # SHA256 hash of verifier, then base64url encode
            digest = hashlib.sha256(code_verifier.encode()).digest()
            computed = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
            return computed == self.code_challenge

        return False

    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "id": str(self.id),
            "code": self.code,
            "client_id": self.client_id,
            "user_id": str(self.user_id) if self.user_id else None,
            "redirect_uri": self.redirect_uri,
            "scope": self.scope,
            "nonce": self.nonce,
            "state": self.state,
            "code_challenge": self.code_challenge,
            "code_challenge_method": self.code_challenge_method,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_used": self.is_used,
        }

    @classmethod
    def from_dict(cls, data: dict) -> AuthorizationCode:
        """Create from dictionary."""
        return cls(
            id=uuid.UUID(data["id"]),
            code=data["code"],
            client_id=data["client_id"],
            user_id=uuid.UUID(data["user_id"]) if data.get("user_id") else None,
            redirect_uri=data["redirect_uri"],
            scope=data["scope"],
            nonce=data.get("nonce"),
            state=data.get("state"),
            code_challenge=data.get("code_challenge"),
            code_challenge_method=data.get("code_challenge_method"),
            created_at=datetime.fromisoformat(data["created_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"])
            if data.get("expires_at")
            else None,
            is_used=data.get("is_used", False),
        )


@dataclass
class RefreshToken:
    """Refresh token entity - stored in database for tracking.

    Long-lived opaque token used to obtain new access tokens.
    """

    id: uuid.UUID = field(default_factory=uuid.uuid4)
    token: str = field(default_factory=lambda: secrets.token_urlsafe(48))
    client_id: str = ""
    user_id: uuid.UUID | None = None
    scope: str = ""
    issued_at: datetime = field(default_factory=now_utc)
    expires_at: datetime | None = None
    is_revoked: bool = False
    revoked_at: datetime | None = None
    replaced_by: str | None = None  # Token rotation
    parent_token: str | None = None  # For token chain tracking

    def __post_init__(self) -> None:
        """Set default expiration if not provided."""
        if self.expires_at is None:
            # Refresh tokens expire in 30 days
            self.expires_at = now_utc() + timedelta(days=30)

    def is_expired(self) -> bool:
        """Check if token has expired."""
        if self.expires_at is None:
            return False
        return now_utc() > self.expires_at

    def is_valid(self) -> bool:
        """Check if token is still valid."""
        return not self.is_expired() and not self.is_revoked

    def revoke(self, replaced_by: str | None = None) -> None:
        """Revoke this token."""
        self.is_revoked = True
        self.revoked_at = now_utc()
        self.replaced_by = replaced_by


@dataclass
class TokenInfo:
    """Token information for introspection response."""

    active: bool = True
    scope: str | None = None
    client_id: str | None = None
    username: str | None = None
    token_type: TokenType = TokenType.BEARER
    exp: int | None = None  # Expiration timestamp
    iat: int | None = None  # Issued at timestamp
    nbf: int | None = None  # Not before timestamp
    sub: str | None = None  # Subject identifier
    aud: str | list[str] | None = None  # Audience
    iss: str | None = None  # Issuer
    jti: str | None = None  # JWT ID

    def to_dict(self) -> dict:
        """Convert to introspection response format."""
        result = {"active": self.active}

        if self.active:
            if self.scope:
                result["scope"] = self.scope
            if self.client_id:
                result["client_id"] = self.client_id
            if self.username:
                result["username"] = self.username
            result["token_type"] = self.token_type.value
            if self.exp:
                result["exp"] = self.exp
            if self.iat:
                result["iat"] = self.iat
            if self.nbf:
                result["nbf"] = self.nbf
            if self.sub:
                result["sub"] = self.sub
            if self.aud:
                result["aud"] = self.aud
            if self.iss:
                result["iss"] = self.iss
            if self.jti:
                result["jti"] = self.jti

        return result


@dataclass
class TokenBlacklistEntry:
    """Entry in the token blacklist (for revoked JWTs).

    Stored in Redis with TTL matching token expiration.
    """

    jti: str = ""  # JWT ID
    revoked_at: datetime = field(default_factory=now_utc)
    reason: str | None = None
    expires_at: datetime | None = None  # When entry can be removed

    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "jti": self.jti,
            "revoked_at": self.revoked_at.isoformat(),
            "reason": self.reason,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> TokenBlacklistEntry:
        """Create from dictionary."""
        return cls(
            jti=data["jti"],
            revoked_at=datetime.fromisoformat(data["revoked_at"]),
            reason=data.get("reason"),
            expires_at=datetime.fromisoformat(data["expires_at"])
            if data.get("expires_at")
            else None,
        )
