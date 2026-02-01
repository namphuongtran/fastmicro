"""Unit of Work pattern implementation.

This module provides the Unit of Work pattern for coordinating
multiple repository operations within a single transaction.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, TypeVar

from shared.dbs.repository import AbstractRepository

T = TypeVar("T")


class AbstractUnitOfWork(ABC):
    """Abstract Unit of Work interface.

    Defines the transaction boundaries and repository coordination.
    """

    @abstractmethod
    async def __aenter__(self) -> AbstractUnitOfWork:
        """Enter the unit of work context."""
        ...

    @abstractmethod
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Exit the unit of work context."""
        ...

    @abstractmethod
    async def commit(self) -> None:
        """Commit the transaction."""
        ...

    @abstractmethod
    async def rollback(self) -> None:
        """Rollback the transaction."""
        ...


class InMemoryUnitOfWork(AbstractUnitOfWork):
    """In-memory Unit of Work implementation.

    Useful for testing and prototyping.
    """

    def __init__(self) -> None:
        """Initialize the unit of work."""
        self._repositories: dict[str, AbstractRepository[Any]] = {}
        self._is_active = False

    @property
    def is_active(self) -> bool:
        """Check if the unit of work is active.

        Returns:
            True if within a transaction context.
        """
        return self._is_active

    def register_repository(
        self,
        name: str,
        repository: AbstractRepository[Any],
    ) -> None:
        """Register a repository with this unit of work.

        Args:
            name: Repository name for lookup.
            repository: The repository instance.
        """
        self._repositories[name] = repository

    def get_repository(self, name: str) -> AbstractRepository[Any]:
        """Get a registered repository by name.

        Args:
            name: Repository name.

        Returns:
            The repository instance.

        Raises:
            KeyError: If repository not found.
        """
        if name not in self._repositories:
            raise KeyError(f"Repository '{name}' not registered")
        return self._repositories[name]

    async def __aenter__(self) -> InMemoryUnitOfWork:
        """Enter the unit of work context."""
        self._is_active = True
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Exit the unit of work context."""
        if exc_type is not None:
            await self.rollback()
        self._is_active = False

    async def commit(self) -> None:
        """Commit the transaction.

        For in-memory implementation, this is a no-op since
        changes are applied immediately.
        """
        pass

    async def rollback(self) -> None:
        """Rollback the transaction.

        For in-memory implementation, this is a no-op.
        A real implementation would restore previous state.
        """
        pass


__all__ = [
    "AbstractUnitOfWork",
    "InMemoryUnitOfWork",
]
