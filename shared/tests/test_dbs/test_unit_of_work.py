"""Tests for shared.dbs.unit_of_work module.

This module tests the Unit of Work pattern implementation
including transaction management and repository coordination.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

if TYPE_CHECKING:
    pass

from shared.dbs.unit_of_work import (
    AbstractUnitOfWork,
    InMemoryUnitOfWork,
)
from shared.dbs.repository import InMemoryRepository


@dataclass
class User:
    """Test user entity."""
    id: str
    name: str
    email: str


@dataclass
class Order:
    """Test order entity."""
    id: str
    user_id: str
    total: float


class TestAbstractUnitOfWork:
    """Tests for AbstractUnitOfWork interface."""

    def test_is_abstract(self) -> None:
        """Should be an abstract class."""
        with pytest.raises(TypeError):
            AbstractUnitOfWork()  # type: ignore[abstract]


class TestInMemoryUnitOfWork:
    """Tests for InMemoryUnitOfWork implementation."""

    @pytest.fixture
    def uow(self) -> InMemoryUnitOfWork:
        """Create a test unit of work."""
        return InMemoryUnitOfWork()

    @pytest.mark.asyncio
    async def test_context_manager_entry(self, uow: InMemoryUnitOfWork) -> None:
        """Should work as async context manager."""
        async with uow:
            # Should not raise
            pass

    @pytest.mark.asyncio
    async def test_commit(self, uow: InMemoryUnitOfWork) -> None:
        """Should commit changes."""
        async with uow:
            await uow.commit()
            # Should not raise

    @pytest.mark.asyncio
    async def test_rollback(self, uow: InMemoryUnitOfWork) -> None:
        """Should rollback changes."""
        async with uow:
            await uow.rollback()
            # Should not raise

    @pytest.mark.asyncio
    async def test_auto_rollback_on_exception(self, uow: InMemoryUnitOfWork) -> None:
        """Should rollback on exception."""
        with pytest.raises(ValueError):
            async with uow:
                raise ValueError("Test error")
        # Rollback should have been called automatically

    @pytest.mark.asyncio
    async def test_register_repository(self, uow: InMemoryUnitOfWork) -> None:
        """Should register repositories."""
        users_repo = InMemoryRepository[User](id_field="id")
        uow.register_repository("users", users_repo)
        
        assert uow.get_repository("users") is users_repo

    @pytest.mark.asyncio
    async def test_get_nonexistent_repository(self, uow: InMemoryUnitOfWork) -> None:
        """Should raise for nonexistent repository."""
        with pytest.raises(KeyError):
            uow.get_repository("nonexistent")

    @pytest.mark.asyncio
    async def test_multiple_repositories(self, uow: InMemoryUnitOfWork) -> None:
        """Should support multiple repositories."""
        users_repo = InMemoryRepository[User](id_field="id")
        orders_repo = InMemoryRepository[Order](id_field="id")
        
        uow.register_repository("users", users_repo)
        uow.register_repository("orders", orders_repo)
        
        async with uow:
            # Add user
            await users_repo.add(User(id="1", name="Alice", email="alice@test.com"))
            
            # Add order for user
            await orders_repo.add(Order(id="100", user_id="1", total=99.99))
            
            await uow.commit()
        
        # Verify both repositories have data
        assert await users_repo.count() == 1
        assert await orders_repo.count() == 1

    @pytest.mark.asyncio
    async def test_is_active_property(self, uow: InMemoryUnitOfWork) -> None:
        """Should track if UoW is active."""
        assert uow.is_active is False
        
        async with uow:
            assert uow.is_active is True
        
        assert uow.is_active is False


class TestUnitOfWorkTransactions:
    """Tests for transaction-like behavior."""

    @pytest.fixture
    def uow(self) -> InMemoryUnitOfWork:
        """Create UoW with repositories."""
        uow = InMemoryUnitOfWork()
        uow.register_repository("users", InMemoryRepository[User](id_field="id"))
        return uow

    @pytest.mark.asyncio
    async def test_commit_persists_changes(self, uow: InMemoryUnitOfWork) -> None:
        """Should persist changes on commit."""
        users = uow.get_repository("users")
        
        async with uow:
            await users.add(User(id="1", name="Test", email="test@test.com"))
            await uow.commit()
        
        assert await users.exists("1")

    @pytest.mark.asyncio
    async def test_changes_visible_within_transaction(
        self, uow: InMemoryUnitOfWork
    ) -> None:
        """Should see changes within same transaction."""
        users = uow.get_repository("users")
        
        async with uow:
            await users.add(User(id="1", name="Test", email="test@test.com"))
            
            # Should be visible before commit
            user = await users.get("1")
            assert user is not None
            assert user.name == "Test"
