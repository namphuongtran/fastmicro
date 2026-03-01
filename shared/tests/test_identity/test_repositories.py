"""Tests for identity PostgreSQL repositories.

Uses in-memory SQLite with aiosqlite for fast, isolated testing.
Repository tests verify CRUD operations and query behavior.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from shared.identity.models.base import IdentityBase
from shared.identity.models.client import ClientModel, ClientScopeModel
from shared.identity.models.consent import ConsentModel, ConsentScopeModel
from shared.identity.models.token import RefreshTokenModel
from shared.identity.models.user import (
    PasswordResetTokenModel,
    UserModel,
    UserRoleModel,
)
from shared.sqlalchemy_async.database import AsyncDatabaseManager, DatabaseConfig


def _utc_now() -> datetime:
    return datetime.now(UTC)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def db_manager() -> AsyncDatabaseManager:
    config = DatabaseConfig(url="sqlite+aiosqlite:///:memory:")
    return AsyncDatabaseManager(config)


@pytest.fixture
async def setup_db(db_manager: AsyncDatabaseManager) -> AsyncDatabaseManager:
    await db_manager.create_all(IdentityBase)
    return db_manager


# ============================================================================
# User Repository Tests (direct model operations, mirrors repo behavior)
# ============================================================================


class TestUserPersistence:
    """Test user CRUD at the model/session level."""

    @pytest.mark.asyncio
    async def test_create_and_find_user(self, setup_db: AsyncDatabaseManager) -> None:
        """Should create a user and find it by email."""
        user_id = str(uuid.uuid4())

        async with setup_db.get_session() as session:
            user = UserModel(
                id=user_id,
                email="alice@example.com",
                username="alice",
                is_active=True,
            )
            session.add(user)
            await session.flush()

        async with setup_db.get_session() as session:
            result = await session.execute(
                select(UserModel).where(UserModel.email == "alice@example.com")
            )
            loaded = result.scalar_one_or_none()
            assert loaded is not None
            assert loaded.username == "alice"
            assert loaded.is_active is True

    @pytest.mark.asyncio
    async def test_case_insensitive_email_lookup(self, setup_db: AsyncDatabaseManager) -> None:
        """Should find user regardless of email case."""
        from sqlalchemy import func

        user_id = str(uuid.uuid4())

        async with setup_db.get_session() as session:
            user = UserModel(
                id=user_id,
                email="Alice@Example.COM",
                is_active=True,
            )
            session.add(user)
            await session.flush()

        async with setup_db.get_session() as session:
            result = await session.execute(
                select(UserModel).where(func.lower(UserModel.email) == "alice@example.com")
            )
            loaded = result.scalar_one_or_none()
            assert loaded is not None
            assert loaded.id == user_id

    @pytest.mark.asyncio
    async def test_update_user(self, setup_db: AsyncDatabaseManager) -> None:
        """Should update user fields."""
        user_id = str(uuid.uuid4())

        async with setup_db.get_session() as session:
            user = UserModel(
                id=user_id,
                email="bob@example.com",
                username="bob",
                is_active=True,
            )
            session.add(user)
            await session.flush()

        async with setup_db.get_session() as session:
            result = await session.execute(select(UserModel).where(UserModel.id == user_id))
            user = result.scalar_one()
            user.username = "bobby"
            user.is_active = False
            await session.flush()

        async with setup_db.get_session() as session:
            result = await session.execute(select(UserModel).where(UserModel.id == user_id))
            user = result.scalar_one()
            assert user.username == "bobby"
            assert user.is_active is False

    @pytest.mark.asyncio
    async def test_soft_delete_user(self, setup_db: AsyncDatabaseManager) -> None:
        """Should soft-delete by setting is_active=False."""
        user_id = str(uuid.uuid4())

        async with setup_db.get_session() as session:
            user = UserModel(
                id=user_id,
                email="del@example.com",
                is_active=True,
            )
            session.add(user)
            await session.flush()

        async with setup_db.get_session() as session:
            result = await session.execute(select(UserModel).where(UserModel.id == user_id))
            user = result.scalar_one()
            user.is_active = False
            await session.flush()

        async with setup_db.get_session() as session:
            # User still exists but is inactive
            result = await session.execute(
                select(UserModel).where(UserModel.id == user_id, UserModel.is_active.is_(True))
            )
            assert result.scalar_one_or_none() is None

            result = await session.execute(select(UserModel).where(UserModel.id == user_id))
            assert result.scalar_one_or_none() is not None

    @pytest.mark.asyncio
    async def test_user_with_roles(self, setup_db: AsyncDatabaseManager) -> None:
        """Should query users by role."""
        user_id = str(uuid.uuid4())

        async with setup_db.get_session() as session:
            user = UserModel(id=user_id, email="admin@example.com", is_active=True)
            session.add(user)
            await session.flush()

            role = UserRoleModel(
                id=str(uuid.uuid4()),
                user_id=user_id,
                role_name="admin",
            )
            session.add(role)
            await session.flush()

        async with setup_db.get_session() as session:
            result = await session.execute(
                select(UserModel)
                .join(UserRoleModel, UserModel.id == UserRoleModel.user_id)
                .where(UserRoleModel.role_name == "admin")
            )
            users = result.scalars().all()
            assert len(users) == 1
            assert users[0].email == "admin@example.com"

    @pytest.mark.asyncio
    async def test_search_users(self, setup_db: AsyncDatabaseManager) -> None:
        """Should search users by email or username pattern."""
        async with setup_db.get_session() as session:
            for name in ["alice", "bob", "charlie"]:
                user = UserModel(
                    id=str(uuid.uuid4()),
                    email=f"{name}@example.com",
                    username=name,
                    is_active=True,
                )
                session.add(user)
            await session.flush()

        async with setup_db.get_session() as session:
            result = await session.execute(select(UserModel).where(UserModel.email.ilike("%ali%")))
            matches = result.scalars().all()
            assert len(matches) == 1
            assert matches[0].username == "alice"

    @pytest.mark.asyncio
    async def test_count_users(self, setup_db: AsyncDatabaseManager) -> None:
        """Should count users with optional filter."""
        from sqlalchemy import func

        async with setup_db.get_session() as session:
            for i in range(5):
                user = UserModel(
                    id=str(uuid.uuid4()),
                    email=f"user{i}@example.com",
                    is_active=i < 3,  # 3 active, 2 inactive
                )
                session.add(user)
            await session.flush()

        async with setup_db.get_session() as session:
            # Count all
            result = await session.execute(select(func.count()).select_from(UserModel))
            total = result.scalar()
            assert total == 5

            # Count active only
            result = await session.execute(
                select(func.count()).select_from(UserModel).where(UserModel.is_active.is_(True))
            )
            active = result.scalar()
            assert active == 3


# ============================================================================
# Client Repository Tests
# ============================================================================


class TestClientPersistence:
    """Test client CRUD at the model/session level."""

    @pytest.mark.asyncio
    async def test_create_and_find_client(self, setup_db: AsyncDatabaseManager) -> None:
        """Should create a client and find by client_id."""
        cid = str(uuid.uuid4())

        async with setup_db.get_session() as session:
            client = ClientModel(
                id=cid,
                client_id="my-web-app",
                client_name="My Web App",
                client_type="confidential",
                is_active=True,
                grant_types="authorization_code,refresh_token",
                response_types="code",
            )
            session.add(client)
            await session.flush()

        async with setup_db.get_session() as session:
            result = await session.execute(
                select(ClientModel).where(ClientModel.client_id == "my-web-app")
            )
            loaded = result.scalar_one()
            assert loaded.client_name == "My Web App"
            assert "authorization_code" in loaded.grant_types

    @pytest.mark.asyncio
    async def test_client_with_scopes(self, setup_db: AsyncDatabaseManager) -> None:
        """Should persist and query client scopes."""
        cid = str(uuid.uuid4())

        async with setup_db.get_session() as session:
            client = ClientModel(
                id=cid,
                client_id="scoped-app",
                client_name="Scoped App",
                client_type="public",
                is_active=True,
            )
            session.add(client)
            await session.flush()

            for scope_name in ["openid", "profile", "email"]:
                scope = ClientScopeModel(
                    id=str(uuid.uuid4()),
                    client_id=cid,
                    scope=scope_name,
                    is_default=scope_name == "openid",
                )
                session.add(scope)
            await session.flush()

        async with setup_db.get_session() as session:
            result = await session.execute(
                select(ClientScopeModel).where(ClientScopeModel.client_id == cid)
            )
            scopes = result.scalars().all()
            assert len(scopes) == 3
            scope_names = {s.scope for s in scopes}
            assert scope_names == {"openid", "profile", "email"}

    @pytest.mark.asyncio
    async def test_list_active_clients(self, setup_db: AsyncDatabaseManager) -> None:
        """Should list only active clients."""
        async with setup_db.get_session() as session:
            for i, active in enumerate([True, True, False]):
                client = ClientModel(
                    id=str(uuid.uuid4()),
                    client_id=f"app-{i}",
                    client_name=f"App {i}",
                    client_type="confidential",
                    is_active=active,
                )
                session.add(client)
            await session.flush()

        async with setup_db.get_session() as session:
            result = await session.execute(
                select(ClientModel).where(ClientModel.is_active.is_(True))
            )
            active_clients = result.scalars().all()
            assert len(active_clients) == 2

    @pytest.mark.asyncio
    async def test_search_clients(self, setup_db: AsyncDatabaseManager) -> None:
        """Should search clients by name pattern."""
        async with setup_db.get_session() as session:
            for name in ["Web Portal", "Mobile App", "API Gateway"]:
                client = ClientModel(
                    id=str(uuid.uuid4()),
                    client_id=name.lower().replace(" ", "-"),
                    client_name=name,
                    client_type="confidential",
                    is_active=True,
                )
                session.add(client)
            await session.flush()

        async with setup_db.get_session() as session:
            result = await session.execute(
                select(ClientModel).where(ClientModel.client_name.ilike("%mobile%"))
            )
            matches = result.scalars().all()
            assert len(matches) == 1
            assert matches[0].client_name == "Mobile App"


# ============================================================================
# RefreshToken Persistence Tests
# ============================================================================


class TestRefreshTokenPersistence:
    """Test refresh token CRUD at the model/session level."""

    @pytest.mark.asyncio
    async def test_create_and_find_token(self, setup_db: AsyncDatabaseManager) -> None:
        """Should create and find a refresh token."""
        token_id = str(uuid.uuid4())
        token_value = "rt_" + str(uuid.uuid4())

        async with setup_db.get_session() as session:
            token = RefreshTokenModel(
                id=token_id,
                token=token_value,
                client_id="my-app",
                user_id=str(uuid.uuid4()),
                scope="openid profile",
                is_revoked=False,
            )
            session.add(token)
            await session.flush()

        async with setup_db.get_session() as session:
            result = await session.execute(
                select(RefreshTokenModel).where(RefreshTokenModel.token == token_value)
            )
            loaded = result.scalar_one()
            assert loaded.scope == "openid profile"
            assert loaded.is_revoked is False

    @pytest.mark.asyncio
    async def test_revoke_token(self, setup_db: AsyncDatabaseManager) -> None:
        """Should revoke a refresh token."""
        token_id = str(uuid.uuid4())
        token_value = "rt_revoke_" + str(uuid.uuid4())

        async with setup_db.get_session() as session:
            token = RefreshTokenModel(
                id=token_id,
                token=token_value,
                client_id="my-app",
                user_id=str(uuid.uuid4()),
                scope="openid",
                is_revoked=False,
            )
            session.add(token)
            await session.flush()

        async with setup_db.get_session() as session:
            result = await session.execute(
                select(RefreshTokenModel).where(RefreshTokenModel.id == token_id)
            )
            token = result.scalar_one()
            token.is_revoked = True
            token.revoked_at = _utc_now()
            await session.flush()

        async with setup_db.get_session() as session:
            result = await session.execute(
                select(RefreshTokenModel).where(RefreshTokenModel.id == token_id)
            )
            token = result.scalar_one()
            assert token.is_revoked is True
            assert token.revoked_at is not None

    @pytest.mark.asyncio
    async def test_list_active_tokens_for_user(self, setup_db: AsyncDatabaseManager) -> None:
        """Should list only active (non-revoked, non-expired) tokens for a user."""
        user_id = str(uuid.uuid4())
        now = _utc_now()

        async with setup_db.get_session() as session:
            # Active token
            t1 = RefreshTokenModel(
                id=str(uuid.uuid4()),
                token="active_token",
                client_id="app",
                user_id=user_id,
                scope="openid",
                is_revoked=False,
                expires_at=now + timedelta(days=30),
            )
            # Revoked token
            t2 = RefreshTokenModel(
                id=str(uuid.uuid4()),
                token="revoked_token",
                client_id="app",
                user_id=user_id,
                scope="openid",
                is_revoked=True,
                revoked_at=now,
                expires_at=now + timedelta(days=30),
            )
            # Expired token
            t3 = RefreshTokenModel(
                id=str(uuid.uuid4()),
                token="expired_token",
                client_id="app",
                user_id=user_id,
                scope="openid",
                is_revoked=False,
                expires_at=now - timedelta(days=1),
            )
            session.add_all([t1, t2, t3])
            await session.flush()

        async with setup_db.get_session() as session:
            result = await session.execute(
                select(RefreshTokenModel).where(
                    RefreshTokenModel.user_id == user_id,
                    RefreshTokenModel.is_revoked.is_(False),
                    RefreshTokenModel.expires_at > now,
                )
            )
            active = result.scalars().all()
            assert len(active) == 1
            assert active[0].token == "active_token"

    @pytest.mark.asyncio
    async def test_revoke_all_for_user_and_client(self, setup_db: AsyncDatabaseManager) -> None:
        """Should revoke all tokens for a specific user+client combination."""
        from sqlalchemy import update

        user_id = str(uuid.uuid4())
        now = _utc_now()

        async with setup_db.get_session() as session:
            for i in range(3):
                token = RefreshTokenModel(
                    id=str(uuid.uuid4()),
                    token=f"bulk_revoke_{i}",
                    client_id="target-app",
                    user_id=user_id,
                    scope="openid",
                    is_revoked=False,
                )
                session.add(token)
            await session.flush()

        async with setup_db.get_session() as session:
            await session.execute(
                update(RefreshTokenModel)
                .where(
                    RefreshTokenModel.user_id == user_id,
                    RefreshTokenModel.client_id == "target-app",
                    RefreshTokenModel.is_revoked.is_(False),
                )
                .values(is_revoked=True, revoked_at=now)
            )
            await session.flush()

        async with setup_db.get_session() as session:
            result = await session.execute(
                select(RefreshTokenModel).where(
                    RefreshTokenModel.user_id == user_id,
                    RefreshTokenModel.is_revoked.is_(True),
                )
            )
            revoked = result.scalars().all()
            assert len(revoked) == 3


# ============================================================================
# Consent Persistence Tests
# ============================================================================


class TestConsentPersistence:
    """Test consent CRUD at the model/session level."""

    @pytest.mark.asyncio
    async def test_create_consent_with_scopes(self, setup_db: AsyncDatabaseManager) -> None:
        """Should create consent with scopes."""
        consent_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())

        async with setup_db.get_session() as session:
            consent = ConsentModel(
                id=consent_id,
                user_id=user_id,
                client_id="my-app",
                remember=True,
            )
            session.add(consent)
            await session.flush()

            for scope_name in ["openid", "profile"]:
                scope = ConsentScopeModel(
                    id=str(uuid.uuid4()),
                    consent_id=consent_id,
                    scope=scope_name,
                )
                session.add(scope)
            await session.flush()

        async with setup_db.get_session() as session:
            result = await session.execute(
                select(ConsentModel).where(
                    ConsentModel.user_id == user_id,
                    ConsentModel.client_id == "my-app",
                )
            )
            consent = result.scalar_one()
            assert consent.remember is True

            scopes = (
                (
                    await session.execute(
                        select(ConsentScopeModel).where(ConsentScopeModel.consent_id == consent_id)
                    )
                )
                .scalars()
                .all()
            )
            assert len(scopes) == 2

    @pytest.mark.asyncio
    async def test_delete_consent(self, setup_db: AsyncDatabaseManager) -> None:
        """Should delete a consent record."""
        consent_id = str(uuid.uuid4())

        async with setup_db.get_session() as session:
            consent = ConsentModel(
                id=consent_id,
                user_id=str(uuid.uuid4()),
                client_id="revoke-app",
                remember=False,
            )
            session.add(consent)
            await session.flush()

        async with setup_db.get_session() as session:
            result = await session.execute(
                select(ConsentModel).where(ConsentModel.id == consent_id)
            )
            consent = result.scalar_one()
            await session.delete(consent)
            await session.flush()

        async with setup_db.get_session() as session:
            result = await session.execute(
                select(ConsentModel).where(ConsentModel.id == consent_id)
            )
            assert result.scalar_one_or_none() is None


# ============================================================================
# Password Reset Token Persistence Tests
# ============================================================================


class TestPasswordResetTokenPersistence:
    """Test password reset token CRUD at the model/session level."""

    @pytest.mark.asyncio
    async def test_create_and_find_reset_token(self, setup_db: AsyncDatabaseManager) -> None:
        """Should create and find by token value."""
        user_id = str(uuid.uuid4())

        async with setup_db.get_session() as session:
            user = UserModel(id=user_id, email="reset@example.com", is_active=True)
            session.add(user)
            await session.flush()

            token = PasswordResetTokenModel(
                id=str(uuid.uuid4()),
                user_id=user_id,
                token="reset_abc123",
                email="reset@example.com",
                is_used=False,
                expires_at=_utc_now() + timedelta(hours=1),
            )
            session.add(token)
            await session.flush()

        async with setup_db.get_session() as session:
            result = await session.execute(
                select(PasswordResetTokenModel).where(
                    PasswordResetTokenModel.token == "reset_abc123"
                )
            )
            loaded = result.scalar_one()
            assert loaded.user_id == user_id
            assert loaded.is_used is False

    @pytest.mark.asyncio
    async def test_mark_token_as_used(self, setup_db: AsyncDatabaseManager) -> None:
        """Should mark a reset token as used."""
        user_id = str(uuid.uuid4())
        token_id = str(uuid.uuid4())

        async with setup_db.get_session() as session:
            user = UserModel(id=user_id, email="mark@example.com", is_active=True)
            session.add(user)
            await session.flush()

            token = PasswordResetTokenModel(
                id=token_id,
                user_id=user_id,
                token="mark_used_token",
                email="mark@example.com",
                is_used=False,
                expires_at=_utc_now() + timedelta(hours=1),
            )
            session.add(token)
            await session.flush()

        async with setup_db.get_session() as session:
            result = await session.execute(
                select(PasswordResetTokenModel).where(PasswordResetTokenModel.id == token_id)
            )
            token = result.scalar_one()
            token.is_used = True
            await session.flush()

        async with setup_db.get_session() as session:
            result = await session.execute(
                select(PasswordResetTokenModel).where(PasswordResetTokenModel.id == token_id)
            )
            token = result.scalar_one()
            assert token.is_used is True

    @pytest.mark.asyncio
    async def test_find_valid_token_for_user(self, setup_db: AsyncDatabaseManager) -> None:
        """Should find only valid (unused, non-expired) tokens for a user."""
        user_id = str(uuid.uuid4())
        now = _utc_now()

        async with setup_db.get_session() as session:
            user = UserModel(id=user_id, email="valid@example.com", is_active=True)
            session.add(user)
            await session.flush()

            # Valid token
            t1 = PasswordResetTokenModel(
                id=str(uuid.uuid4()),
                user_id=user_id,
                token="valid_token",
                email="valid@example.com",
                is_used=False,
                expires_at=now + timedelta(hours=1),
            )
            # Used token
            t2 = PasswordResetTokenModel(
                id=str(uuid.uuid4()),
                user_id=user_id,
                token="used_token",
                email="valid@example.com",
                is_used=True,
                expires_at=now + timedelta(hours=1),
            )
            # Expired token
            t3 = PasswordResetTokenModel(
                id=str(uuid.uuid4()),
                user_id=user_id,
                token="expired_token",
                email="valid@example.com",
                is_used=False,
                expires_at=now - timedelta(hours=1),
            )
            session.add_all([t1, t2, t3])
            await session.flush()

        async with setup_db.get_session() as session:
            result = await session.execute(
                select(PasswordResetTokenModel).where(
                    PasswordResetTokenModel.user_id == user_id,
                    PasswordResetTokenModel.is_used.is_(False),
                    PasswordResetTokenModel.expires_at > now,
                )
            )
            valid_tokens = result.scalars().all()
            assert len(valid_tokens) == 1
            assert valid_tokens[0].token == "valid_token"
