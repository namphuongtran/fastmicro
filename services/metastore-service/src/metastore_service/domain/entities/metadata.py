"""Metadata aggregate - Core domain entity for metadata storage.

The MetadataEntry is an aggregate root that manages metadata with versioning,
multi-tenancy support, and content type awareness.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from metastore_service.domain.value_objects import (
    ContentType,
    MetadataKey,
    MetadataValue,
    Namespace,
    Tag,
    TenantId,
)


@dataclass
class MetadataVersion:
    """Represents a historical version of metadata.

    Maintains an audit trail of all changes to metadata values.
    """

    id: UUID
    metadata_id: UUID
    version_number: int
    value: MetadataValue
    created_at: datetime
    created_by: str | None = None
    change_reason: str | None = None

    @classmethod
    def create(
        cls,
        metadata_id: UUID,
        version_number: int,
        value: MetadataValue,
        created_by: str | None = None,
        change_reason: str | None = None,
    ) -> MetadataVersion:
        """Create a new metadata version."""
        return cls(
            id=uuid4(),
            metadata_id=metadata_id,
            version_number=version_number,
            value=value,
            created_at=datetime.now(timezone.utc),
            created_by=created_by,
            change_reason=change_reason,
        )


@dataclass
class MetadataEntry:
    """Aggregate root for metadata management.

    Represents a single piece of metadata with full version history,
    namespace organization, and multi-tenancy support.

    Attributes:
        id: Unique identifier for the metadata entry
        key: The metadata key (unique within namespace/tenant)
        namespace: Logical grouping for related metadata
        current_value: The current metadata value
        content_type: The type of content stored
        tags: List of tags for categorization
        tenant_id: Optional tenant for multi-tenancy
        is_encrypted: Whether the value is encrypted at rest
        is_secret: Whether this is sensitive data
        description: Human-readable description
        versions: History of all value changes
        created_at: When the entry was created
        updated_at: When the entry was last modified
        created_by: User who created the entry
        updated_by: User who last modified the entry
    """

    id: UUID
    key: MetadataKey
    namespace: Namespace
    current_value: MetadataValue
    content_type: ContentType = ContentType.JSON
    tags: list[Tag] = field(default_factory=list)
    tenant_id: TenantId | None = None
    is_encrypted: bool = False
    is_secret: bool = False
    description: str | None = None
    versions: list[MetadataVersion] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str | None = None
    updated_by: str | None = None

    @classmethod
    def create(
        cls,
        key: str | MetadataKey,
        value: Any,
        namespace: str | Namespace | None = None,
        content_type: ContentType = ContentType.JSON,
        tags: list[str] | None = None,
        tenant_id: str | TenantId | None = None,
        is_encrypted: bool = False,
        is_secret: bool = False,
        description: str | None = None,
        created_by: str | None = None,
    ) -> MetadataEntry:
        """Create a new metadata entry.

        Args:
            key: The metadata key
            value: The metadata value (any JSON-serializable type)
            namespace: Optional namespace (defaults to 'default')
            content_type: The content type of the value
            tags: Optional list of tags
            tenant_id: Optional tenant ID for multi-tenancy
            is_encrypted: Whether to encrypt the value at rest
            is_secret: Whether this is sensitive data
            description: Human-readable description
            created_by: User creating the entry

        Returns:
            A new MetadataEntry instance
        """
        # Convert to value objects if needed
        key_vo = key if isinstance(key, MetadataKey) else MetadataKey(key)
        namespace_vo = (
            namespace
            if isinstance(namespace, Namespace)
            else Namespace(namespace or Namespace.DEFAULT)
        )
        tenant_vo = (
            tenant_id
            if isinstance(tenant_id, TenantId) or tenant_id is None
            else TenantId(tenant_id)
        )
        tag_vos = [Tag(t) if isinstance(t, str) else t for t in (tags or [])]
        value_vo = MetadataValue(raw_value=value, content_type=content_type)

        entry_id = uuid4()
        now = datetime.now(timezone.utc)

        # Create initial version
        initial_version = MetadataVersion.create(
            metadata_id=entry_id,
            version_number=1,
            value=value_vo,
            created_by=created_by,
            change_reason="Initial creation",
        )

        return cls(
            id=entry_id,
            key=key_vo,
            namespace=namespace_vo,
            current_value=value_vo,
            content_type=content_type,
            tags=tag_vos,
            tenant_id=tenant_vo,
            is_encrypted=is_encrypted,
            is_secret=is_secret,
            description=description,
            versions=[initial_version],
            created_at=now,
            updated_at=now,
            created_by=created_by,
            updated_by=created_by,
        )

    def update_value(
        self,
        new_value: Any,
        updated_by: str | None = None,
        change_reason: str | None = None,
    ) -> None:
        """Update the metadata value, creating a new version.

        Args:
            new_value: The new value to set
            updated_by: User making the change
            change_reason: Reason for the change (for audit)
        """
        # Create new value object
        new_value_vo = MetadataValue(raw_value=new_value, content_type=self.content_type)

        # Create new version
        new_version = MetadataVersion.create(
            metadata_id=self.id,
            version_number=self.current_version_number + 1,
            value=new_value_vo,
            created_by=updated_by,
            change_reason=change_reason,
        )

        self.versions.append(new_version)
        self.current_value = new_value_vo
        self.updated_at = datetime.now(timezone.utc)
        self.updated_by = updated_by

    def add_tag(self, tag: str | Tag) -> None:
        """Add a tag to the metadata entry."""
        tag_vo = tag if isinstance(tag, Tag) else Tag(tag)
        if tag_vo not in self.tags:
            self.tags.append(tag_vo)
            self.updated_at = datetime.now(timezone.utc)

    def remove_tag(self, tag: str | Tag) -> None:
        """Remove a tag from the metadata entry."""
        tag_vo = tag if isinstance(tag, Tag) else Tag(tag)
        if tag_vo in self.tags:
            self.tags.remove(tag_vo)
            self.updated_at = datetime.now(timezone.utc)

    def rollback_to_version(
        self,
        version_number: int,
        rolled_back_by: str | None = None,
    ) -> None:
        """Rollback to a previous version.

        This creates a new version with the old value, maintaining history.

        Args:
            version_number: The version number to rollback to
            rolled_back_by: User performing the rollback
        """
        target_version = self.get_version(version_number)
        if target_version is None:
            raise ValueError(f"Version {version_number} not found")

        self.update_value(
            new_value=target_version.value.raw_value,
            updated_by=rolled_back_by,
            change_reason=f"Rollback to version {version_number}",
        )

    def get_version(self, version_number: int) -> MetadataVersion | None:
        """Get a specific version by number."""
        for version in self.versions:
            if version.version_number == version_number:
                return version
        return None

    @property
    def current_version_number(self) -> int:
        """Get the current version number."""
        if not self.versions:
            return 0
        return max(v.version_number for v in self.versions)

    @property
    def fully_qualified_key(self) -> str:
        """Get the fully qualified key including namespace."""
        return f"{self.namespace.value}:{self.key.value}"

    @property
    def version_count(self) -> int:
        """Get the number of versions."""
        return len(self.versions)

    def has_tag(self, tag: str | Tag) -> bool:
        """Check if the entry has a specific tag."""
        tag_vo = tag if isinstance(tag, Tag) else Tag(tag)
        return tag_vo in self.tags

    def matches_namespace(self, namespace_pattern: str) -> bool:
        """Check if the entry matches a namespace pattern.

        Supports wildcard matching with '*'.
        """
        import fnmatch

        return fnmatch.fnmatch(self.namespace.value, namespace_pattern)
