"""PostgreSQL PasswordResetRepository implementation.

Implements the PasswordResetRepository interface from identity-service domain.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.identity.mappers.user_mapper import (
    password_reset_entity_to_model,
    password_reset_model_to_entity,
)
from shared.identity.models.user import PasswordResetTokenModel

if TYPE_CHECKING:
    from shared.identity.entities.password_reset import PasswordResetToken


class PasswordResetRepository:
    """PostgreSQL-backed implementation of PasswordResetRepository interface."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, token: PasswordResetToken) -> None:
        """Save a password reset token."""
        model = password_reset_entity_to_model(token)
        self._session.add(model)
        await self._session.flush()

    async def get_by_token(self, token: str) -> PasswordResetToken | None:
        """Get reset token by its string value."""
        stmt = select(PasswordResetTokenModel).where(PasswordResetTokenModel.token == token)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return password_reset_model_to_entity(model) if model else None

    async def mark_as_used(self, token: str) -> bool:
        """Mark a password reset token as used."""
        stmt = select(PasswordResetTokenModel).where(PasswordResetTokenModel.token == token)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model or model.is_used:
            return False
        model.is_used = True
        model.used_at = datetime.now(UTC)
        await self._session.flush()
        return True

    async def delete_expired(self) -> int:
        """Delete all expired password reset tokens."""
        now = datetime.now(UTC)
        stmt = delete(PasswordResetTokenModel).where(PasswordResetTokenModel.expires_at < now)
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount  # type: ignore[return-value]

    async def delete_for_user(self, user_id: uuid.UUID) -> int:
        """Delete all reset tokens for a user."""
        stmt = delete(PasswordResetTokenModel).where(
            PasswordResetTokenModel.user_id == str(user_id)
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount  # type: ignore[return-value]
