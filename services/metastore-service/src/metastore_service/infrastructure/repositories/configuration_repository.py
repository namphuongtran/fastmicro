"""PostgreSQL repository implementation for Configuration aggregate."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from metastore_service.domain.entities.configuration import (
    Configuration,
    ConfigurationSchema,
    ConfigurationVersion,
    SecretReference,
)
from metastore_service.domain.repositories.configuration_repository import (
    IConfigurationRepository,
    IConfigurationSchemaRepository,
)
from metastore_service.domain.value_objects import Environment, TenantId
from metastore_service.infrastructure.database.models import (
    ConfigurationModel,
    ConfigurationSchemaModel,
    ConfigurationVersionModel,
)

logger = logging.getLogger(__name__)


class PostgresConfigurationRepository(IConfigurationRepository):
    """PostgreSQL implementation of the configuration repository."""

    def __init__(self, session: AsyncSession):
        """Initialize the repository.

        Args:
            session: Async SQLAlchemy session
        """
        self._session = session

    def _to_domain(self, model: ConfigurationModel) -> Configuration:
        """Convert database model to domain entity."""
        versions = [
            ConfigurationVersion(
                id=v.id,
                configuration_id=v.configuration_id,
                version_number=v.version_number,
                values=v.values,
                created_at=v.created_at,
                created_by=v.created_by,
                change_reason=v.change_reason,
            )
            for v in (model.versions or [])
        ]

        secret_refs = [
            SecretReference(
                key=ref.get("key", ""),
                vault_path=ref.get("vault_path", ""),
                vault_key=ref.get("vault_key", ""),
            )
            for ref in (model.secret_refs or [])
        ]

        schema = None
        if model.schema:
            schema = ConfigurationSchema(
                id=model.schema.id,
                name=model.schema.name,
                version=model.schema.version,
                json_schema=model.schema.json_schema,
                description=model.schema.description,
            )

        return Configuration(
            id=model.id,
            service_id=model.service_id,
            name=model.name,
            environment=model.environment,
            values=model.values,
            schema=schema,
            secret_refs=secret_refs,
            tenant_id=TenantId(model.tenant_id) if model.tenant_id else None,
            description=model.description,
            is_active=model.is_active,
            effective_from=model.effective_from,
            effective_until=model.effective_until,
            versions=versions,
            created_at=model.created_at,
            updated_at=model.updated_at,
            created_by=model.created_by,
            updated_by=model.updated_by,
        )

    def _to_model(self, entity: Configuration) -> ConfigurationModel:
        """Convert domain entity to database model."""
        secret_refs = [
            {"key": ref.key, "vault_path": ref.vault_path, "vault_key": ref.vault_key}
            for ref in entity.secret_refs
        ]

        return ConfigurationModel(
            id=entity.id,
            service_id=entity.service_id,
            name=entity.name,
            environment=entity.environment,
            values=entity.values,
            schema_id=entity.schema.id if entity.schema else None,
            secret_refs=secret_refs,
            tenant_id=entity.tenant_id.value if entity.tenant_id else None,
            description=entity.description,
            is_active=entity.is_active,
            effective_from=entity.effective_from,
            effective_until=entity.effective_until,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            created_by=entity.created_by,
            updated_by=entity.updated_by,
        )

    async def get_by_id(self, config_id: UUID) -> Configuration | None:
        """Get a configuration by ID."""
        query = (
            select(ConfigurationModel)
            .options(
                selectinload(ConfigurationModel.versions),
                selectinload(ConfigurationModel.schema),
            )
            .where(ConfigurationModel.id == config_id)
        )
        result = await self._session.execute(query)
        model = result.scalar_one_or_none()

        if model is None:
            return None

        return self._to_domain(model)

    async def get_by_name(
        self,
        service_id: str,
        name: str,
        environment: Environment,
        tenant_id: TenantId | str | None = None,
    ) -> Configuration | None:
        """Get a configuration by service, name, and environment."""
        tenant_str = tenant_id.value if isinstance(tenant_id, TenantId) else tenant_id

        conditions = [
            ConfigurationModel.service_id == service_id,
            ConfigurationModel.name == name,
            ConfigurationModel.environment == environment,
        ]

        if tenant_str:
            conditions.append(ConfigurationModel.tenant_id == tenant_str)
        else:
            conditions.append(ConfigurationModel.tenant_id.is_(None))

        query = (
            select(ConfigurationModel)
            .options(
                selectinload(ConfigurationModel.versions),
                selectinload(ConfigurationModel.schema),
            )
            .where(and_(*conditions))
        )
        result = await self._session.execute(query)
        model = result.scalar_one_or_none()

        if model is None:
            return None

        return self._to_domain(model)

    async def list_by_service(
        self,
        service_id: str,
        environment: Environment | None = None,
        tenant_id: TenantId | str | None = None,
        active_only: bool = True,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Configuration]:
        """List all configurations for a service."""
        conditions = [ConfigurationModel.service_id == service_id]

        if environment:
            conditions.append(ConfigurationModel.environment == environment)

        if tenant_id:
            tenant_str = tenant_id.value if isinstance(tenant_id, TenantId) else tenant_id
            conditions.append(ConfigurationModel.tenant_id == tenant_str)

        if active_only:
            conditions.append(ConfigurationModel.is_active == True)

        query = (
            select(ConfigurationModel)
            .options(
                selectinload(ConfigurationModel.versions),
                selectinload(ConfigurationModel.schema),
            )
            .where(and_(*conditions))
            .order_by(ConfigurationModel.name)
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(query)
        models = result.scalars().all()

        return [self._to_domain(m) for m in models]

    async def list_by_environment(
        self,
        environment: Environment,
        tenant_id: TenantId | str | None = None,
        active_only: bool = True,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Configuration]:
        """List all configurations for an environment."""
        conditions = [ConfigurationModel.environment == environment]

        if tenant_id:
            tenant_str = tenant_id.value if isinstance(tenant_id, TenantId) else tenant_id
            conditions.append(ConfigurationModel.tenant_id == tenant_str)

        if active_only:
            conditions.append(ConfigurationModel.is_active == True)

        query = (
            select(ConfigurationModel)
            .options(
                selectinload(ConfigurationModel.versions),
                selectinload(ConfigurationModel.schema),
            )
            .where(and_(*conditions))
            .order_by(ConfigurationModel.service_id, ConfigurationModel.name)
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(query)
        models = result.scalars().all()

        return [self._to_domain(m) for m in models]

    async def search(
        self,
        query: str,
        service_id: str | None = None,
        environment: Environment | None = None,
        tenant_id: TenantId | str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Configuration]:
        """Search configurations by name or description."""
        pattern = query.replace("*", "%").replace("?", "_")

        conditions = [
            or_(
                ConfigurationModel.name.ilike(f"%{pattern}%"),
                ConfigurationModel.description.ilike(f"%{pattern}%"),
            )
        ]

        if service_id:
            conditions.append(ConfigurationModel.service_id == service_id)

        if environment:
            conditions.append(ConfigurationModel.environment == environment)

        if tenant_id:
            tenant_str = tenant_id.value if isinstance(tenant_id, TenantId) else tenant_id
            conditions.append(ConfigurationModel.tenant_id == tenant_str)

        stmt = (
            select(ConfigurationModel)
            .options(
                selectinload(ConfigurationModel.versions),
                selectinload(ConfigurationModel.schema),
            )
            .where(and_(*conditions))
            .order_by(ConfigurationModel.service_id, ConfigurationModel.name)
            .limit(limit)
            .offset(offset)
        )

        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._to_domain(m) for m in models]

    async def create(self, config: Configuration) -> Configuration:
        """Create a new configuration."""
        model = self._to_model(config)

        # Add versions
        for v in config.versions:
            version_model = ConfigurationVersionModel(
                id=v.id,
                configuration_id=config.id,
                version_number=v.version_number,
                values=v.values,
                created_at=v.created_at,
                created_by=v.created_by,
                change_reason=v.change_reason,
            )
            model.versions.append(version_model)

        self._session.add(model)
        await self._session.flush()

        logger.debug(f"Created configuration: {config.id}")
        return config

    async def update(self, config: Configuration) -> Configuration:
        """Update an existing configuration."""
        # Get existing model
        query = (
            select(ConfigurationModel)
            .options(selectinload(ConfigurationModel.versions))
            .where(ConfigurationModel.id == config.id)
        )
        result = await self._session.execute(query)
        model = result.scalar_one_or_none()

        if model is None:
            raise ValueError(f"Configuration {config.id} not found")

        # Update model attributes
        secret_refs = [
            {"key": ref.key, "vault_path": ref.vault_path, "vault_key": ref.vault_key}
            for ref in config.secret_refs
        ]

        model.service_id = config.service_id
        model.name = config.name
        model.environment = config.environment
        model.values = config.values
        model.schema_id = config.schema.id if config.schema else None
        model.secret_refs = secret_refs
        model.tenant_id = config.tenant_id.value if config.tenant_id else None
        model.description = config.description
        model.is_active = config.is_active
        model.effective_from = config.effective_from
        model.effective_until = config.effective_until
        model.updated_at = config.updated_at
        model.updated_by = config.updated_by

        # Add new versions
        existing_version_ids = {v.id for v in model.versions}
        for v in config.versions:
            if v.id not in existing_version_ids:
                version_model = ConfigurationVersionModel(
                    id=v.id,
                    configuration_id=config.id,
                    version_number=v.version_number,
                    values=v.values,
                    created_at=v.created_at,
                    created_by=v.created_by,
                    change_reason=v.change_reason,
                )
                model.versions.append(version_model)

        await self._session.flush()

        logger.debug(f"Updated configuration: {config.id}")
        return config

    async def delete(self, config_id: UUID) -> bool:
        """Delete a configuration by ID."""
        stmt = delete(ConfigurationModel).where(ConfigurationModel.id == config_id)
        result = await self._session.execute(stmt)
        await self._session.flush()

        deleted = result.rowcount > 0
        if deleted:
            logger.debug(f"Deleted configuration: {config_id}")
        return deleted

    async def get_versions(
        self,
        config_id: UUID,
        limit: int = 50,
    ) -> list[ConfigurationVersion]:
        """Get version history for a configuration."""
        query = (
            select(ConfigurationVersionModel)
            .where(ConfigurationVersionModel.configuration_id == config_id)
            .order_by(ConfigurationVersionModel.version_number.desc())
            .limit(limit)
        )
        result = await self._session.execute(query)
        models = result.scalars().all()

        return [
            ConfigurationVersion(
                id=m.id,
                configuration_id=m.configuration_id,
                version_number=m.version_number,
                values=m.values,
                created_at=m.created_at,
                created_by=m.created_by,
                change_reason=m.change_reason,
            )
            for m in models
        ]

    async def get_version(
        self,
        config_id: UUID,
        version_number: int,
    ) -> ConfigurationVersion | None:
        """Get a specific version of a configuration."""
        query = select(ConfigurationVersionModel).where(
            and_(
                ConfigurationVersionModel.configuration_id == config_id,
                ConfigurationVersionModel.version_number == version_number,
            )
        )
        result = await self._session.execute(query)
        model = result.scalar_one_or_none()

        if model is None:
            return None

        return ConfigurationVersion(
            id=model.id,
            configuration_id=model.configuration_id,
            version_number=model.version_number,
            values=model.values,
            created_at=model.created_at,
            created_by=model.created_by,
            change_reason=model.change_reason,
        )

    async def get_effective_config(
        self,
        service_id: str,
        environment: Environment,
        tenant_id: TenantId | str | None = None,
    ) -> dict[str, Any]:
        """Get the merged effective configuration for a service."""
        configs = await self.list_by_service(
            service_id=service_id,
            environment=environment,
            tenant_id=tenant_id,
            active_only=True,
        )

        # Merge all active configurations
        merged = {}
        for config in configs:
            if config.is_effective:
                merged.update(config.values)

        return merged

    async def exists(
        self,
        service_id: str,
        name: str,
        environment: Environment,
        tenant_id: TenantId | str | None = None,
    ) -> bool:
        """Check if a configuration exists."""
        tenant_str = tenant_id.value if isinstance(tenant_id, TenantId) else tenant_id

        conditions = [
            ConfigurationModel.service_id == service_id,
            ConfigurationModel.name == name,
            ConfigurationModel.environment == environment,
        ]

        if tenant_str:
            conditions.append(ConfigurationModel.tenant_id == tenant_str)
        else:
            conditions.append(ConfigurationModel.tenant_id.is_(None))

        query = select(func.count(ConfigurationModel.id)).where(and_(*conditions))
        result = await self._session.execute(query)
        count = result.scalar_one()

        return count > 0

    async def count(
        self,
        service_id: str | None = None,
        environment: Environment | None = None,
        tenant_id: TenantId | str | None = None,
        active_only: bool = True,
    ) -> int:
        """Count configurations."""
        conditions = []

        if service_id:
            conditions.append(ConfigurationModel.service_id == service_id)

        if environment:
            conditions.append(ConfigurationModel.environment == environment)

        if tenant_id:
            tenant_str = tenant_id.value if isinstance(tenant_id, TenantId) else tenant_id
            conditions.append(ConfigurationModel.tenant_id == tenant_str)

        if active_only:
            conditions.append(ConfigurationModel.is_active == True)

        query = select(func.count(ConfigurationModel.id))
        if conditions:
            query = query.where(and_(*conditions))

        result = await self._session.execute(query)
        return result.scalar_one()

    async def activate(
        self,
        config_id: UUID,
        updated_by: str | None = None,
    ) -> bool:
        """Activate a configuration."""
        stmt = (
            update(ConfigurationModel)
            .where(ConfigurationModel.id == config_id)
            .values(
                is_active=True,
                updated_at=datetime.now(timezone.utc),
                updated_by=updated_by,
            )
        )
        result = await self._session.execute(stmt)
        await self._session.flush()

        return result.rowcount > 0

    async def deactivate(
        self,
        config_id: UUID,
        updated_by: str | None = None,
    ) -> bool:
        """Deactivate a configuration."""
        stmt = (
            update(ConfigurationModel)
            .where(ConfigurationModel.id == config_id)
            .values(
                is_active=False,
                updated_at=datetime.now(timezone.utc),
                updated_by=updated_by,
            )
        )
        result = await self._session.execute(stmt)
        await self._session.flush()

        return result.rowcount > 0


class PostgresConfigurationSchemaRepository(IConfigurationSchemaRepository):
    """PostgreSQL implementation of the configuration schema repository."""

    def __init__(self, session: AsyncSession):
        """Initialize the repository."""
        self._session = session

    async def get_by_id(self, schema_id: UUID) -> ConfigurationSchema | None:
        """Get a schema by ID."""
        query = select(ConfigurationSchemaModel).where(
            ConfigurationSchemaModel.id == schema_id
        )
        result = await self._session.execute(query)
        model = result.scalar_one_or_none()

        if model is None:
            return None

        return ConfigurationSchema(
            id=model.id,
            name=model.name,
            version=model.version,
            json_schema=model.json_schema,
            description=model.description,
        )

    async def get_by_name(
        self,
        name: str,
        version: str | None = None,
    ) -> ConfigurationSchema | None:
        """Get a schema by name and optional version."""
        conditions = [ConfigurationSchemaModel.name == name]
        if version:
            conditions.append(ConfigurationSchemaModel.version == version)

        query = (
            select(ConfigurationSchemaModel)
            .where(and_(*conditions))
            .order_by(ConfigurationSchemaModel.version.desc())
            .limit(1)
        )
        result = await self._session.execute(query)
        model = result.scalar_one_or_none()

        if model is None:
            return None

        return ConfigurationSchema(
            id=model.id,
            name=model.name,
            version=model.version,
            json_schema=model.json_schema,
            description=model.description,
        )

    async def list_all(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ConfigurationSchema]:
        """List all schemas."""
        query = (
            select(ConfigurationSchemaModel)
            .order_by(ConfigurationSchemaModel.name, ConfigurationSchemaModel.version)
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(query)
        models = result.scalars().all()

        return [
            ConfigurationSchema(
                id=m.id,
                name=m.name,
                version=m.version,
                json_schema=m.json_schema,
                description=m.description,
            )
            for m in models
        ]

    async def create(self, schema: ConfigurationSchema) -> ConfigurationSchema:
        """Create a new schema."""
        model = ConfigurationSchemaModel(
            id=schema.id,
            name=schema.name,
            version=schema.version,
            json_schema=schema.json_schema,
            description=schema.description,
        )

        self._session.add(model)
        await self._session.flush()

        return schema

    async def update(self, schema: ConfigurationSchema) -> ConfigurationSchema:
        """Update an existing schema."""
        stmt = (
            update(ConfigurationSchemaModel)
            .where(ConfigurationSchemaModel.id == schema.id)
            .values(
                name=schema.name,
                version=schema.version,
                json_schema=schema.json_schema,
                description=schema.description,
            )
        )
        await self._session.execute(stmt)
        await self._session.flush()

        return schema

    async def delete(self, schema_id: UUID) -> bool:
        """Delete a schema by ID."""
        stmt = delete(ConfigurationSchemaModel).where(
            ConfigurationSchemaModel.id == schema_id
        )
        result = await self._session.execute(stmt)
        await self._session.flush()

        return result.rowcount > 0
