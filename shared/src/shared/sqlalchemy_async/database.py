"""Async SQLAlchemy database management utilities.

This module provides utilities for managing async SQLAlchemy databases:
- AsyncDatabaseManager: Manages async engine and session factory
- DatabaseConfig: Configuration dataclass for database connections
- get_async_session: FastAPI dependency for async sessions
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase


@dataclass
class DatabaseConfig:
    """Configuration for async database connections.

    Attributes:
        url: Async database URL (e.g., postgresql+asyncpg://...).
        pool_size: Connection pool size.
        max_overflow: Maximum overflow connections beyond pool_size.
        pool_timeout: Seconds to wait for available connection.
        pool_recycle: Seconds before connection recycling.
        echo: Enable SQL logging.
        echo_pool: Enable connection pool logging.
        connect_args: Additional connection arguments.
    """

    url: str
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30
    pool_recycle: int = 3600
    echo: bool = False
    echo_pool: bool = False
    connect_args: dict[str, Any] = field(default_factory=dict)


class AsyncDatabaseManager:
    """Manages async SQLAlchemy engine and sessions.

    This class provides:
    - Async engine creation and management
    - Session factory with proper transaction handling
    - Table creation/deletion utilities
    - Health check functionality

    Example:
        >>> config = DatabaseConfig(url="sqlite+aiosqlite:///:memory:")
        >>> db = AsyncDatabaseManager(config)
        >>> async with db.get_session() as session:
        ...     result = await session.execute(text("SELECT 1"))
    """

    def __init__(self, config: DatabaseConfig) -> None:
        """Initialize database manager.

        Args:
            config: Database configuration.
        """
        self._config = config
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    @property
    def config(self) -> DatabaseConfig:
        """Get database configuration."""
        return self._config

    @property
    def engine(self) -> AsyncEngine:
        """Get or create async engine.

        Returns:
            AsyncEngine instance.
        """
        if self._engine is None:
            # Determine engine options based on database type
            engine_options: dict[str, Any] = {
                "echo": self._config.echo,
                "echo_pool": self._config.echo_pool,
            }

            # SQLite doesn't support pool configuration
            if not self._config.url.startswith("sqlite"):
                engine_options.update(
                    {
                        "pool_size": self._config.pool_size,
                        "max_overflow": self._config.max_overflow,
                        "pool_timeout": self._config.pool_timeout,
                        "pool_recycle": self._config.pool_recycle,
                    }
                )

            if self._config.connect_args:
                engine_options["connect_args"] = self._config.connect_args

            self._engine = create_async_engine(
                self._config.url,
                **engine_options,
            )

        return self._engine

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        """Get or create session factory.

        Returns:
            Async session maker instance.
        """
        if self._session_factory is None:
            self._session_factory = async_sessionmaker(
                bind=self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=False,
            )

        return self._session_factory

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get async session with automatic transaction management.

        Commits on successful exit, rolls back on exception.

        Yields:
            AsyncSession instance.

        Example:
            >>> async with db.get_session() as session:
            ...     session.add(model)
            ...     # Commits automatically on exit
        """
        session = self.session_factory()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    async def create_all(self, base: type[DeclarativeBase]) -> None:
        """Create all tables defined in the declarative base.

        Args:
            base: SQLAlchemy declarative base class.
        """
        async with self.engine.begin() as conn:
            await conn.run_sync(base.metadata.create_all)

    async def drop_all(self, base: type[DeclarativeBase]) -> None:
        """Drop all tables defined in the declarative base.

        Args:
            base: SQLAlchemy declarative base class.
        """
        async with self.engine.begin() as conn:
            await conn.run_sync(base.metadata.drop_all)

    async def dispose(self) -> None:
        """Dispose engine and close all connections."""
        if self._engine is not None:
            await self._engine.dispose()

    async def health_check(self) -> bool:
        """Check database connectivity.

        Returns:
            True if database is reachable, False otherwise.
        """
        try:
            async with self.engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False


async def get_async_session(
    db_manager: AsyncDatabaseManager,
) -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for async database sessions.

    Use with FastAPI's Depends for dependency injection:

    Example:
        >>> @app.get("/users")
        ... async def get_users(
        ...     session: AsyncSession = Depends(get_async_session(db_manager))
        ... ):
        ...     # Use session

    Args:
        db_manager: Database manager instance.

    Yields:
        AsyncSession instance.
    """
    async with db_manager.get_session() as session:
        yield session
