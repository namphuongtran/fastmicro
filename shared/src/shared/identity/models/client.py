"""Client aggregate ORM models.

Maps to domain entities: Client, ClientSecret, ClientScope, ClientRedirectUri.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.identity.models.base import IdentityBase


class ClientModel(IdentityBase):
    """ORM model for clients table - OAuth2 client aggregate root."""

    __tablename__ = "clients"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    client_id: Mapped[str] = mapped_column(String(255), nullable=False)
    client_name: Mapped[str] = mapped_column(String(255), nullable=False)
    client_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    client_uri: Mapped[str | None] = mapped_column(String(500), nullable=True)
    logo_uri: Mapped[str | None] = mapped_column(String(500), nullable=True)
    client_type: Mapped[str] = mapped_column(String(20), default="confidential", nullable=False)
    token_endpoint_auth_method: Mapped[str] = mapped_column(
        String(50), default="client_secret_basic", nullable=False
    )

    # Grant/response types stored as comma-separated strings
    grant_types: Mapped[str] = mapped_column(
        Text, default="authorization_code,refresh_token", nullable=False
    )
    response_types: Mapped[str] = mapped_column(Text, default="code", nullable=False)

    # PKCE settings
    require_pkce: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    allow_plain_pkce: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Token lifetime overrides (seconds; NULL = use server default)
    access_token_lifetime: Mapped[int | None] = mapped_column(Integer, nullable=True)
    refresh_token_lifetime: Mapped[int | None] = mapped_column(Integer, nullable=True)
    id_token_lifetime: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Consent
    require_consent: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    allow_remember_consent: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Security
    allowed_cors_origins: Mapped[str | None] = mapped_column(Text, nullable=True)
    front_channel_logout_uri: Mapped[str | None] = mapped_column(String(500), nullable=True)
    back_channel_logout_uri: Mapped[str | None] = mapped_column(String(500), nullable=True)
    post_logout_redirect_uris: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_first_party: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Audit
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)

    # Relationships
    secrets: Mapped[list[ClientSecretModel]] = relationship(
        "ClientSecretModel",
        back_populates="client",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    scopes: Mapped[list[ClientScopeModel]] = relationship(
        "ClientScopeModel",
        back_populates="client",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    redirect_uris: Mapped[list[ClientRedirectUriModel]] = relationship(
        "ClientRedirectUriModel",
        back_populates="client",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_clients_client_id", "client_id", unique=True),
        Index("ix_clients_active", "is_active"),
        Index("ix_clients_created_by", "created_by"),
    )


class ClientSecretModel(IdentityBase):
    """ORM model for client_secrets."""

    __tablename__ = "client_secrets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    client_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False
    )
    secret_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    client: Mapped[ClientModel] = relationship("ClientModel", back_populates="secrets")


class ClientScopeModel(IdentityBase):
    """ORM model for client_scopes."""

    __tablename__ = "client_scopes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    client_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False
    )
    scope: Mapped[str] = mapped_column(String(255), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    client: Mapped[ClientModel] = relationship("ClientModel", back_populates="scopes")

    __table_args__ = (Index("ix_client_scopes_client_scope", "client_id", "scope", unique=True),)


class ClientRedirectUriModel(IdentityBase):
    """ORM model for client_redirect_uris."""

    __tablename__ = "client_redirect_uris"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    client_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False
    )
    uri: Mapped[str] = mapped_column(String(500), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    client: Mapped[ClientModel] = relationship("ClientModel", back_populates="redirect_uris")

    __table_args__ = (Index("ix_client_redirect_uris_client", "client_id"),)
