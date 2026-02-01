"""Test configuration and fixtures for metastore-service tests."""

import asyncio
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from metastore_service.infrastructure.database.models import Base
from shared.cache.backends.null import NullCache

# Test database URL (use SQLite for faster tests)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """Create a test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        future=True,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async_session_maker = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_maker() as session:
        yield session
        await session.rollback()


@pytest.fixture
def null_cache():
    """Create a null cache for testing."""
    return NullCache()


@pytest.fixture
def sample_metadata_data():
    """Sample metadata data for testing."""
    return {
        "key": "test.config.key",
        "namespace": "test-namespace",
        "value": {"setting1": "value1", "setting2": 42},
        "content_type": "json",
        "tags": ["test", "config"],
        "description": "Test configuration entry",
    }


@pytest.fixture
def sample_feature_flag_data():
    """Sample feature flag data for testing."""
    return {
        "name": "test-feature-flag",
        "description": "A test feature flag",
        "enabled": True,
        "default_value": {"variant": "control"},
        "rollout_percentage": 50,
        "tags": ["test", "experiment"],
    }


@pytest.fixture
def sample_configuration_data():
    """Sample configuration data for testing."""
    return {
        "service_id": "test-service",
        "name": "database-config",
        "environment": "development",
        "values": {
            "host": "localhost",
            "port": 5432,
            "pool_size": 10,
        },
        "description": "Test database configuration",
    }
