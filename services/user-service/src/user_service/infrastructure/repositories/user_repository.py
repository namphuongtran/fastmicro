"""PostgreSQL repository implementation for User aggregate."""

from __future__ import annotations

import structlog
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from user_service.domain.entities.user import User
from user_service.domain.repositories import UserRepository
from user_service.infrastructure.database.models import UserModel

logger = structlog.get_logger()


class PostgresUserRepository(UserRepository):
    """PostgreSQL implementation of the user repository.

    Maps between the User domain aggregate and UserModel persistence model.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ---- domain ↔ model mapping ----

    @staticmethod
    def _to_domain(model: UserModel) -> User:
        """Convert database model to domain aggregate."""
        user = User.__new__(User)
        # Manually set slots since we bypass __init__
        object.__setattr__(user, "_id", model.id)
        object.__setattr__(user, "_email", model.email)
        object.__setattr__(user, "_display_name", model.display_name)
        object.__setattr__(user, "_first_name", model.first_name)
        object.__setattr__(user, "_last_name", model.last_name)
        object.__setattr__(user, "_tenant_id", model.tenant_id)
        object.__setattr__(user, "_is_active", model.is_active)
        object.__setattr__(user, "_preferences", dict(model.preferences or {}))
        object.__setattr__(user, "_created_at", model.created_at)
        object.__setattr__(user, "_updated_at", model.updated_at)
        object.__setattr__(user, "_domain_events", [])
        return user

    @staticmethod
    def _to_model(user: User) -> UserModel:
        """Convert domain aggregate to database model."""
        return UserModel(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            first_name=user.first_name,
            last_name=user.last_name,
            tenant_id=user.tenant_id,
            is_active=user.is_active,
            preferences=user.preferences,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

    # ---- queries ----

    async def get_by_id(self, user_id: str) -> User | None:
        """Find a user by ID."""
        stmt = select(UserModel).where(UserModel.id == user_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def get_by_email(self, email: str) -> User | None:
        """Find a user by email address."""
        stmt = select(UserModel).where(UserModel.email == email)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def list_by_tenant(
        self,
        tenant_id: str,
        *,
        offset: int = 0,
        limit: int = 20,
    ) -> list[User]:
        """List users belonging to a tenant."""
        stmt = (
            select(UserModel)
            .where(UserModel.tenant_id == tenant_id)
            .order_by(UserModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [self._to_domain(m) for m in result.scalars().all()]

    async def exists_by_email(self, email: str) -> bool:
        """Check if a user with the given email exists."""
        stmt = select(UserModel.id).where(UserModel.email == email).limit(1)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    # ---- commands ----

    async def add(self, user: User) -> None:
        """Persist a new user."""
        model = self._to_model(user)
        self._session.add(model)
        await self._session.flush()

    async def update(self, user: User) -> None:
        """Update an existing user."""
        stmt = select(UserModel).where(UserModel.id == user.id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return

        model.email = user.email
        model.display_name = user.display_name
        model.first_name = user.first_name
        model.last_name = user.last_name
        model.tenant_id = user.tenant_id
        model.is_active = user.is_active
        model.preferences = user.preferences
        model.updated_at = user.updated_at
        await self._session.flush()

    async def delete(self, user_id: str) -> None:
        """Delete a user by ID."""
        stmt = delete(UserModel).where(UserModel.id == user_id)
        await self._session.execute(stmt)
        await self._session.flush()
