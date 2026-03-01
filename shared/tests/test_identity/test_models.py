"""Tests for identity ORM models - verify table creation and constraints.

Uses in-memory SQLite with aiosqlite for fast, isolated testing.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from shared.identity.models.base import IdentityBase
from shared.identity.models.client import (
    ClientModel,
    ClientRedirectUriModel,
    ClientScopeModel,
    ClientSecretModel,
)
from shared.identity.models.consent import ConsentModel, ConsentScopeModel
from shared.identity.models.token import RefreshTokenModel
from shared.identity.models.user import (
    PasswordResetTokenModel,
    UserClaimModel,
    UserCredentialModel,
    UserModel,
    UserProfileModel,
    UserRoleModel,
)
from shared.sqlalchemy_async.database import AsyncDatabaseManager, DatabaseConfig


class TestModelCreation:
    """Test that ORM models can be instantiated and persisted."""

    @pytest.fixture
    def db_manager(self) -> AsyncDatabaseManager:
        config = DatabaseConfig(url="sqlite+aiosqlite:///:memory:")
        return AsyncDatabaseManager(config)

    @pytest.fixture
    async def setup_db(self, db_manager: AsyncDatabaseManager) -> AsyncDatabaseManager:
        await db_manager.create_all(IdentityBase)
        return db_manager

    @pytest.mark.asyncio
    async def test_create_tables(self, setup_db: AsyncDatabaseManager) -> None:
        """All identity tables should be created without errors."""
        # If we get here, create_all succeeded
        assert setup_db is not None

    @pytest.mark.asyncio
    async def test_persist_user_model(self, setup_db: AsyncDatabaseManager) -> None:
        """Should persist a UserModel with credential and profile."""
        user_id = str(uuid.uuid4())

        async with setup_db.get_session() as session:
            user = UserModel(
                id=user_id,
                email="test@example.com",
                username="testuser",
                is_active=True,
            )
            session.add(user)
            await session.flush()

            cred = UserCredentialModel(
                id=str(uuid.uuid4()),
                user_id=user_id,
                password_hash="hashed_pw",
            )
            session.add(cred)

            profile = UserProfileModel(
                id=str(uuid.uuid4()),
                user_id=user_id,
                given_name="Test",
                family_name="User",
            )
            session.add(profile)
            await session.flush()

        # Verify persistence
        async with setup_db.get_session() as session:
            from sqlalchemy import select

            result = await session.execute(select(UserModel).where(UserModel.id == user_id))
            loaded = result.scalar_one()
            assert loaded.email == "test@example.com"
            assert loaded.username == "testuser"

    @pytest.mark.asyncio
    async def test_persist_client_model(self, setup_db: AsyncDatabaseManager) -> None:
        """Should persist a ClientModel with scopes and redirect URIs."""
        client_id = str(uuid.uuid4())

        async with setup_db.get_session() as session:
            client = ClientModel(
                id=client_id,
                client_id="my-app",
                client_name="My Application",
                client_type="confidential",
                is_active=True,
            )
            session.add(client)
            await session.flush()

            scope = ClientScopeModel(
                id=str(uuid.uuid4()),
                client_id=client_id,
                scope="openid",
                is_default=True,
            )
            session.add(scope)

            redirect = ClientRedirectUriModel(
                id=str(uuid.uuid4()),
                client_id=client_id,
                uri="http://localhost:3000/callback",
            )
            session.add(redirect)

            secret = ClientSecretModel(
                id=str(uuid.uuid4()),
                client_id=client_id,
                secret_hash="hashed_secret",
            )
            session.add(secret)
            await session.flush()

        async with setup_db.get_session() as session:
            from sqlalchemy import select

            result = await session.execute(
                select(ClientModel).where(ClientModel.client_id == "my-app")
            )
            loaded = result.scalar_one()
            assert loaded.client_name == "My Application"

    @pytest.mark.asyncio
    async def test_persist_refresh_token(self, setup_db: AsyncDatabaseManager) -> None:
        """Should persist a RefreshTokenModel."""
        token_id = str(uuid.uuid4())

        async with setup_db.get_session() as session:
            token = RefreshTokenModel(
                id=token_id,
                token="refresh_token_value_123",
                client_id="my-app",
                user_id=str(uuid.uuid4()),
                scope="openid profile",
                is_revoked=False,
            )
            session.add(token)
            await session.flush()

        async with setup_db.get_session() as session:
            from sqlalchemy import select

            result = await session.execute(
                select(RefreshTokenModel).where(RefreshTokenModel.id == token_id)
            )
            loaded = result.scalar_one()
            assert loaded.token == "refresh_token_value_123"
            assert loaded.scope == "openid profile"

    @pytest.mark.asyncio
    async def test_persist_consent(self, setup_db: AsyncDatabaseManager) -> None:
        """Should persist a ConsentModel with scopes."""
        consent_id = str(uuid.uuid4())

        async with setup_db.get_session() as session:
            consent = ConsentModel(
                id=consent_id,
                user_id=str(uuid.uuid4()),
                client_id="my-app",
                remember=True,
            )
            session.add(consent)
            await session.flush()

            scope = ConsentScopeModel(
                id=str(uuid.uuid4()),
                consent_id=consent_id,
                scope="openid",
            )
            session.add(scope)
            await session.flush()

        async with setup_db.get_session() as session:
            from sqlalchemy import select

            result = await session.execute(
                select(ConsentModel).where(ConsentModel.id == consent_id)
            )
            loaded = result.scalar_one()
            assert loaded.client_id == "my-app"
            assert loaded.remember is True

    @pytest.mark.asyncio
    async def test_persist_password_reset_token(self, setup_db: AsyncDatabaseManager) -> None:
        """Should persist a PasswordResetTokenModel."""
        user_id = str(uuid.uuid4())

        async with setup_db.get_session() as session:
            # Create user first (FK constraint)
            user = UserModel(
                id=user_id,
                email="reset@example.com",
                is_active=True,
            )
            session.add(user)
            await session.flush()

            reset = PasswordResetTokenModel(
                id=str(uuid.uuid4()),
                user_id=user_id,
                token="reset_token_abc123",
                email="reset@example.com",
                expires_at=datetime.now(UTC) + timedelta(hours=1),
                is_used=False,
            )
            session.add(reset)
            await session.flush()

        async with setup_db.get_session() as session:
            from sqlalchemy import select

            result = await session.execute(
                select(PasswordResetTokenModel).where(
                    PasswordResetTokenModel.token == "reset_token_abc123"
                )
            )
            loaded = result.scalar_one()
            assert loaded.user_id == user_id
            assert loaded.is_used is False

    @pytest.mark.asyncio
    async def test_user_roles_and_claims(self, setup_db: AsyncDatabaseManager) -> None:
        """Should persist user roles and claims."""
        user_id = str(uuid.uuid4())

        async with setup_db.get_session() as session:
            user = UserModel(id=user_id, email="roles@example.com", is_active=True)
            session.add(user)
            await session.flush()

            role = UserRoleModel(
                id=str(uuid.uuid4()),
                user_id=user_id,
                role_name="admin",
            )
            session.add(role)

            claim = UserClaimModel(
                id=str(uuid.uuid4()),
                user_id=user_id,
                claim_type="department",
                claim_value="engineering",
            )
            session.add(claim)
            await session.flush()

        async with setup_db.get_session() as session:
            from sqlalchemy import select

            roles = (
                (
                    await session.execute(
                        select(UserRoleModel).where(UserRoleModel.user_id == user_id)
                    )
                )
                .scalars()
                .all()
            )
            assert len(roles) == 1
            assert roles[0].role_name == "admin"

            claims = (
                (
                    await session.execute(
                        select(UserClaimModel).where(UserClaimModel.user_id == user_id)
                    )
                )
                .scalars()
                .all()
            )
            assert len(claims) == 1
            assert claims[0].claim_type == "department"
