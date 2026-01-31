"""Tests for shared.sqlalchemy.repository module.

This module tests async SQLAlchemy repository pattern.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import Column, Integer, String, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

from shared.sqlalchemy_async.database import AsyncDatabaseManager, DatabaseConfig
from shared.sqlalchemy_async.repository import (
    AsyncRepository,
    AsyncCRUDRepository,
)
from shared.dbs.repository import (
    Filter,
    FilterOperator,
    OrderBy,
    OrderDirection,
    PageRequest,
    PageResponse,
)


class Base(DeclarativeBase):
    """Test base class."""
    pass


class User(Base):
    """Test user model."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    email = Column(String(100), unique=True)


class UserRepository(AsyncCRUDRepository[User, int]):
    """Test user repository."""
    
    @property
    def model_class(self) -> type[User]:
        return User


class TestAsyncRepository:
    """Tests for AsyncRepository base class."""

    @pytest.fixture
    def db_manager(self) -> AsyncDatabaseManager:
        """Create database manager."""
        config = DatabaseConfig(url="sqlite+aiosqlite:///:memory:")
        return AsyncDatabaseManager(config)

    @pytest.mark.asyncio
    async def test_repository_with_session(
        self, db_manager: AsyncDatabaseManager
    ) -> None:
        """Should work with async session."""
        await db_manager.create_all(Base)
        
        async with db_manager.get_session() as session:
            repo = UserRepository(session)
            assert repo.session == session


class TestAsyncCRUDRepository:
    """Tests for AsyncCRUDRepository class."""

    @pytest.fixture
    def db_manager(self) -> AsyncDatabaseManager:
        """Create database manager."""
        config = DatabaseConfig(url="sqlite+aiosqlite:///:memory:")
        return AsyncDatabaseManager(config)

    @pytest.fixture
    async def setup_db(self, db_manager: AsyncDatabaseManager):
        """Set up database tables."""
        await db_manager.create_all(Base)
        yield
        await db_manager.drop_all(Base)

    @pytest.mark.asyncio
    async def test_create(
        self, db_manager: AsyncDatabaseManager, setup_db
    ) -> None:
        """Should create entity."""
        async with db_manager.get_session() as session:
            repo = UserRepository(session)
            user = await repo.create(name="John", email="john@example.com")
            
            assert user.id is not None
            assert user.name == "John"
            assert user.email == "john@example.com"

    @pytest.mark.asyncio
    async def test_get_by_id(
        self, db_manager: AsyncDatabaseManager, setup_db
    ) -> None:
        """Should get entity by ID."""
        async with db_manager.get_session() as session:
            repo = UserRepository(session)
            created = await repo.create(name="Jane", email="jane@example.com")
        
        async with db_manager.get_session() as session:
            repo = UserRepository(session)
            user = await repo.get_by_id(created.id)
            
            assert user is not None
            assert user.name == "Jane"

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(
        self, db_manager: AsyncDatabaseManager, setup_db
    ) -> None:
        """Should return None for non-existent ID."""
        async with db_manager.get_session() as session:
            repo = UserRepository(session)
            user = await repo.get_by_id(99999)
            
            assert user is None

    @pytest.mark.asyncio
    async def test_get_all(
        self, db_manager: AsyncDatabaseManager, setup_db
    ) -> None:
        """Should get all entities."""
        async with db_manager.get_session() as session:
            repo = UserRepository(session)
            await repo.create(name="User1", email="user1@example.com")
            await repo.create(name="User2", email="user2@example.com")
        
        async with db_manager.get_session() as session:
            repo = UserRepository(session)
            users = await repo.get_all()
            
            assert len(users) == 2

    @pytest.mark.asyncio
    async def test_get_all_with_limit(
        self, db_manager: AsyncDatabaseManager, setup_db
    ) -> None:
        """Should respect limit parameter."""
        async with db_manager.get_session() as session:
            repo = UserRepository(session)
            for i in range(5):
                await repo.create(name=f"User{i}", email=f"user{i}@example.com")
        
        async with db_manager.get_session() as session:
            repo = UserRepository(session)
            users = await repo.get_all(limit=3)
            
            assert len(users) == 3

    @pytest.mark.asyncio
    async def test_get_all_with_offset(
        self, db_manager: AsyncDatabaseManager, setup_db
    ) -> None:
        """Should respect offset parameter."""
        async with db_manager.get_session() as session:
            repo = UserRepository(session)
            for i in range(5):
                await repo.create(name=f"User{i}", email=f"user{i}@example.com")
        
        async with db_manager.get_session() as session:
            repo = UserRepository(session)
            users = await repo.get_all(offset=3)
            
            assert len(users) == 2

    @pytest.mark.asyncio
    async def test_update(
        self, db_manager: AsyncDatabaseManager, setup_db
    ) -> None:
        """Should update entity."""
        async with db_manager.get_session() as session:
            repo = UserRepository(session)
            user = await repo.create(name="Original", email="original@example.com")
            user_id = user.id
        
        async with db_manager.get_session() as session:
            repo = UserRepository(session)
            updated = await repo.update(user_id, name="Updated")
            
            assert updated is not None
            assert updated.name == "Updated"
            assert updated.email == "original@example.com"

    @pytest.mark.asyncio
    async def test_update_not_found(
        self, db_manager: AsyncDatabaseManager, setup_db
    ) -> None:
        """Should return None when updating non-existent entity."""
        async with db_manager.get_session() as session:
            repo = UserRepository(session)
            result = await repo.update(99999, name="Updated")
            
            assert result is None

    @pytest.mark.asyncio
    async def test_delete(
        self, db_manager: AsyncDatabaseManager, setup_db
    ) -> None:
        """Should delete entity."""
        async with db_manager.get_session() as session:
            repo = UserRepository(session)
            user = await repo.create(name="ToDelete", email="delete@example.com")
            user_id = user.id
        
        async with db_manager.get_session() as session:
            repo = UserRepository(session)
            deleted = await repo.delete(user_id)
            
            assert deleted is True
        
        async with db_manager.get_session() as session:
            repo = UserRepository(session)
            user = await repo.get_by_id(user_id)
            
            assert user is None

    @pytest.mark.asyncio
    async def test_delete_not_found(
        self, db_manager: AsyncDatabaseManager, setup_db
    ) -> None:
        """Should return False when deleting non-existent entity."""
        async with db_manager.get_session() as session:
            repo = UserRepository(session)
            result = await repo.delete(99999)
            
            assert result is False

    @pytest.mark.asyncio
    async def test_exists(
        self, db_manager: AsyncDatabaseManager, setup_db
    ) -> None:
        """Should check if entity exists."""
        async with db_manager.get_session() as session:
            repo = UserRepository(session)
            user = await repo.create(name="Exists", email="exists@example.com")
            user_id = user.id
        
        async with db_manager.get_session() as session:
            repo = UserRepository(session)
            
            assert await repo.exists(user_id) is True
            assert await repo.exists(99999) is False

    @pytest.mark.asyncio
    async def test_count(
        self, db_manager: AsyncDatabaseManager, setup_db
    ) -> None:
        """Should count entities."""
        async with db_manager.get_session() as session:
            repo = UserRepository(session)
            await repo.create(name="User1", email="user1@example.com")
            await repo.create(name="User2", email="user2@example.com")
            await repo.create(name="User3", email="user3@example.com")
        
        async with db_manager.get_session() as session:
            repo = UserRepository(session)
            count = await repo.count()
            
            assert count == 3

    @pytest.mark.asyncio
    async def test_find_by(
        self, db_manager: AsyncDatabaseManager, setup_db
    ) -> None:
        """Should find entities by criteria."""
        async with db_manager.get_session() as session:
            repo = UserRepository(session)
            await repo.create(name="John", email="john@example.com")
            await repo.create(name="Jane", email="jane@example.com")
            await repo.create(name="John", email="john2@example.com")
        
        async with db_manager.get_session() as session:
            repo = UserRepository(session)
            johns = await repo.find_by(name="John")
            
            assert len(johns) == 2
            assert all(u.name == "John" for u in johns)

    @pytest.mark.asyncio
    async def test_find_one_by(
        self, db_manager: AsyncDatabaseManager, setup_db
    ) -> None:
        """Should find single entity by criteria."""
        async with db_manager.get_session() as session:
            repo = UserRepository(session)
            await repo.create(name="Unique", email="unique@example.com")
        
        async with db_manager.get_session() as session:
            repo = UserRepository(session)
            user = await repo.find_one_by(email="unique@example.com")
            
            assert user is not None
            assert user.name == "Unique"

    @pytest.mark.asyncio
    async def test_find_one_by_not_found(
        self, db_manager: AsyncDatabaseManager, setup_db
    ) -> None:
        """Should return None when no match found."""
        async with db_manager.get_session() as session:
            repo = UserRepository(session)
            user = await repo.find_one_by(email="nonexistent@example.com")
            
            assert user is None


class TestFilteringAndPagination:
    """Tests for filtering and pagination support."""

    @pytest.fixture
    def db_manager(self) -> AsyncDatabaseManager:
        """Create database manager."""
        config = DatabaseConfig(url="sqlite+aiosqlite:///:memory:")
        return AsyncDatabaseManager(config)

    @pytest.fixture
    async def setup_db(self, db_manager: AsyncDatabaseManager):
        """Set up database tables."""
        await db_manager.create_all(Base)
        yield
        await db_manager.drop_all(Base)

    @pytest.fixture
    async def seed_users(self, db_manager: AsyncDatabaseManager, setup_db):
        """Seed database with test users."""
        async with db_manager.get_session() as session:
            repo = UserRepository(session)
            await repo.create(name="Alice", email="alice@example.com")
            await repo.create(name="Bob", email="bob@example.com")
            await repo.create(name="Charlie", email="charlie@example.com")
            await repo.create(name="David", email="david@example.com")
            await repo.create(name="Eve", email="eve@example.com")
        yield

    @pytest.mark.asyncio
    async def test_filter_eq(
        self, db_manager: AsyncDatabaseManager, seed_users
    ) -> None:
        """Should filter by equality."""
        async with db_manager.get_session() as session:
            repo = UserRepository(session)
            filters = [Filter(field="name", operator=FilterOperator.EQ, value="Alice")]
            users = await repo.find_with_filters(filters)
            
            assert len(users) == 1
            assert users[0].name == "Alice"

    @pytest.mark.asyncio
    async def test_filter_ne(
        self, db_manager: AsyncDatabaseManager, seed_users
    ) -> None:
        """Should filter by not equal."""
        async with db_manager.get_session() as session:
            repo = UserRepository(session)
            filters = [Filter(field="name", operator=FilterOperator.NE, value="Alice")]
            users = await repo.find_with_filters(filters)
            
            assert len(users) == 4
            assert all(u.name != "Alice" for u in users)

    @pytest.mark.asyncio
    async def test_filter_contains(
        self, db_manager: AsyncDatabaseManager, seed_users
    ) -> None:
        """Should filter by contains."""
        async with db_manager.get_session() as session:
            repo = UserRepository(session)
            filters = [Filter(field="email", operator=FilterOperator.CONTAINS, value="@example")]
            users = await repo.find_with_filters(filters)
            
            assert len(users) == 5

    @pytest.mark.asyncio
    async def test_filter_starts_with(
        self, db_manager: AsyncDatabaseManager, seed_users
    ) -> None:
        """Should filter by starts with."""
        async with db_manager.get_session() as session:
            repo = UserRepository(session)
            filters = [Filter(field="name", operator=FilterOperator.STARTS_WITH, value="A")]
            users = await repo.find_with_filters(filters)
            
            assert len(users) == 1
            assert users[0].name == "Alice"

    @pytest.mark.asyncio
    async def test_filter_in(
        self, db_manager: AsyncDatabaseManager, seed_users
    ) -> None:
        """Should filter by IN list."""
        async with db_manager.get_session() as session:
            repo = UserRepository(session)
            filters = [Filter(field="name", operator=FilterOperator.IN, value=["Alice", "Bob"])]
            users = await repo.find_with_filters(filters)
            
            assert len(users) == 2
            names = {u.name for u in users}
            assert names == {"Alice", "Bob"}

    @pytest.mark.asyncio
    async def test_filter_not_in(
        self, db_manager: AsyncDatabaseManager, seed_users
    ) -> None:
        """Should filter by NOT IN list."""
        async with db_manager.get_session() as session:
            repo = UserRepository(session)
            filters = [Filter(field="name", operator=FilterOperator.NOT_IN, value=["Alice", "Bob"])]
            users = await repo.find_with_filters(filters)
            
            assert len(users) == 3
            names = {u.name for u in users}
            assert names == {"Charlie", "David", "Eve"}

    @pytest.mark.asyncio
    async def test_multiple_filters(
        self, db_manager: AsyncDatabaseManager, seed_users
    ) -> None:
        """Should apply multiple filters (AND)."""
        async with db_manager.get_session() as session:
            repo = UserRepository(session)
            filters = [
                Filter(field="name", operator=FilterOperator.STARTS_WITH, value="A"),
                Filter(field="email", operator=FilterOperator.CONTAINS, value="alice"),
            ]
            users = await repo.find_with_filters(filters)
            
            assert len(users) == 1
            assert users[0].name == "Alice"

    @pytest.mark.asyncio
    async def test_order_by_asc(
        self, db_manager: AsyncDatabaseManager, seed_users
    ) -> None:
        """Should order by ascending."""
        async with db_manager.get_session() as session:
            repo = UserRepository(session)
            order_by = [OrderBy(field="name", direction=OrderDirection.ASC)]
            users = await repo.find_with_filters(order_by=order_by)
            
            names = [u.name for u in users]
            assert names == ["Alice", "Bob", "Charlie", "David", "Eve"]

    @pytest.mark.asyncio
    async def test_order_by_desc(
        self, db_manager: AsyncDatabaseManager, seed_users
    ) -> None:
        """Should order by descending."""
        async with db_manager.get_session() as session:
            repo = UserRepository(session)
            order_by = [OrderBy(field="name", direction=OrderDirection.DESC)]
            users = await repo.find_with_filters(order_by=order_by)
            
            names = [u.name for u in users]
            assert names == ["Eve", "David", "Charlie", "Bob", "Alice"]

    @pytest.mark.asyncio
    async def test_filter_with_limit(
        self, db_manager: AsyncDatabaseManager, seed_users
    ) -> None:
        """Should combine filter with limit."""
        async with db_manager.get_session() as session:
            repo = UserRepository(session)
            users = await repo.find_with_filters(limit=2)
            
            assert len(users) == 2

    @pytest.mark.asyncio
    async def test_count_with_filters(
        self, db_manager: AsyncDatabaseManager, seed_users
    ) -> None:
        """Should count with filters."""
        async with db_manager.get_session() as session:
            repo = UserRepository(session)
            filters = [Filter(field="name", operator=FilterOperator.IN, value=["Alice", "Bob"])]
            count = await repo.count(filters)
            
            assert count == 2

    @pytest.mark.asyncio
    async def test_paginate_first_page(
        self, db_manager: AsyncDatabaseManager, seed_users
    ) -> None:
        """Should paginate first page."""
        async with db_manager.get_session() as session:
            repo = UserRepository(session)
            page = await repo.paginate(PageRequest(page=1, size=2))
            
            assert isinstance(page, PageResponse)
            assert len(page.items) == 2
            assert page.total == 5
            assert page.page == 1
            assert page.size == 2
            assert page.total_pages == 3
            assert page.has_next is True
            assert page.has_previous is False

    @pytest.mark.asyncio
    async def test_paginate_middle_page(
        self, db_manager: AsyncDatabaseManager, seed_users
    ) -> None:
        """Should paginate middle page."""
        async with db_manager.get_session() as session:
            repo = UserRepository(session)
            page = await repo.paginate(PageRequest(page=2, size=2))
            
            assert len(page.items) == 2
            assert page.page == 2
            assert page.has_next is True
            assert page.has_previous is True

    @pytest.mark.asyncio
    async def test_paginate_last_page(
        self, db_manager: AsyncDatabaseManager, seed_users
    ) -> None:
        """Should paginate last page."""
        async with db_manager.get_session() as session:
            repo = UserRepository(session)
            page = await repo.paginate(PageRequest(page=3, size=2))
            
            assert len(page.items) == 1  # 5 total, last page has 1
            assert page.page == 3
            assert page.has_next is False
            assert page.has_previous is True

    @pytest.mark.asyncio
    async def test_paginate_with_filters(
        self, db_manager: AsyncDatabaseManager, seed_users
    ) -> None:
        """Should paginate with filters applied."""
        async with db_manager.get_session() as session:
            repo = UserRepository(session)
            filters = [Filter(field="name", operator=FilterOperator.IN, value=["Alice", "Bob", "Charlie"])]
            page = await repo.paginate(PageRequest(page=1, size=2), filters=filters)
            
            assert len(page.items) == 2
            assert page.total == 3
            assert page.total_pages == 2

    @pytest.mark.asyncio
    async def test_paginate_with_ordering(
        self, db_manager: AsyncDatabaseManager, seed_users
    ) -> None:
        """Should paginate with ordering."""
        async with db_manager.get_session() as session:
            repo = UserRepository(session)
            order_by = [OrderBy(field="name", direction=OrderDirection.DESC)]
            page = await repo.paginate(PageRequest(page=1, size=3), order_by=order_by)
            
            names = [u.name for u in page.items]
            assert names == ["Eve", "David", "Charlie"]

    @pytest.mark.asyncio
    async def test_filter_invalid_field(
        self, db_manager: AsyncDatabaseManager, seed_users
    ) -> None:
        """Should ignore filter on invalid field."""
        async with db_manager.get_session() as session:
            repo = UserRepository(session)
            filters = [Filter(field="nonexistent", operator=FilterOperator.EQ, value="test")]
            users = await repo.find_with_filters(filters)
            
            # Should return all users (filter ignored)
            assert len(users) == 5

    @pytest.mark.asyncio
    async def test_order_invalid_field(
        self, db_manager: AsyncDatabaseManager, seed_users
    ) -> None:
        """Should ignore order on invalid field."""
        async with db_manager.get_session() as session:
            repo = UserRepository(session)
            order_by = [OrderBy(field="nonexistent", direction=OrderDirection.ASC)]
            users = await repo.find_with_filters(order_by=order_by)
            
            # Should return all users (order ignored)
            assert len(users) == 5