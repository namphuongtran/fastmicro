"""PostgreSQL repository implementation for MetadataEntry aggregate."""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from metastore_service.domain.entities.metadata import MetadataEntry, MetadataVersion
from metastore_service.domain.repositories.metadata_repository import IMetadataRepository
from metastore_service.domain.value_objects import (
    ContentType,
    MetadataKey,
    MetadataValue,
    Namespace,
    Tag,
    TenantId,
)
from metastore_service.infrastructure.database.models import (
    MetadataEntryModel,
    MetadataVersionModel,
)

logger = logging.getLogger(__name__)


class PostgresMetadataRepository(IMetadataRepository):
    """PostgreSQL implementation of the metadata repository."""

    def __init__(self, session: AsyncSession):
        """Initialize the repository.

        Args:
            session: Async SQLAlchemy session
        """
        self._session = session

    def _to_domain(self, model: MetadataEntryModel) -> MetadataEntry:
        """Convert database model to domain entity."""
        versions = [
            MetadataVersion(
                id=v.id,
                metadata_id=v.metadata_id,
                version_number=v.version_number,
                value=MetadataValue(
                    raw_value=v.value.get("value"),
                    content_type=model.content_type,
                ),
                created_at=v.created_at,
                created_by=v.created_by,
                change_reason=v.change_reason,
            )
            for v in (model.versions or [])
        ]

        return MetadataEntry(
            id=model.id,
            key=MetadataKey(model.key),
            namespace=Namespace(model.namespace),
            current_value=MetadataValue(
                raw_value=model.current_value.get("value"),
                content_type=model.content_type,
            ),
            content_type=model.content_type,
            tags=[Tag(t) for t in (model.tags or [])],
            tenant_id=TenantId(model.tenant_id) if model.tenant_id else None,
            is_encrypted=model.is_encrypted,
            is_secret=model.is_secret,
            description=model.description,
            versions=versions,
            created_at=model.created_at,
            updated_at=model.updated_at,
            created_by=model.created_by,
            updated_by=model.updated_by,
        )

    def _to_model(self, entity: MetadataEntry) -> MetadataEntryModel:
        """Convert domain entity to database model."""
        return MetadataEntryModel(
            id=entity.id,
            key=entity.key.value,
            namespace=entity.namespace.value,
            current_value={"value": entity.current_value.raw_value},
            content_type=entity.content_type,
            tags=[t.value for t in entity.tags],
            tenant_id=entity.tenant_id.value if entity.tenant_id else None,
            is_encrypted=entity.is_encrypted,
            is_secret=entity.is_secret,
            description=entity.description,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            created_by=entity.created_by,
            updated_by=entity.updated_by,
        )

    async def get_by_id(self, metadata_id: UUID) -> MetadataEntry | None:
        """Get a metadata entry by ID."""
        query = (
            select(MetadataEntryModel)
            .options(selectinload(MetadataEntryModel.versions))
            .where(MetadataEntryModel.id == metadata_id)
        )
        result = await self._session.execute(query)
        model = result.scalar_one_or_none()

        if model is None:
            return None

        return self._to_domain(model)

    async def get_by_key(
        self,
        key: MetadataKey | str,
        namespace: Namespace | str | None = None,
        tenant_id: TenantId | str | None = None,
    ) -> MetadataEntry | None:
        """Get a metadata entry by key, namespace, and tenant."""
        key_str = key.value if isinstance(key, MetadataKey) else key
        namespace_str = (
            namespace.value if isinstance(namespace, Namespace) else (namespace or "default")
        )
        tenant_str = tenant_id.value if isinstance(tenant_id, TenantId) else tenant_id

        conditions = [
            MetadataEntryModel.key == key_str,
            MetadataEntryModel.namespace == namespace_str,
        ]

        if tenant_str:
            conditions.append(MetadataEntryModel.tenant_id == tenant_str)
        else:
            conditions.append(MetadataEntryModel.tenant_id.is_(None))

        query = (
            select(MetadataEntryModel)
            .options(selectinload(MetadataEntryModel.versions))
            .where(and_(*conditions))
        )
        result = await self._session.execute(query)
        model = result.scalar_one_or_none()

        if model is None:
            return None

        return self._to_domain(model)

    async def list_by_namespace(
        self,
        namespace: Namespace | str,
        tenant_id: TenantId | str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[MetadataEntry]:
        """List all metadata entries in a namespace."""
        namespace_str = namespace.value if isinstance(namespace, Namespace) else namespace
        tenant_str = tenant_id.value if isinstance(tenant_id, TenantId) else tenant_id

        conditions = [MetadataEntryModel.namespace == namespace_str]
        if tenant_str:
            conditions.append(MetadataEntryModel.tenant_id == tenant_str)

        query = (
            select(MetadataEntryModel)
            .options(selectinload(MetadataEntryModel.versions))
            .where(and_(*conditions))
            .order_by(MetadataEntryModel.key)
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(query)
        models = result.scalars().all()

        return [self._to_domain(m) for m in models]

    async def list_by_tags(
        self,
        tags: list[str],
        tenant_id: TenantId | str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[MetadataEntry]:
        """List all metadata entries with any of the given tags."""
        tenant_str = tenant_id.value if isinstance(tenant_id, TenantId) else tenant_id

        conditions = [MetadataEntryModel.tags.overlap(tags)]
        if tenant_str:
            conditions.append(MetadataEntryModel.tenant_id == tenant_str)

        query = (
            select(MetadataEntryModel)
            .options(selectinload(MetadataEntryModel.versions))
            .where(and_(*conditions))
            .order_by(MetadataEntryModel.key)
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(query)
        models = result.scalars().all()

        return [self._to_domain(m) for m in models]

    async def search(
        self,
        query: str,
        namespace: Namespace | str | None = None,
        tenant_id: TenantId | str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[MetadataEntry]:
        """Search metadata entries by key pattern or description."""
        # Convert wildcards to SQL LIKE pattern
        pattern = query.replace("*", "%").replace("?", "_")

        conditions = [
            or_(
                MetadataEntryModel.key.ilike(f"%{pattern}%"),
                MetadataEntryModel.description.ilike(f"%{pattern}%"),
            )
        ]

        if namespace:
            namespace_str = namespace.value if isinstance(namespace, Namespace) else namespace
            conditions.append(MetadataEntryModel.namespace == namespace_str)

        if tenant_id:
            tenant_str = tenant_id.value if isinstance(tenant_id, TenantId) else tenant_id
            conditions.append(MetadataEntryModel.tenant_id == tenant_str)

        stmt = (
            select(MetadataEntryModel)
            .options(selectinload(MetadataEntryModel.versions))
            .where(and_(*conditions))
            .order_by(MetadataEntryModel.key)
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._to_domain(m) for m in models]

    async def create(self, entry: MetadataEntry) -> MetadataEntry:
        """Create a new metadata entry."""
        model = self._to_model(entry)

        # Add versions
        for v in entry.versions:
            version_model = MetadataVersionModel(
                id=v.id,
                metadata_id=entry.id,
                version_number=v.version_number,
                value={"value": v.value.raw_value},
                created_at=v.created_at,
                created_by=v.created_by,
                change_reason=v.change_reason,
            )
            model.versions.append(version_model)

        self._session.add(model)
        await self._session.flush()

        logger.debug(f"Created metadata entry: {entry.id}")
        return entry

    async def update(self, entry: MetadataEntry) -> MetadataEntry:
        """Update an existing metadata entry."""
        # Get existing model
        query = (
            select(MetadataEntryModel)
            .options(selectinload(MetadataEntryModel.versions))
            .where(MetadataEntryModel.id == entry.id)
        )
        result = await self._session.execute(query)
        model = result.scalar_one_or_none()

        if model is None:
            raise ValueError(f"Metadata entry {entry.id} not found")

        # Update model attributes
        model.key = entry.key.value
        model.namespace = entry.namespace.value
        model.current_value = {"value": entry.current_value.raw_value}
        model.content_type = entry.content_type
        model.tags = [t.value for t in entry.tags]
        model.tenant_id = entry.tenant_id.value if entry.tenant_id else None
        model.is_encrypted = entry.is_encrypted
        model.is_secret = entry.is_secret
        model.description = entry.description
        model.updated_at = entry.updated_at
        model.updated_by = entry.updated_by

        # Add new versions
        existing_version_ids = {v.id for v in model.versions}
        for v in entry.versions:
            if v.id not in existing_version_ids:
                version_model = MetadataVersionModel(
                    id=v.id,
                    metadata_id=entry.id,
                    version_number=v.version_number,
                    value={"value": v.value.raw_value},
                    created_at=v.created_at,
                    created_by=v.created_by,
                    change_reason=v.change_reason,
                )
                model.versions.append(version_model)

        await self._session.flush()

        logger.debug(f"Updated metadata entry: {entry.id}")
        return entry

    async def delete(self, metadata_id: UUID) -> bool:
        """Delete a metadata entry by ID."""
        stmt = delete(MetadataEntryModel).where(MetadataEntryModel.id == metadata_id)
        result = await self._session.execute(stmt)
        await self._session.flush()

        deleted = result.rowcount > 0
        if deleted:
            logger.debug(f"Deleted metadata entry: {metadata_id}")
        return deleted

    async def get_versions(
        self,
        metadata_id: UUID,
        limit: int = 50,
    ) -> list[MetadataVersion]:
        """Get version history for a metadata entry."""
        query = (
            select(MetadataVersionModel)
            .where(MetadataVersionModel.metadata_id == metadata_id)
            .order_by(MetadataVersionModel.version_number.desc())
            .limit(limit)
        )
        result = await self._session.execute(query)
        models = result.scalars().all()

        # Get content type from parent
        entry = await self.get_by_id(metadata_id)
        content_type = entry.content_type if entry else ContentType.JSON

        return [
            MetadataVersion(
                id=m.id,
                metadata_id=m.metadata_id,
                version_number=m.version_number,
                value=MetadataValue(raw_value=m.value.get("value"), content_type=content_type),
                created_at=m.created_at,
                created_by=m.created_by,
                change_reason=m.change_reason,
            )
            for m in models
        ]

    async def get_version(
        self,
        metadata_id: UUID,
        version_number: int,
    ) -> MetadataVersion | None:
        """Get a specific version of a metadata entry."""
        query = select(MetadataVersionModel).where(
            and_(
                MetadataVersionModel.metadata_id == metadata_id,
                MetadataVersionModel.version_number == version_number,
            )
        )
        result = await self._session.execute(query)
        model = result.scalar_one_or_none()

        if model is None:
            return None

        # Get content type from parent
        entry = await self.get_by_id(metadata_id)
        content_type = entry.content_type if entry else ContentType.JSON

        return MetadataVersion(
            id=model.id,
            metadata_id=model.metadata_id,
            version_number=model.version_number,
            value=MetadataValue(raw_value=model.value.get("value"), content_type=content_type),
            created_at=model.created_at,
            created_by=model.created_by,
            change_reason=model.change_reason,
        )

    async def count(
        self,
        namespace: Namespace | str | None = None,
        tenant_id: TenantId | str | None = None,
    ) -> int:
        """Count metadata entries."""
        conditions = []

        if namespace:
            namespace_str = namespace.value if isinstance(namespace, Namespace) else namespace
            conditions.append(MetadataEntryModel.namespace == namespace_str)

        if tenant_id:
            tenant_str = tenant_id.value if isinstance(tenant_id, TenantId) else tenant_id
            conditions.append(MetadataEntryModel.tenant_id == tenant_str)

        query = select(func.count(MetadataEntryModel.id))
        if conditions:
            query = query.where(and_(*conditions))

        result = await self._session.execute(query)
        return result.scalar_one()

    async def exists(
        self,
        key: MetadataKey | str,
        namespace: Namespace | str | None = None,
        tenant_id: TenantId | str | None = None,
    ) -> bool:
        """Check if a metadata entry exists."""
        key_str = key.value if isinstance(key, MetadataKey) else key
        namespace_str = (
            namespace.value if isinstance(namespace, Namespace) else (namespace or "default")
        )
        tenant_str = tenant_id.value if isinstance(tenant_id, TenantId) else tenant_id

        conditions = [
            MetadataEntryModel.key == key_str,
            MetadataEntryModel.namespace == namespace_str,
        ]

        if tenant_str:
            conditions.append(MetadataEntryModel.tenant_id == tenant_str)
        else:
            conditions.append(MetadataEntryModel.tenant_id.is_(None))

        query = select(func.count(MetadataEntryModel.id)).where(and_(*conditions))
        result = await self._session.execute(query)
        count = result.scalar_one()

        return count > 0

    async def bulk_get(
        self,
        keys: list[tuple[str, str | None, str | None]],
    ) -> dict[str, MetadataEntry | None]:
        """Bulk get metadata entries by keys."""
        result = {}

        for key, namespace, tenant_id in keys:
            entry = await self.get_by_key(key, namespace, tenant_id)
            result[key] = entry

        return result

    async def bulk_create(
        self,
        entries: list[MetadataEntry],
    ) -> list[MetadataEntry]:
        """Bulk create metadata entries."""
        for entry in entries:
            await self.create(entry)

        return entries
