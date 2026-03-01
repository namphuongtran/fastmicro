"""PostgreSQL UserRepository implementation.

Implements the UserRepository interface from identity-service domain
using SQLAlchemy async and shared ORM models.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.identity.mappers.user_mapper import user_entity_to_model, user_model_to_entity
from shared.identity.models.user import UserModel

if TYPE_CHECKING:
    from identity_service.domain.entities import User


class UserRepository:
    """PostgreSQL-backed implementation of UserRepository interface.

    Uses SQLAlchemy async session for all database operations.
    Converts between domain entities and ORM models via mappers.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        """Get user by UUID."""
        stmt = select(UserModel).where(UserModel.id == str(user_id))
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return user_model_to_entity(model) if model else None

    async def get_by_email(self, email: str) -> User | None:
        """Get user by email (case-insensitive)."""
        stmt = select(UserModel).where(func.lower(UserModel.email) == email.lower())
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return user_model_to_entity(model) if model else None

    async def get_by_username(self, username: str) -> User | None:
        """Get user by username (case-insensitive)."""
        stmt = select(UserModel).where(func.lower(UserModel.username) == username.lower())
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return user_model_to_entity(model) if model else None

    async def get_by_external_id(self, external_id: str, provider: str) -> User | None:
        """Get user by external provider ID."""
        stmt = select(UserModel).where(
            UserModel.external_id == external_id,
            UserModel.external_provider == provider,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return user_model_to_entity(model) if model else None

    async def create(self, user: User) -> User:
        """Persist a new user."""
        model = user_entity_to_model(user)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return user_model_to_entity(model)

    async def update(self, user: User) -> User:
        """Update an existing user by merging the entity."""
        model = user_entity_to_model(user)
        merged = await self._session.merge(model)
        await self._session.flush()
        await self._session.refresh(merged)
        return user_model_to_entity(merged)

    async def delete(self, user_id: uuid.UUID) -> bool:
        """Soft-delete user (set is_active=False)."""
        stmt = select(UserModel).where(UserModel.id == str(user_id))
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            return False
        model.is_active = False
        await self._session.flush()
        return True

    async def exists_by_email(self, email: str) -> bool:
        """Check if user with email exists."""
        stmt = (
            select(func.count())
            .select_from(UserModel)
            .where(func.lower(UserModel.email) == email.lower())
        )
        result = await self._session.execute(stmt)
        return (result.scalar() or 0) > 0

    async def exists_by_username(self, username: str) -> bool:
        """Check if user with username exists."""
        stmt = (
            select(func.count())
            .select_from(UserModel)
            .where(func.lower(UserModel.username) == username.lower())
        )
        result = await self._session.execute(stmt)
        return (result.scalar() or 0) > 0

    async def find_by_role(self, role_name: str, skip: int = 0, limit: int = 100) -> list[User]:
        """Find users with a specific role."""
        from shared.identity.models.user import UserRoleModel

        stmt = (
            select(UserModel)
            .join(UserRoleModel)
            .where(UserRoleModel.role_name == role_name)
            .offset(skip)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [user_model_to_entity(m) for m in result.scalars().all()]

    async def count(self, include_inactive: bool = False) -> int:
        """Count total users."""
        stmt = select(func.count()).select_from(UserModel)
        if not include_inactive:
            stmt = stmt.where(UserModel.is_active.is_(True))
        result = await self._session.execute(stmt)
        return result.scalar() or 0

    async def search(
        self,
        query: str,
        skip: int = 0,
        limit: int = 100,
        include_inactive: bool = False,
    ) -> list[User]:
        """Search users by email or username (partial match)."""
        pattern = f"%{query}%"
        stmt = select(UserModel).where(
            or_(
                UserModel.email.ilike(pattern),
                UserModel.username.ilike(pattern),
            )
        )
        if not include_inactive:
            stmt = stmt.where(UserModel.is_active.is_(True))
        stmt = stmt.offset(skip).limit(limit)
        result = await self._session.execute(stmt)
        return [user_model_to_entity(m) for m in result.scalars().all()]
