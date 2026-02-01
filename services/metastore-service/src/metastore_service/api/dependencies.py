"""API dependencies for dependency injection.

Uses the shared library's AsyncDatabaseManager and TieredCacheManager
for consistent database and cache access across the application.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from metastore_service.application.services.configuration_service import ConfigurationService
from metastore_service.application.services.feature_flag_service import FeatureFlagService
from metastore_service.application.services.metadata_service import MetadataService
from metastore_service.infrastructure.repositories.configuration_repository import (
    PostgresConfigurationRepository,
    PostgresConfigurationSchemaRepository,
)
from metastore_service.infrastructure.repositories.feature_flag_repository import (
    PostgresFeatureFlagRepository,
)
from metastore_service.infrastructure.repositories.metadata_repository import (
    PostgresMetadataRepository,
)
from shared.cache import TieredCacheManager
from shared.cache.backends.null import NullCache
from shared.sqlalchemy_async import AsyncDatabaseManager

# Global managers - initialized in main.py lifespan
_database_manager: AsyncDatabaseManager | None = None
_cache_manager: TieredCacheManager | None = None


def get_database_manager() -> AsyncDatabaseManager:
    """Get the database manager.

    Raises:
        RuntimeError: If database manager not initialized.
    """
    if _database_manager is None:
        raise RuntimeError("Database manager not initialized")
    return _database_manager


def set_database_manager(manager: AsyncDatabaseManager) -> None:
    """Set the database manager (called during startup)."""
    global _database_manager
    _database_manager = manager


def get_cache() -> TieredCacheManager | NullCache:
    """Get the cache manager (or NullCache if not initialized)."""
    if _cache_manager is None:
        return NullCache()
    return _cache_manager


def set_cache(cache: TieredCacheManager) -> None:
    """Set the cache manager (called during startup)."""
    global _cache_manager
    _cache_manager = cache


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions.

    Yields:
        AsyncSession with automatic commit/rollback handling.
    """
    manager = get_database_manager()
    async with manager.get_session() as session:
        yield session


async def get_metadata_service(
    session: AsyncSession = Depends(get_db_session),
) -> MetadataService:
    """Get the metadata service."""
    repository = PostgresMetadataRepository(session)
    cache = get_cache()
    return MetadataService(repository, cache)


async def get_feature_flag_service(
    session: AsyncSession = Depends(get_db_session),
) -> FeatureFlagService:
    """Get the feature flag service."""
    repository = PostgresFeatureFlagRepository(session)
    cache = get_cache()
    return FeatureFlagService(repository, cache)


async def get_configuration_service(
    session: AsyncSession = Depends(get_db_session),
) -> ConfigurationService:
    """Get the configuration service."""
    repository = PostgresConfigurationRepository(session)
    schema_repository = PostgresConfigurationSchemaRepository(session)
    cache = get_cache()
    return ConfigurationService(repository, schema_repository, cache)
