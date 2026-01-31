"""Metadata application service.

Orchestrates metadata operations using domain entities and repository interfaces.
"""

from __future__ import annotations

import logging
from typing import Any, Protocol
from uuid import UUID

from metastore_service.application.dtos.metadata_dtos import (
    CreateMetadataDTO,
    MetadataDTO,
    MetadataListDTO,
    MetadataVersionDTO,
    UpdateMetadataDTO,
)
from metastore_service.domain.entities.metadata import MetadataEntry
from metastore_service.domain.repositories.metadata_repository import IMetadataRepository
from metastore_service.domain.value_objects import MetadataKey, Namespace, TenantId

logger = logging.getLogger(__name__)


class ICacheService(Protocol):
    """Cache service interface for metadata caching."""

    async def get(self, key: str) -> Any | None: ...
    async def set(self, key: str, value: Any, ttl: int | None = None) -> None: ...
    async def delete(self, key: str) -> None: ...
    async def delete_pattern(self, pattern: str) -> None: ...


class MetadataService:
    """Application service for metadata operations.

    Handles business logic, validation, and orchestration between
    the domain layer and infrastructure concerns.
    """

    def __init__(
        self,
        repository: IMetadataRepository,
        cache: ICacheService | None = None,
        cache_ttl: int = 300,  # 5 minutes default
    ):
        """Initialize the metadata service.

        Args:
            repository: Metadata repository implementation
            cache: Optional cache service for hot data
            cache_ttl: Cache TTL in seconds
        """
        self._repository = repository
        self._cache = cache
        self._cache_ttl = cache_ttl

    def _cache_key(
        self,
        key: str,
        namespace: str | None = None,
        tenant_id: str | None = None,
    ) -> str:
        """Generate a cache key."""
        parts = ["metadata", key]
        if namespace:
            parts.append(namespace)
        if tenant_id:
            parts.append(tenant_id)
        return ":".join(parts)

    async def create(
        self,
        dto: CreateMetadataDTO,
        created_by: str | None = None,
    ) -> MetadataDTO:
        """Create a new metadata entry.

        Args:
            dto: Creation data
            created_by: User creating the entry

        Returns:
            The created metadata entry

        Raises:
            ValueError: If key already exists
        """
        # Check for duplicates
        existing = await self._repository.exists(
            key=dto.key,
            namespace=dto.namespace,
            tenant_id=dto.tenant_id,
        )
        if existing:
            raise ValueError(
                f"Metadata with key '{dto.key}' already exists in namespace '{dto.namespace}'"
            )

        # Create domain entity
        entry = MetadataEntry.create(
            key=dto.key,
            value=dto.value,
            namespace=dto.namespace,
            content_type=dto.content_type,
            tags=dto.tags,
            tenant_id=dto.tenant_id,
            is_encrypted=dto.is_encrypted,
            is_secret=dto.is_secret,
            description=dto.description,
            created_by=created_by,
        )

        # Persist
        created = await self._repository.create(entry)

        logger.info(
            "Created metadata entry",
            extra={
                "metadata_id": str(created.id),
                "key": dto.key,
                "namespace": dto.namespace,
                "created_by": created_by,
            },
        )

        return MetadataDTO.from_entity(created)

    async def get_by_id(self, metadata_id: UUID) -> MetadataDTO | None:
        """Get a metadata entry by ID.

        Args:
            metadata_id: The metadata ID

        Returns:
            The metadata entry or None if not found
        """
        entry = await self._repository.get_by_id(metadata_id)
        if entry is None:
            return None
        return MetadataDTO.from_entity(entry)

    async def get_by_key(
        self,
        key: str,
        namespace: str | None = None,
        tenant_id: str | None = None,
    ) -> MetadataDTO | None:
        """Get a metadata entry by key.

        Args:
            key: The metadata key
            namespace: Optional namespace
            tenant_id: Optional tenant ID

        Returns:
            The metadata entry or None if not found
        """
        # Try cache first
        if self._cache:
            cache_key = self._cache_key(key, namespace, tenant_id)
            cached = await self._cache.get(cache_key)
            if cached:
                return MetadataDTO(**cached)

        # Get from repository
        entry = await self._repository.get_by_key(
            key=key,
            namespace=namespace,
            tenant_id=tenant_id,
        )
        if entry is None:
            return None

        dto = MetadataDTO.from_entity(entry)

        # Cache result
        if self._cache:
            cache_key = self._cache_key(key, namespace, tenant_id)
            await self._cache.set(cache_key, dto.model_dump(), self._cache_ttl)

        return dto

    async def get_value(
        self,
        key: str,
        namespace: str | None = None,
        tenant_id: str | None = None,
        default: Any = None,
    ) -> Any:
        """Get just the value of a metadata entry.

        Convenience method for simple value retrieval.

        Args:
            key: The metadata key
            namespace: Optional namespace
            tenant_id: Optional tenant ID
            default: Default value if not found

        Returns:
            The metadata value or default
        """
        entry = await self.get_by_key(key, namespace, tenant_id)
        if entry is None:
            return default
        return entry.value

    async def update(
        self,
        metadata_id: UUID,
        dto: UpdateMetadataDTO,
        updated_by: str | None = None,
    ) -> MetadataDTO | None:
        """Update a metadata entry.

        Args:
            metadata_id: The metadata ID
            dto: Update data
            updated_by: User making the update

        Returns:
            The updated metadata entry or None if not found
        """
        entry = await self._repository.get_by_id(metadata_id)
        if entry is None:
            return None

        # Apply updates
        if dto.value is not None:
            entry.update_value(
                new_value=dto.value,
                updated_by=updated_by,
                change_reason=dto.change_reason,
            )

        if dto.tags is not None:
            # Replace tags
            entry.tags = []
            for tag in dto.tags:
                entry.add_tag(tag)

        if dto.description is not None:
            entry.description = dto.description

        if dto.is_encrypted is not None:
            entry.is_encrypted = dto.is_encrypted

        if dto.is_secret is not None:
            entry.is_secret = dto.is_secret

        # Persist
        updated = await self._repository.update(entry)

        # Invalidate cache
        if self._cache:
            cache_key = self._cache_key(
                entry.key.value,
                entry.namespace.value,
                entry.tenant_id.value if entry.tenant_id else None,
            )
            await self._cache.delete(cache_key)

        logger.info(
            "Updated metadata entry",
            extra={
                "metadata_id": str(metadata_id),
                "updated_by": updated_by,
                "change_reason": dto.change_reason,
            },
        )

        return MetadataDTO.from_entity(updated)

    async def delete(self, metadata_id: UUID) -> bool:
        """Delete a metadata entry.

        Args:
            metadata_id: The metadata ID

        Returns:
            True if deleted, False if not found
        """
        # Get entry first for cache invalidation
        entry = await self._repository.get_by_id(metadata_id)
        if entry is None:
            return False

        # Delete
        result = await self._repository.delete(metadata_id)

        # Invalidate cache
        if self._cache and result:
            cache_key = self._cache_key(
                entry.key.value,
                entry.namespace.value,
                entry.tenant_id.value if entry.tenant_id else None,
            )
            await self._cache.delete(cache_key)

        logger.info(
            "Deleted metadata entry",
            extra={"metadata_id": str(metadata_id)},
        )

        return result

    async def list_by_namespace(
        self,
        namespace: str,
        tenant_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> MetadataListDTO:
        """List metadata entries by namespace.

        Args:
            namespace: The namespace to filter by
            tenant_id: Optional tenant ID filter
            limit: Maximum results
            offset: Offset for pagination

        Returns:
            Paginated list of metadata entries
        """
        entries = await self._repository.list_by_namespace(
            namespace=namespace,
            tenant_id=tenant_id,
            limit=limit,
            offset=offset,
        )
        total = await self._repository.count(namespace=namespace, tenant_id=tenant_id)

        return MetadataListDTO.from_entities(entries, total, limit, offset)

    async def list_by_tags(
        self,
        tags: list[str],
        tenant_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> MetadataListDTO:
        """List metadata entries by tags.

        Args:
            tags: Tags to filter by (OR logic)
            tenant_id: Optional tenant ID filter
            limit: Maximum results
            offset: Offset for pagination

        Returns:
            Paginated list of metadata entries
        """
        entries = await self._repository.list_by_tags(
            tags=tags,
            tenant_id=tenant_id,
            limit=limit,
            offset=offset,
        )
        # Note: count might need a separate method for tags
        total = len(entries) if len(entries) < limit else limit + offset + 1

        return MetadataListDTO.from_entities(entries, total, limit, offset)

    async def search(
        self,
        query: str,
        namespace: str | None = None,
        tenant_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> MetadataListDTO:
        """Search metadata entries.

        Args:
            query: Search query
            namespace: Optional namespace filter
            tenant_id: Optional tenant ID filter
            limit: Maximum results
            offset: Offset for pagination

        Returns:
            Paginated list of matching entries
        """
        entries = await self._repository.search(
            query=query,
            namespace=namespace,
            tenant_id=tenant_id,
            limit=limit,
            offset=offset,
        )
        total = len(entries) if len(entries) < limit else limit + offset + 1

        return MetadataListDTO.from_entities(entries, total, limit, offset)

    async def get_versions(
        self,
        metadata_id: UUID,
        limit: int = 50,
    ) -> list[MetadataVersionDTO]:
        """Get version history for a metadata entry.

        Args:
            metadata_id: The metadata ID
            limit: Maximum versions to return

        Returns:
            List of versions (newest first)
        """
        versions = await self._repository.get_versions(metadata_id, limit)
        return [
            MetadataVersionDTO(
                id=v.id,
                version_number=v.version_number,
                value=v.value.raw_value,
                created_at=v.created_at,
                created_by=v.created_by,
                change_reason=v.change_reason,
            )
            for v in versions
        ]

    async def rollback_to_version(
        self,
        metadata_id: UUID,
        version_number: int,
        rolled_back_by: str | None = None,
    ) -> MetadataDTO | None:
        """Rollback a metadata entry to a previous version.

        Args:
            metadata_id: The metadata ID
            version_number: The version to rollback to
            rolled_back_by: User performing the rollback

        Returns:
            The updated metadata entry or None if not found
        """
        entry = await self._repository.get_by_id(metadata_id)
        if entry is None:
            return None

        # Rollback (creates new version)
        entry.rollback_to_version(version_number, rolled_back_by)

        # Persist
        updated = await self._repository.update(entry)

        # Invalidate cache
        if self._cache:
            cache_key = self._cache_key(
                entry.key.value,
                entry.namespace.value,
                entry.tenant_id.value if entry.tenant_id else None,
            )
            await self._cache.delete(cache_key)

        logger.info(
            "Rolled back metadata entry",
            extra={
                "metadata_id": str(metadata_id),
                "to_version": version_number,
                "rolled_back_by": rolled_back_by,
            },
        )

        return MetadataDTO.from_entity(updated)

    async def bulk_get(
        self,
        keys: list[tuple[str, str | None, str | None]],
    ) -> dict[str, MetadataDTO | None]:
        """Bulk get metadata entries.

        Args:
            keys: List of (key, namespace, tenant_id) tuples

        Returns:
            Dictionary mapping key to DTO (or None if not found)
        """
        result = await self._repository.bulk_get(keys)
        return {
            key: MetadataDTO.from_entity(entry) if entry else None
            for key, entry in result.items()
        }
