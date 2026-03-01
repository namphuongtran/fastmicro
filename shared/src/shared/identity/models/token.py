"""Token ORM models.

Maps to domain entity: RefreshToken.
Note: AuthorizationCode and TokenBlacklistEntry are stored in Redis,
not in PostgreSQL, so they have no ORM models here.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from shared.identity.models.base import IdentityBase


class RefreshTokenModel(IdentityBase):
    """ORM model for refresh_tokens - persisted in PostgreSQL."""

    __tablename__ = "refresh_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    token: Mapped[str] = mapped_column(String(255), nullable=False)
    client_id: Mapped[str] = mapped_column(String(255), nullable=False)
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    scope: Mapped[str] = mapped_column(Text, default="", nullable=False)
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    replaced_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    parent_token: Mapped[str | None] = mapped_column(String(255), nullable=True)

    __table_args__ = (
        Index("ix_refresh_tokens_token", "token", unique=True),
        Index("ix_refresh_tokens_user", "user_id"),
        Index("ix_refresh_tokens_client", "client_id"),
        Index("ix_refresh_tokens_active", "user_id", "is_revoked"),
    )
