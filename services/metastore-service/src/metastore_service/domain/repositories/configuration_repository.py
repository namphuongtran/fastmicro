"""Abstract repository interface for Configuration aggregate.

Defines the contract for configuration persistence operations.
"""

from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

from metastore_service.domain.entities.configuration import (
    Configuration,
    ConfigurationSchema,
    ConfigurationVersion,
)
from metastore_service.domain.value_objects import Environment, TenantId


class IConfigurationRepository(ABC):
    """Abstract repository interface for Configuration persistence.

    All implementations must support async operations for scalability.
    """

    @abstractmethod
    async def get_by_id(self, config_id: UUID) -> Configuration | None:
        """Get a configuration by ID.

        Args:
            config_id: The unique identifier

        Returns:
            The configuration if found, None otherwise
        """
        ...

    @abstractmethod
    async def get_by_name(
        self,
        service_id: str,
        name: str,
        environment: Environment,
        tenant_id: TenantId | str | None = None,
    ) -> Configuration | None:
        """Get a configuration by service, name, and environment.

        Args:
            service_id: The service identifier
            name: The configuration name
            environment: The deployment environment
            tenant_id: Optional tenant ID

        Returns:
            The configuration if found, None otherwise
        """
        ...

    @abstractmethod
    async def list_by_service(
        self,
        service_id: str,
        environment: Environment | None = None,
        tenant_id: TenantId | str | None = None,
        active_only: bool = True,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Configuration]:
        """List all configurations for a service.

        Args:
            service_id: The service identifier
            environment: Optional environment filter
            tenant_id: Optional tenant ID filter
            active_only: Only return active configurations
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of configurations
        """
        ...

    @abstractmethod
    async def list_by_environment(
        self,
        environment: Environment,
        tenant_id: TenantId | str | None = None,
        active_only: bool = True,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Configuration]:
        """List all configurations for an environment.

        Args:
            environment: The deployment environment
            tenant_id: Optional tenant ID filter
            active_only: Only return active configurations
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of configurations
        """
        ...

    @abstractmethod
    async def search(
        self,
        query: str,
        service_id: str | None = None,
        environment: Environment | None = None,
        tenant_id: TenantId | str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Configuration]:
        """Search configurations by name or description.

        Args:
            query: Search query
            service_id: Optional service filter
            environment: Optional environment filter
            tenant_id: Optional tenant ID filter
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of matching configurations
        """
        ...

    @abstractmethod
    async def create(self, config: Configuration) -> Configuration:
        """Create a new configuration.

        Args:
            config: The configuration to create

        Returns:
            The created configuration

        Raises:
            DuplicateNameError: If name already exists for service/env/tenant
        """
        ...

    @abstractmethod
    async def update(self, config: Configuration) -> Configuration:
        """Update an existing configuration.

        Args:
            config: The configuration to update

        Returns:
            The updated configuration

        Raises:
            NotFoundError: If the configuration doesn't exist
        """
        ...

    @abstractmethod
    async def delete(self, config_id: UUID) -> bool:
        """Delete a configuration by ID.

        Args:
            config_id: The unique identifier

        Returns:
            True if deleted, False if not found
        """
        ...

    @abstractmethod
    async def get_versions(
        self,
        config_id: UUID,
        limit: int = 50,
    ) -> list[ConfigurationVersion]:
        """Get version history for a configuration.

        Args:
            config_id: The configuration ID
            limit: Maximum number of versions to return

        Returns:
            List of versions (newest first)
        """
        ...

    @abstractmethod
    async def get_version(
        self,
        config_id: UUID,
        version_number: int,
    ) -> ConfigurationVersion | None:
        """Get a specific version of a configuration.

        Args:
            config_id: The configuration ID
            version_number: The version number to retrieve

        Returns:
            The version if found, None otherwise
        """
        ...

    @abstractmethod
    async def get_effective_config(
        self,
        service_id: str,
        environment: Environment,
        tenant_id: TenantId | str | None = None,
    ) -> dict[str, Any]:
        """Get the merged effective configuration for a service.

        This merges all active configurations for the service/environment
        into a single dictionary.

        Args:
            service_id: The service identifier
            environment: The deployment environment
            tenant_id: Optional tenant ID

        Returns:
            Merged configuration dictionary
        """
        ...

    @abstractmethod
    async def exists(
        self,
        service_id: str,
        name: str,
        environment: Environment,
        tenant_id: TenantId | str | None = None,
    ) -> bool:
        """Check if a configuration exists.

        Args:
            service_id: The service identifier
            name: The configuration name
            environment: The deployment environment
            tenant_id: Optional tenant ID

        Returns:
            True if exists, False otherwise
        """
        ...

    @abstractmethod
    async def count(
        self,
        service_id: str | None = None,
        environment: Environment | None = None,
        tenant_id: TenantId | str | None = None,
        active_only: bool = True,
    ) -> int:
        """Count configurations.

        Args:
            service_id: Optional service filter
            environment: Optional environment filter
            tenant_id: Optional tenant ID filter
            active_only: Only count active configurations

        Returns:
            The count of matching configurations
        """
        ...

    @abstractmethod
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
        ...

    @abstractmethod
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
        ...


class IConfigurationSchemaRepository(ABC):
    """Abstract repository interface for ConfigurationSchema persistence."""

    @abstractmethod
    async def get_by_id(self, schema_id: UUID) -> ConfigurationSchema | None:
        """Get a schema by ID."""
        ...

    @abstractmethod
    async def get_by_name(
        self,
        name: str,
        version: str | None = None,
    ) -> ConfigurationSchema | None:
        """Get a schema by name and optional version."""
        ...

    @abstractmethod
    async def list_all(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ConfigurationSchema]:
        """List all schemas."""
        ...

    @abstractmethod
    async def create(self, schema: ConfigurationSchema) -> ConfigurationSchema:
        """Create a new schema."""
        ...

    @abstractmethod
    async def update(self, schema: ConfigurationSchema) -> ConfigurationSchema:
        """Update an existing schema."""
        ...

    @abstractmethod
    async def delete(self, schema_id: UUID) -> bool:
        """Delete a schema by ID."""
        ...
