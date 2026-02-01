"""Configuration aggregate - Domain entity for service configuration management.

The Configuration is an aggregate root that manages service-specific configurations
with schema validation, environment awareness, and secret references.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from metastore_service.domain.value_objects import Environment, TenantId


@dataclass(frozen=True)
class SecretReference:
    """Reference to a secret stored in an external secret manager.

    This allows configurations to reference secrets without storing
    the actual secret values in the configuration database.

    Attributes:
        key: The configuration key that holds the secret
        vault_path: Path to the secret in the vault (e.g., 'secret/data/app/db')
        vault_key: The key within the vault secret
    """

    key: str
    vault_path: str
    vault_key: str

    def __str__(self) -> str:
        return f"vault://{self.vault_path}#{self.vault_key}"


@dataclass
class ConfigurationSchema:
    """JSON Schema for validating configuration values.

    Attributes:
        id: Unique identifier
        name: Schema name
        version: Schema version
        json_schema: The JSON Schema definition
        description: Human-readable description
    """

    id: UUID
    name: str
    version: str
    json_schema: dict[str, Any]
    description: str | None = None

    @classmethod
    def create(
        cls,
        name: str,
        json_schema: dict[str, Any],
        version: str = "1.0.0",
        description: str | None = None,
    ) -> ConfigurationSchema:
        """Create a new configuration schema."""
        return cls(
            id=uuid4(),
            name=name,
            version=version,
            json_schema=json_schema,
            description=description,
        )

    def validate(self, values: dict[str, Any]) -> tuple[bool, list[str]]:
        """Validate values against this schema.

        Returns:
            Tuple of (is_valid, error_messages)
        """
        try:
            import jsonschema

            jsonschema.validate(instance=values, schema=self.json_schema)
            return True, []
        except ImportError:
            # jsonschema not available, skip validation
            return True, []
        except jsonschema.ValidationError as e:
            return False, [str(e.message)]
        except jsonschema.SchemaError as e:
            return False, [f"Invalid schema: {e.message}"]


@dataclass
class ConfigurationVersion:
    """Represents a historical version of a configuration.

    Maintains an audit trail of configuration changes.
    """

    id: UUID
    configuration_id: UUID
    version_number: int
    values: dict[str, Any]
    created_at: datetime
    created_by: str | None = None
    change_reason: str | None = None

    @classmethod
    def create(
        cls,
        configuration_id: UUID,
        version_number: int,
        values: dict[str, Any],
        created_by: str | None = None,
        change_reason: str | None = None,
    ) -> ConfigurationVersion:
        """Create a new configuration version."""
        return cls(
            id=uuid4(),
            configuration_id=configuration_id,
            version_number=version_number,
            values=values,
            created_at=datetime.now(UTC),
            created_by=created_by,
            change_reason=change_reason,
        )


@dataclass
class Configuration:
    """Aggregate root for service configuration management.

    Represents a configuration for a specific service and environment,
    with schema validation and secret references support.

    Attributes:
        id: Unique identifier
        service_id: Identifier for the service this config belongs to
        name: Configuration name (unique per service/environment)
        environment: The deployment environment
        values: The configuration key-value pairs
        schema: Optional JSON Schema for validation
        secret_refs: References to secrets in external vault
        tenant_id: Optional tenant for multi-tenancy
        description: Human-readable description
        is_active: Whether this configuration is currently active
        effective_from: When this configuration becomes effective
        effective_until: When this configuration expires
        versions: History of configuration changes
        created_at: Creation timestamp
        updated_at: Last update timestamp
        created_by: User who created the configuration
        updated_by: User who last updated the configuration
    """

    id: UUID
    service_id: str
    name: str
    environment: Environment
    values: dict[str, Any] = field(default_factory=dict)
    schema: ConfigurationSchema | None = None
    secret_refs: list[SecretReference] = field(default_factory=list)
    tenant_id: TenantId | None = None
    description: str | None = None
    is_active: bool = True
    effective_from: datetime | None = None
    effective_until: datetime | None = None
    versions: list[ConfigurationVersion] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    created_by: str | None = None
    updated_by: str | None = None

    @classmethod
    def create(
        cls,
        service_id: str,
        name: str,
        environment: Environment,
        values: dict[str, Any] | None = None,
        schema: ConfigurationSchema | None = None,
        tenant_id: str | TenantId | None = None,
        description: str | None = None,
        effective_from: datetime | None = None,
        created_by: str | None = None,
    ) -> Configuration:
        """Create a new configuration.

        Args:
            service_id: Identifier for the service
            name: Configuration name
            environment: Deployment environment
            values: Initial configuration values
            schema: Optional JSON Schema for validation
            tenant_id: Optional tenant for multi-tenancy
            description: Human-readable description
            effective_from: When this config becomes effective
            created_by: User creating the configuration

        Returns:
            A new Configuration instance
        """
        tenant_vo = (
            tenant_id
            if isinstance(tenant_id, TenantId) or tenant_id is None
            else TenantId(tenant_id)
        )

        config_id = uuid4()
        now = datetime.now(UTC)
        config_values = values or {}

        # Validate against schema if provided
        if schema:
            is_valid, errors = schema.validate(config_values)
            if not is_valid:
                raise ValueError(f"Configuration validation failed: {errors}")

        # Create initial version
        initial_version = ConfigurationVersion.create(
            configuration_id=config_id,
            version_number=1,
            values=config_values,
            created_by=created_by,
            change_reason="Initial creation",
        )

        return cls(
            id=config_id,
            service_id=service_id,
            name=name,
            environment=environment,
            values=config_values,
            schema=schema,
            secret_refs=[],
            tenant_id=tenant_vo,
            description=description,
            is_active=True,
            effective_from=effective_from or now,
            effective_until=None,
            versions=[initial_version],
            created_at=now,
            updated_at=now,
            created_by=created_by,
            updated_by=created_by,
        )

    def update_values(
        self,
        new_values: dict[str, Any],
        updated_by: str | None = None,
        change_reason: str | None = None,
        merge: bool = True,
    ) -> None:
        """Update configuration values.

        Args:
            new_values: New values to set
            updated_by: User making the change
            change_reason: Reason for the change
            merge: If True, merge with existing values; if False, replace
        """
        if merge:
            merged_values = {**self.values, **new_values}
        else:
            merged_values = new_values

        # Validate against schema if exists
        if self.schema:
            is_valid, errors = self.schema.validate(merged_values)
            if not is_valid:
                raise ValueError(f"Configuration validation failed: {errors}")

        # Create new version
        new_version = ConfigurationVersion.create(
            configuration_id=self.id,
            version_number=self.current_version_number + 1,
            values=merged_values,
            created_by=updated_by,
            change_reason=change_reason,
        )

        self.versions.append(new_version)
        self.values = merged_values
        self.updated_at = datetime.now(UTC)
        self.updated_by = updated_by

    def set_value(
        self,
        key: str,
        value: Any,
        updated_by: str | None = None,
    ) -> None:
        """Set a single configuration value."""
        self.update_values(
            new_values={key: value},
            updated_by=updated_by,
            change_reason=f"Updated key: {key}",
            merge=True,
        )

    def get_value(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by key."""
        return self.values.get(key, default)

    def delete_value(self, key: str, updated_by: str | None = None) -> bool:
        """Delete a configuration value by key."""
        if key not in self.values:
            return False

        new_values = {k: v for k, v in self.values.items() if k != key}
        self.update_values(
            new_values=new_values,
            updated_by=updated_by,
            change_reason=f"Deleted key: {key}",
            merge=False,
        )
        return True

    def add_secret_ref(
        self,
        key: str,
        vault_path: str,
        vault_key: str,
    ) -> SecretReference:
        """Add a secret reference.

        This marks a configuration key as containing a secret
        that should be fetched from an external vault.
        """
        ref = SecretReference(key=key, vault_path=vault_path, vault_key=vault_key)
        self.secret_refs.append(ref)
        self.updated_at = datetime.now(UTC)
        return ref

    def remove_secret_ref(self, key: str) -> bool:
        """Remove a secret reference by key."""
        for ref in self.secret_refs:
            if ref.key == key:
                self.secret_refs.remove(ref)
                self.updated_at = datetime.now(UTC)
                return True
        return False

    def get_secret_keys(self) -> list[str]:
        """Get all keys that are secret references."""
        return [ref.key for ref in self.secret_refs]

    def is_secret(self, key: str) -> bool:
        """Check if a key is a secret reference."""
        return any(ref.key == key for ref in self.secret_refs)

    def rollback_to_version(
        self,
        version_number: int,
        rolled_back_by: str | None = None,
    ) -> None:
        """Rollback to a previous version."""
        target_version = self.get_version(version_number)
        if target_version is None:
            raise ValueError(f"Version {version_number} not found")

        self.update_values(
            new_values=target_version.values,
            updated_by=rolled_back_by,
            change_reason=f"Rollback to version {version_number}",
            merge=False,
        )

    def get_version(self, version_number: int) -> ConfigurationVersion | None:
        """Get a specific version by number."""
        for version in self.versions:
            if version.version_number == version_number:
                return version
        return None

    def activate(self, updated_by: str | None = None) -> None:
        """Activate the configuration."""
        self.is_active = True
        self.updated_at = datetime.now(UTC)
        self.updated_by = updated_by

    def deactivate(self, updated_by: str | None = None) -> None:
        """Deactivate the configuration."""
        self.is_active = False
        self.updated_at = datetime.now(UTC)
        self.updated_by = updated_by

    @property
    def current_version_number(self) -> int:
        """Get the current version number."""
        if not self.versions:
            return 0
        return max(v.version_number for v in self.versions)

    @property
    def is_effective(self) -> bool:
        """Check if the configuration is currently effective."""
        now = datetime.now(UTC)
        if not self.is_active:
            return False
        if self.effective_from and now < self.effective_from:
            return False
        if self.effective_until and now > self.effective_until:
            return False
        return True

    @property
    def fully_qualified_name(self) -> str:
        """Get the fully qualified configuration name."""
        return f"{self.service_id}:{self.environment.value}:{self.name}"

    def to_dict(self, include_secrets: bool = False) -> dict[str, Any]:
        """Convert configuration to dictionary.

        Args:
            include_secrets: If False, secret values are masked

        Returns:
            Dictionary representation of the configuration
        """
        result = dict(self.values)

        if not include_secrets:
            for key in self.get_secret_keys():
                if key in result:
                    result[key] = "***REDACTED***"

        return result

    def to_json(self, include_secrets: bool = False) -> str:
        """Convert configuration to JSON string."""
        return json.dumps(self.to_dict(include_secrets), indent=2)
