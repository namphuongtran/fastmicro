"""Configuration application service.

Orchestrates configuration operations using domain entities and repository interfaces.
"""

from __future__ import annotations

import logging
from typing import Any, Protocol
from uuid import UUID

from metastore_service.application.dtos.configuration_dtos import (
    ConfigurationDTO,
    ConfigurationListDTO,
    ConfigurationVersionDTO,
    CreateConfigurationDTO,
    UpdateConfigurationDTO,
)
from metastore_service.domain.entities.configuration import Configuration
from metastore_service.domain.repositories.configuration_repository import (
    IConfigurationRepository,
    IConfigurationSchemaRepository,
)
from metastore_service.domain.value_objects import Environment

logger = logging.getLogger(__name__)


class ICacheService(Protocol):
    """Cache service interface for configuration caching."""

    async def get(self, key: str) -> Any | None: ...
    async def set(self, key: str, value: Any, ttl: int | None = None) -> None: ...
    async def delete(self, key: str) -> None: ...
    async def delete_pattern(self, pattern: str) -> None: ...


class ISecretService(Protocol):
    """Secret service interface for fetching secrets from vault."""

    async def get_secret(self, path: str, key: str) -> str | None: ...


class ConfigurationService:
    """Application service for configuration operations.

    Handles business logic, secret resolution, and orchestration between
    the domain layer and infrastructure concerns.
    """

    def __init__(
        self,
        repository: IConfigurationRepository,
        schema_repository: IConfigurationSchemaRepository | None = None,
        cache: ICacheService | None = None,
        secret_service: ISecretService | None = None,
        cache_ttl: int = 300,  # 5 minutes default
    ):
        """Initialize the configuration service.

        Args:
            repository: Configuration repository implementation
            schema_repository: Optional schema repository
            cache: Optional cache service for hot data
            secret_service: Optional secret service for vault integration
            cache_ttl: Cache TTL in seconds
        """
        self._repository = repository
        self._schema_repository = schema_repository
        self._cache = cache
        self._secret_service = secret_service
        self._cache_ttl = cache_ttl

    def _cache_key(
        self,
        service_id: str,
        name: str,
        environment: Environment,
        tenant_id: str | None = None,
    ) -> str:
        """Generate a cache key."""
        parts = ["config", service_id, environment.value, name]
        if tenant_id:
            parts.append(tenant_id)
        return ":".join(parts)

    async def create(
        self,
        dto: CreateConfigurationDTO,
        created_by: str | None = None,
    ) -> ConfigurationDTO:
        """Create a new configuration.

        Args:
            dto: Creation data
            created_by: User creating the configuration

        Returns:
            The created configuration

        Raises:
            ValueError: If configuration already exists or validation fails
        """
        # Check for duplicates
        existing = await self._repository.exists(
            service_id=dto.service_id,
            name=dto.name,
            environment=dto.environment,
            tenant_id=dto.tenant_id,
        )
        if existing:
            raise ValueError(
                f"Configuration '{dto.name}' already exists for service "
                f"'{dto.service_id}' in environment '{dto.environment.value}'"
            )

        # Get schema if specified
        schema = None
        if dto.schema_id and self._schema_repository:
            schema = await self._schema_repository.get_by_id(dto.schema_id)
            if schema is None:
                raise ValueError(f"Schema with ID '{dto.schema_id}' not found")

        # Create domain entity
        config = Configuration.create(
            service_id=dto.service_id,
            name=dto.name,
            environment=dto.environment,
            values=dto.values,
            schema=schema,
            tenant_id=dto.tenant_id,
            description=dto.description,
            effective_from=dto.effective_from,
            created_by=created_by,
        )

        # Add secret references
        for ref in dto.secret_refs:
            config.add_secret_ref(ref.key, ref.vault_path, ref.vault_key)

        # Persist
        created = await self._repository.create(config)

        logger.info(
            "Created configuration",
            extra={
                "config_id": str(created.id),
                "service_id": dto.service_id,
                "config_name": dto.name,
                "environment": dto.environment.value,
                "created_by": created_by,
            },
        )

        return ConfigurationDTO.from_entity(created)

    async def get_by_id(
        self,
        config_id: UUID,
        include_secrets: bool = False,
    ) -> ConfigurationDTO | None:
        """Get a configuration by ID.

        Args:
            config_id: The configuration ID
            include_secrets: Whether to include secret values

        Returns:
            The configuration or None if not found
        """
        config = await self._repository.get_by_id(config_id)
        if config is None:
            return None

        # Resolve secrets if requested
        if include_secrets and self._secret_service:
            await self._resolve_secrets(config)

        return ConfigurationDTO.from_entity(config, include_secrets)

    async def get_by_name(
        self,
        service_id: str,
        name: str,
        environment: Environment,
        tenant_id: str | None = None,
        include_secrets: bool = False,
    ) -> ConfigurationDTO | None:
        """Get a configuration by service, name, and environment.

        Args:
            service_id: The service identifier
            name: The configuration name
            environment: The deployment environment
            tenant_id: Optional tenant ID
            include_secrets: Whether to include secret values

        Returns:
            The configuration or None if not found
        """
        # Try cache first (only if not including secrets)
        if self._cache and not include_secrets:
            cache_key = self._cache_key(service_id, name, environment, tenant_id)
            cached = await self._cache.get(cache_key)
            if cached:
                return ConfigurationDTO(**cached)

        # Get from repository
        config = await self._repository.get_by_name(
            service_id=service_id,
            name=name,
            environment=environment,
            tenant_id=tenant_id,
        )
        if config is None:
            return None

        # Resolve secrets if requested
        if include_secrets and self._secret_service:
            await self._resolve_secrets(config)

        dto = ConfigurationDTO.from_entity(config, include_secrets)

        # Cache result (only if not including secrets)
        if self._cache and not include_secrets:
            cache_key = self._cache_key(service_id, name, environment, tenant_id)
            await self._cache.set(cache_key, dto.model_dump(mode="json"), self._cache_ttl)

        return dto

    async def _resolve_secrets(self, config: Configuration) -> None:
        """Resolve secret references from vault."""
        if not self._secret_service:
            return

        for ref in config.secret_refs:
            secret_value = await self._secret_service.get_secret(ref.vault_path, ref.vault_key)
            if secret_value:
                config.values[ref.key] = secret_value

    async def get_effective_config(
        self,
        service_id: str,
        environment: Environment,
        tenant_id: str | None = None,
        include_secrets: bool = False,
    ) -> dict[str, Any]:
        """Get the merged effective configuration for a service.

        Args:
            service_id: The service identifier
            environment: The deployment environment
            tenant_id: Optional tenant ID
            include_secrets: Whether to include secret values

        Returns:
            Merged configuration dictionary
        """
        effective = await self._repository.get_effective_config(
            service_id=service_id,
            environment=environment,
            tenant_id=tenant_id,
        )

        # Resolve secrets if requested
        if include_secrets and self._secret_service:
            # Get all configs to find secret refs
            configs = await self._repository.list_by_service(
                service_id=service_id,
                environment=environment,
                tenant_id=tenant_id,
                active_only=True,
            )
            for config in configs:
                for ref in config.secret_refs:
                    secret_value = await self._secret_service.get_secret(
                        ref.vault_path, ref.vault_key
                    )
                    if secret_value:
                        effective[ref.key] = secret_value

        return effective

    async def update(
        self,
        config_id: UUID,
        dto: UpdateConfigurationDTO,
        updated_by: str | None = None,
    ) -> ConfigurationDTO | None:
        """Update a configuration.

        Args:
            config_id: The configuration ID
            dto: Update data
            updated_by: User making the update

        Returns:
            The updated configuration or None if not found
        """
        config = await self._repository.get_by_id(config_id)
        if config is None:
            return None

        # Apply updates
        if dto.values is not None:
            config.update_values(
                new_values=dto.values,
                updated_by=updated_by,
                change_reason=dto.change_reason,
                merge=dto.merge,
            )

        if dto.description is not None:
            config.description = dto.description

        if dto.effective_from is not None:
            config.effective_from = dto.effective_from

        if dto.effective_until is not None:
            config.effective_until = dto.effective_until

        # Persist
        updated = await self._repository.update(config)

        # Invalidate cache
        if self._cache:
            cache_key = self._cache_key(
                config.service_id,
                config.name,
                config.environment,
                config.tenant_id.value if config.tenant_id else None,
            )
            await self._cache.delete(cache_key)

        logger.info(
            "Updated configuration",
            extra={
                "config_id": str(config_id),
                "service_id": config.service_id,
                "config_name": config.name,
                "updated_by": updated_by,
                "change_reason": dto.change_reason,
            },
        )

        return ConfigurationDTO.from_entity(updated)

    async def set_value(
        self,
        config_id: UUID,
        key: str,
        value: Any,
        updated_by: str | None = None,
    ) -> ConfigurationDTO | None:
        """Set a single configuration value.

        Args:
            config_id: The configuration ID
            key: The configuration key
            value: The value to set
            updated_by: User making the update

        Returns:
            The updated configuration or None if not found
        """
        config = await self._repository.get_by_id(config_id)
        if config is None:
            return None

        config.set_value(key, value, updated_by)
        updated = await self._repository.update(config)

        # Invalidate cache
        if self._cache:
            cache_key = self._cache_key(
                config.service_id,
                config.name,
                config.environment,
                config.tenant_id.value if config.tenant_id else None,
            )
            await self._cache.delete(cache_key)

        return ConfigurationDTO.from_entity(updated)

    async def delete_value(
        self,
        config_id: UUID,
        key: str,
        updated_by: str | None = None,
    ) -> ConfigurationDTO | None:
        """Delete a single configuration value.

        Args:
            config_id: The configuration ID
            key: The configuration key to delete
            updated_by: User making the update

        Returns:
            The updated configuration or None if not found
        """
        config = await self._repository.get_by_id(config_id)
        if config is None:
            return None

        deleted = config.delete_value(key, updated_by)
        if not deleted:
            return ConfigurationDTO.from_entity(config)

        updated = await self._repository.update(config)

        # Invalidate cache
        if self._cache:
            cache_key = self._cache_key(
                config.service_id,
                config.name,
                config.environment,
                config.tenant_id.value if config.tenant_id else None,
            )
            await self._cache.delete(cache_key)

        return ConfigurationDTO.from_entity(updated)

    async def delete(self, config_id: UUID) -> bool:
        """Delete a configuration.

        Args:
            config_id: The configuration ID

        Returns:
            True if deleted, False if not found
        """
        # Get config first for cache invalidation
        config = await self._repository.get_by_id(config_id)
        if config is None:
            return False

        # Delete
        result = await self._repository.delete(config_id)

        # Invalidate cache
        if self._cache and result:
            cache_key = self._cache_key(
                config.service_id,
                config.name,
                config.environment,
                config.tenant_id.value if config.tenant_id else None,
            )
            await self._cache.delete(cache_key)

        logger.info(
            "Deleted configuration",
            extra={
                "config_id": str(config_id),
                "service_id": config.service_id,
                "config_name": config.name,
            },
        )

        return result

    async def list_by_service(
        self,
        service_id: str,
        environment: Environment | None = None,
        tenant_id: str | None = None,
        active_only: bool = True,
        limit: int = 100,
        offset: int = 0,
    ) -> ConfigurationListDTO:
        """List configurations for a service.

        Args:
            service_id: The service identifier
            environment: Optional environment filter
            tenant_id: Optional tenant ID filter
            active_only: Only return active configurations
            limit: Maximum results
            offset: Offset for pagination

        Returns:
            Paginated list of configurations
        """
        configs = await self._repository.list_by_service(
            service_id=service_id,
            environment=environment,
            tenant_id=tenant_id,
            active_only=active_only,
            limit=limit,
            offset=offset,
        )
        total = await self._repository.count(
            service_id=service_id,
            environment=environment,
            tenant_id=tenant_id,
            active_only=active_only,
        )

        return ConfigurationListDTO.from_entities(configs, total, limit, offset)

    async def search(
        self,
        query: str,
        service_id: str | None = None,
        environment: Environment | None = None,
        tenant_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> ConfigurationListDTO:
        """Search configurations.

        Args:
            query: Search query
            service_id: Optional service filter
            environment: Optional environment filter
            tenant_id: Optional tenant ID filter
            limit: Maximum results
            offset: Offset for pagination

        Returns:
            Paginated list of matching configurations
        """
        configs = await self._repository.search(
            query=query,
            service_id=service_id,
            environment=environment,
            tenant_id=tenant_id,
            limit=limit,
            offset=offset,
        )
        total = len(configs) if len(configs) < limit else limit + offset + 1

        return ConfigurationListDTO.from_entities(configs, total, limit, offset)

    async def get_versions(
        self,
        config_id: UUID,
        limit: int = 50,
    ) -> list[ConfigurationVersionDTO]:
        """Get version history for a configuration.

        Args:
            config_id: The configuration ID
            limit: Maximum versions to return

        Returns:
            List of versions (newest first)
        """
        versions = await self._repository.get_versions(config_id, limit)
        return [
            ConfigurationVersionDTO(
                id=v.id,
                version_number=v.version_number,
                values=v.values,
                created_at=v.created_at,
                created_by=v.created_by,
                change_reason=v.change_reason,
            )
            for v in versions
        ]

    async def rollback_to_version(
        self,
        config_id: UUID,
        version_number: int,
        rolled_back_by: str | None = None,
    ) -> ConfigurationDTO | None:
        """Rollback a configuration to a previous version.

        Args:
            config_id: The configuration ID
            version_number: The version to rollback to
            rolled_back_by: User performing the rollback

        Returns:
            The updated configuration or None if not found
        """
        config = await self._repository.get_by_id(config_id)
        if config is None:
            return None

        # Rollback (creates new version)
        config.rollback_to_version(version_number, rolled_back_by)

        # Persist
        updated = await self._repository.update(config)

        # Invalidate cache
        if self._cache:
            cache_key = self._cache_key(
                config.service_id,
                config.name,
                config.environment,
                config.tenant_id.value if config.tenant_id else None,
            )
            await self._cache.delete(cache_key)

        logger.info(
            "Rolled back configuration",
            extra={
                "config_id": str(config_id),
                "to_version": version_number,
                "rolled_back_by": rolled_back_by,
            },
        )

        return ConfigurationDTO.from_entity(updated)

    async def activate(
        self,
        config_id: UUID,
        updated_by: str | None = None,
    ) -> bool:
        """Activate a configuration.

        Args:
            config_id: The configuration ID
            updated_by: User making the change

        Returns:
            True if activated, False if not found
        """
        result = await self._repository.activate(config_id, updated_by)

        if result:
            config = await self._repository.get_by_id(config_id)
            if config and self._cache:
                cache_key = self._cache_key(
                    config.service_id,
                    config.name,
                    config.environment,
                    config.tenant_id.value if config.tenant_id else None,
                )
                await self._cache.delete(cache_key)

        return result

    async def deactivate(
        self,
        config_id: UUID,
        updated_by: str | None = None,
    ) -> bool:
        """Deactivate a configuration.

        Args:
            config_id: The configuration ID
            updated_by: User making the change

        Returns:
            True if deactivated, False if not found
        """
        result = await self._repository.deactivate(config_id, updated_by)

        if result:
            config = await self._repository.get_by_id(config_id)
            if config and self._cache:
                cache_key = self._cache_key(
                    config.service_id,
                    config.name,
                    config.environment,
                    config.tenant_id.value if config.tenant_id else None,
                )
                await self._cache.delete(cache_key)

        return result
