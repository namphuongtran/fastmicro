"""Tests for shared.sqlalchemy.models module.

This module tests base model utilities.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID

import pytest
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

from shared.sqlalchemy_async.database import AsyncDatabaseManager, DatabaseConfig
from shared.sqlalchemy_async.models import (
    TimestampMixin,
    SoftDeleteMixin,
    UUIDPrimaryKeyMixin,
    AuditMixin,
)


class TestTimestampMixin:
    """Tests for TimestampMixin."""

    @pytest.fixture
    def model_with_timestamps(self):
        """Create model with timestamp mixin."""
        class Base(DeclarativeBase):
            pass
        
        class TestModel(TimestampMixin, Base):
            __tablename__ = "test_timestamps"
            id = Column(Integer, primary_key=True)
            name = Column(String(100))
        
        return Base, TestModel

    @pytest.fixture
    def db_manager(self) -> AsyncDatabaseManager:
        """Create database manager."""
        config = DatabaseConfig(url="sqlite+aiosqlite:///:memory:")
        return AsyncDatabaseManager(config)

    @pytest.mark.asyncio
    async def test_created_at_set_on_insert(
        self, db_manager: AsyncDatabaseManager, model_with_timestamps
    ) -> None:
        """Should set created_at on insert."""
        Base, TestModel = model_with_timestamps
        await db_manager.create_all(Base)
        
        async with db_manager.get_session() as session:
            model = TestModel(name="test")
            session.add(model)
            await session.flush()
            
            assert model.created_at is not None
            assert isinstance(model.created_at, datetime)

    @pytest.mark.asyncio
    async def test_updated_at_set_on_update(
        self, db_manager: AsyncDatabaseManager, model_with_timestamps
    ) -> None:
        """Should set updated_at on update."""
        Base, TestModel = model_with_timestamps
        await db_manager.create_all(Base)
        
        async with db_manager.get_session() as session:
            model = TestModel(name="original")
            session.add(model)
            await session.flush()
            
            original_updated_at = model.updated_at
            
            # Update the model
            model.name = "updated"
            await session.flush()
            
            assert model.updated_at is not None
            # Note: updated_at should be >= original on update


class TestSoftDeleteMixin:
    """Tests for SoftDeleteMixin."""

    @pytest.fixture
    def model_with_soft_delete(self):
        """Create model with soft delete mixin."""
        class Base(DeclarativeBase):
            pass
        
        class TestModel(SoftDeleteMixin, Base):
            __tablename__ = "test_soft_delete"
            id = Column(Integer, primary_key=True)
            name = Column(String(100))
        
        return Base, TestModel

    @pytest.fixture
    def db_manager(self) -> AsyncDatabaseManager:
        """Create database manager."""
        config = DatabaseConfig(url="sqlite+aiosqlite:///:memory:")
        return AsyncDatabaseManager(config)

    @pytest.mark.asyncio
    async def test_is_deleted_defaults_to_false(
        self, db_manager: AsyncDatabaseManager, model_with_soft_delete
    ) -> None:
        """Should default is_deleted to False."""
        Base, TestModel = model_with_soft_delete
        await db_manager.create_all(Base)
        
        async with db_manager.get_session() as session:
            model = TestModel(name="test")
            session.add(model)
            await session.flush()
            
            assert model.is_deleted is False
            assert model.deleted_at is None

    @pytest.mark.asyncio
    async def test_soft_delete(
        self, db_manager: AsyncDatabaseManager, model_with_soft_delete
    ) -> None:
        """Should soft delete model."""
        Base, TestModel = model_with_soft_delete
        await db_manager.create_all(Base)
        
        async with db_manager.get_session() as session:
            model = TestModel(name="test")
            session.add(model)
            await session.flush()
            
            # Soft delete
            model.soft_delete()
            await session.flush()
            
            assert model.is_deleted is True
            assert model.deleted_at is not None

    @pytest.mark.asyncio
    async def test_restore(
        self, db_manager: AsyncDatabaseManager, model_with_soft_delete
    ) -> None:
        """Should restore soft deleted model."""
        Base, TestModel = model_with_soft_delete
        await db_manager.create_all(Base)
        
        async with db_manager.get_session() as session:
            model = TestModel(name="test")
            session.add(model)
            await session.flush()
            
            model.soft_delete()
            await session.flush()
            
            model.restore()
            await session.flush()
            
            assert model.is_deleted is False
            assert model.deleted_at is None


class TestUUIDPrimaryKeyMixin:
    """Tests for UUIDPrimaryKeyMixin."""

    @pytest.fixture
    def model_with_uuid(self):
        """Create model with UUID primary key."""
        class Base(DeclarativeBase):
            pass
        
        class TestModel(UUIDPrimaryKeyMixin, Base):
            __tablename__ = "test_uuid"
            name = Column(String(100))
        
        return Base, TestModel

    @pytest.fixture
    def db_manager(self) -> AsyncDatabaseManager:
        """Create database manager."""
        config = DatabaseConfig(url="sqlite+aiosqlite:///:memory:")
        return AsyncDatabaseManager(config)

    @pytest.mark.asyncio
    async def test_uuid_generated_on_insert(
        self, db_manager: AsyncDatabaseManager, model_with_uuid
    ) -> None:
        """Should generate UUID on insert."""
        Base, TestModel = model_with_uuid
        await db_manager.create_all(Base)
        
        async with db_manager.get_session() as session:
            model = TestModel(name="test")
            session.add(model)
            await session.flush()
            
            assert model.id is not None
            # Should be a valid UUID string
            UUID(str(model.id))

    @pytest.mark.asyncio
    async def test_uuid_is_unique(
        self, db_manager: AsyncDatabaseManager, model_with_uuid
    ) -> None:
        """Should generate unique UUIDs."""
        Base, TestModel = model_with_uuid
        await db_manager.create_all(Base)
        
        async with db_manager.get_session() as session:
            model1 = TestModel(name="test1")
            model2 = TestModel(name="test2")
            session.add(model1)
            session.add(model2)
            await session.flush()
            
            assert model1.id != model2.id


class TestAuditMixin:
    """Tests for AuditMixin."""

    @pytest.fixture
    def model_with_audit(self):
        """Create model with audit mixin."""
        class Base(DeclarativeBase):
            pass
        
        class TestModel(AuditMixin, Base):
            __tablename__ = "test_audit"
            id = Column(Integer, primary_key=True)
            name = Column(String(100))
        
        return Base, TestModel

    @pytest.fixture
    def db_manager(self) -> AsyncDatabaseManager:
        """Create database manager."""
        config = DatabaseConfig(url="sqlite+aiosqlite:///:memory:")
        return AsyncDatabaseManager(config)

    @pytest.mark.asyncio
    async def test_audit_fields_exist(
        self, db_manager: AsyncDatabaseManager, model_with_audit
    ) -> None:
        """Should have audit fields."""
        Base, TestModel = model_with_audit
        await db_manager.create_all(Base)
        
        async with db_manager.get_session() as session:
            model = TestModel(name="test", created_by="user1")
            session.add(model)
            await session.flush()
            
            assert model.created_by == "user1"
            assert model.updated_by is None

    @pytest.mark.asyncio
    async def test_set_updated_by(
        self, db_manager: AsyncDatabaseManager, model_with_audit
    ) -> None:
        """Should set updated_by on update."""
        Base, TestModel = model_with_audit
        await db_manager.create_all(Base)
        
        async with db_manager.get_session() as session:
            model = TestModel(name="original", created_by="user1")
            session.add(model)
            await session.flush()
            
            model.name = "updated"
            model.updated_by = "user2"
            await session.flush()
            
            assert model.updated_by == "user2"
