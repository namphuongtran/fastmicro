"""OAuth2 Client domain entity - Aggregate root for client applications."""

from __future__ import annotations

import secrets
import uuid
from dataclasses import dataclass, field
from datetime import datetime

from shared.utils import now_utc

from identity_service.domain.value_objects import (
    AuthMethod,
    ClientType,
    GrantType,
    ResponseType,
)


@dataclass
class ClientSecret:
    """Client secret entity - stores hashed client credentials."""

    id: uuid.UUID = field(default_factory=uuid.uuid4)
    client_id: uuid.UUID | None = None
    secret_hash: str = ""  # Hashed secret
    description: str | None = None
    expires_at: datetime | None = None
    created_at: datetime = field(default_factory=now_utc)
    last_used_at: datetime | None = None
    is_revoked: bool = False

    def is_valid(self) -> bool:
        """Check if secret is still valid."""
        if self.is_revoked:
            return False
        if self.expires_at and now_utc() > self.expires_at:
            return False
        return True


@dataclass
class ClientScope:
    """Scope allowed for a client."""

    id: uuid.UUID = field(default_factory=uuid.uuid4)
    client_id: uuid.UUID | None = None
    scope: str = ""
    is_default: bool = False  # Granted without explicit request


@dataclass
class ClientRedirectUri:
    """Redirect URI registered for a client."""

    id: uuid.UUID = field(default_factory=uuid.uuid4)
    client_id: uuid.UUID | None = None
    uri: str = ""
    is_default: bool = False
    created_at: datetime = field(default_factory=now_utc)


@dataclass
class Client:
    """OAuth2 Client aggregate root - represents a registered application.

    This is the main entity for OAuth2 client management.
    Clients are applications that can request tokens on behalf of users.
    """

    id: uuid.UUID = field(default_factory=uuid.uuid4)
    client_id: str = ""  # Public identifier (shown to users)
    client_name: str = ""
    client_description: str | None = None
    client_uri: str | None = None  # Homepage URL
    logo_uri: str | None = None
    client_type: ClientType = ClientType.CONFIDENTIAL
    token_endpoint_auth_method: AuthMethod = AuthMethod.CLIENT_SECRET_BASIC

    # Allowed grants and responses
    grant_types: list[GrantType] = field(
        default_factory=lambda: [GrantType.AUTHORIZATION_CODE, GrantType.REFRESH_TOKEN]
    )
    response_types: list[ResponseType] = field(
        default_factory=lambda: [ResponseType.CODE]
    )

    # PKCE settings
    require_pkce: bool = True
    allow_plain_pkce: bool = False  # Only S256 recommended

    # Token settings (override defaults if set)
    access_token_lifetime: int | None = None
    refresh_token_lifetime: int | None = None
    id_token_lifetime: int | None = None

    # Consent settings
    require_consent: bool = True
    allow_remember_consent: bool = True

    # Security settings
    allowed_cors_origins: list[str] = field(default_factory=list)
    front_channel_logout_uri: str | None = None
    back_channel_logout_uri: str | None = None
    post_logout_redirect_uris: list[str] = field(default_factory=list)

    # Status
    is_active: bool = True
    is_first_party: bool = False  # First-party apps may skip consent

    # Related entities
    secrets: list[ClientSecret] = field(default_factory=list)
    scopes: list[ClientScope] = field(default_factory=list)
    redirect_uris: list[ClientRedirectUri] = field(default_factory=list)

    # Audit
    created_at: datetime = field(default_factory=now_utc)
    updated_at: datetime = field(default_factory=now_utc)
    created_by: uuid.UUID | None = None

    def __post_init__(self) -> None:
        """Generate client_id if not provided."""
        if not self.client_id:
            self.client_id = self._generate_client_id()

    @staticmethod
    def _generate_client_id() -> str:
        """Generate a secure client ID."""
        return secrets.token_urlsafe(24)

    def is_public_client(self) -> bool:
        """Check if this is a public client (SPA, mobile app)."""
        return self.client_type == ClientType.PUBLIC

    def supports_grant(self, grant_type: str) -> bool:
        """Check if client supports a specific grant type."""
        return grant_type in [g.value for g in self.grant_types]

    def supports_response_type(self, response_type: str) -> bool:
        """Check if client supports a specific response type."""
        return response_type in [r.value for r in self.response_types]

    def get_allowed_scopes(self) -> list[str]:
        """Get list of allowed scope strings."""
        return [s.scope for s in self.scopes]

    def get_default_scopes(self) -> list[str]:
        """Get list of default scope strings."""
        return [s.scope for s in self.scopes if s.is_default]

    def validate_scope(self, requested_scope: str) -> list[str]:
        """Validate and filter requested scopes.

        Args:
            requested_scope: Space-separated scope string

        Returns:
            List of valid scopes that client is allowed to request.
        """
        requested = set(requested_scope.split()) if requested_scope else set()
        allowed = set(self.get_allowed_scopes())

        # Return intersection of requested and allowed
        return list(requested & allowed)

    def validate_redirect_uri(self, uri: str | None) -> str | None:
        """Validate redirect URI against registered URIs.

        Args:
            uri: Redirect URI to validate

        Returns:
            The URI if valid, None otherwise.
        """
        if not self.redirect_uris:
            return None

        # If no URI provided, return default
        if uri is None:
            default_uris = [r for r in self.redirect_uris if r.is_default]
            if default_uris:
                return default_uris[0].uri
            return self.redirect_uris[0].uri

        # Check exact match
        registered_uris = [r.uri for r in self.redirect_uris]
        if uri in registered_uris:
            return uri

        return None

    def add_secret(self, description: str | None = None, expires_at: datetime | None = None) -> tuple[str, ClientSecret]:
        """Generate and add a new client secret.

        Returns:
            Tuple of (plain_secret, ClientSecret entity).
            The plain secret is only returned once and must be stored by caller.
        """
        from pwdlib import PasswordHash

        # Generate secure random secret
        plain_secret = secrets.token_urlsafe(32)
        # Use Argon2 for client secrets (no backward compat needed)
        hasher = PasswordHash.recommended()
        secret_hash = hasher.hash(plain_secret)

        secret = ClientSecret(
            client_id=self.id,
            secret_hash=secret_hash,
            description=description,
            expires_at=expires_at,
        )
        self.secrets.append(secret)
        self.updated_at = now_utc()

        return plain_secret, secret

    def verify_secret(self, plain_secret: str) -> bool:
        """Verify a client secret against stored hashes.

        Supports both Argon2 and legacy bcrypt hashes.

        Args:
            plain_secret: Plain text secret to verify

        Returns:
            True if secret matches any valid stored secret.
        """
        from pwdlib import PasswordHash
        from pwdlib.hashers.argon2 import Argon2Hasher
        from pwdlib.hashers.bcrypt import BcryptHasher

        # Support both Argon2 (new) and bcrypt (legacy) hashes
        hasher = PasswordHash((Argon2Hasher(), BcryptHasher()))

        for secret in self.secrets:
            if secret.is_valid():
                if hasher.verify(plain_secret, secret.secret_hash):
                    secret.last_used_at = now_utc()
                    return True
        return False

    def revoke_secret(self, secret_id: uuid.UUID) -> bool:
        """Revoke a specific secret.

        Args:
            secret_id: ID of secret to revoke

        Returns:
            True if secret was found and revoked.
        """
        for secret in self.secrets:
            if secret.id == secret_id:
                secret.is_revoked = True
                self.updated_at = now_utc()
                return True
        return False

    def add_scope(self, scope: str, is_default: bool = False) -> None:
        """Add an allowed scope to the client."""
        if scope not in self.get_allowed_scopes():
            self.scopes.append(
                ClientScope(client_id=self.id, scope=scope, is_default=is_default)
            )
            self.updated_at = now_utc()

    def add_redirect_uri(self, uri: str, is_default: bool = False) -> None:
        """Add a redirect URI to the client."""
        existing_uris = [r.uri for r in self.redirect_uris]
        if uri not in existing_uris:
            self.redirect_uris.append(
                ClientRedirectUri(client_id=self.id, uri=uri, is_default=is_default)
            )
            self.updated_at = now_utc()

    def can_authenticate(self) -> tuple[bool, str | None]:
        """Check if client can authenticate, returns (can_auth, reason_if_not)."""
        if not self.is_active:
            return False, "Client is deactivated"
        if self.client_type == ClientType.CONFIDENTIAL:
            valid_secrets = [s for s in self.secrets if s.is_valid()]
            if not valid_secrets:
                return False, "No valid client secrets"
        return True, None

    def to_metadata(self) -> dict:
        """Convert client to OIDC client metadata format."""
        return {
            "client_id": self.client_id,
            "client_name": self.client_name,
            "client_uri": self.client_uri,
            "logo_uri": self.logo_uri,
            "redirect_uris": [r.uri for r in self.redirect_uris],
            "grant_types": [g.value for g in self.grant_types],
            "response_types": [r.value for r in self.response_types],
            "scope": " ".join(self.get_allowed_scopes()),
            "token_endpoint_auth_method": self.token_endpoint_auth_method.value,
        }
