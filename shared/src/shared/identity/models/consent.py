"""Consent ORM models.

Maps to domain entities: Consent, ConsentScope.
Note: Session entity is stored in Redis, not PostgreSQL.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.identity.models.base import IdentityBase


class ConsentModel(IdentityBase):
    """ORM model for consents - user consent for client access."""

    __tablename__ = "consents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    client_id: Mapped[str] = mapped_column(String(255), nullable=False)
    remember: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    scopes: Mapped[list[ConsentScopeModel]] = relationship(
        "ConsentScopeModel",
        back_populates="consent",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_consents_user_client", "user_id", "client_id", unique=True),
        Index("ix_consents_user", "user_id"),
        Index("ix_consents_client", "client_id"),
    )


class ConsentScopeModel(IdentityBase):
    """ORM model for consent_scopes - individual granted scopes."""

    __tablename__ = "consent_scopes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    consent_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("consents.id", ondelete="CASCADE"), nullable=False
    )
    scope: Mapped[str] = mapped_column(String(255), nullable=False)
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    consent: Mapped[ConsentModel] = relationship("ConsentModel", back_populates="scopes")

    __table_args__ = (Index("ix_consent_scopes_consent", "consent_id"),)
