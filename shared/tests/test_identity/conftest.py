"""Shared test fixtures for identity module tests.

Provides database setup, domain entity factories, and common helpers.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from shared.identity.models.base import IdentityBase
from shared.sqlalchemy_async.database import AsyncDatabaseManager, DatabaseConfig


@pytest.fixture
def db_manager() -> AsyncDatabaseManager:
    """Create an in-memory SQLite async database manager."""
    config = DatabaseConfig(url="sqlite+aiosqlite:///:memory:")
    return AsyncDatabaseManager(config)


@pytest.fixture
async def setup_db(db_manager: AsyncDatabaseManager) -> AsyncDatabaseManager:
    """Set up database tables and return manager."""
    await db_manager.create_all(IdentityBase)
    return db_manager


def make_user_id() -> uuid.UUID:
    """Generate a stable UUID for testing."""
    return uuid.uuid4()


def utc_now() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(UTC)
