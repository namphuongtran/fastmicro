"""PostgreSQL ConsentRepository implementation.

Implements the ConsentRepository interface from identity-service domain.
Note: SessionRepository is Redis-only and remains in-memory for now.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.identity.mappers.consent_mapper import (
    consent_entity_to_model,
    consent_model_to_entity,
)
from shared.identity.models.consent import ConsentModel

if TYPE_CHECKING:
    from identity_service.domain.entities import Consent


class ConsentRepository:
    """PostgreSQL-backed implementation of ConsentRepository interface."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, consent_id: uuid.UUID) -> Consent | None:
        """Get consent by UUID."""
        stmt = select(ConsentModel).where(ConsentModel.id == str(consent_id))
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return consent_model_to_entity(model) if model else None

    async def get_by_user_and_client(self, user_id: uuid.UUID, client_id: str) -> Consent | None:
        """Get consent for a specific user-client pair."""
        stmt = select(ConsentModel).where(
            ConsentModel.user_id == str(user_id),
            ConsentModel.client_id == client_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return consent_model_to_entity(model) if model else None

    async def save(self, consent: Consent) -> Consent:
        """Save or update a consent (upsert via merge)."""
        model = consent_entity_to_model(consent)
        merged = await self._session.merge(model)
        await self._session.flush()
        await self._session.refresh(merged)
        return consent_model_to_entity(merged)

    async def delete(self, consent_id: uuid.UUID) -> bool:
        """Delete a consent by ID."""
        stmt = select(ConsentModel).where(ConsentModel.id == str(consent_id))
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            return False
        await self._session.delete(model)
        await self._session.flush()
        return True

    async def delete_for_user(self, user_id: uuid.UUID) -> int:
        """Delete all consents for a user."""
        stmt = delete(ConsentModel).where(ConsentModel.user_id == str(user_id))
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount  # type: ignore[return-value]

    async def delete_for_client(self, client_id: str) -> int:
        """Delete all consents for a client."""
        stmt = delete(ConsentModel).where(ConsentModel.client_id == client_id)
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount  # type: ignore[return-value]

    async def list_by_user(
        self, user_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> list[Consent]:
        """List all consents for a user."""
        stmt = (
            select(ConsentModel)
            .where(ConsentModel.user_id == str(user_id))
            .offset(skip)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [consent_model_to_entity(m) for m in result.scalars().all()]
