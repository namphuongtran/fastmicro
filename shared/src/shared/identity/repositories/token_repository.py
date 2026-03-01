"""PostgreSQL RefreshTokenRepository implementation.

Implements the RefreshTokenRepository interface from identity-service domain.
Note: AuthorizationCodeRepository and TokenBlacklistRepository are Redis-only
and remain in-memory for now.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from shared.identity.mappers.token_mapper import (
    refresh_token_entity_to_model,
    refresh_token_model_to_entity,
)
from shared.identity.models.token import RefreshTokenModel

if TYPE_CHECKING:
    from shared.identity.entities import RefreshToken


class RefreshTokenRepository:
    """PostgreSQL-backed implementation of RefreshTokenRepository interface."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, token: RefreshToken) -> RefreshToken:
        """Save a refresh token."""
        model = refresh_token_entity_to_model(token)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return refresh_token_model_to_entity(model)

    async def get_by_token(self, token: str) -> RefreshToken | None:
        """Get refresh token by its string value."""
        stmt = select(RefreshTokenModel).where(RefreshTokenModel.token == token)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return refresh_token_model_to_entity(model) if model else None

    async def get_by_id(self, token_id: uuid.UUID) -> RefreshToken | None:
        """Get refresh token by UUID."""
        stmt = select(RefreshTokenModel).where(RefreshTokenModel.id == str(token_id))
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return refresh_token_model_to_entity(model) if model else None

    async def revoke(self, token: str, replaced_by: str | None = None) -> bool:
        """Revoke a refresh token, optionally noting its replacement."""
        stmt = select(RefreshTokenModel).where(RefreshTokenModel.token == token)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model or model.is_revoked:
            return False
        model.is_revoked = True
        model.revoked_at = datetime.now(UTC)
        if replaced_by:
            model.replaced_by = replaced_by
        await self._session.flush()
        return True

    async def revoke_all_for_user(self, user_id: uuid.UUID) -> int:
        """Revoke all active refresh tokens for a user."""
        now = datetime.now(UTC)
        stmt = (
            update(RefreshTokenModel)
            .where(
                RefreshTokenModel.user_id == str(user_id),
                RefreshTokenModel.is_revoked.is_(False),
            )
            .values(is_revoked=True, revoked_at=now)
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount  # type: ignore[return-value]

    async def revoke_all_for_client(self, client_id: str) -> int:
        """Revoke all active refresh tokens for a client."""
        now = datetime.now(UTC)
        stmt = (
            update(RefreshTokenModel)
            .where(
                RefreshTokenModel.client_id == client_id,
                RefreshTokenModel.is_revoked.is_(False),
            )
            .values(is_revoked=True, revoked_at=now)
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount  # type: ignore[return-value]

    async def revoke_all_for_user_and_client(self, user_id: uuid.UUID, client_id: str) -> int:
        """Revoke all active refresh tokens for a user-client combination."""
        now = datetime.now(UTC)
        stmt = (
            update(RefreshTokenModel)
            .where(
                RefreshTokenModel.user_id == str(user_id),
                RefreshTokenModel.client_id == client_id,
                RefreshTokenModel.is_revoked.is_(False),
            )
            .values(is_revoked=True, revoked_at=now)
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount  # type: ignore[return-value]

    async def list_active_for_user(
        self, user_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> list[RefreshToken]:
        """List active (non-revoked, non-expired) refresh tokens for a user."""
        now = datetime.now(UTC)
        stmt = (
            select(RefreshTokenModel)
            .where(
                RefreshTokenModel.user_id == str(user_id),
                RefreshTokenModel.is_revoked.is_(False),
            )
            .where((RefreshTokenModel.expires_at.is_(None)) | (RefreshTokenModel.expires_at > now))
            .offset(skip)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [refresh_token_model_to_entity(m) for m in result.scalars().all()]

    async def cleanup_expired(self) -> int:
        """Delete expired refresh tokens from the database."""
        now = datetime.now(UTC)
        stmt = delete(RefreshTokenModel).where(
            RefreshTokenModel.expires_at.isnot(None),
            RefreshTokenModel.expires_at < now,
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount  # type: ignore[return-value]
