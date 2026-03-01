"""Database infrastructure for identity-service.

Provides AsyncDatabaseManager initialization and FastAPI session dependency.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from shared.sqlalchemy_async import AsyncDatabaseManager, DatabaseConfig

# Module-level database manager - initialized during app lifespan
_db_manager: AsyncDatabaseManager | None = None


def init_db_manager(
    database_url: str,
    pool_size: int = 10,
    max_overflow: int = 20,
    echo: bool = False,
) -> AsyncDatabaseManager:
    """Initialize the database manager singleton.

    Should be called once during application startup (lifespan).

    Args:
        database_url: Async PostgreSQL connection URL.
        pool_size: Connection pool size.
        max_overflow: Pool overflow limit.
        echo: Enable SQL logging.

    Returns:
        Configured AsyncDatabaseManager.
    """
    global _db_manager  # noqa: PLW0603
    _db_manager = AsyncDatabaseManager(
        DatabaseConfig(
            url=database_url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            echo=echo,
        )
    )
    return _db_manager


def get_db_manager() -> AsyncDatabaseManager:
    """Get the database manager singleton.

    Returns:
        AsyncDatabaseManager instance.

    Raises:
        RuntimeError: If database manager has not been initialized.
    """
    if _db_manager is None:
        msg = "Database manager not initialized. Call init_db_manager() during startup."
        raise RuntimeError(msg)
    return _db_manager


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a database session with transaction management.

    The session commits on success and rolls back on exception.

    Yields:
        AsyncSession bound to the identity database.
    """
    db = get_db_manager()
    async with db.get_session() as session:
        yield session


async def dispose_db() -> None:
    """Dispose database connections during shutdown."""
    global _db_manager  # noqa: PLW0603
    if _db_manager is not None:
        await _db_manager.dispose()
        _db_manager = None
