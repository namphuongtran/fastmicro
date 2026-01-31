"""User repository interface - defines data access contract for users."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from identity_service.domain.entities import User


class UserRepository(ABC):
    """Abstract repository for User aggregate persistence.

    Defines the contract for user data access. Implementations should
    handle database-specific details.
    """

    @abstractmethod
    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        """Get user by their unique identifier.

        Args:
            user_id: User's UUID

        Returns:
            User entity if found, None otherwise.
        """

    @abstractmethod
    async def get_by_email(self, email: str) -> User | None:
        """Get user by email address.

        Args:
            email: User's email address (case-insensitive)

        Returns:
            User entity if found, None otherwise.
        """

    @abstractmethod
    async def get_by_username(self, username: str) -> User | None:
        """Get user by username.

        Args:
            username: User's username (case-insensitive)

        Returns:
            User entity if found, None otherwise.
        """

    @abstractmethod
    async def get_by_external_id(
        self, external_id: str, provider: str
    ) -> User | None:
        """Get user by external identity provider ID.

        Args:
            external_id: ID from external provider (e.g., Google, Azure AD)
            provider: Name of the external provider

        Returns:
            User entity if found, None otherwise.
        """

    @abstractmethod
    async def create(self, user: User) -> User:
        """Create a new user.

        Args:
            user: User entity to persist

        Returns:
            Created user with generated ID.

        Raises:
            DuplicateEntityError: If user with same email/username exists.
        """

    @abstractmethod
    async def update(self, user: User) -> User:
        """Update an existing user.

        Args:
            user: User entity with updated values

        Returns:
            Updated user entity.

        Raises:
            EntityNotFoundError: If user doesn't exist.
        """

    @abstractmethod
    async def delete(self, user_id: uuid.UUID) -> bool:
        """Soft delete a user (set is_active=False).

        Args:
            user_id: User's UUID

        Returns:
            True if user was deleted, False if not found.
        """

    @abstractmethod
    async def exists_by_email(self, email: str) -> bool:
        """Check if user with given email exists.

        Args:
            email: Email address to check

        Returns:
            True if user exists.
        """

    @abstractmethod
    async def exists_by_username(self, username: str) -> bool:
        """Check if user with given username exists.

        Args:
            username: Username to check

        Returns:
            True if user exists.
        """

    @abstractmethod
    async def find_by_role(
        self, role_name: str, skip: int = 0, limit: int = 100
    ) -> list[User]:
        """Find users with a specific role.

        Args:
            role_name: Name of the role
            skip: Number of records to skip
            limit: Maximum records to return

        Returns:
            List of users with the specified role.
        """

    @abstractmethod
    async def count(self, include_inactive: bool = False) -> int:
        """Count total users.

        Args:
            include_inactive: Whether to include inactive users

        Returns:
            Total user count.
        """

    @abstractmethod
    async def search(
        self,
        query: str,
        skip: int = 0,
        limit: int = 100,
        include_inactive: bool = False,
    ) -> list[User]:
        """Search users by email or username.

        Args:
            query: Search query (partial match)
            skip: Number of records to skip
            limit: Maximum records to return
            include_inactive: Whether to include inactive users

        Returns:
            List of matching users.
        """
