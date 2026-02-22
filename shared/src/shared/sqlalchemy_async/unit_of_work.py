"""Async SQLAlchemy Unit of Work implementation.

Bridges the abstract ``AbstractUnitOfWork`` from ``shared.dbs`` with
SQLAlchemy's ``AsyncSession``, providing real transactional semantics
for repository coordination.

Architecture
~~~~~~~~~~~~
* Each ``begin()`` / ``async with`` context creates a **new** session.
* Repositories are instantiated lazily the first time they are accessed.
* ``commit()`` flushes the session and commits the underlying connection.
* ``rollback()`` rolls back and discards all pending changes.
* On context-manager exit an uncommitted session is automatically rolled back.

Example::

    async with SqlAlchemyUnitOfWork(db_manager) as uow:
        user_repo = uow.get_repository("users", UserRepository)
        user = await user_repo.create(name="Alice")

        outbox_repo = uow.get_repository("outbox", OutboxRepository)
        await outbox_repo.add(OutboxEntry.from_domain_event(event))

        await uow.commit()

Nested Savepoints
~~~~~~~~~~~~~~~~~
Use ``uow.begin_nested()`` for savepoints inside an already-open
transaction (e.g. in ``@transactional`` decorated methods that may be
called from other transactional methods).

    async with uow.begin_nested():
        ...  # rolls back only this savepoint on error
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from shared.dbs.unit_of_work import AbstractUnitOfWork
from shared.sqlalchemy_async.database import AsyncDatabaseManager

logger = logging.getLogger(__name__)

T = TypeVar("T")


class SqlAlchemyUnitOfWork(AbstractUnitOfWork):
    """Async SQLAlchemy implementation of :class:`AbstractUnitOfWork`.

    Wraps :class:`AsyncSession` to provide a clean transactional boundary
    for coordinating multiple repository operations.

    Parameters
    ----------
    db_manager:
        ``AsyncDatabaseManager`` instance that owns the engine and session
        factory.
    session_factory:
        Optional explicit ``async_sessionmaker``.  When provided it takes
        precedence over ``db_manager.session_factory``.  Useful in tests
        where you want to inject a pre-configured factory.
    """

    def __init__(
        self,
        db_manager: AsyncDatabaseManager | None = None,
        *,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
    ) -> None:
        if db_manager is None and session_factory is None:
            msg = "Either db_manager or session_factory must be provided"
            raise ValueError(msg)

        self._session_factory = session_factory or (
            db_manager.session_factory if db_manager else None
        )
        self._session: AsyncSession | None = None
        self._repositories: dict[str, Any] = {}
        self._is_active = False

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def session(self) -> AsyncSession:
        """Return the current session.

        Raises
        ------
        RuntimeError
            If accessed outside an active UoW context.
        """
        if self._session is None:
            msg = (
                "Session is not available. "
                "Use 'async with uow:' to enter the Unit of Work context first."
            )
            raise RuntimeError(msg)
        return self._session

    @property
    def is_active(self) -> bool:
        """Whether the unit of work context is currently open."""
        return self._is_active

    # ------------------------------------------------------------------
    # Repository access
    # ------------------------------------------------------------------

    def get_repository(self, name: str, repo_class: type[T] | None = None) -> T:
        """Retrieve a repository bound to the current session.

        If a repository with *name* hasn't been created yet and
        *repo_class* is provided, a new instance is created with the
        current session and cached for subsequent calls.

        Parameters
        ----------
        name:
            Logical name of the repository (e.g. ``"users"``).
        repo_class:
            Repository class to instantiate.  Must accept
            ``(session: AsyncSession)`` as its first constructor argument.

        Returns
        -------
        The repository instance, typed to *repo_class*.

        Raises
        ------
        KeyError
            If *name* is not registered and *repo_class* is ``None``.
        RuntimeError
            If the unit of work context is not active.
        """
        if not self._is_active:
            msg = "Unit of Work is not active. Use 'async with uow:' first."
            raise RuntimeError(msg)

        if name not in self._repositories:
            if repo_class is None:
                raise KeyError(f"Repository '{name}' not registered")
            self._repositories[name] = repo_class(self.session)

        return self._repositories[name]

    def register_repository(self, name: str, repository: Any) -> None:
        """Register an already-constructed repository instance.

        Parameters
        ----------
        name:
            Logical name for later lookup.
        repository:
            Pre-constructed repository instance.
        """
        self._repositories[name] = repository

    # ------------------------------------------------------------------
    # Transaction lifecycle
    # ------------------------------------------------------------------

    async def __aenter__(self) -> SqlAlchemyUnitOfWork:
        """Open a new session and start a transaction."""
        if self._session_factory is None:
            msg = "Session factory is not configured"
            raise RuntimeError(msg)

        self._session = self._session_factory()
        self._repositories.clear()
        self._is_active = True
        logger.debug("Unit of Work started")
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Close the session, rolling back on unhandled exceptions."""
        try:
            if exc_type is not None:
                await self.rollback()
        finally:
            if self._session is not None:
                await self._session.close()
            self._session = None
            self._repositories.clear()
            self._is_active = False
            logger.debug("Unit of Work closed")

    async def commit(self) -> None:
        """Flush pending changes and commit the transaction."""
        await self.session.commit()
        logger.debug("Unit of Work committed")

    async def rollback(self) -> None:
        """Roll back all pending changes."""
        await self.session.rollback()
        logger.debug("Unit of Work rolled back")

    # ------------------------------------------------------------------
    # Savepoint support
    # ------------------------------------------------------------------

    @asynccontextmanager
    async def begin_nested(self) -> AsyncGenerator[AsyncSession, None]:
        """Create a savepoint inside the current transaction.

        Usage::

            async with uow.begin_nested() as nested:
                # work that may fail
                ...

        If the body raises, only the savepoint is rolled back — the
        outer transaction remains intact.

        Yields
        ------
        AsyncSession
            The same session, now scoped to a savepoint.
        """
        async with self.session.begin_nested():
            yield self.session


__all__ = [
    "SqlAlchemyUnitOfWork",
]
