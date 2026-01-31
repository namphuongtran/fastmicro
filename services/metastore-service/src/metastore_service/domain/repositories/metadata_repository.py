"""Abstract repository interface for MetadataEntry aggregate.

Defines the contract for metadata persistence operations.
"""

from abc import ABC, abstractmethod
from typing import Protocol
from uuid import UUID

from metastore_service.domain.entities.metadata import MetadataEntry, MetadataVersion
from metastore_service.domain.value_objects import MetadataKey, Namespace, TenantId


class IMetadataRepository(ABC):
    """Abstract repository interface for MetadataEntry persistence.

    All implementations must support async operations for scalability.
    """

    @abstractmethod
    async def get_by_id(self, metadata_id: UUID) -> MetadataEntry | None:
        """Get a metadata entry by ID.

        Args:
            metadata_id: The unique identifier

        Returns:
            The metadata entry if found, None otherwise
        """
        ...

    @abstractmethod
    async def get_by_key(
        self,
        key: MetadataKey | str,
        namespace: Namespace | str | None = None,
        tenant_id: TenantId | str | None = None,
    ) -> MetadataEntry | None:
        """Get a metadata entry by key, namespace, and tenant.

        Args:
            key: The metadata key
            namespace: Optional namespace (defaults to 'default')
            tenant_id: Optional tenant ID

        Returns:
            The metadata entry if found, None otherwise
        """
        ...

    @abstractmethod
    async def list_by_namespace(
        self,
        namespace: Namespace | str,
        tenant_id: TenantId | str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[MetadataEntry]:
        """List all metadata entries in a namespace.

        Args:
            namespace: The namespace to filter by
            tenant_id: Optional tenant ID filter
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of metadata entries
        """
        ...

    @abstractmethod
    async def list_by_tags(
        self,
        tags: list[str],
        tenant_id: TenantId | str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[MetadataEntry]:
        """List all metadata entries with any of the given tags.

        Args:
            tags: Tags to filter by (OR logic)
            tenant_id: Optional tenant ID filter
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of metadata entries
        """
        ...

    @abstractmethod
    async def search(
        self,
        query: str,
        namespace: Namespace | str | None = None,
        tenant_id: TenantId | str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[MetadataEntry]:
        """Search metadata entries by key pattern or description.

        Args:
            query: Search query (supports wildcards)
            namespace: Optional namespace filter
            tenant_id: Optional tenant ID filter
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of matching metadata entries
        """
        ...

    @abstractmethod
    async def create(self, entry: MetadataEntry) -> MetadataEntry:
        """Create a new metadata entry.

        Args:
            entry: The metadata entry to create

        Returns:
            The created metadata entry with ID populated

        Raises:
            DuplicateKeyError: If key already exists in namespace/tenant
        """
        ...

    @abstractmethod
    async def update(self, entry: MetadataEntry) -> MetadataEntry:
        """Update an existing metadata entry.

        Args:
            entry: The metadata entry to update

        Returns:
            The updated metadata entry

        Raises:
            NotFoundError: If the entry doesn't exist
        """
        ...

    @abstractmethod
    async def delete(self, metadata_id: UUID) -> bool:
        """Delete a metadata entry by ID.

        Args:
            metadata_id: The unique identifier

        Returns:
            True if deleted, False if not found
        """
        ...

    @abstractmethod
    async def get_versions(
        self,
        metadata_id: UUID,
        limit: int = 50,
    ) -> list[MetadataVersion]:
        """Get version history for a metadata entry.

        Args:
            metadata_id: The metadata entry ID
            limit: Maximum number of versions to return

        Returns:
            List of versions (newest first)
        """
        ...

    @abstractmethod
    async def get_version(
        self,
        metadata_id: UUID,
        version_number: int,
    ) -> MetadataVersion | None:
        """Get a specific version of a metadata entry.

        Args:
            metadata_id: The metadata entry ID
            version_number: The version number to retrieve

        Returns:
            The version if found, None otherwise
        """
        ...

    @abstractmethod
    async def count(
        self,
        namespace: Namespace | str | None = None,
        tenant_id: TenantId | str | None = None,
    ) -> int:
        """Count metadata entries.

        Args:
            namespace: Optional namespace filter
            tenant_id: Optional tenant ID filter

        Returns:
            The count of matching entries
        """
        ...

    @abstractmethod
    async def exists(
        self,
        key: MetadataKey | str,
        namespace: Namespace | str | None = None,
        tenant_id: TenantId | str | None = None,
    ) -> bool:
        """Check if a metadata entry exists.

        Args:
            key: The metadata key
            namespace: Optional namespace
            tenant_id: Optional tenant ID

        Returns:
            True if exists, False otherwise
        """
        ...

    @abstractmethod
    async def bulk_get(
        self,
        keys: list[tuple[str, str | None, str | None]],
    ) -> dict[str, MetadataEntry | None]:
        """Bulk get metadata entries by keys.

        Args:
            keys: List of (key, namespace, tenant_id) tuples

        Returns:
            Dictionary mapping key to entry (or None if not found)
        """
        ...

    @abstractmethod
    async def bulk_create(
        self,
        entries: list[MetadataEntry],
    ) -> list[MetadataEntry]:
        """Bulk create metadata entries.

        Args:
            entries: List of entries to create

        Returns:
            List of created entries
        """
        ...
