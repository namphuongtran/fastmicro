"""Client repository interface - defines data access contract for OAuth2 clients."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from identity_service.domain.entities import Client


class ClientRepository(ABC):
    """Abstract repository for Client aggregate persistence.

    Defines the contract for OAuth2 client data access.
    """

    @abstractmethod
    async def get_by_id(self, client_id: uuid.UUID) -> Client | None:
        """Get client by internal UUID.

        Args:
            client_id: Client's internal UUID

        Returns:
            Client entity if found, None otherwise.
        """

    @abstractmethod
    async def get_by_client_id(self, client_id: str) -> Client | None:
        """Get client by OAuth2 client_id string.

        Args:
            client_id: OAuth2 client_id (public identifier)

        Returns:
            Client entity if found, None otherwise.
        """

    @abstractmethod
    async def create(self, client: Client) -> Client:
        """Create a new OAuth2 client.

        Args:
            client: Client entity to persist

        Returns:
            Created client with generated ID.

        Raises:
            DuplicateEntityError: If client with same client_id exists.
        """

    @abstractmethod
    async def update(self, client: Client) -> Client:
        """Update an existing client.

        Args:
            client: Client entity with updated values

        Returns:
            Updated client entity.

        Raises:
            EntityNotFoundError: If client doesn't exist.
        """

    @abstractmethod
    async def delete(self, client_id: uuid.UUID) -> bool:
        """Soft delete a client (set is_active=False).

        Args:
            client_id: Client's internal UUID

        Returns:
            True if client was deleted, False if not found.
        """

    @abstractmethod
    async def exists_by_client_id(self, client_id: str) -> bool:
        """Check if client with given client_id exists.

        Args:
            client_id: OAuth2 client_id to check

        Returns:
            True if client exists.
        """

    @abstractmethod
    async def list_active(self, skip: int = 0, limit: int = 100) -> list[Client]:
        """List all active clients.

        Args:
            skip: Number of records to skip
            limit: Maximum records to return

        Returns:
            List of active clients.
        """

    @abstractmethod
    async def list_by_owner(
        self, owner_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> list[Client]:
        """List clients created by a specific user.

        Args:
            owner_id: UUID of the client owner
            skip: Number of records to skip
            limit: Maximum records to return

        Returns:
            List of clients owned by the user.
        """

    @abstractmethod
    async def count(self, include_inactive: bool = False) -> int:
        """Count total clients.

        Args:
            include_inactive: Whether to include inactive clients

        Returns:
            Total client count.
        """

    @abstractmethod
    async def search(
        self,
        query: str,
        skip: int = 0,
        limit: int = 100,
        include_inactive: bool = False,
    ) -> list[Client]:
        """Search clients by name or client_id.

        Args:
            query: Search query (partial match)
            skip: Number of records to skip
            limit: Maximum records to return
            include_inactive: Whether to include inactive clients

        Returns:
            List of matching clients.
        """
