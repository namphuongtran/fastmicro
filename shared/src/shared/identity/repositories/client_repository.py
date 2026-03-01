"""PostgreSQL ClientRepository implementation."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.identity.mappers.client_mapper import (
    client_entity_to_model,
    client_model_to_entity,
)
from shared.identity.models.client import ClientModel

if TYPE_CHECKING:
    from identity_service.domain.entities import Client


class ClientRepository:
    """PostgreSQL-backed implementation of ClientRepository interface."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, client_id: uuid.UUID) -> Client | None:
        """Get client by internal UUID."""
        stmt = select(ClientModel).where(ClientModel.id == str(client_id))
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return client_model_to_entity(model) if model else None

    async def get_by_client_id(self, client_id: str) -> Client | None:
        """Get client by OAuth2 public client_id string."""
        stmt = select(ClientModel).where(ClientModel.client_id == client_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return client_model_to_entity(model) if model else None

    async def create(self, client: Client) -> Client:
        """Persist a new OAuth2 client."""
        model = client_entity_to_model(client)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return client_model_to_entity(model)

    async def update(self, client: Client) -> Client:
        """Update an existing client by merging."""
        model = client_entity_to_model(client)
        merged = await self._session.merge(model)
        await self._session.flush()
        await self._session.refresh(merged)
        return client_model_to_entity(merged)

    async def delete(self, client_id: uuid.UUID) -> bool:
        """Soft-delete client (set is_active=False)."""
        stmt = select(ClientModel).where(ClientModel.id == str(client_id))
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            return False
        model.is_active = False
        await self._session.flush()
        return True

    async def exists_by_client_id(self, client_id: str) -> bool:
        """Check if client with given OAuth2 client_id exists."""
        stmt = (
            select(func.count()).select_from(ClientModel).where(ClientModel.client_id == client_id)
        )
        result = await self._session.execute(stmt)
        return (result.scalar() or 0) > 0

    async def list_active(self, skip: int = 0, limit: int = 100) -> list[Client]:
        """List all active clients."""
        stmt = select(ClientModel).where(ClientModel.is_active.is_(True)).offset(skip).limit(limit)
        result = await self._session.execute(stmt)
        return [client_model_to_entity(m) for m in result.scalars().all()]

    async def list_by_owner(
        self, owner_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> list[Client]:
        """List clients created by a specific user."""
        stmt = (
            select(ClientModel)
            .where(ClientModel.created_by == str(owner_id))
            .offset(skip)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [client_model_to_entity(m) for m in result.scalars().all()]

    async def count(self, include_inactive: bool = False) -> int:
        """Count total clients."""
        stmt = select(func.count()).select_from(ClientModel)
        if not include_inactive:
            stmt = stmt.where(ClientModel.is_active.is_(True))
        result = await self._session.execute(stmt)
        return result.scalar() or 0

    async def search(
        self,
        query: str,
        skip: int = 0,
        limit: int = 100,
        include_inactive: bool = False,
    ) -> list[Client]:
        """Search clients by name or client_id (partial match)."""
        pattern = f"%{query}%"
        stmt = select(ClientModel).where(
            or_(
                ClientModel.client_id.ilike(pattern),
                ClientModel.client_name.ilike(pattern),
            )
        )
        if not include_inactive:
            stmt = stmt.where(ClientModel.is_active.is_(True))
        stmt = stmt.offset(skip).limit(limit)
        result = await self._session.execute(stmt)
        return [client_model_to_entity(m) for m in result.scalars().all()]
