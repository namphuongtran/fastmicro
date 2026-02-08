"""Abstract repository interface for User aggregate."""

from __future__ import annotations

from abc import ABC, abstractmethod

from user_service.domain.entities.user import User


class UserRepository(ABC):
    """Port for User persistence.

    Defines the contract that infrastructure-layer repository
    implementations must fulfill.
    """

    @abstractmethod
    async def get_by_id(self, user_id: str) -> User | None:
        """Find a user by ID.

        Args:
            user_id: Unique user identifier.

        Returns:
            User aggregate or None if not found.
        """
        ...

    @abstractmethod
    async def get_by_email(self, email: str) -> User | None:
        """Find a user by email address.

        Args:
            email: Email address.

        Returns:
            User aggregate or None if not found.
        """
        ...

    @abstractmethod
    async def list_by_tenant(
        self,
        tenant_id: str,
        *,
        offset: int = 0,
        limit: int = 20,
    ) -> list[User]:
        """List users belonging to a tenant.

        Args:
            tenant_id: Tenant identifier.
            offset: Pagination offset.
            limit: Page size.

        Returns:
            List of User aggregates.
        """
        ...

    @abstractmethod
    async def add(self, user: User) -> None:
        """Persist a new user.

        Args:
            user: User aggregate to persist.
        """
        ...

    @abstractmethod
    async def update(self, user: User) -> None:
        """Update an existing user.

        Args:
            user: User aggregate with updated state.
        """
        ...

    @abstractmethod
    async def delete(self, user_id: str) -> None:
        """Delete a user by ID.

        Args:
            user_id: Unique user identifier.
        """
        ...

    @abstractmethod
    async def exists_by_email(self, email: str) -> bool:
        """Check if a user with the given email exists.

        Args:
            email: Email address.

        Returns:
            True if a user exists with this email.
        """
        ...
