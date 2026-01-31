"""Tests for shared.sqlalchemy.database module.

This module tests async database management.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import Column, Integer, String, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

from shared.sqlalchemy_async.database import (
    AsyncDatabaseManager,
    get_async_session,
    DatabaseConfig,
)


class Base(DeclarativeBase):
    """Test base class."""
    pass


class SampleModel(Base):
    """Sample model for database tests."""
    __tablename__ = "sample_model"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100))


class TestDatabaseConfig:
    """Tests for DatabaseConfig dataclass."""

    def test_create_config(self) -> None:
        """Should create database config."""
        config = DatabaseConfig(
            url="sqlite+aiosqlite:///test.db",
        )
        
        assert config.url == "sqlite+aiosqlite:///test.db"

    def test_config_with_pool_settings(self) -> None:
        """Should support pool configuration."""
        config = DatabaseConfig(
            url="postgresql+asyncpg://localhost/test",
            pool_size=10,
            max_overflow=20,
            pool_timeout=30,
            pool_recycle=3600,
        )
        
        assert config.pool_size == 10
        assert config.max_overflow == 20
        assert config.pool_timeout == 30
        assert config.pool_recycle == 3600

    def test_config_defaults(self) -> None:
        """Should have sensible defaults."""
        config = DatabaseConfig(url="sqlite+aiosqlite:///:memory:")
        
        assert config.pool_size == 5
        assert config.max_overflow == 10
        assert config.echo is False


class TestAsyncDatabaseManager:
    """Tests for AsyncDatabaseManager class."""

    @pytest.fixture
    def db_config(self) -> DatabaseConfig:
        """Create test database config."""
        return DatabaseConfig(
            url="sqlite+aiosqlite:///:memory:",
            echo=False,
        )

    @pytest.fixture
    def db_manager(self, db_config: DatabaseConfig) -> AsyncDatabaseManager:
        """Create database manager instance."""
        return AsyncDatabaseManager(db_config)

    def test_create_manager(self, db_config: DatabaseConfig) -> None:
        """Should create database manager."""
        manager = AsyncDatabaseManager(db_config)
        
        assert manager is not None
        assert manager.config == db_config

    def test_engine_property(self, db_manager: AsyncDatabaseManager) -> None:
        """Should provide access to engine."""
        engine = db_manager.engine
        
        assert engine is not None

    def test_session_factory_property(
        self, db_manager: AsyncDatabaseManager
    ) -> None:
        """Should provide session factory."""
        factory = db_manager.session_factory
        
        assert factory is not None

    @pytest.mark.asyncio
    async def test_get_session(self, db_manager: AsyncDatabaseManager) -> None:
        """Should provide async session context manager."""
        async with db_manager.get_session() as session:
            assert isinstance(session, AsyncSession)

    @pytest.mark.asyncio
    async def test_session_commits_on_success(
        self, db_manager: AsyncDatabaseManager
    ) -> None:
        """Should commit session on successful exit."""
        # Create tables first
        async with db_manager.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        async with db_manager.get_session() as session:
            model = SampleModel(name="test")
            session.add(model)
        
        # Verify committed
        async with db_manager.get_session() as session:
            result = await session.execute(
                text("SELECT name FROM sample_model WHERE name = 'test'")
            )
            row = result.fetchone()
            assert row is not None

    @pytest.mark.asyncio
    async def test_session_rollback_on_exception(
        self, db_manager: AsyncDatabaseManager
    ) -> None:
        """Should rollback session on exception."""
        # Create tables first
        async with db_manager.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        try:
            async with db_manager.get_session() as session:
                model = SampleModel(name="rollback_test")
                session.add(model)
                raise ValueError("Test error")
        except ValueError:
            pass
        
        # Verify not committed
        async with db_manager.get_session() as session:
            result = await session.execute(
                text("SELECT name FROM sample_model WHERE name = 'rollback_test'")
            )
            row = result.fetchone()
            assert row is None

    @pytest.mark.asyncio
    async def test_create_all_tables(
        self, db_manager: AsyncDatabaseManager
    ) -> None:
        """Should create all tables."""
        await db_manager.create_all(Base)
        
        # Verify table exists
        async with db_manager.engine.begin() as conn:
            result = await conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND name='sample_model'")
            )
            row = result.fetchone()
            assert row is not None

    @pytest.mark.asyncio
    async def test_drop_all_tables(
        self, db_manager: AsyncDatabaseManager
    ) -> None:
        """Should drop all tables."""
        await db_manager.create_all(Base)
        await db_manager.drop_all(Base)
        
        # Verify table dropped
        async with db_manager.engine.begin() as conn:
            result = await conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND name='sample_model'")
            )
            row = result.fetchone()
            assert row is None

    @pytest.mark.asyncio
    async def test_dispose_engine(
        self, db_manager: AsyncDatabaseManager
    ) -> None:
        """Should dispose engine connections."""
        await db_manager.dispose()
        # Should be able to call multiple times
        await db_manager.dispose()

    @pytest.mark.asyncio
    async def test_health_check(
        self, db_manager: AsyncDatabaseManager
    ) -> None:
        """Should check database health."""
        is_healthy = await db_manager.health_check()
        
        assert is_healthy is True


class TestGetAsyncSession:
    """Tests for get_async_session dependency."""

    @pytest.fixture
    def db_manager(self) -> AsyncDatabaseManager:
        """Create database manager instance."""
        config = DatabaseConfig(url="sqlite+aiosqlite:///:memory:")
        return AsyncDatabaseManager(config)

    @pytest.mark.asyncio
    async def test_get_async_session_dependency(
        self, db_manager: AsyncDatabaseManager
    ) -> None:
        """Should provide session via dependency."""
        dependency = get_async_session(db_manager)
        
        async for session in dependency:
            assert isinstance(session, AsyncSession)
            break
